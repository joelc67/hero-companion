"""BATTERY: the TWO-STEP SOLVE (engine work order item 5, plateau fix).

Joel's rulings (2026-07-30): the fix is the two-stage solve; the tie-break
follows the declared objective with ROLE always the focus; endurance recovery
ranks first, then the role's signature axis (DPS for damage, survivability
for tanks). Step 1's optimum is a hard floor.

Checks (each with the failure mode it exists to catch):
  1 TIE-BREAK PIN — two sets identical on the step-1 objective, recovery on
    the one CBC did NOT pick single-stage: two-stage must pick it. Catches a
    step 2 that runs but doesn't change the arbitrary choice.
  2 STEP-1 FLOOR (negative control) — a huge-recovery set strictly WORSE on
    the primary objective must NOT be chosen: recovery can never buy a step-1
    regression. Catches a leaky floor.
  3 SURVIVAL CUSHION — equal primary, equal recovery, one set carries extra
    UNTARGETED defense (the over-cap cushion): the survival role must take
    it. Catches a dead role-signature term.
  4 RECOVERY NEVER WORSE — on a multi-power fixture, two-stage recovery total
    >= single-stage recovery total (two-stage maximizes recovery among the
    tied optima, so any other optimum can only be <=). Catches inverted sign.
  5 KILL SWITCH — HC_TWO_STAGE=0 reproduces single-stage behavior on check
    1's fixture. Catches a dead A/B seam.

Run:  py tools\\test_plateau_twostep.py
"""
import copy
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import solver  # noqa: E402

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok)))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))


def mk_set(uid, def_melee=0.0, recovery=0.0, def_ranged=0.0):
    bonuses = []
    if def_melee:
        bonuses.append({"pieces_required": 2, "bonuses": [f"{uid}_dm"],
                        "effects": [{"effect": "Defense", "damage_type": "Melee",
                                     "value": def_melee}]})
    if recovery:
        bonuses.append({"pieces_required": 2, "bonuses": [f"{uid}_rec"],
                        "effects": [{"effect": "Recovery", "value": recovery}]})
    if def_ranged:
        bonuses.append({"pieces_required": 2, "bonuses": [f"{uid}_dr"],
                        "effects": [{"effect": "Defense", "damage_type": "Ranged",
                                     "value": def_ranged}]})
    return {"uid": uid, "name": uid, "category": "Defense Sets", "category_id": 901,
            "level_min": 10, "level_max": 50,
            "pieces": [{"name": f"{uid}_p{i}", "uid": f"{uid}_p{i}"} for i in range(6)],
            "bonuses": bonuses}


def mk_power():
    return {"full_name": "Test.Fixture.Toggle", "display_name": "Fixture Toggle",
            "accepted_set_category_ids": [901],
            "accepted_set_categories": ["Defense Sets"],
            "power_type": 2}


def run(sets, roles, targets=None, n_powers=1):
    powers = [dict(mk_power(), full_name=f"Test.Fixture.Toggle{i}")
              for i in range(n_powers)]
    # slot_cap = one 2-piece set per power: the standing PERK pass (Recovery,
    # Defense) would otherwise legitimately add the tempter sets afterward and
    # mask what the TWO-STAGE mechanism chose.
    res = solver.solve_ilp(
        powers, targets or {"defense": {"Melee": 2}}, {901: copy.deepcopy(sets)},
        [], {}, slot_cap=2 * n_powers, tier="premium", roles=roles,
        archetype="Class_Tanker", at_res_cap=0.90, at_base_hp=1874.0)
    chosen = [{s.get("set_uid") for s in p.get("slots") or [] if s and s.get("set_uid")}
              for p in res["powers"]]
    return res, chosen


def main():
    # ── 1 + 5: tie-break pin and kill switch ────────────────────────────────
    A, B = mk_set("SetA", def_melee=0.02), mk_set("SetB", def_melee=0.02)
    os.environ["HC_TWO_STAGE"] = "0"
    _, chosen0 = run([A, B], roles=["survival"])
    single = "SetA" if "SetA" in chosen0[0] else "SetB"
    other = "SetB" if single == "SetA" else "SetA"
    # recovery goes on the set single-stage did NOT pick
    tie_sets = [mk_set(single, def_melee=0.02),
                mk_set(other, def_melee=0.02, recovery=0.05)]
    _, chosen_off = run(tie_sets, roles=["survival"])
    check("5 kill switch: HC_TWO_STAGE=0 keeps the single-stage pick",
          single in chosen_off[0],
          f"single-stage picks {single}; off-switch run picked {sorted(chosen_off[0])}")
    del os.environ["HC_TWO_STAGE"]
    _, chosen_on = run(tie_sets, roles=["survival"])
    check("1 tie-break pin: two-stage picks the higher-recovery tied set",
          other in chosen_on[0] and single not in chosen_on[0],
          f"single-stage arbitrary pick was {single}; two-stage picked {sorted(chosen_on[0])}")

    # ── 2: step-1 floor — recovery cannot buy a primary regression ──────────
    floor_sets = [mk_set("Strong", def_melee=0.03),
                  mk_set("Tempter", def_melee=0.02, recovery=0.50)]
    _, chosen = run(floor_sets, roles=["survival"], targets={"defense": {"Melee": 3}})
    check("2 step-1 floor: a huge-recovery set strictly worse on primary is refused",
          "Strong" in chosen[0] and "Tempter" not in chosen[0],
          f"picked {sorted(chosen[0])} (Tempter's 0.5 recovery must not beat the floor)")

    # ── 3: survival cushion — untargeted defense breaks a recovery-less tie ─
    cush_sets = [mk_set("Flat", def_melee=0.02),
                 mk_set("Cushion", def_melee=0.02, def_ranged=0.02)]
    _, chosen = run(cush_sets, roles=["survival"])
    check("3 survival cushion: extra untargeted defense wins the tie",
          "Cushion" in chosen[0] and "Flat" not in chosen[0],
          f"picked {sorted(chosen[0])}")

    # ── 6: the floor holds under BOTH styles — check 2 already exercises the
    # DEFAULT (eps: the perturbation is capped at 0.001 objective units, far
    # below the fixture's ~0.33 discrete primary gap, so a floor leak would
    # flip the chosen set — testable exactly, no tolerance); this arm pins the
    # LEX step-2 constraint the same way, so a regression in either style's
    # floor goes red. Roster-wide evidence behind both: 0 floor defects at
    # 2e-6 rel across all 24 certified contexts (measure_plateau_ab).
    os.environ["HC_TS_STYLE"] = "lex"
    _, chosen = run([mk_set("Strong2", def_melee=0.03),
                     mk_set("Tempter2", def_melee=0.02, recovery=0.50)],
                    roles=["survival"], targets={"defense": {"Melee": 3}})
    del os.environ["HC_TS_STYLE"]
    check("6 lex style cannot trade primary value (discrete-gap floor, exact)",
          "Strong2" in chosen[0] and "Tempter2" not in chosen[0],
          f"picked {sorted(chosen[0])} under HC_TS_STYLE=lex")

    # ── 4: recovery never worse across a multi-power fixture ───────────────
    pool = [mk_set("P1", def_melee=0.02), mk_set("P2", def_melee=0.02, recovery=0.03),
            mk_set("P3", def_melee=0.015, recovery=0.06),
            mk_set("P4", def_melee=0.02, def_ranged=0.01)]
    os.environ["HC_TWO_STAGE"] = "0"
    res_off, _ = run(pool, roles=["survival"], n_powers=3)
    del os.environ["HC_TWO_STAGE"]
    res_on, _ = run(pool, roles=["survival"], n_powers=3)
    rec_off = res_off["totals"].get(("Recovery", None), 0.0)
    rec_on = res_on["totals"].get(("Recovery", None), 0.0)
    check("4 recovery never worse than the single-stage optimum",
          rec_on >= rec_off - 1e-9,
          f"recovery single-stage {rec_off:.4f} vs two-stage {rec_on:.4f}")

    n = len(CHECKS)
    fails = [c for c, ok in CHECKS if not ok]
    print(f"\n{n} of 6 expected checks ran")
    if n != 6:
        print("COVERAGE FAILURE")
        sys.exit(1)
    print("ALL CHECKS PASS" if not fails else f"FAILURES: {', '.join(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
