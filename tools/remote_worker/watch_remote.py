"""Watch the remote worker's progress from the laptop, from anywhere.

Reads the heartbeat files the box drops into OneDrive every ~60s while a
wave runs. One line per known order, newest first.

Run:  py tools\\remote_worker\\watch_remote.py
"""
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.join(os.environ.get("OneDrive") or "", "HeroCompanionCompute")

hbs = sorted(glob.glob(os.path.join(BASE, "state", "heartbeat_*.json")),
             reverse=True)
if not hbs:
    print("no heartbeats yet (no orders run, or OneDrive still syncing)")
for f in hbs:
    try:
        h = json.load(open(f, encoding="utf-8"))
    except Exception:  # noqa: BLE001 — mid-sync file, try next run
        continue
    print(f"{h.get('order')}: {h.get('status')}  "
          f"{h.get('done')}/{h.get('of')} contexts  "
          f"{h.get('elapsed_min')} min  (as of {h.get('written_utc')} UTC)"
          + (f"  note: {h['note']}" if h.get("note") else ""))
