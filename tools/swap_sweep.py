"""SWAP-SWEEP (work order, 2026-07-16 overnight): size the search-vs-canonical
optimality damage across the certified roster.

THE QUESTION (the IG flip, session-report 2026-07-16 ~11:05 AM): the search
converges on ITS OWN in-run objective, but the number we publish is the
CANONICAL score — and on farm_active a ONE-POWER swap (Long_Jump -> Irradiated
Ground) beat the freshly-certified champion by +40.9 canonical (432.1 -> 473.0,
reproduced fresh-process twice to the decimal). Nobody has checked the rest of
the roster. This tool checks: for every certified champion, evaluate the FULL
one-move neighborhood (swaps + pure drops, the search's own move space) under
the CANONICAL evaluator and report every variant that beats the incumbent.

WHAT IT DOES NOT DO: certify anything, write to champions.json, or claim the
best variant is optimal (it is one move deep). A hit here means "the certified
build is provably not canonically optimal, by at least this much" — sizing
data for the one-objective work order, not a re-certification.

MOVE SPACE mirrors deep_optimize's neighborhood deliberately (accessible
primary/secondary sets + all Pool.* + the CURRENT epic set only; travel and
inherents protected; Kheldian form powers protected on form-keyed contexts):
the question is whether the search missed inside its OWN move space. Cross-
epic moves are outside both and out of scope.

MECHANICS (certification-standard): variants screen under the deterministic
node cap (HC_SOLVER_NODE_CAP=50000 — the 1ce2268 pattern); the incumbent and
the top improvers then RE-EVALUATE UNCAPPED, and only uncapped numbers are
reported as findings. Each context runs in its OWN child process (the
in-process-state drift on long runs is unexplained — stored-vs-canonical
430/387.3 mystery — so no process evaluates more than one context's
neighborhood plus finals).

Run:   py tools\\swap_sweep.py [--workers 2] [--threads 3] [--limit N]
Child: py tools\\swap_sweep.py --context "<key>" [--threads 3] [--limit N]
Out:   benchmarks/swap_sweep_v33/<context>.json (+ swap_sweep_v33.json summary)
Resume: a context with an existing output file is skipped — safe to relaunch.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "benchmarks", "swap_sweep_v33")
SUMMARY = os.path.join(ROOT, "benchmarks", "swap_sweep_v33.json")
MEANINGFUL = 0.5          # canonical points an improver must clear (screen)
TOP_FINALS = 5            # improvers re-evaluated uncapped per context


def _safe(key):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", key)


# --------------------------------------------------------------- child mode
def run_context(key, threads, limit):
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    sys.path.insert(0, os.path.join(ROOT, "server"))
    os.environ["HC_SOLVER_BACKEND"] = "cbc"
    os.environ["HC_SOLVER_NODE_CAP"] = os.environ.get("HC_DEEP_NODE_CAP", "50000")
    import server as srv                      # noqa: E402
    from converge_parallel import certified_union   # noqa: E402
    from evaluate_first import evaluate_picks        # noqa: E402

    champs, _srcs = certified_union()
    entry = champs.get(key)
    if entry is None:
        print(f"context not in the certified union: {key}")
        return 2
    parts = key.split("|")
    at, prim, sec, content = parts[:4]
    form = parts[4] if len(parts) > 4 else None
    role = (srv.ai_build.CONTENT_PRESETS.get(content or "", {})
            .get("default_role") or srv._AT_DEFAULT_ROLE.get(at, "damage"))
    picks = list(entry["picks"])
    stored_canonical = entry.get("canonical_score")

    # ---- protected picks: travel, inherents, and the form's own powers
    travel = set(srv._TRAVEL.values())
    form_words = {"nova": ("Nova",), "dwarf": ("Dwarf",),
                  "triform": ("Nova", "Dwarf")}.get(form or "", ())

    def protected(fn):
        ps = fn.rsplit(".", 1)[0]
        if fn in travel or ps.startswith("Inherent"):
            return True
        short = fn.split(".")[-1]
        return any(w in short for w in form_words)

    # ---- move space (deep_optimize's neighborhood, one move deep)
    picked = set(picks)
    accessible = srv._veat_accessible_sets(prim, sec)
    drops = [fn for fn in picks
             if not protected(fn)
             and (fn.rsplit(".", 1)[0] in accessible
                  or fn.rsplit(".", 1)[0].startswith("Pool.")
                  or fn.rsplit(".", 1)[0].startswith("Epic."))]
    epic_ps = next((fn.rsplit(".", 1)[0] for fn in picked
                    if fn.startswith("Epic.")), None)
    add_sets = set(accessible) | {ps for ps in srv.POWERS
                                  if ps.startswith("Pool.")}
    if epic_ps:
        add_sets.add(epic_ps)
    adds = [q["full_name"] for ps in sorted(add_sets)
            for q in (srv.POWERS.get(ps) or [])
            if q["full_name"] not in picked and q.get("slottable")]

    variants = []                              # (label, pick-list)
    for d in drops:                            # pure drops
        v = [fn for fn in picks if fn != d]
        if srv._picks_legal(set(v), prim, sec):
            variants.append((f"-{d.split('.')[-1]}", v))
    for d in drops:                            # one-for-one swaps
        base = [fn for fn in picks if fn != d]
        for a in adds:
            v = base + [a]
            if srv._picks_legal(set(v), prim, sec):
                variants.append(
                    (f"-{d.split('.')[-1]} +{a.split('.')[-1]}", v))
    if limit:
        variants = variants[:limit]

    print(f"{key}\n  incumbent picks {len(picks)}, drops {len(drops)}, "
          f"adds {len(adds)}, legal variants {len(variants)}, "
          f"threads {threads}", flush=True)

    t0 = time.perf_counter()
    inc_capped, _ = evaluate_picks(at, prim, sec, content, picks, role,
                                   form=form)
    if inc_capped is None:
        print("  incumbent eval FAILED — aborting context")
        return 2
    print(f"  incumbent (capped screen) = {inc_capped:.1f} "
          f"(stored canonical {stored_canonical})", flush=True)

    done = [0]

    def ev(v):
        label, pl = v
        s, _dt = evaluate_picks(at, prim, sec, content, pl, role, form=form)
        done[0] += 1
        if done[0] % 25 == 0:
            print(f"    {done[0]}/{len(variants)} screened "
                  f"({time.perf_counter() - t0:.0f}s)", flush=True)
        return label, pl, s

    with ThreadPoolExecutor(max_workers=threads) as ex:
        screened = list(ex.map(ev, variants))
    screened = [(lb, pl, s) for lb, pl, s in screened if s is not None]
    improvers = sorted((x for x in screened if x[2] > inc_capped + MEANINGFUL),
                       key=lambda x: -x[2])

    # ---- finals: uncapped truth for the incumbent and the top improvers
    os.environ.pop("HC_SOLVER_NODE_CAP", None)
    inc_final, _ = evaluate_picks(at, prim, sec, content, picks, role,
                                  form=form)
    finals = []
    for lb, pl, s_cap in improvers[:TOP_FINALS]:
        s_fin, _ = evaluate_picks(at, prim, sec, content, pl, role, form=form)
        if s_fin is not None:
            finals.append({"move": lb, "capped": round(s_cap, 2),
                           "canonical": round(s_fin, 2),
                           "delta": round(s_fin - inc_final, 2),
                           "picks": pl})
    finals.sort(key=lambda f: -f["canonical"])
    best = finals[0] if finals else None
    dt = time.perf_counter() - t0

    out = {"key": key, "model_note": "canonical evaluator, v33 code at run time",
           "stored_canonical": stored_canonical,
           "incumbent_capped": round(inc_capped, 2),
           "incumbent_canonical": round(inc_final, 2) if inc_final else None,
           "n_variants_legal": len(variants),
           "n_screened": len(screened),
           "n_improvers_capped": len(improvers),
           "screen_top20": [{"move": lb, "capped": round(s, 2)}
                            for lb, _pl, s in improvers[:20]],
           "finals": finals,
           "wall_s": round(dt, 1), "threads": threads,
           "limit": limit or None}
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, _safe(key) + ".json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    if best:
        print(f"  BEATEN by {best['delta']:+.1f}: {best['move']} "
              f"(canonical {best['canonical']:.1f} vs incumbent "
              f"{inc_final:.1f}) — {len(improvers)} capped improvers, "
              f"{dt / 60:.1f} min", flush=True)
    else:
        print(f"  HELD: no one-move variant beats the incumbent "
              f"(screened {len(screened)}, {dt / 60:.1f} min)", flush=True)
    return 0


# -------------------------------------------------------------- driver mode
def run_driver(workers, threads, limit):
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "server"))
    from converge_parallel import certified_union   # noqa: E402
    champs, srcs = certified_union()
    keys = sorted(champs)
    os.makedirs(OUT_DIR, exist_ok=True)
    pend = [k for k in keys
            if not os.path.exists(os.path.join(OUT_DIR, _safe(k) + ".json"))]
    print(f"swap-sweep: {len(keys)} certified contexts "
          f"({', '.join(f'{k} ({v})' for k, v in srcs.items())}); "
          f"{len(pend)} pending (existing outputs resume for free); "
          f"{workers} child processes x {threads} threads", flush=True)

    running = []                                 # (key, Popen)
    while pend or running:
        while pend and len(running) < workers:
            k = pend.pop(0)
            args = [sys.executable, os.path.abspath(__file__),
                    "--context", k, "--threads", str(threads)]
            if limit:
                args += ["--limit", str(limit)]
            print(f"[driver] start {k}", flush=True)
            running.append((k, subprocess.Popen(args)))
        time.sleep(5)
        still = []
        for k, p in running:
            rc = p.poll()
            if rc is None:
                still.append((k, p))
            else:
                print(f"[driver] done  {k} (rc={rc})", flush=True)
        running = still

    # aggregate
    rows = []
    for k in keys:
        fp = os.path.join(OUT_DIR, _safe(k) + ".json")
        if os.path.exists(fp):
            rows.append(json.load(open(fp, encoding="utf-8")))
    beaten = [r for r in rows if r.get("finals")]
    with open(SUMMARY, "w", encoding="utf-8") as f:
        json.dump({"contexts": len(rows), "beaten": len(beaten),
                   "rows": rows}, f, indent=1)
    print(f"\n=== SWAP-SWEEP: {len(beaten)} of {len(rows)} certified builds "
          f"beaten by a one-move variant ===", flush=True)
    for r in sorted(beaten, key=lambda r: -(r["finals"][0]["delta"])):
        b = r["finals"][0]
        print(f"  {b['delta']:+7.1f}  {r['key']}  ({b['move']})", flush=True)
    print(f"summary -> {SUMMARY}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--context", help="child mode: sweep ONE context key")
    ap.add_argument("--workers", type=int, default=2,
                    help="driver: concurrent child processes")
    ap.add_argument("--threads", type=int, default=3,
                    help="solve threads per child")
    ap.add_argument("--limit", type=int, default=0,
                    help="smoke: cap the variant count per context")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.context:
        sys.exit(run_context(args.context, args.threads, args.limit))
    run_driver(args.workers, args.threads, args.limit)


if __name__ == "__main__":
    main()
