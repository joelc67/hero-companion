"""REMOTE WORKER — the gaming box's side of distributed champion crunching.

Design (2026-07-28, Joel's radar item): the dev laptop CONDUCTS from anywhere,
the box CRUNCHES. No new services, no tokens, no open ports:

  code + data   git pull of the PUBLIC repo, pinned to the exact commit the
                order names (mixed model versions poison canonical scores —
                the pin is verified, not assumed)
  orders        %OneDrive%\\HeroCompanionCompute\\orders\\*.json  (laptop → box)
  results       %OneDrive%\\HeroCompanionCompute\\results\\<id>\\ (box → laptop)
  heartbeats    %OneDrive%\\HeroCompanionCompute\\state\\heartbeat_<id>.json —
                the laptop watches progress from anywhere OneDrive syncs

The box NEVER merges: shards + DONE manifest go back, and the laptop's
verdict pipeline (recert_verdicts -> verdicted merge -> battery -> table to
Joel) remains the only road into champions.json.

Run modes:
  py tools\\remote_worker\\worker_watch.py --once   (one poll — the scheduled task)
  py tools\\remote_worker\\worker_watch.py          (same as --once)

Order file shape (written by send_work.py):
  {"id": "wave-YYYYMMDD-HHMM", "keys": [...], "commit": "<full sha>",
   "workers": 4, "node_cap": 50000, "recert": true}
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PY = sys.executable
BASE = os.path.join(os.environ.get("OneDrive") or "", "HeroCompanionCompute")
ORDERS = os.path.join(BASE, "orders")
RESULTS = os.path.join(BASE, "results")
STATE = os.path.join(BASE, "state")
LOCK = os.path.join(STATE, "worker.lock")


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True)


def _pid_alive(pid):
    r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                       capture_output=True, text=True)
    return str(pid) in r.stdout


def _claim_order():
    """Oldest unclaimed order, claimed by rename (rename loses the race
    cleanly if two ticks ever overlap)."""
    for f in sorted(glob.glob(os.path.join(ORDERS, "*.json"))):
        if f.endswith(".claimed.json"):
            continue
        claimed = f[:-5] + ".claimed.json"
        try:
            os.rename(f, claimed)
            return claimed
        except OSError:
            continue
    return None


def _heartbeat(order, prefix, t0, status, note=""):
    os.makedirs(STATE, exist_ok=True)
    counts = {}
    for sf in glob.glob(os.path.join(ROOT, prefix + "_p*.json")):
        try:
            counts[os.path.basename(sf)] = len(json.load(open(sf, encoding="utf-8")))
        except Exception:  # noqa: BLE001 — a mid-write shard reads next tick
            counts[os.path.basename(sf)] = "writing"
    hb = {"order": order["id"], "status": status,
          "elapsed_min": round((time.time() - t0) / 60.0, 1),
          "done": sum(v for v in counts.values() if isinstance(v, int)),
          "of": len(order.get("keys") or []), "shards": counts, "note": note,
          "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    tmp = os.path.join(STATE, f"heartbeat_{order['id']}.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(hb, f, indent=1)
    os.replace(tmp, os.path.join(STATE, f"heartbeat_{order['id']}.json"))


def main():
    if not os.environ.get("OneDrive"):
        print("OneDrive env var missing — is OneDrive set up on this machine?")
        sys.exit(1)
    for d in (ORDERS, RESULTS, STATE):
        os.makedirs(d, exist_ok=True)
    # single-job lock with liveness (a dead lock never wedges the box)
    if os.path.exists(LOCK):
        try:
            old = json.load(open(LOCK, encoding="utf-8"))
            if _pid_alive(old.get("pid", -1)):
                print(f"busy: order {old.get('order')} (pid {old.get('pid')})")
                return
        except Exception:  # noqa: BLE001
            pass
        os.remove(LOCK)

    claimed = _claim_order()
    if not claimed:
        print("no orders")
        return
    order = json.load(open(claimed, encoding="utf-8"))
    oid = order["id"]
    prefix = f"champions_shard_remote_{oid.replace('-', '_')}"
    t0 = time.time()
    print(f"claimed order {oid}: {len(order['keys'])} keys "
          f"@ commit {order['commit'][:12]}")
    json.dump({"pid": os.getpid(), "order": oid}, open(LOCK, "w", encoding="utf-8"))
    try:
        # ── the commit pin, verified not assumed ────────────────────────
        if _git("status", "--porcelain").stdout.strip():
            raise RuntimeError("worker clone is dirty — refusing to checkout")
        _git("fetch", "origin")
        if _git("cat-file", "-e", order["commit"]).returncode != 0:
            raise RuntimeError(f"commit {order['commit']} not found after fetch "
                               "— was it pushed?")
        _git("checkout", "--detach", order["commit"])
        head = _git("rev-parse", "HEAD").stdout.strip()
        if head != order["commit"]:
            raise RuntimeError(f"checkout landed on {head}, wanted {order['commit']}")
        _heartbeat(order, prefix, t0, "running", f"checked out {head[:12]}")

        cmd = [PY, os.path.join(ROOT, "tools", "converge_parallel.py"),
               "--workers", str(order.get("workers") or 4),
               "--shard-prefix", prefix,
               "--keys", ",".join(order["keys"])]
        if order.get("recert", True):
            cmd.insert(2, "--recert")
        env = dict(os.environ,
                   HC_SOLVER_NODE_CAP=str(order.get("node_cap") or 50000))
        logp = os.path.join(ROOT, prefix + "_orchestrator.log")
        with open(logp, "w", encoding="utf-8") as lf:
            proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=lf, stderr=lf)
            while proc.poll() is None:
                time.sleep(60)
                _heartbeat(order, prefix, t0, "running")
        rc = proc.returncode

        # ── return shards + logs + manifest ─────────────────────────────
        outdir = os.path.join(RESULTS, oid)
        os.makedirs(outdir, exist_ok=True)
        returned = []
        for sf in glob.glob(os.path.join(ROOT, prefix + "_p*.json")) \
                + glob.glob(os.path.join(ROOT, prefix + "_p*.log")) \
                + [logp]:
            shutil.copy2(sf, outdir)
            returned.append(os.path.basename(sf))
        done = {"order": oid, "commit": order["commit"], "exit_code": rc,
                "elapsed_min": round((time.time() - t0) / 60.0, 1),
                "files": sorted(returned),
                "keys_requested": len(order["keys"])}
        json.dump(done, open(os.path.join(outdir, "DONE.json"), "w",
                             encoding="utf-8"), indent=1)
        _heartbeat(order, prefix, t0,
                   "done" if rc == 0 else f"done_with_exit_{rc}")
        print(f"order {oid} finished (exit {rc}); "
              f"{len(returned)} files returned")
    except Exception as e:  # noqa: BLE001 — a failed order must say so remotely
        _heartbeat(order, prefix, t0, "FAILED", str(e))
        outdir = os.path.join(RESULTS, oid)
        os.makedirs(outdir, exist_ok=True)
        json.dump({"order": oid, "error": str(e)},
                  open(os.path.join(outdir, "FAILED.json"), "w",
                       encoding="utf-8"), indent=1)
        raise
    finally:
        if os.path.exists(LOCK):
            os.remove(LOCK)


if __name__ == "__main__":
    main()
