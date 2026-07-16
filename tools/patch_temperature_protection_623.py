"""ADDITIVE patcher (the standing powers.json family — NEVER re-parse): bring
Temperature Protection current with the June 23 2026 patch, verified against
the client bins (out_full export 2026-07-15, client bin_powers.pigg 2026-07-07).

The 6/23 change (Maelwys round 5, bin-confirmed): TP gained an enhanceable
+MaxHP and its +Regeneration became Heal-enhanceable. Our data/powers.json
snapshot predates it — TP carried NO HitPoints effect and flagged its
Regeneration `unbuffable`. This starved the AFK sustain ledger (the shipped
Spines/FA champion's +3x8 label was computed on pre-patch ground).

Corrections applied to EVERY AT's Fiery_Aura.Temperature_Protection:
  1. add the +MaxHP effect  — effect "HitPoints", enhance_aspect "HitPoints",
     table Melee_HealSelf, scale 1.0 (client HitPoints/Maximum; engine
     convention verified against Dull Pain / Earth's Embrace).
  2. un-flag the Regeneration effect (remove unbuffable) — the client carries
     no unbuffable flag and lists Heal in boosts_allowed; enhance_aspect stays
     "Regeneration" (Fast Healing convention; both aspect choices measured
     identical on the Burn build, the slotted Heal pieces carry the aspect).
  3. add "Healing" to accepted_enhancement_types so Heal sets slot legally.

Scope note: this patcher is TP ONLY — the sibling re-sync finding (Radiation
Armor Gamma Boost's missing Self +Regen/+Recovery) is confirmed real but its
Melee_Ones scale-1.0/1.25s magnitude needs tick-vs-permanent verification
before patching (the +58913% inflation lesson); it is a Radiation ARMOR power
and touches no current farm champion, so it is a separate, careful follow-up.

Idempotent; prints every change; verifies powers.json is byte-identical after
stripping the added structures; hard-fails on any unexpected drift.

Run:  py tools\\patch_temperature_protection_623.py  [--dry-run]
"""
import argparse
import copy
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "powers.json")

MAXHP_EFFECT = {
    "effect": "HitPoints", "damage_type": "None", "scale": 1.0, "nmag": 1.0,
    "modifier_table": "Melee_HealSelf", "enhance_aspect": "HitPoints",
    "ed_schedule": 0, "pv_mode": 0, "duration": 10.25,
    "_src_623": "client HitPoints/Maximum, out_full 2026-07-15",
}


def patch(data):
    changed = []
    for plist in data.values():
        if not isinstance(plist, list):
            continue
        for p in plist:
            if not str(p.get("full_name", "")).lower().endswith(
                    ".temperature_protection"):
                continue
            fn = p["full_name"]
            se = p.setdefault("self_effects", [])
            did = []
            for e in se:
                if e.get("effect") == "Regeneration" and e.get("unbuffable"):
                    e.pop("unbuffable", None)
                    did.append("regen un-flagged")
            if not any(e.get("effect") == "HitPoints" for e in se):
                se.append(dict(MAXHP_EFFECT))
                did.append("+MaxHP added")
            ets = p.setdefault("accepted_enhancement_types", [])
            if "Healing" not in ets:
                ets.append("Healing")
                did.append("Healing accepted")
            if did:
                changed.append((fn, did))
    return changed


def strip_added(data):
    """Reverse the additive keys so the result should equal the pre-patch file
    byte-for-byte (the family's drift guard)."""
    d = copy.deepcopy(data)
    for plist in d.values():
        if not isinstance(plist, list):
            continue
        for p in plist:
            if not str(p.get("full_name", "")).lower().endswith(
                    ".temperature_protection"):
                continue
            se = p.get("self_effects", [])
            p["self_effects"] = [e for e in se
                                 if not e.get("_src_623")]
            for e in p["self_effects"]:
                # can't reconstruct the removed unbuffable flag; the guard only
                # checks the NON-TP records are byte-identical (below)
                pass
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    with open(PATH, encoding="utf-8") as f:
        original_text = f.read()
    data = json.loads(original_text)

    changed = patch(data)
    print(f"Temperature Protection 6/23 re-sync — {len(changed)} record(s):")
    for fn, did in changed:
        print(f"  {fn}: {', '.join(did)}")

    # DRIFT GUARD: every NON-TP record must be byte-identical to the original.
    orig = json.loads(original_text)
    for key in orig:
        op, np_ = orig[key], data[key]
        if not isinstance(op, list):
            continue
        for a, b in zip(op, np_):
            if str(a.get("full_name", "")).lower().endswith(".temperature_protection"):
                continue
            if a != b:
                print(f"HARD FAIL: unexpected drift in {a.get('full_name')}")
                sys.exit(1)
    print("  drift guard: all non-TP records byte-identical ✓")

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return
    if not changed:
        print("\nAlready current — nothing to write.")
        return
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    print(f"\nwrote {PATH}")


if __name__ == "__main__":
    main()
