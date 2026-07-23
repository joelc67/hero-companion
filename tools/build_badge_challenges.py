"""Extract the Master-of / iTrial challenge badges and what they take to earn.

These badges fall THROUGH the zone-organised badge drawer, and correctly so:
you don't earn "Master of the B.A.F." at a place, you earn it by completing a
task force or Incarnate trial under challenge conditions. They belong on the
TASK FORCE / TRIAL the Journey already places, not on a zone.

A Master badge's own requirements ARE its challenge checklist — each is a
`badge` requirement pointing at a sub-badge (Master of the B.A.F. = Not On My
Watch + Alarm Raiser + Gotta Keep 'Em Separated + Strong & Pretty). This
resolves those keys to their display names so the road can show the whole ask.

Join to the road: the badge name carries the TF/trial name ("Master of Apex's
Task Force"), normalised so the client can match it to an event it already
lists. Source: n15g/coh-content-db (Unlicense), same credit as the locations.

    python tools/build_badge_challenges.py  ->  data/badge_challenges.json
"""
from __future__ import annotations

import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "tools", "gamedata", "_coh_content_db.json")
OUT = os.path.join(REPO, "data", "badge_challenges.json")


def _pick(v):
    """content-db strings are sometimes plain, sometimes a list of alignment
    variants; take the hero-side or the first value either way."""
    if isinstance(v, list):
        return next((x.get("value") for x in v if x.get("alignment") == "hero"),
                    v[0].get("value") if v else "")
    return v or ""


def _name(b: dict) -> str:
    return _pick(b.get("name"))


# "Master of the B.A.F." -> "baf"; "Master of Apex's Task Force" -> "apex".
# Strips the Master-of wrapper and the TF/SF/trial suffix so it matches an
# event label like "Apex TF" or "Behavioral Adjustment Facility (BAF)".
def _tf_key(master_name: str) -> str:
    s = master_name.lower()
    s = re.sub(r"^master of (the )?", "", s)
    s = re.sub(r"['’]s?\b", "", s)
    s = re.sub(r"\b(task force|strike force|incarnate trial|trial|tf|sf)\b", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


def main() -> int:
    if not os.path.exists(SRC):
        print(f"content-db not found at {SRC} — fetch the bundle first")
        return 1
    with open(SRC, encoding="utf-8") as f:
        db = json.load(f)
    by_key = {b.get("key"): b for b in db.get("badges", [])}

    out = {}
    for b in db.get("badges", []):
        nm = _name(b)
        if not nm.lower().startswith("master of"):
            continue
        # resolve the challenge sub-badges this Master requires
        subs = []
        for r in b.get("requirements", []):
            if r.get("type") == "badge":
                sub = by_key.get(r.get("badgeKey"))
                subs.append(_name(sub) if sub else r.get("badgeKey"))
        is_itrial = "incarnate trial" in _pick(b.get("badgeText")).lower()
        rec = {"master_badge": nm, "challenge_badges": subs,
               "kind": "itrial" if is_itrial else "taskforce",
               "text": _pick(b.get("badgeText"))}
        out[_tf_key(nm)] = rec

    payload = {
        "_source": "n15g/coh-content-db-homecoming (Unlicense). Master/iTrial "
                   "challenge badges + their required sub-badges.",
        "_provenance_label": "challenge badges by n15g (coh-content-db)",
        "_join": "keyed by normalised task-force / trial name; the client matches "
                 "it to an event it already lists on the road.",
        "_note": "These badges are earned by COMPLETING a TF/trial under challenge "
                 "conditions, not at a location — hence attached to the run, not a zone.",
        "_coverage": {"master_badges": len(out),
                      "itrials": sum(1 for v in out.values() if v["kind"] == "itrial")},
        "challenges": out,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"wrote {OUT}: {len(out)} Master badges "
          f"({payload['_coverage']['itrials']} iTrials), each with its challenge checklist")
    for k, v in sorted(out.items()):
        print(f"  {k:22s} {v['master_badge']:38s} -> {len(v['challenge_badges'])} sub-badges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
