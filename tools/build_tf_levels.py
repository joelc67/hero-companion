"""When each Task Force / Strike Force becomes available — from the content-db.

Joel: "no mention of when each Task Force or Strike Force becomes available." The
content-db's `missions` carry `type` (task-force / strike-force / trial) and a
`levelRange`, so this emits a name->level lookup the road matches to the events
it already lists, giving each run its "available at N".

    python tools/build_tf_levels.py  ->  data/tf_levels.json
"""
from __future__ import annotations

import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "tools", "gamedata", "_coh_content_db.json")
OUT = os.path.join(REPO, "data", "tf_levels.json")


def _pick(v):
    if isinstance(v, list):
        return next((x.get("value") for x in v if x.get("alignment") == "hero"),
                    v[0].get("value") if v else "")
    return v or ""


# normalise a TF/SF name so an event label matches it: strip "the", the
# task-force/strike-force/trial suffix, "part one/two", punctuation.
def _key(name: str) -> str:
    s = name.lower()
    s = re.sub(r"\bpart (one|two|1|2|i|ii)\b", "", s)
    s = re.sub(r"\b(task force|strike force|trial|tf|sf)\b", "", s)
    s = re.sub(r"^the\s+", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


def main() -> int:
    if not os.path.exists(SRC):
        print(f"content-db not found at {SRC} — fetch the bundle first")
        return 1
    with open(SRC, encoding="utf-8") as f:
        db = json.load(f)

    out = {}
    for m in db.get("missions", []):
        t = m.get("type", "")
        if t not in ("task-force", "strike-force", "trial"):
            continue
        lr = m.get("levelRange")
        if not lr:
            continue
        name = _pick(m.get("name"))
        k = _key(name)
        lo, hi = (lr[0], lr[-1])
        # a TF split into parts: keep the WIDEST span under the shared key so
        # "Positron" reports the whole 8-16 availability, not just part one.
        if k in out:
            lo = min(lo, out[k]["from"])
            hi = max(hi, out[k]["to"])
        out[k] = {"name": re.sub(r"\s+(Part (One|Two))$", "", name),
                  "from": lo, "to": hi, "type": t}

    payload = {
        "_source": "n15g/coh-content-db-homecoming missions (Unlicense).",
        "_provenance_label": "TF/SF levels by n15g (coh-content-db)",
        "_join": "keyed by normalised TF/SF name; the client matches its events.",
        "_coverage": {"runs": len(out)},
        "tf_levels": out,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"wrote {OUT}: {len(out)} task forces / strike forces / trials with availability levels")
    for k, v in sorted(out.items(), key=lambda kv: kv[1]["from"]):
        print(f"  {v['from']:>2}-{v['to']:<2} {v['type']:13s} {v['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
