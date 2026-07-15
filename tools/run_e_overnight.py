"""E-run overnight driver (Joel's work order 2026-07-15) — one keypress, then
the night runs itself. Start it before bed via "Run E Overnight.bat".

What it does, in order:
1. Asks the PRICING RULING (the one decision the written channel is missing):
     [M] adopt the measured aura/patch fix -> merges the parked
         v32-measured-aura-pricing branch, runs the full battery (hard gate),
         runs evaluate-first over the roster, and re-converges any movers
         BEFORE the E queue (certificates are model-version-bound — ground
         truths must not run under a model about to change).
     [T] keep the dev-archive theory -> v31 stands, straight to the E queue.
2. Runs the E ground-truth queue: every context in benchmarks/e_holdout.json
   converged at certification standard on the parallel orchestrator, saved to
   champions_shard_e_gt_*.json (NEVER merged into the roster — experiment
   artifacts only). Per-context checkpointing: a killed night resumes by
   re-running this script (completed contexts are skipped automatically).
3. Leaves the derived-side comparison for the morning session (minutes).

farm_active stays HELD either way (scenario-shape ruling deferred).
"""
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def run(args, **kw):
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, cwd=ROOT, **kw).returncode


def gate(rc, what):
    if rc != 0:
        print(f"\n== HARD STOP: {what} failed (rc={rc}) — nothing else runs. "
              f"Leave everything as is for the morning session. ==")
        sys.exit(rc)


def main():
    print("=" * 72)
    print("E-RUN OVERNIGHT — one decision, then go to bed.")
    print("=" * 72)
    ans = ""
    while ans not in ("m", "t"):
        ans = input("Pricing ruling — [M] adopt the measured aura/patch fix "
                    "(v32) / [T] keep theory (v31): ").strip().lower()
    if ans == "m":
        print("\n[M] Merging the parked v32 branch…")
        gate(run(["git", "merge", "v32-measured-aura-pricing", "--no-edit"]),
             "git merge")
        print("\nFull battery (the gate before anything certifies)…")
        for tool in ("demo_single_build_fixes", "audit_slotting_coherence",
                     "audit_slot_legality", "audit_slot_conservation",
                     "audit_preset_caps", "reality_check_powers",
                     "reality_check_setbonuses"):
            gate(run([PY, os.path.join("tools", f"{tool}.py")]), tool)
        print("\nEvaluate-first over the roster (movers re-converge next)…")
        gate(run([PY, os.path.join("tools", "evaluate_first.py"), "--write",
                  "--skip-riders"]), "evaluate_first")
        # Movers (MOVED verdicts) re-converge before E. evaluate_first exits 0
        # either way, so read the verdicts from champions.json.
        champs = json.load(open(os.path.join(ROOT, "benchmarks",
                                             "champions.json"),
                                encoding="utf-8"))
        movers = [k for k, v in champs.items()
                  if (v.get("certificate", {}).get("evaluated", {})
                      .get("verdict")) == "moved"]
        if movers:
            print(f"\n{len(movers)} mover(s) re-converge first: {movers}")
            gate(run([PY, os.path.join("tools", "converge_parallel.py"),
                      "--keys", ",".join(movers), "--recert", "--merge",
                      "--shard-prefix", "champions_shard_v32_recert"]),
                 "mover re-convergence")
        else:
            print("\nZero movers — the roster carries forward under v32.")
        run(["git", "add", "-u"])
        run(["git", "commit", "-m",
             "v32 adopted on Joel's keypress: measured aura/patch pricing "
             "merged, battery green, roster re-verified",
             "-m", "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"])
        run(["git", "push"])
    else:
        print("\n[T] v31 stands. Straight to the E queue.")

    holdout = json.load(open(os.path.join(ROOT, "benchmarks",
                                          "e_holdout.json"),
                             encoding="utf-8"))
    keys = [row["key"] for row in holdout["contexts"]]
    print(f"\nE ground-truth queue: {len(keys)} contexts "
          f"(completed ones auto-skip via the shard union).")
    print("This runs for hours — that is the plan. Ctrl+C is safe; re-run "
          "this script to resume.\n")
    gate(run([PY, os.path.join("tools", "converge_parallel.py"),
              "--keys", ",".join(keys), "--experiment",
              "--shard-prefix", "champions_shard_e_gt",
              "--workers", "3"]), "E ground-truth queue")
    print("\n== E ground truths done for the night. Do NOT merge the e_gt "
          "shards into champions.json — they are experiment artifacts. The "
          "morning session runs the derived side + the verdict table. ==")


if __name__ == "__main__":
    main()
