"""Build the Journey badge dataset (data/journey_badges.json) from the
Bin Crawler badge export.

Source: tools/gamedata/bin-crawler/exported_powers/badges.json (gitignored,
regenerated via `py -3 -m bin_crawler.export_badges` from the local client
piggs — see PATCH-WATCH). This tool is the committed half: it reshapes the
raw catalog into what the Journey band renders and prints its coverage
denominator per the coverage-denominator rule.

What ships per badge: internal name, id, category, hero/villain display +
description + earn hint, requirement count. Exploration (tourism) badges are
additionally grouped by their structural `<Zone>Tour<N>` name convention
(390 of 476 follow it — measured 2026-07-22; the rest group under "other").

DELIBERATELY ABSENT (honesty tier, awaiting Joel's ruling on the
server-side-data families): zone display names for the zone keys (the
prefix->English map is not in the client bins), zone level ranges, badge
coordinates. The zone_key is the raw name prefix; the band labels the
level-fit column as pending until the ruling lands.

Usage:  py -3 tools\build_journey_badges.py
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "tools" / "gamedata" / "bin-crawler" / "exported_powers" / "badges.json"
OUT = REPO / "data" / "journey_badges.json"

# Categories the Journey band renders. Internal/none/contact-intro records
# (display "." placeholders, tutorial plumbing) are catalog noise for players.
JOURNEY_CATEGORIES = {
    "tourism", "history", "accomplishment", "achievement", "perk",
    "veteran", "pvp", "invention", "defeat", "event", "flashback",
    "auction", "dayjob", "architect", "gladiator",
}

_ZONE_TOUR = re.compile(r"^(?:P_)?([A-Za-z_]+?)Tour(?:ism)?\d*$")


def main():
    if not SRC.is_file():
        sys.exit(f"Missing {SRC} — run `py -3 -m bin_crawler.export_badges` first.")

    raw = json.loads(SRC.read_text(encoding="utf-8"))["badges"]

    expected_total = len(raw)  # denominator from the export itself
    kept = []
    skipped_hidden = 0
    for b in raw:
        if b["category"] not in JOURNEY_CATEGORIES:
            continue
        if not b["display_hero"] and not b["display_villain"]:
            skipped_hidden += 1
            continue
        entry = {
            "name": b["name"],
            "id": b["id"],
            "category": b["category"],
            "display_hero": b["display_hero"],
            "display_villain": b["display_villain"],
            "desc_hero": b["desc_hero"],
            "desc_villain": b["desc_villain"],
            "earn_hint_hero": b["earn_hint_hero"],
            "earn_hint_villain": b["earn_hint_villain"],
            "requires_count": b["requires_count"],
        }
        if b["category"] == "tourism":
            m = _ZONE_TOUR.match(b["name"])
            entry["zone_key"] = m.group(1) if m else "other"
        kept.append(entry)

    zone_counts = Counter(e["zone_key"] for e in kept if "zone_key" in e)
    by_cat = Counter(e["category"] for e in kept)

    checked = len(kept) + skipped_hidden + sum(
        1 for b in raw if b["category"] not in JOURNEY_CATEGORIES)
    print(f"{checked} of {expected_total} expected badges checked")
    if checked != expected_total:
        sys.exit("COVERAGE FAIL: some export records were neither kept nor "
                 "explicitly skipped — fix the filter before shipping.")

    print(f"kept {len(kept)} ({dict(by_cat.most_common())}); "
          f"skipped {skipped_hidden} hidden/placeholder")
    print(f"tourism zone keys: {len(zone_counts)} "
          f"({sum(v for k, v in zone_counts.items() if k != 'other')} zone-grouped, "
          f"{zone_counts.get('other', 0)} other)")

    out = {
        "_source": "badges.bin via bin_crawler.export_badges",
        "_note": ("zone_key is the raw internal-name prefix; zone display "
                  "names / level ranges / coordinates are server-side data "
                  "pending ruling (see session-report 2026-07-22)"),
        "badges": kept,
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"Wrote {OUT} ({len(kept)} badges)")


if __name__ == "__main__":
    main()
