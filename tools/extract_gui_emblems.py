#!/usr/bin/env python3
"""
extract_gui_emblems.py - pull the game's ARCHETYPE and ORIGIN emblems out of the
client texture archives into static/icons/at/ and static/icons/origin/.

Companion to extract_power_icons.py, same pipeline (texture -> DDS -> RGBA ->
PNG via the pigg-wrangler), same rule: never invents or recolors anything, and a
texture the archives do not hold is REPORTED, not faked.

Why this exists: the app names every archetype and origin in plain text, while
the game's own emblems for them sit unextracted on disk.

⚠ THE ART IS SPLIT ACROSS TWO ASSET SETS, AND THAT IS THE WHOLE TRICK:
  - the live Homecoming piggs (texture_*.pigg) hold ONLY the archetypes
    Homecoming added - Sentinel and Guardian - plus all five origin plates;
  - the 14 CLASSIC archetypes are original-game art and live in the i24
    archive, which names its archives tex*.pigg / stage*.pigg, NOT
    texture_*.pigg.
A glob for texture_*.pigg matches ZERO files in the i24 set, which is why a
first sweep of the live piggs finds 2 archetype icons and concludes, wrongly,
that the classic emblems do not exist. They do - 14 of them in stage1b.pigg.
⚠ extract_power_icons.py has exactly this glob bug: it lists the i24 dir in
PIGG_DIRS but globs texture_*.pigg, so its documented i24 fallback has never
actually searched that set.

Villain-side archetypes carry a `v_` prefix in the game's own naming
(v_archetypeicon_brute); hero-side do not. We normalise that away - the app
keys on the archetype, and which side it belongs to is already known.

Usage:  python tools/extract_gui_emblems.py [--dry-run]
"""
import os, sys, glob, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
WRANGLER = os.path.join(HERE, "gamedata", "pigg-wrangler")

OUT_AT = os.path.join(REPO, "static", "icons", "at")
OUT_ORIGIN = os.path.join(REPO, "static", "icons", "origin")
OUT_AT_ART = os.path.join(REPO, "static", "icons", "at_art")

# BOTH naming conventions, because the two asset sets disagree (see the header).
PIGG_GLOBS = [
    os.path.join(r"C:\Games\HC2\assets\live", "*.pigg"),
    os.path.join(r"C:\Games\HC2\assets\issue24", "*.pigg"),
]

AT_DIR = "gui/icons/archetype/"
# ⚠ The 32x32 icons are ICONS. The character-creation screen carries the real
# 512x512 ARTWORK for every archetype, three shots each (2026-08-06). Shot 0 is
# the one extracted: 16 files instead of 48, and the app only needs one.
AT_ART_DIR = "charectercreationui/archetypescreenshotsassets"
ORIGIN_DIR = "gui/creation/origin/"

# The full roster we EXPECT, so the run can state its own denominator and fail
# loudly rather than quietly shipping a partial set (coverage-denominator rule).
EXPECT_AT = {
    "blaster", "controller", "defender", "scrapper", "tanker",
    "peacebringer", "warshade", "brute", "corruptor", "dominator",
    "mastermind", "stalker", "arachnos_soldier", "arachnos_widow",
    "sentinel", "guardian",
}
EXPECT_ORIGIN = {"magic", "mutation", "natural", "science", "technology"}

sys.path.insert(0, WRANGLER)
from pigg_wrangler.pigg import PiggArchive          # noqa: E402
from pigg_wrangler import texture as T              # noqa: E402
from PIL import Image                               # noqa: E402


def _at_key(base):
    """archetypeicon_blaster / v_archetypeicon_brute -> blaster / brute"""
    b = base
    if b.startswith("v_"):
        b = b[2:]
    if b.startswith("archetypeicon_"):
        b = b[len("archetypeicon_"):]
    return b or None


def _origin_key(base):
    """origin_title_magic -> magic"""
    return base[len("origin_title_"):] if base.startswith("origin_title_") else None


def index():
    """key -> (archive, path) for archetype and origin emblems, first win."""
    ats, origins, art = {}, {}, {}
    archives = 0
    for pattern in PIGG_GLOBS:
        for pigg in sorted(glob.glob(pattern)):
            try:
                a = PiggArchive(pigg)
                paths = list(a.list_paths())
            except Exception:  # noqa: BLE001
                continue
            archives += 1
            for p in paths:
                pl = p.lower()
                if not pl.endswith(".texture"):
                    continue
                base = os.path.basename(pl)[: -len(".texture")]
                if AT_DIR in pl:
                    k = _at_key(base)
                    if k:
                        ats.setdefault(k, (a, p))
                elif ORIGIN_DIR in pl:
                    k = _origin_key(base)
                    if k:
                        origins.setdefault(k, (a, p))
                elif AT_ART_DIR in pl and base.endswith("_0"):
                    k = base[len("archetypeshots_"):-2]                         if base.startswith("archetypeshots_") else None
                    if k:
                        art.setdefault(k, (a, p))
    return ats, origins, art, archives


def _crop_pad(img):
    """The archetype shots are a ~512x310 picture padded to a power of two with
    a flat block underneath (seen on screen: `contain` fitted the PAD too and put
    a blue slab under the art). Crop to the picture: the pad is the run of rows
    at the bottom that all match the bottom-left pixel."""
    w, h = img.size
    px = img.convert("RGBA").load()
    pad = px[w // 2, h - 2]
    def is_pad(y):
        hit = 0
        for x in range(0, w, 4):
            c = px[x, y]
            if c[3] < 8 or max(abs(c[i] - pad[i]) for i in range(3)) <= 12:
                hit += 1
        return hit >= (w // 4) * 0.97
    bot = h
    while bot > 1 and is_pad(bot - 1):
        bot -= 1
    # ⚠ The detector gets 11 of 15; three shots have a pad the sampler cannot
    # separate from the picture's own dark sky. Every 512-tall shot measured is a
    # 314-row picture, so that is the fallback — a padded texture NEVER survives
    # uncropped, which is the failure that put a blue slab on screen.
    if not (0 < bot < h):
        bot = 314 if h >= 400 else h
    return img.crop((0, 0, w, bot)) if bot < h else img


def save(entry, dest, size, crop=False):
    """texture -> DDS -> RGBA -> PNG, alpha preserved. Same path as the power
    icons: archive.extract -> texture_to_dds -> decode_dds_to_rgba."""
    archive, path = entry
    dds = T.texture_to_dds(archive.extract(path))
    rgba, w, h, _ = T.decode_dds_to_rgba(dds)
    img = Image.frombytes("RGBA", (w, h), rgba)
    if crop:
        img = _crop_pad(img)
    if size and img.size != (size, size):
        img = img.resize((size, size), Image.LANCZOS)
    img.save(dest, "PNG")
    return True


def main():
    dry = "--dry-run" in sys.argv
    ats, origins, art, archives = index()
    print(f"searched {archives} pigg archives")
    print(f"found {len(ats)} archetype emblems, {len(origins)} origin plates\n")

    missing_at = sorted(EXPECT_AT - set(ats))
    missing_or = sorted(EXPECT_ORIGIN - set(origins))
    extra_at = sorted(set(ats) - EXPECT_AT)

    for d in (OUT_AT, OUT_ORIGIN, OUT_AT_ART):
        if not dry:
            os.makedirs(d, exist_ok=True)

    wrote = collections.Counter()
    failed = []
    for key, entry in sorted(ats.items()):
        dest = os.path.join(OUT_AT, f"{key}.png")
        if dry:
            print(f"  [dry] at/{key}.png  <- {entry[1]}")
            continue
        try:
            save(entry, dest, 32)
            wrote["at"] += 1
        except Exception as e:  # noqa: BLE001
            failed.append(f"at/{key}: {e}")
    for key, entry in sorted(origins.items()):
        dest = os.path.join(OUT_ORIGIN, f"{key}.png")
        if dry:
            print(f"  [dry] origin/{key}.png  <- {entry[1]}")
            continue
        try:
            save(entry, dest, None)   # origin plates are not square icons
            wrote["origin"] += 1
        except Exception as e:  # noqa: BLE001
            failed.append(f"origin/{key}: {e}")

    for key, entry in sorted(art.items()):
        dest = os.path.join(OUT_AT_ART, f"{key}.png")
        if dry:
            print(f"  [dry] at_art/{key}.png  <- {entry[1]}")
            continue
        try:
            save(entry, dest, None, crop=True)   # picture only, pad cropped off
            wrote["at_art"] += 1
        except Exception as e:  # noqa: BLE001
            failed.append(f"at_art/{key}: {e}")

    missing_art = sorted(EXPECT_AT - set(art))
    if dry:
        # ⚠ Never print a success line after writing nothing - a dry run that
        # says "ALL EXTRACTED" is the same defect class as a fake progress bar.
        print(f"\n[dry run] resolved {len(ats)} of {len(EXPECT_AT)} archetype emblems"
              f" and {len(origins)} of {len(EXPECT_ORIGIN)} origin plates. Nothing written.")
        return 0 if not (missing_at or missing_or) else 1

    print(f"\nwrote {wrote['at']} of {len(EXPECT_AT)} expected archetype emblems")
    print(f"wrote {wrote['origin']} of {len(EXPECT_ORIGIN)} expected origin plates")
    print(f"wrote {wrote['at_art']} of {len(EXPECT_AT)} expected archetype artworks")
    if missing_art:
        print(f"note: no artwork for {missing_art}")
    if extra_at:
        print(f"note: {len(extra_at)} archetype emblems beyond the expected roster: {extra_at}")
    if failed:
        print("\nDECODE FAILURES:")
        for f in failed:
            print("  " + f)
    if missing_at or missing_or:
        print("\nMISSING (reported, never faked):")
        for m in missing_at:
            print(f"  archetype: {m}")
        for m in missing_or:
            print(f"  origin: {m}")
        return 1
    if failed:
        return 1
    print("\nALL EXPECTED EMBLEMS EXTRACTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
