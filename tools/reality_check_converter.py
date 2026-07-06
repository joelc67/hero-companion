"""Reality-check our converter COSTS against authoritative game data.

The game client ships bin/conversionsets.bin (inside bin.pigg) listing every
conversion pool with its type and converter cost. A decoded snapshot lives in
tools/gamedata/conversionsets.json — extracted with Pigg Wrangler
(github.com/wednesdaywoe/CoH-Planner); see tools/gamedata/README.md.

Record fields (verified 2026-07-06 against the client's own UI text):
  * type — 2 = category pool, 3 = rarity pool (1 = in-set, which isn't a pool;
    its cost 3 is stated in the game tooltip: "In Set Conversions cost 3
    Enhancement Converters", and the salvage text calls it "three times the
    [out-of-set] cost").
  * cost — converters per roll: rarity pools (Uncommon/Rare/VeryRare/PvP and
    the ATO/Winter pools) = 1, category pools = 2.

Compares those to the constants server/converter.py plans with.

Report-only.  Run:  python tools/reality_check_converter.py
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(os.path.dirname(__file__), "gamedata", "conversionsets.json")
CONVERTER = os.path.join(ROOT, "server", "converter.py")

IN_SET_COST = 3       # from the game's In-Set tooltip (not in the pool table)


def main():
    snap = json.load(open(SNAP, encoding="utf-8"))["sets"]
    rarity_costs = {v["cost"] for v in snap.values() if v["type"] == 3}
    category_costs = {v["cost"] for v in snap.values() if v["type"] == 2}
    print(f"Game pools: {len(snap)} — rarity cost(s) {sorted(rarity_costs)}, "
          f"category cost(s) {sorted(category_costs)}, in-set {IN_SET_COST} (UI text).")

    src = open(CONVERTER, encoding="utf-8").read()
    ours = {}
    m = re.search(r'"by_rarity":\s*\{\s*"cost":\s*(\d+)', src)
    if m:
        ours["by_rarity"] = int(m.group(1))
    for kind, pat in (("by_set", r"By-Set\s*\((\d+) conv"),
                      ("by_category", r"By-Category\s*\((\d+) conv"),
                      ("by_rarity_text", r"By-Rarity\s*\((\d+) conv")):
        m = re.search(pat, src)
        if m:
            ours[kind] = int(m.group(1))

    drift = []
    if rarity_costs != {ours.get("by_rarity", ours.get("by_rarity_text"))}:
        drift.append(f"by_rarity: ours={ours.get('by_rarity')} game={sorted(rarity_costs)}")
    if category_costs != {ours.get("by_category")}:
        drift.append(f"by_category: ours={ours.get('by_category')} game={sorted(category_costs)}")
    if ours.get("by_set") != IN_SET_COST:
        drift.append(f"by_set: ours={ours.get('by_set')} game={IN_SET_COST}")
    if ours.get("by_rarity") is not None and ours.get("by_rarity_text") not in (None, ours["by_rarity"]):
        drift.append(f"by_rarity text/plan disagree: plan={ours['by_rarity']} text={ours['by_rarity_text']}")

    print(f"Ours (server/converter.py): {ours}")
    print(f"REAL DRIFT: {len(drift)}")
    for d in drift:
        print(f"  {d}")
    if not drift:
        print("Converter costs match the live game (By-Set 3, By-Category 2, By-Rarity 1).")
    return len(drift)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
