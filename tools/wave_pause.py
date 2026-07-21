"""PAUSE the v35 recert wave — safe shutdown for the end of the workday.

Progress model (why this is safe): every worker saves each context to its
shard the moment it converges. A pause therefore loses ONLY the context each
worker currently has in flight (deep_optimize holds its exploration in RAM
until context end — the known checkpointing gap). Everything already saved
stays saved; resume_wave re-runs exactly what's missing.

What it does, in order:
  1. kills the converge_parallel ORCHESTRATOR (so nothing fires at "completion")
  2. kills the buildout_champions WORKERS
  3. kills any straggler cbc solver subprocesses
  4. prints the inventory: saved contexts, and which keys will re-run tonight

Run:  py tools\\wave_pause.py            (or double-click pause-wave.bat)
      py tools\\wave_pause.py --dry-run  (show what it WOULD kill, touch nothing)
"""
import glob
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = os.path.join(ROOT, "tools", "wave_v35_keys.txt")
DRY = "--dry-run" in sys.argv


def _procs(match):
    """[(pid, cmdline)] of python.exe processes whose command line contains match."""
    out = subprocess.run(
        ["wmic", "process", "where", "name='python.exe'",
         "get", "ProcessId,CommandLine", "/format:list"],
        capture_output=True, text=True).stdout
    procs, cmd = [], None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("CommandLine="):
            cmd = line[len("CommandLine="):]
        elif line.startswith("ProcessId=") and cmd is not None:
            pid = line[len("ProcessId="):].strip()
            if match in cmd and pid.isdigit():
                procs.append((int(pid), cmd))
            cmd = None
    return procs


def _kill(pid):
    if DRY:
        print(f"    (dry-run) would kill PID {pid}")
        return
    subprocess.run(["taskkill", "/f", "/pid", str(pid)],
                   capture_output=True, text=True)


def main():
    orch = _procs("converge_parallel.py")
    workers = _procs("buildout_champions.py")
    print(f"orchestrator: {len(orch)} process(es); workers: {len(workers)}")
    for pid, _ in orch:
        print(f"  stopping orchestrator PID {pid}")
        _kill(pid)
    for pid, cmd in workers:
        first_key = cmd.split("--keys", 1)[-1].strip().split(",")[0][:60]
        print(f"  stopping worker PID {pid} ({first_key}…)")
        _kill(pid)
    if not DRY:
        subprocess.run(["taskkill", "/f", "/im", "cbc.exe"],
                       capture_output=True, text=True)   # solver stragglers

    all_keys = [l.strip() for l in open(KEYS, encoding="utf-8") if l.strip()]
    done = set()
    for f in glob.glob(os.path.join(ROOT, "champions_shard_par*_p*.json")):
        done |= set(json.load(open(f, encoding="utf-8")))
    remaining = [k for k in all_keys if k not in done]

    def _nm(k):
        p = k.split("|")
        return (p[1].split(".")[-1] + "/" + p[2].split(".")[-1]
                + (f" [{p[4]}]" if len(p) > 4 else ""))

    print(f"\nSAVED: {len(done & set(all_keys))} of {len(all_keys)} contexts "
          f"are converged on disk (shards are the save file — do not delete "
          f"champions_shard_par*_p*.json).")
    print(f"WILL RE-RUN on resume ({len(remaining)}):")
    for k in remaining:
        print(f"  {_nm(k)}")
    print("\nSafe to shut the machine down. Tonight: double-click "
          "resume-wave.bat (or ask Claude) — it re-runs ONLY the list above.")


if __name__ == "__main__":
    main()
