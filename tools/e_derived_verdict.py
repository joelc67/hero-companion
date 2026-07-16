"""E-EXPERIMENT VERDICT (morning side of the 2026-07-15 overnight work order).

Measures directive E's thesis on the pre-registered 28-context holdout
(benchmarks/e_holdout.json, seed 20260715, bar committed at 7caead8 BEFORE
any ground truth ran): can the SHIPPING PATH (autopick picks + the standard
solve chain — what every user gets in seconds) stand in for full converged
certification on combos that have NO champion?

Per context:
  GT      the overnight converged ground truth's picks (champions_shard_e_gt_*
          — experiment artifacts, NEVER merged into the roster), re-evaluated
          CANONICALLY (bare {"full_name"} picks through the exact evaluate()
          chain, fresh process — stored run scores are within-run rankings
          only, per the canonical-score protocol).
  DERIVED /build/autopick picks for the same context, evaluated through the
          IDENTICAL canonical chain. Only the picks differ, so the ratio
          isolates pick quality — the thing champion knowledge is supposed to
          transfer.
  BATTERY engine.validate_build on the derived solved build must return zero
          errors, and every power carries <= 6 slots.

Pre-registered bar: derived >= 97% of GT canonical on >= 90% of the sample,
zero battery failures, worst case (min/p10/median) reported regardless.

Run:  py tools\\e_derived_verdict.py        (writes benchmarks/e_verdict.json)
"""
import copy
import json
import os
import statistics
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv  # noqa: E402
import proc_pass  # noqa: E402
import first_principles as fp  # noqa: E402

GT_SHARDS = ["champions_shard_e_gt_p0.json", "champions_shard_e_gt_p1.json",
             "champions_shard_e_gt_p2.json"]

# PATH-IDENTITY LABEL (verifier flag, ideas.md 2026-07-16): the strategic
# meaning of the verdict hangs on exactly which code path produced the
# derived side. This harness scores:
#   picks:    POST /build/autopick {archetype, primary, secondary, content}
#             (bare full_name list extracted from the response)
#   slotting: srv._assess_solve(at, picks, preset_targets, "premium",
#             perk_focus, roles, False, False, False) -> proc_pass ->
#             _endurance_relief_pass — i.e. evaluate_first's canonical chain,
#             NOT the app's real /build/solve payload (which carries slots/
#             earned_slot_count/exposure/tier) and NOT deep_optimize.
# Whether that equals what a user gets from the wizard's Build is exactly
# what the two-context probe (tools/e_path_probe.py) decides.
DERIVED_PATH = ("picks=/build/autopick; slotting=_assess_solve(premium)"
                "+proc_pass+endurance_relief (evaluate_first canonical chain);"
                " NOT /build/solve payload; NOT deep_optimize")


def canonical_eval(at, content, picks, role):
    """evaluate_first.evaluate_picks, verbatim, but returns the solved build
    too (for the derived-side battery). Same chain both sides — apples to
    apples by construction."""
    pre = srv.ai_build.preset_targets(
        content, role,
        res_cap=round(((srv.ARCH_BY_NAME.get(at) or {}).get("res_cap")
                       or 0.75) * 100, 1),
        archetype=at)
    targets, roles, perk = pre["targets"], pre["roles"], pre["perk_focus"]
    ctx = srv._stat_ctx(at)
    ctx["power_by_full"] = srv.POWER_BY_FULL
    arch_row = srv.ARCH_BY_NAME.get(at)
    res_cap = (round(arch_row["res_cap"] * 100, 1) if arch_row
               else srv.engine.RESISTANCE_HARD_CAP)
    powers = [{"full_name": fn} for fn in picks]
    r = srv._assess_solve(at, copy.deepcopy(powers), copy.deepcopy(targets),
                          "premium", perk, roles, False, False, False,
                          with_powers=True)
    if not r:
        return None, None, None
    _tot, solved = r
    solved = proc_pass.apply_proc_pass(solved, srv.POWER_BY_FULL, role=role,
                                       content=content)
    solved = srv._endurance_relief_pass(solved, at, ctx, res_cap)
    build = {"archetype": at, "powers": solved}
    tot = srv.engine.calculate_build(build, srv.SET_BONUSES, res_cap=res_cap,
                                     ctx=ctx)
    ev = fp.encounter_value(at, solved, ctx, tot, scenario=content,
                            arch_row=arch_row, role_output_mod=srv.role_output)
    tm = (fp.SCENARIOS.get(content) or fp.SCENARIOS["general"]).get(
        "teammates", 0)
    return fp.role_contribution(ev, role, teammates=tm), build, tot


def main():
    os.environ["HC_SOLVER_BACKEND"] = "cbc"
    holdout = json.load(open(os.path.join(ROOT, "benchmarks",
                                          "e_holdout.json"),
                             encoding="utf-8"))
    bar = holdout["acceptance_bar"]
    gt = {}
    for fn in GT_SHARDS:
        p = os.path.join(ROOT, fn)
        if os.path.exists(p):
            gt.update(json.load(open(p, encoding="utf-8")))
    client = srv.app.test_client()

    rows = []
    t0 = time.time()
    for row in holdout["contexts"]:
        key, stratum = row["key"], row["stratum"]
        parts = key.split("|")
        at, prim, sec, content = parts[:4]
        role = (srv.ai_build.CONTENT_PRESETS.get(content or "", {})
                .get("default_role")
                or srv._AT_DEFAULT_ROLE.get(at, "damage"))
        name = f"{prim.split('.')[-1]}/{sec.split('.')[-1]}|{content}"
        entry = gt.get(key)
        if not entry:
            rows.append({"key": key, "stratum": stratum, "status": "NO_GT"})
            print(f"  NO GROUND TRUTH  {name}", flush=True)
            continue
        converged = bool(entry.get("certificate", {}).get("converged"))
        gt_score, _, _ = canonical_eval(at, content, entry["picks"], role)
        ap = client.post("/build/autopick", json={
            "archetype": at, "primary": prim, "secondary": sec,
            "content": content}).get_json()
        if not (ap and ap.get("powers")):
            rows.append({"key": key, "stratum": stratum,
                         "status": "AUTOPICK_FAILED",
                         "gt_canonical": gt_score, "converged": converged})
            print(f"  AUTOPICK FAILED  {name}", flush=True)
            continue
        derived_picks = [p["full_name"] for p in ap["powers"]]
        d_score, d_build, _ = canonical_eval(at, content, derived_picks, role)
        if gt_score is None or d_score is None:
            rows.append({"key": key, "stratum": stratum,
                         "status": "EVAL_FAILED", "converged": converged})
            print(f"  EVAL FAILED      {name}", flush=True)
            continue
        v = srv.engine.validate_build(d_build)
        overslot = [p.get("full_name") for p in d_build["powers"]
                    if len([s for s in (p.get("slots") or []) if s]) > 6]
        battery_errors = list(v.get("errors", [])) + \
            [f"{fn2}: >6 slots" for fn2 in overslot]
        ratio = d_score / gt_score if gt_score else None
        rows.append({"key": key, "stratum": stratum, "status": "OK",
                     "converged": converged,
                     "gt_canonical": round(gt_score, 1),
                     "derived_canonical": round(d_score, 1),
                     "ratio": round(ratio, 4),
                     "battery_errors": battery_errors})
        el = (time.time() - t0) / 60
        print(f"[{el:5.1f}m] {ratio*100:6.1f}%  gt {gt_score:8.1f}  derived "
              f"{d_score:8.1f}  {'' if converged else '[GT NOT CONVERGED] '}"
              f"{'BATTERY-FAIL ' if battery_errors else ''}({stratum}) {name}",
              flush=True)

    ok = [r for r in rows if r["status"] == "OK"]
    conv_ok = [r for r in ok if r["converged"]]
    ratios = sorted(r["ratio"] for r in conv_ok)
    n_meet = sum(1 for r in ratios if r >= bar["derived_over_converged_min_ratio"])
    battery_fails = [r["key"] for r in ok if r["battery_errors"]]
    verdict = {
        "sample": len(holdout["contexts"]), "evaluated": len(ok),
        "converged_gt": len(conv_ok),
        "meeting_ratio": n_meet,
        "share_meeting": round(n_meet / len(conv_ok), 4) if conv_ok else None,
        "min": ratios[0] if ratios else None,
        "p10": ratios[max(0, int(len(ratios) * 0.10) - 0)] if ratios else None,
        "median": round(statistics.median(ratios), 4) if ratios else None,
        "battery_failures": battery_fails,
        "bar": bar,
        "pass": bool(conv_ok) and not battery_fails
                and (n_meet / len(conv_ok)) >= bar["sample_share_meeting_ratio"]
                and len(ok) == len(holdout["contexts"]),
    }
    by_stratum = {}
    for s in ("adjacent", "distant", "thin", "content"):
        rs = sorted(r["ratio"] for r in conv_ok if r["stratum"] == s)
        if rs:
            by_stratum[s] = {"n": len(rs), "min": rs[0],
                             "median": round(statistics.median(rs), 4)}
    verdict["by_stratum"] = by_stratum

    print("\n=== WORST CASES FIRST (converged GT only) ===")
    for r in sorted(conv_ok, key=lambda r: r["ratio"])[:8]:
        print(f"  {r['ratio']*100:6.1f}%  ({r['stratum']}) {r['key']}")
    print(f"\n=== E VERDICT: {verdict['meeting_ratio']} of "
          f"{verdict['converged_gt']} converged contexts >= "
          f"{bar['derived_over_converged_min_ratio']*100:.0f}% "
          f"(need {bar['sample_share_meeting_ratio']*100:.0f}% of sample); "
          f"min {verdict['min']}, p10 {verdict['p10']}, "
          f"median {verdict['median']}; battery failures: "
          f"{len(battery_fails)} ===")
    print(f"PRE-REGISTERED BAR: {'PASS' if verdict['pass'] else 'FAIL'}")

    out = {"derived_path": DERIVED_PATH,
           "pick_order_note": "the evaluate chain is pick-ORDER sensitive "
           "(~8% measured on the certified Rad/Dark Stalker: stored-order "
           "1398.6 vs autopick-order 1509.3, same multiset) — named watch "
           "item, same family as the run-vs-canonical gaps (430/387)",
           "rows": rows, "verdict": verdict}
    with open(os.path.join(ROOT, "benchmarks", "e_verdict.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("written to benchmarks/e_verdict.json")


if __name__ == "__main__":
    main()
