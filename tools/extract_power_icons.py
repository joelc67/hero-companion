#!/usr/bin/env python3
"""
extract_power_icons.py - pull the power icons the game NAMES but that aren't yet
bundled, straight from the client texture piggs, and drop them into
static/icons/powers/ so patch_power_icons.py can map them.

Companion to patch_power_icons.py. That patcher maps app powers to icons ALREADY
on disk; this fills the on-disk gap first. Workflow:
    python tools/extract_power_icons.py     # writes the missing PNGs
    python tools/patch_power_icons.py       # maps them into power_icon_map.json

Game-first: the icon NAME is the game's own per-power field (bin-crawler powers
export), and the image is the game's own texture (texture_gui.pigg, path
texture_library/gui/icons/powers/<name>.texture), decoded via the pigg-wrangler
(texture -> DDS -> RGBA -> 32x32 PNG, the native icon size). Never invents or
recolors anything; a texture the piggs don't hold is reported, not faked.
"""
import json, os, sys, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
GAMEDATA = os.path.join(HERE, "gamedata")
WRANGLER = os.path.join(GAMEDATA, "pigg-wrangler")
OUT_FULL = os.path.join(GAMEDATA, "bin-crawler", "out_full")
ICO = os.path.join(REPO, "static", "icons", "powers")
MAP = os.path.join(REPO, "data", "power_icon_map.json")
POWERS = os.path.join(REPO, "data", "powers.json")

# Icons the game ships live here; other texture piggs are searched as a fallback.
PIGG_DIRS = [r"C:\Games\HC2\assets\live", r"C:\Games\HC2\assets\issue24"]
ICON_PREFIX = "texture_library/gui/icons/powers/"

sys.path.insert(0, WRANGLER)
from pigg_wrangler.pigg import PiggArchive          # noqa: E402
from pigg_wrangler import texture as T              # noqa: E402
from PIL import Image                               # noqa: E402


def _norm(ic):
    if not ic:
        return None
    ic = ic.strip()
    for e in (".png", ".tga", ".texture"):
        if ic.lower().endswith(e):
            ic = ic[: -len(e)]
    return ic or None


def game_icons():
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
    byname = collections.defaultdict(collections.Counter)
    for fn, ic in icon_map.items():
        byname[fn.split(".")[-1]][ic] += 1
    byname = {pn: c.most_common(1)[0][0] for pn, c in byname.items()}
    return lambda fn: bool(icon_map.get(fn) or byname.get(fn.split(".")[-1]))


def build_texture_index():
    """lowercase icon basename -> (archive, path) for every power-icon texture."""
    idx = {}
    for d in PIGG_DIRS:
        for pigg in sorted(glob.glob(os.path.join(d, "texture_*.pigg"))):
            try:
                a = PiggArchive(pigg)
            except Exception:  # noqa: BLE001
                continue
            for p in a.list_paths():
                pl = p.lower()
                if ICON_PREFIX in pl and pl.endswith(".texture"):
                    base = os.path.basename(pl)[: -len(".texture")]
                    idx.setdefault(base, (a, p))   # first pigg wins (live before issue24)
    return idx


def main():
    icon_map = json.load(open(MAP, encoding="utf-8"))
    powers = json.load(open(POWERS, encoding="utf-8"))
    disk_ci = {f[:-4].lower() for f in os.listdir(ICO) if f.lower().endswith(".png")}
    gi = game_icons()
    resolves = _resolver(icon_map)

    # texture names the app needs but that aren't on disk
    want = {}
    for lst in powers.values():
        for p in lst:
            fn = p["full_name"]
            if resolves(fn):
                continue
            g = gi.get(fn)
            if g and g.lower() not in disk_ci:
                want[g.lower()] = g
    print(f"textures needed (not on disk): {len(want)}")

    idx = build_texture_index()
    print(f"power-icon textures found in piggs: {len(idx)}")

    got, missing = 0, []
    for base, orig in sorted(want.items()):
        hit = idx.get(base)
        if not hit:
            missing.append(base)
            continue
        arch, path = hit
        try:
            dds = T.texture_to_dds(arch.extract(path))
            rgba, w, h, _ = T.decode_dds_to_rgba(dds)
            out = os.path.join(ICO, orig + ".png")
            Image.frombytes("RGBA", (w, h), rgba).save(out)
            got += 1
        except Exception as e:  # noqa: BLE001
            missing.append(f"{base} (decode error: {e})")

    print(f"\nextracted: {got} PNG(s) into {ICO}")
    print(f"not in piggs: {len(missing)}")
    if missing:
        for m in missing[:40]:
            print("  -", m)
        if len(missing) > 40:
            print(f"  ... and {len(missing) - 40} more")
    print("\nNow run: python tools/patch_power_icons.py   (to map the new files)")


if __name__ == "__main__":
    main()
