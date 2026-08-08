"""The power-granted protection back-fills are faithful, separated, and inert.

Covers BOTH patchers together because they are one class: an axis that IS scored
but was fed only by IO set bonuses, while the powers that actually grant it
contributed nothing (knockback protection was noticed and stated; slow
resistance and mez were not).

The checks that matter most are the NEGATIVE ones. It is easy to add data; the
expensive mistakes today were all about adding the WRONG data:
  * 78 aspect=Strength recharge BUFFS sit beside the 223 aspect=Resistance slow
    RESISTANCES. Keying on the attrib alone would have converted them.
  * mez PROTECTION (a magnitude threshold) and mez RESISTANCE (a duration
    multiplier) share a template group and differ only by aspect.
  * protection arrives as -30.0. Reinterpreting the sign turns it into a penalty.

Usage: python tools/test_power_protection_backfills.py
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
    by = {}
    for _ps, lst in powers.items():
        for p in lst:
            by[p["full_name"]] = p

    def rows(fn, mark):
        return [e for e in (by.get(fn, {}).get("self_effects") or []) if e.get(mark)]

    slow_powers = sum(1 for p in by.values()
                      if any(e.get("slow_resist_row") for e in (p.get("self_effects") or [])))
    mez_powers = sum(1 for p in by.values()
                     if any(e.get("mez_row") for e in (p.get("self_effects") or [])))

    # ---- coverage, against the denominators the patchers printed ----
    ok("slow-resistance back-fill covers 126 powers", slow_powers == 126,
       f"{slow_powers} powers carry slow_resist rows")
    ok("mez back-fill covers 229 powers", mez_powers == 229,
       f"{mez_powers} powers carry mez rows")

    # ---- faithful to the client, on powers read by hand ----
    wet = rows("Brute_Defense.Ice_Armor.Wet_Ice", "slow_resist_row")
    ok("Wet Ice carries the game's slow resistance (0.6 and 0.5, Melee_Ones)",
       len(wet) == 2 and sorted(r["scale"] for r in wet) == [0.5, 0.6]
       and all(r["modifier_table"] == "Melee_Ones" for r in wet),
       f"{[r['scale'] for r in wet]}")

    uny = rows("Brute_Defense.Invulnerability.Unyielding", "mez_row")
    prot = [r for r in uny if r["effect"] == "MezProtection"]
    res = [r for r in uny if r["effect"] == "MezResist"]
    ok("Unyielding carries BOTH mez aspects, kept separate",
       len(prot) == 4 and len(res) == 4,
       f"{len(prot)} protection rows, {len(res)} resistance rows")
    ok("...protection keeps the game's sign VERBATIM (-30.0, not reinterpreted)",
       prot and all(r["scale"] == -30.0 for r in prot),
       f"scales {sorted({r['scale'] for r in prot})}")
    ok("...resistance is the separate 3.0 duration axis, not merged into it",
       res and all(r["scale"] == 3.0 for r in res),
       f"scales {sorted({r['scale'] for r in res})}")
    ok("...and it covers the four mez types the client names",
       {r["damage_type"] for r in prot} == {"Held", "Immobilized", "Stunned", "Sleep"},
       f"{sorted({r['damage_type'] for r in prot})}")

    # ---- THE NEGATIVE CONTROLS: what must NOT have happened ----
    beta = by.get("Blaster_Support.Radiation_Manipulation.Beta_Decay", {})
    beta_bad = [e for e in (beta.get("self_effects") or [])
                if e.get("slow_resist_row")]
    ok("NEGATIVE CONTROL: aspect=Strength recharge BUFFS were not converted",
       not beta_bad,
       "Beta Decay is a recharge buff (aspect=Strength) and carries no slow-resist row")

    ok("NEGATIVE CONTROL: an ordinary attack got neither back-fill",
       not rows("Brute_Melee.Fiery_Melee.Scorch", "slow_resist_row")
       and not rows("Brute_Melee.Fiery_Melee.Scorch", "mez_row"))

    mixed = [p for p in by.values()
             for e in (p.get("self_effects") or [])
             if e.get("mez_row") and e.get("effect") not in ("MezProtection", "MezResist")]
    ok("NEGATIVE CONTROL: no mez row escaped the two-name split", not mixed,
       f"{len(mixed)} rows with an unexpected effect name")

    # ---- INERT: no consumer branch exists yet, so nothing may move ----
    c = srv.app.test_client()

    def calc(names):
        pw = [{"full_name": n, "slots": [None], "slotCount": 1} for n in names]
        return c.post("/build/calculate",
                      json={"archetype": "Class_Brute", "powers": pw}).get_json()

    base = ["Brute_Melee.Fiery_Melee.Scorch"]
    a = calc(base)
    b = calc(base + ["Brute_Defense.Invulnerability.Unyielding",
                     "Brute_Defense.Ice_Armor.Wet_Ice"])
    # ⚠⚠ THIS CHECK USED TO READ THE TOP LEVEL AND PASSED FOR THE WRONG REASON.
    # calculate_build returns a curated 20-key response; slow_resist is NOT one
    # of them, it lives at bonus_extras.slow_resist.value. Probing the top level
    # returns None however well the branch works - which is exactly what made me
    # revert a correct change. Read where the value actually lives.
    def slow_of(resp):
        return ((resp.get("bonus_extras") or {}).get("slow_resist") or {}).get("value")
    ok("v40: Wet Ice's slow resistance now REACHES the scored total",
       slow_of(a) == 0.0 and slow_of(b) and slow_of(b) > 100,
       f"{slow_of(a)} -> {slow_of(b)}  (0.6 + 0.5 on the literal Melee_Ones table)")
    ok("NEGATIVE CONTROL: a power the client grants none still reads 0.0",
       slow_of(calc(base + ["Brute_Defense.Fiery_Aura.Fire_Shield"])) == 0.0)
    ok("mez is still INERT - no consumer branch exists for it yet",
       b.get("mez_protection") is None and b.get("mez_resist") is None,
       "should fail deliberately when the mez consumer lands")

    # ---- every row resolves against a table the engine actually has ----
    tables = set(json.load(open(os.path.join(ROOT, "data", "modifier_tables.json"),
                                encoding="utf-8"))["tables"])
    allrows = [e for p in by.values() for e in (p.get("self_effects") or [])
               if e.get("slow_resist_row") or e.get("mez_row")]
    ok("every back-filled row names a modifier table the engine has",
       all(r.get("modifier_table") in tables for r in allrows),
       f"{len(allrows)} rows checked")

    print(f"\npower-protection back-fill battery: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
