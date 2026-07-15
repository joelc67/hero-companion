"""CONTEXT-PARALLEL CONVERGENCE ORCHESTRATOR (speed brief lever 3).

Contexts are independent, so N certification workers give near-linear
scaling — the Kheldian queue ran ONE worker on a 32-thread box. This
launches N buildout_champions.py processes, each with:
  - a disjoint slice of the pending context keys (--keys, round-robin),
  - its OWN shard file (HC_CHAMPIONS_PATH=<prefix>_pN.json — no two
    processes ever share a write file),
  - its share of the machine for the in-process parallel sweep
    (HC_SWEEP_WORKERS = (cpu-2)//N unless overridden),
  - its own log (<prefix>_pN.log).

Certification standard is untouched — same buildout_champions, same
budgets, same bans/pins; this only changes HOW MANY run at once.

After all workers exit, prints the per-worker summaries and the exact
merge command (merge -> validate -> battery stays the documented
completion pipeline; pass --merge to run the merge automatically when
every worker exits 0).

⚠ Do NOT start this while another certification run owns the machine
(CLAUDE.md: champions.json/shards belong to the running process).

Run:  py tools\\converge_parallel.py --workers 3 [--pending | --keys k1,k2,...]
      [--max-solves 25000] [--restarts 6] [--sweep-workers N]
      [--shard-prefix champions_shard_par] [--merge]
"""
import argparse
import json
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
BUILDOUT = os.path.join(ROOT, "tools", "buildout_champions.py")


def certified_union():
    """champions.json PLUS every champions_shard_*.json at the repo root.
    A context certified in an UNMERGED shard is still certified — launching a
    new worker for it would re-converge at full cost and then collide at merge
    (measured the hard way 2026-07-14: a 'skip' smoke on shard-certified
    PB/WS human contexts started two real 25k-solve certification runs)."""
    import glob
    champs = json.load(open(os.path.join(ROOT, "benchmarks", "champions.json"),
                            encoding="utf-8"))
    srcs = {"champions.json": len(champs)}
    for sp in sorted(glob.glob(os.path.join(ROOT, "champions_shard_*.json"))):
        if sp.endswith(".bak"):
            continue
        try:
            sd = json.load(open(sp, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        srcs[os.path.basename(sp)] = len(sd)
        champs.update(sd)
    # Contexts PULLED at a gate (ladder-fit 0.12.19) still sit in their
    # original shards — the held file is the record that they are NOT
    # certified and must re-converge. Subtract it.
    held = os.path.join(ROOT, "champions_held_ladderfix.json")
    if os.path.exists(held):
        for k in json.load(open(held, encoding="utf-8")):
            if champs.pop(k, None) is not None:
                srcs[f"held:{k.split('|')[0]}"] = -1
    return champs, srcs


def pending_contexts(certified):
    """NEW_CONTEXTS not yet certified anywhere (import without running main)."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("_bc_list", BUILDOUT)
    # NEW_CONTEXTS lives at module top; executing the module only runs main()
    # under __main__, so this import is side-effect-free apart from loading
    # the server (heavy but read-only).
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [k for k in mod.NEW_CONTEXTS if k not in certified]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--keys", default="", help="explicit context keys (comma-separated)")
    ap.add_argument("--pending", action="store_true",
                    help="run every NEW_CONTEXTS entry not yet certified")
    ap.add_argument("--max-solves", type=int, default=25000)
    ap.add_argument("--restarts", type=int, default=6)
    ap.add_argument("--sweep-workers", type=int, default=0,
                    help="per-worker sweep threads (0 = (cpu-2)//workers)")
    ap.add_argument("--shard-prefix", default="champions_shard_par")
    ap.add_argument("--merge", action="store_true",
                    help="auto-run merge_champion_shards when all workers exit 0")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the partition + exact worker command lines, "
                         "launch nothing")
    ap.add_argument("--recert", action="store_true",
                    help="evaluate-first wave mode: the keys are certified "
                         "MOVERS being re-converged — no certified-skip, "
                         "workers run --recert, merge runs --replace")
    args = ap.parse_args()

    certified, srcs = certified_union()
    print("certified sources: " + ", ".join(f"{k} ({v})" for k, v in srcs.items()))
    if args.recert:
        keys = [s.strip() for s in args.keys.split(",") if s.strip()]
        if not keys:
            raise SystemExit("--recert requires explicit --keys")
    elif args.keys:
        keys = [s.strip() for s in args.keys.split(",") if s.strip()]
        already = [k for k in keys if k in certified]
        for k in already:
            print(f"already certified (main or shard), skipping: {k}")
        keys = [k for k in keys if k not in certified]
    elif args.pending:
        keys = pending_contexts(certified)
    else:
        raise SystemExit("pass --keys or --pending")
    if not keys:
        print("nothing to converge — every requested context is certified")
        return
    n = max(1, min(args.workers, len(keys)))
    sweep = args.sweep_workers or max(1, ((os.cpu_count() or 8) - 2) // n)
    slices = [keys[i::n] for i in range(n)]

    print(f"{len(keys)} context(s) across {n} worker(s), "
          f"{sweep} sweep threads each (cpu={os.cpu_count()}):")
    procs = []
    t0 = time.time()
    for i, sl in enumerate(slices):
        shard = os.path.join(ROOT, f"{args.shard_prefix}_p{i}.json")
        log = os.path.join(ROOT, f"{args.shard_prefix}_p{i}.log")
        env = dict(os.environ, HC_CHAMPIONS_PATH=shard,
                   HC_SWEEP_WORKERS=str(sweep))
        cmd = [PY, BUILDOUT, "--keys", ",".join(sl),
               "--max-solves", str(args.max_solves),
               "--restarts", str(args.restarts)] + (["--recert"] if args.recert
                                                    else [])
        print(f"  worker {i}: {len(sl)} context(s) -> {os.path.basename(shard)}"
              f" (log {os.path.basename(log)})")
        for k in sl:
            print(f"    {k}")
        if args.dry_run:
            print(f"    would run: {' '.join(cmd)}")
            continue
        lf = open(log, "w", encoding="utf-8")
        procs.append((i, sl, shard, log,
                      subprocess.Popen(cmd, env=env, stdout=lf, stderr=lf,
                                       cwd=ROOT), lf))
    if args.dry_run:
        print("dry run — nothing launched")
        return

    fails = 0
    for i, sl, shard, log, p, lf in procs:
        rc = p.wait()
        lf.close()
        el = (time.time() - t0) / 60
        print(f"[{el:6.1f}m] worker {i} exited rc={rc}")
        if rc != 0:
            fails += 1
            print(f"  see {log}")

    shards = [s for _, _, s, _, _, _ in procs if os.path.exists(s)]
    print(f"\n{n - fails} of {n} workers clean, {(time.time() - t0) / 60:.1f} min total")
    merge_cmd = (f'{PY} {os.path.join(ROOT, "tools", "merge_champion_shards.py")} '
                 + ("--replace " if args.recert else "") + " ".join(shards))
    if fails == 0 and args.merge and shards:
        print("merging shards...")
        rc = subprocess.call([PY, os.path.join(ROOT, "tools",
                                               "merge_champion_shards.py")]
                             + (["--replace"] if args.recert else []) + shards)
        if rc == 0:
            print("merged. NEXT: validate_champions -> battery (the standard "
                  "completion pipeline).")
        else:
            sys.exit(rc)
    elif shards:
        print(f"merge when ready:\n  {merge_cmd}")
    if fails:
        sys.exit(1)


if __name__ == "__main__":
    main()
