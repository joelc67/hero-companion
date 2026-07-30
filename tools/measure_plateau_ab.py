"""PLATEAU A/B: single-stage vs TWO-STAGE solve on every certified context.

The item-5 measurement (Joel's go, 2026-07-30). Reuses the backend-validation
harness's machinery (tools/validate_solver_backend.py — the instrument that
measured the ±19.4% equal-optimum tie-break spread under v38), with the two
arms now HC_TWO_STAGE=0 vs 1, both on CBC.

Per context: autopick seed → the exact deep_optimize evaluate() chain
(_assess_solve → proc_pass → endurance_relief → engine totals →
first_principles role_contribution), once per arm.

Verdicts (evidence = per-pass step-1 ILP objectives, solver.DEBUG_OBJ — the
two-stage code restores the step-1 objective expression before the debug seam,
so both arms log step-1 semantics):
  IDENTICAL — same slotting byte-for-byte (no tie existed, or the tie-break
              agreed with CBC's arbitrary pick). The negative-control shape.
  TIE-BREAK — different slotting, step-1 objectives equal at the first
              divergent pass: step 2 chose a different tied optimum. The fp
              delta is the measurement — positive means the tie-break bought
              real physics.
  FLOOR DEFECT — the first divergent pass has a LOWER step-1 objective under
              two-stage (beyond the floor's own 1e-6 eps): step 2 traded away
              step 1's optimum. HARD FAIL.

Output: per-context table (fp both arms, delta %, wall both arms) + summary
(spread stats, movers list = the re-cert justification evidence per Joel's
"never assume a re-cert" ruling).

Run:  py tools\\measure_plateau_ab.py [--contexts N] [--json out.json]
"""
import argparse
import importlib.util as ilu
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ["HC_SOLVER_DEBUG_OBJ"] = "1"
os.environ["HC_SOLVER_BACKEND"] = "cbc"

_spec = ilu.spec_from_file_location(
    "vsb", os.path.join(ROOT, "tools", "validate_solver_backend.py"))
vsb = ilu.module_from_spec(_spec)
_spec.loader.exec_module(vsb)
srv, solver = vsb.srv, vsb.solver


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contexts", type=int, default=0)
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    champs = vsb.certified_contexts()
    keys = sorted(champs)
    if args.contexts:
        keys = keys[:args.contexts]
    print(f"PLATEAU A/B — {len(keys)} of {len(champs)} certified contexts "
          "(single-stage vs two-stage, CBC both arms)")

    client = srv.app.test_client()
    identical = tiebreak = defect = failed = 0
    t_single = t_two = 0.0
    rows = []
    for key in keys:
        parts = key.split("|")
        at, prim, sec, content = parts[:4]
        form = parts[4] if len(parts) > 4 else None
        role = srv._AT_DEFAULT_ROLE.get(at, "damage")
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
        ap_res = client.post("/build/autopick", json={
            "archetype": at, "primary": prim, "secondary": sec,
            "content": content, "form": form}).get_json()
        if not (ap_res and ap_res.get("powers")):
            print(f"  AUTOPICK FAILED       {key}")
            failed += 1
            continue
        powers = ap_res["powers"]

        os.environ["HC_TWO_STAGE"] = "0"
        sc_1, solved_1, s_1, obj_1 = vsb.solve_once(
            at, content, role, powers, targets, perk, roles, arch_row, ctx, res_cap)
        os.environ["HC_TWO_STAGE"] = "1"
        sc_2, solved_2, s_2, obj_2 = vsb.solve_once(
            at, content, role, powers, targets, perk, roles, arch_row, ctx, res_cap)
        t_single += s_1
        t_two += s_2
        if sc_1 is None or sc_2 is None:
            print(f"  SOLVE FAILED          {key} (single={sc_1} two={sc_2})")
            failed += 1
            continue
        c1, c2 = vsb.canon(solved_1), vsb.canon(solved_2)
        name = f"{prim.split('.')[-1]}/{sec.split('.')[-1]}" + (f" [{form}]" if form else "")
        # first pass whose step-1 objectives diverge beyond the floor's own eps
        div = None
        for i in range(max(len(obj_1), len(obj_2))):
            a = obj_1[i] if i < len(obj_1) else None
            b = obj_2[i] if i < len(obj_2) else None
            if a is None or b is None or (
                    abs(a - b) / max(1.0, abs(a or 0), abs(b or 0)) > 2e-6):
                div = (i, a, b)
                break
        delta = 100.0 * (sc_2 - sc_1) / max(abs(sc_1), 1e-9)
        if c1 == c2:
            identical += 1
            v = "IDENTICAL "
        elif div is None or (div[2] is not None and div[1] is not None
                             and div[2] >= div[1] - 2e-6 * max(1.0, abs(div[1]))):
            tiebreak += 1
            v = "TIE-BREAK "
        else:
            defect += 1
            v = "FLOOR DEFECT"
            print(f"    step-1 objective LOWER under two-stage at pass "
                  f"{div[0]}: {div[1]!r} -> {div[2]!r}")
        rows.append({"key": key, "verdict": v.strip(), "fp_single": sc_1,
                     "fp_two": sc_2, "delta_pct": delta,
                     "s_single": s_1, "s_two": s_2})
        print(f"  {v} single={sc_1:9.2f} ({s_1:5.2f}s)  two={sc_2:9.2f} "
              f"({s_2:5.2f}s)  {delta:+7.3f}%  {name}")

    ties = [r for r in rows if r["verdict"] == "TIE-BREAK"]
    deltas = sorted(r["delta_pct"] for r in ties)
    print(f"\n=== PLATEAU A/B: {identical} identical, {tiebreak} tie-break, "
          f"{defect} FLOOR DEFECTS, {failed} failed, of {len(keys)} contexts ===")
    print(f"ILP wall: single {t_single:.1f}s vs two-stage {t_two:.1f}s "
          f"({t_two / max(t_single, 1e-9):.2f}x)")
    if ties:
        up = sum(1 for d in deltas if d > 0.01)
        down = sum(1 for d in deltas if d < -0.01)
        mid = deltas[len(deltas) // 2]
        print(f"tie-break fp deltas (two-stage vs single): {up} up, {down} down, "
              f"{len(deltas) - up - down} flat; median {mid:+.3f}%, "
              f"range [{deltas[0]:+.3f}%, {deltas[-1]:+.3f}%]")
        print("\nMOVERS (re-cert justification evidence — |delta| > 0.5%):")
        for r in sorted(ties, key=lambda r: -abs(r["delta_pct"])):
            if abs(r["delta_pct"]) > 0.5:
                print(f"  {r['delta_pct']:+8.3f}%  {r['key']}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=1)
        print(f"\nwritten: {args.json}")
    if defect or failed:
        print("VERDICT: FAIL")
        sys.exit(1)
    print("VERDICT: PASS — no floor defect; the fp deltas above are the "
          "measurement.")


if __name__ == "__main__":
    main()
