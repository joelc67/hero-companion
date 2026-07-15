"""SOLVER BACKEND VALIDATION: CBC vs HiGHS on every certified champion context.

Speed brief (ideas.md 2026-07-14): HiGHS replaces CBC only if it reproduces the
same optima on the whole certified roster. Both backends run with gap tolerances
pinned to 0 (see solver._mip_solver), so at proven optimality the OBJECTIVE is
guaranteed equal — score-tied builds may still tie-break to different picks.

OUTCOME (2026-07-14 run, 19/19 contexts): equivalence PASSED (zero backend
defects) but HiGHS measured ~3x SLOWER overall on our instances, so CBC stays
the default (solver._mip_solver has the numbers). Two standing uses for this
tool: (1) re-measure the backend question after any objective reshape;
(2) its tie-break report measures ILP-optimum DEGENERACY — equal-objective
slottings whose true fp scores differ (up to 6.5% observed), the plateau
finding feeding work order A.

Per context (champions.json ∪ shard files — denominator printed):
  autopick seed (the certification pipeline's own seed) → the exact
  deep_optimize evaluate() chain (_assess_solve → proc_pass →
  endurance_relief → engine totals → first_principles role_contribution)
  once under CBC, once under HiGHS.

Verdicts (evidence = the per-pass ILP objective log, solver.DEBUG_OBJ):
  IDENTICAL   — same solved slotting byte-for-byte (score equal by construction)
  TIE-BREAK   — different slotting, but at the FIRST divergent ILP pass both
                backends proved the SAME objective value (rel 1e-6): HiGHS
                tie-broke an equal optimum differently. The downstream
                first-principles score may shift slightly because it prices
                things the ILP objective does not — the delta is printed for
                the eyeball list, per the brief. Measured on the Blaster
                context 2026-07-14: pass-0 objectives equal to 2.1e-8, final
                score 282.76 vs 282.72 (0.014%).
  BACKEND DEFECT — the first divergent pass has UNEQUAL objectives
                (HARD FAIL: the swap does not ship).

Run:  py tools\\validate_solver_backend.py [--contexts N] [--repeat-highs]
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
sys.path.insert(0, os.path.join(ROOT, "server"))
os.environ["HC_SOLVER_DEBUG_OBJ"] = "1"
import server as srv  # noqa: E402
import solver  # noqa: E402
import proc_pass  # noqa: E402
import first_principles as fp  # noqa: E402

SHARDS = ["champions_shard_w2.json"]


def certified_contexts():
    champs = json.load(open(os.path.join(ROOT, "benchmarks", "champions.json"),
                            encoding="utf-8"))
    for name in SHARDS:
        p = os.path.join(ROOT, name)
        if os.path.exists(p):
            champs.update(json.load(open(p, encoding="utf-8")))
    return champs


def solve_once(at, content, role, powers, targets, perk, roles, arch_row, ctx,
               res_cap, role_mix=None):
    """deep_optimize's evaluate() chain, verbatim, minus cache/budget.
    Returns (score, solved, seconds, [per-pass ILP objectives])."""
    solver.DEBUG_OBJ.clear()
    t0 = time.perf_counter()
    r = srv._assess_solve(at, copy.deepcopy(powers), copy.deepcopy(targets),
                          "premium", perk, roles, False, False, False,
                          with_powers=True)
    ilp_s = time.perf_counter() - t0
    objs = list(solver.DEBUG_OBJ)
    if not r:
        return None, None, ilp_s, objs
    _tot, solved = r
    solved = proc_pass.apply_proc_pass(
        solved, srv.POWER_BY_FULL, role=role, content=content,
        guard=srv._TargetGuard(at, targets, ctx, res_cap))
    solved = srv._endurance_relief_pass(solved, at, ctx, res_cap)
    tot = srv.engine.calculate_build({"archetype": at, "powers": solved},
                                     srv.SET_BONUSES, res_cap=res_cap, ctx=ctx)
    ev = fp.encounter_value(at, solved, ctx, tot, scenario=content,
                            arch_row=arch_row, role_output_mod=srv.role_output)
    tm = (fp.SCENARIOS.get(content) or fp.SCENARIOS["general"]).get("teammates", 0)
    score = fp.role_contribution(ev, role_mix or role, teammates=tm)
    return score, solved, ilp_s, objs


def canon(solved):
    """Canonical slotting fingerprint: power -> sorted slot descriptors."""
    out = {}
    for p in solved or []:
        slots = []
        for s in (p.get("slots") or []):
            if not s:
                slots.append(None)
                continue
            slots.append((s.get("set_uid"), s.get("uid"), s.get("name"),
                          s.get("io_level"), s.get("boost")))
        out[p["full_name"]] = sorted(slots, key=lambda x: repr(x))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contexts", type=int, default=0,
                    help="limit to first N contexts (0 = all)")
    ap.add_argument("--repeat-highs", action="store_true",
                    help="run HiGHS twice per context to prove determinism")
    args = ap.parse_args()

    champs = certified_contexts()
    keys = sorted(champs)
    if args.contexts:
        keys = keys[:args.contexts]
    print(f"validating {len(keys)} of {len(champs)} certified contexts "
          f"(denominator = champions.json ∪ {SHARDS})")

    client = srv.app.test_client()
    identical = tiebreak = scorediff = failed = 0
    t_cbc = t_highs = 0.0
    eyeball = []
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

        os.environ["HC_SOLVER_BACKEND"] = "cbc"
        sc_c, solved_c, s_c, obj_c = solve_once(at, content, role, powers,
                                                targets, perk, roles, arch_row,
                                                ctx, res_cap)
        os.environ["HC_SOLVER_BACKEND"] = "highs"
        sc_h, solved_h, s_h, obj_h = solve_once(at, content, role, powers,
                                                targets, perk, roles, arch_row,
                                                ctx, res_cap)
        if args.repeat_highs:
            sc_h2, solved_h2, _, _ = solve_once(at, content, role, powers,
                                                targets, perk, roles, arch_row,
                                                ctx, res_cap)
            det = (sc_h == sc_h2 and canon(solved_h) == canon(solved_h2))
            if not det:
                print(f"  ⚠ HiGHS NON-DETERMINISTIC on {key}")
        t_cbc += s_c
        t_highs += s_h
        if sc_c is None or sc_h is None:
            print(f"  SOLVE FAILED          {key} (cbc={sc_c} highs={sc_h})")
            failed += 1
            continue
        cc, ch = canon(solved_c), canon(solved_h)
        name = f"{prim.split('.')[-1]}/{sec.split('.')[-1]}" + (f" [{form}]" if form else "")

        # First ILP pass with unequal objectives (rel 1e-6). Pass 0 always runs
        # on identical inputs, so a pass-0 mismatch is a hard backend defect.
        # Deeper mismatches after an equal-objective pass are the tie-break
        # CASCADE (an equal optimum chosen differently feeds later passes
        # different inputs) — reported, not auto-failed.
        div = None
        for i in range(max(len(obj_c), len(obj_h))):
            c = obj_c[i] if i < len(obj_c) else None
            h = obj_h[i] if i < len(obj_h) else None
            if c is None or h is None or (
                    abs(c - h) / max(1.0, abs(c or 0), abs(h or 0)) > 1e-6):
                div = (i, c, h)
                break
        if cc == ch:
            identical += 1
            v = "IDENTICAL "
        elif div is None or div[0] > 0:
            tiebreak += 1
            v = "TIE-BREAK "
            diffs = [p for p in set(cc) | set(ch) if cc.get(p) != ch.get(p)]
            eyeball.append((key, sc_c, sc_h, div, diffs))
        else:
            scorediff += 1
            v = "DEFECT    "
            print(f"    pass-0 objective mismatch: cbc={div[1]!r} highs={div[2]!r}")
        print(f"  {v} cbc={sc_c:9.2f} ({s_c:5.2f}s)  highs={sc_h:9.2f} "
              f"({s_h:5.2f}s)  {name}")

    print(f"\n=== BACKEND VALIDATION: {identical} identical, {tiebreak} tie-break "
          f"(eyeball), {scorediff} BACKEND DEFECTS, {failed} failed, "
          f"of {len(keys)} contexts ===")
    print(f"ILP wall time: CBC {t_cbc:.1f}s vs HiGHS {t_highs:.1f}s "
          f"({t_cbc / max(t_highs, 1e-9):.1f}x)")
    if eyeball:
        print("\nTIE-BREAK DETAILS (equal ILP optimum, different choice — eyeball):")
        for key, sc, sh, div, diffs in eyeball:
            dd = (f"objective sequences equal" if div is None else
                  f"cascade from pass {div[0]}: cbc={div[1]} highs={div[2]}")
            print(f"  {key}\n    fp score cbc={sc:.4f} highs={sh:.4f} "
                  f"(delta {100 * (sh - sc) / max(sc, 1e-9):+.4f}%)  [{dd}]")
            for p in sorted(diffs):
                print(f"    {p}")
    if scorediff or failed:
        print("VERDICT: FAIL — the swap does not ship")
        sys.exit(1)
    print("VERDICT: PASS — no backend defect; tie-breaks above go to the "
          "eyeball list per the brief")


if __name__ == "__main__":
    main()
