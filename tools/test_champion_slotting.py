"""Battery: the certified-slotting serve layer (game-truth ruling, 2026-08-14).

A champion entry may carry `slotting` — the production-validated refined build
banked by tools/bank_refined_slotting.py. The serve path
(server._champion_slotting inside /build/solve) must hand back EXACTLY that
build on the champion-delivery solve, and must FAIL OPEN to the normal solver
pipeline on any player ask or any doubt about the layer.

Self-contained: builds its own scratch champions file (HC_CHAMPIONS_PATH set
before importing server) from a real roster entry, derives a legal slotting
layer by running the real pipeline once, then MUTATES one piece (an
acceptance-legal in-set swap) so the positive check proves the layer WON over
the solver, not that they happened to agree.

Checks (positive control + negative controls + sabotages):
  1  champion-delivery solve serves the layer (certified_slotting=True)
  2  served slots == stored layer per power (the mutation survives = layer won)
  3  custom_targets  -> solver path (flag False)
  4  earned slots    -> solver path
  5  declared off-role -> solver path
  6  entry without a layer -> solver path
  7  SABOTAGE duplicate piece in the layer -> validation refuses, solver path
  8  SABOTAGE layer picks != entry picks -> no match, solver path
  9  evaluate_first.evaluate_picks(slotting=) == direct engine+fp chain score
"""
import copy
import json
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(tempfile.gettempdir(), "hc_test_champion_slotting.json")
os.environ["HC_CHAMPIONS_PATH"] = SCRATCH   # BEFORE importing server (learn pins it)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv          # noqa: E402
import engine                 # noqa: E402
import first_principles as fp # noqa: E402

KEY = "Class_Dominator|Dominator_Control.Mind_Control|Dominator_Assault.Fiery_Assault|itrial"
FAILS = []


def check(n, label, ok):
    print(f"  {'PASS' if ok else 'FAIL'}  {n}: {label}")
    if not ok:
        FAILS.append(n)


def sig(powers):
    return {p["full_name"]: sorted((s.get("set_uid") or "", s.get("piece_uid") or "")
                                   for s in (p.get("slots") or []) if s)
            for p in powers if p.get("slots")}


def solve(payload):
    with srv.app.test_client() as c:
        return c.post("/build/solve", json=payload).get_json()


def main():
    real = json.load(open(os.path.join(ROOT, "benchmarks", "champions.json"),
                          encoding="utf-8"))
    entry = copy.deepcopy(real[KEY])
    picks_payload = [{"full_name": fn} for fn in entry["picks"]]
    base_payload = {"archetype": "Class_Dominator", "content": "itrial",
                    "powers": picks_payload}

    # derive a legal layer from the real pipeline, then mutate one in-set piece
    json.dump({KEY: entry}, open(SCRATCH, "w", encoding="utf-8"))
    r0 = solve(copy.deepcopy(base_payload))
    assert r0 and r0.get("ok"), "pipeline solve failed — battery cannot run"
    layer = copy.deepcopy(r0["powers"])
    mutated = None
    for p in layer:
        for s in (p.get("slots") or []):
            if not s.get("set_uid"):
                continue
            held = {x.get("piece_uid") for x in p["slots"] if x.get("set_uid") == s["set_uid"]}
            pieces = next((es.get("pieces") for es in srv.ENH_SETS
                           if es.get("uid") == s["set_uid"]), None) or []
            alt = next((pc for pc in pieces
                        if (pc.get("uid") or pc.get("piece_uid")) not in held), None)
            if alt is not None:
                s["piece_uid"] = alt.get("uid") or alt.get("piece_uid")
                s["piece_name"] = alt.get("name")
                mutated = (p["full_name"], s["piece_uid"])
                break
        if mutated:
            break
    assert mutated, "no mutable in-set piece found — battery cannot run"
    errs = engine.validate_build({"archetype": "Class_Dominator", "powers": layer})
    errs = errs.get("errors") if isinstance(errs, dict) else errs
    assert not errs, f"mutated layer must stay legal, got {errs}"

    entry["slotting"] = layer
    json.dump({KEY: entry}, open(SCRATCH, "w", encoding="utf-8"))

    # 1+2 positive control
    r = solve(copy.deepcopy(base_payload))
    check(1, "champion-delivery solve serves the layer",
          bool(r.get("ok")) and r.get("certified_slotting") is True)
    check(2, f"served slots == stored layer (mutation {mutated[1]} survived)",
          sig(r["powers"]) == sig(layer))

    # 3 custom targets -> solver
    r = solve({**copy.deepcopy(base_payload),
               "custom_targets": {"defense": {"Smashing": 32.5}}})
    check(3, "custom_targets takes the solver path",
          bool(r.get("ok")) and not r.get("certified_slotting"))

    # 4 earned slots (a player's build) -> solver
    pp = copy.deepcopy(picks_payload)
    pp[0]["earned_slot_count"] = 3
    r = solve({**copy.deepcopy(base_payload), "powers": pp})
    check(4, "earned slots take the solver path",
          bool(r.get("ok")) and not r.get("certified_slotting"))

    # 5 declared off-role -> solver
    r = solve({**copy.deepcopy(base_payload), "role": "tank"})
    check(5, "a declared off-role takes the solver path",
          bool(r.get("ok")) and not r.get("certified_slotting"))

    # 6 entry without a layer -> solver
    e6 = copy.deepcopy(entry); e6.pop("slotting")
    json.dump({KEY: e6}, open(SCRATCH, "w", encoding="utf-8"))
    r = solve(copy.deepcopy(base_payload))
    check(6, "no layer -> solver path",
          bool(r.get("ok")) and not r.get("certified_slotting"))

    # 7 SABOTAGE: duplicate piece inside one power -> validation refuses
    e7 = copy.deepcopy(entry)
    for p in e7["slotting"]:
        ss = [s for s in (p.get("slots") or []) if s.get("set_uid")]
        if len(ss) >= 2:
            ss[1]["piece_uid"] = ss[0]["piece_uid"]
            ss[1]["piece_name"] = ss[0].get("piece_name")
            break
    json.dump({KEY: e7}, open(SCRATCH, "w", encoding="utf-8"))
    r = solve(copy.deepcopy(base_payload))
    check(7, "sabotaged (duplicate piece) layer is refused -> solver path",
          bool(r.get("ok")) and not r.get("certified_slotting"))

    # 8 SABOTAGE: layer whose picks differ from the entry's -> no match
    e8 = copy.deepcopy(entry)
    e8["picks"] = [fn for fn in e8["picks"] if not fn.endswith(".Hasten")]
    json.dump({KEY: e8}, open(SCRATCH, "w", encoding="utf-8"))
    r = solve(copy.deepcopy(base_payload))
    check(8, "picks mismatch -> no certified serve",
          bool(r.get("ok")) and not r.get("certified_slotting"))

    # 10 a USER perk chip is a player ask -> solver path
    json.dump({KEY: entry}, open(SCRATCH, "w", encoding="utf-8"))
    r = solve({**copy.deepcopy(base_payload), "perk_focus": "recovery"})
    check(10, "a user perk chip takes the solver path",
          bool(r.get("ok")) and not r.get("certified_slotting"))

    # 11 a content PRESET's own perk_focus must NOT block the layer (the
    # 2026-08-14 five-farm SLOT-DRIFT defect: farm presets carry perk_focus,
    # and reading it post-overlay rejected every farm champion's layer)
    real_all = json.load(open(os.path.join(ROOT, "benchmarks", "champions.json"),
                              encoding="utf-8"))
    fkey = next((k for k, v in real_all.items()
                 if k.split("|")[3].startswith("farm") and v.get("slotting")), None)
    if fkey:
        fentry = real_all[fkey]
        json.dump({fkey: fentry}, open(SCRATCH, "w", encoding="utf-8"))
        fat, _, _, fcontent = fkey.split("|")[:4]
        r = solve({"archetype": fat, "content": fcontent,
                   "powers": [{"full_name": fn} for fn in fentry["picks"]]})
        check(11, f"farm preset's own perk_focus does not block the layer ({fcontent})",
              bool(r.get("ok")) and r.get("certified_slotting") is True)
    else:
        check(11, "farm preset check SKIPPED — no farm champion carries a layer", False)
    json.dump({KEY: entry}, open(SCRATCH, "w", encoding="utf-8"))

    # 9 evaluate_first scores the stored layer directly
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import evaluate_first as ef
    got, _ = ef.evaluate_picks("Class_Dominator", KEY.split("|")[1],
                               KEY.split("|")[2], "itrial", entry["picks"],
                               "control", slotting=layer)
    ctx = srv._stat_ctx("Class_Dominator"); ctx["power_by_full"] = srv.POWER_BY_FULL
    ar = srv.ARCH_BY_NAME.get("Class_Dominator")
    rc = round(ar["res_cap"] * 100, 1)
    tot = engine.calculate_build({"archetype": "Class_Dominator", "powers": layer},
                                 srv.SET_BONUSES, res_cap=rc, ctx=ctx)
    ev = fp.encounter_value("Class_Dominator", layer, ctx, tot, scenario="itrial",
                            arch_row=ar, role_output_mod=srv.role_output)
    want = fp.role_contribution(ev, "control",
                                teammates=fp.SCENARIOS["itrial"].get("teammates", 0))
    check(9, f"evaluate_picks(slotting=) == direct chain ({got:.2f})",
          got is not None and abs(got - want) < 0.01)

    os.remove(SCRATCH)
    print(f"\n{'ALL 11 CHECKS PASS' if not FAILS else f'FAILED: {FAILS}'}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
