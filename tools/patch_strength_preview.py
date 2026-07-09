"""
patch_strength_preview.py - Annotate powers.json IN PLACE with the two fields
the Power Boost preview needs, without regenerating the file:

  1. `unbuffable: true` on self_effects entries whose .mhd Buffable flag is
     False. Mids gates EVERY buff-application loop per effect on this flag
     (clsToonX.cs:1776, :1295; renders "[Ignores Enhancements & Buffs]") — so
     a flat +66% amplifier on everything is wrong by the game's own model,
     and the preview must skip these effects.
  2. `strength_effects` on powers that carry Enhancement(X) SELF effects
     outside the four global kinds (Power Boost's Defense/Mez/Heal/Absorb/
     Endurance/speed families, +66% for 15s) — the amplifier records the
     preview consumes. Deduped per (family, scale, duration): the game stores
     one row per damage/mez subtype.

Why not a re-parse: data/powers.json carries layers a fresh parse would erase
(client-synced values, accuracy/heal back-fills, suppression flags, durations,
adjudicated rename end-costs). ADDITIVE ONLY; idempotent re-runs.

Matching is by SIGNATURE SEQUENCE (effect, damage_type, modifier_table,
pv_mode) pairwise — the fields no sync pass touches. Disagreement = drift.

Coverage denominators (standing rule), each hard-fail:
  - unbuffable: N of M powers whose .mhd self-effects carry Buffable=False,
    M counted independently of the annotate loop.
  - strength: N of M powers whose .mhd carries qualifying Enhancement(X)
    self effects.
Pins: every Power_Boost/Power_Build_Up record gains a Defense-family
strength effect; Farsight's Defense self-effects stay BUFFABLE (the Maelwys
acceptance combo — if the data disagreed, the feature premise is wrong and
nothing should be written).
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from parse_mids import (  # noqa: E402
    DB_DIR, EDAMAGE, EFFECT_TO_ENHANCE, EFFECT_TYPE,
    load_attribmod, load_main_db,
)

POWERS_JSON = os.path.join(PROJECT, "data", "powers.json")

# Pin by DISPLAY name — internal names are reused across per-AT variants
# (deviant_code.md convention; this run found Epic.Blaster_Mace_Mastery.
# Power_Boost displaying as "Summon Spiderlings", a pet summon).
PIN_AMPLIFIERS = ("Power Boost", "Power Build Up")   # display_name equals
PIN_BUFFABLE_DEFENSE = [
    "Controller_Buff.Time_Manipulation.Farsight",
    "Defender_Buff.Time_Manipulation.Farsight",
]


def derive(p, canon_table):
    """(signatures+buffable) for self_effects order-matching, and the power's
    strength_effects — parse_mids' exact filters."""
    sigs = []
    strength = []
    seen = set()
    for ef in p["effects"]:
        et = (EFFECT_TYPE[ef["effect_type"]]
              if 0 <= ef["effect_type"] < len(EFFECT_TYPE) else None)
        mod_et = (EFFECT_TYPE[ef["et_modifies"]]
                  if 0 <= ef["et_modifies"] < len(EFFECT_TYPE) else None)
        if et == "Enhancement" and mod_et not in (
                "RechargeTime", "Recovery", "Regeneration", "ToHit", None):
            if (ef["attrib_type"] == 0 and ef["to_who"] == 2
                    and ef["base_probability"] >= 0.99):
                key = (mod_et, round(ef["scale"], 6), round(ef["duration"], 3))
                if key not in seen:
                    seen.add(key)
                    strength.append({"modifies": mod_et,
                                     "scale": round(ef["scale"], 6),
                                     "duration": round(ef["duration"], 3)})
            continue
        if et in EFFECT_TO_ENHANCE:
            eff_stat = et
        elif et == "Enhancement" and mod_et in ("RechargeTime", "Recovery",
                                                "Regeneration", "ToHit"):
            eff_stat = mod_et
        else:
            continue
        if ef["attrib_type"] != 0 or ef["to_who"] != 2:
            continue
        if ef["base_probability"] < 0.99:
            continue
        mt = canon_table(ef["modifier_table"])
        if mt is None:
            continue
        dt = (EDAMAGE[ef["damage_type"]]
              if 0 <= ef["damage_type"] < len(EDAMAGE) else "None")
        sigs.append(((eff_stat, dt, mt, ef["pv_mode"]),
                     bool(ef.get("buffable", True))))
    return sigs, strength


def main():
    main_db = load_main_db(os.path.join(DB_DIR, "I12.mhd"))
    mod_tables = load_attribmod(os.path.join(DB_DIR, "AttribMod.json"))
    _mt_ci = {k.lower(): k for k in mod_tables}

    def canon_table(name):
        return _mt_ci.get((name or "").lower())

    derived = {}
    expect_unbuff = set()     # denominator 1
    expect_strength = set()   # denominator 2
    for p in main_db["powers"]:
        full = p.get("full_name")
        if not full:
            continue
        sigs, strength = derive(p, canon_table)
        if not (sigs or strength):
            continue
        derived[full] = (sigs, strength)
        if any(not b for _, b in sigs):
            expect_unbuff.add(full)
        if strength:
            expect_strength.add(full)

    with open(POWERS_JSON, encoding="utf-8") as f:
        powers = json.load(f)

    done_unbuff, done_strength, drifted = set(), set(), []
    flagged, on_disk = 0, set()
    for plist in powers.values():
        for rec in plist:
            full = rec.get("full_name")
            if not full:
                continue
            on_disk.add(full)
            sigs, strength = derived.get(full, ([], []))
            se = rec.get("self_effects") or []
            if sigs and se:
                if len(sigs) != len(se) or not all(
                        (e.get("effect"), e.get("damage_type"),
                         e.get("modifier_table"), e.get("pv_mode", 0)) == sig
                        for e, (sig, _b) in zip(se, sigs)):
                    if full in expect_unbuff:
                        drifted.append((full, "self_effects signature mismatch"))
                else:
                    for e, (_sig, buffable) in zip(se, sigs):
                        e.pop("unbuffable", None)          # idempotent
                        if not buffable:
                            e["unbuffable"] = True
                            flagged += 1
                    if full in expect_unbuff:
                        done_unbuff.add(full)
            rec.pop("strength_effects", None)              # idempotent
            if strength:
                rec["strength_effects"] = strength
                done_strength.add(full)

    miss_u = expect_unbuff & on_disk - done_unbuff
    miss_s = expect_strength & on_disk - done_strength
    n_u, m_u = len(done_unbuff), len(expect_unbuff & on_disk)
    n_s, m_s = len(done_strength), len(expect_strength & on_disk)
    print(f"unbuffable flags: {n_u} of {m_u} expected powers annotated "
          f"({len(expect_unbuff)} in the .mhd), {flagged} effects flagged")
    print(f"strength effects: {n_s} of {m_s} expected powers annotated "
          f"({len(expect_strength)} in the .mhd)")
    for full, why in drifted:
        print(f"  DRIFT {full}: {why}")

    by_full = {rec.get("full_name"): rec
               for plist in powers.values() for rec in plist}
    pin_fail = []
    amp_pins = [f for f, rec in by_full.items()
                if f and (rec or {}).get("display_name") in PIN_AMPLIFIERS]
    for f in amp_pins:
        sfx = by_full[f].get("strength_effects") or []
        if not any(s["modifies"] == "Defense" for s in sfx):
            pin_fail.append(f"{f}: no Defense strength effect")
        else:
            d = next(s for s in sfx if s["modifies"] == "Defense")
            print(f"  PIN {f}: Defense ×{1 + d['scale']:.2f} for {d['duration']}s")
    for f in PIN_BUFFABLE_DEFENSE:
        se = (by_full.get(f) or {}).get("self_effects") or []
        defs = [e for e in se if e.get("effect") == "Defense"]
        if not defs:
            pin_fail.append(f"{f}: no Defense self-effects found")
        elif any(e.get("unbuffable") for e in defs):
            pin_fail.append(f"{f}: Defense marked UNBUFFABLE — Power Boost+"
                            "Farsight is the known-working combo; investigate")
        else:
            print(f"  PIN {f}: {len(defs)} Defense effects, all buffable")

    if miss_u or miss_s or pin_fail:
        for x in pin_fail:
            print(f"  PIN FAIL — {x}")
        for full in sorted(miss_u):
            print(f"  MISSING unbuffable {full}")
        for full in sorted(miss_s):
            print(f"  MISSING strength {full}")
        print("HARD FAIL: nothing written.")
        return 1

    with open(POWERS_JSON, "w", encoding="utf-8") as f:
        json.dump(powers, f, ensure_ascii=False, indent=1)   # parse_mids' format
    print(f"written: {POWERS_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
