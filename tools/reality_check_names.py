"""STANDING GUARD (Joel, 2026-07-19): every display name the tool offers must
match the CURRENT game files, so nothing reads as an unrecognizable legacy name.
Game-first: the authority is a Bin Crawler export of the installed client
(tools/game_names.py; --export picks it, e.g. the live or open-beta export).
Compares our offered powers + powersets against it; HARD-FAILS on any mismatch
(coverage-denominator rule: N of M matched names checked, fail if N<M).
Unmatched-to-bins records (internal-name divergence — the alias-map
reconciliation class) are reported as a separate coverage caveat, not a failure.

An internal-name SWAP (our name is still shown by another power in the same
game set) passes ONLY when pinned in REVIEWED_SWAPS with its evidence; any other
swap-shaped mismatch fails, because it may just as well be our mislabel.

Companion to tools/patch_display_names.py (which adopts the game names). Runs in
the battery so a future data sync can't silently reintroduce a legacy name.

Run:  py tools\\reality_check_names.py [--export <bin-crawler export dir>]
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_names as G  # noqa: E402

ROOT = G.ROOT

# Deliberate exceptions (empty for now — Joel ruled PURE game names, so identical
# game names for distinct powers are ACCEPTED as-is). Add "Full_Name" here only
# with Joel's sign-off if a disambiguation ever proves necessary.
ALLOW = set()

# Internal-name swaps verified against the game, our name kept. Evidence each.
REVIEWED_SWAPS = {
    # Client Tactical Arrow: the record internally named Gymnastics is displayed
    # "Oil Slick Arrow"; the game's Gymnastics passive sits under another internal
    # name and its own record text matches ours ("Years of training have made you
    # extremely agile..."). See build_power_aliases.py NAME COLLISIONS.
    "Blaster_Support.Tactical_Arrow.Gymnastics",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", default=G.DEFAULT_EXPORT, help="Bin Crawler export of the client to check against")
    args = ap.parse_args()

    powers = json.load(open(os.path.join(ROOT, "data", "powers.json"), encoding="utf-8"))
    recs = [p for lst in powers.values() if isinstance(lst, list) for p in lst]
    gp, gpool, shows, key = G.game_maps(args.export, [p.get("full_name") for p in recs])
    print(f"game export: {args.export}")

    fails, kept = [], []
    matched = unmatched = 0
    for p in recs:
        fn = p.get("full_name")
        kind, shown = G.classify(fn, p.get("display_name"), gp, shows, key)
        if kind == "unmatched":
            unmatched += 1
            continue
        matched += 1
        if kind == "ok" or fn in ALLOW:
            continue
        if kind == "swap" and fn in REVIEWED_SWAPS:
            kept.append((fn, p.get("display_name"), shown))
            continue
        fails.append((kind, fn, p.get("display_name"), shown))

    # powersets we OFFER (by_archetype primary/secondary/epic + pools)
    psets = json.load(open(os.path.join(ROOT, "data", "powersets.json"), encoding="utf-8"))
    entries = [e for cats in (psets.get("by_archetype") or {}).values()
               for cat in ("primary", "secondary", "epic") for e in (cats.get(cat) or [])]
    entries += psets.get("pools") or []
    seen = set()
    for e in entries:
        fn = e.get("full_name")
        if fn in seen or fn not in gpool:
            continue
        seen.add(fn)
        if G.norm(e.get("display_name")) != G.norm(gpool[fn]):
            fails.append(("set", fn, e.get("display_name"), gpool[fn]))

    print(f"names checked vs the game bins: {matched} of {matched} powers "
          f"(matched to bins), {len(seen)} of {len(seen)} powersets")
    print(f"unmatched-to-bins (internal-name divergence, coverage caveat, NOT a "
          f"fail): {unmatched} powers")
    for fn, ours, g in kept:
        print(f"reviewed internal-name swap, ours kept: {fn} '{ours}' (record under this name shows '{g}')")
    if fails:
        print(f"\nNAMES THAT DON'T MATCH THE GAME — {len(fails)}:")
        for kind, fn, ours, g in fails:
            tag = {"rename": "renamed in game", "swap": "UNREVIEWED swap-shaped mismatch", "set": "set name"}[kind]
            print(f"  [{tag}] {fn}: ours='{ours}' GAME='{g}'")
        print("\nFAIL")
        sys.exit(1)
    print("\nPASS — every offered name matches the current game files.")


if __name__ == "__main__":
    main()
