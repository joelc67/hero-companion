"""The mode/meter classification, and the three ways it can be wrong.

`tags` is the client's own gate for its modes and meters. Reading it was the
2026-08-08 finding; classifying it correctly is the work, and the classification
can fail in three directions, each of which is checked here:

  * SKIP SOMETHING REAL - the first version dropped every tagged group, which
    would have deleted Blaze's own Fire DoT along with Fiery Embrace.
  * TAKE SOMETHING CONDITIONAL - crediting a mode-gated group unconditionally is
    the Fiery Embrace inflation this project has warned about since 2026-08-06.
  * TAKE SOMETHING TWICE - Defiance is derived by v36 from cast time and area,
    so the client's own Defiance templates must never be added.

Usage: python tools/test_mode_tags.py
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
    import mode_tags as mt                                    # noqa: E402
    from add_wind_control import client_index, effects_from   # noqa: E402
    import server as srv                                      # noqa: E402

    cl = client_index()

    # ---- the table itself ----
    ok("every entry carries a class AND its evidence",
       all(isinstance(v, tuple) and len(v) == 2 and v[0] in
           (mt.LABEL, mt.PROB, mt.MODE, mt.SCENARIO, mt.DERIVED) and v[1].strip()
           for v in mt.TAGS.values()), f"{len(mt.TAGS)} entries")
    ok("the classes are what the client shows them to be, not guesses from the "
       "tag NAME - PowerBoostA is a gate and 'Damage' is a label",
       mt.TAGS["PowerBoostA"][0] == mt.MODE and mt.TAGS["Damage"][0] == mt.LABEL,
       "three mechanical tests were tried and each got some of the 48 wrong "
       "in both directions; this is why the table is hand-adjudicated")

    # ---- the disposition each class produces ----
    ok("a group with NO tags is taken", mt.group_disposition(None) == "take"
       and mt.group_disposition([]) == "take")
    ok("a LABEL group is taken - it is the power's own effect",
       mt.group_disposition(["FireBlastBonusDoT"]) == "take")
    ok("a MODE group is skipped", mt.group_disposition(["FieryEmbrace"]) == "skip")
    ok("a SCENARIO group is skipped", mt.group_disposition(["Containment"]) == "skip")
    ok("a DERIVED group is skipped (v36 already adds Defiance)",
       mt.group_disposition(["Defiance"]) == "skip")
    ok("a PROB group is WEIGHTED, never skipped and never taken whole",
       mt.group_disposition(["Overpower"]) == "weight")
    ok("the STRICTEST class wins when a group carries several",
       mt.group_disposition(["FireBlastBonusDoT", "FieryEmbrace"]) == "skip"
       and mt.group_disposition(["CritLarge", "ScrapperCrit_ST"]) == "weight")
    ok("an UNKNOWN tag is refused, not guessed",
       mt.group_disposition(["SomethingNewInAPatch"]) == "unknown")

    # ---- it reaches the extractor, and the extractor refuses ----
    refuse, skipped = set(), {}
    fn = next(f for f in cl if f.endswith("Fiery_Aura.Blazing_Aura"))
    effects_from(cl[fn], refuse, skipped)
    ok("Blazing Aura's FieryEmbrace group is skipped AND counted, not silent",
       skipped.get("tag:FieryEmbrace") == 1, f"{skipped}")
    ok("...and its own unconditional Fire damage still comes through",
       any(r["damage_type"] == "Fire" for r in
           effects_from(cl[fn], set(), {})[0]))

    # ---- the LABEL bug the first version had ----
    blaze = next(f for f in cl if f.endswith("Fire_Blast.Blaze")
                 and f.startswith("Blaster"))
    dmg = effects_from(cl[blaze], set(), {})[0]
    # ⚠ the DoT group carries NO entity test, so it lands at pv_mode 0 - a first
    # version of this check filtered on pv_mode == 1 and missed it entirely.
    ok("Blaze keeps its FireBlastBonusDoT damage - a LABEL, not a gate",
       any(abs(r["scale"] - 0.225) < 1e-9 and abs(r["duration"] - 4.1) < 1e-9
           for r in dmg),
       "the first version of the skip dropped this: unconditional damage, "
       "stated in the power's own help, on 29 Fire attacks")

    # ---- the self +damage buff class is LANDED, measured through the route ----
    BU = next(f for f in srv.POWER_BY_FULL if f.endswith("Battle_Axe.Build_Up"))
    ATK = next(f for f in srv.POWER_BY_FULL
               if f.startswith("Scrapper_Melee.Battle_Axe.")
               and (srv.POWER_BY_FULL[f].get("damage_effects")))
    c = srv.app.test_client()

    def calc(names):
        return c.post("/build/calculate", json={
            "archetype": "Class_Scrapper",
            "powers": [{"full_name": n, "slots": [None], "slotCount": 1}
                       for n in names]}).get_json() or {}

    a, b = calc([ATK]), calc([ATK, BU])
    ok("Build Up's self +damage buff REACHES the totals at its duty cycle",
       (b.get("damage_buff") or 0) > 0 and not (a.get("damage_buff") or 0),
       f"damage_buff {a.get('damage_buff')} -> {b.get('damage_buff')} "
       f"(scale 8.0 over 10s on a 90s recharge)")
    ok("...and it moves the attack's DPS, which is the point",
       (b.get("offense") or {}).get("st_dps", 0)
       > (a.get("offense") or {}).get("st_dps", 0),
       f"ST DPS {(a.get('offense') or {}).get('st_dps')} -> "
       f"{(b.get('offense') or {}).get('st_dps')}")
    row = next(r for r in srv.POWER_BY_FULL[BU]["self_effects"]
               if r["effect"] == "DamageBuff")
    ok("...carried by the v39 mode machinery, not a flat add",
       row.get("mode") is True and row.get("host_recharge") == 90.0
       and row.get("duration") == 10.0)

    # ---- Defiance must never be in the data ----
    powers = json.load(open(os.path.join(ROOT, "data", "powers.json"),
                            encoding="utf-8"))
    defiance_scales = {round(float(t.get("scale") or 0), 4)
                       for r in cl.values() for g in (r.get("effects") or [])
                       if "Defiance" in (g.get("tags") or [])
                       for t in (g.get("templates") or [])}
    # ⚠ THIS IS WHY THE DERIVED SKIP IS LOAD-BEARING. A first version of this
    # check asserted the Defiance templates were all scale 0.0 - the note this
    # project carried - and they are NOT: 24 distinct non-zero scales up to
    # 0.176. Taking them would add real damage on top of the v36 derivation.
    ok("Defiance's client templates carry REAL values, so the skip is what "
       "prevents a double-count - it is not a formality",
       len(defiance_scales - {0.0}) > 10,
       f"{len(defiance_scales)} distinct scales, max {max(defiance_scales)}")
    ok("...and none of them reached our data",
       not any("Defiance" in json.dumps(p.get("self_effects") or [])
               for lst in powers.values() for p in lst))

    # ---- and the standing check is wired to the same table ----
    import reality_check_mode_tags as rc                        # noqa: E402
    ok("the reality check imports the SAME table (one copy of the rule)",
       rc.TAGS is mt.TAGS)

    print(f"\nmode-tag battery: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
