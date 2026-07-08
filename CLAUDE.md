# Hero Companion — Session Memory (CLAUDE.md)

Claude Code reads this file automatically at the start of every session.
**Standing rule: when a session establishes a durable fact, workflow, or decision, update this file before the session ends.** Do not let knowledge die with the session.

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

## Release rules

- Nothing is released without Joel's say-so — **always ask before `gh release create`, asset uploads, or publish-intent version bumps.** Commits and pushes stay autonomous. Changelog entries are staged under **"Unreleased"** until he approves.
- "Please make it a rule to not immediately deploy an update until after I have gone over all the issues we need to fix first." Batch fixes; wait for his full field report.
- **champions.json bundles with EVERY release** (client is deterministic, NOT AI — champion knowledge ships as data). ⚠ CHAMPION-MASK TRAP: source tests can pass via hub-only champions.json while standalone users hit the heuristic picker — **smoke-test the FROZEN exe before every release** (pinned Defender Poison/Sonic case).
- Release procedure: bump VERSION → CHANGELOG date → `python tools\build_help_pdf.py` → stop HeroCompanion processes → PyInstaller `HeroCompanion.spec --noconfirm` → copy "Add Shortcuts.bat" into `dist\HeroCompanion\` → frozen-exe smoke → ISCC (`%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe` — per-user, NOT Program Files) → Compress-Archive zip → commit/push → `gh release create vX.Y.Z` with BOTH assets (Setup exe + zip) → verify via `gh api .../releases/latest`.
- The repo is public on GitHub (github.com/joelc67/hero-companion; Joel's GitHub = joelc67, gh CLI authed in keyring). Keep raw brainstorms and personal notes out of commits. Ideation notes live in `C:\Users\joelc\code\ideas.md` (outside this repo); when Joel says "read ideas.md", that's the file.
- License CC BY-NC-SA 4.0 ("free and noncommercial, forever"); truthful credits always, including the Claude co-author line on commits ("Leave it, its true").

## Credits

- **Maelwys** (https://forums.homecomingservers.com/profile/30623-maelwys/) is to be included in CREDITS for his feedback contributions. ✅ Done 2026-07-08: "The Reviewer" section in CREDITS.md + the help.md credits paragraph.

## Design principles (from Joel)

- One shared pool of game-engineered rules, but **every champion/build is unique unto itself** — the planner must not treat builds as one-size-fits-all within that rule scope. (Recorded at the top of docs/build-doctrine.md.)
- Audits/checkmarks are not ground truth — Joel's eyes outrank green audits. Coherence audits must hard-fail on empty slots, icon-less pieces, and validation noise.
- **Role doctrine**: CoH is a role-based game first. The Role picker is the declared objective; off-role is only ever an explicit user choice (warn, don't block). Support/control roles follow the **invisible-role doctrine**: their output must be exceptionally powerful just to be noticed — maximize debuff magnitude × uptime, control reach, sustain; never generic damage slotting on a non-damage role.
- **Optimization doctrine ("3D chess")**: think to the END — converge with restarts and honest certificates, never truncated-as-done; explore, don't prune; **NO ban lists** ("This picker is not a child") — when the search picks trash, fix the model term that made trash look good; LEARN across runs (champions/marginals/lessons/retrospective); masters are evidence and a floor to beat, never prescriptions ("evolve BEYOND master setups").
- **Wiki-verify / GAME-FIRST**: never build on best guesses. Order of authority: game client bins (`C:\Games\HC2\assets\live\` via Bin Crawler/Pigg Wrangler in tools/gamedata) → dev-archive docs → measured logs → wiki paste from Joel (wikis block WebFetch) — never fan posts. When the tool and the game disagree, the game is right.
- **Universal rules, no hacks**: a game-rule fix is implemented archetype-independently and proven with an all-AT audit (audit_epic_tiers / audit_slot_schedule pattern) — never patch just the reported case.
- **Harden-before-certify rule (Joel, 2026-07-08)**: no long certification run (champion refresh, release battery, gold-standard regeneration) STARTS while a correctness question is open or a verification improvement is pending. Certification runs are expensive to invalidate; verification changes are cheap to land — sequence cheap-and-clarifying before expensive-and-committing, always. (Context: the v28 refresh launched before the coverage-denominator retrofit, which then surfaced questions that put a running 2-hour refresh at risk for the third time in one day.) When a question surfaces mid-run: model/data-affecting → stop the run immediately; out of scope → make the checker state the exclusion explicitly so it is never rediscovered.
- **Coverage-denominator rule (Joel, 2026-07-08)**: every audit/reality check/battery prints **"N of M expected checked"** where M comes from an independent source (game snapshot count, data enumeration done OUTSIDE the check loop, or a pinned constant) — and **hard-fails when N < M**. A checker that can't state its denominator can silently lie (twice in one day: the coherence audit never examined icons, the set-bonus check silently verified 43 of 282 values). Retrofitted 2026-07-08 into demo_single_build_fixes, audit_slotting_coherence/slot_legality/slot_schedule/epic_tiers, reality_check_setbonuses/procs/gamedata/powers/converter.
- **Choice doctrine**: "People should always have a choice." Anything touching user data/machines = informed opt-in, remembered + reversible "no", advise-don't-override; sharing consent separate from local capture; anonymous by default; NO PII ever.
- Copy rules: never say "illegal" bare ("the game won't allow it" instead); plain English before jargon; "easiest route, never the only way"; **no em dashes in outward-facing text Joel sends** (Discord/forum — "dead AI giveaway").
- Hasten: Joel dislikes relying on it (crash + only one auto-fire power); Guyver's rule = never past 2 slots. Vocab: a "mule" = a dual-boxed alt character, not a bonus-holding power.

## Project history (condensed; full transcripts in ~/.claude/projects/, memory files in ~/.claude/projects/C--Users-joelc-code/memory/)

- **2026-06-16→17 — prototype**: Flask + vanilla-JS planner; data parsed from Mids Reborn `.mhd` (clone at `C:\Users\joelc\code\MidsReborn`, tools/parse_mids.py → data/*.json). Builds were AI-generated (three tiers Budget/Balanced/Premium via headless Claude calls) — slow, inconsistent, mis-prioritized.
- **2026-06-19 — the solver thesis**: "It's got nothing to do with imagination, it's an equation — 3D chess. Start with the optimal outcome, then make the pieces fall into the right slots." → ILP (PuLP/CBC) in solver.py; AI generation demoted, later removed from the client entirely. Costume/3D-render side quest attempted and killed ("Remove all the code for a costume maker") — parked in `_archive_costume/`.
- **2026-06-29→30 — import & correctness era**: unique-flag enforcement (mutex regular/Superior), in-game `/build_save_file` .txt import (from `C:\Games\HC2\accounts\<acct>\Builds\`), Mids .mbd import/export round-trip (positional PowerEntries), preserve / keep-layout modes, "no empty slots ever", cheap-IO restore as default rule, content×role presets replacing free-text goals, content-aware incarnate recommendations, per-AT caps (res 90 Tanker/Brute, 85 Kheldian/VEAT, 75 rest). **The big pivot**: end-game optimizer → character COMPANION (entry cards: Continue / Start new / Respec 50 / Import; discovery recommender; 1–50 leveling stepper as a "constant evaluator — you are not peddling a finished product, you are helping them succeed").
- **2026-07-01→02 — role system + first-principles model**: role-aware slotting everywhere; first_principles.py encounter model (wiki-verified hit/purple-patch/AV-resist/protection physics), deep_optimize (convergence + restarts + certificates), learning stack (exploration log, marginals, champions.json = PICKS only, lessons, retrospective), full delusion sweep (benchmarks/full_sweep.py, 2703 combos), model v10→v23. Master corpus (42 .mbd in benchmarks/masters) as the benchmark floor.
- **2026-07-03 — LAUNCH**: repo public, HC forum topic 64761 (as Pulsekin), Mids Reborn Discord note, LICENSE/TERMS/CREDITS/help PDF, AI-free client (`HC_AI=1` opt-in seam), releases 0.9.0→0.10.0 (installer/tray/self-update).
- **2026-07-04→05 — Guyver + UI**: Guyver [SoV] donated 4,187 builds → model v24 (PPM procs, typed-35 meta targets, positional swap); masonry "puzzle pieces, no gaps" UI redesign; slot-grant schedule (49-pick ≤4 slots); L1 creation pair rule (one primary + one secondary at creation — secondary first on some imports); Play Log begins (chat-log reader, consent-gated).
- **2026-07-05→07 — Maelwys round 1 + game-first data**: his review (off-role warning, damage linter, PP tier, 43.8-vs-45.1 defense, "spaghetti at a wall") drove 0.12.9–0.12.11; his 2nd reply exposed ~6-month-stale Mids data → game-client bins became the authoritative source (reality checks: modifier tables, conversion sets, clientmessages). Henchmen priced from live game (v26), then v27 (−res anchors all roles, Force Feedback, 62 Hamidon Origins, dev-verified PPM area factor) in 0.12.13; 0.12.14 synced the game's July 7 patch. Pulse Boards + Companion Lite shipped in parallel (0.1.x; separate memory files).
- **2026-07-08 — Maelwys round 2 + regression day**: 0.12.13 shipped a loop-splice (common IOs lost icons = "empty slots"); 5-slot attack cap root-caused (ILP budget overspend + order-blind trim + bomb shrink); HO stacking legality; +58913% MaxHP units bug; all fixed & staged for 0.12.15 behind `tools/demo_single_build_fixes.py` (10 checks on the Bots/Marine case). "How do you play" explainers + summary panel added (`/build/explain_intent`).

## Architecture map

- `server/server.py` — routes, autopick, tray layout, slot plans, explain_intent, endurance relief, release of everything. `server/solver.py` — ILP (options per power, coverage objective `priority×kind_mult÷target`, damage reward w/ 6th-slot credit, exact added-slot budget, value-aware trim, globals pass, common fills). `server/engine.py` — totals/ED/validate/offense/`_scaled_boosts` (PIECE_REF_LEVEL scaling; HOs deliberately have NO ref level). `server/first_principles.py` — encounter model (MODEL_VERSION). `server/proc_pass.py` — post-ILP proc bombs/ST hybrids/−res anchors/FF (all guarded by `_last_swap_safe`). `server/ai_build.py` — presets, goal interpretation, incarnates. `server/mids_import|mids_export|ingame_import.py`, `server/converter.py` (enhancement-converter planner; cheap→purple impossible), `server/role_output.py`, `server/gamelog.py` (Play Log).
- `static/app.js` (SPA) + `index.html` + `style.css`. `data/*.json` from tools/parse_mids.py + game-bin extractions. `benchmarks/` (masters corpus, champions.json = picks+score+certificate keyed `Class|primary|secondary|content`, full_sweep). `tools/` — audits (epic tiers, slot legality, slot schedule, slotting coherence w/ hard-fail pins), reality checks (procs/gamedata/powers/setbonuses), demo_single_build_fixes, smoke_gold/smoke_release, refresh_champions, build_help_pdf, parse_mids, gamedata extractors.
- AI seam: `AI_ENABLED = os.environ.get("HC_AI") == "1"` — client ships AI-free; the hub (Joel's dev box) opts in.

## Recurring pitfalls & tooling quirks

- solver/champions: `/build/solve` preserve defaults TRUE for imported builds (proc pass skipped unless `_generated`); champions.json read per-request; the ILP's slot budget counts pieces (67 + one base per power) — empty powers charge a reserved base piece.
- The app's real solve payload includes `slots`, `earned_slot_count`, `exposure`, `tier` — test through that path, not a bare minimal POST (the tightened coherence audit does).
- PowerShell 5.1: embedded quotes break native args — use `-F`/`--notes-file` message files for git/gh; run gh and git steps separately. Bitdefender is heuristic-sensitive (flags powershell one-liners with tokens, .bat shortcut creation).
- Preview gotchas: wizard `init()` startFromScratch wipes eval-staged builds; frontend caches hard.
- Joel's gaming machine is a SEPARATE box (Windows user "Joel Chambers"); shares files via OneDrive → `C:\Users\joelc\OneDrive\Desktop\temp` (one-time imports only — Joel vetoed OneDrive as infrastructure). Raw game logs archive: `C:\Users\joelc\code\game_logs`.
- Python: `C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe`. gh CLI: `C:\Program Files\GitHub CLI\gh.exe`.
- ⚠ NO agent fan-outs / deep-research without Joel's explicit opt-in AND stated cost (a 106-agent run once produced ~50 permission popups and forced a reboot). "Research" = existing knowledge + local data + a few direct fetches in the main loop.
- ⚠ While a champion refresh runs, **benchmarks/champions.json belongs to the refresh process**: never `git add -A`, `git checkout --`, or otherwise touch it (near-miss 2026-07-08: a blanket add-A committed a mid-refresh save, the checkout-revert then erased it from disk — recovered byte-exact from the reflog blob). Commit champions.json once, complete, after validate_champions. deep_optimize re-reads the file per write, so a restored file merges cleanly with the running process.

## Session history & retention

- Claude Code transcripts live under `~/.claude/projects/` (`C--Users-joelc-code` = main; `C--Users-joelc-code-coh-builder` = the app's own June-16/17 headless AI calls). Distilled memory files: `~/.claude/projects/C--Users-joelc-code/memory/` (MEMORY.md index + per-topic files) — richest cross-session source.
- **Transcript retention was the silent history-killer**: `cleanupPeriodDays` was unset → 30-day default deletion. Set to **3650** in `~/.claude/settings.json` on 2026-07-08. Anything older than ~June 16 2026 was already lost (unverifiable; earliest surviving transcript is 2026-06-16).

## ⭐ CURRENT STATE (2026-07-08 midday) — accuracy term LANDED; refresh running; 0.12.15 gate unchanged

**Accuracy term done (commit 2194bb2) — the real root cause was DATA:** parse_mids's Enhancement-relabel allowlist was missing "Accuracy", so ALL 65 global-accuracy set bonuses (LotG 4pc +9%, ATO +15%s…) parsed to empty effect lists — invisible to engine totals, scorer AND solver since launch. Fixed: parser rule + `tools/patch_accuracy_bonuses.py` back-fill from the game snapshot (65/65 game-verified). Set-bonus reality check name matching also fixed (was silently checking 43 values; now 282, 0 drift). Solver term derived, no magic weights: target = headroom to the 95% hit ceiling from the scenario's player-vs-+N table (rides preset targets as `out["scenario"]`); weight = recharge's per-fraction weight × scorer marginal ratio (1/(1+acc₀) ÷ 0.5/(1+rech₀)). Battery all green (demo 13/13, pins PASS, audits 0, reality checks 0 drift). iTrial probes: MM saturates ceiling (+43%, Adjusted Targeting x5 in Tactics); RF×5-vs-LotG×4 now an honest judged trade (accuracy saturates via cheaper hosts).

**Champion refresh RUNNING** (launched ~11:00, v28 complete, gold defaults, log champions_refresh_postfix_log.txt). On completion: validate_champions 5/5 + battery, report scores. Then **0.12.15 staging is complete — awaits Joel's green light + his 5080 eyeball** (wizard explainers, card notes). NEVER release without his word.

⚠ Push discipline: the Pulse Boards pipeline pushes to this repo's master (~230 commits found 2026-07-08); 12 local commits had never been pushed. After every commit: push; on rejection, `git pull --no-rebase` (merge, never rebase — session reports quote hashes) then push.

Excluded from the batch (post-refresh, documented): #4 Fighting-pool autopick scoped to content=team (itrial champions unaffected), enhancement levels/+5 boosters (#6), manual HO slotting (#7), suppression toggle (#9), henchman +MaxHP inheritance (UNVERIFIED — bins pass or wiki paste is the gate). Queued design (ideas.md, no code yet): "Champion build" wizard checkbox — mechanics answers in session-report.md 2026-07-08 fresh-session entry.

## Open work queue (as of 2026-07-08)

- ✅ "How do you play" section (done 2026-07-08, unreleased): `/build/explain_intent` endpoint
  (server.py, after `_off_role_notice`) derives tailored per-choice explanations + a combined
  summary from the SAME presets the solve uses (ai_build.preset_targets/ROLE_PRESETS/
  CONTENT_PRESETS — never drifts). Frontend: `wizExplain()` in app.js, `#wiz-pop` +
  `#wiz-summary` in index.html, styles in style.css. Pop-up fires on each wiz select change;
  character changes re-tailor the open pop-up + summary. Awaiting Joel's 5080 hard-reload check.
- Maelwys post tasks #3–#10: CJ vs Weave/Maneuvers slot placement (needs end-cost + toggle-magnitude modeling; verify henchmen +MaxHP inheritance game-first in client bins), autopick Fighting pool for team-damage MM, enhancement levels/+5 boosters, manual HO/DSync slotting, suppression toggle, attack-card decision-note wording (awaiting card text from Joel).
- 0.12.15 staged (changelog under Unreleased) — release only after Joel reviews `tools/demo_single_build_fixes.py` output and green-lights.
- Model v28 queue: aura procs from MEASURED 56.7%, mez magnitude, endurance assumption, autopick retunes. Pricing layer #31 (single-claim pairing). Lite 0.1.15 (new parser + iTrial channels). Demorecord attendance, /copychat rescue.
- **Found by the coverage-denominator retrofit (2026-07-08), queued v29/data work:** (1) the game's 11 heal-strength set bonuses (Numina 4pc +6% heal…) are absent from our data AND untracked by the model — same class as the accuracy gap (stated exclusion in reality_check_setbonuses); (2) 221 of 3,987 player-facing powers are UNVERIFIABLE against the client snapshot — internal-name divergence (ours "Temporal_Manipulation" = client "Time_Manipulation", Electrical Affinity, ~15 Epic pools, 39 inherents) — alias-map reconciliation needed; those sets' values haven't been game-verified since the pivot (pinned register in reality_check_powers, fails on any change).
