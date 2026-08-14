# CLAUDE.md ledger — superseded history moved out of the always-loaded file

Moved 2026-08-14 from coh-builder/CLAUDE.md on Joel's ruling: embed old knowledge
in the repo + graphify instead of the per-session context. Content verbatim,
nothing edited. CLAUDE.md keeps standing rules; this file keeps the history.

- **⏰ (superseded, kept for the reasoning) RE-ENABLE THE INBOX WORKFLOWS ON 2026-08-01 (both `disabled_manually` since 2026-07-27).** `gh workflow enable "Collect mailbox" --repo joelc67/hero-companion-inbox` and the same for `"Inbox maintenance"`. **Why disabled:** the private repo's billed Actions minutes ran out after the 7/14 runaway; from 7/16 every scheduled run failed at startup in 2-4s with zero steps and mailed Joel each morning. Nothing lost. **Cost was always $0** (GitHub Free refuses to start jobs rather than bill; billing page: gross $53.32 fully offset, billed $0 every day). **Leave the spending limit at $0 — that is what guarantees it can never cost money.** After re-enabling, confirm the next scheduled run succeeds; failing in seconds with zero steps = allowance not reset. ⚠ Do NOT "fix" this in the workflow files — there is no workflow bug. ⚠ Billing API needs gh `user` scope (not granted; don't re-auth).

## Project history (condensed; transcripts in ~/.claude/projects/, memory files in ~/.claude/projects/C--Users-joelc-code/memory/)

- **2026-06-16→19**: Flask+vanilla-JS prototype from Mids .mhd data → the solver thesis ("it's an equation — 3D chess") → ILP (PuLP/CBC); AI generation removed from the client; costume side-quest killed (parked `_archive_costume/`).
- **2026-06-29→07-02**: import & correctness era (unique flags, in-game .txt + .mbd round-trip, preserve modes, per-AT caps); the COMPANION pivot (entry cards, discovery, 1-50 stepper); role system + first_principles encounter model + deep_optimize + learning stack; model v10→v23; masters corpus as the floor.
- **2026-07-03 LAUNCH**: repo public, HC forum topic 64761 (as Pulsekin), LICENSE/TERMS/CREDITS/help PDF, AI-free client (`HC_AI=1` seam), 0.9.0→0.10.0 (installer/tray/self-update).
- **2026-07-04→08**: Guyver's 4,187 builds → v24; masonry UI; slot-grant schedule; Maelwys rounds 1-2 → game-client bins became the authoritative source; henchmen priced from live game; 0.12.9→0.12.15 ("verified-data release"); regression day fixes behind demo_single_build_fixes.
- **Release ledger since:** 0.12.16 "inheritance" (7/09, v29 henchman set-bonus inheritance + heal-strength) · 0.12.17 "display-only" (7/10, custom targets + booster preview + Power Boost amplifier + IO detail cards) · 0.12.18-0.12.20 (v30-v31, roster split, ladder-fit gate, AFK farm champion "+3x8" honest label) · 0.12.22 "FIRST SIGNED" (7/21, v34 MM pet-buff; release-night walk loop = 4 pinned class fixes incl. the invisible-confirm hang) · 0.12.23 (7/21, v35 endurance physics + full-roster wave + Build-Assistant locks/targets) · 0.12.24 (7/23, Leveling Journey v1 + wizard one-copy + farm gates + v36 meters + opt-in auto-start) · 0.12.25 "THE JOURNEY GROWS UP" (7/23, zone splash art + badge locations/directions + TF levels + challenge checklists + con reads + routes + alignment preview) · 0.12.26 (7/24, Web3Forms in-app bug reports + power icons 4949→6033 via patch/extract pipeline + Journey polish + Play Log dedup) · 0.12.27 (7/26, refuse-with-remedy fixes for legendaryjman + Troo — first release driven entirely by field reports) · 0.12.28 "security" (7/27, escHtml/XSS/realpath/stack-trace fixes) · **0.12.29 "The guided tour" (7/27T22:58Z, af28d2bf: 56-step tour + CSRF guard + corrected help)** · 0.12.30 "Accuracy pass" (7/31, v38 + 24/24 recert) · **0.12.32 "The Stats page becomes a workbench" (8/06T23:02Z, e164fd13: per-IO worth measured by counterfactual + Swap/Remove in place + the universal edit receipt with Undo + the swap picker pricing every candidate via `/build/slot_compare` + the unique-once-per-build picker gate + the green-marks legend + the 390-badge catalogue with `/thumbtack` rows + Flashback landing + honest empty art states + the exploration-log streaming read (89.3s/6.17GB → 29.3s/393MB, byte-identical) + reduced motion reaching the JS scrolls; data 2026.1.1242 and model v38 BOTH unchanged, so no score moves)** · **0.12.33 "Knowing what to do next" (8/07T22:35Z, 898653a: the order-to-work-in band + tour step, the Assistant/Stats ledes, the epic-swap refill, the Gymnastics repair, the phantom receipt + undo-stack leak + per-character sweep, the three panel outlines; data 2026.1.1242 and model v38 unchanged, zero champion exposure on the one data edit)** · **0.12.31 "The desktop app" (8/05T20:35 ET, b2161e12: WebView2 window/no tray, four tabs, four-way alignment + wordmarks + emblems, exemplar arc, split role + output panel, per-power improvement report, buff/debuff reads slotting incl. recharge, one import door + Mids round-trip pin + special-origin names, portable-update refusal, rebuilt 63-step tour, 94 Alpha icons; docs/index.html disclosure flipped to the window truth in the same pass)**. All signed CN=Joel Andrew Chambers from 0.12.22 on; every release: frozen smoke + gold 24/24 SERVED; data currency 2026.1.1242 / model v38 since 0.12.30.


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

- **(superseded) the 2026-08-07 report.** The client ships, per power,
  self-targeted `Strength` templates across all EIGHT damage types (scale 0.8
  and 4.0, duration 15s/30s) beside the ToHit ones. **Our records carry only the
  ToHit half.** Verified on Aim, Build Up, Rage, Follow Up, Power Build Up, Soul
  Drain, Spirit Drain: 6 of 6 have no self +Damage. Root cause is the known
  `parse_mids` Enhancement-relabel allowlist — ToHit is in it, **Damage is
  not** — the same family as the v28 accuracy and v29 heal-strength bugs, but
  far wider than the queue records. **THE CODE ALREADY KNOWS**: server.py's
  `_DMG_ENABLER_NAMES` comment says *"the data files these outside buff_effects
  … Build Up/Soul Drain in self ToHit, so detect by name"*, and it compensates
  BY NAME at the picker (`_ps_priority` +9) and the slotter (`is_steroid`) — so
  these powers get taken and slotted while the MAGNITUDE is never modelled.
  **MEASURED through /build/calculate: adding Aim moves displayed ST DPS by
  0.0.** Exposure, counted over 624 picks: Build Up in 6 champions, Aim in 2 =
  **7 of 24 certified champions**, so crediting it is a MODEL BUMP owing a
  re-cert — Joel's ruling. ⚠ **It is the same capability as Fury / Power Boost
  and must be built with them**: a temporary MODE with an uptime, not a flat
  add. Maelwys's point (a 240s Soul Drain cannot be cycled with a nuke while a
  120s Spirit Drain can) is this same gap seen from the gameplay side — our
  picker scores both at 19.0 because with no magnitude and no uptime the only
  lever left is a name in a list.

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


- **🧾 v38+HO WAVE COMPLETE 24/24 — ✅ MERGED (superseded by the 2026-07-31 recert above; kept for the deltas).** `recert_verdicts.json` (written 2026-07-30 00:10): **4 SUPERSEDE** (Crab_Spider_Soldier +181.3 — this also CLOSES the named autopick defect that failed every leg of the previous wave · Spines/Fiery_Aura +92.4 · Poison/Sonic_Attack +50.9 · Broad_Sword/Super_Reflexes +4.1) / **20 KEEP**, zero collapsed runs, zero eval failures. The gate re-scores BOTH sides fresh under v38 (canonical vs canonical, CBC pinned) so the deltas are real; a mostly-KEEP outcome is the NORMAL shape of a recert wave (the prior wave was 3/20), not a defect. Large negatives cluster on Kheldian per-form contexts, where the form context BANS powers the incumbent build holds — the recert searches a strictly smaller space and cannot win by construction. **Merge = by context, `--verdicts`, canonical winner kept, shards retired `.merged_2026-07-30` — awaits Joel's word.**

- **Wave-run history worth keeping:** ran across the laptop + gaming box; the box was stopped mid-order and its 2 finished champions came home via the new orphan-rescue (2505c2a0) rather than being lost. Drop-dead pauses fired clean twice (4:10 PM, then armed 6 AM). ⚠ `bench_solver_e2e` running beside the wave killed 10 in-flight contexts — several hours of compute, nothing corrupted; see the speed-ledger guard warning.


## 🖥 DESKTOP APP — the full entries, moved 2026-08-14 (rules kept in CLAUDE.md)

Each entry below is the VERBATIM original: the ruling plus the build story
behind it. The condensed rules live in coh-builder/CLAUDE.md.

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
- **🚀 THE LAUNCH IS STAGED, AND EVERY STAGE WAS MEASURED (2026-08-10, Joel:
  "some latency when loading... do we need a prelaunch loading bar like Mids?").**
  Before: double-click → 3.8s of NOTHING (the game database loaded before any
  window could exist). Now three stages: **bootloader splash at 1.3s**
  (PyInstaller `Splash`, assets/splash.png generated with Pillow in brand
  colors; the ONLY thing that can paint early — measured, the WebView2/.NET
  window costs ~3.7s to exist no matter what) → **app window at 3.6s** on an
  in-window HTML splash (`_SPLASH_HTML` in run_app; honest spinner, NEVER a
  progress bar) → **engine ready at 4.1s**, when `_navigate_when_ready`'s
  socket probe swaps the app in. Three structural rules with corpses:
  (1) `import server` is LAZY (`_load_server` on the server thread) — a
  top-level import made the window the last thing to exist; (2) **the server
  load starts FROM `webview.start`'s callback** — starting it on a plain
  thread earlier bought nothing because the 17MB json parse holds the GIL and
  starves the GUI thread (measured: window still 3.8s); (3) `pyi_splash.close()`
  fires on window-up AND on the no-window fallback, and the shutdown hook
  wires only when the lazy server exists (disarmed if the window died).
  ⚠ The spec excludes tkinter but `Splash` packs its own Tcl runtime —
  compatible, build-proven. ⚠ test_desktop_app pins all of it (138 checks).
- **🧭 LAUNCH LANDS ON POWERS & SLOTS, ALWAYS (Joel, 2026-08-10: "each time my
  tool loads, its starts on the leveling guide").** The resume-time journey
  auto-open and the remembered-tab restore (`cohTab`) are RETIRED — launch is
  the first tab, every time. The road still greets a new 1-50 character ONCE,
  at creation (the wizard-exit call sites keep `maybeAutoOpenJourney`), and a
  character loaded while the Leveling tab is open still rebuilds the road for
  THAT character (the 2026-08-03 empty-placeholder fix). Proven live with a
  planted stale `cohTab=leveling` and a resumed sub-50 character: both land
  on Powers & Slots.
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
  while Fiery Embrace is up. Our Mids-derived base correctly counts
  Smashing+Energy alone; counting the Fire template would inflate those 86
  attacks by ~45% (RS 74.1 → 107.4). A future reconciliation pass that trusts
  `requires_expression == ""` will do exactly that.
  ⚠⚠ **CORRECTED 2026-08-08 — "the crawler is not capturing that gate" WAS
  WRONG, and the correction is the useful half. The gate is `tags`, an effect-
  group field nothing in this project had read.** Censused across the whole
  export: **349 groups on 342 powers carry `tags: ["FieryEmbrace"]`**, and the
  same field carries **Containment 119 · Domination 90 · Overpower 86 · the
  Scrapper crit trio · Defiance 33 · PowerBoostA/B · SSDamage · Contaminated**
  and ~150 more. So the whole mode/meter class — the one queued as Fury / Power
  Boost / the self +damage buff — is **mechanically identifiable in the data**,
  which is what any of that work needed first. The tag names the mode; it does
  NOT give the uptime, so it enables the work rather than doing it.
  `add_wind_control.effects_from` skips tagged groups and COUNTS them, and
  ~~`tools/test_origin_pools.py` pins the 349~~ (battery deleted with the
  2026-08-10 retraction; the tags census itself stands).
- **⚠⚠ A `requires_expression` MIXES TARGETING WITH CONDITIONS, AND ONLY ONE OF
  THEM MAKES A GROUP CONDITIONAL (2026-08-08).** "Who may this land on"
  (`enttype target> critter eq`, `entref target.owner> entref source> eq !`,
  `target.isFriend? !`) is always true for the enemy in front of you; "when does
  it apply" (an archetype, `kMeter`, `Source.Mode?`, a `rand` roll, token
  ownership) is the real gate. **Strike out the targeting clauses and 5,123 of
  the 7,323 expression-carrying groups reduce to nothing**; every residue is a
  genuine condition. ⚠ Testing for `critter`/`player` alone is NOT enough — the
  client writes an attack's damage **once per archetype and again per game
  state**, and those variants name `critter`/`player` too: Wrist Blaster has
  **23 damage groups for one attack**, and a naive side test took all 23.
  ⚠ **And `chance: 0.0` means UNSET, not "never"** — the crawler writes 0.0 for
  an absent field. Poisoned Dagger's -DMG group reads 0.0 while the game's own
  short help states the -DMG; corpus-wide only 64 untagged chance-0 groups
  exist and every one carries a real, help-stated effect.
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
  ▶ **2026-08-08: the ROSTER for this work now exists and is mechanical.** The
  client's `tags` field names every one of these modes on the effect groups
  they gate (FieryEmbrace 349 · Containment 119 · Domination 90 · Overpower 86 ·
  Defiance 33 · PowerBoostA/B · the Scrapper crits · ~150 more) — see the
  corrected Fiery Embrace entry above. Whoever starts the mode/meter work no
  longer has to find the affected powers; the remaining unknown is UPTIME, and
  that is the part that was always Joel's ruling.
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
  ⚠⚠ **`__tmScene` DEFAULTS TO "menus" FOR THE WHOLE `start` CHAPTER, and a step
  that omits `scene:` never flips it back** (`s.scene || (s.chapter === "start"
  ? "menus" : "build")`). A start-chapter step whose subject lives on a TAB must
  say `scene: "build"` or it highlights a **collapsed, zero-size stub** while the
  mock still shows the Character menu — which is exactly what shipped for one
  round here. **No audit catches it**: the target id is real, the mock stand-in
  exists, the anchor resolves — they simply are not on screen together.
  ⚠ **Generalize: a tour step is only verified by RUNNING it and looking.**
  Joel's "run the tour and check the new step reads right" found in one pass what
  eight green checks could not.
  ✅ **FULL 64-STEP WALK DONE (2026-08-07, on his "check nothing else is
  broken") — and it found a SECOND one, in shipped code: "Four tabs, one
  character" (`#tabbar`) had the identical defect and predated the band
  entirely.** Both fixed with `scene: "build"`; both confirmed by eye and by
  measurement (0×0 → 1353×39 and 1353×129). Every one of the 64 now measures a
  real, visible target and no card lands outside the viewport.
  ⚠ **THE WALK METHOD, because it is not obvious:** `driver-active-element`
  **accumulates** on every element the tour has visited, so
  `querySelector('.driver-active-element')` returns the FIRST in the DOM, not the
  current one — my first pass silently measured step 1's element 22 times.
  **Clear the class off everything, click Next, wait ~200ms, read the single
  survivor.** Walk ONE CHAPTER at a time (`startTour('stats')`): a 64-step loop
  times out and the pane throttles hard once hidden.
  ✅ **NOW A STANDING CHECK — `audit_tour` check (c)**, which compares each
  step's computed scene/tab against where its stand-in actually lives in
  `TOUR_MOCK_HTML`. 64 checked; sabotage-proven against both real defects.
  ⚠⚠ **ANCESTRY IS PARSED, NOT SCANNED, and this cost two reverts.** My first
  two attempts walked backwards for the nearest preceding `data-tm-tab=` and
  called that the home. That is not ancestry — it ignores closing tags — and it
  confidently reported `#power-info` as living on the `logging` tab while
  MISSING the real defect. I reverted rather than ship a check I did not trust;
  the shipped version uses `html.parser` with a real element stack. **A nesting
  question needs a parser, and a check that cries wolf is worse than none.**
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
- **🗡 v44 CRITICAL HITS — THE CHANCE THE CLIENT STATES, AT THE FLOOR IT
  STATES IT (2026-08-09, `bad38824`, `tools/patch_power_crits.py`).** The
  Scrapper's and Stalker's defining mechanic, never scored. **v36 deferred the
  whole class for want of grounding** ("12/194 explicit, gates only — third-party
  chance tables are forbidden basis"); the `tags` finding removed that obstacle.
  Hack: base chance 1.0 scale 1.64, `CritSmall` 0.05 scale 1.64, `CritLarge`
  0.10 scale 1.64 — **a crit adds 100% of the attack's own damage** and the crit
  row IS the base row again. **253 rows on 247 powers.**
  ⚠ **THE FLOOR IS TAKEN.** Crediting the 0.10 needs the spawn's rank mix and no
  scenario writes one down — `rank_acc` and `ctrl_land` were each derived from a
  mix but neither records it, and inverting `rank_acc` needs an assumption about
  the tail. The minimum needs nothing and is exact on a minion-heavy spawn.
  ⚠⚠ **THREE LEAKS, EACH CAUGHT BY MEASURING RATHER THAN READING** — and every
  wrong version looked reasonable: (1) **a chance of 1.0 is not a die roll** —
  StealthCrit is the guaranteed crit while HIDDEN, and taking it doubled Kyokan
  and Mask Presence unconditionally; (2) **pet/redirect records carry the tags**
  but a pet does not crit as its owner; (3) ⚠⚠ **our `Epic.*` records are SHARED
  across archetypes**, so a first pass handed criticals to Defenders, Tankers,
  Peacebringers and Warshades through their epic picks — **exposure read 14 of
  24** until it was restricted to the two archetypes the game gives a crit
  inherent, then **2**. Generalize: an `Epic.*` record is not archetype-scoped,
  so never write an archetype-specific mechanic onto one.
  ⚠ **THE INVARIANCE GUARD EARNED ITS KEEP**: it refused to write while the
  BASELINE still held the previous pass's rows, leaving the over-broad version
  on disk until the baseline was stripped too — the same idempotency trap as the
  pools generator. Its failing is why the wrong data did not ship.
  ⚠ **A re-cert is owed for 2 of 24** (Scrapper Broad_Sword/SR, Stalker
  Rad_Melee/Dark_Armor). **NOT STARTED.** Battery `tools/test_crits.py` (12
  checks, 3 sabotages) reads the scale and chance back out of the client.
  ⚠ **VERSION PINS: `>=`, NOT `==`.** test_absorb and test_domination each
  pinned MODEL_VERSION exactly and went red on the NEXT bump for a reason
  unrelated to their subject. Both now pin "at or past the version my subject
  landed in", which is what an exact pin was reaching for.
- **👑 v43 DOMINATION — THE HALF THE GAME SETTLES, SHIPPED; THE HALF IT DOES
  NOT, STATED (2026-08-09, `4fc76239`).** The Dominator inherent. **Size, stated
  twice:** its own help says control powers *"will typically last 50 percent
  longer"*, and **41 of 41** encoded pairs in the client carry exactly **1.5×**
  the base duration scale. **Uptime, from the inherent's own numbers:** a 90s
  Set_Mode on a 200s recharge, so the floor is 45% and global recharge shortens
  the 200 like any click — it reaches 1.0 at **+122% recharge, which is the
  perma-dom threshold players build to**, reproduced rather than assumed, and
  capped there.
  ⚠⚠ **APPLIED UNIVERSALLY, NOT PER ENCODED POWER.** The client writes the
  variant rows on only **12 of the 26** Dominator sets — Plant's Strangler has
  one and Mind's **Dominate, the identical tier-1 hold (scale 12.0, mag 3.0),
  does not**. That is an ENCODING asymmetry, not a game one; the help says "your
  control powers" unqualified. Pricing only the encoded 12 would bias the solver
  toward those sets — the "patch just the reported case" the universal-rules
  doctrine forbids. It rides the **existing `mez_dur` channel** the v30 set
  bonuses use, so there is one mechanism, not two.
  ⚠ **THE MAGNITUDE HALF IS DELIBERATELY NOT CREDITED.** The help also promises
  you "more easily Dominate stronger opponents" and the variant rows carry their
  own magnitude — but whether it ADDS to the base (both say `stack: Stack`,
  which would double a mag-3 hold to 6) or REPLACES it is genuinely ambiguous in
  the client, and **3 of the 41 pairs fit neither reading**. Doubling control
  magnitude across an archetype is too big to infer. Understated and said so.
  📏 Measured on the one certified Dominator: control output **999.5 → 1211.3**
  at no global recharge, **→ 1423.1 at +100%**.
  ⚠ **A RE-CERT IS OWED FOR 1 OF 24 CONTEXTS** (Mind_Control|Fiery_Assault|
  itrial, which holds three control powers). **NOT STARTED — Joel's call.**
  Battery `tools/test_domination.py` (16 checks, 4 sabotages) reads the 90/200
  and the 1.5× back out of the client rather than trusting source constants.
  ⚠ `test_absorb` pinned `MODEL_VERSION == 42` exactly and went red on this bump
  for a reason unrelated to absorb; it is `>= 42` now, which is what it meant.
- **🎛 THE MODE/METER CAPABILITY: THE CLASSIFICATION IS BUILT, AND MOST OF
  THE CLASS TURNED OUT NOT TO NEED A RULING (2026-08-08, `tools/mode_tags.py`
  + `reality_check_mode_tags.py` + `tools/test_mode_tags.py`).** 47 tags reach
  a scored group of a power we carry, and every one is adjudicated with its
  evidence; the check hard-fails BOTH ways (an unadjudicated tag, or a stale
  entry for a tag the client no longer carries). Five classes:
  **LABEL 22** (not a gate at all — the client naming the power's own effect),
  **PROB 14** (a chance the client STATES — weighted, never skipped),
  **MODE 4** (duty cycle derivable from the game's own duration and recharge),
  **SCENARIO 6** (real, blocked on one input — Joel's, the `mez_in` class),
  **DERIVED 1** (Defiance — v36 derives it; taking it would double-count).
  ⚠⚠ **A TAG IS NOT AUTOMATICALLY A GATE, AND ASSUMING SO WAS A LIVE BUG I
  SHIPPED THE SAME DAY.** The first fix skipped every tagged group; that is
  right for FieryEmbrace and WRONG for `FireBlastBonusDoT`, which is simply the
  client's name for Blaze's own Fire DoT — unconditional, in the power's help,
  on 29 Fire attacks. **Three mechanical tests were tried** (does the tag name a
  Set_Mode / a power / does the group carry a requires residue) **and each got
  some of the 48 wrong in BOTH directions** — PowerBoostA names neither a mode
  called PowerBoostA nor a power yet is a gate; `Damage` and `Taunt` name real
  powers yet are labels. Hence a hand-adjudicated table, the project's standing
  pattern. ⚠ Adjudicating Overpower as PROB (0.2/0.5, stated) rather than a
  gate put five weighted Controller mez rows back into Wind Control.
  ⚠ **Defiance's templates are NOT all scale 0.0** — 25 distinct scales up to
  0.176 — so the DERIVED skip is load-bearing, not a formality. The older note
  saying they are zero is corrected.
  ▶ **WHAT IS ACTUALLY LEFT, and each names its missing input:**
  (1) **Containment / the stack meters** (BuildStatic, BuildFrenzy, Contaminated,
  Disintegrate, EnergyRelease, ComboBuild, Perfection×3, Bio adaptation — 144
  groups): one scenario constant each, or one ruling for the class.
  (2) **Domination** (87 groups): the duty cycle IS derivable (Set_Mode 90s on a
  200s recharge, both client-stated) but it multiplies CONTROL magnitude, and
  `role_output` has no mode path — an engine change that moves Dominator
  champions, so it is its own measured pass.
  (3) **The crits** (453 PROB groups): the chance is stated PER TARGET RANK
  (`arch target> Class_Minion_Grunt eq` → 0.05, boss → 0.1), so what is missing
  is the encounter's rank mix, not the chance. Today they are dropped by the
  targeting/condition rule, which is honest but understates every Scrapper.
  (4) ⚠ **FieryEmbrace's 305 groups stay excluded, and there is a REAL question
  behind it:** the client's Fiery Embrace record grants `Fire_Dmg` at aspect
  Strength — a **Fire-typed** buff — and our engine folds every `DamageBuff`
  into one type-blind global `damage_buff`. So Fiery Embrace currently raises
  ALL damage at an 11.1% duty cycle, while the game adds Fire components to
  attacks and boosts those. Whether that over- or under-states it is a
  measurement, not a reading. **Do not 'fix' it by adding the Fire templates**
  until the type question is settled — that is the 2026-08-06 inflation trap.
- **🧰 GADGETRY AND UTILITY BELT SHIPPED (2026-08-08, `22b7be2f`,
  `tools/add_origin_pools.py`) — and a POOL needs three things an archetype set
  does not.** (1) **Prerequisites, which the game states outright**: Blaster
  Barrage's requires is "any TWO of the three", read from the expression into
  `prereq_count` and enforced by `_picks_legal` — never left to the tier proxy.
  (2) **The never-pickable free rider**: Turbo Boost and Athletics carry
  `available_level 4294967295`, so they are deliberately absent — the
  `Pool.Flight.Fly_Boost` ruling applied again. (3) **An archetype gate the tool
  cannot express**: the game bars Jetpack from Peacebringers and Warshades, so
  it is RECORDED on the record (`archetype_excluded`) and REPORTED, not dropped
  and not faked. Both pools were ALREADY in `_EXCLUSIVE_POOLS`, so the
  one-origin-pool rule and the four-pool cap covered them the moment they
  existed — checked, not assumed. ⚠ The origin-pool rule itself is **not in any
  `requires` expression** (checked 2026-08-08; Mystic Flight and Nano Net both
  carry none), so it is server-side and unverifiable from the bins, the same
  class as zone level ranges. ⚠ Battery `tools/test_origin_pools.py` was
  DELETED with the 2026-08-10 retraction (the pools are not live); this entry
  stays as the record of how a pool differs from an archetype set.
- **⚠⚠ AUTOPICK WAS PROPOSING BUILDS THE GAME REFUSES — 61 of 2,721, AND THE
  CAUSE WAS A HAND-WRITTEN LIST (2026-08-08).** `_auto_pick_powers`' `place()`
  funnel filtered mutually exclusive twins from `_VEAT_DUPLICATE_PAIRS` — **two
  pairs someone typed out** — while our records mark **thirteen**, so Broad
  Sword proposals held Slice and Boomerang Slice together on 43 combos. The
  validator and `_picks_legal` had already been generalised to read `excludes`;
  autopick had not. The map is built from the data now (the hardcoded pairs are
  a proven subset, so the list is gone). ⚠ **A twin is a SET, not one power** —
  a power may exclude more than one.
  ⚠⚠ **And fixing it EXPOSED a latent second defect, which is the better
  lesson.** The creation-pick fallback seats "the better-scoring of the set's
  first two", and **first-two-by-tier is not available-at-level-1**: Fortunata
  Teamwork's second is **Mask Presence at level 20**, it out-scored Fate Sealed,
  and it was seated into the LEVEL-1 slot — an unbuildable Fortunata on every
  proposal. `_picks_legal` only saw it indirectly (a missing L1 seat), so
  `audit_autopick_legality` gained a check that states the actual rule: **a pick
  level must be at or above the power's own `level_available`**, which names the
  next set shaped that way instead of leaving a symptom. Measured three ways:
  HEAD 61 illegal · twin fix alone 1 (the exposed Fortunata) · both fixes
  **2,721 of 2,721 legal**. All 24 certified contexts and builds stay legal.
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
- **⚠⚠ `JSON.stringify` IS NOT ATTRIBUTE-SAFE, AND AN APOSTROPHE BROKE THE
  PICKER FOR A YEAR (field report BasiliskXVIII, 2026-08-07, fixed `27630c71`,
  shipped 0.12.35).** The enhancement picker wrote
  `onclick='pickPiece("uid", "Gaussian's Synchronized Fire-Control", 3)'`.
  JSON.stringify escapes the double quote and the newline but **not the
  apostrophe**, so the `'` CLOSED the single-quoted attribute and the browser
  kept a truncated handler that cannot parse. **40 of our set and piece names
  carry an apostrophe** — Basilisk's Gaze, Achilles' Heel, Cupid's Crush, every
  archetype set — so **none of them could be slotted by hand**. `git log -S`
  puts the construction in the FIRST COMMIT: every release shipped it. It
  survived because the SOLVER reaches those sets by another path, so only
  someone slotting manually ever hit it. **Attribute payloads go through
  escHtml, which neutralises BOTH quote characters.** Battery
  `tools/test_picker_attrs.js` (10) builds the real attribute with the real
  escHtml, reads it back the way an HTML parser does, and requires it to still
  parse as JS. ⚠ Its source rule is deliberately narrow — JSON.stringify inside
  an inline handler — because a wider regex flagged 19 sites that are safe by
  inspection, and **a check that cries wolf is worse than none**.
- **✅ CLOSED — THE SELF +DAMAGE BUFF CLASS IS LANDED AND WORKING, AND THIS
  ENTRY WAS STALE FOR A DAY (verified by measurement 2026-08-08).**
  **275 powers carry a self `DamageBuff` row** with `mode: true` and the
  game's own duration and recharge — Build Up scale 8.0 for 10s on 90s,
  Aim 5.0, Rage 8.0 for 120s on 240s, Soul Drain 0.8, Follow Up 3.0, Power
  Build Up 8.0, Fiery Embrace 10.0 (Fire-typed). **Measured through the real
  /build/calculate route: adding Build Up moves `damage_buff` 0 → 0.1111 and
  the attack's ST DPS 14.4 → 16.0.** v39's `mode`/`host_recharge` duty cycle
  is what prices it, exactly as this entry said it should be.
  ⚠⚠ **THE "ST DPS MOVES BY 0.0" MEASUREMENT WAS A BAD PROBE, NOT A BUG** —
  it added `Scrapper_Melee.Martial_Arts.Build_Up`, **a full_name that does
  not exist**, so no power was added and of course nothing moved. I made the
  identical mistake again today before catching it. **A probe that adds a
  power must assert the record RESOLVED** — `POWER_BY_FULL.get(fn)` — before
  believing a zero. Pinned by `tools/test_mode_tags.py`.
  ⚠ No re-cert is owed and none ever was: the data has carried these rows
  since v39, so certified scores already include them.
  Superseded text kept below for the reasoning it contains.
- **🛡 DEFENCE DEBUFF RESISTANCE — 178 POWERS, AND THE SCORER ASSUMED NOBODY HAS
  ANY (v41, 2026-08-08, `39cd0872` + `7e9c1fdf`).** Every defence armour set
  grants it and the game says so in its own words: Agile prints *"Auto: Self
  +DEF(Ranged), Res(DeBuff DEF)"*, Tough Hide *"+RES (Debuff DEF)"*. We carried
  the +DEF half and none of the other. `first_principles` has applied incoming
  −def pressure since v10 under the comment *"a squishy has ZERO defense-debuff
  resistance"* — **true of every build it could see, because DDR is
  power-granted ONLY (the game ships no DDR set bonus)**, so Super Reflexes took
  a Blaster's haircut. ⚠ **This one needed no ruling from Joel, and that is what
  made it different from mez and slow: the incoming pressure term already
  existed** — only the resistance was missing. Measured: Agile 6.92%, five SR
  powers 48.44%, Tough Hide 25%, capped at the game's 95%. ⚠ **aspect is the
  whole filter again** — aspect=Strength `Base_Defense` templates are the Alpha
  boost DEFINITIONS. ⚠ **Clicks are duty-cycled**: Elude is 34.6% for 180s on a
  1000s recharge = 6.23% sustained, via v39's `mode`/`host_recharge`.
  ⚠⚠ **Reusing that flag exposed a latent bug worth remembering: the v39 mode
  dedup keyed on `(scale, duration, stack)` with NO effect name.** One family
  made it unambiguous; a second makes it a silent swallow. Fixed at the key.
  Exposure counted: 9 of 24 contexts; **union with v39 (13) and v40 (8) = 17**.
- **🗂 EVERY EFFECT FAMILY IS CLASSIFIED, AND A REAL GAP IS PINNED RATHER THAN
  DISPOSITIONED (`37cbade5`, 2026-08-08).** `reality_check_effect_coverage.py`
  hard-failed on 104 families; residue is now ZERO. Four outcomes, and the
  third is the point: **SOURCE_EXCLUSIONS** (counted and printed — the
  Alpha/Genesis/Hybrid boost tables are ENHANCEMENT definitions whose attribs
  are aspects, not effects a power applies; pet records carry the pet's own
  model), **DISPOSITIONS** (42, each citing its ruling), **OPEN_GAPS** (20 real
  defects, each with its power count **pinned so it fails in BOTH directions** —
  grown = a new defect wearing an old name, shrunk = an entry someone forgot to
  remove; the prereq-baseline contract), and residue = hard fail.
  **⚠ A real gap must never be dispositioned into silence, and must never
  hard-fail forever either — that is how a check gets switched off.**
  ⚠⚠ **RULE 5, the 121-phantom-debuffs lesson in a second coat: TRANSLATE THE
  VOCABULARY, not just the case.** Ours says `AoE` and `Negative` where the
  client says `Area` and `Negative_Energy`; Cloaking Device carries all eleven
  defence vectors and still reported two missing.
- **📭 THE EMPTY-RECORD CLASS — 876 RECORDS, AND ONLY TWO WERE A DATA GAP
  (classified 2026-08-08, `f7077f5a`; `reality_check_empty_records.py`).** Our
  records holding ZERO effect rows while the client populates them looked like
  the biggest hole in the tool. It is not: **632 are not player powers**
  (Alpha/Genesis boost DEFINITIONS 339, inherent machinery whose scored members
  v36 DERIVES 103, pet records 161, temp tokens 28, one redirect stub empty by
  design), **210 are player records whose client templates are pure plumbing**
  (Grant_Power, Set_Mode, Create_Entity, movement), **32 are real and pinned**,
  and **2 were a plain data gap** — Ninjitsu's Bo Ryaku (now 7.5% resistance to
  all eight types) and Stalker Shield Defense's Active Defense (11.25% melee
  defence + S/L resistance; the Brute sibling's 12.75 is the AT column, not a
  discrepancy). Champion exposure ZERO, so no score moved.
  ⚠⚠ **THE STUB WAS WRONG IN TWO FIELDS, NOT ONE.** Both also carried
  `power_type: 0` (a click) where the game says "Toggle:" and "Auto:", and the
  engine only counts self effects when `power_type in ACTIVE_POWER_TYPES` — so a
  CORRECT effect back-fill measured **0.0 through the real route**. The
  correction demands TWO signals (the game's own prefix AND a populated sibling
  on another archetype) and refuses to write if they disagree.
  ⚠ **THE FIRST YIELDING GROUP WINS WHOLE, not row by row** — the client's
  second effect group is the PvP variant and is NOT merely a copy: Shield
  Defense's adds a Psionic defence vector our populated siblings all keep at
  pv_mode 2. Per-(effect, damage type) merging let it into PvE.
  ⚠⚠ **GAMMA BOOST IS NOT A BACK-FILL, and this is "check the game, not your
  parse" earning its keep.** The client hands over flat `Regeneration 1.0` and
  `Recovery 1.0`; the game's help says *"the LOWER your current health, the
  greater the regeneration bonus… the HIGHER your current health, the greater
  the recovery bonus"*. Two ends of ONE curve — writing them flat credits +100%
  of each at once. Same class as **Agile's scaling damage resistance, which the
  export carries at scale 0.0** for exactly this reason. Health-scaling effects
  are their own unbuilt model.
  ⚠ Still named and unbuilt: **Absorb is not modelled ANYWHERE** (no engine
  branch, only an enhancement aspect of that name — Master Brawler, Insulating
  Circuit, Spirit Ward, Particle Shielding), and **ally mez protection has no
  consumer**, so Clear Mind / Clarity ×8 would land inert.
- **🛡 ABSORB IS MODELLED (v42, 2026-08-08, `fc8e6ead` + `3b0ac15d`) — AND THE
  TWO NUMBERS ARE DIFFERENT QUESTIONS.** 38 player powers grant an absorb shield
  and our data carried none of it; the engine had no branch either (`Absorb`
  existed only as an enhancement-aspect name and a display unit), so Radiation
  Armor's signature survival click was scored on its regeneration half alone.
  **`totals["absorb"]` is the shield's SIZE** (Scrapper Particle Shielding
  **401.6 HP**, ~30% of base HP) and **`totals["absorb_hps"]` is what it is
  WORTH** — the pool ÷ how often the power re-arms, because a shield soaks its
  pool once per cast. ⚠ **NEVER ADD THEM**: crediting the pool itself scores a
  120-second click as permanently up. Consumed as damage-not-taken per second
  beside regen and self-heal. ⚠ **ONLY HEAL-TABLE ROWS ARE TAKEN** — 19 records
  grant absorb as a literal `1.0` on a `*_Ones` table (Bio's Ablative Carapace,
  Nature's Wild Bastion) and one hit point is not a shield, so those are pinned,
  not guessed. ⚠⚠ **THE ENHANCE ASPECT IS `Absorb`, NOT `Heal`** — the client's
  `boosts_allowed` says Heal, so "Heal" looks right and enhances NOTHING;
  `Crafted_Heal` boosts Heal, HitPoints, Regeneration **and Absorb** (measured:
  401.6 → 401.6 wrong, → 571.9 right). Three understatements stated: absorb does
  not overheal, its burst value is invisible to time-to-live arithmetic, and the
  v29 heal-strength bonuses are not applied. Champion exposure ZERO.
- **⚠⚠ `Recharge` IS A DEAD WORD IN THIS ENGINE — THE ASPECT IS `RechargeTime`
  (found 2026-08-08, fixed in v42).** No piece in the game carries the aspect
  `Recharge`; **633 carry `RechargeTime`**; and THREE sites asked for the dead
  name, so recharge slotting silently reached **none** of: the v39 mode duty
  cycle, a click buff's uptime, or **TIMED PET uptime**. Always failing
  downward. Same family as the v28 accuracy allowlist — a name that can never
  match. Measured with three recharge IOs: **Rage's damage buff 0.40 → 0.796,
  Category Five pet DPS +96.8%, Auto Turret +87.5%, Lightning Storm +53.8%**
  (Storm Cell and Dark Servant unchanged — already capped at 1.0). The three
  sites share `engine._RECH_ASPECT` now, and `test_absorb` checks that name
  against the **SERVED** piece vocabulary so a rename fails loudly.
  ⚠ **It was found only because a NEW feature reused the old spelling and its
  battery measured no movement** — the general lesson being that a fresh
  measurement across an old code path is how dead lookups surface.
  ⚠ It widened the re-cert union from 17 to **20 of 24**.
- **📐 THE MAGNITUDE IS NOT ALWAYS IN THE SCALE — EVERY CLIENT TEMPLATE CARRIES
  A `magnitude_expression` (found 2026-08-08, `a2451a1b`).** For 226 player
  powers the real number lives in an RPN expression, not the table scale. Bio
  Armor's Ablative Carapace is `Max.kHitPoints source> 0.3 * @Strength *` =
  **30% of your max HP**, which is exactly why its scale is a bare `1.0` and why
  it had been pinned as *"units unknown — a literal 1.0 cannot be one hit
  point"*. It was never unknown; the field had not been read.
  **The class splits in two and the split is the whole finding:**
  **MAX-HP-PROPORTIONAL (10 powers) needs NO scenario input** and is modelled —
  Ablative Carapace 30% ×5, Parasitic Aura 10% ×4, Parasitic Leech 14.3%
  (Scrapper 401.7 HP of 1339, Tanker 562.2 of 1874). **HEALTH-DEPENDENT (13
  powers) is decoded and PINNED** — SR's scaling resistance is 20% at zero HP
  falling to nothing at 60%, and Gamma Boost's regen and recovery run in
  OPPOSITE directions off the same bar. The only missing input is an operating
  health, a scenario constant of the kb_in/mez_in class. ⚠ `@StdResult` resolves
  to the template's own scale, safe ONLY because those rows sit on Melee_Ones
  (1.0 for all 15 playable columns — checked, not assumed). ⚠ Magnitudes compute
  against **BASE hp**, never the boosted pool: `totals["max_hp"]` is still
  accumulating in that loop and reading it would make the answer depend on power
  order — the v39 recharge rule again.
- **⚠⚠ A ZERO-SCALE TEMPLATE *WITH* AN EXPRESSION IS NOT EMPTY — rule 4 was
  hiding a real family.** "A zero scale carries no magnitude" was written for
  Defiance's stubs; zero scale PLUS a `magnitude_expression` is exactly how
  Super Reflexes' scaling resistance is stored. The check requires both now, and
  the moment it did it surfaced **Defiance's own templates, which must stay OUT
  of the data because v36 DERIVES them** from cast time and area — a
  double-count caught within a minute of looking. Computed-magnitude classes are
  dispositioned by EXPRESSION now: Defiance, the token/meter systems, distance
  scaling, and the **Fighting-pool cross-boost** (Boxing/Kick/Cross Punch each
  stronger for owning the others — real, unmodelled, and named rather than
  invisible).
- **🌪 WIND CONTROL SHIPPED — a whole powerset added from the client (2026-08-08,
  `982a8572`).** 20 records across Controller and Dominator, offered in
  `powersets.json`, priced end to end with pets. Every mapping was MEASURED
  against powers we already hold (`docs/wind-control-spec.md`): level +1 (5,478
  of 5,589), Click/Toggle/Auto → 0/2/1, effect_area, `is_attack` = has damage,
  control rows on the 539-power convention, `kind` hard/soft by mez name
  (unanimous), categories by name + two aliases (1,128× and 452×), summon
  entities by underscore normalisation (570 exact + 7), and the spec's
  `permanent` ⟺ duration ≥ 99999 (483/53, perfect). ⚠⚠ **`targets_affected` IS
  THE SIDE, NOT `target_type`** — Thundergust and Wind Shear are `target_type:
  Self` (centred on you) and land entirely on FOES; reading target_type would
  have written a cone attack's damage as a self buff. ⚠ **Clear Skies carries
  nothing on purpose**: all its effects are gated on `kClearSkies Source.Mode?`,
  the mode class. ⚠ **Joel's ruling: Controller and Dominator SHARE the Vortex
  entity.** ⚠ The generator REFUSES rather than guesses — it fired three times
  during the build and each refusal was a real misunderstanding.
- **⚠⚠ `open(path, "wb").write(expr)` TRUNCATES BEFORE IT EVALUATES `expr` — it
  emptied powers.json to ZERO BYTES (2026-08-08).** A `NameError` inside the
  expression was enough: 17 MB gone in one statement. Recovered whole from git
  plus the tools, because every change since the last commit is generated — but
  **build all bytes first, then open**. ⚠ Related, same day: **match each file's
  own serialisation** — powers.json and summons.json are compact single-line,
  **powersets.json is `indent=1` with CRLF**, and writing it compact turned a
  two-entry addition into a 3,102-line diff (content identical, review
  impossible).
- **🎯 CONTROL DRIFT: 29 POWERS DISAGREED WITH THE CLIENT, 25 SYNCED GAME-FIRST
  (2026-08-08, `70f97249`).** Our control encoding matches the client on 539
  powers. Of the 29 that did not: **ten epic holds read a 12.0 duration scale
  where the game says 10.0** (Block of Ice, Fossilize, Char, Dominate, Shocking
  Bolt, Melt Armor), the four **Electric Shackles** 8.0 → 10.0, **Hymn of
  Dissonance** magnitude 1 → 3, and **Telekinesis was recorded as a HOLD when
  the game's own short help says "Foe Immobilize, Repel"**. ⚠ **Four were left
  alone**: Synaptic Overload, Cryo Freeze Ray, EM Pulse and Seismic Smash carry
  multi-row ENCODINGS, not wrong values — collapsing one is a different question
  from correcting a number. ✓ Exposure zero of 24.
  ⚠ **The 269 unresolved `summons[]` references are NOT a pricing gap** —
  pricing reads the SPEC, which carries uid/count/class inline; the entity map
  is metadata. The one case drivable end to end (Shadow Field) shows no pet
  damage because its pseudo-pet genuinely has none.
- **🚫 MUTUALLY EXCLUSIVE POWERS — THE TOOL ALLOWED WHAT THE GAME REFUSES
  (found and fixed 2026-08-08, `35c97c6f`).** The client marks them with a
  `requires` of `<other> !` on BOTH records, and **nine pairs already sat in our
  data on both sides** with nothing stopping a user *or a certification wave*
  from taking both: **Dark Regeneration ⟷ Obscure Sustenance on FIVE
  archetypes**, Master Brawler ⟷ Practiced Brawler, the Widow's Build Up ⟷
  Follow Up, and the two VEAT grenades. `engine.validate_build` raised nothing,
  and **`_picks_legal` knew about TWO of the nine** because they had been typed
  in by hand as `_VEAT_DUPLICATE_PAIRS`. That is the class that shipped eight
  illegal champions in 0.12.30; legality outranks score. ✓ Exposure counted
  BEFORE the change: **zero of 24** hold both sides. Now 13 client-derived
  pairs, **mirrored-or-not-at-all** (a one-sided exclusion is a parse artefact),
  the validator names the pair, and the gate reads the data — the hand-list is a
  proven subset. ⚠ Battery `tools/test_power_exclusions.py` was deleted with
  the 2026-08-10 retraction; the 13 mirrored pairs and the gate rule live on
  (re-verified when Boomerang Slice was restored the same day).
  ⚠ **A sabotage that mattered:** "adding the partner makes it illegal" PASSED
  with the rule deleted, because a 25th pick breaks the ladder cap on its own.
  **The check SWAPS a pick now** — when a negative test can pass for a second
  reason, it is not testing what it names.
- **🗡 BOOMERANG SLICE — the one whole POWER this audit added, and the pattern
  for the rest (2026-08-08).** A real level-1 Broad Sword attack on four
  archetypes. **Not an additive patch**: a whole record, so every field came
  from the **client** (what the power is) or its sibling **Slice** (the
  app-schema fields), the latter justified because the client says the two
  accept an IDENTICAL set of categories and boosts on all four archetypes.
  Live: 40.7 damage, 1.83s cast, cone, level 2 beside Slice, refusing to
  coexist with it. ⚠ It could not be added until the exclusion rule above
  existed — the tool would otherwise have offered a build the game refuses.
  ⚠ **The 15-second Rending Slice bonus is NOT priced** (gated on a `Set_Mode`,
  the meter class) — understated rather than guessed. ⚠ No certified score
  moves, but the one Broad Sword context can now **re-pick into it**: search
  space widening, not a number changing.
- **⚠⚠ `child_effects` IS A LEVEL NOBODY HAD READ, AND THAT IS TWICE IN ONE DAY.**
  Boomerang Slice's two damage groups read as **EMPTY** at the top level; the
  damage hangs off `child_effects`, a group field no probe in this project had
  ever descended into. It nearly ended the work as "the client has no damage for
  it". The same shape as `magnitude_expression` hours earlier. **Generalize:
  treat an empty-looking client group as UNREAD, not empty — enumerate the
  field names before concluding the data is absent.**
- **⚠ THE CLIENT'S `available_level` IS 0-BASED, OURS IS 1-BASED** — 5,478 of
  5,589 matched powers agree on the +1. The Mids `IoLevel` trap in a new coat;
  any record synthesised from the client must add one.
- **⚠⚠ "459 MISSING POWERS" WAS WRONG — IT IS 32, AND THE REST WAS NAMING
  (retracted and corrected the same day, 2026-08-08, `0f585868`).** I reported
  459 absent client powers "including whole shipping powersets — Wind Control,
  **Shock Therapy**, **Blaster Time Manipulation**, Gadgetry". **Two of those
  four are in the tool already**: the client's Shock Therapy is our
  **Electrical Affinity** and its Time Manipulation is our **Temporal
  Manipulation**, both matching on a display-name roster of **1.0, every power**.
  **19 powersets are RENAMED, not missing** (also `Pool.Fitness` =
  `Inherent.Fitness`, and 13 Epic sets already on the proven bridge).
  ⚠⚠ **A RAW SET DIFFERENCE IS NOT A MEASUREMENT** — this is the three-namespaces
  rule, walked into while writing up a finding about a different gap, which is
  exactly when it bites.
  **What is genuinely absent: 32 powers** — Wind Control (Controller +
  Dominator, 20), `Pool.Gadgetry` (6), `Pool.Utility_Belt` (6), and **Boomerang
  Slice** (4 records, a real level-1 Broad Sword attack in a set we already
  have). ⚠ **The app does not OFFER any of the three sets** (powersets.json has
  none of them), so nothing is broken on screen — a player simply cannot plan
  them: an honest absence, not a defect. Everything else is accounted for and
  printed: 24 namespace differences (the client files White Dwarf Strike under
  the Kheldian set, we file it under `Inherent`), 6 never-pickable auto-issue
  powers, 15 `_Aux` combo/redirect variants, and pet records.
  **`tools/reality_check_missing_powers.py` is the standing instrument and it
  belongs in PATCH-WATCH**: after any client re-export it answers what is
  genuinely NEW versus what merely moved name.
- **🤝 THE ALLY SIDE WAS NEVER SWEPT, AND `AnyAffected` IS NOT `ALLY`
  (2026-08-08, `4e3f68f9`).** `reality_check_effect_coverage.py` tested
  `target == "Self"` and stopped, so every buff a power places on someone ELSE
  was invisible to the one instrument built to see everything — **151
  Friend-targeted player powers, 45 uncarried families**. ⚠⚠ **The template's
  `target` field is NOT the side**: `AnyAffected` means whoever the power
  affects — a friend on Clear Mind, the **FOES** on a Brute cone attack — and a
  first sweep keyed on it classified Repulsing Torrent's −damage template as a
  team buff. **The power's own `target_type` (Friend / Foe / Self / Location)
  is the authority**, and pins are keyed by SIDE so a self-side and ally-side
  gap of the same family can never be confused. ⚠ **A general disposition worth
  keeping: an `aspect=Strength` row placed on someone else amplifies THEIR OWN
  effects (Amp Up) — we model no ally's build, so there is nothing to
  multiply.** That rule retired nine would-be pins.
- **⚠⚠ `mez_in` IS NOW THE HIGHEST-LEVERAGE OPEN RULING IN THE PROJECT.** One
  number unblocks **289 powers that score nothing today**: self mez protection
  (229, built and proven but inert), **ally mez protection + resistance (29 —
  Clear Mind, Clarity, Thaw, Increase Density, O2 Boost, Shadow Fall, the
  biggest support gap in the tool)**, and the four debuff-resistance families
  (31: ToHit, endurance-drain, regeneration, recovery). ⚠ Ally SLOW resistance
  (8) is the one that is NOT blocked on an input — `slow_in` exists, but it only
  slows MY damage and the team is a flat `team_dps` the model never slows, so
  what is missing there is the CHANNEL.
- **⛔ DON'T BUILD A TERM FOR ONE POWER WHEN THE CHANNEL IS COMING ANYWAY
  (2026-08-08).** The ally half of `patch_power_absorb` was written, measured
  and REVERTED: Insulating Circuit is clean but Spirit Ward's two ungated groups
  disagree (0.2/20s vs 1.0/10s, an over-time toggle), leaving exactly ONE
  unambiguous power that no champion holds. The same ally channel is needed for
  the 29 mez powers, so it gets built once, properly, when `mez_in` lands.
- **⚠ A CORRECT DATA PATCH READ ZERO THREE TIMES IN ONE SESSION, never once
  because the data was wrong.** `power_type: 0` on a stub (the engine only
  counts self effects on an auto/toggle) · the same click gate dropping an
  absorb row · the dead `Recharge` word. **Generalize: when a back-fill you can
  see in the file measures 0.0 through the route, suspect the ADMISSION PATH
  before the data — and always read a known-good axis in the same probe.**
- **✅ THE TWO-WAY PIN PAID FOR ITSELF THE SAME DAY IT WAS BUILT.** Fixing those
  two records drove TEN of the coverage check's pinned damage-type gaps to zero,
  and the check **hard-failed on the stale entries** instead of passing quietly.
  A pin that only fails upward is half a pin.
- **⚠ FOUR MORE RESISTANCE FAMILIES ARE REAL AND BLOCKED EXACTLY AS `mez_in` IS
  (2026-08-08).** ToHit-debuff resistance (13 powers — Obscure Sustenance,
  Fallout Shelter, Combat Training: Offensive), endurance-drain resistance (8 —
  Inexhaustible, Murky Cloud), regeneration-debuff resistance (7), recovery-
  debuff resistance (3). Each is the same shape as DDR **except that no scenario
  carries that incoming pressure**, so there is nothing to resist and landing
  the data would be inert. One scenario number each, or one ruling for the
  class — Joel's, like `mez_in` and `kb_in`.
- **⚠ TARGET-CAP / RADIUS DRIFT IS MOSTLY NOT DRIFT — NEVER BLANKET-SYNC IT
  (2026-08-07, `tools/patch_drain_target_caps.py`).** Sweeping our powers
  against the client finds **205 max_targets and 265 radius disagreements over
  5,660 covered records**, and copying the client across them would DAMAGE the
  data: **pseudo-pet powers** (Burn, Blizzard, Meteor, Time Bomb, Rise of the
  Phoenix) read 0/0 on the client parent because the damage lives on the patch
  entity and our data deliberately folds the pet in — ours is right; and
  **single-target convention** differs (Tesla Cage 0 for us, 1 for the client).
  Only three were adjudicated and patched (Brute Dark Melee + Corr Soul Mastery
  Soul Drain 7→10 targets, Dom Soul Mastery radius 15→10), each carrying a
  SECOND signal — a sibling record of the same power where our value and the
  client already agree. Champion exposure zero of 24, counted. **Classifying the
  remaining ~460 is its own piece of work and was deliberately not attempted.**
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

