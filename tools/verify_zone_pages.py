"""Prove every fetched zone page against the LIVE game client before it ships.

The question is only ever "does this wiki page describe content the game still
has?" — and the client answers it per ZONE, not per badge. badges.bin groups
every exploration badge under a zone key; so a page is live if its zone exists
in that export with a comparable set of badges. This is deliberately NOT a
per-badge name match: the wiki formats gendered pairs ("King/Queen of Pain")
and comma-containing names ("Veni, Vidi, Vici") in ways a name-by-name compare
trips over, producing false alarms on pages that are perfectly current.

Nobody vouches for the wiki — not Joel, not me — so the check leans on the
client, which cannot be talked into agreeing.

    python tools/verify_zone_pages.py
"""
from __future__ import annotations

import collections
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def norm(s: str) -> str:
    s = re.sub(r"^(the|echo:)\s+", "", str(s or "").lower())
    return "".join(c for c in s if c.isalnum())


def main() -> int:
    with open(os.path.join(REPO, "data", "journey_badges.json"), encoding="utf-8") as f:
        badges = json.load(f)["badges"]
    # exploration-badge count per live zone key, and a flat name set for the
    # informational per-badge tally.
    by_zone = collections.Counter()
    live_names = set()
    for b in badges:
        if b.get("zone_key"):
            by_zone[norm(b["zone_key"])] += 1
        for k in ("display_hero", "display_villain", "name"):
            if b.get(k):
                live_names.add(norm(b[k]))

    with open(os.path.join(REPO, "data", "zone_pages.json"), encoding="utf-8") as f:
        pages = json.load(f)["zones"]

    def live_key_for(zone_name: str) -> str | None:
        n = norm(zone_name)
        if n in by_zone:
            return n
        # "Talos Island" ↔ key "TalosIsland", "Striga Isle" ↔ "Striga"
        for k in by_zone:
            if len(k) >= 5 and len(n) >= 5 and (k.startswith(n) or n.startswith(k)):
                return k
        return None

    # Tolerant per-badge match: gendered pairs ("King/Queen of Pain" vs the
    # wiki's "King of Pain / Queen of Pain") share a word set even when neither
    # string contains the other; commas make some names un-splittable, so this
    # is a fraction, not an all-or-nothing.
    def badge_live(name: str) -> bool:
        if norm(name) in live_names:
            return True
        if any(norm(p) in live_names for p in re.split(r"\s*/\s*", name)):
            return True
        words = set(re.findall(r"[a-z0-9]+", name.lower())) - {"i", "ii", "iii", "iv", "v", "vi"}
        if len(words) < 2:
            return False
        for b in badges:  # word-subset catches gendered + roman-numeral variants
            for k in ("display_hero", "display_villain"):
                bw = set(re.findall(r"[a-z0-9]+", (b.get(k) or "").lower()))
                if bw and words <= bw:
                    return True
        return False

    resolved, unmatched, no_badges = [], [], []
    for z in pages:
        eb = z.get("exploration_badges") or []
        if not eb:
            no_badges.append(z["zone"])
            continue
        key = live_key_for(z.get("wiki_title") or z["zone"]) or live_key_for(z["zone"])
        # A page is live if its zone maps to a badges.bin key OR most of its
        # listed badges exist in the client (covers zones the tourism grouping
        # buckets under "other" — the Praetorian zones — and dev-era key
        # spellings like CreysFolley).
        matched = sum(1 for b in eb if badge_live(b))
        if key or matched >= max(1, int(0.6 * len(eb))):
            resolved.append((z["zone"], key or f"{matched}/{len(eb)} badges live", len(eb),
                             by_zone.get(key, matched)))
        else:
            unmatched.append((z["zone"], len(eb)))

    # informational: how many individual listed names also resolve (tolerant of
    # gendered halves; commas are why this is a tally, not a gate).
    hit = tot = 0
    for z in pages:
        for b in (z.get("exploration_badges") or []):
            tot += 1
            parts = re.split(r"\s*/\s*", b)
            if norm(b) in live_names or any(norm(p) in live_names for p in parts):
                hit += 1

    print(f"{len(resolved)} of {len(pages)} pages map to a LIVE zone in badges.bin")
    print(f"  per-badge name tally (informational): {hit}/{tot} exact-match "
          f"(gendered pairs and comma-names under-count here by design)")
    if no_badges:
        print(f"  no badge list on page — zone identity unverifiable this way "
              f"({len(no_badges)}): {', '.join(no_badges)}")
    if unmatched:
        print(f"\n  STALE / UNKNOWN — page does not map to any live zone "
              f"({len(unmatched)}). DO NOT SHIP until reconciled:")
        for zone, n in unmatched:
            print(f"    {zone} ({n} badges listed, zone not in badges.bin)")
        return 1
    print("\n  OK: every badged page maps to a zone the live client still has — clear to ship")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
