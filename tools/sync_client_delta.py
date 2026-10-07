"""Apply a game patch to data/powers.json BY DIFFERENCE, from two client exports.

Issue 28 Page 4 (2026-10-06) reworked Super Strength, Empathy, Force Field, Traps,
Sonic Resonance and ~140 smaller powers. Our records carry layers no client field
holds (suppression, modes, crash penalties, DDR rows, prereq counts, icons...), so
re-parsing a power from the client would erase them (CLAUDE.md: never re-parse).

This tool reads BOTH client exports - the one our data already matches (BEFORE) and
the patched one (AFTER) - through one converter, and applies only the difference:

  row removed by the patch  -> the matching row of ours is removed
  row added by the patch    -> added; when it replaces a removed row of the same
                               effect/damage type/table/side, it INHERITS that row's
                               layered fields (Rage's damage rows keep mode/stack/flags)
  scalar changed            -> applied only if BEFORE equals our value

A row the converter reads from BEFORE that we do NOT hold means our record and the
converter disagree about that power. Its effects are then left untouched and the
power is REPORTED for review - never guessed. Calibration mode measures exactly that.

  python tools/sync_client_delta.py --calibrate      report agreement, write nothing
  python tools/sync_client_delta.py --check          dry run: what would change
  python tools/sync_client_delta.py --apply          write data/powers.json

Inputs: BEFORE/AFTER export roots (env P4_BEFORE / P4_AFTER, default the CoH-Planner
commits b66be4e7 / 5ecf6563 extracted under %TEMP%/p4diff), and
tools/gamedata/power_aliases.json (our name -> client name).
"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POWERS = os.path.join(ROOT, "data", "powers.json")
ALIASES = os.path.join(ROOT, "tools", "gamedata", "power_aliases.json")
_P4 = os.path.join(os.environ.get("TEMP", ""), "p4diff")
BEFORE = os.environ.get("P4_BEFORE") or os.path.join(_P4, "before", "exported_powers")
AFTER = os.environ.get("P4_AFTER") or os.path.join(_P4, "after", "exported_powers")

AREA = {"SingleTarget": 1, "Sphere": 2, "Cone": 3, "Location": 4, "Chain": 1, "Map": 6}
PTYPE = {"Click": 0, "Auto": 1, "Toggle": 2}
DMG = {"Smashing": "Smashing", "Lethal": "Lethal", "Fire": "Fire", "Cold": "Cold",
       "Energy": "Energy", "Negative_Energy": "Negative", "Psionic": "Psionic",
       "Toxic": "Toxic"}
POS = {"Melee": "Melee", "Ranged": "Ranged", "Area": "AoE"}
MEZ = {"Held", "Stunned", "Immobilized", "Confused", "Terrorized", "Sleep",
       "Knockback", "Knockup", "Repel", "Afraid", "Intangible"}
MEZ_KIND = {"Held": "hard", "Stunned": "hard", "Immobilized": "hard", "Confused": "hard",
            "Terrorized": "hard", "Intangible": "hard", "Knockback": "soft",
            "Knockup": "soft", "Sleep": "soft", "Repel": "soft", "Afraid": "soft"}
# attribs that carry no scored axis in our data (same dispositions as add_wind_control)
IGNORE = {"Create_Entity", "Grant_Power", "Revoke_Power", "Null", "Set_Mode",
          "Set_Costume", "Execute_Power", "Fly", "FlyingSpeed", "RunningSpeed",
          "JumpingSpeed", "JumpHeight", "SpeedRunning", "MovementControl",
          "MovementFriction", "Range", "Translucency", "StealthRadius_PVE",
          "StealthRadius_PVP", "PerceptionRadius", "ThreatLevel", "Global_Chance_Mod",
          "Ninja_Run", "Taunt", "Placate", "Teleport", "Recharge_Power", "Area",
          "Untouchable", "OnlyAffectsSelf", "Radius", "Meter", "Rage", "Unknown(105)",
          "Elusivity", "Accuracy", "Absorb_Overflow", "Reward", "XP_Debt",
          "Influence", "Cur_ToHit"}


import re  # noqa: E402
# The pure-targeting vocabulary, same census as tools/add_wind_control.py _TARGETING.
_TARGETING = re.compile("|".join((
    r"enttype\s+target>\s+(?:critter|player)\s+eq",
    r"entref\s+target\.owner>\s+entref\s+source>\s+eq",
    r"entref\s+target>\s+entref\s+source>\s+eq",
    r"target\.isFriend\?", r"source\.isFriend\?", r"target\.isPlayer\?",
    r"&&", r"\|\|", r"!",
)))
ALLY_MODELED = {"Defense", "DamageBuff", "Resistance", "Heal", "ToHit", "RechargeTime",
                "Recovery", "Regeneration", "HitPoints"}
SELF_MODELED = ALLY_MODELED | {"Absorb", "DefDebuffResist", "Endurance", "MezProtection",
                               "MezResist", "SlowResist"}


def _sec(v):
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v or 0).strip().split()[0])
    except (ValueError, IndexError):
        return 0.0


def _r(x):
    return round(float(x or 0.0), 4)


def load_redirects(root):
    """Homecoming LIVE redirect sub-powers (the targets of Execute_Power)."""
    out = {}
    for fp in glob.iglob(os.path.join(root, "redirects", "**", "*.json"), recursive=True):
        if os.path.basename(fp) == "index.json":
            continue
        try:
            d = json.load(open(fp, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if isinstance(d, dict) and d.get("full_name"):
            out[d["full_name"]] = d
    return out


def load_export(root):
    """HOMECOMING LIVE records only. ⚠ The export root also holds OTHER datasets
    under their own folders that reuse live full_names: `brainstorm/` (Homecoming's
    test server, beta values), `rebirth/` and `thunderspy/` (other private servers),
    and `redirects/` (conditional variants). Loading them overwrote live Rage with
    another server's Rage - the first calibration read 331 changed powers as
    unchanged because of it."""
    out = {}
    for fp in glob.iglob(os.path.join(root, "**", "*.json"), recursive=True):
        top = os.path.relpath(fp, root).replace("\\", "/").split("/", 1)[0]
        if os.path.basename(fp) == "index.json" or top in (
                "brainstorm", "rebirth", "thunderspy", "redirects"):
            continue
        try:
            d = json.load(open(fp, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if isinstance(d, dict) and d.get("full_name"):
            out[d["full_name"]] = d
    return out


def _req(e):
    r = e.get("requires_expression") or []
    return " ".join(map(str, r)) if isinstance(r, list) else str(r)


def _side(crec, t):
    """self / ally / foe. The POWER decides who it lands on (targets_affected);
    a template aimed at Self is self regardless."""
    if t.get("target") == "Self":
        return "self"
    aff = set(crec.get("targets_affected") or [])
    if aff and aff <= {"Self"}:
        return "self"
    if aff & {"Foe"}:
        return "foe"
    if aff:
        return "ally"
    return "self" if crec.get("target_type") == "Self" else "foe"


def convert(crec, resolve=None, _depth=0):
    """Client record -> {bucket: Counter(core-row tuples)} in OUR vocabulary.
    Unconditional groups only (a requires_expression that is more than an entity
    test is a mode/state gate the engine does not read - same rule as the importers).

    resolve (optional, {full_name: client record}): FOLLOW Execute_Power into the
    sub-powers it fires, each read with ITS OWN targeting, rows merged into this
    power. Page 4's Light Affinity delivers its AoE buffs, its -ToHit and Sonic
    Boom's damage this way (Protective Beam -> Redirects.Light_Affinity.
    Refracted_ProtectiveBeam = Def vs all, 25ft, 120s). Off by default so the
    patch sync stays byte-identical to its calibrated behaviour."""
    rows = defaultdict(Counter)
    unmapped = Counter()

    def _once_per_cast(sub):
        """A created entity's power that can fire at most ONCE per cast of this
        power - a click, or a period >= this power's recharge (Sonic Boom's pet:
        Auto, period 75 = Sonic Boom's 75s recharge). Its rows ARE this power's
        one-shot effect. A ticking aura (Prismatic Shield: 0.75s ticks for 45s)
        is not folded - its uptime would need the pet's lifetime modelled."""
        own = float(crec.get("recharge_time") or 0.0)
        per = float(sub.get("activate_period") or 0.0)
        return sub.get("type") == "Click" or (own > 0 and per >= own)

    def follow(t):
        if not resolve or _depth >= 3:
            return
        params = t.get("params") or {}
        if "Create_Entity" in (t.get("attribs") or []):
            for name in params.get("redirects") or []:
                sub = resolve.get(name)
                if sub is not None and _once_per_cast(sub):
                    srows, sun = convert(sub, resolve, _depth + 1)
                    for b, cnt in srows.items():
                        rows[b] += cnt
                    unmapped.update(sun)
                elif sub is not None and sub.get("targets_affected") != ["Self"]:
                    unmapped[f"entity aura not folded (ticks): {name}"] += 1
            return
        for name in (params.get("power_names") or []):
            sub = resolve.get(name)
            if sub is None or sub is crec:
                if sub is None:
                    unmapped[f"Execute_Power target not found: {name}"] += 1
                continue
            srows, sun = convert(sub, resolve, _depth + 1)
            for b, cnt in srows.items():
                rows[b] += cnt
            unmapped.update(sun)

    def take(t, pv, chance):
        attribs = t.get("attribs") or []
        asp, tbl = t.get("aspect"), t.get("table")
        sc, dur = _r(t.get("scale")), _r(_sec(t.get("duration")))
        per = float(t.get("application_period") or 0.0)
        if resolve is not None and per > 0 and dur > 0 and any(
                a in ("Heal", "Heal_Dmg") for a in attribs):
            # new-set mode: a heal-over-time arrives as its TOTAL (add_wind_control's
            # rule - a heal row carries no duration the engine reads; Equalization's
            # 15 ticks of 0.25 over 30s is 3.75, not 0.25)
            sc = _r(sc * max(1, int(dur / per)))
        side = _side(crec, t)
        for a in attribs:
            base = a[:-4] if a.endswith("_Dmg") else a
            if a in IGNORE or base in IGNORE:
                continue
            row = None
            if a.endswith("_Dmg") and base in DMG:
                dt = DMG[base]
                if asp in ("Absolute", "Current") and "Damage" in (tbl or "") and side == "foe":
                    row = ("damage_effects", "Damage", dt)
                elif asp == "Resistance":
                    row = ({"self": "self_effects", "ally": "buff_effects"}.get(side, "debuff_effects"),
                           "Resistance", dt)
                elif asp == "Strength":
                    row = ({"self": "self_effects", "ally": "buff_effects"}.get(side, "debuff_effects"),
                           "DamageBuff", dt)
            elif base in POS or base in DMG:
                if asp in ("Current", "Absolute"):
                    dt = POS.get(base) or DMG[base]
                    row = ({"self": "self_effects", "ally": "buff_effects"}.get(side, "debuff_effects"),
                           "Defense", dt)
                elif asp == "Resistance":
                    # positional defense resistance is DDR on our side
                    row = ("self_effects" if side == "self" else "buff_effects", "DefDebuffResist", "None")
            elif base in MEZ:
                if side == "foe" and asp in ("Current", "Magnitude", None):
                    rows["control_effects"][("control_effects", base, MEZ_KIND[base],
                                             sc, _r(t.get("magnitude") or 1.0), tbl, pv, dur,
                                             _r(chance))] += 1
                    continue
                if asp == "Current":
                    row = ("self_effects" if side == "self" else "buff_effects", "MezProtection", base)
                elif asp == "Resistance":
                    row = ("self_effects" if side == "self" else "buff_effects", "MezResist", base)
            elif base == "Base_Defense":
                row = ({"self": "self_effects", "ally": "buff_effects"}.get(side, "debuff_effects"),
                       "DefDebuffResist" if asp == "Resistance" else "Defense", "None")
            elif base in ("ToHit", "RechargeTime", "Recovery", "Regeneration", "Endurance",
                          "EnduranceDiscount", "HitPoints", "Absorb", "Heal"):
                eff = {"Heal": "Heal"}.get(base, base)
                if asp == "Resistance":
                    row = ("self_effects" if side == "self" else "buff_effects",
                           "SlowResist" if base == "RechargeTime" else f"{base}Resist", "None")
                else:
                    row = ({"self": "self_effects", "ally": "buff_effects"}.get(side, "debuff_effects"),
                           eff, "None")
            if row is None:
                unmapped[f"{a}/{asp}/{side}"] += 1
                continue
            # MIRROR OUR COVERAGE (measured over all 10,985 records): ally buffs are
            # only Defense/DamageBuff/Resistance/Heal/ToHit/RechargeTime/Recovery/
            # Regeneration/HitPoints; self effects never hold the resist-the-debuff
            # families beyond MezResist/SlowResist/DefDebuffResist. Anything else is
            # an axis the engine does not score - skipped, not "missing".
            if row[0] == "buff_effects" and row[1] not in ALLY_MODELED:
                continue
            if row[0] == "self_effects" and row[1] not in SELF_MODELED:
                continue
            if row[1] == "Heal":
                row = ("heal",) + row[1:]      # ours keeps heals in buff_effects OR heal_effects
            rows[row[0]][row + (sc, tbl, pv, dur, _r(chance))] += 1

    def walk(groups, pv_in, chance_in, gated_in):
        for g in groups or []:
            ip = g.get("is_pvp")
            if ip == "PVP_ONLY":
                continue                       # PvE scope
            pv = 1 if ip == "PVE_ONLY" else pv_in
            req = _req(g).strip()
            if "enttype target> player eq" in req and "!" not in req:
                continue
            if req == "0":
                continue                       # literal false: a disabled group
            if resolve is not None:
                # new-set mode: strip ALL pure-targeting clauses (add_wind_control's
                # census: 5,123 of 7,323 expression groups are targeting only) -
                # Sonic Boom's whole group is "target is me", not a game state
                gated = gated_in or bool(_TARGETING.sub(" ", req).strip())
            else:
                gated = gated_in or bool(req.replace("enttype target> critter eq", "").strip())
            ch = g.get("chance")
            chance = chance_in * (ch if ch not in (None, 0.0) else 1.0)
            if not gated:
                for t in g.get("templates") or []:
                    if {"Execute_Power", "Create_Entity"} & set(t.get("attribs") or []):
                        follow(t)
                    take(t, pv, chance)
            walk(g.get("child_effects"), pv, chance, gated)

    walk(crec.get("effects"), 0, 1.0, False)
    return rows, unmapped


def scalars(crec):
    return {"cast_time": _r(crec.get("activation_time")),
            "base_recharge": _r(crec.get("recharge_time")),
            "end_cost": _r(crec.get("endurance_cost")),
            "range": _r(crec.get("range")),
            "radius": _r(crec.get("radius")),
            "max_targets": int(crec.get("max_targets_hit") or 0),
            "effect_area": AREA.get(crec.get("effect_area"), 1),
            "level_available": int(crec.get("available_level") or 0) + 1}


def our_core(p):
    """Our record -> same core-row multiset, so BEFORE can be checked against it."""
    rows = defaultdict(Counter)
    for b in ("damage_effects", "buff_effects", "debuff_effects", "self_effects"):
        for e in p.get(b) or []:
            if e.get("pv_mode") == 2:
                continue
            bk = "heal" if e.get("effect") == "Heal" else b
            key = (bk, e.get("effect"), e.get("damage_type") or "None", _r(e.get("scale")),
                   e.get("modifier_table"), e.get("pv_mode", 0), _r(e.get("duration")),
                   _r(e.get("probability", 1.0)))
            rows[bk][key] += 1
    for e in p.get("heal_effects") or []:
        if e.get("pv_mode") == 2:
            continue
        rows["heal"][("heal", "Heal", "None", _r(e.get("scale")), e.get("modifier_table"),
                      e.get("pv_mode", 0), 0.0, _r(e.get("probability", 1.0)))] += 1
    for e in p.get("control_effects") or []:
        if e.get("pv_mode") == 2:
            continue
        rows["control_effects"][("control_effects", e.get("mez"), e.get("kind"),
                                 _r(e.get("scale")), _r(e.get("nmag")), e.get("modifier_table"),
                                 e.get("pv_mode", 0), _r(e.get("duration")),
                                 _r(e.get("probability", 1.0)))] += 1
    return rows


def ident(k):
    """Row identity ignoring numbers: bucket, effect, type, table, side."""
    if k[0] == "control_effects":
        return (k[0], k[1], k[5], k[6])
    return (k[0], k[1], k[2], k[4], k[5])


def loose(k):
    """Comparison key tolerant of side/duration bookkeeping differences."""
    if k[0] == "control_effects":
        return (k[0], k[1], k[3], k[5])
    return (k[0], k[1], k[2], k[3], k[4])


def main():
    mode = next((a for a in sys.argv[1:] if a.startswith("--")), "--calibrate")
    raw = open(POWERS, "rb").read()
    data = json.loads(raw.decode("utf-8"))
    ours = {p["full_name"]: p for v in data.values() for p in v}
    alias = json.load(open(ALIASES, encoding="utf-8")).get("aliases", {})
    to_client = lambda fn: alias.get(fn, fn)  # noqa: E731
    print(f"loading BEFORE {BEFORE}"); bx = load_export(BEFORE)
    print(f"loading AFTER  {AFTER}");  ax = load_export(AFTER)

    changed = []
    for fn, p in ours.items():
        c = to_client(fn)
        if c in bx and c in ax and json.dumps(bx[c].get("effects"), sort_keys=True) != json.dumps(ax[c].get("effects"), sort_keys=True) \
                or (c in bx and c in ax and scalars(bx[c]) != scalars(ax[c])):
            changed.append(fn)
    print(f"our powers whose client record changed: {len(changed)}")

    stats = Counter()
    report = []
    for fn in sorted(changed):
        p, c = ours[fn], to_client(fn)
        rb, ub = convert(bx[c])
        ra, ua = convert(ax[c])
        mine = our_core(p)
        # scalar calibration
        sb, sa = scalars(bx[c]), scalars(ax[c])
        for k in sb:
            if sb[k] != sa[k]:
                ov = _r(p.get(k)) if isinstance(p.get(k), float) else p.get(k)
                stats["scalar_change"] += 1
                stats["scalar_agrees" if ov == sb[k] else "scalar_mismatch"] += 1
        # effect calibration: every BEFORE row the patch touches must exist in ours
        delta_b = sum((rb[b] - ra[b] for b in rb), Counter())
        delta_a = sum((ra[b] - rb[b] for b in ra), Counter())
        if not delta_b and not delta_a:
            stats["effects_unchanged_by_converter"] += 1
            continue
        mine_loose = Counter(loose(k) for b in mine for k in mine[b].elements())
        miss = [k for k in delta_b.elements() if mine_loose[loose(k)] == 0]
        stats["effect_powers"] += 1
        if miss:
            stats["effect_powers_UNCALIBRATED"] += 1
            report.append((fn, miss[:4], sorted(ub)[:4]))
        else:
            stats["effect_powers_calibrated"] += 1

    print("\nCALIBRATION")
    for k, v in sorted(stats.items()):
        print(f"  {k:34} {v}")
    print(f"\nuncalibrated powers (first 40 of {len(report)}): BEFORE row the patch removes, not found in ours")
    for fn, miss, un in report[:40]:
        print(f"  {fn}")
        for m in miss:
            print(f"       {m}")
    if mode == "--calibrate":
        return
    apply_delta(data, ours, changed, to_client, bx, ax, raw, write=(mode == "--apply"))


# ── apply ────────────────────────────────────────────────────────────────────
MARK = "client_sync"
TAG = "I28P4"
BOOST = {"Accuracy": "Accuracy", "Buff_Defense": "Defense Buff", "Buff_ToHit": "To Hit Buff",
         "Confuse": "Confuse Duration", "Damage": "Damage Increase",
         "Debuff_Defense": "Defense Debuff", "Debuff_ToHit": "To Hit Debuff",
         "EnduranceDiscount": "Endurance Reduction", "Endurance_Drain": "Endurance Modification",
         "Recovery": "Endurance Modification", "Fear": "Fear Duration", "Heal": "Healing",
         "Hold": "Hold Duration", "Immobilize": "Immobilisation Duration",
         "Intangible": "Intangibility Duration", "Interrupt": "Activation Decrease",
         "Jump": "Jumping", "Knockback": "Knockback Distance", "Range": "Range",
         "Recharge": "Recharge Reduction", "Res_Damage": "Resist Damage",
         "Sleep": "Sleep Duration", "Slow": "Slow", "SpeedFlying": "Flight Speed",
         "SpeedRunning": "Run Speed", "Stun": "Disorient Duration", "Taunt": "Taunt Duration",
         "Incarnate_Destiny": "Destiny Incarnate", "Incarnate_Lore": "Lore Incarnate",
         "Incarnate_Interface": "Interface Incarnate"}
CAT = {"Universal Damage Sets": "Universal Damage", "Ranged AoE Damage": "Targeted AoE Damage",
       "Melee AoE Damage": "PBAoE Damage", "Universal Travel": "Travel",
       "Running & Sprints": "Run (No Sprint)", "Leaping & Sprints": "Jump (No Sprint)"}
ASPECT = {"ToHit": "ToHit", "DamageBuff": "Damage", "Heal": "Heal", "Defense": "Defense",
          "Regeneration": "Regeneration", "Recovery": "Recovery", "Endurance": "Endurance",
          "RechargeTime": "RechargeTime", "Resistance": "Resistance", "HitPoints": "HitPoints",
          "Absorb": "Absorb"}   # measured: one aspect per effect over all self_effects
# Per-power decisions for the calibration misses (2026-10-07, every one reported):
ADJUDICATED = {
    "Tanker_Melee.Super_Strength.Hand_Clap": (
        "rebuild", ("damage_effects", "control_effects"), {"max_targets": 5},
        "ours carried Mids' 16 targets and old rows; client 10 -> 5, now a damage attack"),
    "Defender_Buff.Sonic_Debuff.Sonic_Repulsion": (
        "rebuild", ("control_effects",), {},
        "new 25% Hold chance; the per-target endurance tick is not modelled"),
    "Controller_Buff.Sonic_Debuff.Sonic__Repulsion": (
        "rebuild", ("control_effects",), {},
        "new 25% Hold chance; the per-target endurance tick is not modelled"),
    "Brute_Defense.Psionic_Armor.Aura_of_Insanity": ("leave", "Page 4 change is PvP-only"),
    "Scrapper_Defense.Psionic_Armor.Aura_of_Insanity": ("leave", "Page 4 change is PvP-only"),
    "Stalker_Defense.Psionic_Armor.Aura_of_Insanity": ("leave", "Page 4 change is PvP-only"),
    "Epic.Pyre_Mastery.Char": ("leave", "DoT row detail our record never modelled"),
    "Epic.Sentinel_Fire_Mastery.Char": ("leave", "inherent-damage row our record never modelled"),
}
EXTRA = {"mode", "host_recharge", "stack", "penalty", "flags", "suppression", "unbuffable",
         "mez_row", "slow_resist_row", "max_hp_frac", "absorb_row", "ddr_row", "delay",
         "target", "crit_row"}


def _enh_maps(ours):
    eid = {}
    for p in ours.values():
        for i, n in zip(p["accepted_enhancement_type_ids"], p["accepted_enhancement_types"]):
            eid[n] = i
    cats = json.load(open(os.path.join(ROOT, "data", "set_categories.json"), encoding="utf-8"))["categories"]
    return eid, {c["name"]: (c["id"], c["short"]) for c in cats}


def _types(crec, eid):
    out = sorted({BOOST[b] for b in (crec.get("boosts_allowed") or []) if b in BOOST and BOOST[b] in eid},
                 key=lambda n: eid[n])
    return out


def _cats(crec, cid):
    out = []
    for c in crec.get("allowed_set_categories") or []:
        n = CAT.get(c, c)
        if n in cid and n not in out:
            out.append(n)
    return sorted(out, key=lambda n: cid[n][0])


def _row_from(k, extras):
    """Build one of OUR rows from a converter core row, inheriting layered fields."""
    b = k[0]
    if b == "control_effects":
        _, mez, kind, sc, nmag, tbl, pv, dur, ch = k
        return {"mez": mez, "kind": kind, "scale": sc, "nmag": nmag, "modifier_table": tbl,
                "duration": dur, "probability": ch, "pv_mode": pv}
    _, eff, dt, sc, tbl, pv, dur, ch = k
    if b == "damage_effects":
        r = {"effect": "Damage", "damage_type": dt, "scale": sc, "nmag": 1.0,
             "modifier_table": tbl, "probability": ch, "duration": dur, "pv_mode": pv,
             "enhance_aspect": "Damage", "ed_schedule": 0}
    elif b == "self_effects":
        r = {"effect": eff, "damage_type": dt, "scale": sc, "nmag": 1.0, "modifier_table": tbl,
             "enhance_aspect": ASPECT.get(eff, "None"), "ed_schedule": 0, "pv_mode": pv,
             "duration": dur}
    else:   # buff_effects / debuff_effects / heal (heal rows land as buff Heal rows)
        r = {"effect": eff, "damage_type": dt, "scale": sc, "nmag": 1.0, "modifier_table": tbl,
             "probability": ch, "duration": dur, "pv_mode": pv}
    for f, v in (extras or {}).items():
        if f in EXTRA:
            r[f] = v
    return r


def _ourkey(b, e):
    if b == "control_effects":
        return (b, e.get("mez"), _r(e.get("scale")), e.get("modifier_table"))
    return (b, e.get("effect"), e.get("damage_type") or "None", _r(e.get("scale")),
            e.get("modifier_table"))


def apply_delta(data, ours, changed, to_client, bx, ax, raw, write):
    eid, cid = _enh_maps(ours)
    log, review = [], []
    st = Counter()
    for fn in sorted(changed):
        p, c = ours[fn], to_client(fn)
        before, after = bx[c], ax[c]
        touched = []
        # 1) scalars: apply when BEFORE equals ours; cast_time also corrects stale values
        sb, sa = scalars(before), scalars(after)
        for k in sb:
            if sb[k] == sa[k]:
                continue
            ov = _r(p.get(k)) if isinstance(p.get(k), float) else p.get(k)
            if ov == sb[k] or k == "cast_time":
                touched.append(f"{k} {p.get(k)} -> {sa[k]}" + ("" if ov == sb[k] else " (also corrects stale)"))
                p[k] = sa[k]
                st["scalar_applied"] += 1
            else:
                review.append(f"{fn}: {k} ours={p.get(k)} client {sb[k]} -> {sa[k]} (not applied)")
                st["scalar_review"] += 1
        # 2) enhancement types / set categories: apply when mapped BEFORE equals ours
        # BY DIFFERENCE: add what the patch added, remove what it removed - our list
        # may hold entries the client export never did (it is not re-derived)
        tb, ta = _types(before, eid), _types(after, eid)
        if tb != ta:
            cur = list(p["accepted_enhancement_types"])
            new_l = sorted((set(cur) | (set(ta) - set(tb))) - (set(tb) - set(ta)), key=lambda n: eid[n])
            if new_l != cur:
                p["accepted_enhancement_types"] = new_l
                p["accepted_enhancement_type_ids"] = [eid[n] for n in new_l]
                touched.append(f"enhancements +{sorted(set(ta) - set(tb))} -{sorted(set(tb) - set(ta))}")
                st["enh_applied"] += 1
        cb, ca = _cats(before, cid), _cats(after, cid)
        if cb != ca:
            cur = list(p["accepted_set_categories"])
            new_l = sorted((set(cur) | (set(ca) - set(cb))) - (set(cb) - set(ca)), key=lambda n: cid[n][0])
            if new_l != cur:
                p["accepted_set_categories"] = new_l
                p["accepted_set_category_ids"] = [cid[n][0] for n in new_l]
                p["accepted_set_category_shorts"] = [cid[n][1] for n in new_l]
                touched.append(f"set categories +{sorted(set(ca) - set(cb))} -{sorted(set(cb) - set(ca))}")
                st["cat_applied"] += 1
        # 3) effects by difference, only for calibrated powers
        rb, _ = convert(before)
        ra, _ = convert(after)
        gone = sum((rb[b] - ra[b] for b in rb), Counter())
        new = sum((ra[b] - rb[b] for b in ra), Counter())
        adj = ADJUDICATED.get(fn)
        if adj and adj[0] == "rebuild":
            # Joel-visible adjudication: our record never matched the client for this
            # power (old Mids values) and the patch reworked it - the client is the
            # authority, so the modelled buckets are rebuilt from AFTER.
            for b in adj[1]:
                keep = [e for e in (p.get(b) or []) if e.get("pv_mode") == 2]
                p[b] = keep + [_row_from(k, None) for k in ra.get(b, Counter()).elements()]
            for k, v in adj[2].items():
                p[k] = v
            touched.append(f"REBUILT {list(adj[1])} from client AFTER ({adj[3]})")
            st["adjudicated_rebuild"] += 1
            gone = new = Counter()
        elif adj and adj[0] == "leave":
            review.append(f"{fn}: left as is - {adj[1]}")
            st["adjudicated_leave"] += 1
            gone = new = Counter()
        if gone or new:
            mine = our_core(p)
            mine_loose = Counter(loose(k) for b in mine for k in mine[b].elements())
            if any(mine_loose[loose(k)] == 0 for k in gone.elements()):
                review.append(f"{fn}: effects NOT patched (converter cannot reproduce ours); "
                              f"client removes {sum(gone.values())} / adds {sum(new.values())} rows")
                st["effects_review"] += 1
            else:
                inherit = {}
                for k in gone.elements():
                    b = k[0]
                    buckets = ("buff_effects", "self_effects", "heal_effects") if b == "heal" else (b,)
                    done = False
                    for bk in buckets:
                        lst = p.get(bk) or []
                        for i, e in enumerate(lst):
                            ek = _ourkey(bk if b != "heal" else "heal", e) if bk != "heal_effects" else None
                            if bk == "heal_effects":
                                hit = _r(e.get("scale")) == k[3] and e.get("modifier_table") == k[4]
                            elif b == "heal":
                                hit = e.get("effect") == "Heal" and (_r(e.get("scale")), e.get("modifier_table")) == (k[3], k[4])
                            else:
                                hit = ek == loose(k)
                            if hit and e.get("pv_mode", 0) != 2:
                                inherit.setdefault(ident(k), dict(e))
                                lst.pop(i)
                                done = True
                                break
                        if done:
                            break
                for k in new.elements():
                    b = k[0]
                    row = _row_from(k, inherit.get(ident(k)))
                    if row.get("host_recharge") is not None:
                        row["host_recharge"] = _r(after.get("recharge_time"))
                    p.setdefault("buff_effects" if b == "heal" else b, []).append(row)
                touched.append(f"effects -{sum(gone.values())} +{sum(new.values())}")
                st["effects_applied"] += 1
        # is_attack is exactly "has damage rows" (add_wind_control: 2,331/3,332 agree)
        has_dmg = any(e.get("pv_mode") != 2 for e in p.get("damage_effects") or [])
        if touched and bool(p.get("is_attack")) != has_dmg:
            touched.append(f"is_attack {p.get('is_attack')} -> {has_dmg}")
            p["is_attack"] = has_dmg
        if touched:
            p[MARK] = TAG
            log.append((fn, touched))
    print("\nAPPLY" + ("" if write else " (dry run)"))
    for k, v in sorted(st.items()):
        print(f"  {k:20} {v}")
    print(f"  records touched      {len(log)}")
    out_dir = os.path.join(ROOT, "tools", "gamedata")
    with open(os.path.join(out_dir, "i28p4_sync_log.txt"), "w", encoding="utf-8") as f:
        for fn, t in log:
            f.write(f"{fn}\n" + "".join(f"    {x}\n" for x in t))
        f.write("\nREVIEW (not applied)\n" + "".join(f"  {r}\n" for r in review))
    print(f"  log: tools/gamedata/i28p4_sync_log.txt  ({len(review)} review items)")
    if write:
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        json.loads(body.decode("utf-8"))           # build all bytes first, then open
        with open(POWERS, "wb") as f:
            f.write(body)
        print(f"  wrote {POWERS} ({len(raw):,} -> {len(body):,} bytes)")


if __name__ == "__main__":
    main()
