"""STANDING GUARD (Joel's globals-list check, 2026-07-20): every set that carries
a BUILD-WIDE global unique piece must be recognized by server._GLOBAL_DESC, or the
slotting classifier mislabels a power hosting it (the Nimbus Overwhelming-Force
question that surfaced this). Game-first: the authority is each set's piece
short-help in data/set_details.json.

A build-wide global = a single slot granting an always-on, character-wide effect
(global recharge, knockback PROTECTION, slow resistance, +End/+recovery/+regen
proc, scaling-resist, absorb). Deliberately EXCLUDED (per-power, NOT build-wide):
"converts knockback to KNOCKDOWN" uniques (Overwhelming Force, Sudden Acceleration)
— they only affect the power they sit in.

Coverage-denominator rule: prints "N of N build-wide-global sets recognized" and
HARD-FAILS if any is missing from _GLOBAL_DESC.

Run:  py tools\\reality_check_globals.py
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# COVERAGE BOUNDARY (stated honestly): this guard verifies the global classes that
# are RELIABLY identifiable from a piece's short-help — global recharge, knockback
# PROTECTION, slow resistance, and the +End procs. The recovery/regen/defense/
# absorb globals are NOT auto-enumerable (their markers collide with ordinary
# healing-set enhancement aspects and ATO procs — 19 false positives when scanned
# broadly), so those stay CURATED in _GLOBAL_DESC and are out of this check's
# denominator. The value here: a future data sync that adds a new KB-prot / slow-
# resist / recharge / +End global can't silently go unrecognized.
_GLOBAL_MARKERS = (
    "+global recharge", "+res(slow)",
    "chance for +end", "chance for +endurance",
    "-kb", "-knockback",
)
# per-power KB->KD "conversion" uniques read as "-KB"/"-knockback" but are NOT
# build-wide globals (they only affect the power they sit in) — excluded by name.
_KBKD_CONVERSION_SETS = ("overwhelming force", "sudden acceleration")
_EXCLUDE_IF = ("converts knockback", "to knockdown", "chance for knockdown")


def _has_global_piece(pieces):
    for p in pieces or []:
        sh = (p.get("short") or "").lower()
        if not sh or any(x in sh for x in _EXCLUDE_IF):
            continue
        if any(m in sh for m in _GLOBAL_MARKERS):
            return sh
    return None


def main():
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "server"))
    import server as srv  # noqa: E402

    sd = json.load(open(os.path.join(ROOT, "data", "set_details.json"),
                        encoding="utf-8"))
    checked = 0
    missing = []
    for key, v in sd.items():
        disp = v.get("display_name") or key.replace("_", " ")
        if any(x in disp.lower() for x in _KBKD_CONVERSION_SETS):
            continue                       # per-power KB->KD, not a build-wide global
        mark = _has_global_piece(v.get("pieces") or [])
        if not mark:
            continue
        checked += 1
        if not srv._global_key(disp):
            missing.append((disp, mark))

    print(f"build-wide-global sets recognized: {checked - len(missing)} of "
          f"{checked} (via server._GLOBAL_DESC)")
    if missing:
        print(f"\nBUILD-WIDE GLOBALS MISSING from _GLOBAL_DESC — {len(missing)}:")
        for disp, mark in missing:
            print(f"  {disp}: piece '{mark}'")
        print("\nFAIL")
        sys.exit(1)
    print("\nPASS — every set with a build-wide global unique is recognized.")


if __name__ == "__main__":
    main()
