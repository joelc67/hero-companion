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

import diag

# ---- Hardcoded CoH constants (Step 6) ----
DEFENSE_SOFT_CAP = 45.0       # %
RESISTANCE_HARD_CAP = 75.0    # % (most ATs; Tanker/Brute differ but spec says 75)
RULE_OF_FIVE = 5              # most set bonuses count up to 5 instances

DEFENSE_TYPES = ["Smashing", "Lethal", "Fire", "Cold", "Energy", "Negative",
                 "Toxic", "Psionic", "Melee", "Ranged", "AoE"]
# v30: your own mezzes last longer (set-bonus duration families, Str aspect)
MEZ_DURATION_EFFECTS = ("Confused", "Held", "Stunned", "Immobilized",
                        "Sleep", "Terrorized")
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
    # Reactive Defenses: Scaling Resist Damage — +3% res(all) always-on, scaling up
    # to +13% as HP falls. Priced at the CONSERVATIVE +3% floor (the always-on part);
    # the scaling tail is situational. Was entirely INVISIBLE to the solver (Maelwys
    # round 2: 'fitting in the Reactive Defences Unique... would have been better').
    {"set": "reactive defenses", "piece": "scaling resist", "unique": True,
     "effects": [{"effect": "Resistance", "damage_type": "None", "value": 0.03}]},
    {"set": "kismet", "piece": "accuracy +6", "unique": True,
     "effects": [{"effect": "ToHit", "value": 0.06}]},
    # v30: the −KB uniques-that-aren't (they stack in-game, unique flag False in
    # the piece data). Mag 4 each, client-baked in data/set_details.json ("Provides
    # 4 points of Knockback protection" / "Reduces Knockback effects by -4").
    # Encoded as Current Knockback −4 — the same shape the back-filled set
    # bonuses use, so _apply_effect prices all KB protection through one branch.
    # family "kb_prot" (cap: ONE per family — mag 4 is the protection threshold,
    # the scorer's own term saturates there). solver_place False for v30: an
    # unconditional phase-0 grab was MEASURED to cost the slot Force Feedback
    # needs (Bots/Marine A/B, 2026-07-10), and the model prices FF higher
    # (recharge-bound output share vs kb_in availability). Players who slot
    # these get full totals + scorer credit; SOLVER placement is the v31
    # slot-value arbitration item, next to the endurance retune.
    {"set": "karma", "piece": "knockback protection", "unique": False,
     "family": "kb_prot", "solver_place": False,
     "effects": [{"effect": "Knockback", "aspect": "Cur", "value": -4.0}]},
    {"set": "steadfast protection", "piece": "knockback protection", "unique": False,
     "family": "kb_prot", "solver_place": False,
     "effects": [{"effect": "Knockback", "aspect": "Cur", "value": -4.0}]},
    {"set": "blessing of the zephyr", "piece": "knockback reduction", "unique": False,
     "family": "kb_prot", "solver_place": False,
     "effects": [{"effect": "Knockback", "aspect": "Cur", "value": -4.0}]},
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
    # real estate). v35 (endurance batch, Q1 ruling 2026-07-21): the +Endurance procs are
    # credited at their MEASURED average (tools/measure_end_procs.py on Joel's raw chatlogs,
    # ~4,900 10s roll windows: rate 0.497/window — the client's 3.0 PPM auto-host formula
    # exactly; grants log-verified at 50: Performance Shifter 10.64 end/proc, Panacea 7.98).
    # Expressed as base-recovery equivalents (end/s ÷ 1.667) so the existing Recovery
    # plumbing prices them; the old values were flagged conservative estimates and undershot
    # the field 3–5×. CORRECTION vs the design paper's Q1 list (log-verified): Power
    # Transfer's proc is a self-HEAL (80.32 HP @50), NOT an endurance return — it keeps its
    # Regeneration credit; PANACEA is the real end-returning sibling. Performance Shifter's
    # unique flag corrected to the game data's False (it stacks; rule of five applies).
    {"set": "performance shifter", "piece": "+end", "unique": False,
     "needs_running_host": True,
     "effects": [{"effect": "Recovery", "value": 0.317}]},         # MEASURED 0.529 end/s
    {"set": "power transfer", "piece": "heal self", "unique": True,
     "needs_running_host": True,
     "effects": [{"effect": "Regeneration", "value": 0.125}]},     # heal proc (NOT +end)
    {"set": "panacea", "piece": "hit points", "unique": True,
     "needs_running_host": True,
     "effects": [{"effect": "Recovery", "value": 0.239},           # MEASURED 0.398 end/s
                 {"effect": "Regeneration", "value": 0.05}]},
    # Theft of Essence: Chance for +Endurance — heal-set proc (click hosts, Dark
    # Regeneration class). UNMEASURED (absent from the log archive); priced from the client
    # PPM formula (3.0 PPM ≈ 0.5 end/s if fired on cooldown) at a stated HALF-USAGE
    # assumption (heals fire when hurt, not on cooldown) → ~0.25 end/s. PROVISIONAL —
    # replace with a measured average when logs carrying it exist.
    {"set": "theft of essence", "piece": "+endurance", "unique": False,
     "effects": [{"effect": "Recovery", "value": 0.15}]},
]


# eSchedule index per enhanceable aspect (mirrors Enhancement.GetSchedule)
ED_SCHEDULE = {"Defense": 1, "Resistance": 1, "ToHit": 1, "Range": 1,
               "Interrupt": 2, "Mez": 0}
# Power types that are "always on" and counted in passive totals.
ACTIVE_POWER_TYPES = {1, 2}   # Auto, Toggle

# eSuppress events that fire the moment you fight (Mids' combat-suppression
# checkboxes): Attacked(64) | HitByFoe(128) | ActivateAttackClick(512) |
# Damaged(1024). An effect suppresses when its bitmask intersects these.
SUPPRESS_IN_COMBAT = 64 | 128 | 512 | 1024
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
    magnitude down to the IO's actual level, then applying the booster/over-level
    multiplier (#6, Mids' GetRelativeLevelMultiplier: +5% per level above even,
    −10% per level below even; a level-53 HO is +3 over its 50 baseline). Attuned
    IOs scale to the character level (capped at the set's max) and can't take
    boosters, so their boost is ignored. Unknown level -> stored value as-is
    (so generated builds, which carry no level, are unaffected)."""
    boosts = ctx["piece_boosts"].get(slot.get("piece_uid"))
    if not boosts:
        return
    mult_io = ctx.get("mult_io")
    ref = (ctx.get("piece_ref_level") or {}).get(slot.get("piece_uid"))
    b = slot.get("boost")
    if b is None and not ref and (slot.get("io_level") or 0) > 50:
        b = int(slot["io_level"]) - 50   # in-game "(53)" HO/D-Sync imports
    b = 0 if slot.get("attuned") else max(-3, min(5, int(b or 0)))
    relmult = (1.0 + 0.05 * b) if b >= 0 else (1.0 + 0.10 * b)
    if not (mult_io and ref):
        for bo in boosts:                # grade-flat specials (HOs/D-Syncs)
            yield bo["aspect"], bo["value"] * relmult
        return
    if slot.get("attuned"):
        eff = min(int(ctx.get("char_level") or 50), ref)
    else:                          # an IO can't exceed its set's max level
        eff = min(slot.get("io_level") or ref, ref)
    for bo in boosts:
        yield bo["aspect"], _scale_io(bo["value"], bo.get("schedule"),
                                      eff, ref, mult_io) * relmult


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

        # Within one power, a given set's piece may appear at most ONCE — the
        # game won't allow a repeat (field report 2026-07-09: the picker let
        # the same LotG piece into several slots). An ERROR, not a warning:
        # the state is impossible in-game, so any math over it is fiction.
        # Hamidon/Titan/Hydra Origins and D-Syncs are EXEMPT: they aren't set
        # pieces — identical copies stack freely.
        for set_uid, slots in set_pieces.items():
            seen_pieces = defaultdict(int)
            for s in slots:
                pid = s.get("piece_uid") or s.get("piece_name") or ""
                if str(pid).startswith(_SPECIAL_IO_PREFIXES):
                    continue
                seen_pieces[pid] += 1
            for pid, c in seen_pieces.items():
                if c > 1:
                    errors.append(
                        f"'{pname}': the same set piece is slotted {c}x "
                        f"({slots[0].get('set_name','?')}). The game won't "
                        f"allow a set piece to repeat within one power — "
                        f"replace the extra cop{'ies' if c > 2 else 'y'}.")

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
        # v39: SELF +DAMAGE STRENGTH. Two shapes share this total and the
        # difference is the whole point. A TOGGLE's penalty (Granite Armor -30%,
        # Bio Armor's Defensive Adaptation -25%) is always on, so it lands at
        # full magnitude. A CLICK's buff (Build Up, Aim, Rage, Soul Drain, Fiery
        # Embrace) is up for its duration once per recharge, so it lands at
        # magnitude x duty cycle - the honest reading, which UNDERSTATES what a
        # player gets by firing it into an alpha, and says so on the label.
        "damage_buff": 0.0,
        "damage_buff_parts": [],   # display-only: what made it up, per power
        "heal_strength": 0.0,   # v29: global +Heal strength (set bonuses)
        # v30: the ten back-filled bonus families (patch_empty_bonus_tiers).
        # Multi-attrib game records were expanded per attrib with EQUAL values,
        # so each total below counts ONE canonical attrib and skips its mirrors
        # (verified: every slow-resist record carries RechargeTime, every
        # movement record RunningSpeed, every KB record Knockback).
        "kb_protection": 0.0,       # protection POINTS (mag), not a percent
        "slow_resist": 0.0,
        # v41: defence-debuff resistance, a FRACTION. Power-granted only - the
        # game ships no DDR set bonus, so nothing else can feed this and there
        # is nothing to double-count against.
        "def_debuff_resist": 0.0,
        # v41: PROTECTION is a magnitude threshold, RESIST a duration cut -
        # different axes, never merged. Per mez type; protection is read as a
        # MINIMUM across types, not a sum (two powers giving 30 each do not
        # give 60 against a mag-3 hold, they both simply exceed it).
        "mez_protection": {},
        "mez_resist": {},         # resists −recharge and −movement debuffs
        "mez_duration": {m: 0.0 for m in MEZ_DURATION_EFFECTS},
        "movement": 0.0,            # own run/fly/jump speed
        "range": 0.0,               # own power range
        "end_discount": 0.0,        # own powers' endurance costs reduced
        "slow_strength": 0.0,       # your cast slows are stronger
        "kb_strength": 0.0,         # your cast knockback is stronger
    }


def _power_totals(build, totals, ctx):
    """Add active-power self-buff contributions (base x enhancement w/ ED).
    Returns the active strength-amplifier preview summary (or None) so the
    display can state what is being amplified."""
    if not ctx:
        return None
    power_by_full = ctx["power_by_full"]
    piece_boosts = ctx["piece_boosts"]
    mod_tables = ctx["modifier_tables"]
    mult_ed = ctx["mult_ed"]
    col = ctx["at_column"]
    if col is None or col < 0:
        return
    pvp = bool(build.get("pvp"))
    # Display-time combat suppression (#9, mirrors Mids' Effects and Maths >
    # Suppression): with the in-combat view on, any self effect whose eSuppress
    # bitmask intersects the attacked/hit/attacking/damaged events is dropped —
    # Stealth's suppressible defense layer goes, its mez-only layer stays.
    # DISPLAY ONLY: the solver/scorer never sets the flag.
    suppress_mask = SUPPRESS_IN_COMBAT if build.get("suppression") else 0

    # STRENGTH-AMPLIFIER PREVIEW (Power Boost / Power Build Up — display only):
    # a CHECKED click power carrying strength_effects amplifies the families it
    # names on OTHER checked powers' buffable effects, mirroring Mids' math
    # (every buff-application loop gates per-effect on Buffable). Consumed
    # families = the ones these totals display. Clicks are never checked by
    # the solver/scorer (they set include only for auto/toggle), so this is
    # structurally inert outside a user's preview. Clarion Radial is NOT here:
    # its incarnate data carries no verified amplifier record.
    _AMP_FAMILIES = {"Defense": "Defense", "ToHit": "ToHit"}
    amp = defaultdict(float)     # family -> summed scale from active previews
    amp_sources = set()
    for power in build.get("powers", []):
        p = power_by_full.get(power.get("full_name"))
        if not p or p.get("power_type") != 0 or not p.get("strength_effects"):
            continue
        if power.get("include_in_totals") is not True:   # explicit preview only
            continue
        for sfx in p["strength_effects"]:
            if sfx.get("modifies") in _AMP_FAMILIES:
                amp[sfx["modifies"]] += sfx.get("scale") or 0.0
                amp_sources.add(power.get("full_name"))

    attr = (ctx or {}).get("_attr")
    for power in build.get("powers", []):
        full = power.get("full_name")
        p = power_by_full.get(full)
        if not p:
            continue
        if power.get("_exemplar_off"):     # exemplar view: power unusable at this level
            continue
        if full in NONCOMBAT_POWERS:
            continue
        _snap = _tsnap(totals) if attr is not None else None
        # Per-power override; default to auto/toggle powers being always-on.
        include = power.get("include_in_totals")
        if include is None:
            include = p.get("power_type") in ACTIVE_POWER_TYPES
        self_fx = p.get("self_effects") or []
        if not self_fx:
            continue
        # v39 MODE BUFFS. A CLICK is not always-on, so its ordinary self effects
        # rightly stay out of the totals - but a mode buff IS real for its
        # duration (Build Up, Aim, Rage, Soul Drain, Fiery Embrace), so those
        # rows alone are admitted, priced by duty cycle below. A toggle keeps
        # everything and gets full magnitude, which is what makes Granite
        # Armor's -30% and Defensive Adaptation's -25% land correctly.
        if not include:
            self_fx = [fx for fx in self_fx if fx.get(_MODE_KEY)]
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
        # v39 ⚠ THE GAME'S TEMPLATE IS ONE BUFF ACROSS EIGHT DAMAGE TYPES, and
        # the back-fill stores it as eight rows (one per type, faithful to the
        # attribs list). Summing them octuples it - measured: Build Up read
        # 0.7111 instead of 0.0889. A damage-strength buff is ONE number, so
        # each distinct (scale, duration) group is counted ONCE per power.
        # ⚠ And Rage's -999 crash is a 10-second zeroing, not a sustained -999
        # buff; it is excluded from the scalar and left to the display.
        _seen_mode = set()
        # apply each self effect: base x (1 + enhancement)
        for fx in self_fx:
            if fx.get(_MODE_KEY):
                # ⚠ A NEGATIVE IS NOT AUTOMATICALLY A CRASH. Granite Armor's
                # -30% and Defensive Adaptation's -25% are sustained toggle
                # penalties and MUST count; Rage's crash is the -999 sentinel
                # fired on a `delay` as the buff expires, which is a transient
                # zeroing and must not. Skipping every negative deleted
                # Granite (measured: -0.30 -> nothing).
                if fx.get("delay") or (fx.get("scale") or 0) <= -900:
                    continue
                # ⚠ THE EFFECT NAME IS PART OF THE KEY. v39 was the only mode
                # family, so (scale, duration, stack) was unambiguous; v41's DDR
                # rows carry the same flag, and two DIFFERENT families that
                # happened to share those three numbers on one power would have
                # silently swallowed each other. No-op for v39 (its eight rows
                # are all DamageBuff and still collapse to one).
                _key = (fx.get("effect"), fx.get("scale"),
                        fx.get("duration"), fx.get("stack"))
                if _key in _seen_mode:
                    continue
                _seen_mode.add(_key)
            if not _pv_ok(fx.get("pv_mode", 0), pvp):
                continue
            if suppress_mask & (fx.get("suppression") or 0):
                continue
            row = mod_tables.get(fx["modifier_table"])
            if not row or col >= len(row):
                continue
            base = fx["scale"] * fx.get("nmag", 1.0) * row[col]
            boost = ed_by_aspect.get(fx["enhance_aspect"], 0.0)
            val = base * (1.0 + boost)
            # ⚠ ONLY A CLICK GETS THE DUTY CYCLE. A toggle is always on, so its
            # magnitude is the whole story - applying a cadence to Granite Armor
            # shrank its -30% to -2.25% (measured) because the template carries a
            # 0.75s tick against a 10s recharge. `include` is exactly the
            # always-on test the totals loop already trusts.
            if fx.get(_MODE_KEY) and not include:
                val *= _mode_duty_cycle(fx, ed_by_aspect.get("Recharge", 0.0))
            # Active amplifier preview: multiply this effect's contribution
            # when its family is amplified, it is buffable (Mids' per-effect
            # gate), and it isn't the amplifier's own effect (Power Boost
            # boosts what you cast during its window, not itself).
            fam = amp.get(fx["effect"])
            if fam and not fx.get("unbuffable") and full not in amp_sources:
                val *= (1.0 + fam)
            _add_power_effect(totals, fx["effect"], fx["damage_type"], val,
                              base_hp=ctx.get("at_base_hp"))
        _attr_flush(attr, {"kind": "power", "power": full,
                           "name": p.get("display_name") or full.split(".")[-1]},
                    totals, _snap)
    if not amp:
        return None
    return {"sources": sorted(power_by_full[f].get("display_name") or f
                              for f in amp_sources),
            "families": {k: round(v, 3) for k, v in amp.items()}}


_MODE_KEY = "mode"


def _mode_duty_cycle(fx, own_recharge_enh):
    """v39: how much of the time a CLICK's mode buff is actually up.

    duration / (base recharge / (1 + the power's OWN recharge enhancement)).

    ⚠ HONEST, AND DELIBERATELY AN UNDERSTATEMENT - Joel's ruling. Nobody fires
    Build Up at random: they fire it into an alpha or a nuke, so the value a
    player really gets sits ABOVE this number. Pricing that premium would mean
    inventing a model of how someone plays, which the client cannot settle, so
    the conservative reading ships and the label says which it is.

    ⚠ GLOBAL recharge is deliberately NOT folded in. totals["recharge"] is still
    accumulating while this loop runs, so reading it here would make the answer
    depend on power order - a correctness hazard for a few points of uptime.
    Own-slotting only, which is order-independent and errs the same way.
    """
    dur = fx.get("duration") or 0.0
    rech = fx.get("host_recharge") or 0.0
    if dur <= 0 or rech <= 0:
        return 1.0                      # no cadence stated -> treat as continuous
    effective = rech / (1.0 + max(0.0, own_recharge_enh))
    return min(1.0, dur / effective) if effective > 0 else 1.0


def _add_power_effect(totals, et, dt, val, base_hp=None, from_attack=False):
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
    elif et == "MezProtection":
        # the client stores protection NEGATIVE (-30); magnitude is what the
        # threshold test needs, so accumulate abs() here. The DATA keeps the
        # game's sign untouched - only this reader takes the magnitude.
        totals["mez_protection"][dt] = totals["mez_protection"].get(dt, 0.0) + abs(val)
    elif et == "MezResist":
        totals["mez_resist"][dt] = totals["mez_resist"].get(dt, 0.0) + val
    elif et == "SlowResist":
        # v40: POWER-GRANTED slow resistance (Wet Ice, Permafrost, Quickness,
        # Time Lord...). Until now this axis was fed ONLY by IO set bonuses, so
        # a build was credited for slow resist from bonuses and got zero from
        # the powers that actually grant it.
        # UNITS VERIFIED, not assumed: totals["slow_resist"] is a FRACTION - the
        # set-bonus path writes it raw and first_principles reads it back as
        # value/100 off the bonus_extras display, which pct() produced. Our rows
        # resolve on the *_Ones tables (literal 1.0), so a client scale of 0.6
        # IS 0.60 and needs no conversion. Same axis as the IO bonuses, so they
        # ADD, which is correct - both resist the same debuff.
        # ⚠ VERIFY VIA bonus_extras.slow_resist.value, NOT the top level.
        # calculate_build returns a curated 20-key response and slow_resist is
        # not one of them; probing the top level shows None however well the
        # branch works, and that cost a correct change a revert.
        totals["slow_resist"] += val
    elif et == "DefDebuffResist":
        # v41: DEFENCE DEBUFF RESISTANCE, and the game says so in its own words -
        # Agile prints "Res(DeBuff DEF)", Tough Hide "+RES (Debuff DEF)". 178
        # powers grant it and our data carried none of it, while the scorer has
        # applied incoming -def pressure since v10 assuming nobody resists.
        # Same units as slow_resist: a FRACTION. Agile resolves 0.2 x
        # Melee_Res_Boolean(Scrapper 0.346) = 0.069; Tough Hide 0.25 x
        # Melee_Ones(1.0) = 0.25. They ADD across powers, which is what the game
        # does; the 95% game cap is applied where the term is consumed.
        # ⚠ VERIFY VIA bonus_extras.def_debuff_resist.value, NOT the top level -
        # calculate_build returns a curated response and this is not in it.
        totals["def_debuff_resist"] += val
    elif et == "DamageBuff":
        # v39. The caller has already applied the duty cycle for a CLICK; a
        # TOGGLE arrives at full magnitude because it is always on. The game's
        # own templates list all eight damage types with one scale, so a single
        # scalar is faithful; Fiery Embrace's extra fire row simply adds more,
        # which is what the game does.
        totals["damage_buff"] += val
        if from_attack:
            totals["damage_buff_attacks"] += val


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
    inc_names = ctx.get("incarnate_names") or {}
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
            # v34 item 5 (Joel's "not a guess" directive): the +damage% total can
            # be the SUM of several incarnates (Alpha + Hybrid Assault), so the
            # per-card attribution must name the ACTUAL contributors, not assume
            # one. Ledger built from the applied records; `slot` is the game-true
            # source class the card reads for uptime wording (Alpha passive vs
            # Hybrid toggle — resolved from the bins in the taxonomy pass, not
            # hardcoded here).
            totals.setdefault("damage_buff_sources", []).append({
                "slot": slot,
                "name": inc_names.get(full_name)
                or full_name.split(".")[-1],
                "value": round(dmg_buff, 4)})
    if alpha_str["Resistance"] or alpha_str["Defense"]:
        for power in build.get("powers", []):
            if power.get("_exemplar_off"):
                continue
            for (kind, t), base in (power.get("_base_rd") or {}).items():
                s = alpha_str.get(kind, 0.0)
                bucket = "resistance" if kind == "Resistance" else "defense"
                if s and t in totals[bucket]:
                    totals[bucket][t] += base * s


# The 3 inspiration AMPLIFIERS (temp powers many players keep running). Values
# verified against MidsReborn data (amplifier scales on Melee_Ones=1.0 → exact
# fractions). v34 (Joel's split ruling, 2026-07-16): amplifiers are their OWN
# thing — accolades no longer ride this list. The old bundled "+10% HitPoints"
# accolade approximation is RETIRED; accolades route through the game-verified
# per-accolade data (data/accolades.json) below.
AMPLIFIER_BUFFS = [
    # Defense Amplifier
    {"effect": "Defense", "damage_type": "None", "value": 0.05},
    {"effect": "Resistance", "damage_type": "None", "value": 0.075},
    # Offense Amplifier
    {"effect": "ToHit", "value": 0.10},
    {"effect": "RechargeTime", "value": 0.15},
    # Survival Amplifier
    {"effect": "Regeneration", "value": 0.40},
    {"effect": "Recovery", "value": 0.20},
]

_ACCOLADE_TABLE = None


def _accolade_table():
    """data/accolades.json (tools/extract_accolades.py — the GAME's own records,
    Joel's data-source ruling). Cached; frozen-exe aware, same base-path dance
    as _proc_table."""
    global _ACCOLADE_TABLE
    if _ACCOLADE_TABLE is None:
        import json as _json
        import sys as _sys
        if getattr(_sys, "frozen", False):
            base = getattr(_sys, "_MEIPASS", os.path.dirname(_sys.executable))
        else:
            base = os.path.join(os.path.dirname(__file__), "..")
        try:
            with open(os.path.join(base, "data", "accolades.json"),
                      encoding="utf-8") as f:
                _ACCOLADE_TABLE = _json.load(f)
        except Exception:  # noqa: BLE001
            _ACCOLADE_TABLE = {}
    return _ACCOLADE_TABLE


def accolade_flat(rec, mod_tables, col):
    """(flat_hp, flat_end) a single accolade grants, from the GAME's own scales:
    scale × its modifier table at the AT's column. This is the SAME arithmetic
    first_principles.accolade_bonus_hp uses on the scoring side — the battery
    pins that the two agree (test_accolade_hp_parity). Corroborated by the
    client's own text: Freedom Phalanx Reserve HitPoints scale 1.0 → +10% MaxHP;
    The Atlas Medallion Endurance scale 5.0 → +5 Max Endurance."""
    eff = rec.get("effects") or {}
    tabs = rec.get("tables") or {}
    flat_hp = flat_end = 0.0
    if eff.get("HitPoints") and col is not None:
        row = mod_tables.get(tabs.get("HitPoints"))
        if row and col < len(row):
            flat_hp = eff["HitPoints"] * row[col]
    if eff.get("Endurance") and col is not None:
        row = mod_tables.get(tabs.get("Endurance"))
        if row and col < len(row):
            flat_end = eff["Endurance"] * row[col]
    return flat_hp, flat_end


def accolade_signature(rec):
    """The game-effect identity of an accolade — its effect scales and modifier
    tables (AT-independent, so it determines the flat value on every AT). Joel's
    ruling 2026-07-17: accolades that grant the SAME effect are the SAME accolade
    under different names (the hero/villain twins — Portal Jockey ≡ Born in
    Battle ≡ Labyrinth Conqueror, all +HP0.5/+End5.0; Task Force Commander ≡
    Invader; …). "No matter what the name of the accolade chosen, the effects
    should be the same" → identical signature = apply ONCE."""
    eff = rec.get("effects") or {}
    tabs = rec.get("tables") or {}
    return tuple(sorted((k, round(float(v), 4), tabs.get(k, ""))
                        for k, v in eff.items()))


def _amplifier_buffs(build, totals):
    """The 3 inspiration amplifiers, when include_amplifiers is set (off by
    default). Split from accolades per Joel's v34 ruling; `include_external`
    stays honored as the legacy alias for back-compatibility with old payloads."""
    if not (build.get("include_amplifiers") or build.get("include_external")):
        return
    for eff in AMPLIFIER_BUFFS:
        _apply_effect(totals, eff)


def _accolade_buffs(build, totals, ctx):
    """v34: the CHECKED accolades feed the displayed totals — the panel's
    checkmarks are the source of truth (UI state == engine state). `accolades`
    is the list of checked accolade keys; empty/absent = none applied. Each
    lands its game-verified +MaxHP (into totals['max_hp'] as a fraction of base
    HP, the Dull Pain convention) and +MaxEnd (flat points into totals's
    max_end). A per-accolade attribution ledger is stamped for the display so a
    number can say where it came from (deliverable #4)."""
    checked = build.get("accolades") or []
    if not checked:
        return
    align = (build.get("alignment") or "hero").lower()
    tbl = _accolade_table()
    mod_tables = ctx.get("modifier_tables") or {}
    col = ctx.get("at_column")
    base_hp = ctx.get("at_base_hp")
    ledger = totals.setdefault("_accolade_ledger", [])
    # GAME-FIRST ALIGNMENT GATE (Joel's ruling + "check the game", 2026-07-17):
    # each accolade record carries an activate_requires alignment gate — hero-
    # only, villain-only, or none. A character is one alignment, so a hero never
    # gets a villain accolade's effect and vice versa. THAT is the game's own
    # reason only one of a hero/villain twin ever applies (Portal Jockey vs Born
    # In Battle). No-gate accolades (Labyrinth Conqueror, Mazebreaker) apply to
    # either alignment, and every alignment-COMPATIBLE accolade STACKS — they are
    # different accolades, so there is no dedup: two distinct bonuses both count.
    for key in checked:
        rec = tbl.get(key)
        if not rec:
            continue
        acc_align = rec.get("alignment")
        if acc_align and acc_align != align:
            # the game leaves an off-alignment accolade dormant — record it as
            # inactive (0 value) so the panel can say why, never add its value.
            ledger.append({"key": key, "display": rec.get("display", key),
                           "hp": 0.0, "end": 0.0, "inactive_alignment": acc_align})
            continue
        flat_hp, flat_end = accolade_flat(rec, mod_tables, col)
        if not (flat_hp or flat_end):
            continue
        if flat_hp and base_hp:
            totals["max_hp"] += flat_hp / base_hp
        if flat_end:
            totals["max_end"] = totals.get("max_end", 0.0) + flat_end
        ledger.append({"key": key, "display": rec.get("display", key),
                       "hp": round(flat_hp, 1), "end": round(flat_end, 1)})


def _external_buffs(build, totals, ctx=None):
    """Back-compat shim: the old single applier, now split. Kept so any caller
    that still calls it gets both halves; new call sites call the two directly."""
    _amplifier_buffs(build, totals)
    if ctx is not None:
        _accolade_buffs(build, totals, ctx)


# ⚠ ACTIVATION-GATED PROCS ARE NOT ALWAYS-ON GLOBALS (field report,
# BasiliskXVIII 2026-08-01, CONFIRMED). Panacea / Performance Shifter / Power
# Transfer are chance-on-activation procs: they fire when the power hosting them
# fires. Their credited values were MEASURED (tools/measure_end_procs.py) with
# the pieces in their normal homes - Health and Stamina, Auto powers that tick
# forever - so the measurement has the host baked into it. Credited in a click
# you rarely cast, that number is fiction, and the solver was free to move them
# into any "global mule" because nothing in the data said otherwise.
#
# Auto (power_type 1) and Toggle (2) run continuously, so the measured rate
# holds. Click (0) does not. Theft of Essence is deliberately NOT flagged: it is
# a healing-set proc already priced for click hosts at a stated half-usage
# assumption.
_ALWAYS_RUNNING_TYPES = {1, 2}      # 1 = Auto, 2 = Toggle (client enum)


def _host_runs_continuously(power, ctx=None):
    pt = power.get("power_type")
    if pt is None and ctx:
        rec = (ctx.get("power_by_full") or {}).get(power.get("full_name")) or {}
        pt = rec.get("power_type")
    return pt in _ALWAYS_RUNNING_TYPES


# ── Exemplar view (display-only, wiki-pinned 2026-08-03) ────────────────────
# Set bonuses die when the combat level drops more than 3 below the IO's level
# — even though the HOST POWER's availability is a separate rule (bonuses
# survive a lost host; both wikis state it). Attuned pieces follow the SET's
# minimum level instead, and purple / PvP / Winter-O / Archetype sets are
# exempt at every level. `ex` = ctx["exemplar"]: {"level", "exempt", "set_min"}
# built once at server load. The solver/scorer never sets it (view, not a
# build property — the suppression precedent).
def _exemplar_bonus_alive(slot, ex):
    if not ex:
        return True
    if slot.get("set_uid") in ex["exempt"]:
        return True
    lvl = ex["level"]
    if slot.get("attuned") or str(slot.get("piece_uid") or "").startswith("Attuned_"):
        return lvl >= (ex["set_min"].get(slot.get("set_uid")) or 10) - 3
    return lvl >= (slot.get("io_level") or 50) - 3


def _piece_globals(build, totals, ctx=None):
    """Add always-on special-IO piece globals (Steadfast +3% Def, LotG +7.5%
    Recharge, Shield Wall +5% Res, Kismet +6% ToHit, etc.). These work whether
    or not the host power is active, so every slotted piece counts; unique
    globals count once across the build; stackable globals (LotG recharge)
    count per slot up to the game's rule of five — a 6th copy grants nothing
    in-game, so it grants nothing here (field-report audit 2026-07-09)."""
    seen_unique = set()
    stack_count = defaultdict(int)
    ex = (ctx or {}).get("exemplar")
    attr = (ctx or {}).get("_attr")
    for power in build.get("powers", []):
        for si, slot in enumerate(power.get("slots", []) or []):
            if not slot:
                continue
            # LotG-class globals follow the same enhancement-level exemplar
            # rule as set bonuses (attuned/exempt-set exceptions included)
            if not _exemplar_bonus_alive(slot, ex):
                continue
            sn = (slot.get("set_name") or "").lower()
            pn = (slot.get("piece_name") or "").lower()
            for g in PIECE_GLOBALS:
                if g["set"] in sn and g["piece"] in pn:
                    if g.get("needs_running_host") and not _host_runs_continuously(power, ctx):
                        # The credit is simply withheld. ! NOT recorded into
                        # `totals` - that holds floats and dicts only, and a
                        # list here broke Force Feedback seating downstream
                        # (the standing gate caught it). diag only exposes
                        # swallowed(), which means something failed; this did
                        # not fail. Surfacing "why is this proc worth 0 here"
                        # on the info card is a UI job, tracked separately -
                        # an honest silence beats a fake log line.
                        break
                    if g["unique"]:
                        if g["set"] in seen_unique:
                            break
                        seen_unique.add(g["set"])
                    else:
                        stack_count[(g["set"], g["piece"])] += 1
                        if stack_count[(g["set"], g["piece"])] > RULE_OF_FIVE:
                            break
                    _snap = _tsnap(totals) if attr is not None else None
                    for eff in g["effects"]:
                        _apply_effect(totals, eff)
                    _attr_flush(attr, {"kind": "global",
                                       "power": power.get("full_name"),
                                       "name": power.get("display_name")
                                       or (power.get("full_name") or "").split(".")[-1],
                                       "slot": si,
                                       "piece": slot.get("piece_name"),
                                       "set": slot.get("set_name"),
                                       "set_uid": slot.get("set_uid")},
                                totals, _snap)
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


# v32: the MEASURED effective area factor for aura/patch proc rolls. The
# dev-archive AF formula (radius 8 → 1.9) undershoots the field by 42%:
# per-proc, per-host attribution on Joel's raw farm chatlogs (ToLG + Shield
# Breaker → Irradiated Ground by set legality; tools/measure_ig_procs.py,
# 26,541 in-stretch hit ticks) measures 10.66%/10.65% per hit tick for
# 3.5 PPM — an effective AF of 1.09. This confirms and quantifies the
# 2026-07-07 pure-window aura finding ("auras behave as AF≈1", 56.7%±3.2
# per-proc per window vs theory's 26.5-30.7). One measured constant, cited;
# clicks keep the dev-verified formula (proc_damage_per_activation).
AURA_PATCH_AF_MEASURED = 1.1


def aura_proc_dps_per_target(power, rec):
    """v31 introduced the term (aura/patch procs were priced ZERO since
    launch): damage procs slotted in a TOGGLE aura or an AUTO patch power
    roll once per activate_period per target, on the CLIENT'S OWN period
    (Blazing Aura 2.0s, Quills 2.0s, the Irradiated Ground pet 2.0s — all
    from powers.bin). Per-target proc DPS = chance × dmg50 ÷ period.
    v32 (Joel's pricing ruling): chance = min(0.90, PPM × period /
    (60 × AURA_PATCH_AF_MEASURED)) — the geometric area factor does NOT
    apply to aura/patch rolls in the field (measured, see the constant's
    citation above); v31's dev-archive AF (1.9 for an 8-radius patch)
    undershot the game by 42% and priced Irradiated Ground out of its own
    signature content."""
    period = rec.get("activate_period") or 0.0
    if period <= 0:
        return 0.0
    table = _proc_table()
    total = 0.0
    for slot in (power.get("slots") or []):
        if not slot:
            continue
        entry = table.get(slot.get("piece_uid"))
        if not entry:
            continue
        ppm, dmg = entry
        chance = min(0.90, ppm * period / (60.0 * AURA_PATCH_AF_MEASURED))
        total += chance * dmg / period
    return total


def resolve_patch_pet(rec, power_by_full):
    """A summoner power's pseudo-pet PATCH attack record, when we have one
    with real mechanics (the additive patcher backfills them from the client
    bin — _patch_pet marks a record whose period/radius are game-verified).
    Naming convention in the data: Pets.<Set>_<Power>.<Power>."""
    if not rec.get("summons") and "summons" not in rec:
        pass
    set_short = (rec.get("powerset_full_name") or "").rsplit(".", 1)[-1]
    pname = (rec.get("full_name") or "").rsplit(".", 1)[-1]
    pet = power_by_full.get(f"Pets.{set_short}_{pname}.{pname}")
    return pet if (pet and pet.get("_patch_pet")
                   and (pet.get("activate_period") or 0) > 0) else None


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
        if power.get("_exemplar_off"):     # exemplar view: attack unusable at this level
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
        enh_dmg = apply_ed_sched(ED_SCHEDULE.get("Damage", 0),
                                 enh.get("Damage", 0.0), mult_ed)
        dmg_boost = enh_dmg + global_dmg
        if dmg_cap is not None:
            dmg_boost = min(dmg_boost, dmg_cap)
        # v34 item 5, law 3 (GAME BOUNDARIES STATED, NOT SUPERSEDED): the
        # EFFECTIVE global +damage% THIS attack actually received after the
        # game's own damage cap — how much the global moved this attack's boost
        # on top of its enhancement. enh already at/over cap -> global adds 0
        # here; both under cap -> the full global. The per-power ⓘ attribution
        # READS this (never the raw build global), so a capped attack states the
        # truth. Display-only ledger field: `dmg` above is unchanged, so totals
        # stay byte-identical (law 1 invariance).
        if global_dmg and dmg_cap is not None:
            global_dmg_eff = max(0.0, dmg_boost - min(enh_dmg, dmg_cap))
        else:
            global_dmg_eff = global_dmg
        rech_boost = apply_ed_sched(ED_SCHEDULE.get("RechargeTime", 0),
                                    enh.get("RechargeTime", 0.0), mult_ed)
        rech_total = rech_boost + global_rech
        if rech_cap is not None:
            rech_total = min(rech_total, rech_cap)
        dmg = base * (1.0 + dmg_boost)
        cast = p.get("cast_time") or 0.0
        base_rech = p.get("base_recharge") or 0.0
        actual_rech = base_rech / (1.0 + rech_total) if rech_total > -0.999 else base_rech
        cycle = cast + actual_rech
        # model v24: slotted %Damage procs are DAMAGE — priced by PPM math.
        # v31: a TOGGLE aura's procs roll per activate_period per target, not
        # per click cycle (Blazing Aura ticks every 2s from the client's own
        # record) — fold the per-second proc DPS through this attack's cycle
        # so dmg/cycle carries it exactly. Clicks keep the v24 formula.
        # Procs ignore the damage buff/cap by design.
        if p.get("power_type") == 2 and (p.get("activate_period") or 0) > 0:
            proc_add = aura_proc_dps_per_target(power, p) * cycle
            proc_per = "cycle"            # auras roll per pulse, per target
        else:
            proc_add = proc_damage_per_activation(power, p, rech_boost)
            proc_per = "use"
        dmg += proc_add
        # Piece 1 (2026-07-28): the proc-vs-set trade LEDGER — display-only
        # fields the ⓘ card reads (law 1: READ, NEVER RE-ADD; `dmg` above is
        # unchanged, totals stay byte-identical). proc_dmg = the expected proc
        # damage already folded in; when the proc pass recorded what it
        # displaced (_proc_trade), the displaced pieces are priced with the
        # SAME enhancement math as everything else — the counterfactual side
        # of the sentence, from data, never guessed.
        proc_n = sum(1 for s in (power.get("slots") or [])
                     if s and s.get("piece_uid") in _proc_table())
        trade_fields = {}
        tr = power.get("_proc_trade")
        if tr and tr.get("displaced"):
            alt = defaultdict(float)
            for slot in tr["displaced"]:
                if slot and slot.get("piece_uid"):
                    for asp, val in _scaled_boosts(slot, ctx):
                        alt[asp] += val
            alt_boost = (apply_ed_sched(ED_SCHEDULE.get("Damage", 0),
                                        alt.get("Damage", 0.0), mult_ed)
                         + global_dmg)
            if dmg_cap is not None:
                alt_boost = min(alt_boost, dmg_cap)
            tsets = []
            for slot in tr["displaced"]:
                sn = slot.get("set_name")
                if sn and sn not in tsets:
                    tsets.append(sn)
            trade_fields = {"trade_kind": tr.get("kind"),
                            "trade_sets": tsets,
                            "trade_set_dmg": round(base * (alt_boost - dmg_boost), 1)}
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
            # v34 item 5: the global +damage% ledger for the ⓘ card — raw build
            # global vs the effective value after this attack's damage cap.
            "global_dmg_raw": round(global_dmg, 4),
            "global_dmg_eff": round(global_dmg_eff, 4),
            # Piece 1: proc-vs-set trade ledger (display-only, see above)
            "proc_dmg": round(proc_add, 1),
            "proc_n": proc_n,
            "proc_per": proc_per,
            **trade_fields,
        })
    # v31 PATCH SUMMONERS (Irradiated Ground, the poster case): the summoning
    # power carries NO damage_effects — its whole output lives on the pseudo-
    # pet, so it never entered this loop and contributed ZERO priced DPS
    # before v31. Procs slotted in the SUMMONER roll on the PET's own pulse
    # (client bin: Auto, activate_period 2.0s, radius 8, 10 targets). Uptime
    # is taken as continuous — the patch's 4s recharge is far under its
    # duration, the standard farm rotation keeps it down (stated assumption).
    for power in build.get("powers", []):
        p = power_by_full.get(power.get("full_name"))
        if not p or p.get("damage_effects"):
            continue                      # damage-carrying powers priced above
        pet = resolve_patch_pet(p, power_by_full)
        if not pet:
            continue
        pdps = aura_proc_dps_per_target(power, pet)
        if pdps <= 0:
            continue
        attacks.append({
            "name": p.get("display_name"), "damage": round(pdps, 1),
            "damage_types": [], "cast_time": 0.0, "recharge": 1.0,
            "end_cost": p.get("end_cost") or 0.0, "is_aoe": True,
            "dpa": None,                  # never part of the click chain
            "dps_spam": round(pdps, 1),   # per-target proc DPS, continuous
            # Piece 1 ledger: this row IS proc damage (the patch pet's rolls)
            "proc_dmg": round(pdps, 1),
            "proc_n": sum(1 for s in (power.get("slots") or [])
                          if s and s.get("piece_uid") in _proc_table()),
            "proc_per": "cycle",
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
    column, fixed recharge, + the summon power's slotted damage boost).
    v38: also returns the damage-weighted mean of the attacks' INHERENT
    accuracy (client field via patch_pet_accuracy; absent → 1.0) — the
    scorer's pet hit chance multiplies it in. Damage-weighting is a stated
    approximation of the chain's cast mix."""
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
                        "acc": p.get("accuracy") or 1.0,
                        "dpa": (dmg / cast) if cast > 0 else 0})
    if not attacks:
        return 0.0, 0, 1.0
    pet_dps, _ = _chain_dps(attacks)
    tot = sum(a["damage"] for a in attacks) or 1.0
    acc_avg = sum(a["damage"] * a["acc"] for a in attacks) / tot
    return pet_dps, len(attacks), acc_avg


# Pet-directed damage buffs (#13, Joel's rulings 2026-07-19). A Mastermind's main
# damage is its pets, and the MM buffs them: the pet-DPS term must credit those
# buffs. GAME-FIRST ROUTING LEVER: a DamageBuff in a power's `buff_effects` is
# projected onto affected allies — MM pets are affected allies, so it reaches them;
# a DamageBuff only in `self_effects` (e.g. Musculature Alpha) is caster-only and
# does NOT. Confirmed sources: Supremacy +25% (aura, uptime 1), Accelerate
# Metabolism / Fulcrum-class (click, uptime-weighted), Temporal Selection (click,
# SINGLE-TARGET radius 0 -> the top-DPS pet only), the Assault HYBRID *Radial*
# incarnate (team/pet PBAoE; *Core* is self-only, excluded), and Pack Mentality
# (Beast Mastery charge mechanic — empty effects, priced by Joel's ruling at
# _PACK_MENTALITY_STACKS of 10 = +16%; the pet-DPS uptime factor already removes
# idle time, so near-max is scenario-consistent). STATED SIMPLIFICATION (Joel
# option B): pets are modeled as always-hitting, so buff ToHit is not credited and
# pet accuracy is deferred to its own item.
_PACK_MENTALITY_STACKS = 8
_PACK_MENTALITY_PER_STACK = 0.02
_PACK_MENTALITY_FN = "Mastermind_Summon.Beast_Mastery.Pack_Mentality"

# v38: MM henchman tier LEVEL SHIFT by class — the count-gated combat-level
# rule (wiki-sourced, docs/pet-tohit-sources.md: at full strength T1 = 3
# henchmen at −2, T2 = 2 at −1, T3 = 1 at −0). The client summon templates
# are structurally silent on this (all `Ranged_Ones` — swept 2026-07-28), so
# the class IS the key; both class-name spellings ship in the data.
_HENCH_TIER_SHIFT = {
    "Class_Minion_Henchman": 2, "Class_Henchman_Minion": 2,
    "Class_Minion_Henchman_Small": 2, "Class_Henchman_Minion_Small": 2,
    "Class_Lt_Henchman": 1, "Class_Henchman_Lt": 1,
    "Class_Boss_Henchman": 0, "Class_Henchman_Boss": 0,
}


def _pet_damage_buff(build, totals, ctx, global_rech):
    """(all_pet_mult, top_pet_extra_mult, tohit_all, tohit_top, sources[]) —
    the MM's pet-directed +damage AND +ToHit as FRACTIONS, uptime-weighted,
    game-first per the routing lever above. v38 adds the ToHit half the v34
    always-hit simplification deferred: Supremacy's own template carries
    ToHit 0.1 beside its DamageBuffs, Tactics-class auras project, and a
    self_effects-only ToHit (Focused Accuracy) stays caster-only by the same
    lever. Returns zeros for any build with no pet-directed buffs (negative
    control: a non-MM, or an MM with only caster-only buffs, reads exactly 0)."""
    power_by_full = ctx.get("power_by_full") or {}
    mod_tables = ctx.get("modifier_tables") or {}
    mult_ed = ctx.get("mult_ed")
    col = ctx.get("at_column")
    if col is None or col < 0:
        return 0.0, 0.0, 0.0, 0.0, []
    all_mult = top_mult = 0.0
    tohit_all = tohit_top = 0.0
    sources = []
    for power in build.get("powers", []):
        rec = power_by_full.get(power.get("full_name"))
        if not rec:
            continue
        dbs = [d for d in (rec.get("buff_effects") or [])
               if d.get("effect") in ("DamageBuff", "ToHit")
               and d.get("pv_mode") != 2]
        if not dbs:
            continue
        # single-target ally buff (Temporal Selection: radius 0, not an aura) ->
        # the top-DPS pet only; PBAoE/aura buffs -> every pet.
        single = ((rec.get("radius") or 0) == 0
                  and (rec.get("activate_period") or 0) == 0)
        label = rec.get("display_name") or power.get("full_name")
        base_rech = rec.get("base_recharge") or 0.0
        is_click = ((rec.get("power_type") or 0) == 0
                    and (rec.get("activate_period") or 0) == 0)
        rech_boost = None                   # computed once, only if needed
        # one value per EFFECT (typed spread -> first row of each kind)
        for eff_kind in ("DamageBuff", "ToHit"):
            rows = [d for d in dbs if d.get("effect") == eff_kind]
            if not rows:
                continue
            d = rows[0]
            row = mod_tables.get(d.get("modifier_table"))
            if not row or col >= len(row):
                continue
            prob = min(max(d.get("probability") or 1.0, 0.0), 1.0)
            mag = abs((d.get("scale") or 0.0) * (d.get("nmag") or 1.0)
                      * row[col] * prob)
            # uptime: click buffs by duration / enhanced recharge; auras 1.0
            dur = d.get("duration") or 0.0
            uptime = 1.0
            if is_click and base_rech > 0 and dur > 0:
                if rech_boost is None:
                    rech_enh = 0.0
                    for slot in power.get("slots", []) or []:
                        if slot and slot.get("piece_uid"):
                            for asp, val in _scaled_boosts(slot, ctx):
                                if asp == "Recharge":
                                    rech_enh += val
                    rech_boost = apply_ed_sched(ED_SCHEDULE.get("Recharge", 0),
                                                rech_enh, mult_ed)
                enh_rech = base_rech / (1.0 + global_rech + rech_boost)
                uptime = min(1.0, dur / enh_rech) if enh_rech > 0 else 1.0
            val = mag * uptime
            if val <= 0:
                continue
            scope = "top pet" if single else "all pets"
            sources.append({"name": label, "pct": round(val * 100, 1),
                            "scope": scope, "uptime": round(uptime, 2),
                            "effect": "tohit" if eff_kind == "ToHit" else "damage"})
            if eff_kind == "ToHit":
                if single:
                    tohit_top += val
                else:
                    tohit_all += val
            elif single:
                top_mult += val
            else:
                all_mult += val
    # incarnate Assault HYBRID *Radial* (team/pet); Core / Musculature-Alpha excluded
    for s in (totals.get("damage_buff_sources") or []):
        if s.get("slot") == "Hybrid" and "Radial" in (s.get("name") or ""):
            v = s.get("value") or 0.0
            if v > 0:
                all_mult += v
                sources.append({"name": s.get("name"), "pct": round(v * 100, 1),
                                "scope": "all pets", "uptime": 1.0,
                                "effect": "damage"})
    # Pack Mentality (Beast Mastery charge mechanic; empty effects -> priced by rule)
    if any((p.get("full_name") or "") == _PACK_MENTALITY_FN
           for p in build.get("powers", [])):
        v = _PACK_MENTALITY_STACKS * _PACK_MENTALITY_PER_STACK
        all_mult += v
        sources.append({"name": "Pack Mentality", "pct": round(v * 100, 1),
                        "scope": "Beast pets", "effect": "damage",
                        "note": f"assumes {_PACK_MENTALITY_STACKS} of 10 stacks "
                                f"with pets engaged"})
    return all_mult, top_mult, tohit_all, tohit_top, sources


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
        # copies boosts), Recharge shortens the resummon cycle for timed pets.
        # v38: Accuracy rides the same copy_boosts path — the pet-set Acc pieces
        # (Blood Mandate Acc/Dam...) enhance the pets' own attacks.
        dmg_enh = rech_enh = acc_enh = 0.0
        for slot in power.get("slots", []) or []:
            if slot and slot.get("piece_uid"):
                for asp, val in _scaled_boosts(slot, ctx):
                    if asp == "Damage":
                        dmg_enh += val
                    elif asp == "Recharge":
                        rech_enh += val
                    elif asp == "Accuracy":
                        acc_enh += val
        dmg_boost = apply_ed_sched(ED_SCHEDULE.get("Damage", 0), dmg_enh, mult_ed)
        acc_boost = apply_ed_sched(ED_SCHEDULE.get("Accuracy", 0), acc_enh, mult_ed)
        spec = specs.get(p.get("full_name"))
        if spec is not None and not spec.get("copy_boosts", True):
            dmg_boost = 0.0                  # the game does not copy slotting to these
            acc_boost = 0.0
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
            acc_w = 0.0
            for ps_full in ent.get("powerset_full_names", []):
                seen_ps.add(ps_full)
                d, n, a = _pet_damage_for_powerset(ps_full, ctx, pet_col,
                                                   dmg_boost, pvp)
                dps += d
                natk += n
                acc_w += d * a               # dps-weighted inherent accuracy
            if natk == 0 or dps <= 0:    # support/heal pets have no damage
                continue
            count = max(1, int(se.get("count") or 1))
            pcls = se.get("class") or ent.get("class_name")
            pets.append({"name": ent.get("display_name") or uid,
                         "from_power": p.get("display_name"),
                         # v29: the pet's game class + the summon's real cast time
                         # ride along so the scorer's henchman-inheritance term can
                         # key tier HP and the resummon downtime off them.
                         "pet_class": pcls,
                         "resummon_cast": round(p.get("cast_time") or 0.0, 2),
                         # v38 pet hit-chance ledger (docs/pet-tohit-sources.md):
                         # level_shift = henchman tier rule by CLASS (wiki-
                         # sourced: T1 −2 / T2 −1 / T3 −0 at full count) else
                         # the summon template's own client level shell
                         # (patch_summon_level_shift). acc_mult = the attacks'
                         # inherent accuracy × summon-slotted Accuracy (ED,
                         # copy_boosts-gated).
                         "level_shift": _HENCH_TIER_SHIFT.get(
                             pcls, (spec or {}).get("level_shift") or 0),
                         "acc_mult": round((acc_w / dps) * (1.0 + acc_boost), 3),
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
            d, n, a = _pet_damage_for_powerset(ps_full, ctx, pet_min_col,
                                               dmg_boost, pvp)
            if n and d > 0:
                pets.append({"name": ps_full.split(".")[-1].replace("_", " "),
                             "from_power": p.get("display_name"),
                             "level_shift": (spec or {}).get("level_shift") or 0,
                             "acc_mult": round(a * (1.0 + acc_boost), 3),
                             "dps_each": round(d, 1), "attack_count": n,
                             "count": 1, "uptime": round(uptime, 2),
                             "dps_total": round(d * uptime, 1)})
    if not pets:
        return {}
    pets.sort(key=lambda x: x["dps_total"], reverse=True)
    # #13: apply the MM's pet-directed damage buffs. all_mult is uniform (does not
    # reorder), so the pre-buff top pet is still the top pet -> Temporal Selection's
    # single-target bonus lands on pets[0]. v38: the ToHit halves are CARRIED,
    # not applied — hit chance is scenario physics, the scorer owns it.
    all_mult, top_mult, tohit_all, tohit_top, buff_sources = _pet_damage_buff(
        build, totals, ctx, global_rech)
    if all_mult or top_mult:
        for i, pt in enumerate(pets):
            m = 1.0 + all_mult + (top_mult if i == 0 else 0.0)
            pt["dps_each"] = round(pt["dps_each"] * m, 1)
            pt["dps_total"] = round(pt["dps_total"] * m, 1)
        pets.sort(key=lambda x: x["dps_total"], reverse=True)
    out = {"pets": pets,
           "total_each": round(sum(p["dps_each"] for p in pets), 1),
           "total_squad": round(sum(p["dps_total"] for p in pets), 1)}
    if buff_sources:
        out["damage_buff_sources"] = buff_sources
        out["damage_buff_all_pct"] = round(all_mult * 100, 1)
        out["damage_buff_top_pct"] = round(top_mult * 100, 1)
    if tohit_all or tohit_top:
        out["tohit_buff_all_pct"] = round(tohit_all * 100, 1)
        out["tohit_buff_top_pct"] = round(tohit_top * 100, 1)
    return out


# ── WHAT A SLOTTED ENHANCEMENT ACTUALLY DOES TO A BUFF/DEBUFF ────────────────
# The game's model, read out of the client: a boost grants STRENGTH to an
# ATTRIBUTE, and that strength scales every effect of that attribute the power
# has - the target of the effect does not enter into it. Our engine already
# works this way for damage, and the Envenom fix verified it for -Defence.
# Effect names and aspect names are the same client vocabulary, so the match is
# by name, and whether a power may hold a given enhancement at all is answered
# by its own slots (it can only accept what the game lets it accept).
#
# ⚠ RECHARGE IS CREDITED, and the client is why (Joel, 2026-08-06: "lets give
# recharge its accreditation"). I had excluded it on a guess that -recharge
# rides Slow enhancements. The client disproves that guess AND answers the
# question properly:
#   Crafted_Curtail_Speed_A (a Slow IO) enhances ['RunningSpeed','FlyingSpeed',
#     'JumpingSpeed'] + Accuracy - NO RechargeTime. So Slow is not the route.
#   Neurotoxic Breath's -recharge is attribs ['RechargeTime'], aspect Strength,
#     target AnyAffected, and its boosts_allowed includes 'Recharge'.
#   Speed Boost and Accelerate Metabolism carry the same RechargeTime/Strength
#     template pointed at allies, and both allow 'Recharge' too.
# So a Recharge enhancement scales a power's recharge effects in BOTH
# directions, exactly as a Damage enhancement scales its damage.
#
_ENH_BY_NAME = {"Defense", "ToHit", "Heal", "Absorb", "Slow", "Endurance",
                "Recovery", "Regeneration", "HitPoints", "Resistance",
                "RechargeTime"}
# The three exclusions are enforced by the GAME's own allow-lists first — a
# power cannot hold the piece that would enhance them, so the multiplier is
# already 1.0 by construction. They are named anyway as a direction guard, the
# mirror of the HO solver's "DeBuff pieces' Defense aspect never credits armor".
# Evidence, straight from the client's boosts_allowed:
#   Envenom (−res, −regen): EnduranceDiscount, Range, Recharge, Debuff_Defense,
#     Accuracy — nothing that grants Resistance or Regeneration strength.
#   Weaken (−damage): EnduranceDiscount, Range, Recharge, Debuff_ToHit, Accuracy.
#   Assault (+damage): Incarnate_Lore, EnduranceDiscount, Recharge.
_ENH_NEVER = {("Resistance", "debuff"),      # no boost there grants Resistance
              ("Regeneration", "debuff"),    # no boost there grants Regeneration
              ("DamageBuff", "debuff"), ("DamageBuff", "buff")}


def _row_enh(power, ctx):
    """{aspect: post-ED fraction} from this power's OWN slotting — the same
    primitives _offense prices damage with, so there is one ED implementation."""
    tot = defaultdict(float)
    for slot in power.get("slots") or []:
        if not slot or not slot.get("piece_uid"):
            continue
        for asp, val in _scaled_boosts(slot, ctx):
            tot[asp] += val
    mult_ed = ctx.get("mult_ed")
    return {a: apply_ed_sched(ED_SCHEDULE.get(a, 0), v, mult_ed) for a, v in tot.items()}


def _enh_mult(effect, side, enh):
    """How much this power's slotting multiplies one buff/debuff row."""
    if effect not in _ENH_BY_NAME or (effect, side) in _ENH_NEVER:
        return 1.0
    return 1.0 + (enh.get(effect) or 0.0)


def _debuff_buff_summary(build, ctx):
    """Aggregate the build's enemy DEBUFFS and ally/self BUFFS as resolved
    magnitudes for ONE application, WITH the host power's own enhancement
    (Joel, 2026-08-06: "fix the buff/debuff panel so it reads enhancement" — a
    debuffer slotting accurate defence-debuff sets used to see nothing move
    anywhere in the app). Uptime is deliberately NOT folded in: this panel says
    what one application does, and the sustained/uptime-weighted view is the
    scorer's (role_output.enhanced_debuff_totals), which is untouched.
    Returns (debuffs, buffs) lists of {effect, type, pct}."""
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
    # provenance (Stats page): which POWERS make each row — {key: {power: mag}}
    dsrc = defaultdict(lambda: defaultdict(float))
    bsrc = defaultdict(lambda: defaultdict(float))
    # POINT-VALUED effects must never be formatted "×100 %" (Joel's field
    # find, 2026-07-28: a ~943-HP heal total printed as "+94303.2%"). The
    # unit lives in the EFFECT, not the modifier table: Heal/Absorb are
    # always hit points (counterexample that killed the table-suffix rule:
    # Rejuvenating_Circuit stores 165.99 HP as scale on Ranged_Ones), and
    # Endurance effects are points of the 100-end bar.
    hp_keys = set()
    end_keys = set()
    _POINT_HP = ("Heal", "Absorb", "HitPoints")
    for power in build.get("powers", []):
        p = power_by_full.get(power.get("full_name"))
        if not p:
            continue
        enh = _row_enh(power, ctx)
        for d in p.get("debuff_effects", []):
            if not _pv_ok(d.get("pv_mode", 0), pvp):
                continue
            if d.get("target") == "Self":
                continue   # caster-only (client-verified target back-fill)
            row = mod_tables.get(d["modifier_table"])
            if row and col < len(row):
                key = (d["effect"], d["damage_type"])
                if d["effect"] in _POINT_HP:
                    hp_keys.add(key)
                elif d["effect"] == "Endurance":
                    end_keys.add(key)
                _mag = _resolve_mag(d, row, col) * _enh_mult(d["effect"], "debuff", enh)
                deb[key] += _mag
                dsrc[key][p.get("display_name")
                          or power.get("full_name")] += _mag
        for d in p.get("buff_effects", []):
            if not _pv_ok(d.get("pv_mode", 0), pvp):
                continue
            if d.get("target") == "Self":
                continue   # caster-only (client-verified target back-fill)
            row = mod_tables.get(d["modifier_table"])
            if row and col < len(row):
                key = (d["effect"], d["damage_type"])
                if d["effect"] in _POINT_HP:
                    hp_keys.add(key)
                elif d["effect"] == "Endurance":
                    end_keys.add(key)
                _mag = _resolve_mag(d, row, col) * _enh_mult(d["effect"], "buff", enh)
                buf[key] += _mag
                bsrc[key][p.get("display_name")
                          or power.get("full_name")] += _mag

    def fmt(agg, srcmap):
        # Collapse an effect that spans the whole elemental spread with one equal
        # value (e.g. -Damage to all types) into a single "(all)" row.
        by_effect = defaultdict(dict)
        for (et, dt), v in agg.items():
            by_effect[et][dt] = v
        def _sources(et, dt, point):
            # per-power contributors, in the ROW's unit (points vs percent)
            m = srcmap.get((et, dt)) or {}
            rows = [{"name": n, "v": round(x if point else x * 100, 1)}
                    for n, x in m.items() if abs(x) >= 1e-4]
            rows.sort(key=lambda r: -abs(r["v"]))
            return rows

        out = []
        for et, by_dt in by_effect.items():
            label = "Damage" if et == "DamageBuff" else et
            vals = list(by_dt.values())
            spread = len(by_dt) >= len(RESISTANCE_TYPES) and max(vals) - min(vals) < 1e-4
            if spread:
                v = vals[0]
                if abs(v) >= 1e-4:
                    dt0 = next(iter(by_dt))
                    out.append({"effect": label, "type": "all", "pct": round(v * 100, 1),
                                "sources": _sources(et, dt0, False)})
                continue
            for dt, v in by_dt.items():
                if abs(v) < 1e-4:
                    continue
                if (et, dt) in hp_keys:
                    # hit points, one application of each contributing power
                    out.append({"effect": label, "type": dt if dt != "None" else None,
                                "hp": round(v, 1), "sources": _sources(et, dt, True)})
                elif (et, dt) in end_keys:
                    out.append({"effect": label, "type": dt if dt != "None" else None,
                                "end": round(v, 1), "sources": _sources(et, dt, True)})
                else:
                    out.append({"effect": label, "type": dt if dt != "None" else None,
                                "pct": round(v * 100, 1), "sources": _sources(et, dt, False)})
        out.sort(key=lambda r: abs(r.get("pct") if r.get("pct") is not None
                                   else r.get("hp") if r.get("hp") is not None
                                   else r.get("end", 0)), reverse=True)
        return out
    return fmt(deb, dsrc), fmt(buf, bsrc)


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
    # Stats provenance: the opt-in attribution ledger (see _attr_flush). The
    # per-piece detail lives in _power_totals / _piece_globals / the set-bonus
    # loop; incarnates/amplifiers/accolades attribute as one row per layer.
    attr = [] if (ctx or {}).get("attribution") else None
    if ctx is not None:                 # per-build character level for IO scaling
        ctx = dict(ctx)
        ctx["char_level"] = build.get("char_level") or 50
        ctx["_attr"] = attr
    amp_preview = _power_totals(build, totals, ctx)
    _snap = _tsnap(totals) if attr is not None else None
    _incarnate_totals(build, totals, ctx)
    _attr_flush(attr, {"kind": "incarnates", "name": "Incarnates (peak)"}, totals, _snap)
    _piece_globals(build, totals, ctx)      # attributes per slot internally
    _snap = _tsnap(totals) if attr is not None else None
    _amplifier_buffs(build, totals)
    _attr_flush(attr, {"kind": "amplifiers", "name": "Amplifiers (buyable)"}, totals, _snap)
    _snap = _tsnap(totals) if attr is not None else None
    _accolade_buffs(build, totals, ctx)
    _attr_flush(attr, {"kind": "accolades", "name": "Accolades"}, totals, _snap)
    bonus_signature_count = defaultdict(int)
    applied_bonuses = []        # for display / AI context
    capped_out = []
    # v29: TRUE-set-bonus-only subtotals — what MM henchmen inherit at 50%
    # (bins-verified 2026-07-08: Henchmen-tagged effect groups exist ONLY on
    # Set_Bonus.Set_Bonus.* powers; piece globals — Unbreakable Guard, LotG —
    # and accolades have none). Accumulated INSIDE this loop so the exclusion
    # is structural: _piece_globals/_external_buffs never touch it.
    sb_only = _empty_totals()

    ex = (ctx or {}).get("exemplar")
    for power in build.get("powers", []):
        # DISTINCT pieces per set, not slots: a duplicated set piece (an
        # in-game-impossible state validation errors on) must not conjure the
        # next bonus tier — the game grants tiers by distinct pieces.
        # ⚠ Exemplar view gates PER PIECE here — and deliberately NOT on
        # _exemplar_off: the game keeps a lost host power's set bonuses alive
        # as long as each enhancement's own level rule passes (wiki-pinned).
        set_counts = defaultdict(set)
        for slot in power.get("slots", []) or []:
            if slot and slot.get("set_uid") and _exemplar_bonus_alive(slot, ex):
                set_counts[slot["set_uid"]].add(
                    slot.get("piece_uid") or slot.get("piece_name") or id(slot))
        set_counts = {uid: len(pieces) for uid, pieces in set_counts.items()}

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
                _snap = _tsnap(totals) if attr is not None else None
                for eff in bonus.get("effects", []):
                    if eff.get("effect") == "HitPoints":
                        # GAME-VERIFIED unit fix: a HitPoints set-bonus value is a
                        # Melee_HealSelf SCALE, not a fraction (Set_Bonus.*.Increased_
                        # Health_* → scale × Melee_HealSelf table = FLAT hit points;
                        # the table is ~base_hp/10 per AT, so 'Large' 0.1875 = ~1.88%
                        # of base HP). Adding it raw inflated every HP bonus ~10x.
                        eff = dict(eff, value=hp_bonus_fraction(
                            eff.get("value", 0.0), ctx))
                    _apply_effect(totals, eff)
                    _apply_effect(sb_only, eff)
                _attr_flush(attr, {"kind": "set_bonus",
                                   "power": power.get("full_name"),
                                   "name": power.get("display_name")
                                   or (power.get("full_name") or "").split(".")[-1],
                                   "set": sb.get("name"), "set_uid": set_uid,
                                   "pieces": bonus.get("pieces_required")},
                            totals, _snap)

    # FORCE FEEDBACK average recharge (v27): a slotted "Chance for +Recharge" in a cycled
    # attack sustains a real average global-recharge uplift — chance/roll = PPM × (base
    # recharge + cast) / 60 (local recharge divides it; FF hosts carry none), value =
    # chance × 5s ÷ the attack's actual cycle at the build's global recharge. Multiple
    # copies don't stack the buff, they add uptime — capped well short of permanent.
    ff = _ff_recharge_avg(build, totals, ctx)
    if ff:
        totals["recharge"] += ff
        if attr is not None:
            attr.append({"kind": "proc", "name": "Force Feedback +Recharge (average)",
                         "effects": {"recharge": round(ff, 6)}})

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
    # v34 #4 (attribution, not buried numbers): surface which accolades landed
    # in the HP number, so the display can print "Accolades +321" and name them.
    if totals.get("_accolade_ledger"):
        display["accolade_ledger"] = totals["_accolade_ledger"]
        display["accolade_hp"] = round(sum(x["hp"] for x in totals["_accolade_ledger"]), 1)
    # v34 #4 (the Musculature case, Joel's template): the global +damage% an
    # Alpha/Hybrid grants is applied to every attack by _offense — but it was
    # never EXPOSED, so the DPS block could not name where the damage came from.
    # A number that reaches the math and not the screen is exactly the gap this
    # deliverable exists to close.
    if totals.get("damage_buff"):
        display["damage_buff"] = round(totals["damage_buff"], 4)
        # the named contributors, so the attribution line credits every source
        # (Alpha + Hybrid), never a single assumed one (Joel's no-guess rule).
        if totals.get("damage_buff_sources"):
            display["damage_buff_sources"] = totals["damage_buff_sources"]
    if totals.get("max_end"):
        display["max_end_bonus"] = round(totals["max_end"], 1)
    # v29: what MM henchmen inherit (50% of TRUE set bonuses only) — the scorer's
    # henchman-survivability term reads this. Percent units, same as the display.
    display["set_bonus_totals"] = {
        "defense": {t: round(v * 100.0, 2) for t, v in sb_only["defense"].items()},
        "resistance": {t: round(v * 100.0, 2) for t, v in sb_only["resistance"].items()},
        "max_hp": round(sb_only["max_hp"] * 100.0, 2),
        "regeneration": round(sb_only["regeneration"] * 100.0, 2),
        "recovery": round(sb_only["recovery"] * 100.0, 2),
        "heal_strength": round(sb_only["heal_strength"] * 100.0, 2),
    }
    if ff:
        # transparency: how much of the global recharge FF is carrying (shown in %)
        display["ff_recharge_avg"] = round(ff * 100.0, 1)
    if amp_preview:
        # Honesty note for the amplifier preview: name the source, the factor,
        # and the window — burst numbers must read as burst, never sustained.
        display["strength_preview"] = amp_preview
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
    if attr is not None:
        display["attribution"] = attr
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
            if pets.get("damage_buff_sources"):
                offense["pet_damage_buff_sources"] = pets["damage_buff_sources"]
                offense["pet_damage_buff_all_pct"] = pets.get("damage_buff_all_pct")
                offense["pet_damage_buff_top_pct"] = pets.get("damage_buff_top_pct")
            # v38: pet-directed ToHit (Supremacy/Tactics-class) — the scorer's
            # pet hit chance consumes these; display names them with the rest.
            if pets.get("tohit_buff_all_pct") or pets.get("tohit_buff_top_pct"):
                offense["pet_tohit_all_pct"] = pets.get("tohit_buff_all_pct") or 0.0
                offense["pet_tohit_top_pct"] = pets.get("tohit_buff_top_pct") or 0.0
        display["offense"] = offense
    display["endurance"] = _endurance_balance(build, display, offense, ctx)
    return display


# Base endurance recovery ≈ 1.667 end/sec at 100 max endurance (Homecoming); +Recovery scales
# it. A toggle drains end_cost / activate_period per second; a sustained attack chain drains
# offense.chain_end_per_sec. Net = recovery − (toggles + chain).
# v35 travel split (Q3 ruling 2026-07-21, the Nimbus gap): sprint/prestige/rest stay excluded
# (nobody fights in Rest), but Fly/Hover-class TRAVEL toggles are TALLIED SEPARATELY and
# always DISPLAYED — a combat-hover playstyle really does pay that drain in the fight. The
# scorer includes them when the build's declared fighting range is ranged ("back"); the
# displayed ledger never silently drops them again.
_END_BASE_RECOVERY = 1.667
_END_SKIP_TOGGLES = ("sprint", "prestige", "rest")
_END_TRAVEL_TOGGLES = ("fly", "hover", "mystic_flight")
# Measured end/s per slotted copy (tools/measure_end_procs.py — see PIECE_GLOBALS note);
# used here only to STATE the credit already inside the recovery% total.
_END_PROC_EPS = {"performance shifter": 0.529, "panacea": 0.398, "theft of essence": 0.25}


def _endurance_balance(build, display, offense, ctx):
    """Real endurance math (uses end_cost + activate_period): can the build SUSTAIN its rotation,
    or does it need a refuel? Returns recovery/sec vs drain/sec (toggles + nonstop chain) → net,
    plus the v35 fight-duration inputs (travel split, E_max pool, stated end-proc credit)."""
    power_by_full = ctx.get("power_by_full", {})
    toggle = travel = 0.0
    for power in build.get("powers", []):
        p = power_by_full.get(power.get("full_name"))
        if not p or p.get("power_type") != 2:
            continue
        # Honor the per-power totals checkbox: an unchecked toggle (a mule host you
        # never run, or a what-if "Weave off" check) doesn't drain endurance either.
        include = power.get("include_in_totals")
        if include is None:
            include = p.get("power_type") in ACTIVE_POWER_TYPES
        if not include:
            continue
        ap = p.get("activate_period") or 0
        nm = (p.get("full_name") or "").split(".")[-1].lower()
        if ap <= 0 or any(s in nm for s in _END_SKIP_TOGGLES):
            continue
        if any(s in nm for s in _END_TRAVEL_TOGGLES):
            travel += (p.get("end_cost") or 0.0) / ap
        else:
            toggle += (p.get("end_cost") or 0.0) / ap
    chain = (offense or {}).get("chain_end_per_sec", 0.0)
    rec_pct = (display.get("recovery") or {}).get("value", 0.0) / 100.0
    recovery = _END_BASE_RECOVERY * (1.0 + rec_pct)
    drain = chain + toggle
    # E_max: 100 base + flat MaxEnd (accolades + the v35-credited set bonuses).
    pool = 100.0 + (display.get("max_end_bonus") or 0.0)
    # Stated end-proc credit (already inside recovery% via PIECE_GLOBALS — this
    # field only makes the assumption VISIBLE, it is not added again).
    seen_unique, eps = set(), 0.0
    for power in build.get("powers", []):
        for slot in power.get("slots", []) or []:
            if not slot:
                continue
            sn, pn = (slot.get("set_name") or "").lower(), (slot.get("piece_name") or "").lower()
            for key, val in _END_PROC_EPS.items():
                if key in sn and ("+end" in pn or "hit points" in pn or "+endurance" in pn):
                    if key == "panacea":
                        if key in seen_unique:
                            break
                        seen_unique.add(key)
                    eps += val
                    break
    # Declared fighting range decides whether travel drain joins the SCORED fight
    # (Q3: ranged/hover = yes, melee = no); the display shows it regardless.
    travel_declared = (build.get("_exposure") or build.get("exposure")) == "back"
    out = {"recovery_per_sec": round(recovery, 2), "toggle_drain_per_sec": round(toggle, 2),
           "chain_drain_per_sec": round(chain, 2), "drain_per_sec": round(drain, 2),
           "net_per_sec": round(recovery - drain, 2), "sustainable": (recovery - drain) >= 0,
           "max_end_pool": round(pool, 1)}
    if travel > 0:
        out["travel_toggle_drain_per_sec"] = round(travel, 2)
        out["drain_with_travel_per_sec"] = round(drain + travel, 2)
        out["net_with_travel_per_sec"] = round(recovery - drain - travel, 2)
    out["travel_in_combat"] = bool(travel_declared and travel > 0)
    if eps > 0:
        out["end_proc_per_sec"] = round(eps, 2)
    # Stated assumptions (choice doctrine: nothing silent on a safety-relevant line).
    assumes = []
    if eps > 0:
        assumes.append("end procs credited at their measured average (chatlog-verified)")
    if display.get("incarnates_included"):
        assumes.append("incarnate buffs included (your toggle) — recovery is NOT bare")
    if out["travel_in_combat"]:
        assumes.append("travel toggle drain counted in-combat (you fight from range)")
    if assumes:
        out["assumes"] = assumes
    if recovery - drain < -0.05:                  # seconds of nonstop attacking before empty
        out["empty_after_sec"] = round(pool / (drain - recovery))
    return out


def hp_bonus_fraction(val, ctx):
    """Convert a HitPoints SET-BONUS value to a fraction of the AT's base HP.
    GAME-VERIFIED (Set_Bonus.*.Increased_Health_* powers): the stored value is a
    Melee_HealSelf SCALE — flat HP = value × Melee_HealSelf[AT@50], and that table
    is ~base_hp/10 for every AT (Brute deliberately a touch higher). So 'Large'
    0.1875 = ~1.88% of base HP, never 18.75%. Fallback ×0.1 when ctx is missing."""
    try:
        hs = (ctx or {}).get("modifier_tables", {}).get("Melee_HealSelf")
        col = (ctx or {}).get("at_column")
        base = (ctx or {}).get("at_base_hp")
        if hs and col is not None and 0 <= col < len(hs) and base:
            return val * hs[col] / base
    except Exception:  # noqa: BLE001
        diag.swallowed("engine: AT hp-column scaling", "falling back to val*0.1")
    return val * 0.1


# ── ATTRIBUTION LEDGER (Stats provenance, Joel's spec 2026-08-03) ────────────
# Where every number comes from, captured by DIFFING totals around each apply —
# one copy of the mapping (the apply functions themselves), so attribution can
# never drift from the math. OPT-IN via ctx["attribution"] (set only by
# /build/calculate): scoring hot paths pay nothing.
def _tsnap(totals):
    out = {}
    for k, v in totals.items():
        if isinstance(v, dict):
            for t, x in v.items():
                if isinstance(x, (int, float)):
                    out[f"{k}:{t}"] = x
        elif isinstance(v, (int, float)):
            out[k] = v
    return out


def _attr_flush(ledger, src, totals, before):
    """Append {**src, effects: {stat: delta}} for whatever changed since
    `before`. No-op when the ledger is off or nothing moved."""
    if ledger is None or before is None:
        return
    after = _tsnap(totals)
    deltas = {}
    for k, v in after.items():
        d = v - before.get(k, 0.0)
        if abs(d) > 1e-12:
            deltas[k] = round(d, 6)
    if deltas:
        row = dict(src)
        row["effects"] = deltas
        ledger.append(row)


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
        # v30: aspect disambiguates — 'Res' is the recharge component of a SLOW
        # RESIST bonus (Winter sets etc.), never a +recharge buff. Without this
        # branch the back-filled records would pollute the recharge total.
        if eff.get("aspect") == "Res":
            totals["slow_resist"] += val
        else:
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
    elif et == "Heal":
        # v29: heal STRENGTH (Numina 4pc +6% etc.) — multiplies the healing the
        # build's own heal powers put out; unrelated to +HP or +Regeneration.
        totals["heal_strength"] += val
    # v30: the back-filled families. Multi-attrib records were expanded with
    # equal values, so one canonical attrib counts and its mirrors are skipped
    # (SpeedFlying/SpeedJumping/JumpHeight mirror SpeedRunning; Knockup mirrors
    # Knockback) — adding them all would double/quadruple-count one bonus.
    elif et == "Knockback":
        if eff.get("aspect") == "Cur":
            totals["kb_protection"] += -val    # −3.0 Current = mag 3 protection
        else:
            totals["kb_strength"] += val
    elif et == "SpeedRunning":
        if eff.get("aspect") == "Cur":
            totals["movement"] += val
        elif eff.get("aspect") == "Str":
            totals["slow_strength"] += val
        # 'Res' mirror: the slow-resist total is counted on RechargeTime above
    elif et == "Range":
        totals["range"] += val
    elif et == "EnduranceDiscount":
        totals["end_discount"] += val
    elif et == "Endurance":
        # v35: +MaxEnd set bonuses (aspect Max, values already flat-on-base-100:
        # 1.8 = +1.8 points). 40 records existed in the data and were silently
        # dropped here — the same allowlist-gap family as the v28 accuracy and
        # v29 heal-strength finds. Feeds E_max in the fight-duration ledger.
        if eff.get("aspect") == "Max":
            totals["max_end"] = totals.get("max_end", 0.0) + val
    elif et in MEZ_DURATION_EFFECTS:
        totals["mez_duration"][et] += val


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
        "heal_strength": {"value": pct(totals.get("heal_strength", 0.0)),
                          "label": "+% Heal strength"},
        # v30: the back-filled bonus families. kb_protection is protection
        # POINTS (mag), everything else a percent. The frontend shows only
        # nonzero rows, so builds without these bonuses stay uncluttered.
        "bonus_extras": {
            "kb_protection": {"value": round(totals.get("kb_protection", 0.0), 1),
                              "label": "Knockback protection (mag)"},
            "mez_protection": {"value": round(min(totals["mez_protection"].values())
                                              if totals.get("mez_protection") else 0.0, 1),
                               "label": "Mez protection (lowest type)"},
            "slow_resist": {"value": pct(totals.get("slow_resist", 0.0)),
                            "label": "Slow resistance (recharge + movement)"},
            "def_debuff_resist": {
                "value": pct(totals.get("def_debuff_resist", 0.0)),
                "label": "Defence debuff resistance"},
            "mez_duration": {m: pct(v) for m, v in
                             (totals.get("mez_duration") or {}).items() if v},
            "movement": {"value": pct(totals.get("movement", 0.0)),
                         "label": "+% Movement speed"},
            "range": {"value": pct(totals.get("range", 0.0)),
                      "label": "+% Range"},
            "end_discount": {"value": pct(totals.get("end_discount", 0.0)),
                             "label": "+% Endurance discount"},
            "slow_strength": {"value": pct(totals.get("slow_strength", 0.0)),
                              "label": "+% Slow strength"},
            "kb_strength": {"value": pct(totals.get("kb_strength", 0.0)),
                            "label": "+% Knockback strength"},
        },
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
