"""v41 defence-debuff resistance: faithful data, a live term, and the traps pinned.

The expensive mistakes in this family are all about adding the WRONG data or
reading the RIGHT data in the wrong place, so most of these checks are negative:

  * aspect=Strength Base_Defense templates are the Alpha boost definitions
    (defence STRENGTH). Keying on the attrib alone would have converted them.
  * a value the engine computes but never SURFACES cannot be verified -
    def_debuff_resist lives at bonus_extras.def_debuff_resist.value, and probing
    the top level returns None however well the branch works.
  * a CLICK must not read as always-on. Elude grants the biggest DDR in the game
    for 180 seconds on a 1000-second recharge.
  * the v39 `mode` dedup keyed on (scale, duration, stack) with no effect name;
    two families sharing those numbers on one power would swallow each other.

Usage: python tools/test_def_debuff_resist.py
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
    import server as srv          # noqa: E402
    import first_principles as fp  # noqa: E402

    powers = json.load(open(os.path.join(ROOT, "data", "powers.json"), encoding="utf-8"))
    by = {p["full_name"]: p for _ps, lst in powers.items() for p in lst}

    def rows(fn):
        return [e for e in (by.get(fn, {}).get("self_effects") or []) if e.get("ddr_row")]

    carried = [p for p in by.values()
               if any(e.get("ddr_row") for e in (p.get("self_effects") or []))]

    # ---- coverage, against the denominator the patcher printed ----
    ok("back-fill covers 178 powers", len(carried) == 178,
       f"{len(carried)} powers carry ddr_row")

    # ---- faithful to the client, on powers read by hand ----
    agile = rows("Scrapper_Defense.Super_Reflexes.Agile")
    ok("Agile carries the client's 0.2 on Melee_Res_Boolean",
       len(agile) == 1 and agile[0]["scale"] == 0.2
       and agile[0]["modifier_table"] == "Melee_Res_Boolean",
       f"{[(r['scale'], r['modifier_table']) for r in agile]}")
    hide = rows("Scrapper_Defense.Invulnerability.Tough_hide")
    ok("Tough Hide carries the client's 0.25 on Melee_Ones",
       len(hide) == 1 and hide[0]["scale"] == 0.25
       and hide[0]["modifier_table"] == "Melee_Ones")
    ok("every row is named DefDebuffResist and takes no enhancement",
       all(e["effect"] == "DefDebuffResist" and e["enhance_aspect"] == "None"
           for p in carried for e in p["self_effects"] if e.get("ddr_row")),
       "no IO category names DDR, so it must not read an enhancement aspect")

    # ---- THE NEGATIVE CONTROLS: what must NOT have happened ----
    alpha = [e for e in (by.get("Incarnate.Alpha_Silent.Defense_Buff_Rare", {})
                         .get("self_effects") or []) if e.get("ddr_row")]
    ok("NEGATIVE CONTROL: aspect=Strength Base_Defense (Alpha boost definitions) "
       "were not converted", not alpha)
    ok("NEGATIVE CONTROL: an ordinary attack got no row",
       not rows("Scrapper_Melee.Martial_Arts.Thunder_Kick"))
    ok("NEGATIVE CONTROL: a resistance-based armour the client grants none reads none",
       not rows("Scrapper_Defense.Fiery_Aura.Fire_Shield"))

    tables = set(json.load(open(os.path.join(ROOT, "data", "modifier_tables.json"),
                                encoding="utf-8"))["tables"])
    ok("every row names a modifier table the engine has",
       all(e["modifier_table"] in tables
           for p in carried for e in p["self_effects"] if e.get("ddr_row")))

    # ---- the term is LIVE, through the real route ----
    c = srv.app.test_client()

    def calc(names, at="Class_Scrapper"):
        pw = [{"full_name": n, "slots": [None], "slotCount": 1} for n in names]
        return c.post("/build/calculate",
                      json={"archetype": at, "powers": pw}).get_json()

    def ddr_of(resp):
        return ((resp.get("bonus_extras") or {})
                .get("def_debuff_resist") or {}).get("value")

    base = ["Scrapper_Melee.Martial_Arts.Thunder_Kick"]
    SR = ["Scrapper_Defense.Super_Reflexes." + n
          for n in ("Agile", "Dodge", "Lucky", "Focused_Senses", "Evasion")]
    a, one, five = calc(base), calc(base + SR[:1]), calc(base + SR)
    ok("v41: Agile's DDR REACHES the totals at the resolved magnitude",
       ddr_of(a) == 0.0 and abs(ddr_of(one) - 6.92) < 0.01,
       f"{ddr_of(a)} -> {ddr_of(one)}  (0.2 x Melee_Res_Boolean[Scrapper] 0.346)")
    ok("...and stacks across powers, as the game does",
       abs(ddr_of(five) - 48.44) < 0.01, f"five SR powers -> {ddr_of(five)}")
    ok("NEGATIVE CONTROL: a build the client grants none still reads 0.0",
       ddr_of(calc(base + ["Scrapper_Defense.Fiery_Aura.Fire_Shield"])) == 0.0)

    # ⚠ A CLICK IS DUTY-CYCLED. Elude is 34.6% for 180s on a 1000s recharge; if
    # it ever reads as its full magnitude the v39 `mode` wiring has come undone.
    elude = ddr_of(calc(base + ["Scrapper_Defense.Super_Reflexes.Elude"]))
    ok("a CLICK is duty-cycled, not credited as always-on",
       0.0 < elude < 10.0, f"Elude reads {elude}, full magnitude would be 34.6")

    # ⚠ the mode dedup must separate FAMILIES, and this one is pinned at the
    # SOURCE on purpose: the collision needs two families sharing (scale,
    # duration, stack) on ONE power, which no shipped power does today, so a
    # behavioural probe would pass just as happily with the bug back in.
    eng = open(os.path.join(ROOT, "server", "engine.py"), encoding="utf-8").read()
    ok("the mode dedup key carries the effect name, so families cannot swallow "
       "each other", '_key = (fx.get("effect"), fx.get("scale"),' in eng)
    bu = calc(base + ["Scrapper_Melee.Martial_Arts.Focus_Chi"] + SR[:1])
    ok("...and a v39 self +damage power beside a DDR power keeps both",
       abs(ddr_of(bu) - 6.92) < 0.01,
       f"ddr still {ddr_of(bu)} with a self +damage power in the build")

    # ---- the scorer consumes it, and the direction is right ----
    src = open(os.path.join(ROOT, "server", "first_principles.py"),
               encoding="utf-8").read()
    ok("first_principles reads DDR from bonus_extras, never the top level",
       'get("bonus_extras") or {}).get("def_debuff_resist")' in src
       and 'totals.get("def_debuff_resist")' not in src)
    ok("...and applies it to the incoming pressure, capped at the game's 95%",
       'sc.get("def_debuff_in", 0.0) * (1.0 - _ddr)' in src and "0.95" in src)
    # >= not ==: this pin exists to prove the bump HAPPENED with the change, and
    # freezing it would fail every later term for no reason (v42 did exactly that).
    ok("MODEL_VERSION moved with the scoring change", fp.MODEL_VERSION >= 41,
       f"MODEL_VERSION = {fp.MODEL_VERSION}")

    print(f"\ndefence-debuff-resistance battery: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
