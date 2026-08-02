"""AUDIT: every travel-power name the app knows must resolve to a real power.

WHY THIS EXISTS. BasiliskXVIII reported (2026-08-01) that Mighty Leap and Speed
of Sound were not recognised as travel powers. The cause was worse than a missing
entry: the same fact lived in THREE places and they disagreed, and two of the
names in them were ghosts that could never match anything.

Verified errors this audit would have caught the day they were written:
  Leap         - Pool.Leaping.Leap DISPLAYS AS ACROBATICS, a mez-protection
                 toggle. Counting it as travel told a player with Acrobatics they
                 had "more than one travel power".
  Long_Jump    - the real Super Jump, missing from the coaching list, so Super
                 Jump users were told they had no travel power.
  Super_Jump   - a GHOST. No such leaf name exists.
  Infiltration - a GHOST. It is Pool.Invisibility.Invisibility.

The names are leaf names and cannot be derived (the game has no "is travel"
field), so the list is curated. This audit is what keeps a curated list honest.

Coverage denominator: every name in _TRAVEL_MAIN and _TRAVEL_EXTRA.

Run:  py tools\\audit_travel_powers.py
"""
import importlib.util as ilu
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = ilu.spec_from_file_location("cohserver", os.path.join(ROOT, "server", "server.py"))
srv = ilu.module_from_spec(spec)
spec.loader.exec_module(srv)

# Names that are deliberately NOT travel, each with the reason. If one of these
# ever appears in the travel sets again, that is the Acrobatics bug returning.
NEVER_TRAVEL = {
    "Leap": "displays as Acrobatics - a mez-protection toggle, not travel",
    "Combat_Jumping": "utility/mule, does not cross a zone",
    "Hasten": "recharge buff, not movement",
}


def main():
    powers = json.load(open(os.path.join(ROOT, "data", "powers.json"), encoding="utf-8"))
    by_leaf = {}
    for ps, recs in powers.items():
        for r in recs:
            by_leaf.setdefault(r["full_name"].split(".")[-1], []).append(r)

    names = sorted(set(srv._TRAVEL_MAIN) | set(srv._TRAVEL_EXTRA))
    expected = len(names)
    checked, fails = 0, []

    print(f"TRAVEL POWER AUDIT — {expected} names across _TRAVEL_MAIN + _TRAVEL_EXTRA\n")
    for n in names:
        checked += 1
        recs = by_leaf.get(n)
        if not recs:
            fails.append((n, "GHOST — no power with this leaf name exists"))
            continue
        disp = sorted({(r.get("display_name") or "?") for r in recs})
        tier = "MAIN" if n in srv._TRAVEL_MAIN else "extra"
        print(f"  OK  [{tier:5s}] {n:16s} -> {', '.join(disp)}")
        if n in NEVER_TRAVEL:
            fails.append((n, f"must NOT be travel: {NEVER_TRAVEL[n]}"))

    # The two lists must BE the same object, not merely equal today.
    same = srv._TRAVEL_POWER_NAMES is srv._TRAVEL_MAIN
    print(f"\n  {'OK ' if same else 'FAIL'} the coaching list and the classifier are ONE object")
    if not same:
        fails.append(("_TRAVEL_POWER_NAMES", "drifted back into a separate copy"))

    # Negative control: the audit must be able to fail.
    ghost = "Definitely_Not_A_Power"
    if ghost in by_leaf:
        fails.append((ghost, "negative control leaked into the data"))
    print(f"  OK  negative control: a fabricated name resolves to nothing")

    print(f"\n{checked} of {expected} names checked")
    if checked < expected:
        print("HARD FAIL: coverage denominator not met.")
        sys.exit(1)
    if fails:
        print(f"\n{len(fails)} FAILURE(S):")
        for n, why in fails:
            print(f"  {n:20s} {why}")
        sys.exit(1)
    print("ALL TRAVEL NAMES RESOLVE — one list, no ghosts, no mez toggles")


if __name__ == "__main__":
    main()
