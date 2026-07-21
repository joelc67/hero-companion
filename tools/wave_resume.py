"""RESUME the v35 recert wave — picks up exactly where the pause left off.

Computes remaining = tools/wave_v35_keys.txt minus every context already
saved in ANY champions_shard_par*_p*.json, then relaunches the wave for just
those keys into FRESH shards (champions_shard_par_resume*) so old and new
shards never collide at merge time. Safe to run repeatedly: a second resume
after more completions re-runs only what is still missing.

Deliberately NO --merge: the completion pipeline is the VERDICT GATE
(tools/recert_verdicts.py over ALL par shards -> merge --replace --verdicts
-> validate -> battery -> table to Joel BEFORE champions.json commits).

Run:  py tools\\wave_resume.py            (or double-click resume-wave.bat)
      py tools\\wave_resume.py --dry-run  (show the relaunch command only)
"""
import glob
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
KEYS = os.path.join(ROOT, "tools", "wave_v35_keys.txt")
DRY = "--dry-run" in sys.argv


def main():
    all_keys = [l.strip() for l in open(KEYS, encoding="utf-8") if l.strip()]
    done = set()
    for f in glob.glob(os.path.join(ROOT, "champions_shard_par*_p*.json")):
        done |= set(json.load(open(f, encoding="utf-8")))
    remaining = [k for k in all_keys if k not in done]
    print(f"{len(done & set(all_keys))} of {len(all_keys)} saved; "
          f"{len(remaining)} remaining")
    if not remaining:
        print("Nothing to resume — run the verdict gate:")
        print("  py tools\\recert_verdicts.py " + " ".join(sorted(
            os.path.basename(f)
            for f in glob.glob(os.path.join(ROOT, "champions_shard_par*_p*.json")))))
        return
    # a resume run number that never collides with existing resume shards
    n = 1
    while glob.glob(os.path.join(ROOT, f"champions_shard_par_resume{n}_p*.json")):
        n += 1
    workers = min(4, len(remaining))
    cmd = [PY, os.path.join(ROOT, "tools", "converge_parallel.py"),
           "--recert", "--workers", str(workers),
           "--shard-prefix", f"champions_shard_par_resume{n}",
           "--keys", ",".join(remaining)]
    env = dict(os.environ, HC_SOLVER_NODE_CAP="50000")
    print("relaunch:", " ".join(cmd[:7]) + " --keys <" + str(len(remaining)) + " keys>")
    if DRY:
        print("(dry-run — nothing launched)")
        return
    log = os.path.join(ROOT, f"champions_recert_v35_resume{n}_log.txt")
    with open(log, "w", encoding="utf-8") as lf:
        subprocess.Popen(cmd, env=env, stdout=lf, stderr=lf,
                         cwd=ROOT,
                         creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    print(f"launched detached; log: {os.path.basename(log)}")
    print("When all workers finish, the pipeline is: recert_verdicts.py over "
          "ALL par shards -> verdicted merge -> validate -> battery -> "
          "verdict table to Joel before champions.json commits.")


if __name__ == "__main__":
    main()
