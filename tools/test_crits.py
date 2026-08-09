"""v44 critical hits, and the three leaks that measuring caught.

A crit adds 100% of an attack's own damage at a chance the client states per
power. The chance is easy; deciding WHICH records may have one is where this
went wrong three times, and each wrong version looked perfectly reasonable:

  1. A chance of 1.0 is not a die roll. StealthCrit reads 1.0 because it is the
     guaranteed critical while HIDDEN, so taking it doubled Kyokan and Mask
     Presence unconditionally.
  2. Pet and redirect records carry the crit tags; a pet does not crit as its
     owner's archetype.
  3. Our Epic.* records are SHARED across archetypes, so crediting them handed
     criticals to Defenders, Tankers, Peacebringers and Warshades through their
     epic picks. Exposure read 14 of 24 until that was fixed, then 2.

Usage: python tools/test_crits.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

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
    import first_principles as fp                     # noqa: E402
    import server as srv                              # noqa: E402
    from add_wind_control import client_index         # noqa: E402

    powers = json.load(open(os.path.join(ROOT, "data", "powers.json"),
                            encoding="utf-8"))
    rows = [(p["full_name"], r) for lst in powers.values() for p in lst
            for r in (p.get("damage_effects") or []) if r.get("crit_row")]
    names = {fn for fn, _ in rows}

    ok("crit rows exist and are marked so they can be stripped",
       len(rows) == 253 and len(names) == 247, f"{len(rows)} rows, {len(names)} powers")

    # ---- 1. only the two archetypes the game gives a crit inherent ----
    spaces = sorted({fn.split(".")[0] for fn in names})
    ok("ONLY Scrapper and Stalker melee records carry one",
       spaces == ["Scrapper_Melee", "Stalker_Melee"], f"{spaces}")
    ok("NEGATIVE CONTROL: no Epic record has one - they are SHARED across "
       "archetypes and would hand crits to Defenders through their epic picks",
       not any(fn.startswith("Epic.") for fn in names))
    ok("NEGATIVE CONTROL: no pet or redirect record has one",
       not any(fn.startswith(("Pets.", "Redirects.", "Mastermind_Pets.",
                              "Villain_Pets.")) for fn in names))
    ok("NEGATIVE CONTROL: no Blaster or Sentinel record has one - Defiance and "
       "Opportunity are their inherents, not a critical",
       not any(fn.startswith(("Blaster_", "Sentinel_")) for fn in names))

    # ---- 2. every chance is a real die roll from the client ----
    chances = sorted({r["probability"] for _, r in rows})
    ok("every chance is strictly between 0 and 1 - a 1.0 'crit' is the "
       "guaranteed one while HIDDEN, a play state and not a roll",
       all(0 < c < 1 for c in chances), f"{chances}")
    ok("the floor of 0.05 is the commonest, which is the minion rate",
       max(chances, key=lambda c: sum(1 for _, r in rows
                                      if r["probability"] == c)) == 0.05)

    # ---- 3. the size is the client's, not a multiplier I chose ----
    cl = client_index()
    HACK = "Scrapper_Melee.Broad_Sword.Hack"
    base = next(r for r in srv.POWER_BY_FULL[HACK]["damage_effects"]
                if not r.get("crit_row") and r["pv_mode"] == 1)
    crit = next(r for r in srv.POWER_BY_FULL[HACK]["damage_effects"]
                if r.get("crit_row"))
    ok("a crit adds 100% of the attack's own damage - the crit row IS the base "
       "row again, which is what the client says",
       abs(crit["scale"] - base["scale"]) < 1e-9,
       f"base {base['scale']} / crit {crit['scale']} at {crit['probability']}")
    # ⚠ read the CHILD's chance, not the outer group's - the crit rows live one
    # level down and a first version of this line read `g` while looping `c`.
    client_chances = sorted({round(float(c.get("chance") or 0), 3)
                             for g in (cl[HACK].get("effects") or [])
                             for c in [g] + list(g.get("child_effects") or [])
                             if any("Crit" in t for t in (c.get("tags") or []))})
    ok("...and the chance was read from the client, not chosen",
       crit["probability"] in client_chances, f"client offers {client_chances}")

    # ---- 4. it reaches the engine ----
    c = srv.app.test_client()

    def dps(names_):
        r = c.post("/build/calculate", json={
            "archetype": "Class_Scrapper",
            "powers": [{"full_name": n, "slots": [None], "slotCount": 1}
                       for n in names_]}).get_json() or {}
        return (r.get("offense") or {}).get("st_dps") or 0.0

    live = dps([HACK])
    ok("the crit row reaches the served DPS (probability-weighted)", live > 0,
       f"Hack ST DPS {live}")

    # ---- 5. exposure, counted not assumed ----
    ch = json.load(open(os.path.join(ROOT, "benchmarks", "champions.json"),
                        encoding="utf-8"))
    exposed = [k for k, v in ch.items()
               if any((p.get("full_name") if isinstance(p, dict) else p) in names
                      for p in v["picks"])]
    ok("exposure is 2 of 24 - the Scrapper and the Stalker, and nobody else",
       len(exposed) == 2 and len(ch) == 24
       and {k.split("|")[0] for k in exposed} == {"Class_Scrapper",
                                                  "Class_Stalker"},
       f"{[k.split('|')[0] for k in exposed]}")
    ok("MODEL_VERSION is bumped - this moves scores", fp.MODEL_VERSION == 44)

    print(f"\ncrit battery: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
