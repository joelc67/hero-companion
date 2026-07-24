#!/usr/bin/env python3
"""
patch_power_icons.py - additively fill data/power_icon_map.json from the GAME's
own per-power icon field, for powers that currently resolve to no icon.

Game-first, additive-only (the additive-patcher family rule): it NEVER changes or
removes an existing mapping; it only ADDS entries for app powers that today have
no icon, and only when the game's named icon file ALREADY EXISTS on disk under
static/icons/powers/. Powers whose game icon is NOT yet on disk are reported as
the extraction to-do (feed them to the pigg-wrangler), never guessed at.

Source of truth for the icon NAME: the bin-crawler powers export (game powers.bin
field 22, "icon"), local under tools/gamedata/bin-crawler/out_full (gitignored by
design, like every other game-first source). We match the game icon basename to
the real on-disk filename case-insensitively, and write the EXACT disk basename.

Run:  python tools/patch_power_icons.py           # apply
      python tools/patch_power_icons.py --dry-run # report only
"""
import json, os, sys, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MAP = os.path.join(REPO, "data", "power_icon_map.json")
POWERS = os.path.join(REPO, "data", "powers.json")
ICO = os.path.join(REPO, "static", "icons", "powers")
OUT_FULL = os.path.join(HERE, "gamedata", "bin-crawler", "out_full")


def _norm(ic):
    if not ic:
        return None
    ic = ic.strip()
    for e in (".png", ".tga", ".texture"):
        if ic.lower().endswith(e):
            ic = ic[: -len(e)]
    return ic or None


def game_icons():
    """full_name -> game icon basename, from the local bin-crawler export."""
    out = {}
    for jf in glob.glob(os.path.join(OUT_FULL, "**", "*.json"), recursive=True):
        try:
            d = json.load(open(jf, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        fn, ic = d.get("full_name"), _norm(d.get("icon"))
        if fn and ic:
            out[fn] = ic
    return out


def _resolver(icon_map):
    """Mirror server._power_icon_url: direct map, then most-common same-name icon."""
    byname = collections.defaultdict(collections.Counter)
    for fn, ic in icon_map.items():
        byname[fn.split(".")[-1]][ic] += 1
    byname = {pn: c.most_common(1)[0][0] for pn, c in byname.items()}
    return lambda fn: bool(icon_map.get(fn) or byname.get(fn.split(".")[-1]))


def _write_map(path, mapping):
    """Preserve the file's exact shape: CRLF, one "k": "v" per line, no trailing
    comma, no final newline (binary write so nothing re-encodes the unicode)."""
    lines = ",\r\n".join(f'{json.dumps(k)}: {json.dumps(v)}' for k, v in mapping.items())
    blob = "{\r\n" + lines + "\r\n}"
    with open(path, "wb") as f:
        f.write(blob.encode("utf-8"))


def main():
    dry = "--dry-run" in sys.argv
    icon_map = json.load(open(MAP, encoding="utf-8"))
    powers = json.load(open(POWERS, encoding="utf-8"))
    if not os.path.isdir(OUT_FULL):
        sys.exit(f"game export not found: {OUT_FULL}\n"
                 "This patcher needs the local bin-crawler powers export.")
    disk_ci = {f[:-4].lower(): f[:-4] for f in os.listdir(ICO) if f.lower().endswith(".png")}
    gi = game_icons()
    resolves = _resolver(icon_map)

    app_fns = [p["full_name"] for lst in powers.values() for p in lst]
    unresolved = [fn for fn in app_fns if not resolves(fn)]

    additions, need_extract, no_gamedata = {}, {}, []
    for fn in unresolved:
        g = gi.get(fn)
        if not g:
            no_gamedata.append(fn)
            continue
        hit = disk_ci.get(g.lower())
        if hit:
            additions[fn] = hit
        else:
            need_extract[g] = need_extract.get(g, 0) + 1

    # COVERAGE DENOMINATOR (repo rule): every addition must point at a real file.
    bad = [(fn, b) for fn, b in additions.items() if not os.path.exists(os.path.join(ICO, b + ".png"))]
    if bad:
        sys.exit(f"HARD FAIL: {len(bad)} additions point at a missing file, e.g. {bad[:3]}")

    print(f"app powers:            {len(app_fns)}")
    print(f"unresolved before:     {len(unresolved)}")
    print(f"NEW mappings (on disk):{len(additions)}   <- applied")
    print(f"need pigg extraction:  {sum(need_extract.values())} powers, {len(need_extract)} textures")
    print(f"no game icon name:     {len(no_gamedata)} (inherent/incarnate/etc.)")

    # emit the extraction to-do next to the export, sorted by texture
    todo = os.path.join(HERE, "gamedata", "power_icons_to_extract.txt")
    with open(todo, "w", encoding="utf-8") as f:
        for tex, n in sorted(need_extract.items()):
            f.write(f"{tex}\t{n}\n")
    print(f"extraction to-do:      {todo}")

    if dry:
        print("\n--dry-run: nothing written.")
        return
    if not additions:
        print("\nnothing to add.")
        return

    merged = dict(icon_map)
    merged.update(additions)          # additive: existing entries keep their order/value
    _write_map(MAP, merged)

    # VERIFY byte-parseable and that every original entry survived unchanged.
    back = json.load(open(MAP, encoding="utf-8"))
    assert len(back) == len(merged), f"count drift {len(back)} != {len(merged)}"
    for k, v in icon_map.items():
        assert back.get(k) == v, f"clobbered existing mapping {k}"
    after = _resolver(back)
    cov = sum(1 for fn in app_fns if after(fn))
    print(f"\nwrote {len(back)} entries; app-power coverage now {cov}/{len(app_fns)}. OK.")


if __name__ == "__main__":
    main()
