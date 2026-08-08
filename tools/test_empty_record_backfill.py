"""The empty-record back-fill is faithful, live, and did not overreach.

Two records were empty and are now populated. Everything interesting about this
patch is what it did NOT do, so most of these checks are negative:

  * it must not have taken the client's PvP group. Shield Defense's second group
    adds a Psionic defence vector, and our populated Brute/Scrapper/Tanker
    siblings all carry that at pv_mode 2, not in PvE.
  * it must not have touched Gamma Boost. The game's help says the regeneration
    and recovery halves are opposite ends of one health-scaling curve, so the
    client's flat 1.0/1.0 can never both apply.
  * it must not have moved a record that was already populated.
  * and the effects alone would have been INERT: both stubs also carried
    power_type 0 (a click), and the engine only counts self effects on an auto
    or a toggle. That correction is checked here as its own claim.

Usage: python tools/test_empty_record_backfill.py
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
    by = {p["full_name"]: p for _ps, lst in powers.items() for p in lst}
    MARK = "empty_record_row"
    touched = {fn for fn, p in by.items()
               if any(e.get(MARK) for e in (p.get("self_effects") or []))}

    BO = "Stalker_Defense.Ninjitsu.Smoke_Flash"          # displays "Bo Ryaku"
    AD = "Stalker_Defense.Shield_Defense.Active_Defense"

    ok("exactly two records were back-filled", touched == {BO, AD},
       f"{sorted(touched)}")

    bo = [e for e in by[BO]["self_effects"] if e.get(MARK)]
    ok("Bo Ryaku carries the client's all-damage resistance (8 types, 1.0)",
       len(bo) == 8 and {e["scale"] for e in bo} == {1.0}
       and all(e["effect"] == "Resistance" for e in bo)
       and {e["damage_type"] for e in bo} == {"Smashing", "Lethal", "Fire", "Cold",
                                              "Energy", "Negative", "Psionic", "Toxic"},
       f"{len(bo)} rows, types {sorted({e['damage_type'] for e in bo})}")
    ok("...at pv_mode 0 - the client gives it no PvP twin",
       all(e["pv_mode"] == 0 for e in bo))

    ad = [e for e in by[AD]["self_effects"] if e.get(MARK)]
    ok("Active Defense carries Melee defence + Smashing/Lethal resistance",
       sorted((e["effect"], e["damage_type"]) for e in ad)
       == [("Defense", "Melee"), ("Resistance", "Lethal"), ("Resistance", "Smashing")],
       f"{sorted((e['effect'], e['damage_type']) for e in ad)}")
    ok("...at pv_mode 1, matching the populated siblings (a PvP twin exists)",
       all(e["pv_mode"] == 1 for e in ad))
    sib = by["Brute_Defense.Shield_Defense.Active_Defense"]["self_effects"]
    ok("...and the SIBLING's shape is what it was copied from - same scale",
       {e["scale"] for e in ad} == {1.5}
       and {e["scale"] for e in sib if e["pv_mode"] == 1} == {1.5})

    # ---- THE NEGATIVE CONTROLS ----
    ok("NEGATIVE CONTROL: the PvP-only Psionic defence vector was NOT taken",
       not any(e["damage_type"] == "Psionic" for e in ad),
       "the client's second group adds it; the siblings carry it at pv_mode 2")
    gb = [e for e in (by["Scrapper_Defense.Radiation_Armor.Gamma_Boost"]
                      .get("self_effects") or [])]
    ok("NEGATIVE CONTROL: Gamma Boost was NOT back-filled (health-scaling class)",
       not gb, "the game's help makes its flat 1.0/1.0 two ends of one curve")
    ok("NEGATIVE CONTROL: an already-populated record gained nothing",
       not any(e.get(MARK) for e in sib))
    ok("NEGATIVE CONTROL: a redirect stub stayed empty by design",
       not (by.get("Redirects.Kinetics.SiphonPower", {}).get("self_effects") or []))

    # ---- power_type: the half that makes the rest visible ----
    ok("Bo Ryaku is an AUTO now, as the game's short help says",
       by[BO].get("power_type") == 1 and by[BO].get("power_type_was") == 0)
    ok("Active Defense is a TOGGLE now, agreeing with its siblings",
       by[AD].get("power_type") == 2
       and by["Brute_Defense.Shield_Defense.Active_Defense"].get("power_type") == 2)

    # ---- LIVE, through the real route ----
    c = srv.app.test_client()

    def calc(names, at="Class_Stalker"):
        pw = [{"full_name": n, "slots": [None], "slotCount": 1} for n in names]
        return c.post("/build/calculate",
                      json={"archetype": at, "powers": pw}).get_json()

    def res(r, k):
        return round(((r.get("resistance") or {}).get(k) or {}).get("value", 0), 2)

    def dfn(r, k):
        return round(((r.get("defense") or {}).get(k) or {}).get("value", 0), 2)

    base = ["Stalker_Melee.Ninja_Blade.Sting_of_the_Wasp"]
    a, b = calc(base), calc(base + [BO])
    ok("Bo Ryaku's resistance REACHES the totals (7.5% to all eight)",
       res(a, "Smashing") == 0.0 and res(b, "Smashing") == 7.5
       and res(b, "Toxic") == 7.5 and res(b, "Psionic") == 7.5,
       f"{res(a, 'Smashing')} -> {res(b, 'Smashing')}  "
       f"(1.0 x Melee_Res_Dmg[Stalker] 0.075)")
    d = calc(base + [AD])
    ok("Active Defense reaches the totals at the Stalker column",
       dfn(d, "Melee") == 11.25 and res(d, "Smashing") == 11.25,
       f"def Melee {dfn(d, 'Melee')}, res S {res(d, 'Smashing')} "
       f"(Brute reads 12.75 - the AT column, not a bug)")
    ok("NEGATIVE CONTROL: Psionic defence stays 0 in PvE", dfn(d, "Psionic") == 0.0)
    ok("NEGATIVE CONTROL: an untouched Ninjitsu power still reads 0 resistance",
       res(calc(base + ["Stalker_Defense.Ninjitsu.Ninja_Reflexes"]), "Smashing") == 0.0)

    # ---- exposure, counted not assumed ----
    ch = json.load(open(os.path.join(ROOT, "benchmarks", "champions.json"),
                        encoding="utf-8"))
    hit = [k for k, v in ch.items()
           if any((p.get("full_name") if isinstance(p, dict) else p) in touched
                  for p in (v.get("picks") or []))]
    ok("champion exposure is ZERO, so no certified score moved", not hit,
       f"{len(ch)} contexts checked, {len(hit)} hold either power")

    print(f"\nempty-record back-fill battery: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
