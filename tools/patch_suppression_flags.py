"""
patch_suppression_flags.py - Add combat-suppression bitmasks to powers.json
self_effects IN PLACE, without regenerating the file.

Why not a re-parse: data/powers.json carries layers a fresh parse would erase —
the client-synced values (tools/sync_power_values.py), the accuracy back-fill,
and the adjudicated rename end-costs. This tool is ADDITIVE ONLY: it re-reads
the Mids .mhd purely to learn each self-effect's eSuppress bitmask (a field
parse_mids used to discard) and annotates the matching self_effects entries.
No existing value is modified; entries that never suppress gain no key.

Matching is by SIGNATURE SEQUENCE, not position alone: for each power, the
re-derived self-effect list must agree with the on-disk list on
(effect, damage_type, modifier_table, pv_mode) pairwise — the fields no sync
pass touches. Any disagreement skips the power and counts as drift.

Coverage denominator (standing rule): prints "N of M expected" where M = powers
whose .mhd self-effects carry a non-zero suppression bit, counted independently
of the annotate loop — and hard-fails if any of those M can't be annotated, or
if the pinned known-suppressing powers (Pool Stealth family) end up unflagged.
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

# Known suppression-carrying powers (the reason #9 exists). If the run leaves
# any of these unflagged, the extraction is wrong — hard-fail. (Our frozen Mids
# DB predates the Concealment rename: the pool is Pool.Invisibility and has no
# Infiltration power — its stealths are Stealth/Invisibility. Verified against
# the .mhd: Stealth's PvE defense carries a 455 in-combat layer + a 7 mez-only
# layer; Steamy Mist-class team stealths carry mez-only 7.)
PINNED_SUPPRESSING = [
    "Pool.Invisibility.Stealth",
    "Pool.Invisibility.Invisibility",
    "Defender_Buff.Storm_Summoning.Steamy_Mist",
]


def self_effect_signatures(p, canon_table):
    """Re-derive the power's self_effects list (parse_mids.power_self_effects'
    exact filter) as (signature, suppression) pairs, in emission order."""
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
                    int(ef.get("suppression") or 0)))
    return out


def main():
    main_db = load_main_db(os.path.join(DB_DIR, "I12.mhd"))
    mod_tables = load_attribmod(os.path.join(DB_DIR, "AttribMod.json"))
    _mt_ci = {k.lower(): k for k in mod_tables}

    def canon_table(name):
        return _mt_ci.get((name or "").lower())

    derived = {}          # full_name -> [(signature, suppression), ...]
    expected = set()      # powers with any non-zero suppression bit (denominator)
    for p in main_db["powers"]:
        full = p.get("full_name")
        if not full:
            continue
        sigs = self_effect_signatures(p, canon_table)
        if not sigs:
            continue
        derived[full] = sigs
        if any(s for _, s in sigs):
            expected.add(full)

    with open(POWERS_JSON, encoding="utf-8") as f:
        powers = json.load(f)

    annotated, drifted, flagged_effects = set(), [], 0
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
                for e, (sig, _s) in zip(se, sigs))
            if not ok:
                if full in expected:
                    drifted.append((full, "signature mismatch"))
                continue
            for e, (_sig, sup) in zip(se, sigs):
                e.pop("suppression", None)      # idempotent re-runs
                if sup:
                    e["suppression"] = sup
                    flagged_effects += 1
            if full in expected:
                annotated.add(full)

    missing = expected & on_disk - annotated
    n, m = len(annotated), len(expected & on_disk)
    print(f"suppression flags: {n} of {m} expected powers annotated "
          f"({len(expected)} in the .mhd; {len(expected) - m} not in powers.json"
          f" — pets/uncatalogued), {flagged_effects} effects flagged")
    for full, why in drifted:
        print(f"  DRIFT {full}: {why}")

    pin_fail = [pn for pn in PINNED_SUPPRESSING if pn not in annotated]
    if missing or pin_fail:
        if pin_fail:
            print(f"  PIN FAIL — known suppressing powers unflagged: {pin_fail}")
        print("HARD FAIL: nothing written.")
        return 1

    with open(POWERS_JSON, "w", encoding="utf-8") as f:
        json.dump(powers, f, ensure_ascii=False, indent=1)   # parse_mids' format
    print(f"written: {POWERS_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
