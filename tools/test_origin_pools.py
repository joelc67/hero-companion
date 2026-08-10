"""GADGETRY and UTILITY BELT - the last two power pools the tool did not have.

Ten records the game ships and we could not plan with. What is pinned here is
not just "they exist": a pool needs three things an archetype set does not, and
each of them is a way to be wrong.

  1. PREREQUISITES the game states outright, enforced by the legality gate.
  2. THE ONE-ORIGIN-POOL RULE - both are origin-themed, so a build may hold one
     of them or the other, never both, and never a fifth pool of any kind.
  3. THE NEVER-PICKABLE FREE RIDER - Turbo Boost and Athletics carry the
     auto-issue sentinel and are deliberately absent.

⚠⚠ AND THE THING THAT NEARLY SHIPPED WRONG. The client writes an attack's
damage ONCE PER ARCHETYPE and again per game state, so Wrist Blaster carries 23
damage groups for what is one attack. Reading them all made a 20x attack. Two
signals separate the real row from the variants, and both are checked below:
`tags` (the client's own mode gate - FieryEmbrace, Containment, Domination,
Overpower, the Scrapper crits) and a requires expression that still says
something after the pure-TARGETING clauses are struck out.

Usage: python tools/test_origin_pools.py [--sabotage]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

PASS = FAIL = 0
GAD, UB = "Pool.Gadgetry", "Pool.Utility_Belt"


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
    import server as srv                                   # noqa: E402
    from add_wind_control import client_index, effects_from  # noqa: E402

    powers = json.load(open(os.path.join(ROOT, "data", "powers.json"),
                            encoding="utf-8"))
    by = {p["full_name"]: p for _ps, lst in powers.items() for p in lst}
    psets = json.load(open(os.path.join(ROOT, "data", "powersets.json"),
                           encoding="utf-8"))

    # ---- 1. the records exist, and the free riders do not ----
    ok("Gadgetry ships 5 pickable powers", len(powers.get(GAD, [])) == 5,
       f"{[p['display_name'] for p in powers.get(GAD, [])]}")
    ok("Utility Belt ships 5 pickable powers", len(powers.get(UB, [])) == 5,
       f"{[p['display_name'] for p in powers.get(UB, [])]}")
    ok("the auto-issue free riders are ABSENT (the Fly_Boost ruling again)",
       f"{GAD}.Turbo_Boost" not in by and f"{UB}.Athletics" not in by,
       "available_level 4294967295 - the game never offers them as a pick")
    ok("both powersets are registered so the picker can list them",
       {GAD, UB} <= {s["full_name"] for s in psets["pools"]})

    # ---- 2. prerequisites, read from the game's own requires expression ----
    need = {fn.split(".")[-1]: srv._prereq_need(fn)
            for fn in by if fn.startswith((GAD + ".", UB + "."))}
    ok("the two L14 attacks need TWO other pool powers, as the game says",
       need["Blaster_Barrage"] == 2 and need["Flying_Kick"] == 2, f"{need}")
    ok("...as do the two L20 powers",
       need["Force_Barrier"] == 2 and need["Life_Support_System"] == 2)
    ok("NEGATIVE CONTROL: the tier-1 powers need nothing",
       need["Nano_Net"] == 0 and need["Bolas"] == 0)
    ok("...and Jetpack / Freerunning need nothing either - their requires "
       "names no sibling, only an archetype",
       need["Jetpack"] == 0 and need["Freerunning"] == 0)

    # ---- 3. the LEGALITY GATE enforces them, which is what protects a wave ----
    ch = json.load(open(os.path.join(ROOT, "benchmarks", "champions.json"),
                        encoding="utf-8"))
    fixture = None
    for key, v in ch.items():
        picks = {p.get("full_name") if isinstance(p, dict) else p for p in v["picks"]}
        held = {p.rsplit(".", 1)[0] for p in picks if p.startswith("Pool.")}
        if held & srv._EXCLUSIVE_POOLS:
            continue                       # would fail the one-origin rule anyway
        prim, sec = key.split("|")[1], key.split("|")[2]
        for pool in held:
            mine = {p for p in picks if p.startswith(pool + ".")}
            if len(mine) != 3 or not srv._picks_legal(set(picks), prim, sec):
                continue
            fixture = (key, prim, sec, picks, pool, mine)
            break
        if fixture:
            break
    ok("a fixture exists: a legal certified build with a 3-pick swappable pool",
       fixture is not None)
    key, prim, sec, picks, pool, mine = fixture
    G3 = [f"{GAD}.Nano_Net", f"{GAD}.Wrist_Blaster", f"{GAD}.Force_Barrier"]
    swapped = (picks - mine) | set(G3)
    ok("swapping that pool for Gadgetry (2 siblings + Force Barrier) is LEGAL",
       srv._picks_legal(swapped, prim, sec),
       f"{key.split('|')[0]} -{pool.split('.')[-1]} +Gadgetry, {len(swapped)} picks")
    # ⚠ SWAP, NEVER DROP. Removing a sibling shortens the build, and a shorter
    # build can be refused for reasons that have nothing to do with prereqs.
    # The filler comes from a set the build ALREADY holds, so no pool count and
    # no ladder rung moves - only the prerequisite can explain the refusal.
    filler = next(f for f, p in by.items()
                  if p.get("powerset_full_name") == prim and f not in picks
                  and p.get("level_available", 99) <= 20)
    one_sib = (swapped - {f"{GAD}.Nano_Net"}) | {filler}
    ok("...and the SAME SIZE build with only ONE sibling is ILLEGAL",
       not srv._picks_legal(one_sib, prim, sec),
       f"-Nano Net +{filler.split('.')[-1]}, still {len(one_sib)} picks")
    # ⚠ The control must differ from the negative case in ONE respect only.
    # Swapping the filler into the ORIGINAL build is not that: pulling a
    # Fighting pick can strand Tough's own prerequisite, so it fails for an
    # unrelated reason (it did, first run). Swap the filler for FORCE BARRIER
    # instead - same set, same size, same pools; the only thing removed is the
    # power whose prerequisite was in question.
    ok("CONTROL FOR THE SWAP ITSELF: that same filler is legal when it "
       "replaces Force Barrier rather than its prerequisite",
       srv._picks_legal((swapped - {f"{GAD}.Force_Barrier"}) | {filler},
                        prim, sec),
       "so the refusal above is the prerequisite, not the substitution")

    # ---- 4. one origin pool, and never a fifth pool ----
    ok("both pools are in the one-per-build origin group",
       {GAD, UB} <= srv._EXCLUSIVE_POOLS, f"{sorted(srv._EXCLUSIVE_POOLS)}")
    both = (picks - mine) | {f"{GAD}.Nano_Net", f"{GAD}.Wrist_Blaster",
                             f"{UB}.Bolas"}
    ok("holding Gadgetry AND Utility Belt is refused",
       not srv._picks_legal(both, prim, sec))
    c = srv.app.test_client()

    def verrs(fns, needle):
        pw = [dict(srv.POWER_BY_FULL.get(f) or {}, full_name=f, slots=[None])
              for f in fns]
        r = c.post("/build/validate", json={
            "archetype": "Class_Scrapper",
            "primary": "Scrapper_Melee.Martial_Arts",
            "secondary": "Scrapper_Defense.Dark_Armor", "powers": pw}).get_json()
        return [e for e in ((r or {}).get("errors") or []) if needle in e.lower()]

    ok("the USER-FACING validator says so too, in plain English",
       verrs([f"{GAD}.Nano_Net", f"{UB}.Bolas"], "origin"),
       f"{verrs([f'{GAD}.Nano_Net', f'{UB}.Bolas'], 'origin')[:1]}")
    ok("NEGATIVE CONTROL: one origin pool alone raises nothing",
       not verrs([f"{GAD}.Nano_Net"], "origin"))
    ok("the validator message names all five origin pools, not a stale three",
       all(n in " ".join(verrs([f"{GAD}.Nano_Net", f"{UB}.Bolas"], "origin"))
           for n in ("Sorcery", "Gadgetry", "Utility Belt")))

    # ---- 5. served, on the real route, to every archetype ----
    served = {}
    for at in srv.ARCHETYPES["archetypes"]:
        if not at.get("playable"):
            continue
        r = c.get(f"/powersets/{at['name']}").get_json() or {}
        served[at["name"]] = {p["full_name"] for p in (r.get("pools") or [])}
    missing = [a for a, s in served.items() if not {GAD, UB} <= s]
    ok(f"both pools are served to all {len(served)} archetypes "
       f"(N of M, the denominator is the archetype roster)",
       not missing and len(served) == 15, f"missing on {missing}")

    # ---- 6. the archetype gate the tool cannot express is RECORDED ----
    jp = by[f"{GAD}.Jetpack"]
    ok("Jetpack records the archetypes the game bars, rather than dropping them",
       jp.get("archetype_excluded") == ["Class_Peacebringer", "Class_Warshade"],
       f"{jp.get('archetype_excluded')}")
    ok("NEGATIVE CONTROL: an ungated pool power records no exclusion",
       "archetype_excluded" not in by[f"{GAD}.Nano_Net"])

    # ---- 7. THE ROW COUNTS, which is where this nearly shipped wrong ----
    wb = by[f"{GAD}.Wrist_Blaster"]
    pve = [e for e in wb["damage_effects"] if e["pv_mode"] == 1]
    ok("Wrist Blaster has ONE PvE damage row, not the client's 23 groups",
       len(pve) == 1 and abs(pve[0]["scale"] - 1.16) < 1e-9,
       "22 of them are per-archetype PvP copies and state-gated bonuses "
       "(Scrapper crit, containment, low-HP) that all name `critter` or "
       "`player` and so slipped a naive side test")
    ok("...and no Scrapper-crit scale (1.7) reached the record",
       all(abs(e["scale"] - 1.7) > 1e-9 for e in wb["damage_effects"]))
    pd = by[f"{UB}.Poisoned_Dagger"]
    ok("Poisoned Dagger keeps its Lethal hit and its Toxic DoT",
       sorted(round(e["scale"], 4) for e in pd["damage_effects"]
              if e["pv_mode"] == 1) == [0.1, 1.1])
    dmgdeb = [e for e in pd["debuff_effects"] if e["effect"] == "Damage"]
    ok("...and its -DMG, which the game's own short help states, "
       "from a group whose `chance` field reads 0.0 because it is UNSET",
       len(dmgdeb) == 8 and all(abs(e["scale"] - 0.8) < 1e-9 for e in dmgdeb),
       "one client template, eight damage types; the sign lives in the "
       "Ranged_Debuff_Dam table, which is negative")

    # ---- 8. `tags` IS the mode gate, and it is corpus-wide ----
    cl = client_index()
    tagged = sum(1 for r in cl.values() for g in (r.get("effects") or [])
                 if "FieryEmbrace" in (g.get("tags") or []))
    live = sum(1 for r in cl.values() for g in (r.get("effects") or [])
               if "FieryEmbrace" in (g.get("tags") or [])
               and any(t.get("scale") or t.get("magnitude")
                       for t in (g.get("templates") or [])))
    ok("the client carries a FieryEmbrace tag on 352 effect groups, 349 of them "
       "carrying real values - the gate this project recorded as 'not captured "
       "by the crawler' IS captured, and always was",
       tagged == 352 and live == 349, f"{tagged} tagged, {live} with values")
    bs = by["Brute_Melee.Broad_Sword.Boomerang_Slice"]
    ok("NEGATIVE CONTROL: no FieryEmbrace damage reached Boomerang Slice",
       all(e["damage_type"] != "Fire" for e in bs["damage_effects"]),
       "the 86-Brute-attack inflation this file warns about")

    # ---- 9. the two L20 powers actually price ----
    fb = by[f"{GAD}.Force_Barrier"]
    ab = [e for e in fb["self_effects"] if e["effect"] == "Absorb"]
    # ⚠ `.get`, not `[...]`. A sabotage run that POPPED this key crashed the
    # battery instead of failing this check, and a crash reports no FAIL line -
    # it read as "the battery missed it". A check must fail, not explode.
    ok("Force Barrier is an absorb worth a quarter of your max HP",
       len(ab) == 1 and abs((ab[0].get("max_hp_frac") or 0) - 0.25) < 1e-9,
       "decoded from `Max.kHitPoints source> .25 * @Strength *`, not assumed")
    # ...and the ENGINE has to agree, or the row is decoration.
    # ⚠ the payload shape matters: full_name + slots, exactly as the app posts.
    # A dict-spread of the record reads back None for everything.
    fbcalc = c.post("/build/calculate", json={
        "archetype": "Class_Scrapper",
        "powers": [{"full_name": f"{GAD}.Force_Barrier",
                    "slots": [None], "slotCount": 1}]}).get_json() or {}
    base_hp = (srv.ARCH_BY_NAME.get("Class_Scrapper") or {}).get("hitpoints") or 0
    _fbab = ((fbcalc.get("bonus_extras") or {}).get("absorb") or {}).get("value")
    ok("...and the engine turns that fraction into real absorb HP",
       _fbab is not None and abs(_fbab - 0.25 * base_hp) < 1.0,
       f"absorb {_fbab} vs 25% of {base_hp} base HP")
    ls = by[f"{UB}.Life_Support_System"]
    ok("Life Support System heals twice: the instant, and the 9-tick HoT",
       sorted(round(h["scale"], 4) for h in ls["heal_effects"]) == [0.9, 1.0],
       "1.0 instant + 0.1/tick x 9 ticks; the multiplier is the FULL-HEALTH "
       "floor of `(100-HP%)/X + Y` - the game says potency rises as health "
       "falls, and crediting that would need a scenario nobody has ruled on")
    import role_output                                            # noqa: E402
    ctx = {"modifier_tables": srv.MODIFIER_TABLES.get("tables", srv.MODIFIER_TABLES),
           "at_column": 0}
    team, self_, _rez = role_output.power_heal_output(ls, ctx)
    ok("...and role_output prices it as a real self-heal per second",
       self_ > 0 and team == 0.0, f"self {self_} hps, team {team}")

    # ---- 10. nothing certified moved ----
    exposed = [k for k, v in ch.items()
               if any((p.get("full_name") if isinstance(p, dict) else p)
                      .startswith((GAD + ".", UB + "."))
                      for p in v["picks"])]
    # ⚠ THIS CHECK USED TO ASSERT ZERO, AND WAS RIGHT TO. When the pools landed
    # (2026-08-08) no certified champion held one, so adding them could not have
    # moved a score - that was the claim, and it was true. The v43+v44 re-cert
    # then let the solver actually CHOOSE from them, and it did: both of the
    # follow-up wave's two supersedes picked one. Exposure is now 2, and that is
    # the pools earning their place rather than a defect. What still matters is
    # that they are only ever held by a build the solver re-derived under the
    # current model, never grandfathered in.
    ok("the pools are now CHOSEN by certified builds - 2 of 24, both of them "
       "champions the re-cert superseded",
       len(exposed) == 2 and len(ch) == 24,
       f"{[k.split('|')[0].replace('Class_','') for k in exposed]}")
    ok("...and every champion holding one was certified under the CURRENT model",
       all((ch[k].get("model_version") or 0) == 44 for k in exposed),
       "so none was grandfathered in from before the pools existed")

    # ---- 11. the vocabulary came from OUR data, not invented ----
    sc = json.load(open(os.path.join(ROOT, "data", "set_categories.json"),
                        encoding="utf-8"))
    cat_ids = {x["id"] for x in sc["categories"]}
    enh_ids = {x["id"] for x in sc["enhancement_classes"]}
    bad = [p["full_name"] for ps in (GAD, UB) for p in powers[ps]
           if not set(p["accepted_set_category_ids"]) <= cat_ids
           or not set(p["accepted_enhancement_type_ids"]) <= enh_ids]
    ok("every category and enhancement id is one our data defines", not bad,
       f"{bad}")

    print(f"\norigin-pools battery: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
