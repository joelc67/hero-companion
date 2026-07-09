"""
patch_effect_durations.py - Add buff-window durations to powers.json
self_effects IN PLACE, without regenerating the file.

Why not a re-parse: data/powers.json carries layers a fresh parse would erase —
the client-synced values (tools/sync_power_values.py), the accuracy/heal
back-fills, the suppression flags, and the adjudicated rename end-costs. This
tool is ADDITIVE ONLY: it re-reads the Mids .mhd purely to learn each
self-effect's nDuration (a field parse_mids read at :274 but never emitted for
self_effects — the bug that left every click_buff's buff_duration at 0 and the
totals-chip uptime note silently dead) and annotates the matching entries.
No existing value is modified; zero-duration effects gain no key (the
suppression patcher's convention).

Matching is by SIGNATURE SEQUENCE, not position alone: for each power, the
re-derived self-effect list must agree with the on-disk list on
(effect, damage_type, modifier_table, pv_mode) pairwise — the fields no sync
pass touches. Any disagreement skips the power and counts as drift.

Coverage denominator (standing rule): prints "N of M expected" where M = powers
whose .mhd self-effects carry a non-zero duration, counted independently of the
annotate loop — and hard-fails if any of those M can't be annotated, or if the
pinned known-windowed powers (Hasten, a Build Up) end up without a duration.
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

# Known windowed click buffs (the reason the uptime note exists). If the run
# leaves any of these without a duration, the extraction is wrong — hard-fail.
# Values printed for eyeball; the pin asserts nonzero, the data speaks for the
# magnitude (game-first: no wiki number is hardcoded here).
PINNED_WINDOWED = [
    "Pool.Speed.Hasten",
    "Scrapper_Melee.Broad_Sword.Build_Up",
]


def self_effect_signatures(p, canon_table):
    """Re-derive the power's self_effects list (parse_mids.power_self_effects'
    exact filter) as (signature, duration) pairs, in emission order."""
    out = []
    for ef in p["effects"]:
        et = (EFFECT_TYPE[ef["effect_type"]]
              if 0 <= ef["effect_type"] < len(EFFECT_TYPE) else None)
        if et in EFFECT_TO_ENHANCE:
            eff_stat = et
        elif et == "Enhancement":
            mod_et = (EFFECT_TYPE[ef["et_modifies"]]
                      if 0 <= ef["et_modifies"] < len(EFFECT_TYPE) else None)
            if mod_et in ("RechargeTime", "Recovery", "Regeneration", "ToHit"):
                eff_stat = mod_et
            else:
                continue
        else:
            continue
        if ef["attrib_type"] != 0:
            continue
        if ef["to_who"] != 2:
            continue
        if ef["base_probability"] < 0.99:
            continue
        mt = canon_table(ef["modifier_table"])
        if mt is None:
            continue
        dt = (EDAMAGE[ef["damage_type"]]
              if 0 <= ef["damage_type"] < len(EDAMAGE) else "None")
        out.append(((eff_stat, dt, mt, ef["pv_mode"]),
                    round(ef.get("duration") or 0.0, 3)))
    return out


def main():
    main_db = load_main_db(os.path.join(DB_DIR, "I12.mhd"))
    mod_tables = load_attribmod(os.path.join(DB_DIR, "AttribMod.json"))
    _mt_ci = {k.lower(): k for k in mod_tables}

    def canon_table(name):
        return _mt_ci.get((name or "").lower())

    derived = {}          # full_name -> [(signature, duration), ...]
    expected = set()      # powers with any non-zero duration (denominator)
    for p in main_db["powers"]:
        full = p.get("full_name")
        if not full:
            continue
        sigs = self_effect_signatures(p, canon_table)
        if not sigs:
            continue
        derived[full] = sigs
        if any(d for _, d in sigs):
            expected.add(full)

    with open(POWERS_JSON, encoding="utf-8") as f:
        powers = json.load(f)

    annotated, drifted, stamped_effects = set(), [], 0
    on_disk = set()
    for plist in powers.values():
        for rec in plist:
            full = rec.get("full_name")
            se = rec.get("self_effects") or []
            if not (full and se):
                continue
            on_disk.add(full)
            sigs = derived.get(full)
            if sigs is None or len(sigs) != len(se):
                if full in expected:
                    drifted.append((full, "length/lookup mismatch"))
                continue
            ok = all(
                (e.get("effect"), e.get("damage_type"),
                 e.get("modifier_table"), e.get("pv_mode", 0)) == sig
                for e, (sig, _d) in zip(se, sigs))
            if not ok:
                if full in expected:
                    drifted.append((full, "signature mismatch"))
                continue
            for e, (_sig, dur) in zip(se, sigs):
                e.pop("duration", None)         # idempotent re-runs
                if dur:
                    e["duration"] = dur
                    stamped_effects += 1
            if full in expected:
                annotated.add(full)

    missing = expected & on_disk - annotated
    n, m = len(annotated), len(expected & on_disk)
    print(f"effect durations: {n} of {m} expected powers annotated "
          f"({len(expected)} in the .mhd; {len(expected) - m} not in powers.json"
          f" — pets/uncatalogued), {stamped_effects} effects stamped")
    for full, why in drifted:
        print(f"  DRIFT {full}: {why}")

    pin_fail = []
    by_full = {rec.get("full_name"): rec
               for plist in powers.values() for rec in plist}
    for pn in PINNED_WINDOWED:
        rec = by_full.get(pn)
        durs = [e.get("duration") or 0 for e in (rec or {}).get("self_effects") or []]
        if not any(durs):
            pin_fail.append(pn)
        else:
            print(f"  PIN {pn}: max window {max(durs)}s")

    if missing or pin_fail:
        if pin_fail:
            print(f"  PIN FAIL — known windowed powers without duration: {pin_fail}")
        for full in sorted(missing):
            print(f"  MISSING {full}")
        print("HARD FAIL: nothing written.")
        return 1

    with open(POWERS_JSON, "w", encoding="utf-8") as f:
        json.dump(powers, f, ensure_ascii=False, indent=1)   # parse_mids' format
    print(f"written: {POWERS_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
