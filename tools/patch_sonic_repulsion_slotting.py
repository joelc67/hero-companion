"""Sonic Repulsion's slotting, per the 2026-10-17 live client.

The patch took damage out of Sonic Repulsion's slotting. Client diff, live export
2026-09-29 -> 2026-10-17 (bin_crawler.diff_exports + record compare), all four
archetypes' records:
  allowed_set_categories  drop 'Melee AoE Damage' and 'Universal Damage Sets'
                          (ours: id 4 'PBAoE Damage', id 44 'Universal Damage');
                          Defender and Mastermind also drop their archetype sets
                          (ours: id 37, id 40); Controller/Corruptor keep theirs
  boosts_allowed          drop 'Damage' (ours: enhancement type id 4)
and boostsets.json removes Sonic Repulsion from exactly those sets' allowed_powers
(52 entries, nothing else changed in that file). The power's effects did not
change. The game enforces what its records say, so the planner must offer that.

Additive-patcher family rules: the file's own serialization (round-trip identity
asserted BEFORE any write), coverage denominator (exactly 4 records, 10 category
and 4 type removals, hard-fail otherwise), parallel id/name/short arrays edited
together, idempotent (a second run removes nothing and exits 0).

Run:  python tools/patch_sonic_repulsion_slotting.py [--check]
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.join(os.path.dirname(__file__), "..")
POWERS = os.path.join(ROOT, "data", "powers.json")

DAMAGE_CATS = {4, 44}            # PBAoE Damage, Universal Damage
REMOVE_CATS = {
    "Controller_Buff.Sonic_Debuff.Sonic__Repulsion": DAMAGE_CATS,
    "Corruptor_Buff.Sonic_Resonance.Sonic_Repulsion": DAMAGE_CATS,
    "Defender_Buff.Sonic_Debuff.Sonic_Repulsion": DAMAGE_CATS | {37},     # + Defender Archetype Sets
    "Mastermind_Buff.Sonic_Resonance.Sonic_Repulsion": DAMAGE_CATS | {40},  # + Mastermind Archetype Sets
}
REMOVE_TYPES = {4}               # Damage Increase
EXPECT = (4, 10, 4)              # records, category removals, type removals


def main():
    check = "--check" in sys.argv
    raw = open(POWERS, "rb").read()
    powers = json.loads(raw.decode("utf-8"))
    if json.dumps(powers).encode("utf-8") != raw:
        sys.exit("FAIL: powers.json is not in its canonical json.dumps form; refusing to write")

    recs = {p["full_name"]: p for lst in powers.values() for p in lst if p["full_name"] in REMOVE_CATS}
    if len(recs) != len(REMOVE_CATS):
        sys.exit(f"FAIL: found {len(recs)} of {len(REMOVE_CATS)} Sonic Repulsion records")

    cats_removed = types_removed = 0
    for fn, drop in REMOVE_CATS.items():
        p = recs[fn]
        keep = [i for i, cid in enumerate(p["accepted_set_category_ids"]) if cid not in drop]
        cats_removed += len(p["accepted_set_category_ids"]) - len(keep)
        for f in ("accepted_set_category_ids", "accepted_set_categories", "accepted_set_category_shorts"):
            if f in p:
                p[f] = [p[f][i] for i in keep]
        tkeep = [i for i, tid in enumerate(p["accepted_enhancement_type_ids"]) if tid not in REMOVE_TYPES]
        types_removed += len(p["accepted_enhancement_type_ids"]) - len(tkeep)
        for f in ("accepted_enhancement_type_ids", "accepted_enhancement_types"):
            p[f] = [p[f][i] for i in tkeep]
        print(f"  {fn}: sets {p['accepted_set_categories']} | types {p['accepted_enhancement_types']}")

    if (cats_removed, types_removed) == (0, 0):
        print("already applied: nothing to remove")
        return
    got = (len(recs), cats_removed, types_removed)
    print(f"records {got[0]} of {EXPECT[0]}, category removals {got[1]} of {EXPECT[1]}, type removals {got[2]} of {EXPECT[2]}")
    if got != EXPECT:
        sys.exit("FAIL: removal counts differ from the client diff")
    if check:
        print("--check: nothing written")
        return
    open(POWERS, "wb").write(json.dumps(powers).encode("utf-8"))
    print(f"wrote {POWERS}")


if __name__ == "__main__":
    main()
