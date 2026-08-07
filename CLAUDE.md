# Hero Companion — Session Memory (CLAUDE.md)

**⚠ LOADING (found 2026-07-30, after a full session ran without this file): CLAUDE.md
auto-loads for the cwd and its PARENTS, never a subdirectory.** Sessions start in
`C:\Users\joelc\code`, so this file did NOT load — the parent
`C:\Users\joelc\code\CLAUDE.md` now carries `@coh-builder/CLAUDE.md` to pull it in.
If a session ever shows no knowledge of the rules below, check that import first.

**Standing rule: when a session establishes a durable fact, workflow, or decision, update this file before the session ends.** Do not let knowledge die with the session.

## What belongs in this file (Joel's ruling, 2026-07-30)

The 2026-07-27 condensation was right to cut and wrong in what it cut. It removed
14 stacked `PREVIOUS STATE` snapshots (~200 of 331 lines) — correct, that is
superseded history — but durable rulings recorded *inside* those snapshots went
with them. This merge restores those into thematic homes and keeps the snapshots
out. Rules going forward:

- **This file holds STANDING RULES ONLY**: rulings, doctrines, pinned game facts,
  traps with a corpse behind them, and ONE current state. Never a second
  "PREVIOUS STATE" section — the moment one would be written, that content goes to
  session-report.md and the release ledger instead.
- **The accumulated mass lives in graphify** (graphify-out/), git history, and
  session-report.md. That is graphify's whole premise: it is how to approach a
  large accumulated codebase without bloating this file. Reach for
  `graphify query` before growing a section here.
- **Every bullet states its own resolution.** A two-act story ("my parse was
  wrong" → "corrected properly") split across adjacent bullets gets acted on from
  the first one. Cost 2026-07-30: I read the alarm bullet, declared a healthy
  wave's premise broken, and had to retract it. Put the outcome in the same
  bullet as the alarm, or do not write the alarm.
- **Dated measurements carry what they measured and what superseded them.** Cost
  2026-07-30: I quoted "PB triform = 484 min" for hours after the prereq fix had
  made it 261, because the entry read as timeless truth.

## Communication protocol (token discipline — strict)

Joel's session context is a limited resource. Do not spend it on prose.

- **Chat replies: 10 lines max.** State what was done, what's blocked, what you need from Joel. No narrative recaps, no restating the plan, no explaining code Joel didn't ask about.
- **All detail goes to the outbound report:** `C:\Users\joelc\code\session-report.md` (outside this repo, never committed). Prepend each session's entry at the top with a date + session heading. Write dense and factual — findings, decisions, file/function names, open questions — not play-by-play.
- Joel reads session-report.md through his Cowork chat and sends follow-ups via `ideas.md`. So: `ideas.md` = inbound, `session-report.md` = outbound, chat = short status only.
- Long explanations, root-cause writeups, and "where things stand" summaries belong in session-report.md, never in chat.

## Dev preview workflow (do not re-derive this)

- The **installed tray app owns port 5000**. Never kill it, never try to bind 5000.
- The **dev copy runs on port 5080**, launched via `start-dev.bat` at the repo root (Joel also has a desktop shortcut to it). Both copies run side by side.
- To verify UI changes: have Joel run `start-dev.bat` and check http://localhost:5080 (hard-reload after changes — the browser caches app.js).
- The Claude preview_start tool refuses to run while 5000 is busy, even pinned to 5080. For automated smokes, start a throwaway server via `PORT=5081 python server/server.py` in the background, curl it, kill it.
- Server runs `debug=False`: **every server-side code or data change needs a restart** before it takes effect. Headless verification without any port: `sys.path.insert` both repo root and `server/`, `import server as srv`, `srv.app.test_client()`.
- The frozen exe writes saves to `%APPDATA%\HeroCompanion\saves`; dev uses repo `saves/`.
- **Static-file changes need NO restart:** index.html is served no-store with per-file-mtime `?v=` tokens, so a plain F5 on the ROOT url refreshes everything. `/static/index.html` directly BYPASSES the tokens — the root URL is the one that self-refreshes.

## Standing watch items

- **PATCH-WATCH (public promise, posted round-5 correction 7(a); wired 2026-07-17).** Trigger: any Homecoming patch announcement, or Joel's word. Steps, in order: (1) full Bin Crawler re-export from `C:\Games\HC2\assets\live`; (2) structural diff vs current data — `tools/reality_check_effect_structure.py` (effect existence/enhanceability, the gap class scalar checks can't see) plus the scalar reality checks; (3) delta report to session-report.md; (4) **movers ruling BEFORE any certification run starts** — harden-before-certify applies in full. Release procedure addition: release notes state **data currency** — the date of the last client re-export vs the game's latest patch. **After any client re-export, also re-run the power-icon pipeline** (extract_power_icons → patch_power_icons).
- **⚠⚠ ONE DEPLOYER, AND THE TWO HALVES MOVE TOGETHER (found 2026-08-06,
  `0c06b9df`).** From 07-27 to 08-06 the repo had TWO things deploying the site:
  GitHub's own per-push build (the legacy source) **and** a `deploy` job inside
  `render-pulse.yml`. The job arrived 2026-07-20 (`564814ca`) *together with* a
  flip of the Pages source to "GitHub Actions"; on 07-27 the SOURCE was flipped
  back to legacy after the 8-day freeze **but the job was left behind** — half a
  revert. Both then raced into the same `github-pages` environment. Measured
  that day: render deploy 5 success / 3 failure / 2 cancelled, legacy workflow
  11 / 9 / 9, losers carrying `Invalid actions OIDC token` — the signature of
  contention, on top of one genuine GitHub-side token failure. **The deploy job
  is REMOVED; the render's own commit publishes, as it did before 07-20.**
  Evidence it worked: Pages status went `errored` → `built` and the first build
  after the change succeeded (commit `2c1c7040`). ⚠ **RULE: the Pages source and
  this workflow's deploy job are ONE decision. Moving the source back to "GitHub
  Actions" means restoring a deploy job in the same change** — one without the
  other caused both outages. `docs/.nojekyll` stays either way.
- **⚠ PAGES BUILD TYPE MUST STAY `legacy` (branch-based).** Found 2026-07-27 night: build_type had been flipped to "workflow" ~2026-07-20 15:36Z, which silently STOPS automatic branch builds — the site (INCLUDING the pulse board at /pulse) served frozen 7/20 content for 8 days while render-pulse kept committing fresh boards nobody deployed. Restored via `gh api -X PUT .../pages -f build_type=legacy` + POST a build. If the boards ever look stale despite green render runs, check `gh api .../pages/builds/latest` FIRST — a stale build date with green workflows = this failure mode. **Detector: `.github/workflows/site-freshness.yml`** (daily 12:17 UTC, checks the LIVE board for today/yesterday's date; red run emails Joel; cause-agnostic; proving run green 2026-07-28). What flipped the setting on 7/20 is UNKNOWABLE (personal accounts have no repo-settings audit log; likeliest = the Pages settings UI source dropdown).
- **🌐 hero-companion.com (registered at Network Solutions 2026-07-27, Joel's account).** Points at GitHub Pages (master:/docs — landing page + pulse boards): 4×A @→185.199.108-111.153, CNAME www→joelc67.github.io, docs/CNAME committed, Pages cname set, HTTPS ENFORCED (cert approved, http→301→https, www→apex verified), domain VERIFIED to Joel's GitHub account (TXT `_github-pages-challenge-joelc67` — keep forever, checked continuously), parking record deleted+verified gone. ⚠ WATCH: the NetSol RENEWAL date — a lapse breaks the site + every published link. github.io URLs auto-redirect.
- **⛔ THE 08-01 RE-ENABLE WAS TRIED ON 2026-08-06 AND FAILED — THE ALLOWANCE HAS
  NOT RESET. Both workflows are `disabled_manually` again; do NOT re-enable on a
  date alone.** Evidence: enabled both, ran `Collect mailbox` manually (run
  31127012557) — it sat **QUEUED for 55.9 minutes and was then cancelled with
  ZERO steps**. That is a different shape from the July failures (0.1 min) but
  the same fact: **the job never got a runner**. A calendar date is not evidence
  the allowance is back; **the proving run is**. Re-disabled the same evening so
  the daily failure mail does not resume — that mail is exactly why they were
  turned off. ⚠ **Next step is JOEL'S, not mine:** github.com/settings/billing —
  the earlier note suspected a DECLINED PAYMENT METHOD, which would not
  self-heal on a monthly reset, and nothing was consumed in August (the
  workflows were off all month), so an exhausted-minutes explanation does not
  fit. The billing API needs gh `user` scope, which is deliberately not granted;
  do not re-auth to chase this. ⚠ **Nothing is lost meanwhile and the boards are
  unaffected** — the render lives in the PUBLIC repo and reads the inbox
  directly (verified same evening: board 200, current date). What IS accruing is
  un-squashed inbox history: **2,633 commits since 07-27**, ~288/day, 8.4 MB.
  Original context below.
- **⏰ (superseded, kept for the reasoning) RE-ENABLE THE INBOX WORKFLOWS ON 2026-08-01 (both `disabled_manually` since 2026-07-27).** `gh workflow enable "Collect mailbox" --repo joelc67/hero-companion-inbox` and the same for `"Inbox maintenance"`. **Why disabled:** the private repo's billed Actions minutes ran out after the 7/14 runaway; from 7/16 every scheduled run failed at startup in 2-4s with zero steps and mailed Joel each morning. Nothing lost. **Cost was always $0** (GitHub Free refuses to start jobs rather than bill; billing page: gross $53.32 fully offset, billed $0 every day). **Leave the spending limit at $0 — that is what guarantees it can never cost money.** After re-enabling, confirm the next scheduled run succeeds; failing in seconds with zero steps = allowance not reset. ⚠ Do NOT "fix" this in the workflow files — there is no workflow bug. ⚠ Billing API needs gh `user` scope (not granted; don't re-auth).
- **INBOX_READ_TOKEN expires 2026-10-12** (the Pulse render's read-only PAT — rotation is a 5-minute chore per docs/pulse-pipeline-runbook.md; the render workflow self-warns within 14 days).
- **MRB v4 alpha/beta**: keep .mbd import/export compatible as the format moves (public promise to Jacke).
- **Artifact Signing identity revalidation expires 2027-07-15** (Azure Trusted Signing, account `herocompanionsign`). A lapse HALTS all signing. Portal → the signing account → Identity validations. Facts + prereqs: docs/signing-runbook.md; signer: tools/sign_artifacts.py (needs `az login` + "Artifact Signing Certificate Profile Signer" role + `TRUSTED_SIGNING_PROFILE=hero-companion-public`).
- **Unrelenting Fury stack cap — UNRESOLVED DATA CONFLICT (2026-07-16, v33 ruling C).** Template says `stack_limit 2`; the piece's help text says "stacks up to 5 times"; both client-derived. We ship the TEMPLATE value (conservative, errs AGAINST our own sustain claim); disagreement bounded at 1.5pp of regen. **Resolve game-first when convenient** (bins elsewhere, or live-game measurement on Joel's logs). This entry exists so "conservative forever" can never become a silent default.

## Release rules

- Nothing is released without Joel's say-so — **always ask before `gh release create`, asset uploads, or publish-intent version bumps.** Commits and pushes stay autonomous. Changelog entries are staged under **"Unreleased"** until he approves.
- "Please make it a rule to not immediately deploy an update until after I have gone over all the issues we need to fix first." Batch fixes; wait for his full field report.
- **champions.json bundles with EVERY release** (client is deterministic, NOT AI — champion knowledge ships as data). ⚠ CHAMPION-MASK TRAP: source tests can pass via hub-only champions.json while standalone users hit the heuristic picker — **smoke-test the FROZEN exe before every release** (pinned Defender Poison/Sonic case).
- **SIGNING (Windows Citizenship, 2026-07-17): both apps' release artifacts are code-signed.** Chain per release: sign exe → ISCC → sign installer → verify both (tools/sign_artifacts.py prints exactly what's missing and signs nothing if a prereq is absent). ⚠ sign_artifacts with NO args sweeps stale dist artifacts and can abort — pass explicit paths when dist/ is dirty. Per release, run the FP/whitelist submission checklist in docs/signing-runbook.md. **Companion Lite version is a TWO-PLACE bump** (run_lite.py `LITE_VERSION` + installer/CompanionLite.iss `AppVersion`); `lite_version.txt` bumps only when the release actually publishes.
- Release procedure: **data-currency check first** → bump VERSION → **smoke pins** (⚠ smoke_release has TWO version pins — port-race guard AND assertion; smoke_gold same + model pin) → CHANGELOG date → `python tools\build_help_pdf.py` → stop HeroCompanion processes → PyInstaller `HeroCompanion.spec --noconfirm` → copy "Add Shortcuts.bat" into `dist\HeroCompanion\` → frozen-exe smoke + gold → sign exe → ISCC (`%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe` — per-user, NOT Program Files; reads VERSION dynamically) → sign installer → Compress-Archive zip → commit/push → `gh release create vX.Y.Z` with BOTH assets → verify via `gh api .../releases/latest`.
- The repo is public on GitHub (github.com/joelc67/hero-companion; Joel's GitHub = joelc67, gh CLI authed in keyring). Keep raw brainstorms and personal notes out of commits. Ideation notes live in `C:\Users\joelc\code\ideas.md` (outside this repo); when Joel says "read ideas.md", that's the file.
- **Push discipline:** the Pulse pipeline pushes to this repo's master ~30×/day. After every commit: push; on rejection `git pull --no-rebase` (merge, NEVER rebase — session reports quote hashes) then push.
- **⚠ BUT BATCH THEM — EVERY PUSH TO master IS A CI EVENT, AND JOEL GETS THE
  EMAIL (2026-08-06).** He reported "notifications many times today" about
  failed `pages build and deployment`. Diagnosed: **28 commits to master that
  day, 24 of them MINE** across one long session. Each push fires Pages
  build+deploy and can supersede an in-flight `Render Pulse Boards` run;
  **a superseded run is CANCELLED, and GitHub mails "Some jobs were not
  successful" for a cancelled job exactly as for a failed one.** Tally that day:
  Pages 11 success / 9 cancelled / 9 failure, Render Pulse Boards 3/5 (the
  "failures" were cancelled jobs). **The repo was healthy throughout** — site
  200, pulse board showing that day's date, `build_type` still `legacy`.
  ⚠ One deploy DID fail for a real reason, and it was GitHub's, not ours:
  `Invalid actions OIDC token — No keys from key endpoint match the id token`
  (GitHub's own token service failing to validate its own token; nothing in the
  repo or Pages config causes it). **The lesson is mine: commit freely, push in
  batches at natural stopping points**, not after every single commit during a
  long session. Quieting the mail is Joel's account setting, never mine to change.
- License CC BY-NC-SA 4.0 ("free and noncommercial, forever"); truthful credits always, including the Claude co-author line on commits ("Leave it, its true").

## Credits

- **Maelwys** (forums profile 30623) — CREDITS.md "The Reviewer" + help.md credits paragraph (done 2026-07-08). **Gulbasaur** (Good/Mean Missions guides) = *The Guide Writer*; **n15g** (coh-content-db, Unlicense) credited on the surface + in the data (⚠ confirm the coh-content-db LICENSE file reads Unlicense before any wider distribution — repo page says so, raw LICENSE 404'd on the branch guessed). **driver.js 1.8.0** (MIT, vendored static/vendor/) credited in CREDITS.md. Guyver [SoV] per earlier releases.

## Design principles (from Joel)

- One shared pool of game-engineered rules, but **every champion/build is unique unto itself** — the planner must not treat builds as one-size-fits-all within that rule scope. (Recorded at the top of docs/build-doctrine.md.)
- Audits/checkmarks are not ground truth — Joel's eyes outrank green audits. Coherence audits must hard-fail on empty slots, icon-less pieces, and validation noise.
- **Role doctrine**: CoH is a role-based game first. The Role picker is the declared objective; off-role is only ever an explicit user choice (warn, don't block). Support/control roles follow the **invisible-role doctrine**: their output must be exceptionally powerful just to be noticed — maximize debuff magnitude × uptime, control reach, sustain; never generic damage slotting on a non-damage role.
- **Optimization doctrine ("3D chess")**: think to the END — converge with restarts and honest certificates, never truncated-as-done; explore, don't prune; **NO ban lists** ("This picker is not a child") — when the search picks trash, fix the model term that made trash look good; LEARN across runs (champions/marginals/lessons/retrospective); masters are evidence and a floor to beat, never prescriptions ("evolve BEYOND master setups").
- **Wiki-verify / GAME-FIRST**: never build on best guesses. Order of authority: game client bins (`C:\Games\HC2\assets\live\` via Bin Crawler/Pigg Wrangler in tools/gamedata) → dev-archive docs → measured logs → wiki paste from Joel (wikis block WebFetch) — never fan posts. When the tool and the game disagree, the game is right.
- **Universal rules, no hacks**: a game-rule fix is implemented archetype-independently and proven with an all-AT audit (audit_epic_tiers / audit_slot_schedule pattern) — never patch just the reported case.
- **Harden-before-certify (2026-07-08 + sharpened 07-14)**: no long certification run STARTS while a correctness question is open or a verification improvement is pending — and **roster EXPANSION is certification; the rule applies in full.** Mid-run question: model/data-affecting → stop the run; out of scope → make the checker state the exclusion explicitly.
- **Coverage-denominator rule (2026-07-08)**: every audit/reality check/battery prints **"N of M expected checked"** where M comes from an independent source — and **hard-fails when N < M**. A checker that can't state its denominator can silently lie.
- **Boost boundary (2026-07-09)**: champions are NEVER built, certified, or scored on boosted (+1..+5) values — certify clean; boosting is display preview and later a priced upgrade rung. If solver-boosting work proposes certifying boosted champions, the answer is no.
- **Choice doctrine**: "People should always have a choice." Anything touching user data/machines = informed opt-in, remembered + reversible "no", advise-don't-override; sharing consent separate from local capture; anonymous by default; NO PII ever.
- **Custom-targets doctrine (2026-07-20): HONOR the user's stated goal — and STATE what it costs.** Custom targets are the objective's priority at BOTH layers (pick proposal AND slotting), the tradeoff is stated in numbers, and only the genuinely unreachable is refused — with numbers and a remedy. The editor states its drop-semantics. Never silently traded.
- **Instrument, not a sixth fix (2026-07-24)**: when the harness and the user's screen disagree, ship an instrument (a gate-log, the header build stamp) — a repro can only exercise the path I chose; the log speaks from the path he actually took.
- Copy rules: never say "illegal" bare ("the game won't allow it"); plain English before jargon; "easiest route, never the only way"; **no em dashes in outward-facing text Joel sends**.
- Hasten: Joel dislikes relying on it (Guyver's rule = never past 2 slots). Vocab: a "mule" = a dual-boxed alt character, not a bonus-holding power.

## Guided tour — final design (shipped 0.12.29; REBUILT for the tabbed app 2026-08-04, f9176684 — see the tabbed-app section for the rebuild's traps; every rule below is one of Joel's rulings, 2026-07-27, and still governs)

- **The tour NEVER walks the live page.** It paints a full-screen MOCK (z-55): a made-up SS/WP Brute damage build + a copy of the opening menu, hand-built from the app's real markup shapes and painted by the real stylesheet, EXAMPLE badge on top. Items are explained AT THEIR ACTION LOCATION — the mock uses main's REAL grid areas. The live-page design dead-ended whenever a step's subject wasn't on screen (on a fresh install: everything — the tour's own audience).
- **Opening ≠ explaining: click-payoffs OPEN as scenes.** Step `scene:` key; overlays carry `data-tm-overlay="<scene>"`, exactly ONE shown per step. Scenes: `info` (ⓘ details column), `picker` (set chooser), `targets` (editor w/ honest unreachable row), `changes` (before→after diff), `journey` (road + ★ + open stop), `bugreport` (prefilled form). Adding one = mock HTML + `scene:` on the step.
- **Anchors & placement:** step `target` = the REAL app id (audit-verified); mock stand-ins carry `data-for="<id>"`; `anchor: "[data-tm=x]"` narrows the highlight (⚠ never target a full-screen wrapper/backdrop — anchor the BOX); `side:` steers the card into empty space (rail→right, buildcol→left); onHighlightStarted pre-scrolls the subject to the upper quarter (driver centres targets → cards clamp OVER their subject otherwise; per-step `top:` for tall diagram cards); `slim: true` = 300px card for boxed-in subjects; diagrams capped 210px.
- **TOUR GREEN #22c55e** (deliberately outside every theme palette) on the driver outline, the popover border + arrow (10px), and diagram `d-hot` controls — no dark overlay (overlayOpacity 0; the blackout was a "where am I?" moment; the mock's `<details>` are pinned open via preventDefault since clicks land on it).
- **Click rule (FINAL, supersedes advance-on-outside-click): stray clicks do NOTHING.** Advance = Next / space / arrows (`_tourKey`); leave = Exit / ✕ / Esc. `_tourDocClick` swallows outside clicks capture-phase (driver otherwise advances on big targets and CLOSES on small ones); both listeners detach in endTour AND onDestroyed.
- **Save-spot ("always a save favorite, or exit"):** every card footer = "★ Save my spot & exit" + "Exit tour"; `cohTourSpot` {chapter,index}; the 🧭 chooser offers "Resume where you left off"; resume restores step + scene; spot clears on resume/finish; **plain Esc/✕ stores nothing (closing-is-not-a-decision)**. Finished (`cohTourFinished`) is earned only by completing the full tour or spine; offer only on a fresh install (no saves).
- **Deep links:** `explainStep('<key>')` — a ? ON a control jumps to the exact keyed step (first: every power card → the annotated card-anatomy step). Pattern: `key:` on a step + a ? calling explainStep.
- **Coverage:** 56 steps / 7 chapters incl. the summary band (#overview-card/#bonuses-card/#uniques-card/#accolades-card), add-powers-row, #tray-out, #order-out, the per-attack DPA table, and a support-note step (the Brute example stays lean; support/MM growth described honestly, never faked — same honesty as the bar drawing: real bars have NO mid-track cap line, the bar ENDS at its cap).
- **tools/audit_tour.py = 8 checks:** node --check first (hard-exit; missing node FAILS, never silently passes — it once blessed a file that didn't parse), real-id targets, mock data-for coverage, anchor existence, deep-link resolution, chapter checks, themed colours. Negative-control everything.
- **Content sourcing:** docs/help.md + in-app tooltips + rendered code — never guessed (patron-arc unlock rules deliberately NOT claimed). ⚠ Geometry is UNVERIFIABLE from the Claude pane (0×0 viewport, no screenshots) — placement/highlighting need Joel's eyes; JS-level probes (rects, overlap %, computed colors) are the verifiable half. ⚠ Pane-testing: timed-out sweep scripts leave ZOMBIE loops thrashing the page — reload before re-probing, keep sweeps short, shim rAF when the pane is hidden.

## Durable seams & rulings (July arc — each earned the hard way; full stories in git + session-report)

- **⚠⚠ `_stated` is a SEPARATE key from `_declared` ON PURPOSE** (refuse-with-remedy scoping): `solver.py:1016` reads `_declared` for target seniority — writing provenance there would change the objective and move every certified champion's score. preset survival numbers are HARVEST PROXIES, not literal goals; advice fires only for axes the user declared (editor) or stated (goal/exposure).
- **resetToImported: the WIPE stays ("reset means reset", 0.12.20), the SILENCE was the bug** — a confirm names what will be lost; no prompt when there is nothing to lose.
- **server/diag.py**: every broad `except Exception:` swallow prints one stderr line (`diag.swallowed`). Behavior unchanged — the swallows are mostly right. ⚠ Watch on the next certification run: `deep_optimize`'s `save_champion` + exploration-log append were both silent — a failure there discards hours without a word.
- **Security (0.12.28/0.12.29):** ⚠ never re-add `CORS(app)` (the SPA is same-origin; bare CORS let any site READ the loopback API). escHtml escapes the double quote (fixed at the root — attribute XSS via OTHER PLAYERS' names). `/ingame/read` uses realpath BOTH sides (abspath passed symlinks). CSRF guard `_refuse_cross_site_writes` (Origin + Sec-Fetch-Site; non-browser callers pass BY DESIGN; smoke case 7). ⚠ The ~25 remaining CodeQL alerts are TRIAGED false positives — do NOT re-chase (reasoning in d4f439c5). ⚠ codeql.yml is DELIBERATELY scoped (pulse pushes 30×/day) — never simplify to `on: push`. Pillow ships and is NOT removable (pystray/run_lite need it; its advisories are image-parsing bugs, no untrusted images opened).
- **⚠ Page the whole list before saying "nothing else"** — a `per_page=30` query once hid 41 of 71 CodeQL alerts (the serious half). Same class as narrowing Gmail searches.
- **Field-report intake:** Gmail connector = joel717421@gmail.com, ⚠ ONE Google account at a time (disconnect/reconnect only). Forum notification emails carry NO comment text; **Homecoming PM notifications carry the full body**. forums.homecomingservers.com is readable from Joel's machine via the in-app browser (403s automated fetchers) — topic 64761. Web3Forms bug-report key is public-safe (delivers only to Joel's verified inbox).
- **Journey rulings (baked in, do not regress):** Praetoria is NOT startable on Homecoming — the tab is 🌀 Flashback, every note past-tense. Cross-faction access ≠ teaming. ~~The app toggle stays Hero/Villain; the Journey's 5-way is PREVIEW only~~ — **OVERTURNED by Joel 2026-07-31: the app toggle becomes the FOUR-WAY 🦸 Hero / 🛡️ Vigilante / 😈 Rogue / 🦹 Villain, both middles themed the wizard section's yellow, each giving access to both sides' information.** It is **BUILD-NEUTRAL, verified game-first**: Vigilante is hero-type and Rogue villain-type for the accolade `activate_requires` gate, so this changes what a user SEES and nothing about what their build scores. The four alignments already exist journey-local (`_ALIGNMENTS`, `_contentSide()` in app.js) with exactly this model; the work is promoting them app-wide. Greet gates on `isNewCharacterPlan()` (mode new OR new50); import/respec wait for the Leveling Companion catch-up rung; ★ marker deliberately absent on new-50 plans. Road layout: cards below the line, capped + internal scroll, lane padding measured (`_fitJourneyLane`).
- **⛔ i24 ARCHIVE ruling (2026-07-24):** Joel takes the torrent (`magnet:?xt=urn:btih:8ab693089594f577dfed7e0318bacc9c9226acc3&dn=data-v2i1.1.7z`); until it lands, the zones/badges drawers stay as-is and the wiki-bridge stays CLOSED. Zone level ranges / TF gates / coordinates are SERVER-SIDE (client bins searched to the bottom; badges.bin cracked — parser in bin_crawler/parser/_badges.py, 155/155 field-verified). map.bin zone names are DEV-ERA (Baumton=Boomtown) — used only to FIND art, never to name zones. `C:\Games\HC2\assets\issue24` = a second, far larger asset set on disk (zone art + more).
- **Wiki-as-tool:** homecoming.wiki 403s Anthropic's fetcher but returns 200 from Joel's machine with a browser UA — tools/fetch_zone_pages.py (local, 1 req/s, cached) + verify_zone_pages.py; the sanctioned way to pull the one class the client lacks, labelled wiki-sourced.
- **Certification-adjacent (v31-v35 era):** canonical_score is the ONLY portable number (stored run-scores are within-run ranking; never compare fresh evaluation to run score). `_picks_legal` (ladder-fit + 24-pick cap) is the legality gate — the lenient seater never is. The proc-pass target guard runs ONLY on user-DECLARED targets. A1 flat positional asks were built-measured-REVERTED — do not re-add. ⚠ Any deep_optimize probe MUST set HC_CHAMPIONS_PATH to a scratch file (it always saves its result as the context's champion). Certification sweeps run under HC_SOLVER_NODE_CAP=50000 (winner re-solves uncapped). Speed ledger: benchmarks/pyspy_triform_wave.svg (next lever = PuLP model reuse). **Backend re-measured under v38 (2026-07-29, solver_backend_ab_2026-07-29.log): CBC KEEPS the crown — HiGHS ~2.65x slower overall (median 0.59s vs 1.07s), loss CONCENTRATED on the plateau heavies (PB triform 4.8x) which dominate cert wall time; equivalence 24/24 (zero defects); in-process highspy path, so no faster HiGHS route exists. ⚠ NEW plateau datum: equal-optimum tie-break fp spread now ±19.4% under v38 (was 6.5% on 7/14) — the one-objective work order's gap has WIDENED.**
- **My artifacts, his box:** never hand a foreground/long-running server command in a runnable code block (start-dev.bat blocks by design — hand the URL or launch detached). ⚠ No COM shortcut enumeration via PowerShell on this box (Bitdefender reads it as recon). When a fix is too small to be visible, SAY SO before asking him to look.
- **Accolades panel placement:** lives in the SUMMARY BAND (info-course: overview/bonuses/uniques/accolades cards) full-width under the powers wall — the wedged-beside-Stamina layout was ruled bad ("legibility beats cleverness").

## Project history (condensed; transcripts in ~/.claude/projects/, memory files in ~/.claude/projects/C--Users-joelc-code/memory/)

- **2026-06-16→19**: Flask+vanilla-JS prototype from Mids .mhd data → the solver thesis ("it's an equation — 3D chess") → ILP (PuLP/CBC); AI generation removed from the client; costume side-quest killed (parked `_archive_costume/`).
- **2026-06-29→07-02**: import & correctness era (unique flags, in-game .txt + .mbd round-trip, preserve modes, per-AT caps); the COMPANION pivot (entry cards, discovery, 1-50 stepper); role system + first_principles encounter model + deep_optimize + learning stack; model v10→v23; masters corpus as the floor.
- **2026-07-03 LAUNCH**: repo public, HC forum topic 64761 (as Pulsekin), LICENSE/TERMS/CREDITS/help PDF, AI-free client (`HC_AI=1` seam), 0.9.0→0.10.0 (installer/tray/self-update).
- **2026-07-04→08**: Guyver's 4,187 builds → v24; masonry UI; slot-grant schedule; Maelwys rounds 1-2 → game-client bins became the authoritative source; henchmen priced from live game; 0.12.9→0.12.15 ("verified-data release"); regression day fixes behind demo_single_build_fixes.
- **Release ledger since:** 0.12.16 "inheritance" (7/09, v29 henchman set-bonus inheritance + heal-strength) · 0.12.17 "display-only" (7/10, custom targets + booster preview + Power Boost amplifier + IO detail cards) · 0.12.18-0.12.20 (v30-v31, roster split, ladder-fit gate, AFK farm champion "+3x8" honest label) · 0.12.22 "FIRST SIGNED" (7/21, v34 MM pet-buff; release-night walk loop = 4 pinned class fixes incl. the invisible-confirm hang) · 0.12.23 (7/21, v35 endurance physics + full-roster wave + Build-Assistant locks/targets) · 0.12.24 (7/23, Leveling Journey v1 + wizard one-copy + farm gates + v36 meters + opt-in auto-start) · 0.12.25 "THE JOURNEY GROWS UP" (7/23, zone splash art + badge locations/directions + TF levels + challenge checklists + con reads + routes + alignment preview) · 0.12.26 (7/24, Web3Forms in-app bug reports + power icons 4949→6033 via patch/extract pipeline + Journey polish + Play Log dedup) · 0.12.27 (7/26, refuse-with-remedy fixes for legendaryjman + Troo — first release driven entirely by field reports) · 0.12.28 "security" (7/27, escHtml/XSS/realpath/stack-trace fixes) · **0.12.29 "The guided tour" (7/27T22:58Z, af28d2bf: 56-step tour + CSRF guard + corrected help)** · 0.12.30 "Accuracy pass" (7/31, v38 + 24/24 recert) · **0.12.32 "The Stats page becomes a workbench" (8/06T23:02Z, e164fd13: per-IO worth measured by counterfactual + Swap/Remove in place + the universal edit receipt with Undo + the swap picker pricing every candidate via `/build/slot_compare` + the unique-once-per-build picker gate + the green-marks legend + the 390-badge catalogue with `/thumbtack` rows + Flashback landing + honest empty art states + the exploration-log streaming read (89.3s/6.17GB → 29.3s/393MB, byte-identical) + reduced motion reaching the JS scrolls; data 2026.1.1242 and model v38 BOTH unchanged, so no score moves)** · **0.12.31 "The desktop app" (8/05T20:35 ET, b2161e12: WebView2 window/no tray, four tabs, four-way alignment + wordmarks + emblems, exemplar arc, split role + output panel, per-power improvement report, buff/debuff reads slotting incl. recharge, one import door + Mids round-trip pin + special-origin names, portable-update refusal, rebuilt 63-step tour, 94 Alpha icons; docs/index.html disclosure flipped to the window truth in the same pass)**. All signed CN=Joel Andrew Chambers from 0.12.22 on; every release: frozen smoke + gold 24/24 SERVED; data currency 2026.1.1242 / model v38 since 0.12.30.

## Certification protocol rules (learned the hard way — each one has a corpse behind it)

- **🚨 CHECK THE GAME, NOT YOUR PARSE (2026-07-29 — cost a 12-hour wave).** I parsed a client `requires` string, declared ~20 champions "game-illegal", rewrote the legality gate and launched a fleet wave. The game's OWN help text then said: Tough needs "one other Fighting Powers" (ANY one). **My gate change was WRONG and is reverted (00ed2a39).** Rules: a parse of an undocumented field is a HYPOTHESIS — the game's display_help, weeks of working evidence, and Joel outrank it; a finding that invalidates certified work is JOEL'S RULING, never my wave.
- **✅ PREREQ MODEL, CORRECTED PROPERLY (3f55cc37, 2026-07-29).** The game STATES each power's prerequisite count in display_help; our position-based proxy disagreed in BOTH directions. **`server._prereq_need` is now THE authority** (prefers data `prereq_count`, falls back to the tier proxy for the 68 records the game doesn't state). Data: `tools/patch_prereq_counts.py`. **EVIDENCE RULE — patch only where TWO of three signals agree:** (A) the help sentence, (B) whether the requires expression names other POWERS (⚠ NOT "is it non-empty" — most epic expressions are ARCHETYPE gates `$archetype @Class_Scrapper ==`), (C) the corpus-validated tier model. 404/472 patched, **9 HELD and reported** (6 whose help sentence describes a DIFFERENT power — Vengeance's says "before selecting Victory Rush"). Real corrections: travel powers (Fly/Teleport/Super Speed/Invisibility/Mystic Flight/Arcane Bolt/Toxic Dart/Project Will/Long Jump) were OVER-required → we were REFUSING legal builds; Weave/Group Fly/Wall of Force/Invoke Panic/Burnout/Misdirection/Field Medic were UNDER-required (game wants 2). **STANDING CHECK: `tools/reality_check_prereqs.py`** — the game's words vs what the app enforces, every pool/epic power, self-skeptical (flags help text that names another power as TEXT evidence, not RULE evidence). 405/413 agree (was 388).
- **🚦 THE PREREQ REALITY CHECK NOW GATES THE LAUNCHER (78bd351d, 2026-07-30 — Joel: "why are you checking reality of game AFTER the builds?").** The check existed as a manual tool written as the lesson of the burn, and the very next wave launched without it. `converge_parallel` now runs `reality_check_prereqs.py --gate` BEFORE spawning a worker, failing only on disagreements NEW since `tools/prereq_disagreement_baseline.json` (8 accepted: 6 are help sentences naming a DIFFERENT power, 1 Field_Medic parse artifact, 1 unparsable). Override `--skip-reality-check` exists to be said out loud. Proven both directions (passes at 405-agree; an emptied `HC_PREREQ_BASELINE` blocks the launch). **Generalize the pattern: a lesson that lives only in a docstring is a note — wire it into the thing it protects.**
- **⏱ PER-CONTEXT COST, MEASURED CORRECTLY (2026-07-30 — supersedes the 484-min figure).** ⚠ `buildout_champions` prints `total: X min` for the **whole worker queue**, not one context (`t0` is set once before the loop, line ~211) — per-context duration is the gap between consecutive `[Xm]` markers. Measured over 19 completed contexts under the corrected prereq model: **min 12 (Defender/Poison) · median 77 · mean 75 · max 261 (PB triform)**. The old "PB triform = 484 min / no hardware beats that" entry was pre-prereq-fix and must not be re-quoted. Full space = **2,691 combos** (AT × primary × secondary, VEAT cross-branch excluded; Scrapper/Tanker/Brute ~320 each, Kheldians and VEATs 1-3 because their sets are fixed) ⇒ ~3,370 worker-hours ⇒ **28 concurrent workers for a 5-day full sweep, ~70 for 2 days.** Content types multiply that directly, so which contents matter is a bigger lever than any purchase.
- **🐌 SPEED LEDGER (measured, py-spy — restored 2026-07-30, this is the real efficiency lever).** **30-40% of worker time is PuLP model rebuild + MPS file I/O + temp-file churn** → next lever = model reuse / in-process small solves (`benchmarks/pyspy_triform_wave.svg`). Also measured: CBC warm-start ≈1.0× (bound-proving dominates), parallel sweeps 3.2× (shipped), context parallelism near-linear (shipped). **Solver backend is settled and is NOT a lever:** CBC keeps the crown — per-solve HiGHS ~2.65× slower under v38 (median 0.59s vs 1.07s, `solver_backend_ab_2026-07-29.log`, equivalence 24/24), and end-to-end on real certification runs **1.2-1.7× slower** (`bench_solver_e2e.log`: brute_farm 112s vs 190s, defender_support 89 vs 115, mastermind_pets 78 vs 92). ⚠ Quote the END-TO-END number for wall-clock decisions; the per-solve ratio does not transfer. ⚠ `deep_optimize` force-sets `HC_SOLVER_NODE_CAP` but `solver._mip_solver` reads it only on the CBC branch — the HiGHS branch returns first and ignores it, so a naive A/B runs CBC capped and HiGHS uncapped (the e2e harness neutralises this and asserts `capped_floor == 0`). ⚠ `bench_solver_e2e.py` guards itself against running beside a live wave — but on 2026-07-29 the wave died as it started, so treat that guard as unproven and check for live workers by hand.
- **⚠ THE CANONICAL RETRACTION, WITH ITS EVIDENCE (9a7a5f8) — and it was never root-caused.** The finale uncapped re-solve does NOT make stored scores canonical: the r3 worker scored its winner **430.0**; a fresh process reproduces **387.3** (stable, repeatable). In-process state after a ~7,000-solve 30-thread run changes evaluation; **mechanism NOT root-caused** (100-solve single-run churn does not reproduce it; same family as the historical run-vs-canonical gaps). Stored score = within-run ranking only; `canonical_score` from a fresh-process evaluate is the only portable number. `evaluate_first` mirrors `deep_optimize` exactly (archetype= + content-first role — two counterfeit-comparison defects fixed, proven no-op on the 23).
- **⚠ SKIP-CHECK UNION (wave/orchestrator, restored).** `converge_parallel` unions champions.json PLUS every root `champions_shard_*.json` MINUS `champions_held_ladderfix.json` (held = deliberately pulled, must re-converge). Shard-vs-shard collisions still hard-fail. Held-context shards get renamed OUT of the glob.
- **🔬 AURA/PATCH PROC VALUATION — OPEN RULING WITH FIELD DATA (restored; do not lose again).** Field re-derivation from Joel's archived chatlogs (`tools/measure_ig_procs.py`, per-proc/per-host attribution via ToLG+Shield Breaker → Ice Grasp): **measured 10.66% per hit-tick vs the v31 dev-archive AF formula's 6.14% (AF=1: 11.67) — the formula undershoots the field by 42%; effective AF ≈ 1.1.** Also measured and still UNPRICED: IG base damage 7.97/hit/target (the stated v31 exclusion), and real farming double-stacks IG (1.21s effective cadence). The 2026-07-07 note said per-proc 56.7% ±3.2/window and "price from the MEASURED number". Any change here = model bump ⇒ re-converge both farm champions.
- **⚡ EFFICIENCY EVERY WAVE (Joel's standing ask, 2026-07-29).** `tools/wave_cost_report.py` mines worker logs (no instrumentation) for per-context minutes/sweeps/solves/throughput → `benchmarks/wave_cost_history.json`. **Measured truth: the Kheldian slowness is PEACEBRINGER, not Warshade.** ⚠ The absolute minutes below are the PRE-prereq-fix run (2026-07-29) and are SUPERSEDED — see the per-context entry above for the current numbers (PB triform 484 → **261**, median 53 → 77). What survives is the SHAPE, and it is the durable finding: PB triform was 16.7 min/sweep vs a median ~1.5, PB dwarf and even Battle_Axe (not a Kheldian) ranked above every Warshade. **Sweep COUNTS are uniform (24-37) — slow contexts do the same number of iterations at up to 16× the per-sweep cost, so the lever is neighborhood size × solve difficulty, NOT iteration count.** **`split_wave.py` now schedules LPT** (longest-first, dealt to least-predicted-load-relative-to-capacity — ⚠ never SLICE the sorted list, that hands every monster to one machine): balanced 333 vs 335 min/worker on the current roster vs ~2× scheduling loss before. **Predicted makespan floor = the single longest context — no hardware beats that** (currently 261 min, PB triform); shrinking it is the next real lever, and per the speed ledger the lever is PuLP model reuse, not silicon. Run wave_cost_report after every wave to refresh the history.
- **🖥 HARDWARE SIZING (2026-07-30, from the corrected per-context numbers).** The workload is hundreds of thousands of INDEPENDENT single-threaded CBC solves ⇒ throughput scales with core count × sustained clock; no GPU, storage irrelevant. Laptop = i9-13900HX (24C/32T, 8P+16E, 64GB) and it THROTTLES under sustained all-core load; the gaming box = i9-9900K (8C/16T) measured ~2× slower per context. **Whole 24-context wave in one shot needs ~24 concurrent workers** (wall clock then = the single longest context). Full 2,691-combo sweep: **~28 concurrent for 5 days (Threadripper 7970X 32C/64T, ~$4.5k), ~70 for 2 days (7980X 64C/128T, ~$8k)**. ⚠ RAM is the binding constraint and it is a SOFTWARE bug: `learn.marginals()` → `_load_log()` parses the ENTIRE `benchmarks/exploration_log.jsonl` (1.87 GB / ~1.6M rows as of 2026-07-30) into dicts once per `deep_optimize` call (server.py:3670) — ~12s CPU and 1+ GB resident per context, per worker. Under 1% of runtime today, but it sets the RAM spec for wide fan-out and grows every wave. **Fix the parse before buying 256GB.** ⚠ Joel's standing frame: hardware buys VOLUME, never speed on the slow ones — and size any purchase on a measured full-parallel run (rent a box for one night), not on my arithmetic.
- **📡 REMOTE HEARTBEAT SHOWS MOTION (25b7bb8a):** the box's heartbeat reports per-worker current context + sweep/restart + best + minutes-in (`in_flight_summary`), because a banked count alone reads "0 of 8" for 40 minutes and Joel nearly cancelled a healthy order. Lands on the box automatically via the next order's commit pin.
- **⚠ USE THE FLEET (Joel's rebuke, 2026-07-29 3:33 AM — "you made adding a worker pointless").** At every wave launch/resume, partition the UN-STARTED keys across every available healthy worker (laptop + gaming box) — in-flight contexts stay put, queued ones split. The v38+HO wave soloed on the laptop to 3:30 AM while the freshly-validated box idled six hours. A safety concern gets SOLVED (collision-proof split tooling), never used as a reason to idle capacity; idling a worker must be justified out loud, never a silent default. Split tooling gets built BEFORE the next wave.

- **EXPENSIVE RUNS LAUNCH DETACHED, NEVER AS SESSION BACKGROUND TASKS (2026-07-16).** Any convergence wave / champion build-out / roster battery starts as its OWN process that outlives the chat session — a session auth failure once killed two live workers mid-context (~50-55 min compute each; deep_optimize does NOT checkpoint mid-context). **Launch mechanism: Windows scheduled task via `Register-ScheduledTask` cmdlets (schtasks.exe quoting breaks under PS 5.1), action = `wscript.exe launch_hidden.vbs "<bat>"` window style 0** ⚠⚠ **NEVER register a near-future trigger AND call `Start-ScheduledTask` — it DOUBLE-FIRES the launcher** (cost 2026-07-30: the i6r wave launched twice 10s apart; run 2 saw run 1's contexts in flight, re-split the BOX's slice, and spawned 3 local workers on the SAME shard prefix — the collision this file already warns about — plus a duplicate box order. Caught in ~30 min: no shard had been written, zero results lost; killed run 2's orchestrator+workers by PID, deleted the unclaimed duplicate order. ⚠ run 2 also TRUNCATED run 1's p0-p2 logs on open, so a double-fire garbles the very logs you monitor with.) **Use the trigger alone (+10s) OR register far-future and Start manually — never both.** (visible task consoles got killed by a literal ^C twice; Start-Process detachment failed to survive twice). Unregister the task after the processes are confirmed running. Recovery: relaunch detached — converge_parallel skips certified shards — then VERIFY the shard logs are actually advancing (two snapshots) before trusting it. ⚠ Shard-prefix collision: a resumed wave with fewer workers reassigns `_pN` suffixes — copy completed shards to non-colliding names (still `champions_shard_*`) BEFORE relaunching.
- **NEVER MERGE A SHARD WHOLESALE — MERGE BY CONTEXT, AND CHECK THE VERDICT FIRST (2026-07-16).** The printed "merge when ready" hint is a footgun: (a) one shard can hold a shipping context AND a held one; (b) `--replace` supersedes by construction, so a WORSE re-convergence silently replaces a better build. Read the shard's CONTEXTS, merge only cleared ones (split mixed shards), run evaluate-first after, KEEP THE CANONICAL WINNER — a recert earns supersession, it is not entitled to it. Held-context shards get renamed OUT of the glob. Bare `--replace` now HARD-FAILS without --verdicts (structural).
- **SHARD RETIREMENT AT MERGE (2026-07-16).** The moment a shard merges, RENAME it to a non-matching suffix (`.merged_YYYY-MM-DD`) — `certified_union()` globs `champions_shard_*.json` and a stale copy once SHADOWED a live champions.json entry (8 stale shards, 28 shadowing attempts, caught by luck). The certified_union stale-shadow guard is the second lock. **Deliberately-never-merged shards are NOT stale** — the E ground truths (`champions_shard_e_gt_*.json`) stay in the union.
- **VERDICT BEFORE `--write` (2026-07-16).** Read and RECORD the wave's verdict before `evaluate_first --write` runs — `--write` overwrites `canonical_score`, the very values the verdict compares.
- **EVERY NEW PRICING TERM SHIPS WITH A NEGATIVE CONTROL (2026-07-16)** — a real build that must read 0.0, alongside its positive test. The negative control is what proves a term reads ACTUAL slotting rather than firing on a lookalike.
- **"READY FOR YOUR WALK" IS A CLAIM WITH A DEFINITION — AND IT NAMES THE COMMIT HASH (2026-07-16).** ALL of: (a) server restarted from current HEAD after the last server-side edit, (b) a FRESH page load with zero injected state, (c) the exact URL Joel opens, driven through a REAL entry path he would use, (d) the claim states the commit hash. Anything less is "probably ready" and must be said that way. Verification theater = the same defect class as a fake progress bar; the tell: the check never touched the thing the user touches. **Drive the real path** (the Journey-greeting and escHtml lessons).
- **THE MACHINE CLOCK IS LOCAL EASTERN — `Get-Date` IS THE TIME AUTHORITY, NEVER A TZ CONVERSION (2026-07-16; re-bitten 07-27 with a same-evening "7/28" erratum; re-bitten TWICE 07-30 by deriving elapsed time from monitor-tick COUNTS — told Joel "35 min to the pause" when it was 75, then "~20 min" at what was already 4:02).** For anything a deadline, ritual, or timestamp depends on, run `Get-Date` and use it verbatim — and **never STATE a clock time, countdown, or "N minutes until X" without a same-turn `Get-Date`**. Event cadence (monitor ticks, notification arrival) is not a clock; ticks queue, lag, and batch. `date -u` only for UTC-labelled facts; never convert to derive local time.
- **SCRIPTED-WRITE GUARD (2026-07-16) — the catch is mechanical, not vigilant.** (a) Every scripted edit of a repo file writes binary/newline-preserving (`open(p,'rb')`→transform→`'wb'`) and matches the file's existing serialisation (powers.json is COMPACT single-line — never `indent=`). (b) Before committing, compare `git diff --stat` to INTENDED size (cross-check `--ignore-all-space`); >2× intent or whitespace-blind much smaller → STOP and diagnose. (c) Prefer the dedicated edit tooling; **NEVER PowerShell string rewrites on source files** (PS5.1 reads BOM-less UTF-8 as ANSI and mangles unicode).

## Naming: three namespaces, and the trap (settled game-first 2026-07-30)

Joel's order: "understand how we name things and make a clear understanding
between game historical naming conventions and what is displayed to players."
There are THREE namespaces and they routinely disagree:

1. **The game's INTERNAL name** (client bins) — historical, dev-era, and
   **REUSED over time**. It is an identifier, never an identity.
2. **The DISPLAY name** (client `display_name`) — what the player sees.
3. **OUR internal name** (Mids-derived) — sometimes copies #1, sometimes #2.

**The proof case, and why internal names can never be trusted as identity:**
```
client internal "Afterburner"  ->  player sees "Evasive Maneuvers"
client internal "Fly_Boost"    ->  player sees "Afterburner"
```
The record still named `Afterburner` is now shown as Evasive Maneuvers, and a
newer record took over the "Afterburner" label. Same family, all client-verified:
`Pool.Leaping.Leap` = **"Acrobatics"** · `Pool.Leadership.Defense` =
**"Maneuvers"** · `Pool.Teleportation.Long_Range_Teleport` = **"Fold Space"** ·
`Epic.Fire_Mastery_Dominator.Consume` = **"Melt Armor"** (and see the
internal-name-reuse pitfall: 15 such groups).

⚠ **This caused six FALSE alarms** in `reality_check_prereqs.py`: its
"the help sentence names a DIFFERENT power" warning was comparing prose display
names against our internal names. Nothing was misattributed — "before selecting
Acrobatics" IS the sentence for `Leaping.Leap`. When a check compares names
across two namespaces, it must say which namespace each side is in.

- **Set-name divergence is systematic, three ways at once:** word order
  (ours `Dark_Mastery_Blaster` / client `Blaster_Dark_Mastery`), abbreviation
  (ours `Corr`/`Elec`/`Lev`/`Psi`/`ScrapStalk`/`TankBrute` / client
  `Corruptor`/`Electricity`/`Leviathan`/`Psionic`/`Scrapper`/`Tank`), and a
  different theme word (ours `Flame_Mastery` / client `Fire_Mastery`).
  **12 pairs PROVEN** and recorded in `tools/epic_set_name_bridge.json` — proven
  by TWO signals: identical power leaf rosters AND an agreeing archetype token.
  ⚠ Content alone is NOT sufficient: `Corr_Flame_Mastery` and
  `Def_Flame_Mastery` have byte-identical rosters, so content matching alone
  mapped both onto Corruptor's copy. The archetype token is what separates them.
- **✅ The "7 remaining differences" DISPOSED game-first (2026-07-30, work order
  §1.6).** Five were NAMING, not data — settled mechanically by the resolver's
  display-identity rung (`patch_prereq_counts.resolve`: exact name → set bridge
  → UNIQUE display-name match inside archetype-constrained sets; our names are
  Mids/display-derived, the client's are historical): our Sentinel `Chum_Spray`
  displays "Arctic Breath" and IS client `Arctic_Breath`; `Havoc_Punch` = client
  `Havok_Punch`; `Umbral_Torrent` = client `Torrent`; DefCorr `Build_Up` =
  client `Ice_Slick` (displays "Build Up"); "missing" `Gather_Shadows`+`Torrent`
  = our `Midnight_Grasp`+`Umbral_Torrent`. The two REAL data items:
  **`Epic.Scrapper_Mace_Mastery` REMOVED** (e4d63760 — client doesn't have it;
  game gives Mace to Stalkers); **`Pool.Flight.Fly_Boost` ("Afterburner") stays
  absent ON PURPOSE** — client says `auto_issue=True`, never pickable
  (`available_level` 0xFFFFFFFF), accepts zero enhancements; it is a free rider
  on Fly, not a pick. Do not "add" it to pickable data.

## Game facts pinned from the client (game-first evidence — restored 2026-07-30)

These were proven against the client bins and then buried in dated state blocks.
They are the evidence behind shipped model terms; do not re-derive or re-litigate
them from a parse without the same standard of proof.

- **Henchmen inherit 50% of ALL true set bonuses (verified in bins, 2026-07-08).** `SetBonusPetShareHP[50]` = 40.159 (= MM 803.17 × 10% × 0.5, caster-table, flat to every tier — henchman classes lack the table) plus a generic `SetBonusPetShare` = 0.5 for def/res/dmg/regen/rec/heal-strength/mez-duration. **Henchmen-tagged effect groups live ONLY on `Set_Bonus.Set_Bonus.*`** — Global_Bonus uniques (e.g. Unbreakable Guard) and accolades share NOTHING. Tier HP from `villain_classes.bin`: 578.3 / 771.0 / 963.8.
- **Content-layer bins are EXHAUSTED and these hypotheses are DISPROVEN by name** (do not re-search): `pc_def_contacts.bin` = faction contact-name lists only, no TF gates · `mapstats`/`mapspecs` = mission spawn/layout catalogs · `map.bin` = minimap image bounds (its zone names are the dev-era Rosetta Stone — Baumton=Boomtown, Overbrook=Faultline — used only to FIND art, never to name a zone) · `minimap.bin` = geometry, string table has ZERO badge markers · `clientmessages` gate strings = `{level}` templates, values server-supplied · `villaingroups.bin` = 225 mob-group names, no zone link. **Zone level ranges, TF/SF rosters and gates, per-zone spawns, and exploration coordinates are ALL server-side in Homecoming.** Only unopened door: `geobin_cz*.pigg` zone scene graphs (different format, days not hours).
- **ALIGNMENT & ACCOLADES — verified game-first 2026-07-31 (badges.bin export +
  accolade power records).** (a) **Each accolade badge is ONE badge whose NAME
  changes by side**, not two badges: id 160 `AtlasSet` = 'Received the Atlas
  Medallion' (hero) / 'Atlas Shrugged' (villain); 532 `Marshal` = 'Ex-Marshal' /
  'Marshal'; 161 `FreedomPhalanxSet` = 'Freedom Phalanx Reserve Member' /
  'Freedom Phalanx Fallen'; 535 = 'Gotten Soft' / 'High Pain Threshold'; 551 =
  'Return Visitor' / 'Invader'; 608 = 'Task Force Commander' / 'Task Force
  Abandoner'. The game ships a villain-facing name for every hero badge, so
  cross-faction earning is anticipated BY DESIGN. (b) **You can EARN and HOLD
  both sides' accolades, but only your CURRENT side's APPLY — the game gates
  them at runtime.** Every side-tagged accolade power carries
  `activate_requires` = `type char> hero eq` or `type char> villain eq`, so an
  off-alignment accolade is DORMANT, not additive. The pool does NOT double.
  Same-side accolades DO stack with each other (they are distinct powers, no
  dedup). engine.py:602-620 already implements exactly this and records a
  ledger entry (`inactive_alignment`) so the panel can say why a held accolade
  contributes nothing. ⚠ I first reported 'both stack, pool roughly doubles'
  from `requires`/`num_allowed`/no-mutex alone — WRONG, because the gate lives
  in `activate_requires`, a DIFFERENT field. Check activate_requires for any
  'does this actually apply' question. Consequence for a 4-way alignment:
  Vigilante is hero-type and Rogue is villain-type for this gate, so adding
  them is BUILD-NEUTRAL as long as they map to hero/villain the way
  `_contentSide()` already does.
  (c) **IOs are alignment-NEUTRAL** — zero alignment/side field in any
  enhancement dataset (sets, common IOs, bonuses, categories, details).
  (d) ⚠⚠ **SEARCH BADGES BY THEIR HERO-SIDE NAME AND BY TEMPLATE** — badge
  displays carry gender templates: Iron Man is stored as id 10 `Adamant` with
  villain display `Iron{Hero.gender=male man|woman}`. A substring search for
  'iron man' returns ZERO and I wrongly reported 'no such badge exists in
  2,396 records' on the strength of it.
- **🧭 THE MAP MARKER IS `/thumbtack <x> <y> <z>` — pinned from the CLIENT'S OWN
  COMMAND TABLE (2026-08-06).** `cityofheroes.exe` registers `thumbtack` with the
  help string *"Set the thumbtack location on the minimap. <x> <y> <z>"*. ⚠ The
  const pool interleaves names and help strings, so ADJACENCY ALONE PROVES
  NOTHING — this pairing stands because **the help text names the command
  itself**, and its two neighbours (`batch_create_map_images`,
  `show_all_minimaps`) match their own help the same way. The map's right-click
  `CMSetWayPoint` / "Set as Waypoint" is the same idea via the UI. ⚠ Do NOT
  claim what `/loc` does from that dump: the strings around it (`whereami`,
  `loc`, `getpos`) pair ambiguously and none of them names itself. n15g's badge
  coordinates are `[x, y, z]` in the game's own order, so they paste through
  unchanged. **STILL UNCONFIRMED IN GAME:** nobody has pasted one and watched the
  X land — Joel's eyes settle it.
- **✅ RESOLVED GAME-FIRST (2026-08-03): a FIFTH power pool is impossible, and
  pools can NEVER disable the Epic — they are separate counters with separate
  schedules.** Settled from Homecoming's own shipped `schedules.bin` (bin.pigg,
  488 bytes, decoded): `PoolPowerSet = [4, 6, 8, 10]` — exactly 4 entries, so
  `CountForLevel` can never return 5; `EpicPowerSet = [35]` — its own 1-entry
  schedule. Engine code (leaked CoH source, `Common/entity/character_level.c` +
  `power_system.c`, github odasm/coh-server-original — Common/ is SHARED
  client+server): `character_CanBuyPoolPowerSet` and `character_CanBuyEpicPowerSet`
  count independently; neither gate reads the other. Decode self-verified
  against three known facts (24-pick Power ladder ending L49, 67 AssignableBoost
  slots, epic at 35). Our `pool_rules` max-4/epic-separate stands; NO UI change.
  Joel's field memory (picked a 5th pool, Epic vanished, GM involved) is real
  but the mechanism must have been something else — the client DOES ship a
  `NoEpicPoolTooltip: "Ancillary/Patron Powers Disabled"` state (Kheldians/VEATs
  have no epic category; live-era villains needed a patron ARC to unlock patron
  pools). ⚠ Method note: the schedule caps are DATA, so any future Homecoming
  patch could add a 5th entry — the PATCH-WATCH re-export would catch it; check
  schedules.bin on the next re-export.
- **❓ OPEN (since 2026-07-16, re-confirmed 07-31): does the Adamant / Iron Man
  badge actually GRANT its accolade power (+10% Max HP, +10 Max End) on
  Homecoming?** The BADGE is real and game-corroborated (clientmessages-en.bin;
  Born in Battle's requirement string lists it). What is unverified is the
  POWER GRANT — +10/+10 would outsize every documented accolade, and the wiki's
  badge page documents no grant. **Joel's in-game check settles it: a character
  holding the badge either shows the HP/End bump or does not.** Until then the
  record STAYS (dropping it would lose a real badge); `unobtainable: false`.
  ⚠ Super_Patriot is the opposite case and is ALREADY handled: wiki says the
  badge 'is not defined at this time', the game badge table has no record, and
  our data carries `unobtainable: true` which the UI renders honestly. Do not
  'clean up' either record without reading data/accolade_attainment.json first.
- **Duplicate-piece legality / rule-of-five:** the picker blocks duplicates, validation ERRORS on them, tiers count DISTINCT pieces, and `_piece_globals` caps at five — **6×LotG = 37.5%, not 45%**.
- **Mids `IoLevel` is 0-BASED** → +1 on import; `RelativeLevel` → `slot.boost`; engine applies ×(1+0.05·boost); the 53 Hamidon Origins = ×1.15. Old imported saves carry the 0-based value (re-import heals them).
- **Power Boost amplifiers are their own exclusivity group** — one amplifier plus one burst together is BLESSED, not a conflict. (Separate from the still-queued gap that Power Boost's +66% amplifier effects are invisible to the parser allowlist.)
- **Epic eligibility leaks are a pinned subtraction** in `parse_mids._EPIC_NOT` (Stalker×Sentinel_Fire, Dominator×Dark_TankBrute + Sentinel_Psi), removed game-first. ⚠ Related trap: the Dominator "Melt Armor" mislabel was a FALSE ALARM — the client's own Consume record IS Melt Armor, values match 1:1 (see the internal-name-reuse pitfall).

## Architecture map

- `server/server.py` — routes, autopick, tray layout, slot plans, explain_intent, endurance relief, release of everything. `server/solver.py` — ILP (options per power, coverage objective `priority×kind_mult÷target`, damage reward w/ 6th-slot credit, exact added-slot budget, value-aware trim, globals pass, common fills). `server/engine.py` — totals/ED/validate/offense/`_scaled_boosts` (PIECE_REF_LEVEL scaling; HOs deliberately have NO ref level). `server/first_principles.py` — encounter model (MODEL_VERSION). `server/proc_pass.py` — post-ILP proc bombs/ST hybrids/−res anchors/FF (all guarded by `_last_swap_safe`). `server/ai_build.py` — presets, goal interpretation, incarnates. `server/mids_import|mids_export|ingame_import.py`, `server/converter.py` (cheap→purple impossible), `server/role_output.py`, `server/gamelog.py` (Play Log), `server/diag.py` (swallow instrumentation).
- `static/app.js` (SPA) + `index.html` + `style.css` + `tour.js` (guided tour + mock) + `vendor/driver.js.iife.js`. `data/*.json` from tools/parse_mids.py + game-bin extractions. `benchmarks/` (masters corpus, champions.json keyed `Class|primary|secondary|content`, full_sweep). `tools/` — audits (epic tiers, slot legality, slot schedule, slotting coherence, tour, tabs, links — audit_links.py = the design once-over: local refs/routes/onclick/tab targets/external hosts, run after UI surgery), reality checks, demo_single_build_fixes, smoke_gold/smoke_release, refresh_champions, converge_parallel/evaluate_first/merge_champion_shards/recert_verdicts, build_help_pdf, parse_mids, sign_artifacts, gamedata extractors.
- AI seam: `AI_ENABLED = os.environ.get("HC_AI") == "1"` — client ships AI-free; the hub opts in.

## Recurring pitfalls & tooling quirks

- ⚠ **Internal-name reuse across per-AT epic variants is a systemic game convention, not corruption** (15 groups found: Fire_Blast→"Rain of Fire", Consume→"Melt Armor"…). **Never classify or flag a power off its internal name.** One spot-check unconfirmed: Field_Mastery.Personal_Force_Field→"Temp Invulnerability".
- ⚠ **The game has at least TWO distinct Auto-power shapes** (periodic-tick vs constant-effect) — power_type is the authority, never fingerprint "Auto-ness" from one shape. `Inherent.` prefix means auto-granted, NOT "has no off-switch".
- **powers.json additive-patcher family** (never re-parse — it erases client-synced layers): patch_suppression_flags, patch_accuracy_bonuses, patch_heal_strength, patch_effect_durations, patch_interrupt_times, patch_power_icons. Pattern: signature-sequence matching, coverage denominator, hard-fail, verify byte-identical after stripping added keys.
- **Power icons**: tools/extract_power_icons.py (pigg texture→PNG) + tools/patch_power_icons.py (additive map from the game's own icon field). Run order: extract → patch. Residual 38 gaps = 18 inherents (different convention), 3 incarnates (`_incarnate_icon`), 17 the game gives no icon.
- **⚠⚠ CLIENT ART IS SPLIT ACROSS TWO ASSET SETS WITH DIFFERENT FILE NAMING (2026-07-31, nearly cost a false "the game doesn't have it").** `C:\Games\HC2\assets\live` names its texture archives **`texture_*.pigg`**; `C:\Games\HC2\assets\issue24` names them **`tex*.pigg` / `stage*.pigg`**. **A glob for `texture_*.pigg` matches ZERO files in the i24 set.** Consequence: the live piggs hold only what Homecoming ADDED (e.g. archetype icons for Sentinel + Guardian only), while all the ORIGINAL-game art lives in i24 (the 14 classic archetype emblems are in `stage1b.pigg`). A live-only sweep finds 2 icons and looks like proof the classic emblems don't exist. **Always glob `*.pigg` across BOTH dirs.** Same class as the badge search that returned zero: the search was wrong, not the game.
- **✅ FIXED (7a67c48c, 2026-08-06): the `extract_power_icons.py` i24 glob defect** — it globbed `texture_*.pigg`, so the documented i24 fallback never once ran. Now globs `*.pigg` (the ICON_PREFIX filter does the real selection). The glob alone closed NOTHING — the payoff needed a second finding: **`e_icon_gen_*` icon names live under `GUI/Icons/Enhancements`** (i24 stage2.pigg), a second prefix the tool never searched. Result: 23 textures extracted, **94 Incarnate Alpha boost sub-powers** mapped to the game's own generic enhancement art, coverage 6033→6122. Residual TRUE gaps = 7 textures absent from BOTH asset sets (e3brawling, illusions_decoy, oilslick ×2, entangledaura ×2, preemptive interface) — reported, not faked.
- **GUI emblems**: `tools/extract_gui_emblems.py` (2026-07-31) pulls the 16 archetype emblems (complete roster) → `static/icons/at/` and the 5 origin title plates (512×128) → `static/icons/origin/`, same texture→DDS→RGBA→PNG path as the power icons. **Archetype↔file mapping is MECHANICAL** — strip `Class_`, lowercase; the game's villain-side `v_` prefix is normalised away at extraction. 15 of 15 app archetypes resolve. Origin plates are extracted but **not yet placed in the UI**.
- **parse_mids Enhancement-relabel allowlist** (`RechargeTime, Recovery, Regeneration, ToHit, Accuracy` + heal-strength fix) silently DROPS other Enhancement(X) self-effects — caused the accuracy (v28) and heal-strength (v29) bugs; Power Boost's +66% amplifier effects invisible today (queued).
- solver/champions: `/build/solve` preserve defaults TRUE for imported builds (proc pass skipped unless `_generated`); champions.json read per-request; the ILP's slot budget counts pieces (67 + one base per power). The app's real solve payload includes `slots`, `earned_slot_count`, `exposure`, `tier` — test through that path, not a bare minimal POST.
- PowerShell 5.1: embedded quotes break native args — use `-F`/`--notes-file` message files for git/gh; run gh and git steps separately.
- ⚠ **Bitdefender ATD on release nights (root confirmed 2026-07-20):** flags the chain UNSIGNED claude.exe→powershell doing taskkill/relaunch — the app is collateral, the SHIPPED release is clean. Exception = Joel's call, never add it for him. Expect the kill, verify 5000 after publishing, relaunch once; dies again = active block. Runbook FP submission per release stays routine. Also heuristic-sensitive to one-liners with tokens and .bat shortcut creation.
- Preview gotchas: wizard `init()` startFromScratch wipes eval-staged builds; frontend caches hard (see Dev preview: F5-on-root refreshes statics).
- Joel's gaming machine is a SEPARATE box (Windows user "Joel Chambers"); shares via OneDrive → `C:\Users\joelc\OneDrive\Desktop\temp` (one-time imports only). Raw game logs archive: `C:\Users\joelc\code\game_logs`.
- Python: `C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe`. gh CLI: `C:\Program Files\GitHub CLI\gh.exe`. Node: on PATH (v26), required by audit_tour.
- ⚠ NO agent fan-outs / deep-research without Joel's explicit opt-in AND stated cost. "Research" = existing knowledge + local data + a few direct fetches in the main loop.
- ⚠ **Never cd-chain commands; run git through a wrapper** (restored — bit me twice on 2026-07-30 when a `cd`-chained shell lost its working directory mid-session). Permission thrash is already resolved by the curated allowlist + dontAsk in `C:\Users\joelc\code\.claude\` — keep using it rather than re-prompting.
- **Full re-slot is idempotent:** `preserve=False` ignores inbound `_existing_slots`/`_earned` entirely; a sub-50 import solved at the 50 plan gets the server-side `level_plan` warning. `tools/audit_slot_conservation.py` (3 arms × 3 presses) is battery-standing. ⚠ Slot inflation itself NEVER reproduced — the real defects were silence and non-idempotence.
- **AoE/suppression display honesty:** `/build/calculate` attaches per-defense-row `in_combat` values whenever the out-of-combat view differs by >0.05 (suppressible Hide-class defense); `barRow` prints "⚔ N%" inline. **No default flips** — the honest number rides alongside, it never replaces.
- ⚠ **Never mutate a resumed/saved build to test live-update behavior** — autoSaveTick persists (~2 min, sometimes immediately) to gitignored saves/. Test destructive edits on a scratch build.
- ⚠ While a champion refresh runs, **benchmarks/champions.json belongs to the refresh process** — no `git add -A`, no checkout. Commit once, complete, after validate_champions.

## ✅ CLOSED: the engine-accuracy work order (`engine-accuracy-work-order.md`)

Joel's 2026-07-30 freeze ("NO champion work until the engine is proven accurate")
is **LIFTED — items 1-6 all complete, 24/24 recertified and merged 2026-07-31,
shipped as v0.12.30.** The work order stays on disk as the record of what was
fixed; it is no longer a gate. Champion work and waves are open again.

## 🖥 DESKTOP APP (Joel's ruling 2026-08-02, built same day)

Hero Companion stops being a browser app: **pywebview → WebView2** (the runtime
already ships with Win10/11, so users install nothing), **no tray at all —
window close = quit**, update check **automatic on launch**, the autostart
toggle **in the app UI**, and a **one-time share prompt** for the Pulse feed.
**Companion Lite is UNCHANGED and keeps its tray** — do not touch `run_lite.py`.

- **The window is the DEFAULT and the tray is DELETED** (`_run_tray`, the
  first-run notice, the autostart MessageBox, `app_state.json`, pystray in the
  spec, `tools/test_tray_first_run_notice.py`). `HC_WINDOW=0` falls back to a
  browser tab and is the only escape hatch.
- **⚠ JUDGE THE APP FROM THE FROZEN EXE, NEVER FROM A SOURCE RUN.** Joel's
  verdict on the first prototype — *"obviously a python executable, its not a
  self contained application like Mids Reborn"* — was aimed at scaffolding I
  handed him (a .bat, a console, python.exe). Handing a source run as the
  artifact is the mistake; `dist\HeroCompanion\HeroCompanion.exe` is the app.
- **⚠ pywebview's defaults are a BROWSER's defaults, and three of them are
  wrong for an app.** `SHOW_DEFAULT_MENUS` = WebView2's right-click
  Back/Reload/Save-as/View-source menu (the loudest "this is a browser" tell);
  `background_color` = white, which flashes on a dark app; and worst,
  **`private_mode` defaults to TRUE, which throws localStorage away every
  launch** — alignment theme, update switch, tour spot and finished flag, all
  silently forgotten. All three fixed in `_run_window`; keep them named there
  so a pywebview upgrade flipping one is a visible diff.
- **⚠ The window icon MUST be a `.ico`.** A `.png` throws inside
  `System.Drawing.Icon` on a .NET thread, OUTSIDE the try/except, and the app
  dies with no window and no fallback message.
- **⚠ The self-update path outlives the tray.** `_run_window` sets
  `server.SHUTDOWN_HOOK` exactly as the tray did, so `POST /app/shutdown` and
  `_graceful_self_exit_for_update` still retire the copy. Window mode exits
  immediately — the tray's "let the message loop delete the icon" delay existed
  only to prevent a ghost icon, and there is no icon now.
- **⚠ ABSENT ≠ NO in the feed consent.** `feed_disabled` absent (never asked)
  and `feed_disabled=True` (explicit no) both read `opted_in_here: False`, so
  the old status could not tell them apart and would have re-asked forever.
  `pulse_feed.feed_status()` now also returns **`asked_here`** (`"feed_disabled"
  in st`) and the prompt fires on `not asked_here`. ✕ stores nothing.
- **⚠ The launch prompt fires from `hideEntry()`, never at page load** — the
  entry overlay is up at load on every launch, and two stacked overlays is the
  bug that shape invites.
- **⚠ The dev copy and the installed app SHARE the gamelog state** in
  `%APPDATA%\HeroCompanion\gamelog`, and this source checkout HAS an inbox key
  (`key_present: true`). Answering the share prompt in a dev copy writes Joel's
  REAL feed preference — render it and close it when testing, never click an
  answer.
- **⚠ The forum reply's "the update check only runs when you click it" is now
  FALSE in the code** and the post is uncorrected. See RESUME-HERE for the
  accurate replacement sentence.
- **⚠ PORTABLE IS NOT INSTALLED, and `sys.frozen` cannot tell them apart** (field
  report BasiliskXVIII, topic 64761, 2026-08-05): the portable zip and the
  installed folder hold the SAME frozen build, so `/update/install` gated on
  `sys.frozen` alone downloaded the Setup exe and ran it `/SILENT` — silently
  converting a portable user into an installed one. The tell is Inno's
  **`unins000.exe` beside the exe**, which the zip has never carried;
  `server._install_kind()` → installed / portable / source, and an unreadable
  directory reads **portable** so the failure mode is a refusal, never a
  conversion. The refusal sits UPSTREAM of the Popen. **✅ SETTLED 2026-08-05
  (Joel: "I am following your lead"): the refusal + the download page is the
  WHOLE behaviour.** No "install the app version instead" button — a control
  that changes how the app lives on your machine does not belong one click from
  a routine update prompt, and the download page already offers the installer to
  anyone who wants it. No zip self-update either: portable users chose portable,
  and unzipping over the folder is the honest instruction. Do not re-open either
  without a field report asking for it.
- **⚠ "ON" MUST BE A DOOR THAT SWINGS BOTH WAYS, on the surface that owns it.**
  The Play Log's off state offered "Turn it on"; the on state offered nothing
  back, and the answer to "does this run when I'm not using the app?" lived in
  the About dialog under a version number. Both now sit on the Logging tab
  (`gamelogChoiceRow()`), wired to the SAME `playlogConsent`/`setAutostart` —
  never a second copy of a choice. ⚠ `setAutostart` re-renders whichever
  surface was clicked; an unconditional `showAbout()` stacks the About modal on
  top of the Logging tab.
- **⚠⚠ THE LEVELING GUIDE'S SIDE PICKER IS A PREVIEW, AND THAT PROMISE HAD A
  HOLE (Joel, 2026-08-05: "this is a preview of other content, not a
  semi-permanent change to that alignment once we leave this tab").** `_JNY_ALIGN`
  was cleared only in `closeJourneyView()` — which **the tab strip never calls**
  (it is the wizard's list-view path and calls `activateTab` itself), so leaving
  by tab kept the previewed side on return. The reset now lives in
  **`activateTab`** (`if (key !== "leveling") _JNY_ALIGN = null`), the one route
  every exit takes; `closeJourneyView` keeps NO second copy and the battery
  negative-controls that. The preview never writes `cohAlignment` /
  `applyAlignment` / `build` — also pinned, since that is the half that matters.
  ⚠ Generalize: when a promise is "X resets when you leave", find EVERY way out
  before believing the one function named "close".
  **⚠⚠ AND THE OTHER DIRECTION (Joel, same day): "if someone toggles themselves
  in the View menu as another alignment, that STICKS even if they go preview
  other content."** That was backwards too — `_journeyAlign()` reads
  `_JNY_ALIGN || cohAlignment`, and `applyAlignment` wrote cohAlignment without
  clearing the preview, so choosing Villain mid-preview flipped the theme and
  left the road on Rogue. `applyAlignment` now clears `_JNY_ALIGN` and repaints
  the road if it is on screen; the battery pins the ORDER so the clear cannot
  drift above the write. **Precedence rule: the real choice always outranks a
  preview, and a preview never survives a real choice.**
  ⚠ The Flashback context line needs `.keep-whole` — `collapseLongExplanations`
  fires on RE-renders, so it read fine until the View menu repainted the road.
  ⚠ The menu now sits directly under the title (Joel moved it there for
  visibility), so this is easier to trip than it was.
- **📐 SMALL DISPLAYS: BOTH TWO-COLUMN REGIONS COLLAPSE BELOW 1400px (Joel,
  2026-08-05).** "Two columns ALWAYS" was tuned at 1920, where the columns are
  close in height; narrow the window and the main column keeps every tall thing
  while the side column's tiles do not grow, so the difference balloons into a
  structural void a packer could never move. `@media (max-width: 1400px)` sets
  BOTH `.powers-layout` and `.stats-provlayout` to one column (fixing only the
  first just moves the complaint to Stats — universal rules, no hacks), and the
  grout rule retires with the second column. Measured at his 1250: the wall goes
  2 cards across → 4, the catalogue 2 powerset columns → 4. ⚠ Trade, stated: the
  page is taller and the WINDOW scrolls — allowed; the banned thing is a
  scrollbar INSIDE a panel.
- **🧬 THE INHERENT IS A STAT, NOT A PANEL (Joel, 2026-08-05).** The Powers-tab
  card is DELETED; `inherent_mechanics` renders as the **Archetype bonus** group
  at the top of Stats, above Defence, in the ordinary stat-row shape. The value
  column is the honest word — **COUNTED / SHOWN ONLY / NOT MODELED** — so the row
  answers "is this in my numbers?" without a card explaining itself. ⚠ "Counted"
  means counted in the SCORE (`first_principles`), not in the displayed DPS;
  **applying a meter to displayed damage is still Joel's ruling** because
  Vigilance is team-size dependent and a headline stat has no scenario.
- **⚠⚠ A WARNING MUST CARRY ITS OWN FIX, AND THE FIX MUST NOT CRASH.** Joel's
  level-50 character showed "not available at level 1 yet" because
  `startFromScratch` stamps `level_reached: 1` and nothing ever moves it; the
  only level input lived on the Leveling Guide, a tab away from the banner on
  Stats. The banner carries the input now (same `setCurrentLevel`, one writer).
  ⚠⚠ **And the fix crashed**: `renderLevelStep()` paints into `#wiz-plan-out`,
  which lives in the respec wizard — closed on every other tab, so the write was
  `null.innerHTML`. `setCurrentLevel` runs
  `level → renderEndgameWarnings → renderLevelStep → autoSaveTick`, so the throw
  killed it BEFORE the save: the warning cleared on screen while the typed value
  was discarded. **A crash between a UI update and its persistence is the worst
  shape — it looks done and isn't.** Guard the ELEMENT, not just the data.
- **🔍 audit_tour NOW CHECKS CONTENT, NOT JUST STRUCTURE (2026-08-05).** It was
  ALL GREEN while the tour taught a deleted "Refine with AI" item, an exemplar
  control that "takes you to the dial", and a Help menu with no Settings. Every
  check asked "does this step POINT at something real?" and none asked "does it
  DESCRIBE something real?". Two rules now: retired UI must not be named in any
  step body (`_RETIRED` list — **add a line the day you delete a feature**), and
  every menu item the tour quotes must still exist in index.html. ⚠ The mock must
  also MOVE when a surface moves (the side preview went to the top of the
  Leveling Guide and the mock still drew it at the bottom) — the tour's own rule
  is that things are explained at their action location.
- **🏷 THE LEVELING SURFACE IS "LEVELING GUIDE" EVERYWHERE IT IS LABELLED
  (Joel, 2026-08-05 — the tab said Leveling Guide, the panel it opened said "The
  Leveling Journey").** Renamed: panel heading, the greeting, the intro fold, the
  wizard button, the tour mock + chapter title, help.md. Pinned by
  test_desktop_app so it cannot drift back.
  **⚠ RENAMES ARE FOR LABELS, NOT PROSE (his ruling when I asked): "leave
  sentences alone, this is more for labeling areas of the tool, not sentence
  usage."** So server.py's level-1 note "This is a JOURNEY, not a race to 50"
  STAYS — the word is doing work there. Generalize it: a naming order means the
  names of areas/controls/tabs, never a sweep of every occurrence of the word.
  ⚠ Internal names stay `journey-*` / `.jny-*` / `/journey/...` — identifier, not
  identity (three-namespaces rule); renaming them is churn that can break a route
  or selector for no user-visible gain.
- **⚠ ONE IMPORT DOOR, and it TEACHES (Joel, 2026-08-05: "two options that do
  the same thing, and neither do a good job explaining how to do it").**
  `import-btn` opened a bare OS file dialog with zero instructions; `entry-ingame`
  opened the panel; both ended in the same `importBuildText()`. Now one menu item
  → `showEntry("ingame")` → a panel with a labelled ROUTE per file kind
  (`/build_save_file` for a played character, "Mids saves builds as a .mbd" for a
  planned one), picker inside. The picker is never the front door: it answers
  "where do I click" and never "how do I get a file". `entry-ingame`'s CSS and
  tour step were DELETED, not left dressing nothing.
- **✅ THE MIDS ROUND TRIP IS PINNED, AND IT IS SOUND (2026-08-05, Joel: "test
  mids reborn export and import work flawlessly").** `test_mbd_alignment.py`
  4→9 checks: every power returns, all 93 slots keep their exact piece in order,
  engine totals do not move (def/res/45 set bonuses identical), and
  export→import→export **converges at hop 2**. Hop 1 normalising is CORRECT, not
  drift — an HO's "+3" becomes "a level-53 HO", the game's own convention
  (`mids_import._SPECIAL_PREFIXES`; HOs have no ref level, so level carries what
  boost would). Fixture boosts every slot across 0..5 so an off-by-one in the
  0-based `IoLevel` conversion cannot hide.
- **⚠ SPECIAL ORIGINS LIVE IN `common_ios.json`, NOT `ENH_SETS` — so they were
  missing from `PIECE_BY_UID`** and both importers fell through to the generic
  common-IO fallback, which labels a slot with its own uid: a re-imported .mbd
  read "Hamidon_Damage_Accuracy" instead of "Nucleolus Exposure", set line blank.
  All 62 are registered at the `PIECE_BY_UID` build (server.py, right after the
  ENH_SETS loop) because that is where BOTH importers **and** the ⓘ image lookup
  read — fixing the .mbd path fixed the in-game .txt path for free. ⚠ Their
  `set_name` must never be None: `test_exemplar_view`/`test_stat_attribution`
  call `.lower()` on it while sweeping the map. Math was never affected (engine
  prices by `piece_uid`; identical totals are the proof).
- **⚠ Companion Lite is NOT a watered-down Hero Companion (Joel, 2026-08-05).**
  It is a LOGGER whose whole job is feeding the Pulse Boards — it plans no
  builds and optimizes nothing. "Lite" describes what it carries, not what it
  lacks; never write "little brother" or imply a lesser version of the same
  tool. Icons: **Lite = light blue P, the full app = green P.** Its
  start-with-Windows is opt-in, asked once, and flips from the same right-click
  menu as Quit (all already true in `run_lite.py`; the pages just never said
  so).
- **📉 THE IMPROVEMENT REPORT NOW ANSWERS PER POWER (2026-08-06, `10a7ed0b`) —
  and the exclusion is the durable half.** Attacks diff by **Cycled DPS** (the
  same number the ⓘ card prints, so the two can never disagree) plus a per-hit
  row; **pets are credited to their summoning power** (`offense.pets[].from_power`),
  which is Joel's henchman case. ⚠ **Buffs/debuffs are NOT diffed per power even
  though `_debuff_buff_summary` records the provenance** — its magnitudes come
  from `_resolve_mag` (base scale × modifier table, **no slot boosts**), so no
  re-solve can ever move them. ⚠ **OPEN, and it bites the invisible-role
  doctrine:** the whole buff/debuff panel is unenhanced, so a debuffer slotting
  accurate defence-debuff or −regen sets sees zero movement anywhere in the app.
  Engine work, unstarted, needs Joel's ruling.
- **🧪 THE BUFF/DEBUFF PANEL READS ENHANCEMENT (Joel's ruling, 2026-08-06,
  `be8641db`) — and the RULE needs no table.** Effect names and enhancement-aspect
  names come from the SAME client vocabulary, so an effect is enhanced by the host
  power's own post-ED enhancement in the aspect of that name; whether the power may
  hold that enhancement at all is already answered by its own slots (the game only
  lets it accept what it accepts). **Four exclusions, and the client's
  accepted-category vocabulary is the evidence:** across 3,650 powersets there is
  no resistance-debuff, no −regeneration and no −damage category, because those
  enhancements do not exist. **RechargeTime was excluded at first** on my guess
  that a −recharge debuff rides Slow enhancements. ✅ **THAT GUESS WAS WRONG AND
  THE ITEM IS CLOSED** (`6b503c0c`, 2026-08-05, Joel: "lets give recharge its
  accreditation"). The client settled it: `Crafted_Curtail_Speed_A`, a Slow IO,
  enhances RunningSpeed/FlyingSpeed/JumpingSpeed + Accuracy and **no
  RechargeTime**, so Slow is not the route; Neurotoxic Breath's −recharge is
  `attribs ['RechargeTime'], aspect Strength` and its `boosts_allowed` includes
  **Recharge**, as do Speed Boost and Accelerate Metabolism pointing the same
  template at allies. A **Recharge** enhancement therefore scales a power's
  recharge effects in BOTH directions, exactly as Damage scales damage.
  `RechargeTime` is in `_ENH_BY_NAME`; verified live 2026-08-06 — Neurotoxic
  Breath reads **−81.2% unslotted → −102.6% slotted**.
  ⚠⚠ **This bullet still said "OPEN / under-credited" a day after the fix
  shipped, and it cost a later session real time chasing finished work.** It is
  the exact stale-entry trap the top of this file warns about: when you close
  something, close it HERE in the same commit. ⚠⚠ **The re-cert question was TRACED, not assumed:**
  `first_principles._deb()` reads `role_output.enhanced_debuff_totals` whenever a
  role_output module is supplied and EVERY serving call site supplies one — this
  summary is only its fallback, role_output was untouched, and encounter_value is
  identical to 9 dp. ⚠ `payoff_metrics["support"]` DOES read it, but its only
  consumer is `joint_refine(scorer="payoff")`, **which has no callers** — wire
  that up again and it starts moving with slotting.
- **🖥 UPDATE THE COPY HE OPENS, DON'T EXPLAIN THE SPLIT (Joel, 2026-08-06: "The
  deliberately means nothing to me, its giberish without context").** The
  dist-vs-installed distinction is MY plumbing. After a server-side change:
  rebuild, smoke, then `robocopy dist\HeroCompanion <installed> /MIR /XF
  unins000.exe unins000.dat` — the uninstaller and ARP entry survive and
  `_install_kind()` still reads *installed*. Then relaunch. Never hand him a
  choice between two copies of his own app.
- **⛔ THE CLASS-ART FILLER WAS REMOVED AT JOEL'S WORD (2026-08-06, `018b539d`:
  "Remove the one image, from your attempts. I will try and find something").
  He is sourcing his own art — do not re-add mine.** The extraction stays
  behind `extract_gui_emblems.py --art` (opt-in, so a routine run cannot drop
  3.8 MB of unused PNGs into static/). The history below is kept ONLY because
  the debugging lesson is the durable part.
- **🖼 (history) the filler's three failed rounds.** The
  art is REAL and now extracted (`charectercreationui/archetypescreenshotsassets`,
  512×512 × 3 shots × 16 ATs; `extract_gui_emblems.py` pulls shot 0 to
  `static/icons/at_art/`, 15 of 16 — Guardian has none). The PLACEMENT never
  painted in the frozen shell: panel background + blend, absolute `::after` at
  0.16, then 0.55 with no mask — because all three were anchored to
  **`#powers-list`, which holds the wall AND the catalogue**, so bottom-right of
  it is the bottom of the CATALOGUE, nowhere near the hole. Joel spotted it
  ("I saw one image for one build but it was small") and that one sentence
  located the bug three measurement rounds could not. **Anchor to
  `.powers-wall`**, size to the hole its last row leaves (measured 978×152),
  `z-index:-1` inside the wall's own stacking context so the opaque cards mask
  it. ⚠ The textures are a ~512×314 picture **padded to a power of two with a
  flat block** — `contain` fitted the pad and put a blue slab on screen; the
  extractor crops it now. ⚠ A cropped BAND fills the strip but the crop lands
  differently per class (Defender lost its legs, Brute lost its heads), so it
  fits by HEIGHT and shows whole at ~245px. ⚠ A dead `.cat-art` rule proved an
  EARLIER session tried this and abandoned it. **Generalize: when three
  measurement rounds disagree with the screen, the thing being measured is the
  wrong element.**
- **⚠ "NOW SLOT THEM" IS A CLAIM ABOUT THE BUILD (Joel, 2026-08-06: "This
  appears no matter if slots are all filled or not").** The catalogue's
  finished-picks line invited slotting unconditionally. It is gated on free
  pool slots or an empty slot in a REAL power, and it names which.
  ⚠ **The seven granted inherents must be excluded** — Brawl/Sprint/Rest hold
  a base slot `_is_no_enhance_inherent` caps the solver out of, so counting
  them makes the invitation permanent: the same bug in a different hat.
  **Generalize: any line that tells the user to do something is a claim, and
  a claim needs a condition.**
- **⚠ A HALF-UPDATED FROZEN COPY IS A LIE, SO DON'T HALF-UPDATE IT.** This fix is
  server-side; the wording that goes with it is static. Pushing statics to the
  installed copy while its PYZ is a build behind would have put "with your
  slotting" above unenhanced numbers. Statics were deliberately withheld from the
  installed copy — it stays wholly on the old text until an install. **Generalize:
  when a change spans the PYZ and the statics, both halves reach a copy together
  or neither does.**
- **🏅 THE BADGE CATALOGUE PUTS EVERY BADGE ON THE SURFACE, AND THE NAME IS THE
  BUTTON (Joel, 2026-08-06).** *"List every badge in each zone underneath the
  names… with the ability to click on any badge name and get the location
  copied. Then make it clear that the zones have full explanations."* It was 57
  closed drawers whose name and count told you nothing about the contents, so
  one location cost an expand and a read-down. All 390 badges render as chips
  under their zone, visible with the drawer shut; the chip carries
  `/thumbtack`; the drawer keeps the prose and NAMES what it holds
  ("Directions and what each badge commemorates"); the how-to is stated ONCE at
  the catalogue head, not on all 57 zones. ⚠ **The copy handler keys on
  `[data-cmd]`, not `.cmd-row`** — one mechanism for every presentation, so a
  new shape can never drift from the shipped one; a chip keeps its label and
  takes a CSS tick (swapping its text reflows the grid under the cursor), the
  wide row keeps its words. ⚠ **The 8 badges with no coordinates are PLAIN
  TEXT, never buttons** — a control that copies nothing is worse than none.
  ⚠ Still pending and visible here: zone keys are RAW internal prefixes
  (`AbSewerNetwork`, and both `CapAuDiable`/`CapauDiable`) — display names ride
  the i24 server-data pass, and the header says so. Do not invent them.
- **📊 THE STATS SIDE COLUMN HOLDS TO 1000px, NOT 1400 (Joel, 2026-08-06: "not
  where it used to be with an arrow pointing to them all in a right hand
  column").** ⚠⚠ **"Alongside what is clicked" meant HIS COLUMN BACK, not a new
  position for the panel** — I read it as inline-under-the-row and shipped the
  wrong shape first. The fault was the BREAKPOINT: the 2026-08-05 rule
  collapsed `.stats-provlayout` below 1400px, and the 1.6× shell zoom put his
  effective width under it, so the column was simply switched off. **Unlike the
  powers rail, this side column is 300-380px of real content that only exists
  while a stat is selected — not a void** — so 1400 was far too early; 1000 is
  where a 380px column stops fitting beside a readable list. Measured at 1240:
  two columns (811+380), panel beside the row, green ➜ intact. `.powers-layout`
  KEEPS 1400. ⚠ `test_desktop_app` pinned "both collapse at 1400" and correctly
  failed — it now pins each at its own width plus a negative control that stats
  has not crept back to 1400; **that control must match the exact collapse
  declaration**, since the base `.stats-provlayout { display: grid; … }` rule
  sits between the two media blocks.
- **📍 THE BREAKDOWN FOLLOWS THE ROW BELOW 1000px (the same day).** `#stat-breakdown` is the LAST child of `.stats-provlayout`, so the
  moment the 1400px rule collapses that grid to one column it lands after
  everything — measured at 1240px: row at y=570, panel at y=**2320**. It was
  never missing, it was 1750px down the page. ⚠ **His window is wide but the
  shell zooms up to 1.6×, so the EFFECTIVE width is what crosses the
  threshold** — always reproduce a layout report at the effective width, not
  the window's pixel width. Fix: one column ⇒ `insertAdjacentElement("afterend")`
  on the selected row; two columns ⇒ restored to its own column with the
  existing centre-on-the-row maths. ⚠⚠ **Re-homing it puts the panel INSIDE the
  rows container, whose innerHTML is rewritten on every recompute — which
  deletes it, and a bare `getElementById` would then return null and the panel
  would vanish for good.** `_breakdownHost()` holds the element in JS and
  re-attaches it when detached; `_SB_HOME`/`_SB_HOME_NEXT` remember where it
  belongs. Proven by driving a real recompute.
- **🚫 THE PICKER REFUSES WHAT THE GAME REFUSES (Joel, 2026-08-06: "make sure
  the end user cannot break rules… a unique IO a second time the entire build,
  or the same IO in the same power more than once").** Both were ALREADY errors
  in `engine.validate_build`, and the same-power repeat was already prevented;
  the gap was a unique held in a DIFFERENT power — takeable, then told off.
  `_uniqueBlockedElsewhere` greys it with the reason, **naming the power that
  holds it**, and `pickPiece` enforces it too (a rule that exists only by not
  drawing a click target is one stray call from being broken). Blocked rows drop
  their `data-cand`, so the swap comparison never advertises a piece you cannot
  take. ⚠⚠ **OVER-BLOCKING IS THE WORSE MISTAKE and the guard is the hard part:**
  LotG's Def/Increased Global Recharge Speed is flagged unique yet legitimately
  slotted many times, so `/meta` now ships `engine.NON_UNIQUE_OVERRIDES` (same
  reasoning as `pool_rules` — never a second copy in JS), and with no meta the
  check **fails OPEN**, because the server validator is the backstop and a blind
  block would refuse legal builds. Verified live: three uniques held in Agile
  correctly greyed elsewhere, LotG slotted in FIVE powers still offered.
  Battery `tools/test_slot_rules.js` (9, four sabotages).
- **🔀 THE SWAP PICKER PRICES EVERY REPLACEMENT (Joel, 2026-08-06: "can there be
  a % increase or deficit shown in the list of replacement IOs?").** Measured,
  not derived — same rule as the per-IO panel. **Cost was measured BEFORE
  designing around it: one `/build/calculate` is 4.9 ms server-side**, so 165
  candidates fit in ONE batched request under a second; no lazy loading needed.
  `POST /build/slot_compare` takes the payload + slot + candidate slot-dicts +
  dotted `keys`. ⚠ **It drives the REAL `build_calculate` through a nested
  `test_request_context`** rather than re-implementing it, so the picker and the
  Stats page can never disagree. ⚠ Candidates ride on the rows as `data-cand`,
  built byte-identical to what `pickPiece`/`pickSpecial` installs — the compare
  prices the thing the click actually does. ⚠ **The axis is `SELECTED_STAT`**: a
  swap moves many numbers and a bare "+x%" is meaningless without naming one, so
  with no stat selected the picker SAYS to pick one rather than inventing an
  axis; set-bonus count always rides along (a lost tier is the cost people
  miss). ⚠ **On a solver-optimised build every single-piece swap on the
  optimised stat reads as a deficit — that is the truth, not a bug**; the gain
  direction is proven by emptying the slot and re-pricing what was in it
  (+1.87% Melee, +1 bonus). Battery `tools/test_slot_compare.py` (9).
- **🧾 EVERY EDIT REPORTS ITSELF, AND HANDS BACK THE UNDO (Joel, 2026-08-06:
  "we need to see the results of a change immediately… perhaps even adding an
  undo button").** ⚠⚠ **The hook is `recordEdit`, NOT the popover's buttons** —
  it runs before every build-mutating edit from every surface, so capturing
  `LAST_TOTALS` there is what makes the receipt universal instead of a special
  case; `_showEditReceipt()` then fires from the recompute, after `renderStats`
  (it anchors into the wall that render just rebuilt, and measures its own
  height). Proven with an edit made through the plain `clearSlot` path, nothing
  to do with the popover. ⚠ **The undo produces no receipt of its own** —
  `undoEdit` never calls `recordEdit`, so nothing is captured, and a receipt for
  putting something back is noise. ⚠ **The popover must survive losing its
  anchor**: removing a piece re-renders the wall and destroys the chit, so
  `_placeIoPop` re-centres rather than closing — closing would take the Undo
  button with it. ⚠ **Column labels are per-caller** (`opts.labels`): "Without
  it / With it" is right for the per-IO panel and WRONG for the receipt, whose
  columns are before/after an edit. Pinned both ways, sabotage-proven.
- **🛠 STATS IS THE MANUAL SURFACE — THAT IS WHAT IT IS FOR (Joel, 2026-08-06:
  "the whole point of the stats page is to provide the end user with a manual
  option to change their stats manually, instead of relying on a global I want
  more percentage on X, Y and Z using the build assistant").** Powers & Slots
  holds the Assistant's target-driven global re-solve; **Stats is where a player
  changes one piece at a time and watches the numbers move.** Consequence: any
  surface here that shows a cost must also let you act on it — the per-IO
  popover carries **Swap this enhancement… / Remove it**, wired to the SAME
  `openSlot`/`clearSlot` the wall and breakdown use, so an edit made there
  records history, recomputes and undoes like any other. ⚠ Swap closes the
  popover BEFORE raising the picker (stacked overlays), Remove closes it too
  (the wall re-renders and replaces its anchor chit). ⚠ **Verified the
  prediction IS the outcome:** predicted Without-it Lethal 23.8 / Smashing 23.8
  / Melee 45.1 / bonuses 41; pressing Remove delivered 23.76 / 23.76 / 45.08 /
  41. Do not add a second editing path — route everything through the two
  existing functions.
- **🎯 THE PER-IO ANSWER IS A POPOVER AT THE CHIT, AND THE *PURPOSE* PICKED THE
  SHAPE (Joel, 2026-08-06).** He offered two options — scroll to the top, or "a
  pop-up next to where the end user is" — and then gave the reason that decides
  it: *"see what they might want to sacrifice on their IO choices to attain a
  better percentage with the LEAST amount of impact on their build."* **That is
  a comparison, so the page must not move**: scrolling answers one question and
  loses your place for the next click. `#io-worth-pop` anchors to the chit in
  FIXED coordinates (the mini wall is sticky, so the chit moves against the
  document but not the screen), re-places on scroll, clamps to the viewport and
  flips above when there is no room. ⚠ Closes on ✕ or an outside click — **never
  advertise Escape, it does not reach the page in the frozen shell**. ⚠ The
  better half: **the stat breakdown underneath is left alone**, so a stat can
  stay selected with its contributors ringed while each contributor is probed in
  turn. ⚠ The per-power table opens FOLDED — an open one made the popover want
  its own scrollbar, which this app does not do.
- **💎 WHAT ONE ENHANCEMENT IS WORTH IS MEASURED, NEVER DERIVED (Joel,
  2026-08-06: "click on one and see all the individual %'s that it affects…
  what would happen if they remove or replace an IO").** `explainSlotWorth(pi,
  si)` recomputes the build with that ONE slot empty and diffs. **The analytic
  version — read the piece's aspects, add its set's bonus table — is wrong
  wherever the game is interesting:** ED makes the last point worth less than
  the first, pulling a piece can drop a whole set TIER, and the rule of five can
  mean a bonus was never applying. Proof, measured: removing a Reactive Defenses
  **Defense/Endurance** costs **Max HP** (tier loss) — an analytic build would
  have shown defence only. ⚠ **The probe is built from `buildPayload()`, never
  from `build`** — the payload carries accolades, incarnate inclusion,
  alignment, PvP and the exemplar view, and diffing without them prices the
  piece against a different character. ⚠ **`/build/calculate` returns the totals
  object ITSELF, not `{totals: …}`** — checking `.totals` silently fails every
  call. Reuses `renderImproveDiff` (now takes a host id + `{bare}`) so this and
  the solve report are the same arithmetic; `bare` drops the solve heading and
  export nag and relabels the columns "Without it / With it", because
  Before/After would misdescribe what the two columns hold.
- **✅ THE "RADIATION MELEE DISCREPANCY" WAS MY BAD COMPARISON — THE DATA IS
  CORRECT (2026-08-06, chased on Joel's word).** I reported the engine as the
  outlier on a ratio of **enhanced** engine damage against **base** client
  scales. It is not comparable: in that build Radioactive Smash holds ONE
  Nucleolus (+33.2%) and Devastating Blow holds THREE Hecatomb damage pieces
  (+96.7% post-ED), so the enhanced ratio must sit below the base ratio.
  Done properly, our base damage is exact: RS 74.1 and DB 154.2 are the client's
  PvE scales (1.48 and 3.08) × an implied table factor of **50.07 / 50.06** —
  agreeing to 0.01 — and the base ratio is **0.481 = the client's 0.481**.
  ⚠ **Retract the earlier claim if it is quoted anywhere: there is no per-attack
  data bug in Radiation Melee.**
- **⚠⚠ DO NOT "FIX" OUR DATA BY ADDING THE EXPORT'S `Fire_Dmg` TEMPLATES — THAT
  IS FIERY EMBRACE (found 2026-08-06).** **86 of 108** Brute melee attacks carry
  a `Fire_Dmg` template whose `requires_expression` is EMPTY in the bin-crawler
  export, across Claws, Rad Melee, everything. It is not unconditional: 124
  clean logged swings show ZERO Fire components, because in game it only applies
  while Fiery Embrace is up. **The crawler is not capturing that gate.** Our
  Mids-derived base correctly counts Smashing+Energy alone; counting the Fire
  template would inflate those 86 attacks by ~45% (RS 74.1 → 107.4). A future
  reconciliation pass that trusts `requires_expression == ""` will do exactly
  that.
- **🔥 FURY: THE NAMED INSTRUMENT IS BUILT, AND IT MOVED THE BLOCKER (2026-08-06).**
  v36 left Fury dormant at a 228% residual spread with a named next step —
  component-summed swing reconstruction. `tools/measure_fury_residual.py` v2
  does it: group damage lines by (timestamp, target, attack), sum the
  components, exclude DoT ticks. **Spread 228% → 25.2%.**
  ⚠ **AoEs CANNOT be reconstructed from this log format and the tool now says
  so per attack.** Farm mobs share a display name, so the grouping merges an
  AoE's hits on DIFFERENT enemies — Atom Smasher logs 2x/4x/6x…18x components
  for a two-component attack. Only single-target attacks isolate (100% shape
  purity); the tool prints each attack's purity and anchors only on the pure.
  ⚠⚠ **STILL UNCLEAN, AND THE REASON IS NOT THE METER.** Both clean attacks'
  swing distributions are tight and unimodal with near-identical shape (p95/p05
  1.38 and 1.45), so this is not Fury noise. The disagreement is on the EXPECTED
  side, and a global multiplier CANCELS in an attack-to-attack ratio:
  Radioactive Smash ÷ Devastating Blow reads **engine 0.325 · game 0.420 ·
  client 0.481**. ⚠ **The "engine is the outlier" reading of those three numbers
  was WRONG and is retracted — see the entry above.** The engine number is
  ENHANCED and the client number is BASE, and the two attacks are slotted very
  differently, so they were never comparable. Our base data is exact.
  **What actually blocks Fury: only TWO attacks isolate cleanly, and two data
  points cannot separate a multiplier from a flat term** — solving
  `expected×F + C = observed` on both gives F≈0.995 / C≈48.9 with zero degrees
  of freedom left to validate it, which is fitting, not measuring. **The next
  step is a THIRD clean single-target attack**: farm logs from a Brute whose
  rotation carries three or more single-target attacks (this build's rotation is
  almost all AoE, and AoEs cannot be reconstructed at all).
- **🔗 POWER BOOST AND THE FURY METER ARE THE SAME MISSING CAPABILITY (found
  game-first 2026-08-06).** Power Boost was queued as a parser-allowlist data
  gap ("+66% amplifier effects invisible"). The client says otherwise: all 10
  Power_Boost/Boost_Range records carry **zero effects** in our data, and the
  client's own record is a **`Set_Mode` template (mode_name `BoostPower`, 15
  seconds)** followed by effect groups tagged `PowerBoostA`. It is a temporary
  MODE that amplifies what you cast while it is up — not a flat bonus a patcher
  can add. That is the same shape as Fury / Rage / Domination / Defiance /
  Gauntlet: **the engine has no model for a temporary mode or meter.** Build
  them as ONE piece of work, and note the display half is already Joel's
  standing ruling (a meter has no headline number without a scenario).
  ✓ **Champion exposure is ZERO** — no certified build holds Power Boost — so
  whenever this lands it cannot move a certified score, and needs no re-cert.
- **🧭 THE ORDER TO WORK IN IS STATED ONCE, AT THE TOP (Joel, 2026-08-07: "I
  really do not see a well defined decision tree, just lots of choices").**
  The evaluation, measured on a 900px window with a level-50 loaded: Powers &
  Slots runs **~4.6 screens**, the Build Assistant heading sits **2.7 screens**
  down and the **SOLVE BUTTON 3.6** — so a returning player meets 24 power cards
  first and the engine last. The loop WAS written down, as four fragments at
  four depths (0.3, 1.5, 3.8 screens, plus a line on Stats), and the Character
  menu offers four ways IN with **nothing for "I have a build and want to change
  it"** — the commonest case after week one.
  **His ruling: a band at the top of Powers & Slots**, four numbered steps
  (goal → Solve → tune on Stats → change powers last), each LINKING to the
  surface that does it. ⚠ Shown only when a build EXISTS (`renderChangeSpine`,
  called from `renderPowers` BEFORE its empty-build early return, or it could
  never hide itself). ⚠ **Not a fold** — folds default CLOSED here, which would
  hide the one thing it exists to say; it is sized to stay a signpost instead.
  ⚠ **Step 2 points AT Solve, it does not press it** — a signpost that runs the
  optimizer is a decision the user did not make.
  ⚠ **The tour carries the other half** (his follow-up: it should reinforce the
  workflow "so people know what they are likely to do with results"). The band
  says the ORDER; the tour step says what each step HANDS BACK — Solve returns
  the before/after that answers "did this help?", Stats answers "why?". Mock
  stand-in `data-for="change-spine"` added, or audit_tour fails its coverage
  check.
- **🧯 WHEN I BREAK SOMETHING, I FIX IT — I DO NOT HAND HIM THE MENU (Joel,
  2026-08-07: "not sure why this was a suggestion. If it is broken fix it").**
  I damaged a sample save by testing on it instead of a copy, could not restore
  it exactly, and then offered him a choice of which power to sacrifice. Wrong
  shape twice over: the damage was mine, and the choice was between three
  options he had no reason to care about. **Repair it, state plainly what could
  not be recovered and why, and stop** — a question is for a decision that is
  genuinely his, not for me to share out the cost of my own mistake.
  ⚠ The prevention is the real rule and it is already in this file: **never test
  against a real save** (autoSaveTick persists). Use a scratch copy and delete
  it. I read that rule, then broke it inside the same session.
- **🔁 THE EPIC SWAP FINISHES THE JOB (Joel, 2026-08-07: "I wanted to change the
  Epic from Electricity to attain access to Mace Mastery. It took more effort
  than I thought").** It was an asymmetry the code stated outright — primary and
  secondary offered "switch and rebuild", *"epic keeps the lighter prune-only
  confirm"*. **MEASURED** on a real save (Scrapper, Dark → Energy Mastery):
  picks **24 → 22**, added slots **67 → 65**, powers from the pool just chosen
  **ZERO**. Now a three-action dialog: **Switch and refill** (default) ·
  *Switch, I'll pick them* (the old path — **the light route stays, Joel's
  ruling**) · Keep.
  ⚠⚠ **The client half alone did NOT work, and the reason is the durable bit:**
  `/build/autopick` chose its OWN favourite epic pool, and `autopickRemaining`'s
  `mySets` filter then discarded every one of those powers as belonging to a set
  the build does not hold — so the first version refilled **0 epic seats**.
  Fixed at the source: `_pick_epic(force=)` (one line — `ps = force if force in
  epics else max(epics, key=pool_score)`), threaded
  `_auto_pick_powers(epic=)` → `/build/autopick` → the client sends
  `epic: build.epic`. The server still decides WHICH powers inside the pool.
  ⚠ **`force=None` is BYTE-IDENTICAL — proven on 272 archetype × content × role
  combinations**, because `_auto_pick_powers` also feeds the wizard and the
  champion paths and no certified score may move for a UI convenience. An epic
  the archetype cannot take is IGNORED (fail-safe to the scored pick).
  ⚠ `_solveAlreadyApproved()` was factored out of `_scheduleIdentityRebuild` —
  ONE copy of "run the real Solve, carrying an approval already given"; a second
  hand-written auto-clicking loop would drift.
  Battery `tools/test_epic_swap_refill.py` (6, negative-controlled).
  ⚠⚠ **THIS SPANS THE PYZ AND THE STATICS.** The client sends `epic:` and only a
  REBUILT server reads it — statics alone give the half-working shape the
  "half-updated frozen copy is a lie" rule forbids. Rebuild before the statics
  reach any frozen copy.
- **🧹 THE FULL SWEEP FOR PER-CHARACTER STATE (Joel, 2026-08-07: "do a full pass
  over the app for anything else like this").** Enumerated all 97 pieces of
  mutable module state in app.js, then **measured** which survive a real
  character swap in a live page rather than reasoning about it. **Ten did**, and
  they are now cleared in `resetBuildScopedState`: `SELECTED_STAT`,
  `SELECTED_POWER`, `IMPORT_BEFORE`, `IMPORTED_POWERS`, `CHANGES_AVAILABLE`,
  `SOLVE_INTENT`, `PROPOSED_RESPEC`, `LAST_TIERS`, `PENDING_FOCUS`,
  `INTERP_MATCHED`, `INCARNATE_RECS`, `INCARNATE_LOADOUTS`, `LAST_ASSESS_ROUTES`.
  **The visible one was `SELECTED_STAT`:** click an attack row on a Warshade,
  open a Defender, and the Stats breakdown still stands open headed **"Boxing"**,
  a power the loaded character does not have. Reproduced deliberately.
  ⚠ **`_convHaul` is DELIBERATELY NOT SWEPT** — it is a list the USER typed (the
  drops they walked in with), not state the app derived, and dropping typed input
  on a swap destroys work. Whether it should be per-character is a ruling, not a
  sweep's call; the battery pins the decision either way so it cannot drift.
  ⚠ **My own bad probe, recorded because it nearly became a claim:** I reported
  the import "what changed" button as still OFFERED after a swap. It was not —
  my check tested for a `hidden` CLASS while the button is hidden by
  `display:none`. The STATE leak was real and worth clearing; the visible symptom
  was not. **A visibility check must ask the layout (`offsetParent` /
  `getClientRects`), never a class name.**
  ⚠ Also confirmed CLEAN and not worth re-checking: `RESPEC_LAST_HINT` and
  `SELECTED_ENH` already reset, and `LEVELING_STEPS` is genuinely rebuilt per
  character (verified by comparing the actual power ids, not the object).
  Battery `tools/test_edit_history_scope.js` grew to **24 checks / 7 sabotages**.
- **⏪ OPENING A CHARACTER IS NOT AN EDIT — AND THE PHANTOM RECEIPT WAS THE
  SMALL HALF (Joel, 2026-08-07: "it now looks terrible").** A "What changed"
  receipt appeared by itself at launch. **TRACED, not guessed** — hooking
  `recordEdit` in a live page gave the stack
  `recordEdit ← onPoolChange ← onArchetypeChange ← applyImportedBuild ← loadSave`:
  every load drives the archetype/pool cascade, and the cascade records an edit
  exactly as a user's dropdown change would.
  ⚠⚠ **The serious half was the UNDO STACK.** Measured before the fix: open one
  character, then another, and Undo is **ENABLED having done nothing**, with the
  top differing snapshot holding **ZERO powers** — pressing it emptied the build
  you had just opened. `resetBuildScopedState` cleared custom targets, exposure,
  travel, previews and accolade ticks and **never cleared `EDIT_HISTORY`**, which
  is the same state-lifecycle family its own comment describes.
  **Fix, both at the source:** `_LOADING_BUILD` guards `recordEdit` (the ~15 call
  sites are all legitimately edits when a *person* does them — what makes it not
  an edit is that the app is driving, the same reasoning as `_atGuard` one
  function over), set across the WHOLE of `applyImportedBuild` in a **try/finally**
  because a load can throw and a leaked flag would silently stop recording every
  real edit afterwards; and `EDIT_HISTORY` is cleared in `resetBuildScopedState`,
  whose only two callers — `applyImportedBuild` and `startFromScratch` — both mean
  "different character now".
  ⚠ Battery `tools/test_edit_history_scope.js` (10, lifted under node, **four
  sabotages** each caught by its own check) — and it carries a POSITIVE CONTROL,
  because a battery that only proves recordEdit does nothing would pass just as
  happily if recordEdit were gutted.
  ⚠ Method note worth keeping: the pane could not reproduce the receipt (fresh
  page, `LAST_TOTALS` null, so `_showEditReceipt` returned early) but it DID
  reproduce the root cause, and `EDIT_HISTORY.length === 1` on a page with **zero
  powers** was the tell that broke it open. Probe the mechanism, not the symptom.
- **🔲 THE BORDER WAS NEVER THE DIFFERENCE — CENSUS THE TREATMENTS BEFORE
  "FIXING" ONE (Joel, 2026-08-07: "Build assistance, in-game commands, and how
  set bonuses stack, are the only items on this entire powers and slots tab that
  do not have a small blue line around them").** He was right about the symptom
  and I was about to fix the wrong thing: **every `.panel` on that tab already
  carries the identical 1px `rgb(39,57,92)`** — I measured all six and they were
  byte-identical, which flatly contradicted the screen. A census of EVERY
  bordered box on the tab found three treatments:
  **32** dim border on the LIGHTER fill `rgb(27,39,64)` (`.cat-col`,
  `.generate`) — *the fill change draws the edge, not the border*; **6** the
  accent outline `rgb(77,163,255)` (`.accolades-card`, `.order-out`); **17** dim
  border on the panel's OWN fill `rgb(20,29,48)` — a slate line between two
  near-identical darks. The 17 read as boxes only when they CONTAIN one of the
  first two, which is why the Epic panel and Accolades look fine. Joel's three
  contain neither at their own edge, so they alone float. Fix:
  `.pw-cardband > .panel, #assistant { border-color: var(--accent); }` —
  ⚠ deliberately NOT applied to panels that already hold an accent-outlined box,
  which would double the line. **Generalize: when a visual complaint and the
  computed styles disagree, the property you are looking at is not the one
  doing the work — tally every treatment on the surface before changing any.**
- **📣 A TOOL THAT CANNOT EXPLAIN ITSELF IS HALF-BUILT — AND THE APP CANNOT
  ZOOM ITS WAY OUT OF SMALL TYPE (Joel, 2026-08-07: "the Build Assistant and
  Stats really leave the end user wondering what either actually do… tiny text
  and barely a breakdown of how potent both can be on an existing build").**
  Three separate faults, and the first is the one with a corpse:
  ⚠⚠ **`collapseLongExplanations` ate the Assistant's own description.** The
  sentence saying what the tool does is over 26 words, so it was folded — and
  its lead clause is over 96 characters, so the summary truncated **mid-word**:
  *"never touches 🔒 l… more"*. The one paragraph explaining the feature was the
  one paragraph nobody could read. **Every lede that explains a surface gets
  `.keep-whole` at birth** — this is the same rule the file already carries,
  broken again, now on the two most important panels in the app.
  ⚠ **Type size is only ever fixable in CSS here.** `fitZoom` takes ONE zoom
  from the TALLEST tab with a floor of **1.00**, and Powers & Slots never fits,
  so the whole app is pinned at 1.00 permanently. "Make it bigger" can never
  come from the zoom. New `.tool-lede` (14px against the 12px `.small`) and
  `.tool-head`, deliberately scoped to these ledes — **`.small` is load-bearing
  on cards, chips and slot labels and must not be raised globally.**
  ⚠ **"Potent" means saying what it does to a build you ALREADY have**, which is
  what the copy now leads with: the Assistant never touches the powers you
  picked and re-solves every earned slot in about a second with a before/after;
  Stats prices one enhancement by pulling it, prices every legal replacement
  before you commit, and undoes anything.
  ⚠ **`↳` (U+21B3) HAS NO GLYPH IN THE APP'S FONT** — it painted as a broken box
  in **11 places**. Replaced with `→`, which the app already renders. Check any
  new symbol on screen before shipping it; the batteries cannot see this.
  ⚠ `var(--text)` IS UNDEFINED in style.css — the ink token is **`--ink`**.
  Three existing rules already use the dead name (`.sb-leg b`, `.jny-chip-how b`,
  and `.ghost-btn`, the only one with a fallback). Do not copy that pattern.
- **🪪 THE ALIAS MAP LEARNED THE DISPLAY NAME, AND THE RUNG THAT MATTERS IS
  "TWO OF OURS WANT ONE OF THEIRS" (2026-08-07).** `build_power_aliases.py`
  matched on internal names, fuzzy names and scalar fingerprints — three rungs,
  none of which is the namespace both sides actually share. Adding a
  **unique display-name match inside the candidate sets** (the same rung
  `patch_prereq_counts.resolve` already had) took roster diffs **12 → 3** and
  changed **zero existing aliases** (proven by diffing the map with the rung
  disabled: 164 → 173, none changed, none lost). The 3 that remain are real
  roster differences and are now each **named with their evidence** in
  `ROSTER_DIFF_DISPOSITIONS`, with a **hard fail both ways** — an
  undispositioned diff fails, and a disposition left behind after a fix fails
  too (Joel's "knowing all, not just most").
  ⚠⚠ **The collision rung found a defect nothing else could see — ✅ FIXED the
  same day on Joel's "fix the Tactical Arrow power".** Blaster **Tactical Arrow
  showed "Oil Slick Arrow" twice and never showed "Gymnastics"**: our
  `Gymnastics` record holds the client **Quickness** record's effects (+25%
  defence on all 11 vectors, `Melee_Buff_Def`, plus RechargeTime 0.2 — that is
  the Gymnastics passive) while wearing client **Gymnastics'** display name AND
  header, so the passive was priced at Oil Slick's **90s recharge and 15.6
  endurance** instead of 10s and 0.13, **and could not hold a defence set**.
  Our separate `Oil_Slick_Arrow` record is the genuine click and pairs
  correctly. **A display check passes it** (both sides say "Oil Slick Arrow")
  and **a scalar check passes it** (the header matches its name-pair exactly) —
  only two-of-ours-wanting-one-of-theirs sees it.
  **The repair is `tools/patch_display_name_collisions.py`, and it hardcodes
  nothing.** Identity is proven by the EFFECT signature (the one thing the
  overwrite did not touch) matching a unique client record in the same set;
  the scalars then come from that twin. ⚠ **The categories had a second,
  independent signal already in our own file: `accepted_set_category_shorts`
  survived intact and still carried `Defense`** (6 shorts against 9 names and
  5 ids — the length mismatch WAS the tell), so the name/id lists are rebuilt
  from our shorts and then **cross-checked against the client**, with a hard
  failure if the two disagree. Result: exactly **1 record, 7 fields**, verified
  through the served `/powers` route. ✓ Champion exposure ZERO, counted not
  assumed — no score moved, no re-cert owed.
  ⚠ **Two follow-ons the fix REQUIRED, and forgetting either would have put
  false drift into a standing check:** the pinned rename
  `our Gymnastics -> client Quickness` must be applied even though a same-name
  client record exists (the loop only walks powers missing from the snapshot),
  and `reality_check_powers` must prefer an **adjudicated alias over a same-name
  coincidence** — otherwise it compares our defence passive against Oil Slick
  and reports four fields of drift that are not drift. Both done; the check
  reads 5,832 powers with slotting drift 0 and value drift unchanged.
  Battery `tools/test_display_name_collisions.py` (3,727 pickable powers; the
  allowlist is now **empty**, which is the goal state — its stale-entry check is
  what forced the entry back out the moment the fix landed).
  ⚠ **Retracted mid-investigation, recorded so the shape is visible:** I first
  read this as the exact-name rung mis-pairing our Gymnastics passive to the
  client's Oil Slick click, and swept for it. **The sweep found 0 of 5,659
  exact-name pairs disagreeing on display name** — because our record's display
  is itself wrong, the two agree by accident. A names-only detector cannot find
  a names problem.
- **🔒 A `pv_mode: 2` ROW IS A PvP VARIANT, NOT A DATA DEFECT — and 189 of them
  were sitting in the reconciliation residue (closed 2026-08-07).** The "8
  irreducible Chrono_Shift rows", queued since 2026-07-28 as *"values match
  nothing client-side, suspected Mids pre-enhanced bakes"*, are neither. Each is
  **exactly 5.33× the client's OWN timed `Heal_Dmg` scale on the same power**
  (0.2 → 1.066, 0.3 → 1.599), the same constant on all four AT variants, with
  the Mastermind's 0.88 support factor riding cleanly through both sides
  (0.176 → 0.93808). A constant multiple of a client scale across four
  archetypes cannot be an enhanced bake — it is a deliberate heal-over-time →
  regeneration conversion. Nature Affinity's Regrowth is the same shape at ×5.0.
  ⚠ **They cannot move a PvE number**: `engine._pv_ok` gates `pv_mode 2` off
  everywhere (engine, solver, role_output, server), proven live — the buff panel
  reads nothing in PvE and +266.5% Regeneration in PvP.
  ⚠ **Why reconciliation could never match them:** the client export's
  Chrono_Shift record has **zero `PVP_ONLY` effect groups**, and the export DOES
  carry 541 of those elsewhere — so that is a real absence, not a crawler gap.
  Mids maintains its PvP variants outside the bins. **Whether 5.33 is the right
  constant for live PvP is UNVERIFIABLE from the client and is deliberately not
  claimed**; it is inert in PvE either way, so nothing is owed.
  `classify_unmatched_effects.py` now tests `pv_mode` FIRST and names the class:
  residue **240 → 184**, same 1,424 rows, no data changed. Battery
  `tools/test_pvp_variant_gate.py` (9, three sabotages).
- **⚠ AN EMPTY STATE IS A CLAIM TOO (Joel, 2026-08-06 — the Flashback art).**
  The art slot had ONE message, "zone art pending", for two different empties:
  a zone we hold no texture for (true) and a level the current view maps no zone
  to at all (false — nothing is pending, and on Flashback above level 20 nothing
  ever will be, while `nova-praetoria.jpg` sits on disk). Joel read it as missing
  artwork, which is exactly what it said. **When one message serves two states,
  it is wrong in one of them.** The out-of-range note now names the range and
  DERIVES it from the zone data (`_praeRange`) instead of hardcoding 20.
  ⚠ Related, same fix: badge coordinates were nested INSIDE the directions
  block, so the **25 badges with coordinates but no written directions showed no
  location at all** — a fact must never be gated on whether prose exists beside
  it. Battery `tools/test_journey_macro.js` (20 checks, node, alternative-app.js
  argv[2], proven against 6 sabotages).
- **⚠ A JS-ONLY function CAN have a real battery: lift it out and run it under
  node.** `tools/test_improve_diff.js` brace-matches `renderImproveDiff` out of
  app.js, evals it with `escHtml`/`$` stubs, and asserts the HTML. It takes an
  alternative app.js as `argv[2]` **so the battery itself is proven against
  sabotaged copies** rather than trusted for going green — six sabotages, each
  caught by the right check. Beats another regex pin in test_desktop_app.
- **⚠ THE SHARE PROMPT IS NOT A MODAL, and that took three tries.** Hooked to
  `hideEntry()` it ambushed the first meaningful action on every entry path;
  moved to once-per-launch it was still a wall with a backdrop between the user
  and his character. It now lives INSIDE the opening menu, in the flow, under the
  tour line. **The lesson is the general one:** the first two fixes changed *when*
  a wall appeared; only the third asked whether it should be a wall.
- **⚠ JUDGE FROM THE FROZEN EXE, and know which one.** Handing Joel a `.bat` +
  console + python.exe and calling it the app was my error. Frozen builds now
  carry their commit (`HeroCompanion.spec` stamps `build_commit.txt`, server.py
  reads it when frozen) because two 0.12.30 builds on one machine were
  indistinguishable and a bug got reported twice against a build without the fix.
  The header shows the hash on SOURCE runs only; About and the tooltip always.
- **⚠ Installing overwrites `dist\HeroCompanion-Setup-{VERSION}.exe`** — which was
  the RELEASED SIGNED installer. Preserved as
  `HeroCompanion-Setup-0.12.30.released-signed.exe`. Check before every ISCC run
  while VERSION is unchanged.
- **⚠⚠ NEVER hang a Window object (or anything rich) on the js_api object.**
  pywebview WALKS the api object's attributes to build the JS bridge —
  `_Api.win = win` froze the app at "(Not Responding)" before first input
  (2026-08-03, cost one hung build). The window ref lives in a `_winref`
  closure inside `_run_window`; the api object carries only plain state.
- **⚠ `ALLOW_DOWNLOADS=False` SILENTLY EATS blob downloads** — the .mbd export
  clicked its `<a download>` and nothing happened, no file, no error (found
  2026-08-03 driving the advanced path; audit passes could never see it).
  Every file the page produces routes through `js_api.save_file` (a real
  Save As dialog, saveTextFile() in app.js picks the path per surface). The
  setting stays False on purpose — the download flyout is a browser tell.
- **The build tile has a NAME field (Joel, 2026-08-03: "perhaps we want a new
  field called name?").** Empty for auto-named saves (placeholder invites),
  commits on blur/Enter through saveProgress, the nudge's "Give it a name"
  now focuses it. ⚠ autoSaveTick sends `named: !NEEDS_NAME`, never a blanket
  true — the blanket stamped person-chose-this on saves nobody named and
  silently killed the rename nudge (found + repaired 2026-08-03).
- **`/saves` sends `picks`** so the Continue list can label a half-built save
  "✏️ In progress · N of 24 picks" — a 4-pick save read "✓ Level-50 build"
  because the badge keyed on mode alone. Client tolerates a server without
  the field (old label) — but only a REBUILT frozen server sends it.
- Battery: `tools/test_desktop_app.py` (54, negative-controlled both ways).
  `tools/audit_tabs.py` = the tab-shell audit (ids resolve, wiring, 4 negative
  controls); it caught 5 dead nav-era references on its first run, one of
  which (autopick reading retired ids) was silently dropping the wizard's
  exposure/travel answers from every generated build.

## 🖥 THE TABBED APP (Joel's redesign, 2026-08-03 — supersedes the tile layout)

The single-page app became a tabbed desktop application: build tile
(identity) + tab strip as sticky chrome, then **FOUR tabs — Powers & Slots /
Stats / Leveling Guide / Logging. The END GAME TAB WAS RETIRED (Joel,
2026-08-04, 21d5fdd7): accolades = full-width panel under the powers wall
(#endgame-panel); epic + incarnates = the End-game plan fold in the side
column under the Assistant (#endgame-plan-panel — the pre-tab rail
placement his screenshot asked for); the import/solve Improvement report
sits in the Assistant under the solve buttons. Menu + ladder gates jump
via openEndgame(); stale remembered "endgame" tab keys fall back to
powers; tour chapter endgame maps TM_TAB→powers with its mock block
re-tagged powers (stacks under the wall mock).** `balanceColumns()` is DELETED — tabs split the columns
it shuffled tiles between. Full detail in `tabbed-layout-spec.md`; handoff state
in RESUME-HERE.md.

- **✅ Navigation declared done + TOUR REBUILT (Joel's word, 2026-08-04,
  f9176684): 59 steps / 9 tab-shaped chapters over a mock of the REAL shell**
  (menubar + five-tab strip + tile + one mock panel per tab; `TM_TAB` maps
  chapter→tab, `_mockShowScene(scene, tab)` drives it). All 0.12.29 tour
  rulings still apply (mock-never-live, scenes, anchors, tour green, stray
  clicks, save-spot, deep links). New traps: the REAL
  `body:not(.tab-powers)` tile-hide and sticky tabbar leak INTO the mock —
  overridden `#tour-mock`-scoped; the mock's own tile-off must be a CLASS
  (`.tm-tile-off`, later in source) because the flex override is !important.
  statBar/headerRow diagrams retired with their surfaces; `.ov-table`/
  `.prov-*` CSS deleted (the old mock was the last user).

- **⚠⚠ GET EYES BEFORE TOUCHING LAYOUT.** `mcp__computer-use__request_access`
  (["Hero Companion", "MidsReborn"]) then `screenshot`/`zoom` on the REAL
  installed window. Joel: *"I feel like you are going about this blind."* He was
  right — roughly half the layout defects fixed on 08-03 were invisible to
  measurement and obvious in a screenshot. The Claude pane fires NO layout
  callbacks, has a 0×0 viewport where every hit-test falsely passes, and times
  out at 30s: fine for logic, useless for appearance.
- **🚫 NO SIDE BAR ON POWERS & SLOTS UNLESS AN ENHANCEMENT IS ASKED FOR (Joel,
  2026-08-06, `809c9190`).** *"The output of a build assistant is terrible on the
  far right… Epic and incarnate first, then Build Assistant. Let it take up the
  entire horizontal width so no side bar appears at all, unless IO details are
  asked to be displayed."* He named the cause: the Assistant's output is
  **tabular**, and 340px turned a four-column table into wrapped fragments
  (measured after: 1489px wide, every row one 22px line). `#endgame-plan-panel`
  then `#assistant` are full-width under the builder; `.powers-side` holds the ⓘ
  card alone. ⚠ **The card opens the column in CSS** —
  `.powers-layout:has(#power-info:not(.hidden))` — never a JS class: the card is
  shown/hidden from several places and each was a place to forget. ⚠ **Every
  narrow override must REPEAT the whole `:has()` selector**: `:has()` takes its
  argument's specificity, so a bare `.powers-layout` loses to the id inside it.
  ⚠ This retires the grout rule and the "two columns ALWAYS" rule; the
  2026-08-04 one-row arithmetic (7 powerset columns can't fit beside the wall)
  is also superseded — with no side column they fit, verified on screen.
- **🎨 THE WORDMARK IS TEXT, NOT FOUR IMAGES (Joel's art sheet, 2026-08-06 —
  `C:\Users\joelc\Downloads\Art\Hero Companion Wordmarks.html`).** The sheet is
  HTML/CSS in the **Anton** face, so the app sets it as text: crisp at every
  zoom the shell picks, two-tone driven by the name `applyAlignment` already
  swaps, no fifth asset to keep in sync. Anton is **vendored** with its SIL OFL
  (`static/vendor/anton-latin.woff2` + `anton-OFL.txt`, CREDITS.md) — ⚠ never
  linked to Google Fonts; the app has no network and an href renders nothing.
  ⚠ **Each alignment carries its own `body.align-<key>` class**: theme-hero /
  theme-villain / align-mid are only THREE states and Vigilante vs Rogue are
  different marks. ⚠ **Sized to the space that was already there** (his order:
  "obviously trim the size down to fit into the existing space") — the sheet's
  30px header row measures 171px against the old title's 136px; shipped at 20px
  = 132px with the masthead unchanged at 47.5px, so the measured sticky-chrome
  vars never move. Anton is tall and condensed, so it still reads bigger.
- **⚠⚠ A STATIC SUBDIRECTORY NEVER REACHED THE FROZEN COPIES (found 2026-08-06).**
  `push_statics.py` copied `os.listdir(static)` — TOP-LEVEL FILES ONLY — so
  `static/vendor/` and `static/icons/` were never synced. A vendored font landed
  in the repo, the CSS using it reached both frozen copies, the font reached
  neither, and the tool printed "2 of 2 known copies updated" over the miss:
  the exact assumed-not-visible failure it was written to end. It walks the
  whole tree now and prints "N of 3100 files written". ⚠ Generalize: a coverage
  denominator counted over the wrong SET is not a denominator.
- **⚠⚠ THERE ARE TWO FROZEN COPIES, AND A HAND COPY REACHES ONLY ONE.**
  `%LOCALAPPDATA%\Programs\HeroCompanion` (installer) **and**
  `<repo>\dist\HeroCompanion` (PyInstaller output). On 2026-08-05 I copied
  statics into the installed one, screenshotted it, called the work verified —
  and dist stayed on day-old files; Joel reported "it still shows the AI choice"
  and he was right about the artifact even though his shortcut points at the
  installed copy. **Use `py tools\push_statics.py`** — it writes every known copy
  and prints a coverage denominator, so a missed copy is visible instead of
  assumed. Then RELAUNCH (statics load at launch; F5 does nothing in WebView2).
  **server.py / run_app.py changes need a REBUILD** — the frozen build carries
  them inside the PYZ, so a file copy silently does nothing.
  ⚠ Generalize: verifying against a copy the user might not open is verification
  theater with extra steps — confirm WHICH artifact he launches.
- **It ZOOMS, it does not rearrange** (his words: *"like a zooming in or out.
  Not a break a working screen layout"*). One zoom for the whole app from the
  TALLEST tab — per-tab was measurably correct and awful, because every tab click
  resized the masthead. Floor **1.00** (never shrink: shrinking to fit is what
  made everything tiny), ceiling 1.60. ⚠ Solved by BINARY SEARCH — the obvious
  `z ← z·(avail/need)` OSCILLATES, because scrollHeight is a STEP function of
  zoom (zooming out adds a wall column, which drops a row).
- **⚠ NO SCROLLBAR INSIDE THE APP.** Nested scroll boxes were removed from the
  panels, the accolade list, the road cards and the journey panel. If a tab is
  genuinely taller than the window, the WINDOW scrolls — one bar, at the edge.
- **⚠ Panels are HIDDEN, never unmounted.** recompute() writes into elements on
  four different tabs; unmounting makes every write a silent no-op. `[hidden]`
  needs `!important` to beat a panel's own display rule. Nothing may MEASURE a
  hidden panel — display:none is zero geometry.
- **Powers & Slots is the in-game RESPEC**: picks in level order along the 24-rung
  ladder, only what the game offers at that level, prereqs from
  `server._prereq_need` shipped on `/powers` as `prereq_need` (never a second
  copy in JS — that rule already cost a 12-hour wave once). Pool rules likewise
  ship on `/meta.pool_rules` from `_picks_legal`: **max 4, the epic does NOT
  count, and the origin-themed pools are one per build.**
- **⚠ GREY OUT, NEVER HIDE** what the rules forbid (his ruling). A removed option
  teaches nothing; a disabled one with the reason on it teaches the rule.
  ⚠ Doing so changes what "first option" means — the pool cascade then chose
  Concealment four times. Take the first AVAILABLE option.
- **⚠ NEVER label a powerset from its internal name** — the app showed "Radiation
  Manipulation" beside a dropdown reading Atomic Manipulation. One
  `powersetDisplayName()`; internal-derived text is a visible last resort.
- **⚠ evaluate_js from pywebview's `closing` handler DEADLOCKS the app** (shipped
  it; "Not Responding" on the first close). The handler runs on the GUI thread
  and evaluate_js waits on that same thread. The page PUSHES its dirty flag via
  js_api; the prompt fires from a worker thread; the veto is one-time.
- **⚠ A z-index on a child cannot escape its parent's stacking context.**
  `#masthead` at 30 under sticky bars at 40/39 clipped its own dropdown.
- **⚠ `collapseLongExplanations` eats any muted block over 26 words.** It folded a
  rules line behind "more" the moment it was written. Rules lines carry
  `.keep-whole`. ⚠⚠ **It fires on RE-renders too, so a line can read fine when
  written and lose its second half later** — three separate blocks lost their
  tails on 2026-08-05 alone (the import panel's closing note, the Leveling
  Guide's Flashback line when the View menu repainted the road, and the exemplar
  dialog's state line on every recompute). **Any muted block you author over ~26
  words gets `.keep-whole` at birth, not after someone spots the "more".**
  ⚠ Broken AGAIN 2026-08-06, hours after the rule was restated: a LENGTHENED
  mini-wall header showed both copies at once, the folded one and the expanded
  one. **Making an existing muted line longer counts as authoring it.**
- **🧹 VIEW MENU, TRIMMED (Joel's marked-up screenshot, 2026-08-05).** **End Game
  REMOVED** — it jumped to panels living on Powers & Slots, which the menu
  already lists (`openEndgame()` stays for the ladder gates; battery pins that
  the route survived the item). **Layout mode REMOVED from the menu** — it is
  MY design tool, not a player feature, and it sat under Alignment as if it
  were one; unchanged and still on **Ctrl+Shift+L** (its on/off label went with
  the item — `audit_tabs` caught the dangling `$("layout-mode-item")`).
  **Exemplared view now opens a DIALOG** (`#exemplar-modal`) that explains what
  exemplaring is in plain English and sets the level, replacing a focus-and-pulse
  that only ever answered "where is the control". THREE dials now (build tile,
  Stats row, dialog), one state, one setter — add any new one to BOTH the list in
  `setExemplarView` and the one in `initExemplarControl`. `.exemp-pulse` deleted
  with the behaviour it served.
- **Build Assistant placement RULED (Joel, 2026-08-03): it stays on Powers &
  Slots.** Do not re-litigate spec §10.2.
- **🎚 EXEMPLAR ARC (Joel's rulings, built 2026-08-03 — Layers 1-3 complete).**
  Rules wiki-pinned (both wikis): powers received > level+5 off (inherents/
  accolades/temps immune); set bonuses live while level ≥ IO level − 3, PER
  PIECE, and SURVIVE a lost host power; attuned follow set_min − 3; purple/
  PvP/Winter/ATO exempt (rosters = converter.py's, one copy; ATO = "Archetype
  Sets" category → `_EXEMPLAR_EXEMPT_UIDS`); LotG-class globals follow the
  piece rule; PROCS keep firing (why proc builds exemplar well); incarnates
  off <45. **Layer 1** = the VIEW (suppression precedent: never saved/solved):
  dial in THREE synced places (build tile / Stats toggles row / View menu),
  bold banner, ⛔ card badges, engine gates via ctx["exemplar"].
  **Layer 2** = the advice in numbers on the banner incl. the fully-ATTUNED
  counterfactual (2 extra display calculates). **Layer 3** = opt-in
  `solve_ilp(target_level_ctx=)` — ABSENT IS BYTE-IDENTICAL (pinned); NOT a
  model bump; champions/deep_optimize never pass it; dead bonuses zero,
  past-L+5 powers = pure bonus mules, surviving sets EMIT ATTUNED (before
  finalize — locked/preserved pieces untouched), fp arbitration skipped
  (level-50 physics = wrong judge). Measured: Spines/FA solved for 27 keeps
  47 tiers vs plain 19, zero cost at 50. Batteries: test_exemplar_view 18 ·
  test_target_level_solve 9 (+ full sweep green).
- **⚠ STICKY CONTENT MUST CLEAR THE STICKY CHROME, and the chrome heights are
  MEASURED, never guessed** — fitZoom writes `--masthead-h/--tabbar-h/--chrome-h`
  CSS vars each pass (the tile wraps, so they change); the tabbar, build tile
  and the sticky ⓘ detail card offsets all read them. The card at top:10px slid
  UNDER the chrome and read as "the set info is missing" (Joel, 2026-08-03).
- **Every character carries the game's SEVEN slottable inherents** (Brawl,
  Sprint, Rest, Swift, Hurdle + Health, Stamina) — `ensureInherents()` grants
  client-side in recompute, SOLVER-NEUTRAL because `_is_no_enhance_inherent`
  caps the utility five to hand-placed set pieces (a Celerity +Stealth in
  Sprint survives; the ILP can never add). Autos count in totals; Sprint/
  Brawl/Rest do not. ⚠ The grant is SINGLE-FLIGHT with a post-await re-check —
  concurrent recomputes raced it into Brawl×2/Swift×3, and a self-heal drops
  duplicates a save may have persisted.
- **Characters get NAMES.** autoSaveTick used to invent "{primary} {Archetype}",
  so two Blasters with the same sets were indistinguishable. Autosave now only
  UPDATES an already-named character; saves carry `plan.named`; old auto-named
  ones still open and are nudged (narrow test: only the exact string autosave
  would have produced). Closing prompts to save; launch reopens the last one.

## 🧱 STRUCTURAL BALANCE on Powers & Slots (Joel, 2026-08-04, FINAL — 29cc3bbc supersedes the packer)

**⛔ NO PANEL PACKER, EVER AGAIN.** packPowersTab (and balanceColumns before
it) moved whole panels between two competing columns — Joel's verdict after
one evening of see-saw: "Instead of finding balance you moved… content to
the right, now the left has a big empty space. Please stop wasting tokens
on terrible design ideas." A mover can only RELOCATE a void. The battery
now pins that no packer function exists.

The layout is STRUCTURAL: (1) two-column region ends with the wall —
builder+catalogue left, assistant + epic/incarnate plan right (side's last
tile stretches to the shared bottom edge as grout); (2) below it,
**.pw-cardband** — Accolades / ⌨ In-game commands (click-to-copy) /
🧬 Your inherent / 💠 How set bonuses stack — one full-width row of
equal-height auto-fit columns; (3) the reference slabs (trays, level plan,
converters), full width, content flowing horizontally; all folds default
OPEN (`_foldOpen`: absent = open, explicit closes remembered). The L50
catalogue banner is deleted (pointed at content on the same tab); the L35
epic gate stays.

## 🧩 LAYOUT MODE — the design tool, and the catalogue rulings around it (2026-08-04 evening)

**Joel's order: "make it so I can move each area and change its width and height
then have you check it and make the changes set."** Three evenings had gone into me
guessing proportions off screenshots. View menu or Ctrl+Shift+L; per-area toolbar;
native corner handle resizes; panel drags by its header and collapses; the draft
(sizes, hidden, panel position) lives in localStorage and survives recomputes.
**📋 Copy sizes for Claude** is the handoff — he pastes the JSON, I bake it into
style.css. It is a VIEW tool: the battery negative-controls that it never calls
recordEdit, saveProgress, a solve or autoSaveTick, and every CSS rule is scoped to
`body.layout-mode` so leaving restores the shipped layout exactly.

- **⛔ IT RESIZES AND HIDES. MOVING IS DELETED AND STAYS DELETED (Joel, 2026-08-04:
  "Let's remove all this moves functions, they are simply not working" — `c11c6c28`,
  −172 lines, pinned out of BOTH app.js and style.css by the battery).** Three
  shapes were built and all three failed him in one evening: HTML5 drag, then a
  12px ⤵ target, then whole-area drop targets. A legacy draft's `order` is dropped
  on read so old moves cannot re-parent anything. **Moving panels is MY job, in
  CSS, from his numbers and his word** — the tool's purpose is to hand me measured
  sizes, not to be a layout engine.

- **⚠⚠ HTML5 DRAG IS BANNED IN THIS APP, and the battery pins it out.** My first
  version told him to drag a ⠿ badge that was a CSS `::before` with
  `pointer-events: none` — ungrabbable, so *nothing* was draggable and every area
  read as "stuck inside its own box". Drag also **cannot scroll the page
  mid-gesture**, so an area could never be placed anywhere off-screen. Anything
  that needs a pointer gesture (the panel) uses POINTER events, which do work.
- **⚠ THE WHOLE ARC IS ONE LESSON: I shipped three mechanisms for the same feature
  in one evening and none of them earned its keep.** The right move after the second
  failure was to stop and ask whether the feature should exist, not to build a third
  shape. His answer, when it came, was to delete it — and the deletion is the
  version that works.
- **⚠⚠ TEST INPUT WITH A REAL MOUSE, NOT `dispatchEvent`.** Joel reported "I still
  cannot move any objects" on a build whose every path I had "verified" with
  synthetic clicks. Driven with the real pointer, the mechanism was fine and the
  AIM was the bug: the placing click had to hit another area's 12px glyph, and a
  click anywhere else did nothing with no feedback. Fix = **while holding, the
  WHOLE area is the target** (`body.lay-holding`, hover outline, click swallowed so
  it never reaches the app), and the buttons carry WORDS ("⠿ move", "⤵ here").
  Synthetic-event checks are the same defect class as verification theater: they
  only ever exercise the path I chose.
- **⚠ ESCAPE DOES NOT REACH THE PAGE in the frozen shell** — the app's own Escape
  handlers swallow it, and a capture-phase listener did not help either (measured
  twice with real key presses). Anything cancellable needs a VISIBLE way out: here
  it is clicking ⠿ move again, plus a ✖ button in the panel. Do not advertise Esc.
- **⚠ Clamp any REMEMBERED window position into the viewport.** The panel had
  drifted off-screen with a window that sat partly off-display, and its own ✕ is
  the only way to close it — an unreachable control is a trap.
- **⚠ An injected label changes the geometry being measured.** The toolbar is
  `position: absolute` for that reason. ⚠ And the two slabs whose renderers rewrite
  innerHTML (`#tray-out`, `#order-out`) EAT injected nodes — `refreshBuildViews`
  re-applies the draft, or 13 of 15 areas silently lose their toolbar.
- **⚠ NEVER resolve a container key by CSS class.** A stray `theme-hero` key
  matched `body.theme-hero` and would have appended five panels into `<body>`.
  data-lay or id only, and the target must be inside `#tab-powers`.
- **⚠ An absolutely positioned flex box shrink-fits and the label yields first**
  (every name rendered "le…"): `width: max-content` on the bar + `flex: 0 0 auto`
  on the label. Measured 16px → 84-164px.
- **⚠ The size snapshot is a `pointerup` scan of the inline styles the native
  handle already wrote — NOT a ResizeObserver.** The Claude pane fires no layout
  callbacks at all, so an observer here is code neither of us can test; I shipped
  one first and it recorded nothing.
- **⛔ MULTICOL ON `.cat-cols` IS REVERTED AND BANNED** (work order 2026-08-04
  3:11 PM, on Joel's annotated shots of `019b41f9`). Multicol assigns boxes to
  columns by HEIGHT, so it flows column-major and stacked Primary under Secondary;
  the catalogue's premise is ONE POWERSET PER COLUMN, side by side, the way the
  game shows them. It also never bought the flat bottom it cost that for. The
  battery pins the grid rule in and `column-width: 210px` out.
- **⚠ A grid item with a DEFINITE `grid-row` is placed BEFORE the auto-flow items.**
  `grid-row: 1 / -1` on the two cards put them in tracks 1-2 and shoved the Primary
  powerset to track 3 — the same reading-order damage. They live in `.cat-side`, a
  stretched flex sibling of `.cat-cols`, instead.
- **📐 THE ONE-ROW ARITHMETIC (measured, and it is why the gate's flat-bottom test
  cannot pass beside the wall):** 7 powerset boxes at the 190px track minimum need
  ~1400px of the 1480 available at his window; each card needs ~400px to stay short
  (measured: 203px wide → 486px tall, 399px → 254px, 924px → 165px, against a
  tallest column of 290px). 1400 + 800 does not fit. Wall bottom spread at 1920:
  cards stacked beside the wall 315px, side by side 498px, **full-width strip
  101px**. The strip is the only arrangement under his 120px bar and the only one
  that keeps the wall at one row — **and it reverses the `019b41f9` intent, so it
  is HIS call, still pending.**

## 🧱 (superseded) THE PERFECT WALL packer (2026-08-04 night, 472a76a3)

"Open all the drop downs on the first tab, then move the items around until
they fit into a perfect wall with zero gaps any where." The architecture:
- **All folds default OPEN** (`_foldOpen`: absent key = open; explicit closes
  remembered). The wall is judged with everything expanded.
- **packPowersTab()** seats the two COLUMN TILES (#endgame-plan-panel,
  #endgame-panel) into whichever column is currently shorter — measured
  live, on render/recompute/toggle/resize/tab-arrival (hidden tab = zero
  geometry, skip). The balanceColumns lesson: measure, never predict.
- **BASE SLABS**: trays, level plan, converters are giant references — in a
  column any one strands a void. They sit FULL WIDTH under the columns where
  their content flows horizontally (the wide-brick CSS: the 24-row respec
  order becomes a 5-across course). ⚠ Found twice the hard way: conv guide
  first, level plan second — a "tile" taller than everything else can never
  be balanced; promote it to a slab.
- **GROUT**: each column's last tile stretches to the shared bottom edge
  (`.powers-main/.powers-side > :last-child { flex: 1 0 auto }`) — the
  residual discrete tiles can't split is panel surface, never raw page.
- The builder flex-stretch rule is DELETED (it painted the void); the 3-up
  fold row is gone; accolades are a free tile in index.html again.

## 🧩 Layout: tiles, never a scrollbar (Joel's ruling, 2026-08-02)

- **⚠ NEVER cap the rail with its own scroll.** It removed 1745px of dead space
  and he rejected it on sight: *"there is no desire for a scroll bar in the middle
  of this app."* The battery negative-controls this — `overflow-y: auto` or
  `max-height` back on `.rail` fails the build.
- The fix is his: *"think of the spaces on the left as tiles that can be shuffled
  to make it all balanced."* `balanceColumns()` places `_TILES` in whichever
  column minimises page height and side-to-side difference, **measured live** —
  tile height depends on column width, so arrangements cannot be predicted.
  Measured 1900×1150: imbalance 1745px → 275px. Whole tiles are the unit, so 275px
  is the floor until a card is split internally.
- **⚠ The Assistant's slot is ABOVE `#builder`, never below** — it was moved to
  the top of the rail on 2026-08-01 after a field report could not find it at 78%
  down the page. A balancer must not undo a placement someone complained about.
- **⚠⚠ THE CLAUDE PANE FIRES NO LAYOUT CALLBACKS AT ALL** (measured): no `resize`,
  no matchMedia `change`, no ResizeObserver — not even the initial observation,
  not even for a width change forced in script. Same class as its 0×0-viewport
  geometry blindness, and it cost a wrong diagnosis (I called a working resize
  listener broken and rewrote it). **Always `resize_window` first** — at 0×0
  `elementFromPoint` returns null and every hit-test reads as a pass — verify the
  FUNCTION by calling it directly per viewport, and treat event triggers as
  unverifiable here.

## ⭐ CURRENT STATE & open queue (2026-07-31)

**Nothing is running; no scheduled tasks armed.** Shipped v0.12.30 "Accuracy pass".
The live handoff detail is `coh-builder/RESUME-HERE.md`; the entries below are the
standing record of how the engine-accuracy batch was done.
**✅ SHIPPED 2026-07-31 evening (Joel accepted both on sight):** the **four-way
alignment** (3d62f4fa + eb1aa204 — 🦸 Hero / 🛡️ Vigilante / 😈 Rogue / 🦹 Villain,
header picker + four entry cards; the middles are a **third THEME**, a peer of
theme-hero/theme-villain with their own `--bg`/`--panel`/`--accent`, sharing the
Journey's amber `#e0a63c` so the app and the 1-50 road agree; build-neutral proven
end-to-end with a negative control) and the **archetype emblems** (e99524e1 +
59e25203 — the game's own art on the Build panel and the saved-character rows,
15 of 15 archetypes resolving).
⚠ **`#masthead` carries an ID and outranks `body.theme-x header`, so the themed
header gradients + 2px underlines have NEVER rendered on hero or villain.** The
middle rule is scoped to `body.align-mid #masthead` to win; the other two are left
DEAD on purpose — reviving them changes both shipped themes, which is Joel's call.

**▶ OPEN, in Joel's order:** (1) ~~verdict-gate legality hole~~ **CLOSED
(07ce596e + tools/test_verdict_legality.py — legality outranks score, all four
branches, fail-safe on unmeasurable)** · (2) Iron Man accolade grant (Joel's
in-game look) · (3) origin plates extracted but unplaced (~~i24 glob bug~~ fixed
7a67c48c, see pitfalls) · gaming box silent since 2026-07-29 11:51 · drafted
forum/Discord posts unsent · reduced-motion, exploration-log parse,
strict-dominance experiment.

- **🔧 ENGINE-ACCURACY WORK ORDER: ITEMS 1-4 DONE (2026-07-30 morning; commits
  4c9243cc · 9de25d30 · 9025dee8 · e4d63760 — details in session-report).**
  (1) The user-facing validator now checks POOL prerequisites, not just Epic
  (`_epic_prereq_errors` widened; proof = `tools/audit_pool_prereq_validator.py`,
  both arms through the real /build/validate route, negative-controlled; its
  `--champions` re-derived the 12-of-24 illegal list independently — matches §1.1).
  (2) `reality_check_prereqs.py` RE-BASED on the requires EXPRESSION the game
  executes; prose = corroboration only; the "no sentence means needs 0" default
  is DELETED. **Full accounting is enforced**: every one of our pool/epic powers
  either game-verified or named in `tools/prereq_unmatched_dispositions.json`,
  hard-fail otherwise (Joel: "knowing all, not just most"). Baseline regenerated
  EMPTY (was 8 prose-era entries); gate interface unchanged for converge_parallel.
  (3) Bridge 9→12 pairs + display-identity resolver rung → **prereq coverage
  467 of 467, all from the expression, zero held** (was 413/472); all 54 new
  counts equal the proxy's — ZERO enforcement movers. (4) §1.6 disposed (see the
  Naming section — Scrapper Mace removed, Fly_Boost deliberately absent).
  Also fixed: the standing gate was RED at HEAD (pre-existing) — lone-HO
  Ribosome in an armor toggle had no `_slot_plan` note; HO branch added, 23/23.
  Verification stack: 467/467 · gate OK · 273/273 · 23/23 · epic-tiers clean ·
  autopick legality 2,691/2,691 (re-run because Scrapper eligibility changed).
  **✅ ITEM 5 RULED AND IMPLEMENTED (aea7e1fd, same morning).** Joel's rulings:
  tie-break = what the user chose the build for, ROLE always the focus; fix =
  (b) the TWO-STAGE solve; "never assume we need a re-cert — always check
  whether the change justifies it" (STANDING RULE); endurance recovery ranks
  first among tie-breaks, then DPS (damage) / survivability (tanks). Design:
  `C:\Users\joelc\code\plateau-fix-paper.md`. Implementation: `_ilp_pass`
  step 2 re-solves among tied optima (step-1 optimum = hard floor constraint;
  failed step 2 restores step 1 verbatim; HC_TWO_STAGE=0 = A/B seam). NOT a
  model bump — canonical scores stay comparable (Piece 3 family). Battery
  test_plateau_twostep.py 5/5 (tie pin, floor negative control, cushion,
  recovery-never-worse, kill switch); gate 23/23, HO/proc/pet green. ⚠ Step 2
  is an ADDED solve: spot A/B 0.5s→1.9s, identical step-1 outcome — the trade
  is tie-correctness for wall time; the paper's original "speed win" hope was
  WRONG and is corrected in the paper. **📊 MEASUREMENT DONE (911d998b,
  tools/measure_plateau_ab.py — solve-level A/B, all 24 contexts, both arms,
  ZERO floor defects):** recovery-first (Joel's ordering) = 12 up / 5 down /
  3 flat, median +1.31%, range −20.3% (Blaster Fire/EM) .. +61.9% (Warshade
  itrial); role-first comparison arm = 7/8/4, median 0.0% — **Joel's ordering
  wins on every axis and stands.** Honest negatives: 3 outliers (Blaster
  −20.3, Battle_Axe/FA −9.5, Stalker Rad/Dark −7.2 — linear proxies can't see
  procs/chains that fp prices) and cost 3.15× ILP wall (up to 9× per solve).
  `HC_TS_REC_W` = measurement seam for the recovery dominance.
  **✅ NEGATIVES CLOSED STRUCTURALLY (7820d06a, Joel's "fix the honest
  negatives"):** no static tie-break weighting survives fp (measured 3-way:
  each fixes one outlier, breaks another — no more weight tuning, ever). Fix =
  (a) tie-break STYLES per-call on solve_ilp ("eps" = tie-preference folded
  into step 1, HC_TS_EPS cap 0.001, measured 1.05× = FREE, outliers bounded
  −4.6%, the DEFAULT everywhere incl. sweeps; "lex" = the two-solve step 2;
  False = plain) — per-call param, never env (sweep pool is threaded);
  (b) **deep_optimize FINALE solves the winner under every style and PHYSICS
  picks** (cert["tie_arbitration"] records arms) — committed champions never
  worse than any style by construction, cost 2 solves per CONTEXT.
  **🐌 SLOW-BUILD DIAGNOSIS COMPLETE:** sweep counts uniform — per-solve cost
  is the whole story; eps FALSIFIED the degeneracy-collapse hypothesis (1.05×,
  not <1×) so plateau bound-proving is INTRINSIC; the remaining measured lever
  = the 30-40% PuLP rebuild/MPS-I/O overhead → in-process CBC (python-mip),
  ⚠ a NEW DEPENDENCY in the shipped client — Joel's call before any port.
  ⚠ Battery lesson: eps makes re-solves REPRODUCIBLE — the v35 lock check's
  "others changed" witness died of it; now locks a MANGLED slotting instead
  (byte-identity proves the lock overrides the optimizer). All batteries
  green. ⚠ RETRACTED same day: "CBC tie choice varies under CPU load" — the
  observed drift was (a) three concurrent measurement copies interleaving
  writes to one output file and (b) LEARNING CARRYOVER: any deep_optimize
  probe warm-starts from HC_CHAMPIONS_PATH and appends to the REAL
  exploration log, so back-to-back probes on one context are NOT independent
  — isolate scratch paths PER ARM and run separate processes, or the ladder
  measures learning, not the variable.
- **✅ NO-SHORTCUTS AUDIT (8d676076, Joel: "make sure we did not take
  shortcuts that will undermine the accuracy"):** three holes found+closed —
  (1) the eps floor is now a STANDING battery check for BOTH styles
  (discrete-gap fixture, exact); (2) the lock check regained the
  "allocated empties stay empty" half (mangled slotting carries an explicit
  None; empties = the None entries in the incoming list, NOT derived from
  earned); (3) **serve-time /build/solve now physics-arbitrates too** —
  generated/full-re-slot solves with a scorable objective run the plain arm
  and fp picks (preserve/keep-layout/perk-chip skip; ~2× solve seconds).
  Gate grew check 24: both arms RAN and the arbitration swallow did NOT fire
  — silent death is the failure mode, and this check caught a real NameError
  pre-ship. Gate 24/24 · plateau 6/6.
- **🧾 MOVERS WAVE (2026-07-30 afternoon — Joel's ruling mid-run: this is the
  FIRST TRANCHE OF ITEM 6, never "just a test"; a same-cost rehearsal of
  certification is a waste — the cheap instrument answers "did it move", the
  next spend goes to the REAL artifact):** 6 mover contexts, --recert, eps
  solver + arbitrated finales, launched detached 12:34 PM, paused clean 4:05
  (armed pre-departure), 5 banked; Warshade resumed on Joel's "continue"
  (4:54 PM, distinct prefix abmov_ws per the collision rule) and converged
  in 88.6 min. **WAVE COMPLETE 6/6 — verdicts (recert_verdicts.json 18:25,
  regenerated with ALL six shards — ⚠ the tool OVERWRITES per invocation,
  always regenerate complete before any merge): 2 SUPERSEDE (Night_Widow
  +99.3 · Blaster Fire/EM +6.3) / 4 KEEP (Broad_Sword −180.8, Warshade
  −352.0, Stalker Rad/Dark −304.6, Battle_Axe −551.0 — gate held).**
  Notable, both directions: the Blaster (worst solve-level outlier, −20.3%)
  SUPERSEDES converged; the Warshade (+61.9% solve-level) KEEPS —
  single-solve tie deltas predict NOTHING about converged outcomes; the
  sweep+arbitrated-finale decides and the verdict gate protects the roster.
  ✅ MERGED on Joel's word (73aaab77, evening): Night_Widow + Blaster by
  context via --verdicts; all abmov shards retired (.merged /
  .kept_incumbent); validate_champions exit 0, both new champions SERVED.
  **✅ ITEM 6 COMPLETE (2026-07-31): 24 of 24 contexts re-certified under
  the new solver across both tranches — **8 SUPERSEDE / 16 KEEP**, all
  supersedes MERGED on Joel's word (73aaab77 movers, ed03df77 remainder).
  Remainder wave 18/18: PB nova +391.2, Crab +248.9, Poison/Sonic +131.6,
  WS dwarf +85.6, Sentinel Fire/WP +77.7, Rad/Sonic +55.9; PB dwarf ran
  last (101.3 min) and KEEPS. Supersedes CONCENTRATED in form-locked
  Kheldian + VEAT contexts — the tie-break work earned its keep.
  All shards retired .merged_2026-07-31; validate_champions exit 0.
  ✓ MERGE SAFETY, VERIFIED not assumed: workers write ONLY their own shard
  (HC_CHAMPIONS_PATH, converge_parallel:183), never champions.json — so a
  merge is safe while a worker runs; and merge_champion_shards filters
  PER CONTEXT against --verdicts, so MIXED shards need NO manual splitting
  (it prints 'KEEP incumbent' for each non-superseding context).
  ⚠ The gaming box has NOT woken since 2026-07-29 11:51 (no heartbeat,
  orders unclaimed) — check it before the next wave counts on it.
  **▶ OPEN: box health · optional strict-dominance solver experiment ·
  release still HELD (Mids export fix + slotting batch staged Unreleased).** Cheap win parked: exploration-log parse.
- **🧾 v38+HO WAVE COMPLETE 24/24 — ✅ MERGED (superseded by the 2026-07-31 recert above; kept for the deltas).** `recert_verdicts.json` (written 2026-07-30 00:10): **4 SUPERSEDE** (Crab_Spider_Soldier +181.3 — this also CLOSES the named autopick defect that failed every leg of the previous wave · Spines/Fiery_Aura +92.4 · Poison/Sonic_Attack +50.9 · Broad_Sword/Super_Reflexes +4.1) / **20 KEEP**, zero collapsed runs, zero eval failures. The gate re-scores BOTH sides fresh under v38 (canonical vs canonical, CBC pinned) so the deltas are real; a mostly-KEEP outcome is the NORMAL shape of a recert wave (the prior wave was 3/20), not a defect. Large negatives cluster on Kheldian per-form contexts, where the form context BANS powers the incumbent build holds — the recert searches a strictly smaller space and cannot win by construction. **Merge = by context, `--verdicts`, canonical winner kept, shards retired `.merged_2026-07-30` — awaits Joel's word.**
- **Wave-run history worth keeping:** ran across the laptop + gaming box; the box was stopped mid-order and its 2 finished champions came home via the new orphan-rescue (2505c2a0) rather than being lost. Drop-dead pauses fired clean twice (4:10 PM, then armed 6 AM). ⚠ `bench_solver_e2e` running beside the wave killed 10 in-flight contexts — several hours of compute, nothing corrupted; see the speed-ledger guard warning.
- **⚠ MY OWN ERRORS THIS WAVE, recorded so the pattern is visible:** quoted a per-solve solver ratio (2.65×) as if it were end-to-end (really 1.2-1.7×); quoted a pre-fix 484 min as current (really 261); inflated the banked count by 2 by incrementing from monitor events instead of counting the shards; read a docstring's history as current state and wrongly declared a healthy wave's premise broken. **Common thread: passing along a number without checking what it measured.** Count from the artifact, not from the narration.

### Carried forward (2026-07-27 night)

- **Latest release: 🚀 v0.12.32 "The Stats page becomes a workbench"** (published
  2026-08-06 23:02Z on Joel's "Cut 0.12.32"; signed, API-verified, both assets;
  installed copy mirrored to `e164fd1` and relaunched; the 0.12.31 signed
  installer was NOT overwritten). ⚠ Announcement post drafted and handed to him
  in chat, **not yet posted to topic 64761**. ⚠ Its badge sentence was corrected
  before publishing: it claims only that `/thumbtack` is the command the client
  registers for placing a minimap marker, never that the marker lands as
  expected — nobody has confirmed that in game, and Joel said to skip the check.
  Superseded entry kept for the ledger: **v0.12.31 "The desktop app"** (published 2026-08-05 8:35 PM ET on Joel's thumbs-up after his review walk; signed, API-verified, both assets; installed copy mirrored to the release build b2161e1 and relaunched). Superseded entry kept for the ledger: **v0.12.30 "Accuracy pass"** (published 2026-07-31, signed, API-verified; model v38, data currency 2026.1.1242). It carried the whole held batch: display units, honest panel headers, scale/target data patch, model v37 target-aware scoring, v38 pet hit chance, solver HO options, the proc-vs-set trade note, and the 8 superseding champions. **hero-companion.com is live** (see Standing watch).
- **✅ THE 2026-07-28 RELEASE HOLD IS DISCHARGED** — everything staged under Unreleased shipped in 0.12.30. The standing rule that survives is the ordinary one: nothing publishes without Joel's say-so, changelog entries stage under "Unreleased" until he approves.
- **⚠ 0.12.30 caught a real defect on the way out, and it is NOT fully closed:** 8 of 24 bundled champions could not be built in game (Wall of Force / Misdirection / Weave held with one pool power where the game wants two). The verdict gate had "kept" them because **it compares SCORE ONLY** and the illegal incumbents outscored their legal replacements. Joel's ruling: **legality outranks score.** The champions were fixed (gold 16/24 → 24/24 SERVED) but **the verdict gate still has no legality dimension** — close it before the next wave.
- **Joel's hand (post-0.12.29):** FP/whitelist submissions, gaming-box install acceptance, tray relaunch (BD watch), forum announcement (draft in session-report; "thirteen times" tally verified).
- **▶ ACTIVE BATCH (Joel's pick 2026-07-28, re-orders the queue): SLOTTING-JUDGMENT REMAINDER.** Paper = `C:\Users\joelc\code\slotting-remainder-paper.md` (plain-English per his flag: every new number ships with its explanation + a tour card). **✅ RULINGS R1-R3 ANSWERED (Joel, 2026-07-28 afternoon):** R1 = an unpinnable pet fact HOLDS its sub-piece with an honest label (Fury's "shown, not yet scored" pattern), no log hunts by default. R2 = champions may use HOs **only in endgame content presets (itrial, farm)**, every HO carries an attain note ("from Hamidon raids or merits"). R3 = **MOOT AND DEFERRED — Joel: "we have not had a real scale or choice to pick cheap over expensive builds in a long time"** (the tier dial exists in solver.py:920 but every API path defaults premium); HOs are gated by R2 alone, NO per-tier HO rule; "make budget/balanced/premium a real player choice again" is queued as its own future item — do not resurrect R3-as-posed. **✅ PIECE 1 SHIPPED (2d8dbca9, staged Unreleased): the proc-vs-set trade explains itself.** proc_pass records `_proc_trade` (kind bomb/hybrid/anchor/ff + displaced slots; fresh pass clears stale notes on unlocked powers); engine `_offense` emits the display-only ledger (proc_dmg/proc_n/proc_per + trade_* — displaced pieces priced by the same enhancement math, invariance proven byte-identical); ⓘ card renders one sentence per kind (a −res anchor in a non-damage toggle renders from the power record — no offense row exists); tour step 57 "Why these enhancements" (key `proc-why`, the note's ? deep-links to it); tools/test_proc_trade_note.py = 8-check battery (negative control, invariance, real /build/solve route). NOTE: **pet accuracy is now v38** (the paper's "v37" was taken by target-aware scoring); the paper's role_output caster-penalty question was already answered/fixed in v37. graphify-out/ now gitignored (derived). **✅ PIECE 2 SHIPPED (8aec988d, staged Unreleased): MODEL v38 pet hit chance.** All four facts pinned (NO R1 hold needed): pets roll like PLAYERS (wiki Attack Mechanics "Pet Accuracy" — 75% base table, rank acc 1.00), MM tiers −2/−1/−0 at full count (wiki Mastermind, count-gated; bins structurally silent), Levelminus pets client-pinned (patch_summon_level_shift 474/474), inherent accuracy client-pinned (patch_pet_accuracy 529/559, Incarnate_Pets/Redirects named exclusions), Supremacy ToHit = **7.5% as table-priced** (0.1 scale × MM table), Tactics routes, Focused Accuracy excluded. Citations: docs/pet-tohit-sources.md. Structural: pet DPS outside my_dps (meter exemption structural; no hasten elasticity on pets; end_factor whole — stated). PP/base tables extended +6/+7 (wiki Purple_Patch). Display: per-pet "fights at −N"/"acc ×M" tags + pet ToHit list + retired always-hit apology; tour support-note rewritten; help.md "How pet damage is counted". Batteries: test_pet_hit_v38 7/7, Piece 1 regression 8/8, gate 23/23, tour 8/8. **⚠ MM/pet-controller champions NOT recerted yet — the ONE combined wave runs after Piece 3.** ⚠ wiki fetch route: Chrome-MCP Edge tab works (bot-check auto-clears); pane and urllib both dead. **✅ PIECE 3 SHIPPED (237fafdf, staged Unreleased): solver proposes HOs.** Search capability, NO model bump: `_options_for_power` offers armor-toggle HO options (synthetic single-piece sets: no bonuses/sigs, stackable, rank 0 per R3-deferred), engine-ED-priced server-side (`_ho_solver_pieces` from _special_accepts legality + piece_boosts; ⚠ DIRECTION GUARD: DeBuff pieces' Defense aspect never credits armor). Gate `_HO_CONTENTS` = {itrial, fire_farm, farm_afk, farm_active} (R2), threaded via `_assess_solve(content=)` + build_solve/headroom/deep_optimize — champions inherit per-context; any other content ho_pieces=None = byte-identical solve (battery-pinned). Attacks/holds keep v27 proc-pass HO cores. Attain note on EVERY ⓘ-card HO (ILP/proc-pass/hand) + tour step 59 `ho-why` (picker scene) + help.md paragraph. Battery test_ho_solver.py 6/6 (farm solve placed 2 Ribosomes unprompted — 3 HOs = 6-piece res enh in half the slots, ED 0.2/0.4/0.56); all regressions green. **🧾 WAVE COMPLETE 23/24, VERDICTS READY (2026-07-29 morning): 3 SUPERSEDE (Water/Kin +319.2, PB nova +162.3, WS dwarf +132.8) / 20 KEEP, zero collapsed — TABLE WITH JOEL, merge awaits his word** (recert_verdicts.json + verdicts_v38ho.log; merge = by context, --verdicts, retire shards .merged). **⛔ 24th context = NAMED DEFECT: Crab Spider Soldier AUTOPICK emits a ladder-ILLEGAL 26-pick seed** ("seed cannot be made pick-legal", zero pins; _assign_pick_levels concurs; failed instantly EVERY wave leg — the "in flight for hours" read was wrong, buildout's TypeError crash masked it, now fixed to report score-NONE). ⚠ Autopick feeds the WIZARD → likely user-facing VEAT bug (two-phase branch vs pick ladder suspected). Harden-before-certify: NO recert attempts for this context until fixed; incumbent (canonical 1691.19) stands. ⚠ Stale champions_shard_par_p0 (canonical None) queued for .merged retirement. Fleet splitter SHIPPED (tools/remote_worker/split_wave.py); scheduled-pause log appends now (the 6:10 pause DID fire, result 0 — its log was clobbered, not its run). Wave history: (launched 2026-07-28 11:35 AM ET): scope finding — ALL 24 certified contexts are itrial/farm content, so the whole roster re-converges ("Run V38 HO Wave.bat", 6 workers × 4 contexts, node cap 50000, shards champions_shard_v38ho_p0..p5, NO --merge; launcher task unregistered after process verification; stale par_/v34/v36 root shards = shadow-blocked pre-existing condition, untouched). **⚠ champions.json + shards belong to the wave process until it completes (~2.5-4 h est).** THEN: recert_verdicts/evaluate_first per context → **VERDICT TABLE TO JOEL BEFORE any champions.json merge** → merge by context with --verdicts, canonical winner kept, shards retired .merged_2026-07-28. Fact-hunt details (2026-07-28 evening checkpoint — session-report): Fact 4 PINNED (Tactics buff_effects ToHit projects / Focused Accuracy self-only excluded / **Supremacy carries +10% ToHit buff the v34 lever deferred**); Fact 3 PINNED (14 pet-set Accuracy pieces; copy_boosts routes, same as Damage); Fact 2 half-pinned (client per-attack `accuracy` field swept, 559 files, 1.0–1.2; base 50% held; MISSING the critter attacking-UP level ladder); Fact 1: **bins SILENT on MM henchman tier level shift** (all 8 sets × 3 tiers = `Ranged_Ones`, no offset; entity defs level-less; Controller pets DO encode −1 via `Ranged_Levelminus` — Fire Imps pinned) → server-engine behavior, R1 hold-with-label unless wiki-cited. ⚠ homecoming.wiki now 403s tools/fetch_zone_pages.py too (not just Anthropic's fetcher); ⚠⚠ **the in-app browser pane CRASHED Claude desktop 2× opening homecoming.wiki — use Claude-in-Chrome (Edge) for that site, never the pane.** **✅ R4 + BOTH DATA PASSES DONE 2026-07-28 morning ("fix all these", b230c8dc, staged):** patch_effect_scales_targets.py (client = sole authority) → exactly **2** ×100 records normalized (Shock family; movers = ZERO, no champion slots them), **1452 targets back-filled** (engine panels skip target==Self — Absorb Pain caster penalty no longer an "ally buff", save-verified), 1187 scales confirmed exact, **drift measured not touched: 264 multi-template + 1635 table-name mismatches = the reconciliation lane's hard numbers**. Display units (staged): Heal/Absorb/HitPoints→HP BY EFFECT, Endurance→end points; headers "all your powers applied once, unenhanced" (R4a). Probe = tools/probe_display_magnitudes.py (26 residual flags = legit sums). **✅ Scoring question ANSWERED + FIXED = MODEL v37** (abs() was crediting caster penalties as ally buffs; Self rows skipped; ZERO champion movement proven). **✅ RECONCILIATION PASS (91921fcf): vocabulary corrected (client slow attribs = RunningSpeed/FlyingSpeed/JumpingSpeed/JumpHeight), confirmed 1787, targets 1841, 3 one-to-one value syncs (Jolting Chain ×2, Blood Widow Poison Dart; zero champion exposure). ⚠ Sync rule guard: our side must have EXACTLY ONE row — the unguarded draft multiplied client values onto every flattened row (Lightning_Strike 4× overcount, caught pre-commit). RESIDUE FULLY DISPOSITIONED (6720c191, tools/classify_unmatched_effects.py = the lane's instrument): 761 pseudo-pet folds + **230 REDIRECT folds PROVEN by twin value-match (Zapp-class: player records are zero-template stubs, effects live on pets/*_normal|_quick twins — fold correct by design)** + 167 stub-class (twin naming unknown) + 26 grant/revoke = by design; **✅ 293 CLOSED (ac08d084): EV/pv census 293→135 hard; tools/patch_family_rebuild.py REPLACED the hard groups with client-template flattenings (69 groups / 225 rows / 63 powers, `rebuilt_from_client` marked, idempotent); absent-family side = +92 set-entity + +317 weak-proof entity folds (Storm Cell class under pets/). ~~IRREDUCIBLE CORE = 8 rows: Chrono_Shift Regeneration ×4 AT variants, values match nothing client-side (suspected Mids pre-enhanced bakes)~~ **CLOSED 2026-08-07 — see the PvP-variant entry in Recurring pitfalls. They are neither irreducible nor bakes: pv_mode 2 (PvE-gated) and exactly 5.33× the client's own timed heal scales.** MOVERS ZERO, triple-checked (scanner sanity-verified, 624 picks; Water/Kin Transfusion = Corruptor variant, client-confirmed).** Piece 1 (per-attack proc-vs-set display) is UNGATED and builds first; Pieces 2 (pet accuracy = v37, his own option-B deferral coming due; MM+pet-controller recerts) + 3 (solver HO options — search capability, NOT a model bump) build behind rulings; ONE combined certification wave at the end.
- **✅ REMOTE WORKER KIT BUILT (f34549b0, 2026-07-28 evening — tools/remote_worker/, README is the authority):** the gaming box crunches, the laptop conducts from anywhere. OUTBOUND-ONLY (Joel asked about internet accessibility — the box needs NONE: it polls `%OneDrive%\HeroCompanionCompute` for orders and git-fetches the public repo pinned to the order's commit; no ports/tokens/inbound; LAN IP irrelevant to operation). send_work refuses unpushed commits; the box verifies the checkout; box NEVER merges — laptop verdict gate only. **✅ INSTALLED ON THE BOX 2026-07-28 evening** (Joel ran install-worker.bat: clone + deps + mailbox + HC_RemoteWorker task all verified; box runs Python 3.11.9 via the 3.13→3.11→PATH ladder; canonical scoring stays laptop-side). **The box is an i9-9900K @ 3.60GHz — 8 cores / 16 logical** (Joel's exact spec; laptop = 32 logical, so the laptop stays the bigger single engine and the box adds ~50% fleet capacity); orders may omit `workers` (auto-sizes to the box's cores → 3 workers there, 1596b6ce). **🎉 MAIDEN RUN VALIDATED END-TO-END (wave-20260728-193746, 2026-07-28 evening):** box claimed via OneDrive, verified pin 07483a67, crunched the Spines/FA farm_afk context in 25 min (converged, 34 sweeps, no truncation, exit 0), returned shard+logs+DONE manifest. Shard = VALIDATION-ONLY, left in results/, never collected to root (⚠ in-run 377.5 is NOT comparable to the laptop's in-run 302.0 — within-run ranking only; canonical is the only portable number). Maiden #1 (192056) FAILED loudly as designed — dirty-check counted untracked files (the tick's own log); fixed 07483a67, box pulled by hand once (future updates ride each order's pin). ⚠ Observed claim latency ~7-10 min (OneDrive legs + 5-min tick); "Always keep on this device" on the mailbox folder recommended, tick can go 1-min via `schtasks /change /tn HC_RemoteWorker /ri 1` if ever wanted. ⚠ GitHub sign-in is NEVER needed on the box (public repo, anonymous read; a stray "Continue with Google" GitHub account got created during setup — harmless, Joel may delete). Retire: `schtasks /delete /f /tn HC_RemoteWorker`. · make budget/balanced/premium a REAL player choice again (Joel's R3 answer — the dial is vestigial; UI + honest cost story; its own item, not part of this batch) · Leveling Companion batch (shares the Journey surface) · Fury meter class (Fury/Rage/Domination/Defiance/Gauntlet — silently absent; no public Brute damage absolutes until then) · pricing #31 (single-claim pairing) · 18 inherent icons (optional) · i24 archive content (Joel's torrent hand) · alias-map roster reconciliation + Power Boost amplifier effects (parser allowlist family) · Maelwys leftovers (CJ-vs-Weave slot modeling, attack-card wording awaiting Joel's text) · **Lite is at 0.1.18** (⚠ notes saying "0.1.17 next" are stale).

## Session history & retention

- Claude Code transcripts live under `~/.claude/projects/` (`C--Users-joelc-code` = main). Distilled memory files: `~/.claude/projects/C--Users-joelc-code/memory/` (MEMORY.md index + per-topic files) — richest cross-session source.
- `cleanupPeriodDays` set to **3650** in `~/.claude/settings.json` (2026-07-08); earliest surviving transcript is 2026-06-16.

## graphify — this is where the accumulated mass belongs

**Joel's framing (2026-07-30):** graphify's premise is to make a large, long-lived
codebase approachable WITHOUT this file becoming the dumping ground. When a
section here starts wanting paragraphs of detail, that detail belongs in the
graph, in git, or in session-report.md — and this file keeps the ruling only.
⚠ `graphify-out/` is gitignored (derived); regenerate rather than commit it.
⚠ Strict mode blocks raw Reads until one query has run in the session — that is
by design, satisfy it with a real question rather than a token one.

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
