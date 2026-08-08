"""The self +Damage back-fill is present, faithful to the client, and INERT.

The inertness half is the one that matters. The rows describe a buff that is up
for 10 seconds in every 90, and nothing prices it yet - so this battery pins that
adding one of these powers still moves no number. The day the mode/uptime model
lands, check 3 is what should fail, deliberately, and be updated with the ruling.

Usage: python tools/test_self_damage_buffs.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))

PASS = FAIL = 0


def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}")
    if detail:
        print(f"        {detail}")


def main():
    import server as srv  # noqa: E402
    powers = json.load(open(os.path.join(ROOT, "data", "powers.json"), encoding="utf-8"))

    by_name = {}
    for _ps, lst in powers.items():
        for p in lst:
            by_name[p["full_name"]] = p

    def mode_rows(fn):
        return [e for e in (by_name.get(fn, {}).get("self_effects") or []) if e.get("mode")]

    # 1. COVERAGE, with a denominator from the data itself
    total = sum(1 for p in by_name.values()
                if any(e.get("mode") for e in (p.get("self_effects") or [])))
    # 345 have an ungated self damage template; Vigilance is dropped because its
    # AT_Uniqueness table is one the engine does not carry, so 344 land.
    ok("the back-fill covers the expected 344 powers", total == 344,
       f"{total} powers carry mode rows")
    ok("NEGATIVE CONTROL: Vigilance stays out - its table is unresolvable",
       not mode_rows("Inherent.Inherent.Vigilance"),
       "AT_Uniqueness is absent from modifier_tables.json; skipped and reported")

    # 1b. THE TABLES ARE READ FROM THE CLIENT, NOT CHOSEN. If they had been
    # hardcoded to Melee_Buff_Dmg this would be 1 - and 1,356 of 2,946 rows
    # would carry the wrong table, because Ranged_Ones and Melee_Ones are
    # literal-magnitude tables, not archetype-scaled ones.
    allrows0 = [e for p in by_name.values() for e in (p.get("self_effects") or [])
                if e.get("mode")]
    tables = {r["modifier_table"] for r in allrows0}
    ok("the modifier tables come from the client, not a hardcoded guess",
       len(tables) >= 4, f"{len(tables)} distinct tables: {sorted(tables)}")

    # 1c. The game distinguishes stacking from replacing, and so do we
    sd = [r for r in mode_rows("Epic.Corruptor_Soul_Mastery.Soul_Drain")]
    per_target = [r for r in sd if r["scale"] == 0.8 and r.get("stack") == "Stack"]
    flat = [r for r in sd if r["scale"] == 4.0 and r.get("stack") == "Replace"]
    ok("Soul Drain keeps the game's split: 0.8 per-target Stack vs 4.0 flat Replace",
       len(per_target) == 8 and len(flat) == 8,
       f"{len(per_target)} stacking rows, {len(flat)} replacing rows")

    # 1d. Rage's crash is carried as a PENALTY with the game's own 120s delay
    rg = mode_rows("Brute_Melee.Super_Strength.Rage")
    crash = [r for r in rg if r.get("penalty") and r.get("delay") == 120.0]
    ok("Rage's -999 crash is kept as a penalty firing at the game's 120s delay",
       len(crash) == 8, f"{len(crash)} crash rows")

    # 2. FAITHFUL to the client's own numbers, on three powers read by hand
    bu = mode_rows("Brute_Melee.Fiery_Melee.Build_Up")
    ok("Build Up: 8 damage types, scale 8.0, 10s on a 90s recharge",
       len(bu) == 8 and all(r["scale"] == 8.0 for r in bu)
       and all(r["duration"] == 10.0 for r in bu)
       and all(r["host_recharge"] == 90.0 for r in bu),
       f"{len(bu)} rows, scale {bu[0]['scale'] if bu else '?'}, dur {bu[0]['duration'] if bu else '?'}")

    rage = mode_rows("Brute_Melee.Super_Strength.Rage")
    buff = [r for r in rage if not r.get("penalty")]
    ok("Rage: the 120s BUFF rows are separated from the crash rows",
       len(buff) == 8 and all(r["duration"] == 120.0 and r["scale"] > 0 for r in buff),
       f"{len(buff)} buff rows of {len(rage)} total")

    fe = [r for r in mode_rows("Brute_Defense.Fiery_Aura.Fiery_Embrace")
          if not r.get("penalty")]
    fire = [r for r in fe if r["damage_type"] == "Fire"]
    other = [r for r in fe if r["damage_type"] != "Fire"]
    ok("Fiery Embrace keeps the game's SPLIT: fire 10.0/20s, the rest 8.0/10s",
       len(fire) == 1 and fire[0]["scale"] == 10.0 and fire[0]["duration"] == 20.0
       and other and all(r["scale"] == 8.0 and r["duration"] == 10.0 for r in other),
       f"fire {fire[0]['scale'] if fire else '?'}@{fire[0]['duration'] if fire else '?'}s, "
       f"{len(other)} others")

    # 3. INERT - the whole safety argument, measured not assumed
    c = srv.app.test_client()

    def st_dps(names):
        pw = [{"full_name": n, "slots": [None], "slotCount": 1} for n in names]
        r = c.post("/build/calculate",
                   json={"archetype": "Class_Brute", "powers": pw}).get_json()
        return (r.get("offense") or {}).get("st_dps")

    base = ["Brute_Melee.Fiery_Melee.Scorch", "Brute_Melee.Fiery_Melee.Cremate",
            "Brute_Defense.Fiery_Aura.Fire_Shield"]
    a = st_dps(base)
    b = st_dps(base + ["Brute_Melee.Fiery_Melee.Build_Up"])
    ok("INERT: adding Build Up still moves displayed DPS by nothing",
       a == b, f"without {a}, with {b} - equal until the mode model lands")

    # 4. The mode facts are ON every row, so no consumer can read it as always-on
    allrows = [e for p in by_name.values() for e in (p.get("self_effects") or [])
               if e.get("mode")]
    ok("every row carries its duration AND its host recharge",
       all(r.get("duration") is not None and r.get("host_recharge") is not None
           for r in allrows),
       f"{len(allrows)} rows checked")
    ok("every row names a modifier table the engine actually has",
       all(r.get("modifier_table") in
           json.load(open(os.path.join(ROOT, "data", "modifier_tables.json"),
                          encoding="utf-8"))["tables"] for r in allrows))

    # 5. NEGATIVE CONTROL - a power the client gives no self +Damage keeps none
    ok("NEGATIVE CONTROL: an ordinary attack has no mode rows",
       not mode_rows("Brute_Melee.Fiery_Melee.Scorch"),
       "Scorch carries none, as the client says")
    ok("NEGATIVE CONTROL: a gated-only power was excluded, not guessed at",
       not mode_rows("Inherent.Inherent.Cosmic_Balance"),
       "Cosmic Balance is teammate-conditional and stays out")

    print(f"\nself +Damage back-fill battery: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
