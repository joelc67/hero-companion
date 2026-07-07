# Companion Lite

The little brother of Hero Companion. One job, done quietly.

| | **Hero Companion** (green P) | **Companion Lite** (blue P) |
|---|---|---|
| What it is | The full build planner: optimizer, 1–50 walkthrough, respec worksheets, drop appraisal, Play Log insights | A tiny tray app that captures your game logs into local intel |
| Feeds | Your builds, plans, and insights | **The Pulse Boards only** |
| Size | ~55 MB, installer + tray server | One ~27 MB exe, no install |
| When you'd run it | When planning or reviewing | Whenever the game is on |

## What Lite does

- Watches **every account** with chat logging enabled (`/logchat` in game) — including
  dual-boxed accounts; a second account enabling logging mid-session is picked up
  automatically within seconds.
- Turns log lines into structured events: your rewards (XP, influence, drops, merits,
  badges, defeats) and **recruitment facts** from public channels (what's forming on
  the server — never raw chat).
- Renders your **Pulse Boards (alpha)** page from those events — right-click the blue
  P → Open Pulse Boards.
- Installs an optional **in-game menu** (`/popmenu Companion`) so enabling logging is
  one click from inside the game. A consent dialog shows exactly what file goes where
  before anything is written; Remove reverses it completely.

## What Lite shares

**Nothing.** Everything lives in `%APPDATA%\HeroCompanion` on your machine. There is
no upload, no telemetry, no account. When community boards open, sharing will be a
**separate, per-stat opt-in** — Lite will ask you again then, item by item, and
"no" will be remembered.

## Running Lite and the full app together

Fully supported, in any order, by design:

- **They never fight.** Different process names, no shared ports; the full app's
  single-instance logic ignores Lite entirely.
- **They never duplicate data.** Both read and write the same local event store behind
  a single-capturer lock: whichever is actively capturing holds it (the full app while
  its browser page is open; Lite the rest of the time), and the hand-off is automatic
  within about 90 seconds. Byte offsets are shared, so a line is only ever ingested
  once, by exactly one of them.
- **Either works alone.** Lite without the full app captures and shows boards; the
  full app without Lite captures while its Play Log page is open.

## Updates

Right-click the blue P → **Check for updates**. Never automatic — same policy as the
full app. If a newer Lite exists, the download page opens.
