"""END-TO-END SOLVER BACKEND BENCHMARK: CBC vs HiGHS on real champion
certification runs (deep_optimize), not the per-solve atoms.

Why this exists (Joel's hardware brief, 2026-07-29): the per-SOLVE A/B
(tools/validate_solver_backend.py, solver_backend_ab_2026-07-29.log) measures
ONE ILP pass on ONE autopick seed per context. A certification run is a
thousand-plus solves inside a threaded hill-climb, so the end-to-end ratio can
differ from the atom ratio for reasons the atom test cannot see (thread
scaling: CBC is a SUBPROCESS per solve, HiGHS is IN-PROCESS highspy under the
GIL; and the search visits plateau-heavy neighbours an autopick seed never is).
This measures the number the hardware decision keys on: wall time per champion.

GATES (each one is a way the measurement could lie; all reported in the output):
  1. Matched termination. deep_optimize FORCES HC_SOLVER_NODE_CAP (server.py
     ~3618) — but solver._mip_solver honours the cap ONLY on the CBC branch;
     the HiGHS branch returns before the cap is read. Left alone, CBC would run
     node-capped while HiGHS ran uncapped. So this harness sets
     HC_DEEP_NODE_CAP enormous: the cap is inert for BOTH, both prove
     optimality, gap tolerances already pinned to 0 on both sides.
     `capped_floor` in the results must read 0 — if it does not, the run was
     truncated and its wall time is not a like-for-like number.
  2. Matched threads. HiGHS is pinned threads=1 in _mip_solver; PULP_CBC_CMD
     passes no -threads, and the bundled cbc.exe is single-threaded per solve.
     The SEARCH's own pool (HC_SWEEP_WORKERS) is pinned identically per run and
     recorded.
  3. Objective equality is NOT re-derived here — validate_solver_backend.py
     already proved it 24/24 today, per pass, with HC_SOLVER_DEBUG_OBJ=1. What
     this harness records instead is the END-TO-END consequence: the final
     champion picks + score per backend, so an equal-optimum tie-break that
     walks the search somewhere else is visible rather than hidden.
  4. HiGHS interface: pulp.HiGHS == in-process highspy (pulp 3.3.2
     createAndConfigureSolver builds highspy.Highs()), NOT HiGHS_CMD.

FAIRNESS CONTROLS
  - Each run is its OWN process: no in-process state carries between backends
    (the very effect that makes stored run-scores non-portable).
  - HC_CHAMPIONS_PATH always points at a scratch file. deep_optimize SAVES its
    result as the context's champion; without this a benchmark would rewrite
    the certified roster. COLD = scratch file absent (nothing to warm-start
    from). WARM = scratch file holding just this context's real champion entry.
  - benchmarks/exploration_log.jsonl is append-only and feeds move ORDERING.
    Run N would otherwise see run N-1's exploration and do different work, so
    the parent truncates it back to its starting length after every child.

Run:  py tools\\bench_solver_e2e.py --self-check      (plumbing, ~1 min)
      py tools\\bench_solver_e2e.py                   (the matrix)
"""
import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(ROOT, "benchmarks", "exploration_log.jsonl")
CHAMPIONS = os.path.join(ROOT, "benchmarks", "champions.json")
SCRATCH = os.path.join(os.environ.get("TEMP", ROOT), "hc_bench_solver")

# One per mechanically distinct region of the model, per the brief. Each is a
# CERTIFIED context, so a warm run has a real champion to start from.
CONTEXTS = [
    ("brute_farm", "Class_Brute|Brute_Melee.Spines|Brute_Defense.Fiery_Aura|farm_afk"),
    ("defender_support",
     "Class_Defender|Defender_Buff.Poison|Defender_Ranged.Sonic_Attack|itrial"),
    ("mastermind_pets",
     "Class_Mastermind|Mastermind_Summon.Demon_Summoning|Mastermind_Buff.Radiation_Emission|itrial"),
    ("kheldian_triform",
     "Class_Peacebringer|Peacebringer_Offensive.Luminous_Blast|"
     "Peacebringer_Defensive.Luminous_Aura|itrial|triform"),
]

NO_CAP = "2000000000"     # gate 1: cap inert on BOTH backends


# --------------------------------------------------------------------------
# CHILD: one champion, one backend, one warm/cold state. Prints one JSON line.
# --------------------------------------------------------------------------
def child(key, max_solves, restarts):
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "server"))
    import server as srv
    import solver
    from buildout_champions import FORM_POWERS, KHELDIAN_FORMS

    parts = key.split("|")
    at, prim, sec, content = parts[:4]
    form = parts[4] if len(parts) > 4 else None
    pin = set(FORM_POWERS[(at, form)]) if form else set()
    ban = (KHELDIAN_FORMS - pin) if at in ("Class_Peacebringer",
                                           "Class_Warshade") else set()

    client = srv.app.test_client()
    ap_res = client.post("/build/autopick", json={
        "archetype": at, "primary": prim, "secondary": sec,
        "content": content}).get_json()
    if not (ap_res and ap_res.get("powers")):
        print(json.dumps({"key": key, "error": "AUTOPICK FAILED"}))
        return

    capped0 = len(solver.CAPPED_SOLVES)
    t0 = time.perf_counter()
    solved, info = srv.deep_optimize(at, prim, sec, None, content, ap_res["powers"],
                                     max_solves=max_solves, restarts=restarts,
                                     ban=ban, pin=pin, form=form)
    wall = time.perf_counter() - t0
    cert = info.get("certificate") or {}
    print(json.dumps({
        "key": key, "wall": wall, "solves": info.get("solves"),
        "score": info.get("score"),
        "picks": sorted(p["full_name"] for p in (solved or [])),
        "converged": cert.get("converged"),
        "budget_truncated": cert.get("budget_truncated"),
        # "champion" proves the warm start actually fired; "autopick" proves a
        # cold run really was cold. The warm/cold split is worthless without it.
        "seed_src": info.get("seed"),
        "capped_floor": (cert.get("node_cap") or {}).get("capped_solves_floor",
                                                         len(solver.CAPPED_SOLVES) - capped0),
        "backend": os.environ.get("HC_SOLVER_BACKEND"),
        "sweep_workers": os.environ.get("HC_SWEEP_WORKERS"),
    }))


# --------------------------------------------------------------------------
# PARENT
# --------------------------------------------------------------------------
def run_one(name, key, backend, warm, max_solves, restarts, workers):
    """One child process. Returns its result dict (or an error dict)."""
    os.makedirs(SCRATCH, exist_ok=True)
    champ_path = os.path.join(SCRATCH, f"{name}_{backend}_"
                                       f"{'warm' if warm else 'cold'}.json")
    if os.path.exists(champ_path):
        os.remove(champ_path)
    if warm:
        entry = json.load(open(CHAMPIONS, encoding="utf-8")).get(key)
        if not entry:
            return {"key": key, "error": "no certified champion to warm from"}
        json.dump({key: entry}, open(champ_path, "w", encoding="utf-8"))

    env = dict(os.environ,
               HC_SOLVER_BACKEND=backend,
               HC_CHAMPIONS_PATH=champ_path,
               HC_SWEEP_WORKERS=str(workers),
               HC_DEEP_NODE_CAP=NO_CAP,
               PYTHONIOENCODING="utf-8")
    env.pop("HC_SOLVER_NODE_CAP", None)      # deep_optimize sets it from HC_DEEP_NODE_CAP

    log_len = os.path.getsize(LOG_PATH) if os.path.exists(LOG_PATH) else 0
    t0 = time.time()
    p = subprocess.run([sys.executable, os.path.abspath(__file__), "--child", key,
                        "--max-solves", str(max_solves), "--restarts", str(restarts)],
                       env=env, capture_output=True, text=True, encoding="utf-8")
    proc_wall = time.time() - t0
    # Restore the learning substrate so every run sees identical prior knowledge.
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r+b") as f:
            f.truncate(log_len)

    line = next((ln for ln in reversed((p.stdout or "").splitlines())
                 if ln.startswith("{")), None)
    if not line:
        return {"key": key, "error": f"child produced no result (rc={p.returncode})",
                "stderr": (p.stderr or "")[-800:]}
    r = json.loads(line)
    r.update(name=name, backend=backend, warm=warm, proc_wall=proc_wall,
             workers=workers, max_solves=max_solves, restarts=restarts)
    return r


def refuse_if_wave_running():
    """HARD GUARD, not vigilance. Two reasons this must never run beside a wave:
    (a) shared CPU makes every wall-clock number a lie; (b) this harness
    TRUNCATES benchmarks/exploration_log.jsonl back to its starting length, and
    a live wave appends to that same file — truncating would silently discard
    hours of a wave's exploration records."""
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
         "Select-Object -ExpandProperty CommandLine"],
        capture_output=True, text=True).stdout or ""
    busy = [ln.strip() for ln in out.splitlines()
            if any(t in ln for t in ("converge_parallel", "buildout_champions",
                                     "watch_remote", "worker_watch", "swap_sweep"))]
    if busy:
        print("REFUSING TO RUN — a certification wave is active "
              "(shared CPU invalidates wall-clock timing; the exploration-log "
              "restore would eat its records):")
        for b in busy[:6]:
            print("  " + b[:160])
        sys.exit(2)


def fmt(r):
    if r.get("error"):
        return f"    ERROR {r['error']}"
    return (f"    {r['wall']:8.1f}s  solves {str(r['solves']):>5}  "
            f"score {r['score'] if r['score'] is None else round(r['score'], 1)}  "
            f"capped {r['capped_floor']}  "
            f"{'converged' if r.get('converged') else 'truncated'}  "
            f"seed={r.get('seed_src')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--child", default="")
    ap.add_argument("--max-solves", type=int, default=1200)
    ap.add_argument("--restarts", type=int, default=1)
    ap.add_argument("--workers", type=int, default=8,
                    help="HC_SWEEP_WORKERS, pinned identically for both backends")
    ap.add_argument("--contexts", default="",
                    help="comma-separated short names (default: all four)")
    ap.add_argument("--self-check", action="store_true",
                    help="tiny end-to-end plumbing proof, then exit")
    ap.add_argument("--out", default=os.path.join(ROOT, "bench_solver_e2e.json"))
    args = ap.parse_args()

    if args.child:
        return child(args.child, args.max_solves, args.restarts)

    refuse_if_wave_running()

    if args.self_check:
        # Smallest thing that fails if the harness is wrong: a 3-solve run on
        # each backend must return a result, and must NOT touch the roster.
        before = os.path.getsize(CHAMPIONS)
        log_before = os.path.getsize(LOG_PATH) if os.path.exists(LOG_PATH) else 0
        for backend in ("cbc", "highs"):
            r = run_one("defender_support", CONTEXTS[1][1], backend, False, 3, 0, 2)
            print(f"  {backend:5s} {fmt(r)}")
            assert not r.get("error"), r
            assert r["solves"], "no solves ran"
        assert os.path.getsize(CHAMPIONS) == before, "champions.json was written!"
        assert (os.path.getsize(LOG_PATH) if os.path.exists(LOG_PATH)
                else 0) == log_before, "exploration log not restored!"
        print("SELF-CHECK PASS: both backends ran, roster and exploration log untouched")
        return

    picked = {s.strip() for s in args.contexts.split(",") if s.strip()}
    ctxs = [c for c in CONTEXTS if not picked or c[0] in picked]
    results = []
    print(f"matrix: {len(ctxs)} contexts x 2 backends x cold/warm, "
          f"max_solves={args.max_solves} restarts={args.restarts} "
          f"sweep_workers={args.workers}, node cap INERT (both backends)")
    for warm in (False, True):
        for name, key in ctxs:
            print(f"\n[{'WARM' if warm else 'COLD'}] {name}", flush=True)
            for backend in ("cbc", "highs"):
                r = run_one(name, key, backend, warm, args.max_solves,
                            args.restarts, args.workers)
                results.append(r)
                print(f"  {backend:5s}{fmt(r)}", flush=True)
                json.dump(results, open(args.out, "w", encoding="utf-8"), indent=1)

    print("\n=== END-TO-END BACKEND RESULT ===")
    for warm in (False, True):
        rows = [r for r in results if r.get("warm") is warm and not r.get("error")]
        if not rows:
            continue
        cbc = [r["wall"] for r in rows if r["backend"] == "cbc"]
        hi = [r["wall"] for r in rows if r["backend"] == "highs"]
        label = "WARM" if warm else "COLD"
        print(f"{label}: CBC median {statistics.median(cbc):.1f}s "
              f"(min {min(cbc):.1f} max {max(cbc):.1f}, total {sum(cbc):.1f}s)")
        print(f"{label}: HiGHS median {statistics.median(hi):.1f}s "
              f"(min {min(hi):.1f} max {max(hi):.1f}, total {sum(hi):.1f}s)")
        print(f"{label}: HiGHS speedup vs CBC = "
              f"{sum(cbc) / max(sum(hi), 1e-9):.2f}x on totals, "
              f"{statistics.median(cbc) / max(statistics.median(hi), 1e-9):.2f}x on medians")
        for name, _k in ctxs:
            c = next((r for r in rows if r["name"] == name and r["backend"] == "cbc"), None)
            h = next((r for r in rows if r["name"] == name and r["backend"] == "highs"), None)
            if c and h:
                print(f"    {name:18s} cbc {c['wall']:7.1f}s  highs {h['wall']:7.1f}s  "
                      f"= {c['wall'] / max(h['wall'], 1e-9):.2f}x  "
                      f"(solves {c['solves']}/{h['solves']}, "
                      f"score {round(c['score'] or 0, 1)}/{round(h['score'] or 0, 1)})")
    bad = [r for r in results if r.get("capped_floor")]
    print(f"\nGATE 1 (cap inert, both prove optimality): "
          f"{'FAIL — ' + str(len(bad)) + ' runs hit the node cap' if bad else 'PASS — 0 capped solves'}")
    wrong = [f"{r['name']}/{r['backend']}/{'warm' if r['warm'] else 'cold'}={r['seed_src']}"
             for r in results if not r.get("error")
             and r["seed_src"] != ("champion" if r["warm"] else "autopick")]
    print(f"WARM/COLD seed gate: "
          f"{'FAIL — ' + ', '.join(wrong) if wrong else 'PASS — every warm run seeded from its champion, every cold run from autopick'}")
    print(f"results: {args.out}")


if __name__ == "__main__":
    main()
