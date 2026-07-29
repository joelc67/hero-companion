"""FLEET SPLIT — partition a wave across every available worker (the 3:33 AM rule).

Joel's standing rule (2026-07-29, CLAUDE.md certification protocol): at every
wave launch or resume, UN-STARTED keys split across every healthy worker —
idling capacity is never a silent default. This tool is the mechanical form:

  1. remaining = key list minus everything banked in the current wave's shards
     minus anything held by a live LOCAL worker (never double-launch in-flight)
  2. split remaining proportionally to fleet capacity (laptop 32 : box 16 by
     default → 2/3 local, 1/3 remote), remote slice first-out (OneDrive+tick
     latency means the box should start claiming while local workers spin up)
  3. LOCAL slice: converge_parallel --recert, detached-safe shard prefix
     REMOTE slice: send_work.py order (commit-pinned, box auto-sizes workers)

Collision-proof by construction: local and remote prefixes never overlap, and
in-flight contexts are excluded the same way wave_resume learned to (the
2026-07-21 double-launch). The verdict gate downstream is unchanged — shards
from BOTH machines meet in recert_verdicts on the laptop.

Run:  py tools\\remote_worker\\split_wave.py --dry-run
      py tools\\remote_worker\\split_wave.py [--local-share 0.67]
      [--keys-file tools\\wave_current_keys.txt] [--local-workers N]
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PY = sys.executable
sys.path.insert(0, os.path.join(ROOT, "tools"))
from wave_resume import _live_worker_keys  # noqa: E402 — the double-launch guard


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys-file",
                    default=os.path.join(ROOT, "tools", "wave_current_keys.txt"))
    ap.add_argument("--local-share", type=float, default=0.67,
                    help="fraction of remaining keys the laptop takes (default "
                         "2/3, the 32:16 thread ratio)")
    ap.add_argument("--local-workers", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    prefix = "champions_shard_par"
    try:
        prefix = open(os.path.join(ROOT, "tools", "wave_current_prefix.txt"),
                      encoding="utf-8").read().strip() or prefix
    except Exception:  # noqa: BLE001
        pass
    all_keys = [l.strip() for l in open(args.keys_file, encoding="utf-8")
                if l.strip()]
    done = set()
    for f in glob.glob(os.path.join(ROOT, prefix + "*_p*.json")):
        done |= set(json.load(open(f, encoding="utf-8")))
    live = _live_worker_keys()
    remaining = [k for k in all_keys if k not in done and k not in live]
    print(f"{len(done & set(all_keys))} banked, {len(live & set(all_keys))} "
          f"in flight locally, {len(remaining)} remaining to split")
    if not remaining:
        print("nothing to split")
        return

    # LONGEST-PROCESSING-TIME-FIRST (2026-07-29, Joel's efficiency standing
    # ask). Measured on the v38 wave: 2752 context-minutes over 6 workers took
    # ~16h wall where perfect packing is 7.6h — the loss is scheduling, and the
    # fix is free. One context (PB triform, 484 min) is 9x the median, so if it
    # starts last the wave's tail IS that context. Start the monsters first;
    # unknown contexts sort as median so a first-time context is not starved.
    # Cost history: benchmarks/wave_cost_history.json (tools/wave_cost_report.py).
    try:
        hist = json.load(open(os.path.join(ROOT, "benchmarks",
                                           "wave_cost_history.json"),
                              encoding="utf-8"))
    except Exception:  # noqa: BLE001 — no history yet = original order
        hist = {}
    if hist:
        med = sorted(hist.values())[len(hist) // 2]
        remaining.sort(key=lambda k: -hist.get(k, med))
        top = remaining[0]
        print(f"scheduled longest-first (history: {len(hist)} contexts); "
              f"first out = {hist.get(top, med):.0f} min "
              f"{top.split('|')[0].replace('Class_','')}"
              f"{'/' + top.split('|')[4] if len(top.split('|')) > 4 else ''}")

    if hist:
        # LPT LIST-SCHEDULING: deal longest-first to whichever machine has the
        # least predicted load RELATIVE to its capacity. Slicing the sorted
        # list instead would hand every monster to one machine and idle the
        # other early — last night's failure with extra steps.
        med = sorted(hist.values())[len(hist) // 2]
        local, remote = [], []
        load_l = load_r = 0.0
        cap_l, cap_r = args.local_share, max(1e-6, 1.0 - args.local_share)
        for k in remaining:                       # already longest-first
            cost = hist.get(k, med)
            if load_l / cap_l <= load_r / cap_r:
                local.append(k)
                load_l += cost
            else:
                remote.append(k)
                load_r += cost
        print(f"predicted load: local {load_l:.0f} min / remote {load_r:.0f} min "
              f"(makespan is set by the busier side)")
    else:
        n_local = round(len(remaining) * args.local_share)
        if len(remaining) >= 2:
            n_local = max(1, min(len(remaining) - 1, n_local))
        remote, local = remaining[n_local:], remaining[:n_local]
    print(f"split: {len(local)} local / {len(remote)} remote (box)")
    for k in local:
        print(f"   L {k}")
    for k in remote:
        print(f"   R {k}")
    if args.dry_run:
        print("(dry-run — nothing launched)")
        return

    # remote first: the box's claim latency runs while local workers spin up
    if remote:
        subprocess.run([PY, os.path.join(ROOT, "tools", "remote_worker",
                                         "send_work.py"),
                        "--keys", ",".join(remote)], cwd=ROOT, check=True)
    if local:
        n = 1
        while glob.glob(os.path.join(ROOT, f"{prefix}_split{n}_p*.json")):
            n += 1
        workers = min(args.local_workers, len(local))
        env = dict(os.environ, HC_SOLVER_NODE_CAP="50000")
        log = os.path.join(ROOT, f"{prefix}_split{n}_log.txt")
        with open(log, "w", encoding="utf-8") as lf:
            subprocess.Popen(
                [PY, os.path.join(ROOT, "tools", "converge_parallel.py"),
                 "--recert", "--workers", str(workers),
                 "--shard-prefix", f"{prefix}_split{n}",
                 "--keys", ",".join(local)],
                env=env, cwd=ROOT, stdout=lf, stderr=lf,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        print(f"local slice launched detached ({workers} workers); "
              f"log: {os.path.basename(log)}")
    print("Both slices launched. Verdict gate unchanged: all shards meet in "
          "recert_verdicts on the laptop; table to Joel before any merge.")


if __name__ == "__main__":
    main()
