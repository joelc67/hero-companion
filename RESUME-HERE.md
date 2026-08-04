# Resume point — 2026-08-04 end of day (handoff: the big UI/UX day)

Tracked tree clean, master pushed, **HEAD = `2e6e6f9c`**. Nothing running;
no scheduled tasks armed. Untracked root files are old wave artifacts,
deliberately uncommitted.

**Installed app: `%LOCALAPPDATA%\Programs\HeroCompanion`, UNSIGNED dev
build, frozen stamp `297ddcf` + statics copied through HEAD.** Statics are
current via copy; **server.py changes since `297ddcf` (only the saves .bak
+ preserve/_generated fix are IN the frozen build; anything server-side
after that needs a rebuild — currently nothing is).** Release still HELD at
0.12.30; publishing is Joel's call.

**Read `coh-builder/CLAUDE.md` first** — today added several standing
rulings. This file is the live handoff.

## What today was (all in CLAUDE.md / session-report.md, commits tell it)

- ui-ux-pro-max skills installed (.claude/skills/, 7 skills, no npm).
- Two design passes + a punch-list cycle, all screenshot-verified.
- **End Game tab retired** → everything on Powers & Slots.
- **Structural balance doctrine (FINAL, ⛔ no panel packers ever)**:
  two-column region ends with the wall; then .pw-cardband (Accolades /
  ⌨ commands click-to-copy / 🧬 inherent / 💠 set-bonus blurb) as one
  equal-height full-width row; then the three reference slabs; all folds
  default open.
- **Identity-change overhaul**: primary/secondary swap = themed confirm →
  full auto-rebuild (autopick + solve, one approval); archetype change
  detaches the save (the Pyrotechnic loss root cause); pool/epic prune
  with confirm; stale auto-names heal; server keeps .json.bak on save
  overwrite; heal_ghost_powers.py fixed Joinny Healer.
- **All native dialogs replaced** by themed askDialog/askPrompt (13
  confirms + 3 prompts); quit gained "Keep working", archetype gained
  "Keep this character".
- **No naked numbers**: every stat row clickable incl. pets ("Because you
  are a Mastermind" panels), extras (slow res / movement / end discount)
  wired to the attribution ledger; Stats breakdown has an inviting empty
  state.
- **Full test sweep**: 45 batteries + new tools/test_user_paths.py (61/61
  routes covered w/ hard-fail denominator); found+fixed the preserve
  oscillation (_generated read a phantom field — one line) and closed the
  31 slotting-category drifts game-first (fresh bin re-export verified;
  patch_slotting_categories.py; register re-pinned 57→52).
- Frozen exe rebuilt once (stamp 297ddcf) with the server fixes.

## ▶ Open / next

1. **Joel's next walk** — the structural band + all of today lands fresh;
   expect nits. Screenshots BEFORE reporting, always.
2. Set-bonuses-in-force + rule-of-five meter view — Joel wants it near
   the IO sets / on Stats (stats stay on Stats); concept approved, not
   built. The blurb card exists; the live meter doesn't.
3. "Gear this build" shopping list card (concept pitched, well received,
   not ordered).
4. Origin plates still unplaced; extract_power_icons i24 glob bug still open.
5. Release when Joel says: rebuild frozen exe first (statics + any
   server drift), data patch (31 categories) bundles automatically.
6. Standing queue unchanged: verdict-gate legality hole, Iron Man
   accolade in-game check, box silent since 07-29, reduced-motion done?,
   exploration-log parse.
