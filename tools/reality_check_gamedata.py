"""Reality-check our archetype modifier data against AUTHORITATIVE game data.

Source of truth: the game client's own bins, extracted with Bin Crawler
(https://github.com/wednesdaywoe/CoH-Planner) — NOT Mids (which we found frozen
6 months stale). A snapshot of the per-archetype tables lives in
tools/gamedata/tables/. To refresh after a game patch:

  git clone https://github.com/wednesdaywoe/CoH-Planner
  cd CoH-Planner/tools/bin-crawler
  py -m bin_crawler.export_classes --assets-dir "<CoH>/assets/live" --output-dir out
  # copy out/tables/<playable-at>.json into coh-builder/tools/gamedata/tables/

Then run this to see what drifted, and tools/sync will apply it.

Compares only LEVEL-INDEPENDENT (flat) modifiers, where a single per-AT value is
unambiguous (defense/resist/damage buff scalars, etc.). Level-scaling tables
(damage, HP curves) need index alignment and are checked separately.

Run:  python tools/reality_check_gamedata.py
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
import server as srv  # noqa: E402

TABLES = os.path.join(os.path.dirname(__file__), "gamedata", "tables")


def _norm(n):
    return (n[6:] if n.lower().startswith("class_") else n).lower()


def main():
    mt = srv.MODIFIER_TABLES
    ats = [a for a in srv.ARCH_BY_NAME.values()
           if a.get("playable") and a.get("column") is not None]
    checked = stale = 0
    rows = []
    for a in ats:
        f = os.path.join(TABLES, _norm(a["name"]) + ".json")
        if not os.path.exists(f):
            continue
        ex = json.load(open(f, encoding="utf-8")).get("named_tables", {})
        for t, vals in ex.items():
            if not vals or (max(vals) - min(vals) > 1e-6):
                continue                       # flat tables only
            our = mt.get(t)
            if our is None or a["column"] >= len(our):
                continue
            checked += 1
            if abs(our[a["column"]] - vals[0]) > 0.0005:
                stale += 1
                rows.append(f"  {a['display_name']:16s} {t:22s} ours={our[a['column']]:+.4f}  game={vals[0]:+.4f}")
    print(f"Flat AT modifiers compared vs game data: {checked}")
    print(f"STALE (drifted from the live game): {stale}")
    for r in rows:
        print(r)
    if not stale:
        print("Every level-independent archetype modifier matches the live game.")
    return stale


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
