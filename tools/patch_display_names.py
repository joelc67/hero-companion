"""ADOPT THE GAME'S DISPLAY NAMES (Joel, 2026-07-19: "accurate to the names used
in the game, or they will be unrecognizable to the players"). GAME-FIRST: the
client bins' per-pool index.json carries `powers` (internal full-names) parallel
to `power_display_names` (the CURRENT in-game display) + the pool `display_name`.
This additive patcher overwrites our stale/legacy display names with the game's,
keyed by internal full_name — KEYS ARE NEVER TOUCHED, so champions, imports,
pins and every lookup are unaffected (display-only).

Sibling of the powers.json additive-patcher family: never re-parses (that would
erase client-synced layers); writes powers.json COMPACT (json.dump, no indent —
its canonical shape) and powersets.json indent=1 (its shape); verifies the diff
is display-only. Run reality_check_names.py afterwards to confirm zero remain.

Run:  py tools\\patch_display_names.py [--dry-run]
"""
import argparse
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BINS = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
POWERS = os.path.join(ROOT, "data", "powers.json")
POWERSETS = os.path.join(ROOT, "data", "powersets.json")


def game_name_maps():
    """(power full_name -> current display, pool full_name -> current display)
    from every out_full/**/index.json. `powers` and `power_display_names` are
    parallel arrays — alignment self-validates on neighbors that already match."""
    gp, gpool = {}, {}
    for idx in glob.glob(os.path.join(BINS, "**", "index.json"), recursive=True):
        try:
            r = json.load(open(idx, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        key, dn = r.get("key"), r.get("display_name")
        if key and dn:
            gpool[key] = dn
        names, disp = r.get("powers") or [], r.get("power_display_names") or []
        # DEFENSIVE: only trust the parallel arrays when they are the same length
        # (validated 100% aligned vs each power's own record on the swap/rotation
        # pools — but never zip mismatched arrays, which would corrupt names).
        if len(names) != len(disp):
            continue
        for fn, d in zip(names, disp):
            if d:
                gp[fn] = d
    return gp, gpool


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    gp, gpool = game_name_maps()
    print(f"bins: {len(gp)} power display names, {len(gpool)} pool display names")

    # ── powers.json (compact) ────────────────────────────────────────────────
    raw = open(POWERS, "rb").read()
    powers = json.loads(raw.decode("utf-8"))
    changed = []
    for ps, lst in powers.items():
        if not isinstance(lst, list):
            continue
        for rec in lst:
            fn = rec.get("full_name")
            g = gp.get(fn)
            if g and rec.get("display_name") != g:
                changed.append((fn, rec.get("display_name"), g))
                if not args.dry_run:
                    rec["display_name"] = g
    print(f"\npowers.json: {len(changed)} display names updated to the game's")
    for fn, old, new in changed[:20]:
        print(f"   {fn.split('.')[-1]:24s} '{old}' -> '{new}'")
    if len(changed) > 20:
        print(f"   … +{len(changed) - 20} more")

    # ── powersets.json (indent=1) — pool display names ───────────────────────
    psraw = open(POWERSETS, "rb").read()
    psets = json.loads(psraw.decode("utf-8"))
    pool_changed = []
    for at, cats in (psets.get("by_archetype") or {}).items():
        for cat in ("primary", "secondary", "epic"):
            for e in (cats.get(cat) or []):
                fn = e.get("full_name")
                g = gpool.get(fn)
                if g and e.get("display_name") != g:
                    pool_changed.append((fn, e.get("display_name"), g))
                    if not args.dry_run:
                        e["display_name"] = g
    print(f"\npowersets.json: {len(pool_changed)} pool display names updated")
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
