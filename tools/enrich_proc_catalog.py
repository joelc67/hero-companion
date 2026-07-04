"""Add PPM + damage values to data/proc_catalog.json so the engine can price
damage procs (model v24).

PROVISIONAL CONSTANTS (pending verification against homecoming.wiki
"Procs Per Minute"): regular damage procs 3.5 PPM / 71.75 damage at 50;
purple (premium) procs 4.5 PPM / 107.09. -Res procs 3.5 PPM.
Re-run after editing; idempotent.
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "proc_catalog.json")

d = json.load(open(PATH, encoding="utf-8"))
n = 0
for cat, procs in d.get("damage_procs", {}).items():
    for p in procs:
        p["ppm"] = 4.5 if p.get("premium") else 3.5
        p["dmg50"] = 107.09 if p.get("premium") else 71.75
        p["provisional"] = True
        n += 1
for cat, procs in d.get("res_procs", {}).items():
    for p in procs:
        p["ppm"] = 3.5
        p["provisional"] = True
        n += 1
json.dump(d, open(PATH, "w", encoding="utf-8"), indent=1)
print(f"enriched {n} procs with ppm/dmg50 (provisional)")
