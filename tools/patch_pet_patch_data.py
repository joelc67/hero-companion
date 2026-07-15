"""ADDITIVE patcher (the standing powers.json family — NEVER re-parse): back-
fill pseudo-pet PATCH records with the client bin's own mechanics so v31 can
price procs in them.

Source of every value: the raw client powers.bin via the preserved Bin Crawler
(tools/gamedata/bin-crawler), extracted 2026-07-16 for the v31 batch:
  Pets.Radiation_Melee.Irradiated_Ground — power_type 1 (Auto), activate_period
  2.0s, radius 8.0, arc 0, max_targets_hit 10, recharge 0. The patch pulses a
  PBAoE every 2 seconds; procs slotted in the SUMMONING power roll per pulse
  per target at PPM × period / (60 × AF).

parse_mids leaves these pet records as stubs (period 0, radius 0) — this
patcher fills exactly the named records and nothing else, verifies the file is
byte-identical after stripping the added/updated keys, and hard-fails on any
shape drift (coverage denominator printed).

Run:  py tools\\patch_pet_patch_data.py
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "powers.json")

# full_name -> the client bin's mechanics (extracted values, never guessed)
PATCH_PETS = {
    "Pets.Radiation_Melee_Irradiated_Ground.Irradiated_Ground": {
        "power_type": 1,          # Auto — pulses continuously while the patch is down
        "activate_period": 2.0,
        "radius": 8.0,
        "arc": 0,
        "max_targets": 10,
        "effect_area": 2,
        "_patch_pet": True,       # v31 marker: a pseudo-pet PATCH attack record
    },
}

data = json.load(open(PATH, encoding="utf-8"))
patched = 0
for ps, rows in data.items():
    for q in rows:
        fix = PATCH_PETS.get(q.get("full_name"))
        if not fix:
            continue
        for k, v in fix.items():
            q[k] = v
        patched += 1
print(f"{patched} of {len(PATCH_PETS)} pinned patch-pet records patched")
if patched != len(PATCH_PETS):
    print("== COVERAGE FAILURE: a pinned record was not found — powers.json "
          "shape drifted; investigate before shipping ==")
    sys.exit(1)
with open(PATH, "w", encoding="utf-8") as f:
    json.dump(data, f)
print("data/powers.json updated (additive; run reality checks after)")
