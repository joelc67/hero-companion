"""ADOPT THE GAME'S DISPLAY NAMES (Joel, 2026-07-19: "accurate to the names used
in the game, or they will be unrecognizable to the players"; 2026-10-26: "always
compare to actual game, NO guessing"). GAME-FIRST: a Bin Crawler export of the
installed client is the authority (tools/game_names.py). This additive patcher
overwrites our stale/legacy display names with the game's, keyed by internal
full_name — KEYS ARE NEVER TOUCHED, so champions, imports, pins and every
lookup are unaffected (display-only).

Only RENAMES are applied: the game's set no longer shows our name on any power.
An internal-name SWAP (our name still shown by another power in the same game
set — Tactical Arrow's Gymnastics) is reported and left alone, because joining
by the reused internal name would mislabel it.

Sibling of the powers.json additive-patcher family: never re-parses (that would
erase client-synced layers); writes powers.json COMPACT (json.dump, no indent —
its canonical shape) and powersets.json indent=1 (its shape); verifies the diff
is display-only. Run reality_check_names.py afterwards to confirm zero remain.

Run:  py tools\\patch_display_names.py [--export <bin-crawler export dir>] [--dry-run]
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_names as G  # noqa: E402

ROOT = G.ROOT
POWERS = os.path.join(ROOT, "data", "powers.json")
POWERSETS = os.path.join(ROOT, "data", "powersets.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", default=G.DEFAULT_EXPORT, help="Bin Crawler export of the client to follow")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # ── powers.json (compact) ────────────────────────────────────────────────
    raw = open(POWERS, "rb").read()
    powers = json.loads(raw.decode("utf-8"))
    ours = [rec for lst in powers.values() if isinstance(lst, list) for rec in lst]
    gp, gpool, shows, key = G.game_maps(args.export, [r.get("full_name") for r in ours])
    print(f"game export: {args.export}")
    print(f"bins: {len(gp)} power display names, {len(gpool)} set display names")

    changed, swaps = [], []
    for rec in ours:
        kind, shown = G.classify(rec.get("full_name"), rec.get("display_name"), gp, shows, key)
        if kind == "rename":
            changed.append((rec["full_name"], rec.get("display_name"), shown))
            if not args.dry_run:
                rec["display_name"] = shown
        elif kind == "swap":
            swaps.append((rec["full_name"], rec.get("display_name"), shown))
    print(f"\npowers.json: {len(changed)} display names updated to the game's")
    for fn, old, new in changed:
        print(f"   {fn:60s} '{old}' -> '{new}'")
    if swaps:
        print(f"\nleft alone, internal-name swap (our name is still shown in that game set): {len(swaps)}")
        for fn, old, new in swaps:
            print(f"   {fn:60s} ours '{old}', game record under this internal name shows '{new}'")

    # ── powersets.json (indent=1) — set display names ────────────────────────
    psraw = open(POWERSETS, "rb").read()
    psets = json.loads(psraw.decode("utf-8"))
    entries = [e for cats in (psets.get("by_archetype") or {}).values()
               for cat in ("primary", "secondary", "epic") for e in (cats.get(cat) or [])]
    entries += psets.get("pools") or []
    pool_changed = []
    for e in entries:
        g = gpool.get(e.get("full_name"))
        if g and G.norm(e.get("display_name")) != G.norm(g):
            pool_changed.append((e["full_name"], e.get("display_name"), g))
            if not args.dry_run:
                e["display_name"] = g
    print(f"\npowersets.json: {len(pool_changed)} set display names updated")
    for fn, old, new in pool_changed:
        print(f"   {fn:36s} '{old}' -> '{new}'")

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return

    # Write each file matching its ORIGINAL serialisation AND line ending — a
    # display-only edit must never churn the file (write-guard). powers.json is
    # COMPACT+LF; powersets.json is indent=1+CRLF. Detect EOL from the bytes we
    # read so the diff stays exactly the names that changed.
    def _write(path, text, orig):
        data = text.encode("utf-8")
        if b"\r\n" in orig:
            data = data.replace(b"\n", b"\r\n")
        open(path, "wb").write(data)

    _write(POWERS, json.dumps(powers), raw)
    _write(POWERSETS, json.dumps(psets, indent=1), psraw)
    print(f"\nwrote {POWERS} (compact) and {POWERSETS} (indent=1), EOL preserved")


if __name__ == "__main__":
    main()
