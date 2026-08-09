"""Wind Control: a whole powerset added from the game client.

Twenty records across two archetypes, plus the powerset entries that make them
selectable and the summon specs that make the pets real. Everything here is
checked against the CLIENT, and the mappings it relies on were measured against
the powers we already hold - never a wiki, never a guess.

The checks that matter most are the ones that would catch a *plausible* mistake:
a cone attack whose damage got written as a self buff, a mode-gated power priced
as though it were always on, a pet that resolves to the wrong entity.

Usage: python tools/test_wind_control.py
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
    psets = json.load(open(os.path.join(ROOT, "data", "powersets.json"), encoding="utf-8"))
    summ = json.load(open(os.path.join(ROOT, "data", "summons.json"), encoding="utf-8"))
    CS, DS = "Controller_Control.Wind_Control", "Dominator_Control.Wind_Control"
    by = {p["full_name"]: p for _ps, lst in powers.items() for p in lst}

    ok("both archetypes' Wind Control exists, 10 powers each",
       len(powers.get(CS) or []) == 10 and len(powers.get(DS) or []) == 10,
       f"{len(powers.get(CS) or [])} / {len(powers.get(DS) or [])}")
    ok("every record is marked as client-added (so it can be regenerated)",
       all(p.get("added_from_client") for p in powers[CS] + powers[DS]))
    lv = [(p["display_name"], p["level_available"]) for p in powers[CS]]
    ok("the level ladder matches the client +1 (Updraft 1 ... Vortex 26)",
       lv[0][1] == 1 and lv[-1] == ("Vortex", 26) and [x[1] for x in lv] == sorted(x[1] for x in lv),
       f"{lv}")

    # ---- the trap that would be easy to get wrong ----
    tg = by[f"{CS}.Thundergust"]
    ok("Thundergust's damage went to FOES, not to self",
       tg["damage_effects"] and not any(e.get("effect") == "DamageBuff"
                                        for e in tg["self_effects"]),
       "it is target_type Self (centred on you) but targets_affected Foe - "
       "reading target_type would have written a cone attack as a self buff")
    ws = by[f"{CS}.Wind_Shear"]
    ok("Wind Shear is a TOGGLE with foe debuffs and no damage",
       ws["power_type"] == 2 and ws["debuff_effects"] and not ws["damage_effects"])
    cs = by[f"{CS}.Clear_Skies"]
    ok("Clear Skies carries NOTHING - all of its effects are mode-gated",
       not any(cs[k] for k in ("damage_effects", "control_effects",
                               "debuff_effects", "self_effects", "buff_effects")),
       "gated on `kClearSkies Source.Mode?`; pricing it would invent a mode the "
       "engine has no model for")

    # ---- control rows, on the 539-power convention ----
    dd = by[f"{CS}.Downdraft"]
    held = [e for e in dd["control_effects"] if e["mez"] == "Held"]
    ok("Downdraft holds, with magnitude in nmag and duration-scale in scale",
       held and all(e["kind"] == "hard" for e in held)
       and any(e["nmag"] >= 2 for e in held),
       f"{[(e['mez'], e['scale'], e['nmag'], e['pv_mode']) for e in held][:2]}")
    # ⚠⚠ THIS CHECK USED TO PASS FOR THE WRONG REASON. It compared Downdraft's
    # rows across the two archetypes and found them different - but the whole
    # difference was the Containment / Domination group, which is MODE-GATED
    # (client `tags`) and must not be priced at all. Once those are dropped the
    # two Downdrafts are legitimately identical, and the old check went red.
    # What is actually true, and is pinned instead: FIVE of the ten powers still
    # differ, and where the two agree it is because the client's only difference
    # was the gated group - the per-archetype magnitude then comes from the
    # shared modifier table's archetype column, not from the row.
    _K = ("damage_effects", "control_effects", "debuff_effects",
          "self_effects", "buff_effects", "heal_effects")
    _differ = [p["power_name"] for p in powers[CS]
               if any(json.dumps(p[k], sort_keys=True)
                      != json.dumps(by[f"{DS}.{p['power_name']}"][k], sort_keys=True)
                      for k in _K)]
    ok("the Dominator's rows are not a blanket copy - 5 of the 10 still differ",
       len(_differ) == 5, f"{sorted(_differ)}")
    ok("...and Downdraft is one of the five that now AGREE, because the client's "
       "only difference there was Containment vs Domination",
       "Downdraft" not in _differ
       and [e["scale"] for e in by[f"{DS}.Downdraft"]["control_effects"]]
       == [e["scale"] for e in dd["control_effects"]],
       "the archetype's own magnitude rides the modifier table, not the row")

    # ---- categories and enhancements came from OUR vocabulary ----
    sc = json.load(open(os.path.join(ROOT, "data", "set_categories.json"), encoding="utf-8"))
    cat_ids = {c["id"] for c in sc["categories"]}
    enh_ids = {c["id"] for c in sc["enhancement_classes"]}
    allp = powers[CS] + powers[DS]
    ok("every accepted set-category id is one our data defines",
       all(i in cat_ids for p in allp for i in p["accepted_set_category_ids"]))
    ok("every accepted enhancement id is one our data defines",
       all(i in enh_ids for p in allp for i in p["accepted_enhancement_type_ids"]))
    ok("the two category aliases landed (Targeted AoE / Universal Damage)",
       any("Targeted AoE Damage" in p["accepted_set_categories"] for p in allp)
       and any("Universal Damage" in p["accepted_set_categories"] for p in allp))

    # ---- pets ----
    vac, vor = by[f"{CS}.Vacuum"], by[f"{CS}.Vortex"]
    ok("Vacuum and Vortex summon entities our pet model actually has",
       vac["summons"] == ["Pets_Wind_Control_Vacuum_Controller"]
       and vor["summons"] == ["Pets_Wind_Control_Vortex"],
       "client spellings are Pets_WindControl_* - resolved by normalising "
       "underscores, a rule proven on 570 existing summons")
    ok("JOEL'S RULING: Controller and Dominator SHARE the Vortex entity",
       by[f"{DS}.Vortex"]["summons"] == vor["summons"] == ["Pets_Wind_Control_Vortex"])
    spec = summ["powers"].get(f"{CS}.Vortex")
    ok("Vortex's summon spec says permanent, because the client says 99999s",
       spec and spec["permanent"] is True and spec["duration"] >= 99999)
    ok("Vacuum's says NOT permanent, because the client says 8s",
       summ["powers"][f"{CS}.Vacuum"]["permanent"] is False)

    # ---- selectable, and priced, through the real routes ----
    c = srv.app.test_client()
    for at in ("Class_Controller", "Class_Dominator"):
        names = [s["display_name"] for s in c.get(f"/powersets/{at}").get_json()["primary"]]
        ok(f"{at.split('_')[1]} is offered Wind Control", "Wind Control" in names)
    served = c.get(f"/powers/{CS}").get_json()["powers"]
    ok("the set serves 10 powers in level order",
       len(served) == 10 and [p["level_available"] for p in served]
       == sorted(p["level_available"] for p in served))
    t = c.post("/build/calculate", json={"archetype": "Class_Controller", "powers": [
        {"full_name": f"{CS}.Updraft", "slots": [None], "slotCount": 1},
        {"full_name": f"{CS}.Vortex", "slots": [None], "slotCount": 1}]}).get_json()
    o = t.get("offense") or {}
    atk = (o.get("attacks") or [{}])[0]
    ok("Updraft is priced as an attack (Smashing, ~30.6 at cast 1.03)",
       abs((atk.get("damage") or 0) - 30.6) < 0.5 and atk.get("damage_types") == ["Smashing"],
       f"{atk.get('damage')} / {atk.get('damage_types')}")
    ok("the Vortex PET produces damage - the summon spec is wired",
       (o.get("pets") or []) and (o["pets"][0].get("dps_total") or 0) > 1,
       f"{[(p.get('name'), round(p.get('dps_total') or 0, 1)) for p in (o.get('pets') or [])]}")

    # ---- it does not disturb anything else ----
    ok("NEGATIVE CONTROL: no certified champion holds a Wind Control power",
       not [k for k, v in json.load(open(os.path.join(ROOT, "benchmarks",
                                                      "champions.json"), encoding="utf-8")).items()
            if any(str(p.get("full_name") if isinstance(p, dict) else p).startswith(
                ("Controller_Control.Wind_Control", "Dominator_Control.Wind_Control"))
                for p in v["picks"])])

    print(f"\nWind Control battery: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
