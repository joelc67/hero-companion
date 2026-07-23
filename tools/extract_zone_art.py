"""Extract the game's own zone map art for the Leveling Journey.

GAME-FIRST, and the join is the safe direction throughout:

  bin/map.bin pairs every zone's map file with a named .tga asset —
  ``maps/City_Zones/City_01_01/City_01_01.txt`` → ``City_01_01_Atlas_Park.tga``.
  That gives a code ↔ name table straight from the client.

  ⚠ Those asset names are DEV-ERA and sometimes historical: Hazard_02_01 is
  named "Baumton" (now Boomtown) and City_02_05 is "Overbrook" (now Faultline).
  So the names are used only to FIND the art for a zone we already name from
  elsewhere — never to rename a zone. Same rule as the badge zone keys: matching
  a name we have TO an asset is safe, generating a display name FROM one is not.

The shipped art is ``texture_library/maps/static/map_<code>.texture`` (and the
v_maps equivalents for the Rogue Isles). Anything without a texture in the
client simply has no art, and the Journey says so rather than showing a picture
of the wrong place.

Run:  python tools/extract_zone_art.py
Out:  static/zone_art/<slug>.jpg  +  data/zone_art.json
"""
from __future__ import annotations

import json
import os
import re
import sys

REPO = os.path.dirname(os.path.abspath(os.path.join(__file__, "..")))
WRANGLER = os.path.join(REPO, "tools", "gamedata", "pigg-wrangler")
sys.path.insert(0, WRANGLER)

from pigg_wrangler.pigg import PiggCollection  # noqa: E402
from pigg_wrangler import texture as tx  # noqa: E402

# TWO asset sets ship with the install, and the order matters. `live` is what the
# game runs today and wins wherever it has the art. `issue24` is the archived i24
# set the launcher also keeps — and it holds the zone maps `live` no longer
# carries (Kings Row, Steel Canyon, The Hollows, Cap au Diable, and 20 more).
# Live-first means a revamped zone shows its current map, never a stale one.
ASSET_SETS = [("live", r"C:\Games\HC2\assets\live"),
              ("issue24", r"C:\Games\HC2\assets\issue24")]
ASSETS = ASSET_SETS[0][1]
OUT_IMG = os.path.join(REPO, "static", "zone_art")
OUT_JSON = os.path.join(REPO, "data", "zone_art.json")


def zone_pairs(col: PiggCollection) -> list[tuple[str, str]]:
    """(zone code, asset name) from bin/map.bin, in file order."""
    data = col.extract("bin/map.bin")
    out, cur = [], None
    for raw in re.findall(rb"[ -~]{4,}", data):
        s = raw.decode()
        if s.lower().startswith("maps/"):
            m = re.search(r"/([^/]+)\.txt$", s)
            cur = m.group(1) if m else None
        elif s.lower().endswith(".tga") and cur:
            out.append((cur, s[:-4]))
            cur = None
    return out


def art_name(code: str, asset: str) -> str:
    """The zone name carried by the asset, with the code prefix stripped.

    'City_01_01_Atlas_Park' → 'Atlas Park'. Historical names come through as
    they are (Baumton, Overbrook) — the caller decides what to trust.
    """
    tail = asset[len(code):].lstrip("_") if asset.lower().startswith(code.lower()) else asset
    tail = re.sub(r"^(city|hazard|trial|v_city|v_pvp|coop|war|p_city)_\d\d_\d\d_?", "", tail, flags=re.I)
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", tail.replace("_", " ")).strip()


def find_splash(col: PiggCollection, code: str) -> str | None:
    """The loading-screen SPLASH plate for a zone (the recognizable comic-panel
    art — City Hall, the Atlas statue). Joel's call: the flat top-down map is
    unreadable at thumbnail size; the splash reads at a glance."""
    want = f"{code.lower()}.texture"
    for p in col.list_paths():
        low = p.lower()
        if ("loading_screen" in low and "city_zones/" in low
                and "#base" not in low and low.rsplit("/", 1)[-1] == want):
            return p
    return None


def find_map(col: PiggCollection, code: str) -> str | None:
    """The top-down street map — fallback only, for zones with no splash."""
    cl = code.lower()
    want = f"map_{cl}.texture"
    for p in col.list_paths():
        low = p.lower()
        if low.endswith(".texture") and "maps/" in low and low.rsplit("/", 1)[-1] == want:
            return p
    for p in col.list_paths():
        low = p.lower()
        if low.endswith(".texture") and "maps/" in low and low.rsplit("/", 1)[-1].startswith(cl):
            return p
    return None


# A zone map is a picture of a place. Some entries under maps/ are 28x21 UI
# icons — they are not art and must not ship as if they were.
MIN_SIDE = 128

# These ship inside the installer, so they get sized for the 230px slot they are
# actually displayed in rather than at source resolution: 38 zone maps came to
# 20 MB as extracted, which is not a reasonable thing to put in a download for a
# thumbnail. 640px longest side, JPEG q82 — still sharp at 2x the slot width.
SHIP_MAX_SIDE = 640
SHIP_QUALITY = 82


def _fit_for_shipping(img: bytes, ext: str) -> tuple[bytes, str]:
    try:
        import io
        from PIL import Image
    except ImportError:  # Pillow absent — ship the source image unchanged
        return img, ext
    im = Image.open(io.BytesIO(img))
    if max(im.size) > SHIP_MAX_SIDE:
        scale = SHIP_MAX_SIDE / max(im.size)
        im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))),
                       Image.LANCZOS)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=SHIP_QUALITY, optimize=True)
    return buf.getvalue(), "jpg"


def main() -> int:
    if not os.path.isdir(ASSETS):
        print(f"game assets not found at {ASSETS} — nothing extracted")
        return 1
    os.makedirs(OUT_IMG, exist_ok=True)
    cols = [(label, PiggCollection(d)) for label, d in ASSET_SETS if os.path.isdir(d)]
    print("asset sets: " + ", ".join(f"{lab} ({len(c.list_paths())} entries)" for lab, c in cols))
    pairs = zone_pairs(cols[0][1])
    print(f"map.bin: {len(pairs)} zone code/name pairs")

    rows, missing = [], []
    for code, asset in pairs:
        name = art_name(code, asset)
        # SPLASH first across BOTH asset sets, THEN the map across both. Splash
        # beats map everywhere — so a zone whose splash is only in i24 uses it
        # rather than falling to live's top-down map. Within a kind, live wins
        # (current art). A result under MIN_SIDE is a UI icon, not real art.
        found = None
        for finder in (find_splash, find_map):
            for label, col in cols:
                path = finder(col, code)
                if not path:
                    continue
                data = col.extract(path)
                info = tx.get_texture_info(data)
                if min(info.get("width") or 0, info.get("height") or 0) < MIN_SIDE:
                    continue
                found = (label, col, path, data, info)
                break
            if found:
                break
        if not found:
            missing.append((code, name))
            continue
        label, col, path, data, info = found
        img, mime = tx.texture_to_image(data)   # mime, e.g. "image/png"
        ext = "png" if "png" in mime else "jpg"
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or code.lower()
        img, ext = _fit_for_shipping(img, ext)
        fn = f"{slug}.{ext}"
        with open(os.path.join(OUT_IMG, fn), "wb") as f:
            f.write(img)
        rows.append({"code": code, "asset_name": name, "file": fn,
                     "w": info.get("width"), "h": info.get("height"),
                     "bytes": len(img), "source": path, "asset_set": label})
        print(f"  {code:16s} {name:24s} {info.get('width')}x{info.get('height')}"
              f"  {len(img)//1024:5d} KB  [{label}]  {fn}")

    # COVERAGE DENOMINATOR (standing rule): say what was NOT found, always.
    print(f"\nextracted {len(rows)} of {len(pairs)} zones; {len(missing)} have no map texture in the client:")
    for code, name in missing:
        print(f"  - {code} ({name})")

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "_source": "bin/map.bin (zone code ↔ asset name) + texture_library/maps/*.texture, "
                       "extracted from the game client by tools/extract_zone_art.py",
            "_note": "asset_name is the DEV-ERA name from the .tga and is sometimes historical "
                     "(Baumton = Boomtown, Overbrook = Faultline). Match a zone name you already "
                     "have TO these entries; never read a display name OUT of them.",
            "_coverage": {"zones_in_map_bin": len(pairs), "with_art": len(rows),
                          "without_art": [c for c, _ in missing]},
            "zones": rows,
        }, f, indent=2)
    print(f"\nwrote {OUT_JSON} and {len(rows)} images to {OUT_IMG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
