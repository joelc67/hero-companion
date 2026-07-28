# Companion Lite

The little brother of Hero Companion. One job, done quietly.

| | **Hero Companion** (green P) | **Companion Lite** (blue P) |
|---|---|---|
| What it is | The full build planner: optimizer, 1–50 walkthrough, respec worksheets, drop appraisal, Play Log insights | A tiny tray app that captures your game logs into local intel |
| Feeds | Your builds, plans, and insights | **The Pulse Boards only** |
| Size | ~45 MB signed installer (or ~58 MB portable zip) | ~21 MB signed installer (per-user, Start Menu entry, clean uninstall) |
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
- Asks **once, on first run**, whether to start with Windows — never silently on, and
  you can flip it any time from the tray. Uninstalling removes it cleanly.
- Both the installer and the app are **code-signed** — Windows names the publisher
  instead of showing an "unknown publisher" warning.

## What Lite shares

**Nothing, until you say otherwise.** Everything lives in `%APPDATA%\HeroCompanion`
on your machine; there is no telemetry and no account. Feeding the community Pulse
Board is a **separate, explicit opt-in**: before you agree, Lite shows you exactly
what sharing looks like (structured events only, accounts pseudonymized — never raw
chat), and the public board preview shows precisely what would be visible. The feed
can be turned off from either app and the off is honored by both; your "no" is
remembered. When more board stats arrive, each will be its own opt-in.

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
full app. If a newer Lite exists it asks first; say yes and it updates itself and
relaunches (if it can't — for example, running from source — it opens the download
page instead).
