"""Read the Homecoming wiki's zone pages for the Journey's level-fit layer.

WHY THIS EXISTS, and why it is not the wiki-bridge Joel closed:

  The closed bridge is about GAME NUMBERS the client can answer — those come
  from the bins, always. This fetches exactly the class the client does NOT
  contain and that was searched to the bottom on 2026-07-22: zone level ranges,
  neighbourhood names, their level bands, and the Yellow/Orange/Red difficulty
  marks. Joel asked for this directly ("You sure you cannot scrape these
  pages?"). Everything it writes is labelled wiki-sourced on the surface and is
  never blended into the game-first data.

WHY IT RUNS HERE AND NOT THROUGH THE ASSISTANT'S FETCHER:
  homecoming.wiki returns 403 to Anthropic's fetcher (datacenter IP) on the
  article URL, the api.php endpoint and action=raw alike. From Joel's own
  machine with an ordinary browser user-agent it returns 200. So this is a
  local tool, run on his box, at his request.

MANNERS: one request per second, a real user-agent, and an on-disk cache so a
re-run never re-fetches a page it already has. Be a good guest.

VERIFY AFTER RUNNING: tools/verify_zone_pages.py checks every badge each page
lists against badges.bin from the live client. A page whose badges are absent
describes content that no longer exists and must not ship.

    python tools/fetch_zone_pages.py            # the standing zone list
    python tools/fetch_zone_pages.py Croatoa Eden --force
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "data", "zone_pages.json")
CACHE = os.path.join(REPO, "tools", "gamedata", "_wiki_cache")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
DELAY = 1.0

# Every zone a levelling character might be pointed at. Titles are the wiki's
# own page names; a title that 404s is reported, never silently skipped.
ZONES = [
    # Paragon core
    "Atlas_Park", "Galaxy_City", "Kings_Row", "Steel_Canyon", "Skyway_City",
    "The_Hollows", "Perez_Park", "Boomtown", "Faultline", "Independence_Port",
    "Talos_Island", "Striga_Isle", "Croatoa", "Founders'_Falls", "Brickstown",
    "Crey's_Folly", "Terra_Volta", "Eden", "The_Hive", "Peregrine_Island",
    "Dark_Astoria", "Kallisti_Wharf", "Rikti_War_Zone", "Cimerora", "Ouroboros",
    "First_Ward", "Night_Ward",
    # Rogue Isles
    "Mercy_Island", "Port_Oakes", "Cap_au_Diable", "Sharkhead_Isle",
    "Nerva_Archipelago", "St._Martial", "Grandville", "Monster_Island", "The_Abyss",
    # PvP
    "Bloody_Bay", "Siren's_Call", "Warburg", "Recluse's_Victory",
    # Praetoria
    "Nova_Praetoria", "Imperial_City", "Neutropolis",
    # Shadow Shard
    "Firebase_Zulu", "Cascade_Archipelago", "The_Chantry", "Storm_Palace",
]

_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t ]+")


def _text(fragment: str) -> str:
    fragment = re.sub(r"(?is)<(script|style).*?</\1>", "", fragment)
    fragment = re.sub(r"(?i)<(br|/p|/li|/tr|/h[1-6]|/div)[^>]*>", "\n", fragment)
    return _WS.sub(" ", html.unescape(_TAGS.sub("", fragment))).strip()


def fetch(title: str, force: bool = False) -> str | None:
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9_.-]", "_", title) + ".html")
    if os.path.exists(path) and not force:
        with open(path, encoding="utf-8") as f:
            return f.read()
    url = "https://homecoming.wiki/wiki/" + urllib.parse.quote(title)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 — a dead page is data, not a crash
        print(f"  ! {title}: {type(e).__name__} {str(e)[:70]}")
        return None
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    time.sleep(DELAY)
    return body


# "Hero City Zone (1-6)" / "PvP Zone (25)" / "Co-op Trial Zone (45-50)"
_KIND = re.compile(
    r"((?:Hero|Villain|Co-?op|Cooperative|Praetorian|PvP)[A-Za-z \-]*?Zone)\s*"
    r"\(\s*(\d+)\s*(?:[-–—]\s*(\d+))?\s*\)", re.I)
# "Atlas Plaza (Green - Level 1-2)" — the level part is optional (safe havens)
_HOOD = re.compile(
    r"^(.{2,80}?)\s*\(\s*(Green|Yellow|Orange|Red|Purple|Blue)\s*"
    r"(?:[-–—]\s*(?:Level\s*)?(\d+)?\s*(?:[-–—]\s*(\d+))?)?([^)]*)\)", re.I)


def parse(body: str, title: str) -> dict:
    out: dict = {"zone": title.replace("_", " ").replace("'", "'"), "wiki_title": title}
    plain = _text(body)
    m = _KIND.search(plain)
    if m:
        out["kind"] = re.sub(r"\s+", " ", m.group(1)).strip()
        out["from"] = int(m.group(2))
        out["to"] = int(m.group(3)) if m.group(3) else int(m.group(2))

    # The Neighborhoods section: from its heading to the next h2.
    sec = re.search(r'(?is)id="Neighborhoods".*?(<ul.*?)(?=<h2)', body)
    hoods, havens = [], []
    if sec:
        for li in re.findall(r"(?is)<li>(.*?)</li>", sec.group(1)):
            t = _text(li)
            t = re.sub(r"\((?:Music|unknown|Interior Music)\)", "", t, flags=re.I).strip()
            t = re.sub(r"\s*\(\s*\)\s*$", "", t).strip()
            if not t:
                continue
            h = _HOOD.match(t)
            if not h:
                continue
            name, risk = h.group(1).strip(" .,-"), h.group(2).title()
            lo, hi, extra = h.group(3), h.group(4), (h.group(5) or "").strip()
            if lo:
                hoods.append({"name": name, "risk": risk, "from": int(lo),
                              "to": int(hi) if hi else int(lo),
                              **({"extra": extra} if extra else {})})
            else:
                # Green with no band = a safe area (medical centres, bases).
                havens.append(name)
    out["neighborhoods"] = hoods
    if havens:
        out["safe_havens"] = havens

    def row(label: str):
        r = re.search(rf"(?im)^\s*{re.escape(label)}:\s*(.+)$", plain)
        if not r:
            return None
        v = r.group(1).strip()
        return None if v.lower() in ("none", "n/a", "") else v

    for key, label in (("exploration_badges", "Exploration Badges"),
                       ("enemies", "Enemies"), ("events", "Events"),
                       ("tf_contacts", "Trial / TF Contacts"),
                       ("connecting", "Connecting Zones"), ("transits", "Transits")):
        v = row(label)
        if v:
            out[key] = [s.strip() for s in v.split(",") if s.strip()] \
                if key in ("exploration_badges", "enemies", "connecting") else v
    out["url"] = "https://homecoming.wiki/wiki/" + title
    return out


def main(argv: list[str]) -> int:
    force = "--force" in argv
    wanted = [a for a in argv if not a.startswith("--")] or ZONES
    print(f"fetching {len(wanted)} zone pages (cache: {CACHE})")
    rows, failed, no_bands = [], [], []
    for t in wanted:
        body = fetch(t, force)
        if not body:
            failed.append(t)
            continue
        z = parse(body, t)
        rows.append(z)
        if not z.get("neighborhoods"):
            no_bands.append(t)
        print(f"  {z['zone']:24s} {z.get('kind','?'):24s} "
              f"{z.get('from','?')}-{z.get('to','?')}  "
              f"{len(z.get('neighborhoods', []))} bands")

    # COVERAGE DENOMINATOR (standing rule): state what did NOT come back.
    print(f"\n{len(rows)} of {len(wanted)} pages parsed")
    if failed:
        print(f"  FAILED ({len(failed)}): {', '.join(failed)}")
    if no_bands:
        print(f"  no neighbourhood bands on the page ({len(no_bands)}): {', '.join(no_bands)}")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({
            "_source": "homecoming.wiki zone pages, fetched by tools/fetch_zone_pages.py",
            "_why": "zone level ranges, neighbourhood bands and difficulty marks — the one "
                    "content class absent from every client bin (searched 2026-07-22).",
            "_provenance_label": "homecoming.wiki",
            "_verify_with": "tools/verify_zone_pages.py — every listed badge must exist in badges.bin",
            "_coverage": {"requested": len(wanted), "parsed": len(rows),
                          "failed": failed, "no_bands": no_bands},
            "zones": rows,
        }, f, indent=2, ensure_ascii=False)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
