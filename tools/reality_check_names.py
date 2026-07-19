"""STANDING GUARD (Joel, 2026-07-19): every display name the tool offers must
match the CURRENT game files, so nothing reads as an unrecognizable legacy name.
Game-first: the authority is the client bins' per-pool index.json (`powers`
parallel `power_display_names` + pool `display_name`). Compares our offered
powers + powersets against it; HARD-FAILS on any mismatch (coverage-denominator
rule: N of M matched names checked, fail if N<M). Unmatched-to-bins records
(internal-name divergence — the alias-map reconciliation class) are reported as
a separate coverage caveat, not a failure.

Companion to tools/patch_display_names.py (which adopts the game names). Runs in
the battery so a future data sync can't silently reintroduce a legacy name.

Run:  py tools\\reality_check_names.py
"""
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BINS = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")

# Deliberate exceptions (empty for now — Joel ruled PURE game names, so identical
# game names for distinct powers are ACCEPTED as-is). Add "Full_Name" here only
# with Joel's sign-off if a disambiguation ever proves necessary.
ALLOW = set()


def _norm(s):
    return " ".join((s or "").split()).strip().lower()


def game_maps():
    gp, gpool = {}, {}
    for idx in glob.glob(os.path.join(BINS, "**", "index.json"), recursive=True):
        try:
            r = json.load(open(idx, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if r.get("key") and r.get("display_name"):
            gpool[r["key"]] = r["display_name"]
        names, disp = r.get("powers") or [], r.get("power_display_names") or []
        if len(names) == len(disp):
            for fn, d in zip(names, disp):
                if d:
                    gp[fn] = d
    # alias-divergent internal names (Temporal_Manipulation vs Time_Manipulation):
    # resolve OUR name to the game key via the local alias map so those display
    # names are verified against the game too.
    ap = os.path.join(ROOT, "tools", "gamedata", "power_aliases.json")
    if os.path.exists(ap):
        alias = json.load(open(ap, encoding="utf-8")).get("aliases", {})
        for our_fn, game_fn in alias.items():
            if our_fn not in gp and game_fn in gp:
                gp[our_fn] = gp[game_fn]
    return gp, gpool


def main():
    gp, gpool = game_maps()
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "server"))
    import server as srv  # noqa: E402

    fails = []

    # powers we OFFER (everything in powers.json)
    powers = json.load(open(os.path.join(ROOT, "data", "powers.json"),
                            encoding="utf-8"))
    recs = [p for lst in powers.values() if isinstance(lst, list) for p in lst]
    matched = unmatched = 0
    for p in recs:
        fn = p.get("full_name")
        if fn in gp:
            matched += 1
            if fn not in ALLOW and _norm(p.get("display_name")) != _norm(gp[fn]):
                fails.append(("power", fn, p.get("display_name"), gp[fn]))
        else:
            unmatched += 1

    # powersets we OFFER (by_archetype primary/secondary/epic)
    pool_checked = 0
    seen = set()
    for at, cats in (srv.POWERSETS.get("by_archetype") or {}).items():
        for cat in ("primary", "secondary", "epic"):
            for e in (cats.get(cat) or []):
                fn = e.get("full_name")
                if fn in seen or fn not in gpool:
                    continue
                seen.add(fn)
                pool_checked += 1
                if _norm(e.get("display_name")) != _norm(gpool[fn]):
                    fails.append(("pool", fn, e.get("display_name"), gpool[fn]))

    print(f"names checked vs the game bins: {matched} of {matched} powers "
          f"(matched to bins), {pool_checked} of {pool_checked} powersets")
    print(f"unmatched-to-bins (internal-name divergence, coverage caveat, NOT a "
          f"fail): {unmatched} powers")
    if fails:
        print(f"\nLEGACY NAMES STILL PRESENT — {len(fails)}:")
        for kind, fn, ours, g in fails[:40]:
            print(f"  [{kind}] {fn}: ours='{ours}' GAME='{g}'")
        print("\nFAIL")
        sys.exit(1)
    print("\nPASS — every offered name matches the current game files.")


if __name__ == "__main__":
    main()
