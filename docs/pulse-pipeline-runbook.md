# Pulse Boards pipeline — runbook

How the boards get built and published, and the one credential that needs
periodic care. (History: the 2026-07-14 quota incident — per-push renders on
the private inbox burned all 2,000 private-repo Actions minutes by mid-month;
2,031 runs ≈ 2,031 billed minutes, because a 31-second job bills a full
minute. The design below makes that class of failure structurally impossible.)

## The shape

- **Uploads** (Companion Lite / Hero Companion, consented): HTTPS PUTs into the
  private `hero-companion-inbox` repo. Uploads never trigger workflows.
- **Render** (`hero-companion/.github/workflows/render-pulse.yml`, THIS public
  repo): every 15 minutes, batches everything accumulated, builds the sanitized
  public board, commits `docs/pulse/index.html` to this repo. Public-repo
  minutes are free at any scale. Reads the inbox via the `INBOX_READ_TOKEN`
  secret (below). Cancel-in-progress; a red run means the pipeline itself broke.
- **Collect** (`hero-companion-inbox/.github/workflows/collect.yml`): once a
  day, folds processed chunks into one compacted file per source (the mailbox
  rule) — the only workflow on the private repo, ~31 billed minutes/month.
  NEVER add a push trigger there.
- **Staleness honesty**: the published page carries its own build stamp and a
  client-side script that flags "built N hours ago" past 2h — so even total
  render stoppage is visible without any server run (the server-drawn banner
  cannot cover that class; field-verified 2026-07-14).

## INBOX_READ_TOKEN (the one credential)

Fine-grained PAT, **expires 2026-10-12** (90 days). Settings:
- Resource owner: joelc67 · Repository access: ONLY `hero-companion-inbox`
- Permissions: **Contents: Read-only**. Nothing else.
- Stored as an Actions secret named `INBOX_READ_TOKEN` on the PUBLIC
  `hero-companion` repo (Settings → Secrets and variables → Actions).

**Expiry reminders, two layers:** the render workflow prints a warning
annotation on every run within 14 days of the hardcoded expiry date, and
CLAUDE.md's watch items carry the date. The staleness banner on the public
page is the LAST line of defense, not the first.

## Rotation (the 5-minute October chore)

1. github.com → Settings → Developer settings → Fine-grained tokens →
   Generate new token with exactly the settings above; set a new 90-day expiry.
2. hero-companion repo → Settings → Secrets and variables → Actions →
   update `INBOX_READ_TOKEN` with the new value.
3. Update the `EXPIRY=` date in `.github/workflows/render-pulse.yml` and the
   date in this file + CLAUDE.md's watch line.
4. Actions tab → Render Pulse Boards → Run workflow — confirm one green run.
5. Revoke the old token.

## If the board goes stale

1. Check the public repo's Actions tab — is Render Pulse Boards running/green?
2. Red runs: read the log — since the 2026-07-10 hardening, bad input degrades
   to a stale banner and exits green, so red = pipeline code/credential broke.
3. No runs at all: the schedule is disabled (repo inactivity auto-disable after
   60 days without commits — any commit re-enables) or the token expired.
