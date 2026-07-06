"""Refresh every champion in benchmarks/champions.json to the GOLD STANDARD —
fully local, no AI involved: deep_optimize is the deterministic CBC/first-principles
climb running on this machine's CPU.

Each context gets a fresh L1-legal autopick seed, then converge + restarts under a
GENEROUS budget (the overnight setting), and learn.save_champion stores the result
with its honest certificate. Safe to interrupt: each champion is saved as its
context finishes, and the learning log keeps everything explored.

Run overnight:   py tools\refresh_champions.py
Quick pass:      py tools\refresh_champions.py --max-solves 1500 --restarts 3
"""
import argparse
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-solves", type=int, default=25000,
                    help="solve budget per context (default 25000 = overnight)")
    ap.add_argument("--restarts", type=int, default=6,
                    help="perturb-and-reclimb restarts per context (default 6)")
    args = ap.parse_args()

    client = srv.app.test_client()
    champs = json.load(open(os.path.join(ROOT, "benchmarks", "champions.json"),
                            encoding="utf-8"))
    t0 = time.time()
    results = []
    for key in list(champs.keys()):
        at, prim, sec, content = key.split("|")
        el = (time.time() - t0) / 60
        print(f"[{el:6.1f}m] {key}", flush=True)
        ap_res = client.post("/build/autopick", json={
            "archetype": at, "primary": prim, "secondary": sec,
            "content": content}).get_json()
        if not (ap_res and ap_res.get("powers")):
            results.append((key, "AUTOPICK FAILED", None))
            continue
        try:
            _, info = srv.deep_optimize(at, prim, sec, None, content,
                                        ap_res["powers"],
                                        max_solves=args.max_solves,
                                        restarts=args.restarts)
            cert = info.get("certificate")
            results.append((key, f"score {info.get('score'):.1f}", cert))
            print(f"   -> score {info.get('score'):.1f}  certificate: {cert}", flush=True)
        except Exception as e:  # noqa: BLE001
            results.append((key, f"ERROR {type(e).__name__}: {e}", None))
            print(f"   -> ERROR {e}", flush=True)

    print("\n=== GOLD-STANDARD REFRESH SUMMARY ===")
    for key, status, cert in results:
        conv = "CONVERGED" if (cert or {}).get("converged") else "truncated"
        print(f"  {conv:10s} {status:16s} {key}")
    print(f"total: {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
