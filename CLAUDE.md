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
- **⚠⚠ COMPLETE, THEN BRIEF (Joel, 2026-08-10: "Stop giving me incomplete and
  overwhelming threads of responses. You are literally wasting my tokens by
  performing an incomplete request. And I am not reading the Iliad and Odyssey
  just to check your work.")** Finish the WHOLE request — including the
  follow-through a finding demands (an audit that finds a red row FIXES the
  row, it does not report it) — before writing anything to chat. Then the
  10-line protocol taken literally: outcome, one proof reference, what is his.
  Never hand back a partially-executed thread or enumerate middle steps.
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

- **PATCH-WATCH (public promise, posted round-5 correction 7(a); wired 2026-07-17).** Trigger: any Homecoming patch announcement, or Joel's word. Steps, in order: (1) full Bin Crawler re-export from `C:\Games\HC2\assets\live`; (2) structural diff vs current data — `tools/reality_check_effect_structure.py` (effect existence/enhanceability, the gap class scalar checks can't see) plus the scalar reality checks; (3) `tools/reality_check_missing_powers.py` - what is genuinely NEW content versus what merely moved NAME (added 2026-08-08 after "459 missing powers" turned out to be 32 and 19 renames); (4) delta report to session-report.md; (5) **movers ruling BEFORE any certification run starts** — harden-before-certify applies in full. Release procedure addition: release notes state **data currency** — the date of the last client re-export vs the game's latest patch. **After any client re-export, also re-run the power-icon pipeline** (extract_power_icons → patch_power_icons).
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
- **INBOX_READ_TOKEN expires 2026-11-11** (the Pulse render's read-only PAT, named `pulse-board` in Joel's GitHub fine-grained token list, rotated 2026-08-13 — the prior token died 2026-08-13 despite a recorded 2026-10-12 expiry, so trust the mint date + 90 days, not old notes; rotation is a 5-minute chore per docs/pulse-pipeline-runbook.md; the render workflow self-warns within 14 days).
- **MRB v4 alpha/beta**: keep .mbd import/export compatible as the format moves (public promise to Jacke).
- **Artifact Signing identity revalidation expires 2027-07-15** (Azure Trusted Signing, account `herocompanionsign`). A lapse HALTS all signing. Portal → the signing account → Identity validations. Facts + prereqs: docs/signing-runbook.md; signer: tools/sign_artifacts.py (needs `az login` + "Artifact Signing Certificate Profile Signer" role + `TRUSTED_SIGNING_PROFILE=hero-companion-public`).
- **Unrelenting Fury stack cap — UNRESOLVED DATA CONFLICT (2026-07-16, v33 ruling C).** Template says `stack_limit 2`; the piece's help text says "stacks up to 5 times"; both client-derived. We ship the TEMPLATE value (conservative, errs AGAINST our own sustain claim); disagreement bounded at 1.5pp of regen. **Resolve game-first when convenient** (bins elsewhere, or live-game measurement on Joel's logs). This entry exists so "conservative forever" can never become a silent default.

## 📖 THE KNOWN-GAPS LEDGER (Joel's doctrine, 2026-08-10: proactive, never one-bug-at-a-time)

Joel: *"our main encounter of new bugs are based on not having knowledge about
everything in-game... having only detailed knowledge when one person brings up
one bug is not really being well thought out."* The knowledge existed but was
scattered across six instruments' pins. **`tools/gap_ledger.py` compiles it
into `docs/KNOWN-GAPS.md`** — the coverage check's OPEN_GAPS and the mode-tags
classes pulled LIVE (they cannot drift silently), plus the ruling-class items
and the needs-eyes-in-game list, each citing its entry here.

- **TRIAGE EVERY NEW FIELD REPORT AGAINST THE LEDGER FIRST.** A report
  matching a known gap confirms priority; one matching nothing is genuinely
  new knowledge and belongs in an instrument before it belongs in a fix.
- `--check` fails when the doc is stale vs regeneration — run it after any
  change to OPEN_GAPS, mode_tags, or the curated lists (they live in the
  generator, one copy). Regenerate after every PATCH-WATCH re-export.
- The 2026-08-10 census that motivated it: every table class in shipped
  0.12.36 equals its pre-retraction count exactly (zero real rows lost; the
  one absorb host that vanished was Wind Control's own record). Prose numbers
  larger than shipped counts ("229 mez", "38 absorb") were CLIENT-side class
  denominators; the landed subset is smaller by exclusions pinned in the
  batteries, which read the client and go red if a row vanishes.

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
- **My artifacts, his box:** never hand a foreground/long-running server command in a runnable code block (start-dev.bat blocks by design — hand the URL or launch detached). (The old no-COM-enumeration rule was Bitdefender's — REMOVED 2026-08-15, see the Bitdefender entry below.) When a fix is too small to be visible, SAY SO before asking him to look.
- **Accolades panel placement:** lives in the SUMMARY BAND (info-course: overview/bonuses/uniques/accolades cards) full-width under the powers wall — the wedged-beside-Stamina layout was ruled bad ("legibility beats cleverness").

## Project history

Moved to docs/claude-md-ledger.md (2026-08-14, Joel's ruling: old knowledge
lives in the repo + graphify, not in the always-loaded file). Query it via
`graphify query`; superseded release/wave entries live there too.

## Certification protocol rules (learned the hard way — each one has a corpse behind it)

**Full corpse stories: docs/claude-md-ledger.md (graphify-indexed).**

- **⛔⛔ THE CLIENT BINS PROVE MECHANICS, NOT LIVENESS. NEVER ADD CONTENT THE
  MIDS-DERIVED SNAPSHOT LACKS** (Joel 2026-08-10; the fake Gadgetry/Utility
  Belt/Wind Control records reached two certified champions and three re-cert
  waves, ~17.3 h). **The liveness authority is `data/powers.json` AS SHIPPED.**
  There is NO client field separating live from unshipped (measured — do not
  look again) and the play logs are blind (Storm Summoning also greps to zero).
  **The authority lags:** official patch notes ARE the game saying otherwise
  (Boomerang Slice restored via `tools/liveness_dispositions.json` with
  patch-note evidence); Joel's in-game check outranks a fan post but not the
  game's own notes. Wind Control / Gadgetry / Utility Belt STAY retracted.
  ⚠ A wholesale record removal must strip the mirror edits too (dangling
  `excludes` debris). ✅ Standing guard: `tools/reality_check_liveness.py` —
  current record names + offered sets vs the SAME files at the highest release
  tag, hard-fails both ways unless dispositioned with evidence (empty = the
  goal state); gated into `converge_parallel`; battery `tools/test_liveness.py`.
  Real new content rides PATCH-WATCH (the shipping release moves the baseline).
- **⚠ A PICK THE DATA DOES NOT HAVE IS NOT LEGAL** — `_picks_legal` refuses
  unknown powers outright (`.get(fn) or {}` had passed every rule while two
  champions named deleted powers).
- **🎯 SCOPE A WAVE BY THE MOVERS, NOT BY WHO HOLDS A PATCHED POWER** — holding
  is sufficient, not necessary (pet uptime, scenario and team channels move
  scores with nothing patched picked; cost a second wave). **The right test is
  an evaluate-first pass BEFORE the wave; done properly the wave ENDS with
  `0 moved`, which is the completion signal.**
- **⚡ THE QUICK NEEDS-UPDATE CHECK IS `evaluate_first --skip-riders`, no
  --write (0.7 min measured)** — answers MOVED / ILLEGAL / STALE STAMP per
  context; "NEEDS UPDATE: none" = no wave owed; a wave runs only over the
  contexts it names. ⚠ **THE CEILING:** it proves the stored build is legal,
  current, correctly scored — it CANNOT prove a different pick-set wouldn't
  win; only a converge wave searches. ⚠ recert_verdicts still prints no
  legality column — **keep checking merges by hand** (the 0.12.30 failure that
  shipped 8 unbuildable champions).
- **✅ The `e_gt` ground-truth shards are RETIRED (Joel: "illegal floors")** —
  game-illegal under the corrected prereq model
  (`.retired_2026-08-10_illegal_prereq_floors`); `e_derived_verdict` refuses
  until `run_e_overnight.py` regenerates legal floors. Past E clearances
  stand — an illegal floor is at least as strong as a legal one.
- **✅ EVERY CHAMPION RECORDS THE MODEL THAT CERTIFIED IT** —
  `merge_champion_shards` stamps `model_version` at its single write point;
  scope checks are one line of inspection. ⚠ METADATA ONLY:
  `tools/test_model_stamp.py` forbids scoring modules from READING it (tests
  field ACCESS, not the bare word; drives the real merge tool over an
  unstamped shard).
- **🚨 CHECK THE GAME, NOT YOUR PARSE** (cost a 12-hour wave): a parse of an
  undocumented field is a HYPOTHESIS — the game's display_help, weeks of
  working evidence, and Joel outrank it; a finding that invalidates certified
  work is JOEL'S RULING, never my wave.
- **✅ PREREQ MODEL: `server._prereq_need` is THE authority** (data
  `prereq_count` first, tier proxy for the 68 the game doesn't state).
  Evidence rule — patch only where TWO of three signals agree: the help
  sentence · the requires expression NAMES other powers (not merely non-empty;
  most epic expressions are archetype gates) · the corpus-validated tier
  model. Standing check `tools/reality_check_prereqs.py` (self-skeptical:
  help text naming another power is TEXT evidence, not RULE evidence), and
  **it GATES the launcher** — `converge_parallel` runs `--gate` BEFORE
  spawning, failing on disagreements new since
  `tools/prereq_disagreement_baseline.json`; `--skip-reality-check` exists to
  be said out loud. **A lesson that lives only in a docstring is a note —
  wire it into the thing it protects.**
- **⏱ PER-CONTEXT COST (corrected 2026-07-30):** min 12 · median 77 · mean 75
  · max 261 min (PB triform; never re-quote the pre-prereq-fix 484).
  ⚠ `buildout_champions`' printed `total:` is the WHOLE worker queue —
  per-context = the gap between consecutive `[Xm]` markers. Full space =
  2,691 combos ⇒ ~3,370 worker-hours (~28 concurrent for 5 days, ~70 for 2);
  content types multiply that directly.
- **🐌 SPEED LEDGER (measured; the solver backend is SETTLED and NOT a
  lever):** CBC keeps the crown — HiGHS 2.65× per-solve and **1.2-1.7×
  END-TO-END (quote the end-to-end number for wall-clock decisions)**;
  python-mip and in-process OR-tools both rejected (GIL — subprocess CBC is
  how the sweep escapes it); warm-start ≈1.0×. Hard plateau contexts sit
  89.8% inside cbc.exe — Python-side optimization reclaims little there.
  **The one measured win, awaiting Joel's scoping: process-pool persistent
  workers + in-process OR-tools CBC per worker = 1.5-1.9× wall-clock**
  (`sandbox/solver_upgrade/RESULTS.md`). ⚠ `HC_SOLVER_NODE_CAP` is read only
  on the CBC branch — a naive A/B runs CBC capped and HiGHS uncapped.
  ⚠ `bench_solver_e2e.py`'s live-wave guard is UNPROVEN — check for live
  workers by hand (it once killed 10 in-flight contexts).
- **⚠ THE CANONICAL RETRACTION (never root-caused):** in-process state after a
  ~7,000-solve 30-thread run changes evaluation (in-run 430.0 vs fresh 387.3,
  stable). **Stored score = within-run ranking ONLY; `canonical_score` from a
  fresh-process evaluate is the only portable number.**
- **⚠ SKIP-CHECK UNION:** `converge_parallel` unions champions.json + every
  root `champions_shard_*.json` − held shards (held = deliberately pulled,
  must re-converge); shard-vs-shard collisions hard-fail.
- **🔬 AURA/PATCH PROC VALUATION — OPEN RULING WITH FIELD DATA (do not lose
  again):** measured 10.66% per hit-tick vs the v31 formula's 6.14% — the
  formula undershoots the field by 42%. IG base damage (7.97/hit/target) and
  farming's double-stack still unpriced. Any change = model bump ⇒ re-converge
  both farm champions. `tools/measure_ig_procs.py`.
- **⚡ EFFICIENCY EVERY WAVE (Joel's standing ask):** run
  `tools/wave_cost_report.py` after every wave. The Kheldian slowness is
  PEACEBRINGER; sweep COUNTS are uniform — the lever is neighborhood size ×
  solve difficulty, not iteration count. `split_wave.py` schedules LPT
  (⚠ never SLICE the sorted list — that hands every monster to one machine).
  Makespan floor = the single longest context; the lever is PuLP model reuse,
  not silicon.
- **🖥 HARDWARE SIZING:** the workload is independent single-threaded CBC
  solves ⇒ cores × sustained clock, no GPU. The laptop (24C/32T) THROTTLES
  under sustained all-core load; the box ~2× slower per context. A 24-context
  wave in one shot needs ~24 workers. The RAM ceiling is FIXED (0.12.32,
  `learn._iter_log` streams). ⚠ Joel's frame: hardware buys VOLUME, never
  speed on the slow ones — size any purchase on a measured rented-box run,
  not my arithmetic.
- **📡 The box heartbeat reports per-worker motion** (`in_flight_summary`) — a
  banked count alone reads "0 of 8" for 40 minutes and nearly got a healthy
  order cancelled.
- **⚠ USE THE FLEET (Joel's rebuke):** at every wave launch/resume, partition
  the un-started keys across every healthy worker; idling a worker must be
  justified out loud, never a silent default.
- **EXPENSIVE RUNS LAUNCH DETACHED, NEVER AS SESSION BACKGROUND TASKS** (a
  session auth failure once killed two live workers mid-context;
  deep_optimize does not checkpoint mid-context). Mechanism:
  `Register-ScheduledTask` cmdlets (schtasks.exe quoting breaks under PS
  5.1), action `wscript.exe launch_hidden.vbs "<bat>"` window style 0.
  ⚠⚠ **Use the trigger alone (+10s) OR register far-future and Start
  manually — NEVER both: trigger+Start DOUBLE-FIRES the launcher** (a
  double-fire re-splits in-flight work onto colliding shard prefixes AND
  truncates the logs you monitor with). Unregister the task once processes
  are verified. Recovery: relaunch detached (certified shards are skipped),
  then VERIFY shard logs advance (two snapshots). ⚠ A resumed wave with fewer
  workers reassigns `_pN` suffixes — copy completed shards to non-colliding
  names (still `champions_shard_*`) BEFORE relaunching.
- **NEVER MERGE A SHARD WHOLESALE — MERGE BY CONTEXT, AND CHECK THE VERDICT
  FIRST.** Read the shard's CONTEXTS, merge only cleared ones, run
  evaluate-first after, KEEP THE CANONICAL WINNER — a recert earns
  supersession, it is not entitled to it. Bare `--replace` hard-fails without
  --verdicts (structural).
- **SHARD RETIREMENT AT MERGE:** rename merged shards `.merged_YYYY-MM-DD`
  immediately — `certified_union()` globs `champions_shard_*.json` and a
  stale copy once SHADOWED a live champions.json entry. With the e_gt shards
  retired, the union is champions.json alone until a wave writes new shards.
- **VERDICT BEFORE `--write`** — `evaluate_first --write` overwrites
  `canonical_score`, the very values the verdict compares.
- **EVERY NEW PRICING TERM SHIPS WITH A NEGATIVE CONTROL** — a real build that
  must read 0.0 beside the positive test; that is what proves the term reads
  ACTUAL slotting rather than firing on a lookalike.
- **"READY FOR YOUR WALK" IS A CLAIM WITH A DEFINITION — AND IT NAMES THE
  COMMIT HASH.** ALL of: server restarted from current HEAD · a FRESH page
  load with zero injected state · the exact URL Joel opens, driven through a
  REAL entry path · the claim states the hash. Anything less is "probably
  ready" and must be said that way. Verification theater's tell: the check
  never touched the thing the user touches. **Drive the real path.**
- **THE MACHINE CLOCK IS LOCAL EASTERN — `Get-Date` IS THE TIME AUTHORITY,
  NEVER A TZ CONVERSION** (re-bitten three times). Never STATE a clock time,
  countdown, or "N minutes until X" without a same-turn `Get-Date`; event
  cadence (monitor ticks) is not a clock. `date -u` only for UTC-labelled
  facts.
- **SCRIPTED-WRITE GUARD — the catch is mechanical, not vigilant.** This repo
  is CRLF: read `'rb'` → transform bytes → write `'wb'`; **never
  `newline=''` on a text-mode write** (silently rewrites CRLF→LF; bit
  server.py and RESUME-HERE.md in one week). Match each file's existing
  serialisation (powers.json is COMPACT single-line — never `indent=`).
  Before committing, compare `git diff --stat` to INTENDED size (cross-check
  `--ignore-all-space`); >2× intent or whitespace-blind much smaller → STOP.
  **Never PowerShell string rewrites on source files** (PS5.1 reads BOM-less
  UTF-8 as ANSI and mangles unicode).

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
- **⚔ SPIRIT DRAIN IS DARK MASTERY; SOUL MASTERY KEEPS SOUL DRAIN (settled
  game-first 2026-08-07, corroborated by Maelwys on topic 64761).** A field
  report said Corruptor **Soul** Mastery should read Spirit Drain since i27p7.
  It should not. The i27p7 note reads *"Dark Mastery > Spirit Drain (replaces
  Soul Drain) … from the **Dark Mastery** epic pool (Defenders, Corruptors)"*.
  **Our data is correct on both** and matches the client: `Epic.Dark_Mastery.
  Soul_Drain` displays **"Spirit Drain"** (the internal name never changed —
  the three-namespaces rule again), `Epic.Corruptor_Soul_Mastery.Soul_Drain`
  displays **"Soul Drain"**. They are genuinely different powers: 120s/15s/
  radius 15/5 targets vs 240s/30s/radius 10/10 targets. ⚠ **Both pools sit next
  to each other in the same dropdown and BOTH contain Dark Embrace**, which is
  why the confusion is easy and will recur. ⚠ **DATA CURRENCY, checked the same
  day: the newest Homecoming patch is the July 7 update and our client bins ARE
  that July 7 build** — the snapshot is live, not stale. I raised a
  "we may be a month behind" worry first and it was unfounded; retracted.
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
- **⚠⚠ A POWER THE GAME NEVER OFFERS IS NOT A PICK — `server._pickable` (level_available ≥ 1) is the rule, client-verified 2026-08-16:** 42 records inside primary/secondary sets are auto-granted set mechanics (Bio's three Adaptation stances, Staff forms, Dual Pistols ammo swaps, Seismic Shockwaves — client `auto_issue=True`/`available_level 0xFFFFFFFF`, the Fly_Boost class) and our data marks them `level_available 0`. Enforced in `_picks_legal`, the autopick enumeration, and `/build/validate` (field report 2026-08-16: a generated Bio/Rad Tanker spent three seats on stances). **The OPPOSITE mistake is real too: `slottable` is NOT pickability** — five REAL picks accept zero enhancements (Bio's Adaptation unlock = record `Evolution`, Swap Ammo, Staff Mastery, Reach for the Limit, Fate Sealed; client `auto_issue=False`) and the catalogue's old `slottable` filter HID them; the filter is now `level_available ≥ 1`, unslottable picks take `slots: []`, `changeSlots` refuses, validator flags slotted pieces on them. ⚠ Internal-name trap inside this family: Bio record `Adaptation` displays "Evolving Armor" (a normal slottable aura); the stance unlock is record `Evolution` displaying "Adaptation". ⚠ Open, honest: autopick never proposes the unslottable picks (their stance/mode effects are the unpriced stack-meter class), so generated Bio builds carry no Adaptation until the mode class is priced — the catalogue offers it by hand.
- **⚠⚠ THE BUILD EPOCH: an async recompute can resolve AFTER a character swap and write the OLD character's totals back** (field report 2026-08-16, the "new 50 still diffs my last character" recurrence that survived the 0.12.40 sweep fix). `_BUILD_EPOCH` bumps in `resetBuildScopedState`; `recompute` captures it before its await and DISCARDS the whole response on mismatch. The wizard's first solve of a generated build also passes `noDiff: true` — a fresh character has no "previous slotting", so no change-list renders at all. Pinned in test_edit_history_scope (31 checks).
- **⚠⚠ buildPayload() SENDS PER-POWER `full_name`/`pick_level`/`slots` ONLY — no `powerset_full_name`, no `level_available`** (field report 2026-08-15: the L1-seating heal no-opped its creation-pair logic on every REAL recompute payload and stamped two same-set picks onto level 1, then re-stamped them each recompute). Server helpers derive the set via `server._ps_of` (full_name prefix) and availability via `_sched_avail`'s POWER_BY_FULL fallback — any new server code reading power dicts from a request must do the same, and its battery must drive the BARE payload shape (test_slot_schedule check 6; check 5 passed for months on solve-enriched dicts while the field failed).
- PowerShell 5.1: embedded quotes break native args — use `-F`/`--notes-file` message files for git/gh; run gh and git steps separately.
- ⛔ **BITDEFENDER IS REMOVED FROM THIS MACHINE (Joel, 2026-08-15: "there is no bitdefender on this machine anymore. try and remember that").** Every Bitdefender behavior recorded in this file (release-night ATD kills, COM-enumeration sensitivity, .bat/token heuristics) is HISTORY, not a live constraint — never diagnose a dead process as "Bitdefender killed it" again (I did exactly that on the 0.12.39 release night and was wrong; the real cause was an unverified relaunch). FP/whitelist submissions for Bitdefender are no longer routine per release; other vendors' FP submissions only if a field report names one.
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

**Full build stories for every entry: docs/claude-md-ledger.md (graphify-indexed;
`graphify query` reaches them). This section keeps the RULES.**

Hero Companion stops being a browser app: **pywebview → WebView2** (runtime ships
with Win10/11), **no tray — window close = quit**, update check automatic on
launch, autostart toggle in the app UI, one-time share prompt for the Pulse feed.
**Companion Lite is UNCHANGED and keeps its tray — do not touch `run_lite.py`.**

- **The window is the DEFAULT and the tray is DELETED.** `HC_WINDOW=0` falls back
  to a browser tab and is the only escape hatch.
- **⚠ JUDGE THE APP FROM THE FROZEN EXE, NEVER FROM A SOURCE RUN** — and know
  WHICH exe: frozen builds stamp their commit (`build_commit.txt`; About + tooltip
  always show it, header on source runs only).
- **🚀 THE LAUNCH IS STAGED** (bootloader splash 1.3s → window 3.6s on
  `_SPLASH_HTML` → engine 4.1s via `_navigate_when_ready` socket probe). Rules:
  `import server` is LAZY (`_load_server`, started FROM `webview.start`'s
  callback — earlier threads starve the GUI on the GIL); `pyi_splash.close()`
  fires on window-up AND the no-window fallback; honest spinner, NEVER a progress
  bar. test_desktop_app pins it (138 checks).
- **🧭 LAUNCH LANDS ON POWERS & SLOTS, ALWAYS** (Joel 2026-08-10). Resume-time
  journey auto-open and `cohTab` restore RETIRED; the road still greets a new
  1-50 character once, at creation.
- **⚠ pywebview defaults are a BROWSER's defaults — three overridden in
  `_run_window`, keep them named there:** `SHOW_DEFAULT_MENUS` (right-click
  browser menu), white `background_color`, and **`private_mode=True`, which
  throws localStorage away every launch.**
- **⚠ The window icon MUST be a `.ico`** — a .png throws on a .NET thread OUTSIDE
  the try/except; app dies with no window and no message.
- **⚠ The self-update path outlives the tray**: `_run_window` sets
  `server.SHUTDOWN_HOOK`; window mode exits immediately.
- **⚠ ABSENT ≠ NO in the feed consent**: `feed_status()` returns `asked_here`
  separately from `opted_in_here`; the prompt fires on `not asked_here`; ✕ stores
  nothing. The prompt lives INSIDE the opening menu (not a modal — two wall
  attempts failed before asking whether it should be a wall), fires from
  `hideEntry()`, never at page load (stacked overlays).
- **⚠ The dev copy and the installed app SHARE gamelog state**
  (`%APPDATA%\HeroCompanion\gamelog`) and this checkout HAS an inbox key —
  answering the share prompt in a dev copy writes Joel's REAL feed preference.
- **⚠ PORTABLE IS NOT INSTALLED** (field report, 0.12.31 era): the tell is Inno's
  `unins000.exe` beside the exe; `server._install_kind()` → installed / portable
  / source, unreadable reads portable, so self-update REFUSES rather than
  converts. **Settled: refusal + download page is the WHOLE behaviour** — no
  install-instead button, no zip self-update. Do not re-open without a field
  report.
- **⚠ "ON" MUST BE A DOOR THAT SWINGS BOTH WAYS, on the surface that owns it**
  (Play Log on/off both live on the Logging tab, one `playlogConsent`/
  `setAutostart` — never a second copy of a choice).
- **⚠⚠ THE LEVELING GUIDE'S SIDE PICKER IS A PREVIEW.** The reset lives in
  **`activateTab`** (the one route every exit takes), `closeJourneyView` keeps no
  second copy; the preview never writes `cohAlignment`/`build`. **Precedence
  rule: the real choice always outranks a preview, and a preview never survives
  a real choice** (`applyAlignment` clears `_JNY_ALIGN`, order pinned).
  Generalize: when a promise is "X resets when you leave", find EVERY way out.
- **📐 SMALL DISPLAYS**: `.powers-layout` collapses to one column below 1400px;
  **`.stats-provlayout` at 1000px** (its side column is real content, not a
  void; his shell zooms 1.6×, so reproduce layout reports at EFFECTIVE width).
  Below 1000px `#stat-breakdown` re-homes after the selected row via
  `_breakdownHost()` (the rows container's innerHTML rewrite would delete it —
  held in JS, re-attached when detached). Page taller + WINDOW scrolls =
  allowed; a scrollbar INSIDE a panel is banned.
- **🧬 THE INHERENT IS A STAT, NOT A PANEL**: renders as the Archetype bonus
  group atop Stats with the honest word COUNTED / SHOWN ONLY / NOT MODELED
  ("counted" = in the SCORE, not displayed DPS; a meter on displayed damage is
  still Joel's ruling).
- **⚠⚠ A WARNING MUST CARRY ITS OWN FIX, AND THE FIX MUST NOT CRASH** — guard
  the ELEMENT, not just the data; a crash between a UI update and its
  persistence looks done and isn't.
- **🔍 audit_tour CHECKS CONTENT, NOT JUST STRUCTURE**: retired UI must not be
  named in any step (`_RETIRED` list — **add a line the day you delete a
  feature**); quoted menu items must exist in index.html; the mock MOVES when a
  surface moves.
- **🏷 The surface is "LEVELING GUIDE" everywhere it is LABELLED.** **⚠ RENAMES
  ARE FOR LABELS, NOT PROSE** (Joel: "leave sentences alone"); internal names
  stay `journey-*` (identifier, not identity).
- **⚠ ONE IMPORT DOOR, and it TEACHES**: one menu item → `showEntry("ingame")`
  → labelled route per file kind; the OS picker is never the front door.
- **✅ THE MIDS ROUND TRIP IS PINNED** (`test_mbd_alignment.py`, 9 checks;
  converges at hop 2 — hop-1 normalising of HO "+3" → level-53 is CORRECT).
- **⚠ Special origins live in `common_ios.json`, registered into `PIECE_BY_UID`
  at its build** (both importers + ⓘ image read there); their `set_name` must
  never be None.
- **⚠ Companion Lite is NOT a watered-down Hero Companion** — it is a LOGGER
  feeding the Pulse Boards; never "little brother". Lite = light blue P, full
  app = green P.
- **📉 The improvement report answers PER POWER** (attacks by Cycled DPS — same
  number as the ⓘ card; pets credited to their summoning power). ⚠ Buffs/debuffs
  are NOT diffed per power (`_resolve_mag` takes no slot boosts). ⚠ **OPEN,
  bites the invisible-role doctrine:** the buff/debuff panel elsewhere IS
  enhanced (below) but per-power diffs are not.
- **🧪 THE BUFF/DEBUFF PANEL READS ENHANCEMENT** (Joel's ruling): an effect is
  enhanced by the host power's own post-ED enhancement in the aspect of that
  name; exclusions only where the enhancement does not exist (no res-debuff,
  −regen, −damage categories). **RechargeTime IS credited** (`6b503c0c`, closed —
  a Recharge enhancement scales recharge effects both directions). Re-cert
  question TRACED: `first_principles._deb()` reads role_output at every serving
  call site — no score moved. `joint_refine(scorer="payoff")` has no callers;
  wire it up and support metrics start moving with slotting.
- **🖥 UPDATE THE COPY HE OPENS, DON'T EXPLAIN THE SPLIT**: after a server-side
  change — rebuild, smoke, `robocopy dist\HeroCompanion <installed> /MIR /XF
  unins000.exe unins000.dat`, relaunch. Never hand him a choice between two
  copies of his own app.
- **⛔ THE CLASS-ART FILLER WAS REMOVED AT JOEL'S WORD — he is sourcing his own
  art; do not re-add mine.** Extraction stays behind `extract_gui_emblems.py
  --art` (opt-in). Debugging lesson (ledger): when three measurement rounds
  disagree with the screen, the thing being measured is the wrong element.
- **⚠ "NOW SLOT THEM" IS A CLAIM ABOUT THE BUILD** — gated on actual free/empty
  slots, granted inherents excluded. **Any line that tells the user to do
  something is a claim, and a claim needs a condition.**
- **⚠ A HALF-UPDATED FROZEN COPY IS A LIE**: when a change spans the PYZ and the
  statics, both halves reach a copy together or neither does.
- **🏅 THE BADGE CATALOGUE: every badge on the surface, the name is the button**
  (chips carry `/thumbtack`; copy handler keys on `[data-cmd]`, one mechanism
  for every presentation; badges with no coordinates are PLAIN TEXT, never dead
  buttons; zone keys stay RAW internal prefixes until the i24 pass — do not
  invent display names).
- **🚫 THE PICKER REFUSES WHAT THE GAME REFUSES** (`_uniqueBlockedElsewhere`
  greys with the reason AND `pickPiece` enforces — a rule that exists only by
  not drawing a click target is one stray call from broken). **⚠⚠ OVER-BLOCKING
  IS THE WORSE MISTAKE**: `engine.NON_UNIQUE_OVERRIDES` ships on `/meta` (LotG
  class), no meta = fail OPEN (server validator is the backstop).
  `tools/test_slot_rules.js`.
- **🔀 THE SWAP PICKER PRICES EVERY REPLACEMENT, measured not derived** —
  `/build/slot_compare` drives the REAL `build_calculate` (nested
  `test_request_context`); candidates ride rows as `data-cand`, byte-identical
  to what the click installs; the axis is `SELECTED_STAT` (no stat = say so,
  never invent an axis). On a solver-optimised build every swap on the optimised
  stat reads as a deficit — that is the truth. (One /build/calculate = 4.9 ms;
  batch, don't lazy-load.)
- **🧾 EVERY EDIT REPORTS ITSELF AND HANDS BACK THE UNDO.** The hook is
  `recordEdit`, NOT any button — that is what makes the receipt universal.
  `undoEdit` never calls `recordEdit` (a receipt for putting something back is
  noise); the popover survives losing its anchor (re-centres, keeps Undo);
  column labels are per-caller (`opts.labels`).
- **🛠 STATS IS THE MANUAL SURFACE** — one piece at a time, numbers move; any
  surface showing a cost must let you act on it (popover Swap/Remove wired to
  the SAME `openSlot`/`clearSlot` — never a second editing path).
- **🎯 THE PER-IO ANSWER IS A POPOVER AT THE CHIT** (comparison ⇒ the page must
  not move). Fixed coordinates, re-places on scroll, flips when out of room;
  closes on ✕/outside click — **never advertise Escape, it does not reach the
  page in the frozen shell**; per-power table opens FOLDED (no inner scrollbar).
- **💎 WHAT ONE ENHANCEMENT IS WORTH IS MEASURED, NEVER DERIVED**
  (`explainSlotWorth` recomputes with the slot empty; analytic is wrong wherever
  the game is interesting — ED, tier loss, rule of five). ⚠ Probe from
  `buildPayload()`, never `build`; ⚠ `/build/calculate` returns the totals
  object ITSELF, not `{totals:…}`.
- **✅ "RADIATION MELEE DISCREPANCY" RETRACTED** — enhanced-vs-base was not
  comparable; our base damage is exact (ratio 0.481 = client's).
- **⚠⚠ DO NOT ADD THE EXPORT'S `Fire_Dmg` TEMPLATES — THAT IS FIERY EMBRACE**
  (86 of 108 Brute attacks would inflate ~45%). **The gate is `tags`** — the
  effect-group field naming the whole mode/meter class (FieryEmbrace 349 ·
  Containment 119 · Domination 90 · Overpower 86 · Defiance 33 · PowerBoost ·
  crits · ~150 more); the tag names the mode, NOT the uptime.
- **⚠⚠ A `requires_expression` MIXES TARGETING WITH CONDITIONS** — strike the
  targeting clauses and 5,123 of 7,323 reduce to nothing; the client writes an
  attack's damage once per archetype and again per game state (Wrist Blaster:
  23 damage groups). ⚠ `chance: 0.0` means UNSET, not "never".
- **🔥 FURY: instrument built** (`measure_fury_residual.py` v2, spread 228% →
  25.2%; AoEs CANNOT be reconstructed from this log format). **Blocked on a
  THIRD clean single-target attack** — two points cannot separate a multiplier
  from a flat term.
- **🔗 POWER BOOST = the same missing mode/meter capability as Fury** (client:
  a `Set_Mode` 15s, groups tagged PowerBoostA — not a patchable flat bonus).
  Build the class as ONE piece of work; the `tags` census IS the roster; the
  missing input is UPTIME (Joel's ruling). Champion exposure zero.
- **🧭 THE ORDER TO WORK IN IS STATED ONCE, AT THE TOP** — the band on Powers &
  Slots (goal → Solve → tune on Stats → change powers last), shown only when a
  build exists, not a fold, step 2 points AT Solve and never presses it; the
  tour states what each step HANDS BACK. ⚠⚠ `__tmScene` defaults to "menus" for
  the whole start chapter — a step whose subject lives on a tab must say
  `scene: "build"` or it highlights a zero-size stub; **a tour step is only
  verified by RUNNING it and looking** (now audit_tour check (c), parsed with a
  real element stack — a nesting question needs a parser). Walk method: clear
  `driver-active-element` off everything, Next, ~200ms, read the survivor; one
  chapter at a time.
- **🧯 WHEN I BREAK SOMETHING, I FIX IT — I DO NOT HAND HIM THE MENU.** Repair,
  state plainly what could not be recovered, stop. And never test against a real
  save (autoSaveTick persists) — scratch copies only.
- **🔁 THE EPIC SWAP FINISHES THE JOB**: three-action dialog (Switch and refill
  default · switch-I'll-pick · Keep). Server-side `_pick_epic(force=)` threaded
  through `/build/autopick` (`epic: build.epic`); `force=None` BYTE-IDENTICAL,
  proven on 272 combos. `_solveAlreadyApproved()` is the ONE copy of
  "run the real Solve with an approval already given". Spans PYZ + statics.
- **🧹 PER-CHARACTER STATE: ten globals cleared in `resetBuildScopedState`**
  (SELECTED_STAT et al., measured not reasoned). `_convHaul` deliberately NOT
  swept (user-typed input). **A visibility check must ask the layout
  (`offsetParent`/`getClientRects`), never a class name.**
  `tools/test_edit_history_scope.js` (24 checks).
- **⏪ OPENING A CHARACTER IS NOT AN EDIT**: `_LOADING_BUILD` guards `recordEdit`
  across `applyImportedBuild` in try/finally (a leaked flag would stop recording
  real edits); `EDIT_HISTORY` cleared in `resetBuildScopedState`. Battery keeps
  a POSITIVE control. Probe the mechanism, not the symptom.
- **🔲 CENSUS THE TREATMENTS BEFORE "FIXING" ONE**: when a visual complaint and
  the computed styles disagree, the property you are looking at is not the one
  doing the work — tally every treatment on the surface first. (The fix:
  `.pw-cardband > .panel, #assistant { border-color: var(--accent) }`, not on
  panels already holding an accent box.)
- **📣 A TOOL THAT CANNOT EXPLAIN ITSELF IS HALF-BUILT**: every explanatory lede
  gets `.keep-whole` AT BIRTH; type size is CSS-only (`fitZoom` floor 1.00 pins
  the app — `.tool-lede` 14px, never raise `.small` globally); "potent" means
  saying what it does to a build you already have. ⚠ `↳` has no glyph in the
  app's font (use `→`); ⚠ the ink token is `--ink`, `var(--text)` is undefined.
- **🗡 v44 CRITICAL HITS** (`patch_power_crits.py`, 253 rows / 247 powers): the
  chance the client states, at the FLOOR it states (minion 0.05; crediting boss
  0.10 needs a rank mix no scenario writes down). Rules with corpses: a chance
  of 1.0 is not a die roll (StealthCrit); pets don't crit as their owner;
  **an `Epic.*` record is not archetype-scoped — never write an
  archetype-specific mechanic onto one** (exposure 14→2). ⚠ Re-cert owed 2/24
  (Scrapper BS/SR, Stalker Rad/DA) — NOT STARTED. `tools/test_crits.py`.
  **Version pins are `>=`, never `==`.**
- **👑 v43 DOMINATION**: 1.5× control duration (help + 41/41 encoded pairs),
  uptime from the inherent's own 90s/200s (perma at +122% recharge, capped),
  applied UNIVERSALLY via the existing `mez_dur` channel (client encodes only
  12/26 sets — encoding asymmetry, not a game one). Magnitude half deliberately
  NOT credited (client ambiguous). ⚠ Re-cert owed 1/24 (Mind/Fiery itrial) —
  NOT STARTED, Joel's call. `tools/test_domination.py`.
- **🎛 MODE/METER CLASSIFICATION BUILT** (`tools/mode_tags.py` + reality check,
  hard-fails both ways): LABEL 22 · PROB 14 · MODE 4 · SCENARIO 6 · DERIVED 1
  (Defiance — v36 derives it; its templates are NOT all zero-scale, the skip is
  load-bearing). **A tag is not automatically a gate** (FireBlastBonusDoT is a
  label; three mechanical tests all failed both directions — hand-adjudicated
  table). Left, each naming its missing input: stack meters (scenario constant),
  Domination magnitude (engine mode path), crits per-rank (rank mix),
  FieryEmbrace 305 groups (Fire-TYPED buff vs type-blind `damage_buff` — a
  measurement, not a reading; do not add the Fire templates).
- **🧰 (retracted content, standing lessons) A POOL NEEDS THREE THINGS an
  archetype set does not**: stated prereqs into `prereq_count`; the
  never-pickable free rider (`available_level 0xFFFFFFFF`); archetype gates
  RECORDED (`archetype_excluded`), not dropped. The origin-pool rule is
  server-side, unverifiable from bins.
- **⚠⚠ AUTOPICK: exclusion twins read from the DATA, never a hand list** (the
  typed `_VEAT_DUPLICATE_PAIRS` knew 2 of 13; a twin is a SET). **A pick level
  must be ≥ the power's own `level_available`** (first-two-by-tier is not
  available-at-level-1 — the Fortunata trap); `audit_autopick_legality` states
  both; 2,721/2,721 legal.
- **🪪 THE ALIAS MAP'S DECIDING RUNG IS "TWO OF OURS WANT ONE OF THEIRS"**
  (display-name rung changed zero existing aliases; remaining diffs live in
  `ROSTER_DIFF_DISPOSITIONS`, hard fail both ways). It found the Gymnastics/
  Quickness/Oil Slick collision no display or scalar check could see; repair =
  `patch_display_name_collisions.py` (identity by EFFECT signature; categories
  rebuilt from our `accepted_set_category_shorts`, cross-checked). ⚠
  `reality_check_powers` prefers an adjudicated alias over a same-name
  coincidence. A names-only detector cannot find a names problem.
- **🔒 A `pv_mode: 2` ROW IS A PvP VARIANT, NOT A DEFECT** (Chrono_Shift class:
  exactly 5.33× the client's timed heal scale — a designed HoT→regen
  conversion; `engine._pv_ok` gates it off everywhere in PvE; whether 5.33 is
  right for live PvP is unverifiable and not claimed).
  `classify_unmatched_effects.py` tests pv_mode FIRST.
- **⚠ AN EMPTY STATE IS A CLAIM TOO**: when one message serves two states, it is
  wrong in one of them; derive ranges from data, never hardcode. A fact must
  never be gated on whether prose exists beside it.
- **⚠⚠ `JSON.stringify` IS NOT ATTRIBUTE-SAFE** — an apostrophe closed the
  single-quoted onclick and broke manual slotting of 40 sets since the FIRST
  COMMIT (shipped 0.12.35). Attribute payloads go through escHtml (both quote
  chars). `tools/test_picker_attrs.js`; its source rule is deliberately narrow —
  a check that cries wolf is worse than none.
- **✅ THE SELF +DAMAGE BUFF CLASS IS LANDED AND WORKING** (275 powers, v39
  mode/host_recharge duty cycle; measured: Build Up moves damage_buff 0→0.1111).
  ⚠ The "moves by 0.0" scare was a bad probe — **a probe that adds a power must
  assert the record RESOLVED (`POWER_BY_FULL.get`) before believing a zero.**
  No re-cert owed. (Superseded 2026-08-07 report: ledger.)
- **🛡 v41 DDR** (178 powers): DDR is power-granted ONLY (no set bonus), the
  incoming −def term already existed. Clicks duty-cycled via v39 mode. ⚠ aspect
  is the whole filter (aspect=Strength = Alpha definitions); ⚠ the v39 mode
  dedup now keys the effect NAME (was a silent swallow).
- **🗂 EVERY EFFECT FAMILY IS CLASSIFIED** (`reality_check_effect_coverage.py`,
  residue zero): SOURCE_EXCLUSIONS counted, DISPOSITIONS cite rulings,
  OPEN_GAPS pinned to fail BOTH directions. **A real gap must never be
  dispositioned into silence, nor hard-fail forever.** Rule 5: TRANSLATE THE
  VOCABULARY (ours `AoE`/`Negative`, client `Area`/`Negative_Energy`).
- **📭 THE EMPTY-RECORD CLASS: 876 records, 2 were data gaps** (Bo Ryaku,
  Active Defense — each fixed on TWO signals: the game's Toggle:/Auto: prefix
  AND a populated sibling; both stubs were wrong in power_type TOO, which is why
  a correct back-fill measured 0.0). **The first yielding group wins WHOLE**
  (the second group is the PvP variant, not a copy). **Gamma Boost is NOT a
  back-fill** — health-scaling effects are their own unbuilt model.
- **🛡 v42 ABSORB**: `totals["absorb"]` = shield SIZE, `absorb_hps` = worth
  (pool ÷ re-arm) — **NEVER ADD THEM**. Only heal-table rows taken (a literal
  1.0 on a `*_Ones` table is not a shield). ⚠⚠ **The enhance aspect is
  `Absorb`, NOT `Heal`** (the client's boosts_allowed says Heal and enhances
  nothing).
- **⚠⚠ `Recharge` IS A DEAD WORD — THE ASPECT IS `RechargeTime`** (three sites
  asked the dead name; mode duty cycle, click uptime, and timed-PET uptime all
  silently failed downward; now share `engine._RECH_ASPECT`, checked against
  the SERVED vocabulary). A fresh measurement across an old code path is how
  dead lookups surface.
- **📐 THE MAGNITUDE IS NOT ALWAYS IN THE SCALE** — 226 powers carry it in
  `magnitude_expression` (RPN). MAX-HP-PROPORTIONAL (10) modelled;
  HEALTH-DEPENDENT (13) decoded and PINNED (needs an operating-health scenario
  constant). ⚠ Magnitudes compute against BASE hp, never the accumulating
  boosted pool. **A zero-scale template WITH an expression is not empty**
  (SR's scaling resistance); computed-magnitude classes dispositioned by
  EXPRESSION (Defiance stays out — v36 derives it).
- **🌪 WIND CONTROL build lessons** (the set itself was RETRACTED 2026-08-10 —
  not live): ⚠⚠ `targets_affected` IS THE SIDE, NOT `target_type` (a Self-typed
  cone lands on FOES); a mode-gated power legitimately carries nothing; the
  generator REFUSES rather than guesses.
- **⚠⚠ `open(path,"wb").write(expr)` TRUNCATES BEFORE `expr` EVALUATES** — it
  emptied powers.json to zero bytes once. Build all bytes first, then open.
  Match each file's own serialisation (powers/summons compact single-line,
  powersets `indent=1` CRLF).
- **🎯 CONTROL DRIFT synced game-first (25 of 29)**; four multi-row ENCODINGS
  left alone — collapsing one is a different question from correcting a number.
  The 269 unresolved `summons[]` refs are metadata, not a pricing gap.
- **🚫 MUTUALLY EXCLUSIVE POWERS: 13 client-derived pairs,
  mirrored-or-not-at-all** (one-sided = parse artefact); validator names the
  pair, gate reads the data. ⚠ A negative test that can pass for a second
  reason is not testing what it names — SWAP a pick, don't add a 25th.
- **🗡 BOOMERANG SLICE = the pattern for whole-record adds**: every field from
  the client (what it is) or the proven sibling (app schema); could not land
  until the exclusion rule existed. Rending Slice bonus NOT priced (meter
  class) — understated rather than guessed.
- **⚠⚠ `child_effects` IS A LEVEL THE PROBES MUST DESCEND** — treat an
  empty-looking client group as UNREAD, not empty; enumerate field names before
  concluding absence.
- **⚠ The client's `available_level` is 0-BASED, ours 1-based** — any record
  synthesised from the client adds one.
- **⚠⚠ A RAW SET DIFFERENCE IS NOT A MEASUREMENT** ("459 missing powers" was
  32 + naming). `tools/reality_check_missing_powers.py` is the standing
  instrument, part of PATCH-WATCH.
- **🤝 THE ALLY SIDE: the template's `target` field is NOT the side**
  (`AnyAffected` ≠ ally) — **the power's own `target_type` is the authority**,
  pins keyed by SIDE. An `aspect=Strength` row placed on someone else amplifies
  THEIR build — nothing to multiply, no pin.
- **⚠⚠ `mez_in` IS THE HIGHEST-LEVERAGE OPEN RULING**: one number unblocks 289
  inert powers (self mez prot 229, ally mez 29, four debuff-resistance families
  31). Ally SLOW resistance is blocked on the CHANNEL, not an input. **⛔ Don't
  build a term for one power when the channel is coming anyway** (ally absorb
  reverted; builds once, with mez_in). Four more resistance families same shape
  (ToHit/end-drain/regen/recovery-debuff) — one scenario number each, Joel's.
- **⚠ A correct data patch read zero three times, never because the data was
  wrong** — suspect the ADMISSION PATH; always read a known-good axis in the
  same probe. **A pin that only fails upward is half a pin.**
- **⚠ TARGET-CAP / RADIUS DRIFT IS MOSTLY NOT DRIFT — never blanket-sync**
  (pseudo-pet folds and convention differences; patch only with a second
  signal). Classifying the ~460 remaining is its own piece of work.
- **⚠ A JS-only function can have a real battery**: lift it out, run under node,
  prove the battery against sabotaged copies (`test_improve_diff.js` pattern).
- **⚠ Installing overwrites `dist\HeroCompanion-Setup-{VERSION}.exe`** — check
  for a released signed installer before every ISCC run at unchanged VERSION.
- **⚠⚠ NEVER hang a rich object on the js_api object** — pywebview walks its
  attributes to build the JS bridge; a Window ref froze the app. `_winref`
  closure instead.
- **⚠ `ALLOW_DOWNLOADS=False` silently eats blob downloads** — every produced
  file routes through `js_api.save_file`; the setting stays False on purpose.
- **The build tile has a NAME field**; autoSaveTick sends `named: !NEEDS_NAME`,
  never a blanket true (a blanket killed the rename nudge).
- **`/saves` sends `picks`** for the honest in-progress label; only a REBUILT
  frozen server sends it.
- Batteries: `tools/test_desktop_app.py` (negative-controlled both ways);
  `tools/audit_tabs.py` = the tab-shell audit (caught autopick reading retired
  ids, silently dropping wizard answers).

## 🔎 SEARCHABLE HELP (Joel's order, 2026-08-10: help leaves the PDF and enters the client)

Joel: *"type in a term and get a breakdown of what it does, how it functions,
why it exists, and where is sits in the workflow of building, updating,
tweaking or manually changing builds… making the workflow stupid easy to
follow is vital."* Shipped statics-only (staged Unreleased; his installed copy
carries it via push_statics).

- **Content = `static/help_topics.json`** — 44 topics, each answering the FOUR
  questions (`what`/`how`/`why`/`where`) plus a `stage` (building / updating /
  tweaking / manual / reference) and `go` actions. **Statics-only by design:
  content edits need no rebuild**, just push_statics + relaunch.
- **The empty query IS the workflow**: opening help with nothing typed shows
  the four-step loop and the four workflow descriptions, every term one click
  away. The loop text is the same order the band and the tour teach — three
  surfaces, one order.
- **Actions are a two-word vocabulary**: `tab:<key>` (activateTab) and
  `tour:<key>` (explainStep deep link). Battery `tools/test_help_search.py`
  (15 checks, 4 sabotages) fails any action naming a tab or tour key that does
  not exist — a help button that goes nowhere teaches distrust.
- **Modal follows the `.about-body` pattern** (scrolls inside the 80vh modal
  cap — the sanctioned exception to no-inner-scrollbars). Body text 14px per
  the tool-lede rule; all topic text renders through escHtml; `.keep-whole` on
  every block at birth. ✕/backdrop close; Escape deliberately not advertised.
- **Content sourcing rule applies**: topics were written from docs/help.md,
  the shipped ledes and this file's pinned rulings — never guessed. The honest
  gaps live in a topic of their own ("What is deliberately not counted").
- Verified through the REAL path on a live 5081 server: menu click → loop
  home → term/alias/no-match search → `tab:` switches the tab → `tour:` opens
  the tour. audit_tabs / audit_links / audit_tour all green after the surgery.
- **v2, same day (Joel's flow: anticipate the typing → dropdown → full screen →
  leave help and work on it).** Typing shows a SUGGESTION list — most likely
  term first with its one-line answer, ↑↓/Enter or click — and Enter opens a
  **full-screen page** (`.help-full`, min(1150px, 96vw)): the four answers, a
  **For example** block (38 topics, only verified facts — LotG 37.5, the
  3-Ribosome parity, set_min−3, cap+5, the 5% floor), and where it helps a
  **figure taken from the guided tour's mock** (15 topics; `fig:` names a
  `data-for` stand-in, rendered inside a `#tour-mock`-scoped wrapper so the
  real stylesheet paints it — position static, pointer-events none).
  ⚠⚠ **CLOSING EMPTIES `#help-search-out`, never just hides** — a hidden
  figure carries a `#tour-mock` node that would shadow the real tour's mock by
  document order. Battery pins this (20 checks, 5 sabotages incl. a dead fig).
  ⚠ Every topic should carry a `go` — the live walk caught Exemplar view
  without one, which silently made "leave help and work on it" unreachable
  for that topic.
  ⚠ **A CONTROL'S HELP STATES ITS KEYBOARD SHORTCUT, verified from the code
  binding, never assumed** (Joel's field test, 2026-08-10: the Undo topic
  explained the function and never mentioned Ctrl+Z). The Undo topic now
  carries the whole truth from app.js:6900 — Ctrl+Z anywhere, ASKS first
  naming what it takes back (his 2026-08-04 ruling), skipped while typing so
  text fields keep native undo, the button immediate. The shortcut is also an
  ALIAS ("ctrl+z"), so typing the keystroke finds the topic. When authoring a
  topic for anything with a binding, grep for the keydown handler first.
- **⌨ MENU ACCELERATORS EXIST NOW (Joel, same day: "every major usage on the
  menus has a shortcut keyboard combo" — the census said Ctrl+Z was the ONLY
  player-facing one, so the set was BUILT, not documented).** `_KBD` table in
  app.js beside the Ctrl+Z handler: **Ctrl+S save · Ctrl+I import · Ctrl+E
  export · Ctrl+K search help · Ctrl+1..4 tabs.** Rules baked in: every combo
  presses the SAME control the menu clicks (a menu rewire carries the shortcut
  for free); combos skip while typing; the tour owns the keys while a
  driver-popover exists; Ctrl+letter is the PROVEN class in the frozen shell
  (Ctrl+Z / Ctrl+Shift+L reach it, Escape does not) — never bind bare F-keys
  or Escape. Hints ride the menu items (`.menu-kbd`) and tab tooltips.
  ⚠ The battery enforces PARITY both ways: every `_KBD` key documented in the
  "Keyboard shortcuts" help topic, and the topic may claim nothing the code
  does not bind (test_help_search checks 21-24).
  ⚠ New combos are page-proven; ONE press each in the frozen shell (Joel's
  hands) is the final word, per the Escape lesson.
- ⚠ help.md's stale "(v23 today)" model pin was removed in the same pass —
  versions belong in About, never hardcoded in prose.
- The PDF stays: built from docs/help.md at release, linked in the same menu.

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

**Completed-batch narratives (engine-accuracy items 1-6, the 2026-07-30/31
waves, the v38+HO wave, the slotting-remainder pieces, the remote-worker maiden
run, the superseded release chain back to 0.12.30): docs/claude-md-ledger.md.**

**✅ THE OWED 20-MOVER WAVE IS DISCHARGED (2026-08-14, Joel's rulings: new-shape
population wave → "merge 17, hold the Dominator" → "refresh the scores").**
`evaluate_first --write` refreshed the 20 stale canonical scores on deduped
data (picks unchanged); re-run reads **0 moved / no wave owed**, 24/24 SERVED,
all stamped v44 (commit `3ca12b1e`). ⚠⚠ **THE STRUCTURAL FINDING: champions.json
stores PICKS ONLY — the app re-derives slotting at serve time (`_champion_picks`
→ autopick → client solver), so population-refined SLOTTING has no persistence
channel.** The wave's 17 production-validated refined slottings (+8% to +64%,
median ~+17%) are saved in `coh-scorer-lab/wave_pop_results/` as evidence for
the **slotting-integration work item**: persist a slotting layer or make the
population refine a finale pass — blocked on Joel's certificate-doctrine
ruling. **Dominator Mind/Fiery (+183.8%): SCRUTINY DONE 2026-08-14
(`coh-scorer-lab/scrutiny_dominator.py`, fresh-process) — the control channel
is EXONERATED: both builds sit at the prevented-control CAP (ctrl_frac 0.9,
identical 1170 credit), Domination duration is near-neutral (−8/−73 with the
credit zeroed), perma-dom refill inert (endurance sustainable both). The whole
delta is AVAILABILITY 0.366 → 1.0 (ttl 14.8s → 338.8s): the challenger cashed
past-the-cap control-duration pieces into defense/HP/regen. Rule-of-five clean
(exactly 5 LotG globals). The magnitude is the one-objective gap on an
unusually fragile incumbent, not a control artifact. Merge stays Joel's call
(blocked on the same slotting-persistence channel as the 17).**
Two lab parity gaps noted: the lab seed path emits unseatable slot layouts for
Tanker Inv/SS and PB base (their certified picks seat fine — lab-only issue).

**✅ THE CERTIFIED-SLOTTING LAYER IS BUILT AND BANKED (2026-08-14, Joel's
game-truth ruling: "Whatever is valid to game truth" — the stored score and
the served build must be the same real, game-legal build).** This CLOSES the
slotting-integration item and the Dominator merge question. Mechanism, one
copy each: champion entries may carry **`slotting`** (the production-validated
refined build); `server._champion_slotting` serves it VERBATIM inside
`/build/solve` on the exact champion-delivery shape (generated kit + content
preset + certified role + no custom/targets/exemplar/pvp/keep-layout/
perk-chips) after re-validating on TODAY's data — **FAIL OPEN to the solver on
any doubt**; `evaluate_first` scores a stored layer directly (no re-solve) so
canonical describes the served build; `tools/bank_refined_slotting.py` is the
only writer (hard-fails on pick mismatch / validation / seating). Response
carries `certified_slotting`; validate_champions prints `+SLOTTING` /
`!!SLOT-DRIFT` by driving the REAL /build/solve. **Banked: the 18 CHALLENGER
layers from the 08-14 wave incl. the Dominator (canonical 759.8 → 2156.0;
whole-roster median gain ~+17%).** One-time MOVED rows at banking = the basis
change, not drift (second run: 28 unaffected). Battery
`tools/test_champion_slotting.py` (9 checks, 2 sabotages; the positive control
MUTATES one in-set piece so serving it proves the layer beat the solver).
⚠ Lifecycle: `learn.save_champion` writes picks/score/certificate only, so a
re-certification DROPS the layer — correct (stale by definition); the context
falls back to solver serve until a new refine wave banks a new layer, and
evaluate_first flags the basis change as MOVED. ⚠ evaluate_first's printed
"re-converge the movers" advice after a BANKING pass is a false alarm — the
proof of health is the second run reading 0 moved.
**✅ INTEGRATED PRE-POST (same night, Joel's order): frozen exe rebuilt (stamp
`defe1b0` = HEAD), smoke PASS + gold 28/28 PASS (the earlier stale-bundle gold
failures are gone), installed copy mirrored + relaunched, Dominator serves
`certified_slotting: true` through the installed app's real HTTP path.
RECERT: NONE OWED (28 unaffected / 0 moved, v44 — the layer is serve
capability, not a model bump). Changelog staged under Unreleased; VERSION
stays 0.12.38 until Joel cuts the release.**
**✅ LAYERS COMPLETE (same night, Joel: "run the refine wave on the 8" →
"bank the 8 and reintegrate"): 26 of 28 contexts carry certified slotting** —
the 8-context wave ran 2.4 min, 8/8 CHALLENGER (Spines/FA +193.6%,
Poison/Sonic 2037→2718, Rad/Sonic 1791→2458), banked, stability 28/0,
reintegrated at stamp **`c6d136a`** (smoke + gold 28/28 PASS, installed copy
mirrored + relaunched, farm AND itrial layers verified serving through the
real HTTP path). Only the 2 lab-parity contexts (Tanker Inv/SS, PB base)
remain layer-less — blocked on the lab seed-parity fix, not owed.
**⚠⚠ GATE TRAP, FIXED + PINNED (battery check 11): a content PRESET can carry
its own `perk_focus` — the certified-slotting gate must test the USER's ask
(`_user_perk`, captured before the preset overlay), never the post-overlay
value.** Reading it post-overlay rejected every FARM champion's layer while
itrial served fine (validate_champions caught it: 23/28, 5-farm SLOT-DRIFT).
Generalize: any serve-gate condition on a request field must ask whether the
PRESET fills that field downstream. `wave_pop.py` now takes keys via argv;
prior verdicts preserved as `.banked_2026-08-14` before any rerun (it
overwrites, same trap class as recert_verdicts).

**✅ THE FARM-ALT WAVE IS BANKED (2026-08-14, Joel: "relaunch the scrapper and
merge the three").** The 2026-08-11 half-run (rediscovered as uncommitted
edits, code committed `edd88f07`) is resolved: the 3 converged shards MERGED
as new contexts (plain merge — no incumbents; hand-run `_picks_legal` + pick
liveness green first), shards retired `.merged_2026-08-14`. **Roster = 27
contexts, 27/27 SERVED**, canonical baselines set fresh on CURRENT post-dedup
data via `evaluate_first --write` (the pre-dedup in-run scores shed the
expected inflation): Tanker FA/FM afk 275.8 · Brute TW/Bio afk 359.8 ·
Stalker Claws/EA active 658.2. **The 4th (Scrapper Rad/Rad farm_active)
relaunched detached on current data and CONVERGED same evening** (65.2 min,
clean certificate, `--sweep-backend process`, `farmalt2` prefix): merged,
shard retired, canonical **699.7** (in-run 790.3 — the usual inflation).
**ROSTER = 28 CONTEXTS, 28/28 SERVED, all legal, stamped v44, 0 moved, no
wave owed.** All four fire-farm alternatives are distinct in AT + primary +
secondary + farm mode, none overlapping Brute Spines/FA. They ride the next
release's champions.json per standing rule. wave_cost_report run (standing
ask): the Scrapper's 65 min sits under the 77-min roster median.

**✅ THE RECERT27 WAVE IS BANKED WHOLE (2026-08-15, the full ritual).**
27/27 converged (12.2 h wall, 4 workers, `--sweep-backend process`, makespan
= the Kheldian tail as always). Verdicts: **10 SUPERSEDE / 17 KEEP**
(canonical-vs-canonical, both sides fresh re-solve = the honest picks-level
comparison; hand legality 10/10). Winners merged `--verdicts`, shards retired
`.merged_2026-08-15`. The 11 then-layer-less contexts re-refined (wave_pop,
3.2 min): 10 banked; **PB base remains the ONE lab-parity holdout** (solver
serve, honest). **End state: 28 contexts, 27 layers, stability 28/0,
validate 28/28 + 27 `+SLOTTING`, batteries slotting 11/11 · demo 24/24 ·
desktop 141/141; integrated at stamp `e9a7ac4`** (smoke + gold 28/28 PASS,
installed copy mirrored + relaunched). Roster top: Poison/Sonic 2718 ·
RadEm/Sonic 2519 (superseded picks) · RadEm/RadBlast 2376 · Plant/Poison
2307 · Dominator 2156. ⚠ Superseded-pick recerts that LOST (17) stay
incumbents by the gate — that most recerts lose remains the norm.
⚠ NEW `_slot_plan` rule: a LONE ordinary set piece now carries its own note
(single-piece / single-proc kinds) — the refined layers place 43 such
singles, and a card that cannot explain itself is half-built.
**🚀 RELEASED as v0.12.39 "Certified builds, served as certified"
(2026-08-15, Joel's "cut the release"): stamp `b87d832`, both assets signed
(CN=Joel Andrew Chambers) + API-verified (published 13:22Z); smoke PASS,
gold 28/28; installed copy mirrored + relaunched at 0.12.39. Notes state
data currency (July 7 2026 patch, re-export verified 08-07). Announcement
draft: `Downloads\hero-companion-0.12.39-post.txt` — posting is Joel's hand.
FP/whitelist submissions per signing runbook: Joel's hand, now for 0.12.39.
Liveness baseline: roll to v0.12.39 on next check.**

**🚀 v0.12.40 "Three field-report fixes" RELEASED same night (2026-08-15,
Joel's "cut the release"): stamp `756c41e`, both assets signed + API-verified
(published 2026-08-16T03:11Z); smoke PASS, gold 28/28; installed copy
mirrored + relaunched; liveness baseline rolled to v0.12.40 (0 diffs).
Carries the three fixes from the 2026-08-15 Web3Forms report (Ice/Ice
Brute): new-character state sweep (LAST_TOTALS/LAST_CALC), save-then-close
dirty-flag push + confirmQuit recheck, and the L1 creation-pair heal fixed
for the app's bare payload shape (`server._ps_of` — see the buildPayload
pitfall). ✅ ANNOUNCED: Joel posted the 0.12.40 reply on topic 64761
(2026-08-16) — it supersedes the never-posted standalone 0.12.39 draft
(`hero-companion-0.12.39-post.txt`), same rule as the 0.12.31/0.12.32
drafts: do not resurrect. FP/whitelist submissions: Joel's hand, now for
0.12.40.**

**✅ THE MAELWYS FARM ARC IS CLOSED PUBLICLY (2026-08-16/17: models v45+v46,
three waves, two releases, one combined post — HIS ROUND-2 WAS RIGHT ON EVERY
COUNT).** v45 = AFK offense (auras full credit + ONE click auto-fire; only
scenario farm_afk reads `afk_st_dps`/`afk_aoe_dps`). v46 = his round-2 fixes:
**one auto-fire, one ledger** (when the attack claims the slot, the sustain
LABEL is passive-only — the v45 heal-on-autofire credit was a double-book) +
**momentum gates** (`engine.MOMENTUM_GATED_DISPLAY` = Whirling Smash + Follow
Through, client short help "Requires Momentum", censused 6 player records,
keyed by DISPLAY name, re-census at PATCH-WATCH — zero AFK credit, active
uptime stays the meter-class arc). ⚠ IG-was-a-toggle: our DATA was always
right (power_type 2); only release-note PROSE was wrong — check the data
before conceding a model error. Battery `tools/test_afk_offense.py` 12/12
(⚠ its sustain checks need `srv._stat_ctx`, never a hand-rolled ctx — a stub
ctx zeroed heal output and false-failed the negative control).
**Roster after the v45+v46 waves:** Spines/FA 243.2 (**honest +0x8 passive**)
· TW/Bio 274.5 (+3x8) · Tanker FA/FM 294.5 (+2x8) — labels refreshed via
`tools/refresh_afk_labels.py` (the designed relabel path; no wave needed for
label-only changes). Stability 28/0. ⚠⚠ **THE OPEN DESIGN QUESTION (Joel's,
stated publicly): tier-vs-objective** — the v46 TW/Bio challenger hit +4x8
FULLY-PASSIVE (38.9 HP/s) and LOST on contribution (120.6 vs 274.5); labels
are floors, not combo ceilings; whether the AFK tier joins the farm objective
is a certificate-doctrine ruling. Ledgered with it: the +5x8 tier (needs +5
enemy numbers) and the Stone Armor candidate (Brimstone, proc-valuation
ruling). ⚠ v0.12.42 SHIPS v45 labels — its GitHub notes carry a dated
correction section (gh release edit, Joel's word, 2026-08-17); **the v46
labels ride the NEXT release (0.12.43 owed for that alone)**. ⚠ At that
release: smoke_gold model pin 45→46. ⚠ Stamp noise: the quick check reads
"28 need update" on STAMP alone under v46 (scores unmoved; 21 keeps just
DEFENDED under a full v45 search) — do not read it as a wave owed.
✅ ANNOUNCED: Joel posted the combined round-2 reply + 0.12.41/0.12.42
announcement on topic 64761 (2026-08-17) — supersedes ALL prior drafts
(maelwys-farms-reply, 0.12.41-post; never resurrect).

**✅ v47 CLOSED THE ARC (2026-08-17 evening, shipped as 0.12.44 + posted):**
farm scenarios carry `dmg_type="Fire"` (survival reads Fire res +
position/Fire def in farms ONLY; untyped scenarios byte-identical, pinned) —
found because Maelwys's 90%-Fire RadM/FA measured ttl 6.6s in its own farm
(availability 0.102, the "20× contribution anomaly"). AFK auto-fire judged
at SPAWN scale (aoe ×6.0 vs st ×0.4 — Burn beats Boxing). ⚠⚠ **JOEL'S FIRST
EXPLICIT TIER OVERRIDE (precedent):** the v47 TW/Bio challenger lost by 1.4
pts (0.7%) but delivered +4x8 fully-passive — his "merge all three" took it;
the verdict FILE says supersede, commit `fa59b284` says WHY. An override is
HIS to make, never the gate's; always record both halves. ⚠ THE DAY'S PROBE
CORPSES (all three mine, all caught by verify-first): a PHANTOM PIECE UID
slots nothing silently (assert pieces resolve, same rule as powers) · a
census keyed on the wrong row field reads 0-of-146 (our rows key the
attribute as `effect`) · common IOs resolve via common_ios.json, NOT
PIECE_BY_UID. **The regen model was VERIFIED CORRECT end to end** — the
"missing regen class" alarm was retracted before any build; census
instrument: `tools/census_power_regen.py`. **Forum-build importer lives at
`coh-scorer-lab/measure_maelwys.py`** (Sidekick URL fragment → faithful
build → canonical + AFK label; conversion needs set_uid on slots or set
bonuses count ZERO, include_in_totals from power_type, and the inherents
section). Maelwys's examples under v47: Stone 244.5 @ +4x8 · FA 115.1 @
+3x8 — his sheets and our model agree.

**✅ v48 (2026-08-17 night, Maelwys round 4, Joel: "go with what fixes his
response"): THE AFK TIER GATE READS THE BUILD NOW — and the +4x8 TW/Bio claim
is WITHDRAWN.** He audited the shipped champions.json and was right on the one
that matters: the AFK ladder was ONE absolute (`AFK_SUSTAIN_ASK_HPS = 37.0`,
his reference number at capped Fire res + softcap def) scaled only by critter
accuracy — it never read the build, so tiers ANTI-CORRELATED with mitigation
(90%-res builds tier 0/2, the 63%-res TW/Bio tier 4 on regen alone).
`afk_sustain_assessment` now computes per-shift requirements from the build's
OWN typed mitigation via the score side's v47 arithmetic (`incoming_hit` +
`_def_against`, DDR erosion, res capped 90; toggle −ToHit deliberately not
credited — conservative, stated), prints the basis on the label, and stamps a
`mitigation` block on the cert. Result: **all three farm_afk labels honestly
read "active play only"** (relabeled via refresh_afk_labels; scores
byte-identical — evaluate_first all UNAFFECTED Δ0.0; stamp noise v4x<48 is the
documented label-bump artifact, no wave owed). heal_rates rows carry
`counted:` so the ledger can't be misread as summing click heals (it never
did — his (i) was that misread; his (ii)/(iv) were internal-name misreads:
`Sweeping_Strike` displays "Titan Sweep", Bio `Adaptation` displays "Evolving
Armor"). Batteries: test_afk_offense 21/21 (+6 v48 checks) · demo 24/24 ·
slotting 11/11 · validate 28/28. smoke_gold model pin 47→48. Changelog staged
Unreleased; **release owed for the labels (carries the withheld v46 labels
too)**. Reply draft: `Downloads\maelwys-round4-reply.txt` (posting = Joel).
⚠ The 08-17 tier override's premise (the +4x8 label) is gone — the merged
TW/Bio champion STAYS (scores unmoved) but whether the override stands is
JOEL'S open ruling. ⚠ His two UI gaps queued: no champion-build surface (he
read _internal by hand), no from-empty manual build path (generate-then-delete
is the only route today). ⚠ The three farm_afk slotting layers remain dropped
since the 08-17 merges (solver serve, honest) — re-refine wave owed at Joel's
word.

**✅ v49 (2026-08-17 night, Joel: "Make the rule and run the wave") — AFK
SUSTAIN JOINED THE FARM OBJECTIVE, wave banked same evening.** The
tier-vs-objective question is CLOSED. Mechanism (farm_afk only, others
byte-identical, pinned): survival is PASSIVE-ONLY (`_afk_autofire_heal` = ONE
copy of the auto-fire selection rule shared by ledger and score; click heals
excluded, negative control keeps general crediting them) and the window is a
600s AFK STINT (was 60s) — non-sustaining builds collapse in availability, so
the requirement rides physics, not a ban list. Wave: 3 workers / 20.7 min /
3/3 SUPERSEDE (gains +325/+5/+178), merged, layers refined+banked for
Spines/FA (499.1) + TW/Bio (292.6); **FA/FM refined layout would not seat —
the lab seed-parity class now holds THREE contexts (Tanker Inv/SS, PB base,
Tanker FA/FM)**. Labels restamped FROM THE SERVED BUILDS (banked layer or
live solve — the wave cert's build is NOT what serves once a layer banks; a
label written at cert time can lie the moment banking changes the serve).
⚠ **OPEN TENSION, Joel's word pending: the score-optimal banked layers traded
away the wave builds' tiers 2/0 → None** (+4x8 sustain is worth ~12×
availability but is unreachable for all three combos, so tiers 0-2 carry
little weight at scenario shift 4 — the objective chose score, per the
ruling; serving the tier-holding wave builds instead is a one-word override).
⚠ `wave_pop` keys are ONE comma-separated argv — multi-arg invocations
silently run only the first key. ⚠ recert_verdicts preserved
`.banked_v49_2026-08-17` (overwrite trap). Batteries: afk_offense 25/25 ·
demo 24/24 · slotting 11/11 · validate 28/28 · stability 28/0. Integrated at
stamp `05b6d9f` (smoke + gold PASS, model pin 49, installed copy mirrored +
relaunched, wizard explainer verified through the real path + real window via
computer-use). Pushed `769ffed7`. **Release owed: carries v48 (honest gate,
+4x8 claim withdrawn) + v49 (objective + re-converged champions); changelog
staged; reply draft `Downloads\maelwys-round4-reply.txt` updated with the v49
paragraph — posting is Joel's hand.**

Otherwise nothing running. Live handoff detail:
`coh-builder/RESUME-HERE.md`.

**Latest release: 🚀 v0.12.38 "The window that says why"** (2026-08-11, stamp
`92bc365`, signed, API-verified; installed copy mirrored + relaunched): an
engine that fails to start is CAPTURED (traceback to app.log, reason held for
the UI) and the window shows a diagnosis page instead of navigating to a dead
port. Battery 141/141; data 2026.1.1242 + model v44 unchanged. ⚠ Awaiting
Glacier Peak's answer on topic 64761 (app.log lines + installer-or-portable);
thread checked 2026-08-11, nothing new after Joel's posts.

**▶ OPEN, in Joel's order:** (1) ~~verdict-gate legality hole~~ **CLOSED**
(07ce596e + tools/test_verdict_legality.py — legality outranks score, all four
branches, fail-safe on unmeasurable) · (2) Iron Man accolade grant (Joel's
in-game look) · (3) origin plates extracted but unplaced · gaming box silent
since 2026-07-29 11:51 (dual-3090 + 1200W rebuild pending — Qwen3.8-27B slated
for it) · drafted forum/Discord posts unsent · reduced-motion ·
strict-dominance experiment.

**Queue (carried forward):** budget/balanced/premium as a REAL player choice
again (the tier dial is vestigial; do not resurrect R3-as-posed) · Leveling
Companion batch (shares the Journey surface) · Fury meter class
(Fury/Rage/Domination/Defiance/Gauntlet — no public Brute damage absolutes
until then) · pricing #31 (single-claim pairing) · 18 inherent icons
(optional) · i24 archive content (Joel's torrent hand) · alias-map roster
reconciliation + Power Boost amplifier effects (parser allowlist family) ·
Maelwys leftovers (CJ-vs-Weave slot modeling, attack-card wording awaiting
Joel's text) · **Lite is at 0.1.18** (notes saying "0.1.17 next" are stale).

Standing rules and facts that survive the moved narratives:

- **⚠ `#masthead` carries an ID and outranks `body.theme-x header`** — the
  themed header gradients have NEVER rendered on hero or villain; the middle
  theme is scoped `body.align-mid #masthead` to win; the other two are left
  DEAD on purpose — reviving them changes both shipped themes, Joel's call.
- **The tie-break machinery (engine-accuracy item 5, shipped):** solve_ilp
  takes tie-break STYLES per-call — "eps" (folded into step 1, HC_TS_EPS cap
  0.001, measured 1.05× = free) is the DEFAULT everywhere incl. sweeps; "lex"
  = the two-solve step 2; per-call param, NEVER env (the sweep pool is
  threaded). **deep_optimize's finale solves the winner under every style and
  PHYSICS picks** (cert["tie_arbitration"]); serve-time /build/solve
  physics-arbitrates too (preserve/keep-layout/perk-chip skip). NOT a model
  bump. Plateau bound-proving is INTRINSIC (eps falsified the
  degeneracy-collapse hypothesis). Joel's tie-break ordering (recovery first,
  then role) measured and stands.
- **⚠ Probe isolation:** any deep_optimize probe warm-starts from
  HC_CHAMPIONS_PATH and appends to the REAL exploration log — back-to-back
  probes on one context are NOT independent; isolate scratch paths PER ARM in
  separate processes, or the ladder measures learning, not the variable.
- **Single-solve tie deltas predict NOTHING about converged outcomes** — the
  sweep + arbitrated finale decides; the verdict gate protects the roster.
- **Merge safety, verified not assumed:** workers write ONLY their own shard
  (HC_CHAMPIONS_PATH), never champions.json — merging while a worker runs is
  safe; merge_champion_shards filters PER CONTEXT against --verdicts, so
  mixed shards need no manual splitting.
- **⚠ recert_verdicts OVERWRITES per invocation** — always regenerate complete
  (ALL shards) before any merge.
- **Count from the artifact, never the narration** — the recorded wave-week
  errors (stale figures re-quoted, counts incremented from monitor events)
  all shared that thread.
- **⚠⚠ Release-announcement rulings:** the 0.12.31 and 0.12.32 announcement
  drafts were NEVER posted and never will be (the 0.12.33 post superseded
  them; Joel cut the catch-up paragraph) — so **nothing public has ever
  announced that the app stopped being a browser tab**; a "why is this not in
  my browser" field report is that, not a bug. The 0.12.33 post publicly
  corrected the update-check claim (watch item CLOSED) and states
  `/thumbtack` is untested in game (confirmation = the trigger to strengthen
  it). FP/whitelist submissions per docs/signing-runbook.md are Joel's hand.
- **⚠ The 0.12.34 refill failure was never root-caused** — the
  verify-and-refuse guard makes the symptom impossible; that is a guarantee,
  not a diagnosis.
- **Release-hold rule that survives:** nothing publishes without Joel's
  say-so; changelog entries stage under "Unreleased" until he approves.
- **Remote worker kit** (tools/remote_worker/ — README is the authority): the
  box crunches, the laptop conducts. OUTBOUND-ONLY: the box polls
  `%OneDrive%\HeroCompanionCompute` and git-fetches the public repo pinned to
  the order's commit — no ports/tokens/inbound. send_work refuses unpushed
  commits; **the box NEVER merges** — laptop verdict gate only; canonical
  scoring stays laptop-side. Box = i9-9900K 8C/16T (~50% fleet add; orders
  may omit `workers`, auto-sizes to 3 there). Claim latency ~7-10 min
  observed. Retire: `schtasks /delete /f /tn HC_RemoteWorker`. ⚠ GitHub
  sign-in is never needed on the box.
- **Slotting-remainder rulings that stand:** R1 = an unpinnable pet fact
  HOLDS its sub-piece with an honest label; R2 = champions may use HOs
  **only in endgame content presets** (`_HO_CONTENTS` = itrial/farms), every
  HO carries an attain note; R3 = MOOT AND DEFERRED. Pet-hit facts +
  citations: docs/pet-tohit-sources.md. Proc-trade + HO display surfaces
  shipped with batteries (test_proc_trade_note, test_pet_hit_v38,
  test_ho_solver).
- **⚠ homecoming.wiki route: Claude-in-Chrome (Edge) ONLY** — the in-app
  browser pane CRASHED Claude desktop twice on that site; automated fetchers
  403.
- **Reconciliation-lane guard:** a one-to-one value sync requires our side to
  have EXACTLY ONE row — the unguarded draft multiplied client values onto
  every flattened row (4× overcount, caught pre-commit).

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

The graphify command rules live in the parent CLAUDE.md files (one copy).
