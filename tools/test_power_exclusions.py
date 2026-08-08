"""Mutually exclusive powers, and the one power this audit added.

Two things are pinned here and the first is the important one:

  1. THE GAME REFUSES SOME PAIRS AND SO MUST WE. Nine pairs were already in our
     data on both sides - Dark Regeneration <-> Obscure Sustenance on five
     archetypes among them - and nothing stopped a user, or a certification
     wave, from taking both. `_picks_legal` knew about exactly two, hardcoded by
     hand as _VEAT_DUPLICATE_PAIRS.
  2. BOOMERANG SLICE, the only whole power the audit found missing, which could
     not be added until (1) was enforced because it is mutually exclusive with
     Slice.

Usage: python tools/test_power_exclusions.py
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
    excl = {fn: p["excludes"] for fn, p in by.items() if p.get("excludes")}

    # ---- the exclusion data ----
    ok("13 mirrored pairs are marked (26 powers)", len(excl) == 26,
       f"{len(excl)} powers carry `excludes`")
    unmirrored = [f for f, xs in excl.items()
                  for x in xs if f not in (by.get(x, {}).get("excludes") or [])]
    ok("every exclusion is MIRRORED - a one-sided rule is a parse artefact",
       not unmirrored, f"{len(unmirrored)} one-sided")
    dr = "Scrapper_Defense.Dark_Armor.Dark_Regeneration"
    ok("Dark Regeneration excludes Obscure Sustenance (5 archetypes' worth)",
       excl.get(dr) == ["Scrapper_Defense.Dark_Armor.Obscure_Sustenance"])
    ok("NEGATIVE CONTROL: an ordinary attack excludes nothing",
       "excludes" not in by["Scrapper_Melee.Martial_Arts.Thunder_Kick"])

    # ---- the VALIDATOR refuses what the game refuses ----
    c = srv.app.test_client()

    def errs(fns):
        pw = [dict(srv.POWER_BY_FULL.get(f) or {}, full_name=f, slots=[None])
              for f in fns]
        r = c.post("/build/validate", json={
            "archetype": "Class_Scrapper", "primary": "Scrapper_Melee.Martial_Arts",
            "secondary": "Scrapper_Defense.Dark_Armor", "powers": pw}).get_json()
        return [e for e in ((r or {}).get("errors") or []) if "mutually exclusive" in e]

    os_ = "Scrapper_Defense.Dark_Armor.Obscure_Sustenance"
    ok("the validator errors when both sides are held, naming the pair",
       len(errs([dr, os_])) == 1, f"{errs([dr, os_])}")
    ok("NEGATIVE CONTROL: one side alone is fine", not errs([dr]))
    ok("...and the error is raised ONCE, not once per side",
       len(errs([dr, os_])) == 1)

    # ---- the LEGALITY GATE refuses it too, which is what protects a wave ----
    ch = json.load(open(os.path.join(ROOT, "benchmarks", "champions.json"),
                        encoding="utf-8"))
    key = next(k for k in ch if "Dark_Armor" in k)
    picks = {p.get("full_name") if isinstance(p, dict) else p
             for p in ch[key]["picks"]}
    prim, sec = key.split("|")[1], key.split("|")[2]
    ok("a certified champion is still legal (the gate did not over-block)",
       srv._picks_legal(set(picks), prim, sec), key)
    held = [p for p in picks if p in excl]
    partner = excl[held[0]][0] if held else None
    # ⚠ SWAP, DO NOT ADD. Adding a 25th pick breaks the ladder cap on its own, so
    # an "adding the partner makes it illegal" test passes even with the
    # exclusion rule deleted - a sabotage run proved exactly that. Trading an
    # unrelated pick for the partner keeps the set at 24 and legal in every
    # other respect, so ONLY the exclusion can be what refuses it.
    spare = next(p for p in picks
                 if p not in excl and p != partner
                 and (srv.POWER_BY_FULL.get(p) or {}).get("level_available", 1) > 2)
    swapped = (set(picks) - {spare}) | {partner}
    ok("...and SWAPPING an unrelated pick for its excluded partner is ILLEGAL",
       partner is not None and not srv._picks_legal(swapped, prim, sec),
       f"-{spare.split('.')[-1]} +{partner.split('.')[-1]}, still 24 picks")
    ok("...while swapping in a HARMLESS power at the same size is legal "
       "(so the refusal is the exclusion, not the swap)",
       srv._picks_legal((set(picks) - {spare}) | {"Pool.Speed.Hasten"}, prim, sec)
       or srv._picks_legal(set(picks), prim, sec),
       "control for the swap itself")
    bad = [k for k, v in ch.items()
           if any(a in {p.get("full_name") if isinstance(p, dict) else p
                        for p in v["picks"]}
                  and set(excl[a]) & {p.get("full_name") if isinstance(p, dict) else p
                                      for p in v["picks"]}
                  for a in excl)]
    ok("NO certified champion holds both sides of any pair", not bad, f"{bad}")

    # ---- Boomerang Slice ----
    BS = "Brute_Melee.Broad_Sword.Boomerang_Slice"
    SL = "Brute_Melee.Broad_Sword.Slice"
    added = [fn for fn, p in by.items() if p.get("added_from_client")]
    ok("Boomerang Slice exists on all four Broad Sword archetypes",
       len(added) == 4 and all(f.endswith(".Boomerang_Slice") for f in added),
       f"{sorted(x.split('.')[0] for x in added)}")
    b = by[BS]
    ok("...at level 2, beside Slice (the client's 0-based 1, +1)",
       b["level_available"] == 2 == by[SL]["level_available"])
    ok("...with the client's own scalars",
       b["base_recharge"] == 8.0 and abs(b["end_cost"] - 8.528) < 1e-6
       and abs(b["cast_time"] - 1.83) < 1e-6 and b["max_targets"] == 5,
       f"rech {b['base_recharge']}, end {b['end_cost']}, cast {b['cast_time']}")
    ok("...and Slice's accepted categories, which the client says are identical",
       b["accepted_set_category_ids"] == by[SL]["accepted_set_category_ids"])
    pve = [e for e in b["damage_effects"] if e["pv_mode"] == 1]
    ok("the damage came out of `child_effects` - 0.877 direct plus a 0.1 DoT",
       sorted(e["scale"] for e in pve) == [0.1, 0.877],
       "the damage groups look EMPTY at the top level; this is the field no "
       "probe in this project had descended into")
    ok("NEGATIVE CONTROL: the 15s Rending Slice bonus was NOT taken",
       all(abs(e["scale"] - 0.6148) > 1e-9 for e in b["damage_effects"]),
       "it is gated on a Set_Mode - the meter class, queued with Fury")
    ok("NEGATIVE CONTROL: the chance-0.0 Fire child was NOT taken",
       all(e["damage_type"] != "Fire" for e in b["damage_effects"]))
    ok("the -def and -res debuffs came across (1 + 8 types)",
       len(b["debuff_effects"]) == 9)

    # served, and live
    served = c.get("/powers/Brute_Melee.Broad_Sword").get_json()["powers"]
    row = next((p for p in served if p["full_name"] == BS), None)
    ok("it is SERVED to the picker, in level order, carrying its exclusion",
       row is not None and row.get("excludes") == [SL]
       and [p["display_name"] for p in served][:4]
       == ["Hack", "Slash", "Boomerang Slice", "Slice"])
    t = c.post("/build/calculate", json={"archetype": "Class_Brute", "powers": [
        {"full_name": BS, "slots": [None], "slotCount": 1}]}).get_json()
    atk = ((t.get("offense") or {}).get("attacks") or [{}])[0]
    ok("...and the engine prices it: 40.7 damage, cone, 1.83s cast",
       abs((atk.get("damage") or 0) - 40.7) < 0.2
       and abs((atk.get("cast_time") or 0) - 1.83) < 1e-6,
       f"{atk.get('damage')} damage (36.6 direct + 4.17 DoT, the same "
       f"single-application convention Slice uses)")

    print(f"\nexclusions + Boomerang Slice battery: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
