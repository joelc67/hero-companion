# Resume point — 2026-08-04 20:32 ET (stop for the night, continue tomorrow)

Tracked tree clean, master pushed, **HEAD = `c4d9274c`** (last real commit
`8996df3a`, the tour update). Nothing running; no scheduled tasks armed. The dev
server and my scratch browser windows are closed.

**Installed app: `%LOCALAPPDATA%\Programs\HeroCompanion`, UNSIGNED dev build,
frozen stamp `297ddcf` + statics copied through HEAD.** It is RUNNING with today's
statics, layout mode off, shipped layout. Release still HELD at 0.12.30.

⚠ **Statics load at LAUNCH only.** F5/Ctrl+R do nothing in this shell. After any
static edit: copy into `_internal\static`, then relaunch. server.py changes need a
full rebuild. `WScript.Shell.AppActivate($pid)` fronts the window when
`open_application` grabs an Edge tab of the same name instead.

## ▶ THE ONE THING WAITING ON JOEL

**The catalogue's last empty cell.** Powerset boxes tile 4 + 3 at his window, so row
2 has one empty ~205px cell after Ice Mastery. Three ways to close it, his pick:
1. leave it (one cell, ~205×190);
2. one row of seven narrower columns — zero void, pool names clip again;
3. let the epic box span the spare cell — clean at his width, breaks at others.

## What landed today, after the 16:13 handoff

- **His third markup (`c409a243`)**: ⌨ commands + 💠 set bonuses moved OUT of the
  catalogue into the full-width strip (their sidebar was taking exactly the width
  the pool boxes needed); pools + epic now tile **two rows, 4 across**; the 🧬
  inherent card no longer stretches (199px, was ~550px of empty panel). Order below
  the wall: powerset rows → card strip → full-width Accolades → the three slabs.
  `.cat-body`/`.cat-side` and the JS that re-parented those cards are deleted.
- **Slabs (`47f1855b`)**: all three default CLOSED (supersedes default-open, which
  existed only so the wall could be judged expanded), and all three share one
  disclosure language — the native arrow, same title font. An explicit open is
  remembered.
- **Layout mode is RESIZE + HIDE only (`c11c6c28`)**: moving areas is deleted and
  pinned out of both files after three failed shapes. He sizes areas, hits
  📋 Copy sizes for Claude, and **I bake the numbers into style.css** — that is the
  workflow now, and no layout draft has been sent yet.
- **Tour refreshed (`8996df3a`)**: 61 steps. Fixed prose the audit cannot see (it
  still said five tabs and headed a mock block "End Game"), told users the three
  slabs start folded, and added steps for the ⌨ commands card and the 🧬 inherent
  card with matching mock stand-ins.
- **karpathy-guidelines skill installed** at Joel's request:
  `.claude/skills/karpathy-guidelines/SKILL.md` (MIT, pinned to upstream
  `2c60614`), provenance in `.claude/skills/SOURCES.karpathy.md`, documented in
  `.claude/CLAUDE.md`. Its always-on CLAUDE.md variant was deliberately NOT
  installed — ponytail and coh-builder/CLAUDE.md already carry the same ground.

## ▶ Open / next

1. **His ruling on the empty cell** (above) — everything else on the catalogue is
   done and measured.
2. **His layout draft**, whenever he wants: drag corners, ✕ hide, 📋 Copy, paste to
   me, I bake it. Layout mode should probably be hidden from the View menu before a
   release — design tool, not a feature. His call.
3. Set-bonuses-in-force + rule-of-five meter view (approved concept, not built).
4. "Gear this build" shopping list card (pitched, not ordered).
5. Origin plates unplaced; `extract_power_icons.py` i24 glob bug still open.
6. Release when he says: rebuild the frozen exe first (statics + server drift).
7. Standing queue unchanged: verdict-gate legality hole, Iron Man accolade in-game
   check, gaming box silent since 07-29, exploration-log parse.

## Session-local facts worth one more session

- `saves/poison-defender.json` in the repo is a COPY of his Joinny Healer save, so
  the dev copy on 5081 has a real 9-box build to measure. Gitignored. (⚠ its stored
  sets are Poison/Sonic; the app window shows Empathy/Dual Pistols.)
- Measuring loop: dev server on 5081 + the Claude Browser pane for JS geometry (it
  lays out and runs JS **only while the pane is displayed**, and never screenshots),
  then the frozen app + computer-use for eyes.
- ⚠ **Measure the width the USER has.** I set a track minimum from a 1920-wide pane;
  his window is ~1250 and the rule did the opposite of what he asked.
- ⚠ **Test input with a real mouse, never `dispatchEvent`.** Escape never reaches
  the page in this shell, even from the capture phase.
