# Remote Worker — distributed champion crunching

The dev laptop **conducts**; a second machine (the gaming box) **crunches**.
Built 2026-07-28 for big certification waves and future mass roster expansion.

## The connectivity model (read this first)

The worker box is **never reachable from the internet, and never needs to
be**. It makes outbound connections only:

- **Orders** (tiny JSON) travel laptop → box via a shared OneDrive folder
  (`%OneDrive%\HeroCompanionCompute\`).
- **Code + data** arrive by `git fetch` of the public GitHub repo, pinned to
  the exact commit each order names.
- **Heartbeats + finished shards** travel box → laptop via the same OneDrive
  folder.

No port forwarding, no VPN, no tokens, no services listening. A LAN IP is
irrelevant to operation — it works identically whether the laptop is at home,
at work, or anywhere else with internet. If the box is asleep, orders simply
wait; the watcher claims them within ~5 minutes of the box being awake.

## One-time setup on the worker box

Prereqs: Git for Windows, Python 3.11+, OneDrive signed in (same account as
the laptop).

1. Copy `tools\remote_worker\install-worker.bat` to the box (or clone the
   repo and run it from there) and double-click it. It clones the repo to
   `%USERPROFILE%\code\hero-companion-worker`, installs deps, creates the
   OneDrive mailbox, and registers the hidden 5-minute watcher task
   (`HC_RemoteWorker`).
2. That's it. Retire it any time: `schtasks /delete /f /tn HC_RemoteWorker`.

Power settings matter: the box only crunches while awake. For overnight jobs,
set sleep to Never (or wake it before sending the order).

## Conducting from the laptop

```
py tools\remote_worker\send_work.py --keys-file tools\wave_current_keys.txt --workers 6
py tools\remote_worker\watch_remote.py          # progress, from anywhere
py tools\remote_worker\collect_work.py          # pull finished shards home
```

`send_work.py` refuses to send a commit that isn't pushed; the box refuses to
run a commit it can't check out exactly. That pin is what keeps canonical
scores comparable — **both machines always run identical code and data.**

## Hard rules (the certification protocol applies in full)

- **The box never merges.** Shards come home and go through the same verdict
  gate as local ones: `recert_verdicts` → verdicted merge → validate →
  battery → **table to Joel before champions.json commits**.
- Remote shard names are collision-proof by construction
  (`champions_shard_remote_<order-id>_p*.json`), and `collect_work.py`
  refuses to overwrite an existing file.
- One order at a time per box (lock with liveness check — a crashed run
  never wedges the worker).
- Roster **expansion** is certification: harden-before-certify applies to
  remote waves exactly as to local ones.

## Failure modes, stated

- Order fails on the box → `FAILED.json` + a `FAILED` heartbeat come back
  with the error; nothing partial is collected silently.
- Box interrupted mid-wave → completed contexts are banked in its shards
  (same per-context banking as local waves); resend a fresh order for the
  remainder — shard prefixes never collide, and `--recert` orders re-run
  exactly what you name.
- OneDrive still syncing when you collect → `collect_work.py` names the
  missing files and leaves the manifest uncollected so a later run finishes
  the job.
