"""Powers the CLIENT has that our data does not - separating naming from absence.

WHY THIS EXISTS, AND WHY IT IS MOSTLY A NAMING CHECK
----------------------------------------------------
Both other reality checks compare only powers we already carry, so a record we
never had is invisible to them by construction. Counting the raw difference
gives ~459 client player powers "missing" - and that number is wrong in the way
this project keeps being wrong. Almost all of it is the three-namespaces rule:

  * 19 POWERSETS are RENAMED, not missing. The client's Shock Therapy is our
    Electrical Affinity; its Time Manipulation is our Temporal Manipulation; its
    Pool.Fitness is our Inherent.Fitness; and thirteen Epic sets are the
    already-proven bridge (Epic.Blaster_Dark_Mastery = Epic.Dark_Mastery_Blaster).
    Every one matches on a display-name roster of 1.0 - identical rosters.
  * The KHELDIAN FORMS are a namespace difference: the client files White Dwarf
    Strike under the Kheldian powerset, we file it under Inherent.Inherent.
  * NEVER-PICKABLE powers (available_level 0xFFFFFFFF) are absent ON PURPOSE -
    Afterburner/Fly_Boost is the recorded case, and Double Jump, Speed Phase,
    Arcane Power and Takeoff are the same auto-issue class.
  * REDIRECT variants (Rending_Flurry_Normal/Large, Savage_Leap_AoE) are the
    reconciliation lane's proven fold, not separate picks.
  * PET records are the pet model's, not the build's.

What is left after all that is small, real, and named in ABSENT below.

⚠ THE APP DOES NOT OFFER THE ABSENT SETS AT ALL - powersets.json has no Wind
Control, Gadgetry or Utility Belt - so nothing is broken on screen. A player
simply cannot plan them. That is an honest absence, not a defect, and the
distinction matters when deciding what to do about it.

Report-only. Usage:  python tools/reality_check_missing_powers.py [--all]
"""
import json
import os
import sys
import glob
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEVER_PICKABLE = 4294967295          # the client's "auto-issue, never chosen"

# Player-pickable powerset prefixes. Pets, temp powers, incarnates and inherents
# are modelled elsewhere and are not what this check is about.
PICKABLE = (
    "Pool.", "Epic.", "Blaster_Ranged", "Blaster_Support", "Controller_Control",
    "Controller_Buff", "Defender_Ranged", "Defender_Buff", "Scrapper_Melee",
    "Scrapper_Defense", "Tanker_Melee", "Tanker_Defense", "Brute_Melee",
    "Brute_Defense", "Stalker_Melee", "Stalker_Defense", "Sentinel_Ranged",
    "Sentinel_Defense", "Corruptor_Ranged", "Corruptor_Buff", "Dominator_Control",
    "Dominator_Assault", "Mastermind_Summon", "Mastermind_Buff",
    "Peacebringer_", "Warshade_", "Arachnos_Soldiers", "Widow_Training",
)

# ⚠ REAL AND PINNED. Counts are POWERS, and the pin fails in both directions.
ABSENT = {
    # ✅ CLOSED by tools/add_wind_control.py: both archetypes' Wind Control
    # is in the data, offered in powersets.json and priced (pets included).
    # The pin failed the moment it landed, which is what a pin is for.
    # ✅ CLOSED by tools/add_origin_pools.py: both origin pools are in the data,
    # served to all 15 archetypes, prerequisites read from the game's own
    # requires expression and enforced by _picks_legal, and the two auto-issue
    # free riders (Turbo Boost, Athletics) deliberately left out. Their pins
    # went red the moment the pools landed, which is what a pin is for.
    # ⚠ NO PIN REMAINS for either. 5 of the 6 client records per pool are
    # pickable and now exist; the sixth (Turbo Boost / Athletics) carries the
    # auto-issue sentinel and is already counted under NEVER-PICKABLE above, so
    # a pin of 1 here would double-count it - as a first attempt at retiring
    # these did, and the check said so.
    # ✅ CLOSED by tools/add_boomerang_slice.py: all four records now exist,
    # client-sourced, with the mutual exclusion against Slice enforced in the
    # validator and in _picks_legal. The pin is what said so - it failed on
    # the stale entries the moment the power landed.
}


def load():
    ours = json.load(open(os.path.join(ROOT, "data", "powers.json"), encoding="utf-8"))
    client = {}
    for f in glob.glob(os.path.join(ROOT, "tools", "gamedata", "bin-crawler",
                                    "out_full", "**", "*.json"), recursive=True):
        if os.path.basename(f) == "index.json":
            continue
        try:
            c = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if c.get("full_name"):
            client[c["full_name"]] = c
    return ours, client


def main():
    show_all = "--all" in sys.argv
    ours_raw, client = load()
    ours = {p["full_name"] for _ps, l in ours_raw.items() for p in l}
    # display-name rosters, for the rename test
    our_set_disp = {ps: {(p.get("display_name") or "").lower() for p in l}
                    for ps, l in ours_raw.items()}
    our_disp_any = {d for s in our_set_disp.values() for d in s if d}

    cl_sets = collections.defaultdict(dict)
    for fn, c in client.items():
        if fn.count(".") < 2:
            continue
        cl_sets[".".join(fn.split(".")[:2])][fn.split(".")[-1]] = c

    renamed, absent_sets, unpickable, ns_diff, residue = [], [], 0, 0, []
    aux_variants = {}
    for ps, leaves in cl_sets.items():
        if not ps.startswith(PICKABLE):
            continue
        miss = {leaf: c for leaf, c in leaves.items()
                if f"{ps}.{leaf}" not in ours}
        if not miss:
            continue
        if ps.endswith("_Aux") or "_Aux." in ps:
            # ⚠ AN `_Aux` SET IS THE COMBO/REDIRECT VARIANTS OF POWERS WE
            # ALREADY HOLD, not new content: Rending_Flurry_Normal/Large are the
            # combo-dependent forms of Rending Flurry and Savage_Leap_AoE is
            # Savage Leap's area component. We carry the base power on every
            # archetype (checked, not assumed) and our data folds the variant
            # in - the reconciliation lane's proven redirect class.
            aux_variants[ps] = len(miss)
            continue
        if ps not in our_set_disp:
            # whole set unknown to us: rename, or genuinely absent?
            cd = {(c.get("display_name") or "").lower() for c in leaves.values()}
            cd.discard("")
            best, who = 0.0, None
            for ops, od in our_set_disp.items():
                if not od or not cd:
                    continue
                j = len(cd & od) / len(cd | od)
                if j > best:
                    best, who = j, ops
            if best >= 0.8:
                renamed.append((ps, who, round(best, 2), len(miss)))
                continue
            absent_sets.append((ps, len(miss)))
            continue
        for leaf, c in miss.items():
            dn = (c.get("display_name") or "").lower()
            # ⚠ ORDER IS SEMANTIC: "never pickable" is a stronger statement than
            # "we file it elsewhere", so it is tested first. Note this rule
            # classifies rather than gates - deleting it moves those six powers
            # into the namespace bucket and the verdict does not change, which a
            # sabotage run showed. It earns its place in the REPORT, not in the
            # pass/fail, and saying so beats implying every rule is load-bearing.
            if (c.get("available_level") or 0) == NEVER_PICKABLE:
                unpickable += 1                # auto-issue free riders
                continue
            if dn in our_set_disp[ps]:
                continue                       # renamed inside a set we have
            if dn in our_disp_any:
                ns_diff += 1                   # we file it under another set
                continue
            residue.append((f"{ps}.{leaf}", c.get("display_name")))

    print(f"client powersets checked (player-pickable) : "
          f"{sum(1 for ps in cl_sets if ps.startswith(PICKABLE))}")
    print(f"RENAMED powersets - we hold them under another internal name : "
          f"{len(renamed)}")
    for ps, who, j, n in sorted(renamed):
        print(f"    {ps:<42} = {who}  (display roster {j}, {n} leaves)")
    print(f"NEVER-PICKABLE client powers, absent on purpose  : {unpickable}")
    print(f"NAMESPACE differences (we file them elsewhere)   : {ns_diff}")
    print(f"_Aux combo/redirect variants of powers we hold   : "
          f"{sum(aux_variants.values())} in {len(aux_variants)} sets")

    print("\nGENUINELY ABSENT - real player content the tool cannot plan:")
    found = collections.Counter()
    for ps, n in absent_sets:
        found[ps] = n
    for fn, _dn in residue:
        found[fn] = found.get(fn, 0) + 1
    bad = []
    for key in sorted(ABSENT):
        want, note = ABSENT[key]
        got = found.get(key, 0)
        print(f"{'  ' if got == want else ' !'} {key:<46} {got:>3} (pinned {want})")
        print(f"       {note.splitlines()[0][:96]}")
        if got != want:
            bad.append((key, want, got))
    extra = {k: v for k, v in found.items() if k not in ABSENT}
    if extra:
        print(f"\nUNCLASSIFIED - {len(extra)} absences with no entry:")
        for k, v in sorted(extra.items(), key=lambda x: -x[1])[:25]:
            print(f"  {k:<58} {v}")
        print("\nHARD FAIL: client content we do not carry and have not accounted "
              "for. Add it to ABSENT with its evidence, or explain it as a "
              "rename / namespace difference / never-pickable power.")
        sys.exit(1)
    if bad:
        print("\nHARD FAIL: an ABSENT pin no longer matches reality:")
        for key, want, got in bad:
            print(f"  {key}: pinned {want}, found {got} - "
                  f"{'GREW' if got > want else 'SHRANK or was added'}")
        sys.exit(1)
    if show_all:
        print("\nresidue detail:")
        for fn, dn in sorted(residue):
            print(f"  {fn:<58} {dn}")
    print(f"\nEVERY ABSENCE ACCOUNTED FOR. {len(ABSENT)} pinned, none moved.")


if __name__ == "__main__":
    main()
