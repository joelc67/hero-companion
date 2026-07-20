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

**The 90-day expiry is DELIBERATE (Joel's ruling, 2026-07-14).** A forever
token was considered and rejected: rotation is the documented 5-minute chore
above, the workflow self-warns 14 days out, and the staleness banner catches
a missed rotation honestly. Do not "improve" this to no-expiry.

## pulse-boards-inbox-upload (the OTHER credential — accepted exception)

The Lite/full-app UPLOAD key (`inbox_key.bin`, obfuscated in release builds)
has **NO expiration, deliberately** — an accepted, documented exception to
the expiry rule above, NOT an oversight:
- It is baked into every shipped exe in the field. Expiring it would brick
  the entire fleet's uploads until every user manually updated — a
  distribution constraint, not a hygiene preference.
- Its blast radius is bounded by scope: write-only to the private inbox
  repo. Worst case if leaked: junk uploads into a private mailbox that the
  growth guard and render sanitizer already defend against; it cannot read
  anything, cannot touch the public site, cannot see other users' data.
- **Do NOT add an expiration to this token.** If it must ever be revoked
  (actual leak), that is a coordinated fleet event: revoke + mint + bundle
  the new key into emergency releases of BOTH apps, knowing field installs
  are silent until they update.

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

## Pages deploy shape (2026-07-20 — ended the daily Jekyll-503 failure emails)

**Root cause (from the failure annotations):** Pages built in LEGACY mode (Deploy
from branch `master`/`docs`), which ran Jekyll on **every master push**;
`jekyll-github-metadata` called `api.github.com/.../pages` and intermittently
returned **503**, failing the build and emailing Joel — worst in rapid-push
windows. Nothing in docs/ actually uses `site.github` metadata.

**Current shape:** Pages source = **GitHub Actions** (`build_type: workflow`, set
via `gh api --method PUT repos/joelc67/hero-companion/pages -f build_type=workflow`).
`render-pulse.yml` owns the deploy — a `deploy` job (`needs: render`, `if: always()`)
runs `configure-pages` → `upload-pages-artifact (path: docs)` → `deploy-pages` after
each render. `docs/.nojekyll` makes the already-static site skip Jekyll entirely.

**Effects:** code pushes to master trigger **no** build (the legacy per-push build
is off; render-pulse runs only on its schedule + `workflow_dispatch`). The daily
failure emails end. The client-side staleness banner + "old board stays live if a
deploy is skipped" behavior are unchanged (the deploy publishes the same
`docs/pulse` output the render produces). Concurrency group `pages`,
`cancel-in-progress: false` — never cancel an in-flight Pages deploy.

**If the board stops updating:** check the `Render Pulse Boards` run — the `deploy`
job is the publish step now (not the old legacy build). Verify
`https://joelc67.github.io/hero-companion/pulse/` returns 200. To force a deploy:
`gh workflow run render-pulse.yml`.
