"""Piece 3 battery — Hamidon Origins as solver options (R2 gate, no model bump).

R2 (Joel, 2026-07-28): solves may propose HOs only in endgame content presets
(itrial + the farm family); every placed HO carries its attain note. R3 ruled
moot/deferred: no tier gate.

Checks:
  1. _ho_solver_pieces builds from the app's own sources: Ribosome carries
     res_ed + end_ed, Cytoskeleton/Membrane carry def_ed.
  2. DIRECTION GUARD (negative control): DeBuff pieces (Enzyme/Lysosome class)
     have NO def_ed — a debuff Defense aspect must never credit armor.
  3. OPTION CAPABILITY: a real resistance toggle offered ho_pieces yields HO
     options with a Resistance contribution; the same call with ho_pieces=None
     yields none (the gate is structural).
  4. R2 GATE PIN: _HO_CONTENTS is exactly itrial + the farm family.
  5. NEGATIVE CONTROL (real route): /build/solve at content=general ships ZERO
     ILP HO slots (set_uid HO_*), twice, identically (determinism).
  6. ENDGAME PATH: /build/solve at a farm content runs clean; any ILP HO slots
     are real, engine-priced hamidon pieces (count reported, not required —
     sets may legitimately win the trade).

Run:  py tools\\test_ho_solver.py
"""
import copy
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv  # noqa: E402
import solver  # noqa: E402

checks = 0
fails = []


def check(name, ok, detail=""):
    global checks
    checks += 1
    print(f"  {'PASS' if ok else 'FAIL'}  {name}"
          + (f"\n        {detail}" if detail else ""))
    if not ok:
        fails.append(name)


def canon(powers):
    return [(p.get("full_name"),
             sorted((s or {}).get("piece_uid") or "" for s in p.get("slots") or []))
            for p in powers]


def main():
    pieces = srv._ho_solver_pieces()
    by_uid = {p["uid"]: p for p in pieces}
    rib = by_uid.get("Hamidon_Res_Damage_Endurance_Discount")
    cyt = by_uid.get("Hamidon_Buff_Endurance_Discount")
    mem = by_uid.get("Hamidon_Buff_Recharge")
    check("ho pieces build from app sources (Ribosome res+end, Cyto/Membrane def)",
          bool(rib and rib.get("res_ed") and rib.get("end_ed")
               and cyt and cyt.get("def_ed") and mem and mem.get("def_ed")),
          f"{len(pieces)} pieces; Ribosome res_ed={rib and rib.get('res_ed')}")

    debuffs = [p for p in pieces if "debuff" in p["uid"].lower()]
    check("DIRECTION GUARD: DeBuff pieces carry no def_ed (debuff ≠ armor)",
          bool(debuffs) and all(not p.get("def_ed") for p in debuffs),
          f"{len(debuffs)} debuff pieces checked")

    # a real resistance toggle, dressed with the solver's own prep fields
    rec = srv.POWER_BY_FULL.get("Pool.Fighting.Tough")
    assert rec, "Tough not found"
    p = {"full_name": rec["full_name"],
         "_cats": set(rec.get("accepted_set_category_ids") or []),
         "_is_attack": False, "_armor_res": True, "_armor_def": False,
         "_base_rd": {("Resistance", "Smashing"): 0.225,
                      ("Resistance", "Lethal"): 0.225},
         "_end_drain": 0.325,
         "accepted_enhancement_types": rec.get("accepted_enhancement_types") or []}
    targets = {("Resistance", "Smashing"): 0.90}
    with_ho = solver._options_for_power(p, srv.SETS_BY_CATEGORY, targets, {},
                                        (6, 5, 4, 3, 2), ho_pieces=pieces)
    no_ho = solver._options_for_power(p, srv.SETS_BY_CATEGORY, targets, {},
                                      (6, 5, 4, 3, 2), ho_pieces=None)
    ho_opts = [o for o in with_ho if o["set"].get("_ho")]
    check("a res toggle yields HO options with Resistance contrib; None → zero",
          bool(ho_opts)
          and all(any(k[0] == "Resistance" and v > 0
                      for k, v in o["contrib"].items()) for o in ho_opts)
          and not any(o["set"].get("_ho") for o in no_ho),
          f"{len(ho_opts)} HO options (e.g. n={ho_opts and ho_opts[0]['n']}, "
          f"contrib={ho_opts and dict(ho_opts[0]['contrib'])})")

    check("R2 GATE PIN: endgame presets only (itrial + farm family)",
          srv._HO_CONTENTS == {"itrial", "fire_farm", "farm_afk", "farm_active"},
          f"_HO_CONTENTS = {sorted(srv._HO_CONTENTS)}")

    client = srv.app.test_client()

    def route_solve(content):
        ap = client.post("/build/autopick", json={
            "archetype": "Class_Brute", "primary": "Brute_Melee.Spines",
            "secondary": "Brute_Defense.Fiery_Aura",
            "content": content}).get_json()
        pre = [{"full_name": q["full_name"], "slots": q.get("slots"),
                "earned_slot_count": q.get("earned_slot_count")}
               for q in ap["powers"]]
        sol = client.post("/build/solve", json={
            "archetype": "Class_Brute", "goal": "", "tier": "premium",
            "content": content, "preserve": False, "keep_layout": False,
            "powers": pre}).get_json()
        return (sol or {}).get("powers") or []

    g1 = route_solve("general")
    g2 = route_solve("general")
    g_ho = [s for q in g1 for s in q.get("slots") or []
            if s and (s.get("set_uid") or "").startswith("HO_")]
    check("NEGATIVE CONTROL: general-content solve ships zero ILP HO slots, "
          "deterministically", not g_ho and canon(g1) == canon(g2),
          f"{len(g_ho)} HO slots; identical={canon(g1) == canon(g2)}")

    f1 = route_solve("farm_afk")
    f_ho = [s for q in f1 for s in q.get("slots") or []
            if s and (s.get("set_uid") or "").startswith("HO_")]
    priced = all((s.get("piece_uid") or "").lower().startswith("hamidon_")
                 and srv._stat_ctx("Class_Brute")["piece_boosts"].get(s["piece_uid"])
                 for s in f_ho)
    check("ENDGAME PATH: farm solve runs clean; any ILP HOs are real, "
          "engine-priced pieces", bool(f1) and priced,
          f"{len(f_ho)} ILP HO slots placed "
          f"({sorted({s.get('piece_name') for s in f_ho}) if f_ho else 'sets won the trade everywhere'})")

    print(f"\n{checks} of 6 expected checks ran")
    if checks != 6:
        fails.append("coverage denominator")
    print("══ ALL CHECKS PASS ══" if not fails
          else "FAILURES: " + ", ".join(fails))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
