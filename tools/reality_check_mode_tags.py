"""Every client mode tag is classified, or this fails.

The client gates its modes and meters with an effect-group field called `tags`.
`tools/mode_tags.py` says what each one means and why. This check enforces the
project's full-accounting rule against it: a tag that reaches a SCORED group of
a power we actually carry must have an adjudication, and a stale adjudication
for a tag that no longer appears must be removed.

⚠ THE DENOMINATOR IS THE POINT. "48 of 48 tags classified" is only worth
anything if 48 comes from the client rather than from this file. It is counted
by sweeping the export for tags on scored groups of powers in our data.

⚠ SCOPE, stated: a tag on a record we do NOT carry (a boost definition, a pet, a
temp power) is reported and not required to be classified. Those records are
excluded from scoring for reasons that have nothing to do with modes.

Usage: python tools/reality_check_mode_tags.py [--verbose]
"""
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from add_wind_control import client_index                      # noqa: E402
from mode_tags import TAGS, LABEL, PROB, MODE, SCENARIO, DERIVED  # noqa: E402

VERBOSE = "--verbose" in sys.argv
MEZ = {"Held", "Immobilized", "Stunned", "Sleep", "Confused", "Terrorized",
       "Afraid", "Intangible", "Knockback", "Knockup", "Repel"}
PLAIN = {"Defense", "Resistance", "ToHit", "RechargeTime", "Regeneration",
         "Recovery", "Absorb", "HitPoints", "Endurance", "Heal_Dmg"}
# records that exist in our data but are not powers a player picks and score
NOT_A_PICK = ("Boosts.", "Incarnate.", "Pets.", "Temporary_Powers.",
              "Mastermind_Pets.", "Villain_Pets.", "Redirects.")


def scored(group):
    """Does this group carry a value our extractor would turn into a row?"""
    for t in (group.get("templates") or []):
        if not (t.get("scale") or t.get("magnitude")):
            continue
        for a in (t.get("attribs") or []):
            if a.endswith("_Dmg") or a in MEZ or a in PLAIN:
                return True
    return False


def main():
    powers = json.load(open(os.path.join(ROOT, "data", "powers.json"),
                            encoding="utf-8"))
    ours = {p["full_name"] for lst in powers.values() for p in lst
            if not p["full_name"].startswith(NOT_A_PICK)}
    client = client_index()

    in_scope = collections.Counter()
    scope_powers = collections.defaultdict(set)
    out_of_scope = collections.Counter()
    for fn, rec in client.items():
        mine = fn in ours
        for g in (rec.get("effects") or []):
            for tag in (g.get("tags") or []):
                if mine and scored(g):
                    in_scope[tag] += 1
                    scope_powers[tag].add(fn)
                else:
                    out_of_scope[tag] += 1

    print(f"Tags on a SCORED group of a power we carry : {len(in_scope)} "
          f"({sum(in_scope.values())} groups, "
          f"{len(set().union(*scope_powers.values())) if scope_powers else 0} powers)")
    print(f"Tags only on records we do not score       : "
          f"{len(set(out_of_scope) - set(in_scope))} (reported, not required)")

    by_class = collections.Counter()
    unclassified = []
    for tag in sorted(in_scope, key=lambda t: -in_scope[t]):
        cls = TAGS.get(tag, (None, None))[0]
        if cls is None:
            unclassified.append(tag)
        else:
            by_class[cls] += in_scope[tag]

    print()
    for cls, what in ((LABEL, "not a gate - the effect is taken"),
                      (PROB, "a stated chance - weighted, never skipped"),
                      (MODE, "duty cycle derivable from the game's own numbers"),
                      (SCENARIO, "real, blocked on ONE scenario input (Joel's)"),
                      (DERIVED, "the engine models it another way - taking it "
                                "would double-count")):
        tags = [t for t in in_scope if TAGS.get(t, (None,))[0] == cls]
        print(f"{cls:<9} {len(tags):>3} tags / {by_class[cls]:>4} groups  - {what}")
        if VERBOSE:
            for t in sorted(tags, key=lambda x: -in_scope[x]):
                print(f"            {t:<24}{in_scope[t]:>4}  {TAGS[t][1]}")

    # a stale entry is as much a defect as a missing one - the two-way pin rule
    stale = [t for t in TAGS if t not in in_scope and t not in out_of_scope]
    fail = 0
    if unclassified:
        fail = 1
        print(f"\nHARD FAIL: {len(unclassified)} tag(s) reach a scored group with "
              "no adjudication in tools/mode_tags.py:")
        for t in unclassified:
            ex = sorted(scope_powers[t])[:2]
            print(f"    {t:<24}{in_scope[t]:>4} groups  e.g. "
                  f"{', '.join(x.split('.')[-1] for x in ex)}")
    if stale:
        fail = 1
        print(f"\nHARD FAIL: {len(stale)} adjudication(s) name a tag the client no "
              "longer carries anywhere - remove them:")
        for t in stale:
            print(f"    {t}")
    if fail:
        return 1
    print(f"\nEVERY TAG CLASSIFIED. {len(in_scope)} of {len(in_scope)} in scope, "
          f"no stale entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
