"""Reality check: pet entities/squads/durations vs the LIVE game (task #33).

Run after any data refresh:  py tools\\gamedata\\reality_check_pets.py
Guards the convert_pet_entities.py reconciliation:
- henchman-family classes exist as columns with the client's level-50 values
- squad counts are real (Soldiers = 2xSoldier+1xMedic, tier-1 squads of 3)
- durations are real (MM henchmen permanent; Spiderlings timed)
- every power-spec class resolves to a modifier-table column
- all modifier tables stay uniform width
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

fails = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        fails.append(name)


def _load(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as f:
        return json.load(f)


summons = _load("summons.json")
arch = _load("archetypes.json")["archetypes"]
tables = _load("modifier_tables.json")["tables"]

cols = {}
for a in arch:
    cols.setdefault(a["name"], a.get("column"))    # FIRST wins (duplicate-name trap)

specs = summons.get("powers") or {}
check("power specs present", len(specs) > 400, f"{len(specs)} specs")

sol = specs.get("Mastermind_Summon.Mercenaries.Soldiers") or {}
by_uid = {p["uid"]: p for p in sol.get("pets", [])}
check("Soldiers squad = 2 Soldiers + 1 Medic",
      by_uid.get("Pets_Soldier", {}).get("count") == 2
      and by_uid.get("Pets_Medic", {}).get("count") == 1, json.dumps(sol.get("pets")))
check("Soldiers are permanent henchmen", sol.get("permanent") is True)
check("Soldiers copy the summon's slotting", sol.get("copy_boosts") is True)
check("Soldier priced as LIVE Class_Henchman_Minion",
      by_uid.get("Pets_Soldier", {}).get("class") == "Class_Henchman_Minion")

hm_col = cols.get("Class_Henchman_Minion")
rgd = tables["Ranged_Damage"]
check("Class_Henchman_Minion column exists", hm_col is not None, f"column {hm_col}")
check("henchman ranged scale = client 11.6268@50 (was 26.09 = 2.2x hot)",
      hm_col is not None and abs(abs(rgd[hm_col]) - 11.6268) < 0.01,
      f"{rgd[hm_col] if hm_col is not None else None}")

spiders = next((v for k, v in specs.items() if k.endswith("Summon_Spiderlings")), None)
check("Spiderlings are TIMED (240s), not permanent",
      bool(spiders) and spiders.get("duration") == 240.0
      and not spiders.get("permanent"), json.dumps(spiders)[:120])

t1 = {"Mastermind_Summon.Necromancy.Zombie_Horde": 3,
      "Mastermind_Summon.Robotics.Battle_Drones": 3,
      "Mastermind_Summon.Demon_Summoning.Summon_Demonlings": 3,
      "Mastermind_Summon.Beast_Mastery.Summon_Wolves": 3,
      "Mastermind_Summon.Ninjas.Call_Genin": 3,
      "Mastermind_Summon.Thugs.Call_Thugs": 3}
for full, want in t1.items():
    got = sum(p.get("count", 0) for p in (specs.get(full) or {}).get("pets", []))
    check(f"tier-1 squad of {want}: {full.split('.')[-1]}", got == want, f"got {got}")

bad_class = [(k, p["class"]) for k, v in specs.items() for p in v.get("pets", [])
             if p.get("class") and cols.get(p["class"]) is None]
check("every spec class resolves to a column", not bad_class, str(bad_class[:3]))
bad_count = [k for k, v in specs.items() for p in v.get("pets", [])
             if not isinstance(p.get("count"), int) or p["count"] < 1]
check("every spec count is a positive integer", not bad_count, str(bad_count[:3]))
widths = {len(v) for v in tables.values()}
check("modifier tables uniform width", len(widths) == 1, str(widths))

print(f"\n══ {'ALL PASS' if not fails else f'{len(fails)} FAILURE(S): ' + ', '.join(fails)} ══")
sys.exit(1 if fails else 0)
