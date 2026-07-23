"""Merge badge LOCATIONS from n15g's coh-content-db into our game-first badges.

The split, kept clean:
  - badges.bin (the game client) owns the badge's IDENTITY — name, description,
    category, which zone it belongs to. That is game-first and never overwritten.
  - the content-db (community, Unlicense/public domain) adds the one thing the
    client does NOT carry: WHERE the badge physically is — coordinates and, for
    442 of them, a plain-English direction ("on top of the casino, 120 yards
    due east of Meteor Do"). Credited to n15g regardless of the licence.

Join key: the content-db's `gameId` IS our badges.bin `name` (BloodyBayTour1).
1,738 match exactly; 499 carry a location.

Given the game has NO paste-to-navigate command (getpos only reads your own
position, verified in command.bin), the plain-English hint is the useful part —
so it is preserved verbatim, only stripping the content-db's `[text](zone://k)`
link markup down to its display text.

    python tools/build_badge_locations.py
    -> data/badge_locations.json  (keyed by gameId; the server joins on it)
"""
from __future__ import annotations

import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "tools", "gamedata", "_coh_content_db.json")
OUT = os.path.join(REPO, "data", "badge_locations.json")

# "[Boomtown](zone://boomtown)" -> "Boomtown"; "[x](badge://y)" -> "x"
_LINK = re.compile(r"\[([^\]]+)\]\((?:zone|badge|contact|mission)://[^)]+\)")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", _LINK.sub(r"\1", text or "")).strip()


def _locations(badge: dict) -> list[dict]:
    out = []
    for r in badge.get("requirements", []):
        loc = r.get("location")
        for l in (loc if isinstance(loc, list) else [loc]):
            if isinstance(l, dict) and l.get("coords"):
                out.append({"zone": l.get("zoneKey"),
                            "coords": [round(c, 1) for c in l["coords"]],
                            "label": l.get("iconText")})
    return out


def main() -> int:
    if not os.path.exists(SRC):
        print(f"content-db not found at {SRC} — run the fetch first "
              f"(github.com/n15g/coh-content-db-homecoming release bundle.json)")
        return 1
    with open(SRC, encoding="utf-8") as f:
        db = json.load(f)
    version = (db.get("header") or {}).get("version") or "?"

    out = {}
    n_hint = 0
    for b in db.get("badges", []):
        gids = b.get("gameId")
        gids = gids if isinstance(gids, list) else ([gids] if gids else [])
        locs = _locations(b)
        if not gids or not locs:
            continue
        hint = _clean(b.get("notes", ""))
        if hint:
            n_hint += 1
        rec = {"locations": locs}
        if hint:
            rec["hint"] = hint
        # the wiki link is handy on the surface too
        links = b.get("links") or []
        if links:
            rec["wiki"] = links[0].get("href")
        for g in gids:
            out[g] = rec

    payload = {
        "_source": f"n15g/coh-content-db-homecoming bundle.json v{version} "
                   "(Unlicense / public domain); coordinates + directions only.",
        "_credit": "Badge locations and directions by n15g (coh-content-db). "
                   "The game client supplies each badge's identity; this adds only where it is.",
        "_provenance_label": "badge locations by n15g (coh-content-db)",
        "_join": "keyed by the game's internal badge id (badges.bin 'name' == content-db 'gameId').",
        "_coverage": {"located_badges": len(out), "with_direction": n_hint},
        "locations": out,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"wrote {OUT}: {len(out)} located badges, {n_hint} with a plain-English direction")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
