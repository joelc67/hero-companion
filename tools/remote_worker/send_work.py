"""Send a champion-crunch work order to the remote worker (laptop side).

Writes one order JSON into %OneDrive%\\HeroCompanionCompute\\orders\\. The box's
watcher (worker_watch.py, scheduled every 5 min) claims it, checks out the
EXACT commit named here, runs the wave, and returns shards + heartbeats via
OneDrive. Watch progress from anywhere:  py tools\\remote_worker\\watch_remote.py

The commit pin is enforced on BOTH ends: this refuses to send an order for a
commit that isn't pushed (the box fetches from GitHub), and the box refuses
to run one it can't check out exactly.

Run:  py tools\\remote_worker\\send_work.py --keys-file tools\\wave_current_keys.txt
      py tools\\remote_worker\\send_work.py --keys "k1,k2" [--workers 4]
      [--node-cap 50000] [--no-recert] [--commit <sha>]
"""
import argparse
import json
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(os.environ.get("OneDrive") or "", "HeroCompanionCompute")


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys")
    ap.add_argument("--keys-file")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--node-cap", type=int, default=50000)
    ap.add_argument("--no-recert", action="store_true")
    ap.add_argument("--commit", help="default: current HEAD")
    args = ap.parse_args()
    if not os.environ.get("OneDrive"):
        raise SystemExit("OneDrive env var missing on this machine")
    if args.keys_file:
        keys = [l.strip() for l in open(args.keys_file, encoding="utf-8")
                if l.strip()]
    elif args.keys:
        keys = [k.strip() for k in args.keys.split(",") if k.strip()]
    else:
        raise SystemExit("pass --keys or --keys-file")

    commit = args.commit or _git("rev-parse", "HEAD").stdout.strip()
    # the box pulls from origin — an unpushed commit can never run remotely
    on_remote = _git("branch", "-r", "--contains", commit).stdout.strip()
    if not on_remote:
        raise SystemExit(f"commit {commit[:12]} is not on any remote branch — "
                         "push first (the box fetches from GitHub)")
    dirty = _git("status", "--porcelain").stdout.strip()
    if dirty and not args.commit:
        print("⚠ working tree is dirty — the box runs the PUSHED commit, "
              "not your local edits:")
        print("   " + "\n   ".join(dirty.splitlines()[:8]))

    oid = "wave-" + time.strftime("%Y%m%d-%H%M%S")
    order = {"id": oid, "keys": keys, "commit": commit,
             "workers": args.workers, "node_cap": args.node_cap,
             "recert": not args.no_recert}
    orders = os.path.join(BASE, "orders")
    os.makedirs(orders, exist_ok=True)
    path = os.path.join(orders, oid + ".json")
    json.dump(order, open(path, "w", encoding="utf-8"), indent=1)
    print(f"order {oid} sent: {len(keys)} keys @ {commit[:12]} "
          f"({args.workers} workers)")
    print(f"  {path}")
    print("The box claims it within ~5 min of being awake. Progress: "
          "py tools\\remote_worker\\watch_remote.py")


if __name__ == "__main__":
    main()
