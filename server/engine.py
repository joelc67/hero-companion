"""
engine.py - Build validation + stat calculation.

Scope / honesty note
--------------------
The numbers this engine computes come from Mids Reborn *set-bonus* data, which
are flat values (verified against the source, e.g. Luck of the Gambler 5-piece =
+3.75% S/L resistance). Set-bonus totals therefore match Mids exactly.

Innate values from the powers themselves (e.g. the raw defense a toggle grants)
require Mids' attribute-modifier scaling tables (AttribMod.json) and the full
effect-scaling engine, which is out of scope here. The calculator is explicit
about this: it reports the set-bonus contribution to each stat and labels it as
such, so "how close to the soft cap am I from set bonuses" is accurate.
"""

import os
from collections import defaultdict

# ---- Hardcoded CoH constants (Step 6) ----
DEFENSE_SOFT_CAP = 45.0       # %
RESISTANCE_HARD_CAP = 75.0    # % (most ATs; Tanker/Brute differ but spec says 75)
RULE_OF_FIVE = 5              # most set bonuses count up to 5 instances

DEFENSE_TYPES = ["Smashing", "Lethal", "Fire", "Cold", "Energy", "Negative",
                 "Toxic", "Psionic", "Melee", "Ranged", "AoE"]
RESISTANCE_TYPES = ["Smashing", "Lethal", "Fire", "Cold", "Energy", "Negative",
                    "Toxic", "Psionic"]

# Enhancements that are explicitly NOT unique even when slotted many times.
# (Luck of the Gambler: Def/Increased Global Recharge Speed - allow multiples.)
NON_UNIQUE_OVERRIDES = {"luck of the gambler: defense/increased global recharge speed"}

# Hamidon/Titan/Hydra Origins + D-Syncs: NOT set pieces — identical copies stack
# freely in one power, so the per-power duplicate-piece rule never applies to them.
_SPECIAL_IO_PREFIXES = ("Hamidon_", "Titan_", "Hydra_", "DSync_", "Dsync_")

# Special-IO PIECE globals: always-on buffs the IO itself grants (distinct from
# set bonuses). Their values aren't in the parseable enhancement data (the FX is
# a placeholder), so these are the known Homecoming constants, matched by
# (set substring, piece substring) against a slotted piece. damage_type "None"
# spreads to all types. unique=True counts once per build; False counts per slot.
PIECE_GLOBALS = [
    {"set": "luck of the gambler", "piece": "global recharge", "unique": False,
     "effects": [{"effect": "RechargeTime", "value": 0.075}]},
    {"set": "steadfast protection", "piece": "+def 3", "unique": True,
     "effects": [{"effect": "Defense", "damage_type": "None", "value": 0.03}]},
    {"set": "gladiator's armor", "piece": "+3% def", "unique": True,
     "effects": [{"effect": "Defense", "damage_type": "None", "value": 0.03}]},
    {"set": "shield wall", "piece": "+5% res", "unique": True,
     "effects": [{"effect": "Resistance", "damage_type": "None", "value": 0.05}]},
    {"set": "kismet", "piece": "accuracy +6", "unique": True,
     "effects": [{"effect": "ToHit", "value": 0.06}]},
    # Regen/recovery uniques (verified vs MidsReborn data + Homecoming wiki; the
    # game models them as 100%-chance 120s procs = effectively always-on).
    {"set": "numina", "piece": "regeneration", "unique": True,
     "effects": [{"effect": "Regeneration", "value": 0.20},
                 {"effect": "Recovery", "value": 0.10}]},
    {"set": "miracle", "piece": "recovery", "unique": True,
     "effects": [{"effect": "Recovery", "value": 0.15}]},
    {"set": "regenerative tissue", "piece": "regeneration", "unique": True,
     "effects": [{"effect": "Regeneration", "value": 0.25}]},
    # SUSTAIN procs — the masters universally slot these in Stamina/Health (the free Fitness
    # real estate) and the tool was BLIND to them (no parseable FX). Added so the solver SEES +
    # PLACES them (every modern master fit has them). Values are CONSERVATIVE effective estimates
    # of the chance-proc's always-on equivalent in an auto power — [ESTIMATE — audit vs Mids].
    {"set": "performance shifter", "piece": "+end", "unique": True,
     "effects": [{"effect": "Recovery", "value": 0.10}]},          # Chance for +Endurance
    {"set": "power transfer", "piece": "heal self", "unique": True,
     "effects": [{"effect": "Regeneration", "value": 0.125}]},     # Chance to Heal Self
    {"set": "panacea", "piece": "hit points", "unique": True,
     "effects": [{"effect": "Recovery", "value": 0.05},            # Chance for +HP/+End
                 {"effect": "Regeneration", "value": 0.05}]},
]


# eSchedule index per enhanceable aspect (mirrors Enhancement.GetSchedule)
ED_SCHEDULE = {"Defense": 1, "Resistance": 1, "ToHit": 1, "Range": 1,
               "Interrupt": 2, "Mez": 0}
# Power types that are "always on" and counted in passive totals.
ACTIVE_POWER_TYPES = {1, 2}   # Auto, Toggle
# Situational powers that the data marks as toggle/auto but are NOT always-on in
# combat (their effects apply only under a special condition). Rest, e.g., gives
# a huge self-defense/resistance penalty that only applies while actually resting
# out of combat — counting it wrecks totals. Imported builds carry these; the
# solver/generator never picks them.
NONCOMBAT_POWERS = {"Inherent.Inherent.Rest"}


def apply_ed_sched(sched, val, mult_ed):
    """Mirror Enhancement.ApplyED using the Maths.mhd EDRT thresholds.
    mult_ed: {schedule_index: [t1, t2, t3]}. val/result are fractions."""
    ed = mult_ed.get(str(sched)) or mult_ed.get(sched)
    if not ed:
        return val
    if val <= ed[0]:
        return val
    edm0 = ed[0]
    edm1 = ed[0] + (ed[1] - ed[0]) * 0.9
    edm2 = edm1 + (ed[2] - ed[1]) * 0.7
    if val > ed[2]:
        return edm2 + (val - ed[2]) * 0.15
    if val > ed[1]:
        return edm1 + (val - ed[1]) * 0.7
    return edm0 + (val - ed[0]) * 0.9


def _pv_ok(pv_mode, pvp):
    """Whether an effect/bonus applies in the current arena. Mirrors Mids'
    DisablePvE flag: Any(0) always; PvE(1) only out of PvP; PvP(2) only in PvP."""
    pm = pv_mode or 0
    if pm == 0:
        return True
    return pm == 2 if pvp else pm == 1


def _scale_io(value, sched, eff_level, ref_level, mult_io):
    """Scale a stored IO enhancement value (computed at ref_level) to eff_level via
    the MultIO[level][schedule] table. value(L) = stored * MultIO[L]/MultIO[ref].
    Returns the value unchanged when it isn't level-scalable (proc/odd schedule)."""
    if not mult_io or sched is None or sched < 0 or sched > 3:
        return value
    e = max(10, min(50, int(eff_level)))
    r = max(10, min(50, int(ref_level)))
    if e == r:
        return value
    row_e = mult_io.get(str(e)) or mult_io.get(e)
    row_r = mult_io.get(str(r)) or mult_io.get(r)
    if not row_e or not row_r or not row_r[sched]:
        return value
    return value * (row_e[sched] / row_r[sched])


def _scaled_boosts(slot, ctx):
    """Yield (aspect, value) for a slot's enhancement, scaling the stored max-level
    magnitude down to the IO's actual level. Attuned/Superior IOs scale to the
    character level (capped at the set's max). Unknown level -> stored value as-is
    (so generated builds, which carry no level, are unaffected)."""
    boosts = ctx["piece_boosts"].get(slot.get("piece_uid"))
    if not boosts:
        return
    mult_io = ctx.get("mult_io")
    ref = (ctx.get("piece_ref_level") or {}).get(slot.get("piece_uid"))
    if not (mult_io and ref):
        for b in boosts:
            yield b["aspect"], b["value"]
        return
    if slot.get("attuned"):
        eff = min(int(ctx.get("char_level") or 50), ref)
    else:                          # an IO can't exceed its set's max level
        eff = min(slot.get("io_level") or ref, ref)
    for b in boosts:
        yield b["aspect"], _scale_io(b["value"], b.get("schedule"), eff, ref, mult_io)


# ---------------------------------------------------------------------------
# Validation (Step 6)
# ---------------------------------------------------------------------------
def validate_build(build):
    """Return {errors:[...], warnings:[...]} for a build state."""
    errors = []
    warnings = []

    unique_seen = defaultdict(int)        # piece identity -> count
    bonus_counter = defaultdict(int)      # bonus signature -> count (rule of 5)

    for power in build.get("powers", []):
        pname = power.get("display_name") or power.get("full_name") or "?"
        accepted = set(power.get("accepted_set_category_ids", []))
        # per-power per-set piece counts (for rule-of-5 + ED hints)
        set_pieces = defaultdict(list)

        for i, slot in enumerate(power.get("slots", []) or []):
            if not slot:
                continue
            cat = slot.get("category_id")
            set_name = slot.get("set_name", "?")
            piece_name = slot.get("piece_name", "?")

            # 1) CATEGORY ENFORCEMENT - the core rule
            if cat is not None and accepted and cat not in accepted:
                errors.append(
                    f"'{set_name}: {piece_name}' (category {cat}) is not valid "
                    f"in '{pname}'. Accepted categories: {sorted(accepted)}.")

            # 2) UNIQUE enhancement - max one per build
            ident = (slot.get("set_name", ""), slot.get("piece_name", "")).__str__().lower()
            label = f"{slot.get('set_name','')}: {slot.get('piece_name','')}".lower()
            if slot.get("unique") and label not in NON_UNIQUE_OVERRIDES:
                unique_seen[label] += 1

            set_uid = slot.get("set_uid")
            if set_uid:
                set_pieces[set_uid].append(slot)

        # within one power, a given set's piece should not be duplicated.
        # Hamidon/Titan/Hydra Origins and D-Syncs are EXEMPT: they aren't set pieces —
        # the game lets you stack as many identical ones in a power as you like
        # (field report: HO x2 cores were warned as "duplicate piece" — wrongly).
        for set_uid, slots in set_pieces.items():
            seen_pieces = defaultdict(int)
            for s in slots:
                pid = s.get("piece_uid") or s.get("piece_name") or ""
                if str(pid).startswith(_SPECIAL_IO_PREFIXES):
                    continue
                seen_pieces[pid] += 1
            for pid, c in seen_pieces.items():
                if c > 1:
                    warnings.append(
                        f"'{pname}': duplicate piece slotted {c}x in the same set "
                        f"({slots[0].get('set_name','?')}). A set piece can only be "
                        f"slotted once per power.")

    for label, count in unique_seen.items():
        if count > 1:
            errors.append(
                f"Unique enhancement '{label}' is slotted {count} times. "
                f"Unique enhancements are limited to ONE per build.")

    return {"errors": errors, "warnings": warnings}


# ---------------------------------------------------------------------------
# Stat calculation (Step 3 / Step 5 center panel)
# ---------------------------------------------------------------------------
def _empty_totals():
    return {
        "defense": {t: 0.0 for t in DEFENSE_TYPES},
        "resistance": {t: 0.0 for t in RESISTANCE_TYPES},
        "recharge": 0.0,
        "recovery": 0.0,
        "regeneration": 0.0,
        "max_hp": 0.0,
        "tohit": 0.0,
        "accuracy": 0.0,
    }


def _power_totals(build, totals, ctx):
    """Add active-power self-buff contributions (base x enhancement w/ ED)."""
    if not ctx:
        return
    power_by_full = ctx["power_by_full"]
    piece_boosts = ctx["piece_boosts"]
    mod_tables = ctx["modifier_tables"]
    mult_ed = ctx["mult_ed"]
    col = ctx["at_column"]
    if col is None or col < 0:
        return
    pvp = bool(build.get("pvp"))

    for power in build.get("powers", []):
        full = power.get("full_name")
        p = power_by_full.get(full)
        if not p:
            continue
        if full in NONCOMBAT_POWERS:
            continue
        # Per-power override; default to auto/toggle powers being always-on.
        include = power.get("include_in_totals")
        if include is None:
            include = p.get("power_type") in ACTIVE_POWER_TYPES
        if not include:
            continue
        self_fx = p.get("self_effects") or []
        if not self_fx:
            continue
        # sum this power's slotted enhancement values per aspect
        enh_by_aspect = defaultdict(float)
        for slot in power.get("slots", []) or []:
            if not slot or not slot.get("piece_uid"):
                continue
            for asp, val in _scaled_boosts(slot, ctx):
                enh_by_aspect[asp] += val
        # apply ED per aspect
        ed_by_aspect = {}
        for asp, tot in enh_by_aspect.items():
            ed_by_aspect[asp] = apply_ed_sched(ED_SCHEDULE.get(asp, 0), tot, mult_ed)
        # apply each self effect: base x (1 + enhancement)
        for fx in self_fx:
            if not _pv_ok(fx.get("pv_mode", 0), pvp):
                continue
            row = mod_tables.get(fx["modifier_table"])
            if not row or col >= len(row):
                continue
            base = fx["scale"] * fx.get("nmag", 1.0) * row[col]
            boost = ed_by_aspect.get(fx["enhance_aspect"], 0.0)
            val = base * (1.0 + boost)
            _add_power_effect(totals, fx["effect"], fx["damage_type"], val,
                              base_hp=ctx.get("at_base_hp"))


def _add_power_effect(totals, et, dt, val, base_hp=None):
    if et == "Defense":
        if dt in totals["defense"]:
            totals["defense"][dt] += val
    elif et == "Resistance":
        if dt in totals["resistance"]:
            totals["resistance"][dt] += val
    elif et == "RechargeTime":
        totals["recharge"] += val
    elif et == "Recovery":
        totals["recovery"] += val
    elif et == "Regeneration":
        totals["regeneration"] += val
    elif et == "HitPoints":
        # A POWER's MaxHP effect comes out of the AT's HP modifier table as FLAT
        # hit points (Dull Pain-class: +540 HP), but totals["max_hp"] is a FRACTION
        # of base HP (set bonuses add 0.015-style values). Convert flat -> fraction,
        # or the display explodes (field report: '+58913.12%' on a /Regen Scrapper).
        # Values <= 3 are already fractions (percent-style HP buffs).
        if base_hp and abs(val) > 3.0:
            val = val / base_hp
        totals["max_hp"] += val
    elif et == "ToHit":
        totals["tohit"] += val


def _incarnate_totals(build, totals, ctx):
    """Add incarnate self-buffs (peak values) when include_incarnates is set.

    Each effect is applied the way it actually works, so incarnates drive the
    build's goals the same way set bonuses do:
      * Destiny / Hybrid FLAT buffs (Barrier +Def/Res, Ageless +Rech, Clarion,
        Assault's recharge, etc.) go straight into totals — a flat buff is exactly
        what they are. Barrier's value is its initial spike (~57%), the fully-
        buffed peak Mids displays.
      * DamageBuff (Musculature Alpha, Assault Hybrid) is a GLOBAL +damage%,
        folded into totals['damage_buff'] so _offense applies it to every attack.
        The parsed effect repeats per damage-type with the same value, so we take
        ONE value per incarnate (max), not the sum of the per-type entries.
      * Alpha Res/Def is an enhancement-STRENGTH boost on your armor powers, not a
        flat buff — so it adds (armor toggle's base res/def x strength) per type.
        Applying it flat (+33% to every type) would wildly over-state. Needs the
        per-power base res/def the server attaches (p['_base_rd']); if absent it
        contributes nothing rather than guessing.
    """
    if not ctx or not build.get("include_incarnates"):
        return
    fx_by_full = ctx.get("incarnate_fx") or {}
    chosen = build.get("incarnates_full") or {}
    alpha_str = {"Resistance": 0.0, "Defense": 0.0}
    for slot, full_name in chosen.items():
        dmg_buff = 0.0
        for eff in fx_by_full.get(full_name, []):
            et = eff.get("effect")
            if et == "DamageBuff":
                dmg_buff = max(dmg_buff, eff.get("value", 0.0))
            elif slot == "Alpha" and et in ("Resistance", "Defense"):
                alpha_str[et] = max(alpha_str[et], eff.get("value", 0.0))
            else:
                _apply_effect(totals, eff)
        if dmg_buff:
            totals["damage_buff"] = totals.get("damage_buff", 0.0) + dmg_buff
    if alpha_str["Resistance"] or alpha_str["Defense"]:
        for power in build.get("powers", []):
            for (kind, t), base in (power.get("_base_rd") or {}).items():
                s = alpha_str.get(kind, 0.0)
                bucket = "resistance" if kind == "Resistance" else "defense"
                if s and t in totals[bucket]:
                    totals[bucket][t] += base * s


# Common always-up EXTERNAL buffs: the 3 inspiration Amplifiers (temp powers
# most players keep running) + the permanent passive accolades. Values verified
# against MidsReborn data (amplifier scales on Melee_Ones=1.0 → exact fractions).
# Accolades give Max HP / Endurance, NOT resistance — the res/def here is from
# the Defense Amplifier. These are OFF by default and clearly attributed.
EXTERNAL_BUFFS = [
    # Defense Amplifier
    {"effect": "Defense", "damage_type": "None", "value": 0.05},
    {"effect": "Resistance", "damage_type": "None", "value": 0.075},
    # Offense Amplifier
    {"effect": "ToHit", "value": 0.10},
    {"effect": "RechargeTime", "value": 0.15},
    # Survival Amplifier
    {"effect": "Regeneration", "value": 0.40},
    {"effect": "Recovery", "value": 0.20},
    # Accolades (permanent) — Max HP (approx; flat HP is AT-dependent)
    {"effect": "HitPoints", "value": 0.10},
]


def _external_buffs(build, totals):
    """Add accolade + amplifier buffs when include_external is set (off by
    default; these are temporary/external, not from the build's powers)."""
    if not build.get("include_external"):
        return
    for eff in EXTERNAL_BUFFS:
        _apply_effect(totals, eff)


def _piece_globals(build, totals):
    """Add always-on special-IO piece globals (Steadfast +3% Def, LotG +7.5%
    Recharge, Shield Wall +5% Res, Kismet +6% ToHit, etc.). These work whether
    or not the host power is active, so every slotted piece counts; unique
    globals count once across the build, LotG recharge counts per slot."""
    seen_unique = set()
    for power in build.get("powers", []):
        for slot in power.get("slots", []) or []:
            if not slot:
                continue
            sn = (slot.get("set_name") or "").lower()
            pn = (slot.get("piece_name") or "").lower()
            for g in PIECE_GLOBALS:
                if g["set"] in sn and g["piece"] in pn:
                    if g["unique"]:
                        if g["set"] in seen_unique:
                            break
                        seen_unique.add(g["set"])
                    for eff in g["effects"]:
                        _apply_effect(totals, eff)
                    break   # at most one global per slotted piece


def _resolve_mag(d, row, col):
    """Resolved base magnitude of one effect: scale*nMag*table[AT.col]*prob.
    Damage tables store negatives (damage subtracts HP); callers abs() those."""
    return d["scale"] * d.get("nmag", 1.0) * row[col] * d.get("probability", 1.0)


def _chain_dps(attacks, window=120.0):
    """Greedy gapless single-target rotation: repeatedly cast the highest-DPA
    (damage-per-animation) attack that has recharged; if none is ready, skip to
    the next ready time. Returns (sustained ST DPS, endurance drained per second) —
    end/sec = Σ end_cost of the casts over the window, the cost of attacking nonstop.
    Not provably optimal, but a transparent, deterministic estimate."""
    n = len(attacks)
    casts = [a["cast_time"] for a in attacks]
    rech = [a["recharge"] for a in attacks]
    dval = [a["damage"] for a in attacks]
    ecost = [a.get("end_cost") or 0.0 for a in attacks]
    order = sorted(range(n), key=lambda i: (attacks[i]["dpa"] or 0), reverse=True)
    avail = [0.0] * n
    t = dmg = end = 0.0
    guard = 0
    while t < window and guard < 100000:
        guard += 1
        ready = [i for i in order if avail[i] <= t and casts[i] > 0]
        if ready:
            i = ready[0]
            dmg += dval[i]
            end += ecost[i]
            t += casts[i]
            avail[i] = t + rech[i]
        else:
            future = [avail[i] for i in range(n) if casts[i] > 0 and avail[i] > t]
            if not future:
                break
            t = min(future)
    if window <= 0:
        return 0.0, 0.0
    return dmg / window, end / window


# Set categories that only AoE attacks accept. Kept for proc_pass, which needs powers that
# ACCEPT AoE-damage proc SETS (not merely hit an area) — a Confuse cone like Seeds takes no
# damage proc, so categories are the right signal there.
AOE_DMG_CATS = {"Targeted AoE Damage", "PBAoE Damage", "Melee AoE",
                "Player Melee AoE", "Targeted AoE"}

# Real geometry (now extracted into powers.json): eEffectArea 2 Sphere / 3 Cone / 4 Location
# are AoE even when the cast power's own radius is 0 (the patch/pets carry the area).
_AOE_EFFECT_AREAS = {2, 3, 4}


# ── Damage-proc pricing (model v24) ─────────────────────────────────────────
# PPM math prices each slotted %Damage proc into the attack's damage, so the
# optimizer can trade set bonuses against procs — the current meta's core trade.
# PROVISIONAL until verified against homecoming.wiki "Procs Per Minute":
#   click chance = min(90%, PPM × (local_recharge_time + cast) / 60)
#   (LOCAL slotted recharge only — global recharge deliberately excluded, per PPM rules)
#   AoE divides by AreaFactor = 1 + radius × 0.15 × (0.75 + 0.25×arc/360 for cones)
_PROC_TABLE = None


def _proc_table():
    global _PROC_TABLE
    if _PROC_TABLE is None:
        import json as _json
        import sys as _sys
        if getattr(_sys, "frozen", False):
            base = getattr(_sys, "_MEIPASS", os.path.dirname(_sys.executable))
        else:
            base = os.path.join(os.path.dirname(__file__), "..")
        try:
            with open(os.path.join(base, "data", "proc_catalog.json"), encoding="utf-8") as f:
                cat = _json.load(f)
            _PROC_TABLE = {p["uid"]: (p.get("ppm") or 3.5, p.get("dmg50") or 71.75)
                           for procs in cat.get("damage_procs", {}).values() for p in procs}
        except Exception:  # noqa: BLE001
            _PROC_TABLE = {}
    return _PROC_TABLE


def _area_factor(rec):
    """Bopper's canonical PPM area factor (the HC forums PPM guide, corroborated by the
    Homecoming wiki): AF = [1 + 0.15·R − 0.011·R·(360−Arc)/30] × 0.75 + 0.25, with
    Arc=360 for spheres/PBAoE (our data stores arc=0 when a power isn't a cone).
    Replaces the provisional reconstruction, which over-discounted spheres ~20% and
    priced narrow cones at roughly a THIRD of their real proc chance."""
    r = rec.get("radius") or 0
    if r <= 0:
        return 1.0
    arc = rec.get("arc") or 360.0
    inner = 1.0 + 0.15 * r - 0.011 * r * (360.0 - arc) / 30.0
    return max(1.0, inner * 0.75 + 0.25)


def proc_damage_per_activation(power, rec, local_rech_boost):
    """Expected proc damage added to ONE activation of this attack, from every
    %Damage proc slotted in it."""
    table = _proc_table()
    total = 0.0
    for slot in (power.get("slots") or []):
        if not slot:
            continue
        entry = table.get(slot.get("piece_uid"))
        if not entry:
            continue
        ppm, dmg = entry
        base_rech = rec.get("base_recharge") or 0.0
        cast = rec.get("cast_time") or 0.0
        local_rech = base_rech / (1.0 + max(0.0, local_rech_boost))
        chance = min(0.90, ppm * (local_rech + cast) / 60.0 / _area_factor(rec))
        total += chance * dmg
    return total


def is_aoe(rec):
    """Does the power hit an AREA? From the authoritative Mids geometry (radius + effect_area),
    not guessed from accepted set categories. PBAoE/cone/sphere/location all qualify."""
    return (rec.get("radius") or 0) > 0 or (rec.get("effect_area") or 0) in _AOE_EFFECT_AREAS


def _offense(build, totals, ctx):
    """Per-attack enhanced damage + an estimated single-target DPS. Damage =
    Σ scale·nMag·|AttribMod[table][AT.col]|·hitProb over a power's damage
    effects, × (1 + ED-capped slotted Damage enhancement + global +Dmg), capped
    at the AT damage cap. Recharge uses slotted recharge (ED) + global recharge,
    capped at the AT recharge cap. Returns {} if ctx/data missing (never raises)."""
    if not ctx:
        return {}
    col = ctx.get("at_column")
    if col is None or col < 0:
        return {}
    power_by_full = ctx["power_by_full"]
    piece_boosts = ctx["piece_boosts"]
    mod_tables = ctx["modifier_tables"]
    mult_ed = ctx["mult_ed"]
    global_rech = totals.get("recharge", 0.0)
    global_dmg = totals.get("damage_buff", 0.0)
    dmg_cap = ctx.get("at_damage_cap")
    rech_cap = ctx.get("at_recharge_cap")
    pvp = bool(build.get("pvp"))
    # POOL melee punches are not part of a ranged AT's job: a Defender/Blaster/Corruptor
    # doesn't weave Boxing between blasts, so counting pool melee in the ST chain made a
    # never-pressed mule attack look like real DPS (86 DPA Boxing on a Poison Defender) —
    # which is what made "trash picks" beat always-on toggles. Melee-native ATs keep them.
    melee_native = (build.get("archetype") in
                    ("Class_Scrapper", "Class_Brute", "Class_Stalker", "Class_Tanker",
                     "Class_Peacebringer", "Class_Warshade"))
    attacks = []
    for power in build.get("powers", []):
        p = power_by_full.get(power.get("full_name"))
        if not p or not p.get("damage_effects"):
            continue
        fn = p.get("full_name") or ""
        if (not melee_native and (fn.startswith("Pool.") or fn.startswith("Inherent."))
                and "Melee Damage" in (p.get("accepted_set_categories") or [])):
            continue
        base = 0.0
        dtypes = set()
        for d in p["damage_effects"]:
            if not _pv_ok(d.get("pv_mode", 0), pvp):
                continue
            row = mod_tables.get(d["modifier_table"])
            if not row or col >= len(row):
                continue
            base += abs(_resolve_mag(d, row, col))
            if d["damage_type"] not in ("None", "Special"):
                dtypes.add(d["damage_type"])
        if base <= 0:
            continue
        enh = defaultdict(float)
        for slot in power.get("slots", []) or []:
            if not slot or not slot.get("piece_uid"):
                continue
            for asp, val in _scaled_boosts(slot, ctx):
                enh[asp] += val
        dmg_boost = apply_ed_sched(ED_SCHEDULE.get("Damage", 0),
                                   enh.get("Damage", 0.0), mult_ed) + global_dmg
        if dmg_cap is not None:
            dmg_boost = min(dmg_boost, dmg_cap)
        rech_boost = apply_ed_sched(ED_SCHEDULE.get("RechargeTime", 0),
                                    enh.get("RechargeTime", 0.0), mult_ed)
        rech_total = rech_boost + global_rech
        if rech_cap is not None:
            rech_total = min(rech_total, rech_cap)
        dmg = base * (1.0 + dmg_boost)
        # model v24: slotted %Damage procs are DAMAGE — priced by PPM math (see
        # proc_damage_per_activation). Procs ignore the damage buff/cap by design.
        dmg += proc_damage_per_activation(power, p, rech_boost)
        cast = p.get("cast_time") or 0.0
        base_rech = p.get("base_recharge") or 0.0
        actual_rech = base_rech / (1.0 + rech_total) if rech_total > -0.999 else base_rech
        cycle = cast + actual_rech
        # AoE vs single-target by the set categories the power accepts — no radius
        # field in the data, but a hit-many attack always accepts an AoE damage set.
        is_aoe_hit = is_aoe(p)                  # real geometry: hits an area (radius/effect_area)
        attacks.append({
            "name": p.get("display_name"),
            "damage": round(dmg, 1),
            "damage_types": sorted(dtypes),
            "cast_time": round(cast, 2),
            "recharge": round(actual_rech, 2),
            "end_cost": p.get("end_cost") or 0.0,
            "is_aoe": is_aoe_hit,
            "dpa": round(dmg / cast, 1) if cast > 0 else None,
            "dps_spam": round(dmg / cycle, 1) if cycle > 0 else None,
        })
    if not attacks:
        return {}
    st_dps, chain_end_ps = _chain_dps(attacks)
    # Farm throughput: cycle every AoE as it recharges. Sum of AoE spam DPS is the
    # right damage objective for a FARMER (per the user); single-target chain is for
    # EB/AV finishers. Per-target value — ×spawn-size in play, but the relative
    # number is what the solver optimizes.
    aoe = [a for a in attacks if a["is_aoe"] and a["dps_spam"]]
    aoe_dps = round(sum(a["dps_spam"] for a in aoe), 1)
    aoe_burst = round(sum(a["damage"] for a in aoe), 1)
    attacks.sort(key=lambda a: (a["dpa"] or 0), reverse=True)
    return {"attacks": attacks, "st_dps": round(st_dps, 1),
            "top_dpa": attacks[0]["dpa"], "attack_count": len(attacks),
            "aoe_dps": aoe_dps, "aoe_burst": aoe_burst, "aoe_count": len(aoe),
            "chain_end_per_sec": round(chain_end_ps, 2)}    # endurance to attack nonstop


def _pet_damage_for_powerset(ps_full, ctx, pet_col, dmg_boost, pvp=False):
    """Best-attack-chain DPS for one pet powerset's attacks (pet's own AT
    column, fixed recharge, + the summon power's slotted damage boost)."""
    power_by_full = ctx["power_by_full"]
    mod_tables = ctx["modifier_tables"]
    powers = ctx.get("powers_by_set", {}).get(ps_full, [])
    attacks = []
    for p in powers:
        if not p.get("damage_effects"):
            continue
        base = 0.0
        for d in p["damage_effects"]:
            if not _pv_ok(d.get("pv_mode", 0), pvp):
                continue
            row = mod_tables.get(d["modifier_table"])
            if row and pet_col < len(row):
                base += abs(_resolve_mag(d, row, pet_col))
        if base <= 0:
            continue
        cast = p.get("cast_time") or 0.0
        rech = p.get("base_recharge") or 0.0
        dmg = base * (1.0 + dmg_boost)
        attacks.append({"name": p.get("display_name"), "damage": dmg,
                        "cast_time": cast, "recharge": rech,
                        "dpa": (dmg / cast) if cast > 0 else 0})
    if not attacks:
        return 0.0, 0
    pet_dps, _ = _chain_dps(attacks)
    return pet_dps, len(attacks)


def _pet_offense(build, totals, ctx):
    """Pet damage: resolve each summon power to its pet entities -> pet powersets ->
    pet attacks, priced with the pet's own class column. The reconciled summon specs
    (data/summons.json 'powers', straight from the game's EntCreate templates) supply
    what the Mids snapshot never had: SQUAD counts (Soldiers = 2xSoldier+1xMedic),
    per-power class (a Controller pet and a Dominator pet can share an entity uid),
    duration (timed summons earn only their UPTIME), and copy_boosts (whether the
    summon's slotting reaches the pets at all). dps_each stays per-pet for display;
    dps_total = each x count x uptime is what the optimizer eats. Returns {} if none."""
    if not ctx:
        return {}
    entities = ctx.get("entities") or {}
    if not entities:
        return {}
    power_by_full = ctx["power_by_full"]
    piece_boosts = ctx["piece_boosts"]
    mult_ed = ctx["mult_ed"]
    class_cols = ctx.get("class_columns") or {}
    specs = ctx.get("summon_powers") or {}
    global_rech = (totals or {}).get("recharge", 0.0)   # totals stores a FRACTION
    pvp = bool(build.get("pvp"))
    pets = []
    for power in build.get("powers", []):
        p = power_by_full.get(power.get("full_name"))
        if not p or not (p.get("summons") or p.get("pet_powersets")):
            continue
        # summon power's slotted enhancement: Damage boosts the pets (when the game
        # copies boosts), Recharge shortens the resummon cycle for timed pets
        dmg_enh = rech_enh = 0.0
        for slot in power.get("slots", []) or []:
            if slot and slot.get("piece_uid"):
                for asp, val in _scaled_boosts(slot, ctx):
                    if asp == "Damage":
                        dmg_enh += val
                    elif asp == "Recharge":
                        rech_enh += val
        dmg_boost = apply_ed_sched(ED_SCHEDULE.get("Damage", 0), dmg_enh, mult_ed)
        spec = specs.get(p.get("full_name"))
        if spec is not None and not spec.get("copy_boosts", True):
            dmg_boost = 0.0                  # the game does not copy slotting to these
        uptime = 1.0
        if spec is not None and not spec.get("permanent"):
            dur = float(spec.get("duration") or 0.0)
            if dur > 0:
                rech_boost = apply_ed_sched(ED_SCHEDULE.get("Recharge", 0),
                                            rech_enh, mult_ed)
                rech_eff = (p.get("base_recharge") or 0.0) / (1.0 + rech_boost
                                                              + global_rech)
                cycle = max(dur, rech_eff + (p.get("cast_time") or 0.0))
                uptime = max(0.05, min(1.0, dur / cycle))
        spec_by_uid = {e.get("uid"): e for e in (spec or {}).get("pets", [])}
        seen_ps = set()
        for uid in p["summons"]:
            ent = entities.get(uid)
            if not ent:
                continue
            se = spec_by_uid.get(uid) or {}
            pet_col = class_cols.get(se.get("class") or ent.get("class_name"))
            if pet_col is None or pet_col < 0:
                continue
            dps = 0.0
            natk = 0
            for ps_full in ent.get("powerset_full_names", []):
                seen_ps.add(ps_full)
                d, n = _pet_damage_for_powerset(ps_full, ctx, pet_col, dmg_boost, pvp)
                dps += d
                natk += n
            if natk == 0 or dps <= 0:    # support/heal pets have no damage
                continue
            count = max(1, int(se.get("count") or 1))
            pets.append({"name": ent.get("display_name") or uid,
                         "from_power": p.get("display_name"),
                         "dps_each": round(dps, 1), "attack_count": natk,
                         "count": count, "uptime": round(uptime, 2),
                         "dps_total": round(dps * count * uptime, 1)})
        # POWER-redirect pseudo-pets (Carrion Creepers' vines): the summon points at pet POWERS,
        # not an entity — their powersets arrive via `pet_powersets` (parse_mids). Price their
        # damage with the standard minion-pet column so the optimizer finally SEES the patch's
        # damage engine (it was invisible — and got the power dropped in deep run 9).
        pet_min_col = class_cols.get("Class_Minion_Pets")
        for ps_full in (p.get("pet_powersets") or []):
            if ps_full in seen_ps or pet_min_col is None:
                continue
            d, n = _pet_damage_for_powerset(ps_full, ctx, pet_min_col, dmg_boost, pvp)
            if n and d > 0:
                pets.append({"name": ps_full.split(".")[-1].replace("_", " "),
                             "from_power": p.get("display_name"),
                             "dps_each": round(d, 1), "attack_count": n,
                             "count": 1, "uptime": round(uptime, 2),
                             "dps_total": round(d * uptime, 1)})
    if not pets:
        return {}
    pets.sort(key=lambda x: x["dps_total"], reverse=True)
    return {"pets": pets,
            "total_each": round(sum(p["dps_each"] for p in pets), 1),
            "total_squad": round(sum(p["dps_total"] for p in pets), 1)}


def _debuff_buff_summary(build, ctx):
    """Aggregate the build's enemy DEBUFFS and ally/self BUFFS as resolved base
    magnitudes (single application, unenhanced). Lets the debuff/buff roles show
    a measured number. Returns (debuffs, buffs) lists of {effect, type, pct}."""
    if not ctx:
        return [], []
    col = ctx.get("at_column")
    if col is None or col < 0:
        return [], []
    power_by_full = ctx["power_by_full"]
    mod_tables = ctx["modifier_tables"]
    pvp = bool(build.get("pvp"))
    deb = defaultdict(float)
    buf = defaultdict(float)
    for power in build.get("powers", []):
        p = power_by_full.get(power.get("full_name"))
        if not p:
            continue
        for d in p.get("debuff_effects", []):
            if not _pv_ok(d.get("pv_mode", 0), pvp):
                continue
            row = mod_tables.get(d["modifier_table"])
            if row and col < len(row):
                deb[(d["effect"], d["damage_type"])] += _resolve_mag(d, row, col)
        for d in p.get("buff_effects", []):
            if not _pv_ok(d.get("pv_mode", 0), pvp):
                continue
            row = mod_tables.get(d["modifier_table"])
            if row and col < len(row):
                buf[(d["effect"], d["damage_type"])] += _resolve_mag(d, row, col)

    def fmt(agg):
        # Collapse an effect that spans the whole elemental spread with one equal
        # value (e.g. -Damage to all types) into a single "(all)" row.
        by_effect = defaultdict(dict)
        for (et, dt), v in agg.items():
            by_effect[et][dt] = v
        out = []
        for et, by_dt in by_effect.items():
            label = "Damage" if et == "DamageBuff" else et
            vals = list(by_dt.values())
            spread = len(by_dt) >= len(RESISTANCE_TYPES) and max(vals) - min(vals) < 1e-4
            if spread:
                v = vals[0]
                if abs(v) >= 1e-4:
                    out.append({"effect": label, "type": "all", "pct": round(v * 100, 1)})
                continue
            for dt, v in by_dt.items():
                if abs(v) < 1e-4:
                    continue
                out.append({"effect": label, "type": dt if dt != "None" else None,
                            "pct": round(v * 100, 1)})
        out.sort(key=lambda r: abs(r["pct"]), reverse=True)
        return out
    return fmt(deb), fmt(buf)


# Force Feedback: Chance for +Recharge — +100% recharge for 5s, PPM 2.0 (client data).
_FF_UIDS = {"Crafted_Force_Feedback_F", "Attuned_Force_Feedback_F"}
_FF_PPM, _FF_BUFF, _FF_DUR = 2.0, 100.0, 5.0


def _ff_recharge_avg(build, totals, ctx):
    """Average +recharge sustained by slotted Force Feedback procs, as a FRACTION
    (totals['recharge'] units — the display layer multiplies by 100)."""
    if not ctx:
        return 0.0
    power_by_full = ctx.get("power_by_full") or {}
    gr = 1.0 + (totals.get("recharge") or 0.0)      # totals stores a fraction
    total = 0.0
    for power in build.get("powers", []):
        if not any(s and s.get("piece_uid") in _FF_UIDS
                   for s in (power.get("slots") or [])):
            continue
        rec = power_by_full.get(power.get("full_name")) or {}
        rech = rec.get("base_recharge") or 8.0
        cast = rec.get("cast_time") or 1.0
        chance = min(0.90, _FF_PPM * (rech + cast) / 60.0 / _area_factor(rec))
        cycle = max(rech / gr + cast, 2.0)
        total += (_FF_BUFF / 100.0) * chance * _FF_DUR / cycle
    return round(min(total, 0.75), 4)


def calculate_build(build, set_bonuses_by_uid, res_cap=RESISTANCE_HARD_CAP, ctx=None):
    """Aggregate the build's defense/resistance/etc.

    Contributions: (1) active power self-buffs (base magnitude from the
    AttribMod tables x slotted enhancement value with ED), (2) set bonuses, and
    (3) incarnate peak buffs when build["include_incarnates"] is true.
    `ctx` carries the lookup data for (1) and (3); without it, only set bonuses
    count.

    res_cap: the archetype's resistance hard cap (90 for Tankers/Brutes, 75
    most). Resistance is a true ceiling; defense's 45% is a soft cap.
    """
    totals = _empty_totals()
    pvp = bool(build.get("pvp"))
    if ctx is not None:                 # per-build character level for IO scaling
        ctx = dict(ctx)
        ctx["char_level"] = build.get("char_level") or 50
    _power_totals(build, totals, ctx)
    _incarnate_totals(build, totals, ctx)
    _piece_globals(build, totals)
    _external_buffs(build, totals)
    bonus_signature_count = defaultdict(int)
    applied_bonuses = []        # for display / AI context
    capped_out = []

    for power in build.get("powers", []):
        set_counts = defaultdict(int)
        for slot in power.get("slots", []) or []:
            if slot and slot.get("set_uid"):
                set_counts[slot["set_uid"]] += 1

        for set_uid, n_pieces in set_counts.items():
            sb = set_bonuses_by_uid.get(set_uid)
            if not sb:
                continue
            for bonus in sb.get("bonuses", []):
                if bonus.get("pieces_required", 99) > n_pieces:
                    continue
                if not _pv_ok(bonus.get("pv_mode", 0), pvp):
                    continue
                sig = "|".join(bonus.get("bonuses", []))
                # Rule of five
                if bonus_signature_count[sig] >= RULE_OF_FIVE:
                    capped_out.append(sig)
                    continue
                bonus_signature_count[sig] += 1
                applied_bonuses.append({
                    "set": sb.get("name"),
                    "pieces": bonus.get("pieces_required"),
                    "text": bonus.get("bonuses"),
                })
                for eff in bonus.get("effects", []):
                    _apply_effect(totals, eff)

    # FORCE FEEDBACK average recharge (v27): a slotted "Chance for +Recharge" in a cycled
    # attack sustains a real average global-recharge uplift — chance/roll = PPM × (base
    # recharge + cast) / 60 (local recharge divides it; FF hosts carry none), value =
    # chance × 5s ÷ the attack's actual cycle at the build's global recharge. Multiple
    # copies don't stack the buff, they add uptime — capped well short of permanent.
    ff = _ff_recharge_avg(build, totals, ctx)
    if ff:
        totals["recharge"] += ff

    # Per-AT bonus caps for HP / regen / recovery (resistance handled separately).
    # hp_cap is ABSOLUTE max HP -> convert to a +%MaxHP ceiling off the AT's base HP;
    # regen/recovery caps are bonus fractions (20.0 => +2000%), as for damage/recharge.
    sec_caps = {}
    if ctx:
        if ctx.get("at_hp_cap") and ctx.get("at_base_hp"):
            sec_caps["max_hp"] = (ctx["at_hp_cap"] / ctx["at_base_hp"] - 1.0) * 100.0
        if ctx.get("at_regen_cap") is not None:
            sec_caps["regeneration"] = ctx["at_regen_cap"] * 100.0
        if ctx.get("at_recovery_cap") is not None:
            sec_caps["recovery"] = ctx["at_recovery_cap"] * 100.0
    # Convert fractions -> percentages for display
    display = _to_display(totals, res_cap, sec_caps, ctx=ctx)
    if ff:
        # transparency: how much of the global recharge FF is carrying (shown in %)
        display["ff_recharge_avg"] = round(ff * 100.0, 1)
    display["incarnates_included"] = bool(build.get("include_incarnates"))
    display["external_included"] = bool(build.get("include_external"))
    extras = []
    if display["incarnates_included"]:
        extras.append("incarnate buffs (Destiny/Hybrid)")
    if display["external_included"]:
        extras.append("accolades + the 3 Amplifiers (Defense Amplifier = +5% Def "
                      "/ +7.5% Res, Offense = +ToHit/+Rech, Survival = +Regen/"
                      "+Recovery; accolades = +Max HP/End)")
    if extras:
        display["note"] = (
            "Totals include: active powers + set bonuses + special-IO globals, "
            "PLUS " + " and ".join(extras) + ". Uncheck those toggles for the "
            "passive powers+IOs baseline. (Amplifiers are temporary buyable "
            "buffs; accolades are permanent.)")
    display["applied_bonus_count"] = len(applied_bonuses)
    display["applied_bonuses"] = applied_bonuses
    display["rule_of_five_capped"] = sorted(set(capped_out))
    # Offense: enhanced per-attack damage + estimated single-target DPS, a
    # debuff/buff summary, and pet damage (shown separately) — so the damage/
    # buff/debuff roles show a real number and pet ATs aren't left blank.
    offense = _offense(build, totals, ctx) or {}
    pets = _pet_offense(build, totals, ctx)
    if offense or pets:
        debuffs, buffs = _debuff_buff_summary(build, ctx)
        offense["debuffs"] = debuffs
        offense["buffs"] = buffs
        if pets:
            offense["pets"] = pets["pets"]
            offense["pet_dps_each"] = pets["total_each"]
            offense["pet_dps_squad"] = pets.get("total_squad")
        display["offense"] = offense
    display["endurance"] = _endurance_balance(build, display, offense, ctx)
    return display


# Base endurance recovery ≈ 1.667 end/sec at 100 max endurance (Homecoming); +Recovery scales
# it. A toggle drains end_cost / activate_period per second; a sustained attack chain drains
# offense.chain_end_per_sec. Net = recovery − (toggles + chain). Travel/sprint/rest toggles
# aren't running while you fight, so they're excluded.
_END_BASE_RECOVERY = 1.667
_END_SKIP_TOGGLES = ("sprint", "prestige", "fly", "hover", "rest", "mystic_flight")


def _endurance_balance(build, display, offense, ctx):
    """Real endurance math (uses end_cost + activate_period): can the build SUSTAIN its rotation,
    or does it need a refuel? Returns recovery/sec vs drain/sec (toggles + nonstop chain) → net."""
    power_by_full = ctx.get("power_by_full", {})
    toggle = 0.0
    for power in build.get("powers", []):
        p = power_by_full.get(power.get("full_name"))
        if not p or p.get("power_type") != 2:
            continue
        ap = p.get("activate_period") or 0
        nm = (p.get("full_name") or "").split(".")[-1].lower()
        if ap <= 0 or any(s in nm for s in _END_SKIP_TOGGLES):
            continue
        toggle += (p.get("end_cost") or 0.0) / ap
    chain = (offense or {}).get("chain_end_per_sec", 0.0)
    rec_pct = (display.get("recovery") or {}).get("value", 0.0) / 100.0
    recovery = _END_BASE_RECOVERY * (1.0 + rec_pct)
    drain = chain + toggle
    out = {"recovery_per_sec": round(recovery, 2), "toggle_drain_per_sec": round(toggle, 2),
           "chain_drain_per_sec": round(chain, 2), "drain_per_sec": round(drain, 2),
           "net_per_sec": round(recovery - drain, 2), "sustainable": (recovery - drain) >= 0}
    if recovery - drain < -0.05:                  # seconds of nonstop attacking before empty
        out["empty_after_sec"] = round(100.0 / (drain - recovery))
    return out


def _apply_effect(totals, eff):
    et = eff.get("effect")
    dt = eff.get("damage_type", "None")
    val = eff.get("value", 0.0)
    if et == "Defense":
        if dt in totals["defense"]:
            totals["defense"][dt] += val
        elif dt in ("None", "Special"):
            for t in DEFENSE_TYPES:
                totals["defense"][t] += val
    elif et == "Resistance":
        if dt in totals["resistance"]:
            totals["resistance"][dt] += val
        elif dt in ("None", "Special"):
            for t in RESISTANCE_TYPES:
                totals["resistance"][t] += val
    elif et == "RechargeTime":
        totals["recharge"] += val
    elif et == "Recovery":
        totals["recovery"] += val
    elif et == "Regeneration":
        totals["regeneration"] += val
    elif et in ("HitPoints",):
        totals["max_hp"] += val
    elif et == "ToHit":
        totals["tohit"] += val
    elif et == "Accuracy":
        totals["accuracy"] += val


def _to_display(totals, res_cap=RESISTANCE_HARD_CAP, sec_caps=None, ctx=None):
    sec_caps = sec_caps or {}

    def pct(x):
        return round(x * 100.0, 2)

    def capped(key, label):
        """A +% stat with a per-AT hard cap (HP / regen / recovery): show the capped
        value + the raw + how far over, mirroring resistance. No cap -> plain value."""
        raw = pct(totals[key])
        cap = sec_caps.get(key)
        if cap is None:
            return {"value": raw, "label": label}
        return {"value": min(raw, cap), "raw": raw, "cap": round(cap, 1), "label": label,
                "at_cap": raw >= cap, "over_cap": round(max(0.0, raw - cap), 2),
                "pct_to_cap": round(min(raw / cap * 100, 100), 1) if cap else 0}

    defense = {}
    for t in DEFENSE_TYPES:
        v = pct(totals["defense"][t])
        # 45% is a SOFT cap: values can (and beneficially do) exceed it.
        defense[t] = {"value": v, "cap": DEFENSE_SOFT_CAP,
                      "at_cap": v >= DEFENSE_SOFT_CAP,
                      "over_cap": round(max(0.0, v - DEFENSE_SOFT_CAP), 2),
                      "pct_to_cap": round(min(v / DEFENSE_SOFT_CAP * 100, 100), 1)}
    resistance = {}
    for t in RESISTANCE_TYPES:
        raw = pct(totals["resistance"][t])
        # Resistance is a TRUE ceiling: effective mitigation caps at res_cap. Show the
        # capped value (what actually mitigates) + the overcap separately (a buffer vs
        # -resistance debuffs), so a Fiery-Aura farmer reads 90% + overcap, not 138%.
        v = min(raw, res_cap) if res_cap else raw
        resistance[t] = {"value": v, "raw": raw, "cap": res_cap,
                         "at_cap": raw >= res_cap,
                         "over_cap": round(max(0.0, raw - res_cap), 2),
                         "pct_to_cap": round(min(raw / res_cap * 100, 100), 1) if res_cap else 0}
    # RESULTANT readouts (field report: '+% Max HP' alone answers nothing — show the
    # actual hit points, capped, and the regen in HP/sec). Regen: 100% = full HP over
    # 240s (5% of MaxHP per 12s tick), so HP/sec = MaxHP_final x regen_frac / 240.
    max_hp_abs = {}
    regen_hps = None
    base_hp = (ctx or {}).get("at_base_hp")
    if base_hp:
        hp_cap_abs = (ctx or {}).get("at_hp_cap")
        uncapped = base_hp * (1.0 + totals["max_hp"])
        final = min(uncapped, hp_cap_abs) if hp_cap_abs else uncapped
        max_hp_abs = {"hp_base": round(base_hp, 1), "hp_final": round(final, 1),
                      "hp_uncapped": round(uncapped, 1),
                      "hp_cap_abs": round(hp_cap_abs, 1) if hp_cap_abs else None,
                      "hp_at_cap": bool(hp_cap_abs) and uncapped >= hp_cap_abs}
        regen_frac = 1.0 + totals["regeneration"]
        rc = sec_caps.get("regeneration")
        if rc is not None:
            regen_frac = min(regen_frac, 1.0 + rc / 100.0)
        regen_hps = round(final * regen_frac / 240.0, 2)

    return {
        "defense": defense,
        "resistance": resistance,
        "recharge": {"value": pct(totals["recharge"]), "label": "+% Recharge (global)"},
        "recovery": capped("recovery", "+% Recovery"),
        "regeneration": dict(capped("regeneration", "+% Regeneration"),
                             **({"hp_per_sec": regen_hps} if regen_hps is not None else {})),
        "max_hp": dict(capped("max_hp", "+% Max HP"), **max_hp_abs),
        "tohit": {"value": pct(totals["tohit"]), "label": "+% ToHit"},
        "accuracy": {"value": pct(totals["accuracy"]), "label": "+% Accuracy"},
        "caps": {"defense_soft_cap": DEFENSE_SOFT_CAP,
                 "resistance_hard_cap": res_cap,
                 "max_hp_cap": sec_caps.get("max_hp"),
                 "regen_cap": sec_caps.get("regeneration"),
                 "recovery_cap": sec_caps.get("recovery")},
        "note": "Totals = active (toggle/auto) power values, enhanced with ED, "
                "plus set bonuses and special-IO globals (Steadfast/Gladiator's "
                "+Def, Luck of the Gambler +Recharge, Shield Wall +Res, Kismet "
                "+ToHit). Click buffs (e.g. Hasten, Dull Pain) and incarnate "
                "buffs are not auto-included.",
    }
