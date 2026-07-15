"""EVALUATE-FIRST WAVE (Joel's selective re-certification ruling, run for the
A-fix 2026-07-15): nothing assumed broken, nothing assumed fine.

PROTOCOL FINDING (2026-07-15, proven by worktree bisect at d10f6a0): the
STORED certified score is NOT reproducible from (picks, model) alone — it was
computed in-run on candidate dicts mixing the buildout-era autopick seed's
field shapes (slots/slotCount/earned per surviving power) with bare added
picks, and that seed no longer exists once the champion itself is served.
The release code reproduces tonight's numbers exactly; the stored numbers
reproduce under NOTHING. Scores were honest as within-run rankings (all
candidates shared a shape); they are not portable baselines.

THE CANONICAL BASIS, defined here: evaluate the stored picks as bare
{"full_name"} dicts through the exact evaluate() chain. Deterministic,
reconstructible from the certificate alone, forever. --write stores it as
entry["canonical_score"]; every future evaluate-first pass compares canonical
vs canonical.

Per certified context (champions.json ∪ shards − held):
  UNAFFECTED  canonical score matches the last recorded canonical (or this is
              the first canonical baseline) → certificate annotated
  MOVED       canonical drifted since last recorded → queued for --recert wave

RIDERS (Joel's green light — measured during the wave, free because the
re-solves run anyway):
  1. Backend portfolio: every context's re-solve also runs under HiGHS —
     per-instance time split (racing data) and the TRUE scorer's verdict on
     each backend's tie-break (diversity data). CBC stays canonical; nothing
     kept from HiGHS — numbers only.

Run:   py tools\\evaluate_first.py [--write] [--skip-riders]
Then:  py tools\\converge_parallel.py --recert --workers N --merge --keys <movers>
"""
import argparse
import copy
import json
import os
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
from converge_parallel import certified_union  # noqa: E402

EPS = 0.05


def evaluate_picks(at, prim, sec, content, picks, role, form=None):
    """deep_optimize's evaluate() chain, verbatim, on the stored pick list.
    Certified scores were computed on SEARCH-CONSTRUCTED candidate dicts
    (bare full_name/pick_level — _assess_solve reads only full_name), so bare
    picks are the bit-faithful reconstruction; feeding the autopick seed's
    field shape (slots/earned from the tray plan) measurably changes the
    solve (Crab −7.5 artifact, 2026-07-15)."""
    pre = srv.ai_build.preset_targets(
        content, role,
        res_cap=round(((srv.ARCH_BY_NAME.get(at) or {}).get("res_cap")
                       or 0.75) * 100, 1))
    targets, roles, perk = pre["targets"], pre["roles"], pre["perk_focus"]
    ctx = srv._stat_ctx(at)
    ctx["power_by_full"] = srv.POWER_BY_FULL
    arch_row = srv.ARCH_BY_NAME.get(at)
    res_cap = (round(arch_row["res_cap"] * 100, 1) if arch_row
               else srv.engine.RESISTANCE_HARD_CAP)
    powers = [{"full_name": fn} for fn in picks]
    t0 = time.perf_counter()
    r = srv._assess_solve(at, copy.deepcopy(powers), copy.deepcopy(targets),
                          "premium", perk, roles, False, False, False,
                          with_powers=True)
    dt = time.perf_counter() - t0
    if not r:
        return None, dt
    _tot, solved = r
    solved = proc_pass.apply_proc_pass(solved, srv.POWER_BY_FULL, role=role,
                                       content=content)
    solved = srv._endurance_relief_pass(solved, at, ctx, res_cap)
    tot = srv.engine.calculate_build({"archetype": at, "powers": solved},
                                     srv.SET_BONUSES, res_cap=res_cap, ctx=ctx)
    ev = fp.encounter_value(at, solved, ctx, tot, scenario=content,
                            arch_row=arch_row, role_output_mod=srv.role_output)
    tm = (fp.SCENARIOS.get(content) or fp.SCENARIOS["general"]).get("teammates", 0)
    return fp.role_contribution(ev, role, teammates=tm), dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="annotate champions.json certificates with the verdicts")
    ap.add_argument("--skip-riders", action="store_true",
                    help="skip the HiGHS rider measurements")
    args = ap.parse_args()

    champs, srcs = certified_union()
    print("certified sources: " + ", ".join(f"{k} ({v})" for k, v in srcs.items()))
    print(f"evaluating {len(champs)} certified context(s) against the current "
          f"model+code (A-fix)\n")

    movers, unaffected, failed = [], [], []
    rider_rows = []
    for key in sorted(champs):
        parts = key.split("|")
        at, prim, sec, content = parts[:4]
        role = srv._AT_DEFAULT_ROLE.get(at, "damage")
        entry = champs[key]
        form = parts[4] if len(parts) > 4 else None
        # canonical-vs-canonical: the run score (entry["score"]) is a
        # within-run ranking, not a portable baseline (see docstring). The
        # FIRST pass records the canonical baseline; later passes diff it.
        old = entry.get("canonical_score")
        os.environ["HC_SOLVER_BACKEND"] = "cbc"
        new, t_cbc = evaluate_picks(at, prim, sec, content, entry["picks"],
                                    role, form=form)
        if new is None:
            failed.append(key)
            print(f"  EVAL FAILED           {key}")
            continue
        name = f"{prim.split('.')[-1]}/{sec.split('.')[-1]}" + (
            f" [{parts[4]}]" if len(parts) > 4 else "")
        if old is None:
            verdict = "BASELINE"
            unaffected.append(key)
            print(f"  BASELINE   canonical={new:9.1f} (run score "
                  f"{entry.get('score', 0):9.1f})  {name}")
        else:
            delta = new - old
            verdict = "UNAFFECTED" if abs(delta) <= EPS else "MOVED"
            (unaffected if verdict == "UNAFFECTED" else movers).append(key)
            print(f"  {verdict:10s} canonical {old:9.1f} -> {new:9.1f} "
                  f"(Δ {delta:+8.1f})  {name}")
        entry["canonical_score"] = round(new, 2)
        if not args.skip_riders:
            os.environ["HC_SOLVER_BACKEND"] = "highs"
            new_h, t_h = evaluate_picks(at, prim, sec, content, entry["picks"],
                                        role, form=form)
            os.environ["HC_SOLVER_BACKEND"] = "cbc"
            rider_rows.append({"key": key, "cbc_s": round(t_cbc, 2),
                               "highs_s": round(t_h, 2),
                               "cbc_score": new,
                               "highs_score": new_h})
        if args.write:
            cert = entry.setdefault("certificate", {})
            cert["evaluated"] = {"against": f"model {fp.MODEL_VERSION}, "
                                            f"{time.strftime('%Y-%m-%d')}",
                                 "verdict": verdict.lower(),
                                 "canonical_score": round(new, 2)}

    if args.write:
        # annotations + canonical baselines land in MAIN champions.json for
        # contexts that live there; shard-only contexts get theirs at merge
        # time (the shard files stay untouched — they belong to their runs)
        main_path = os.path.join(ROOT, "benchmarks", "champions.json")
        main_data = json.load(open(main_path, encoding="utf-8"))
        for k in main_data:
            if k in champs and champs[k].get("certificate", {}).get("evaluated"):
                main_data[k]["certificate"]["evaluated"] = \
                    champs[k]["certificate"]["evaluated"]
                main_data[k]["canonical_score"] = champs[k]["canonical_score"]
        with open(main_path, "w", encoding="utf-8") as f:
            json.dump(main_data, f, indent=1)
        print("\nannotations + canonical baselines written to "
              "benchmarks/champions.json")

    out = {"movers": movers, "unaffected": unaffected, "failed": failed,
           "riders": rider_rows}
    rp = os.path.join(ROOT, "benchmarks", "evaluate_first_afix.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    print(f"\n=== EVALUATE-FIRST: {len(unaffected)} unaffected, {len(movers)} "
          f"moved, {len(failed)} failed, of {len(champs)} ===")
    if rider_rows:
        tc = sum(r["cbc_s"] for r in rider_rows)
        th = sum(r["highs_s"] for r in rider_rows)
        hw = sum(1 for r in rider_rows
                 if (r["highs_score"] or 0) > (r["cbc_score"] or 0) + EPS)
        cw = sum(1 for r in rider_rows
                 if (r["cbc_score"] or 0) > (r["highs_score"] or 0) + EPS)
        print(f"RIDER (backend portfolio): CBC {tc:.1f}s vs HiGHS {th:.1f}s; "
              f"true-scorer diversity: HiGHS better on {hw}, CBC better on "
              f"{cw}, tied on {len(rider_rows) - hw - cw} (details in "
              f"evaluate_first_afix.json)")
    if failed:
        print("EVAL FAILURES above — resolve before the wave")
        sys.exit(1)
    if movers:
        print("\nre-converge the movers:\n  py tools\\converge_parallel.py "
              f"--recert --merge --workers 4 --keys \"{','.join(movers)}\"")


if __name__ == "__main__":
    main()
