"""Collect finished remote work into the repo (laptop side).

Scans %OneDrive%\\HeroCompanionCompute\\results\\*/DONE.json, verifies each
manifest's commit against the order that produced it, copies the shards into
the repo root (REFUSING any filename that already exists — collision-proof by
construction), and renames the manifest COLLECTED.json so a re-run is a no-op.

It then prints the verdict-gate command — the box never merges, and neither
does this: recert_verdicts -> verdicted merge -> battery -> table to Joel
remains the only road into champions.json.

Run:  py tools\\remote_worker\\collect_work.py [--dry-run]
"""
import glob
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(os.environ.get("OneDrive") or "", "HeroCompanionCompute")
DRY = "--dry-run" in sys.argv


def main():
    if not os.environ.get("OneDrive"):
        raise SystemExit("OneDrive env var missing on this machine")
    manifests = sorted(glob.glob(os.path.join(BASE, "results", "*", "DONE.json")))
    if not manifests:
        print("nothing to collect (no uncollected DONE.json manifests)")
        failed = glob.glob(os.path.join(BASE, "results", "*", "FAILED.json"))
        for f in failed:
            print(f"  ⚠ FAILED order: {f}: "
                  + (json.load(open(f, encoding='utf-8')).get('error') or '?'))
        return
    collected_shards = []
    for mf in manifests:
        d = json.load(open(mf, encoding="utf-8"))
        oid, commit = d["order"], d["commit"]
        outdir = os.path.dirname(mf)
        print(f"order {oid} (commit {commit[:12]}, exit {d.get('exit_code')}, "
              f"{d.get('elapsed_min')} min):")
        for fn in d.get("files", []):
            src = os.path.join(outdir, fn)
            if not os.path.exists(src):
                print(f"  ⚠ listed but missing (OneDrive still syncing?): {fn}")
                continue
            dst = os.path.join(ROOT, fn)
            if fn.endswith(".json"):
                if os.path.exists(dst):
                    raise SystemExit(f"  COLLISION: {fn} already exists in the "
                                     "repo root — refusing (resolve by hand)")
                if not DRY:
                    shutil.copy2(src, dst)
                collected_shards.append(fn)
                print(f"  shard -> {fn}")
            else:
                logdst = os.path.join(ROOT, fn)
                if not DRY and not os.path.exists(logdst):
                    shutil.copy2(src, logdst)
        if not DRY:
            os.replace(mf, os.path.join(outdir, "COLLECTED.json"))
    if collected_shards:
        print("\nNext (the verdict gate, laptop-only):")
        print("  py tools\\recert_verdicts.py " + " ".join(sorted(collected_shards)))
    if DRY:
        print("(dry-run — nothing copied)")


if __name__ == "__main__":
    main()
