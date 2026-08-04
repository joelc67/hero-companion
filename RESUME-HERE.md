# Resume point — 2026-08-04 16:13 ET (handoff: catalogue work order + layout mode)

Tracked tree clean, master pushed, **HEAD = `e28d2227`**. Nothing running; no
scheduled tasks armed. The dev server on 5081 and the scratch browser windows I
used for measuring are closed.

**Installed app: `%LOCALAPPDATA%\Programs\HeroCompanion`, UNSIGNED dev build,
frozen stamp `297ddcf` + statics copied through HEAD.** It is RUNNING and left
with **layout mode ON** so Joel can start dragging where he left off. Release
still HELD at 0.12.30.

⚠ **Statics only load at LAUNCH.** WebView2 in this app has accelerator keys off,
so F5 and Ctrl+R do nothing. After any static edit: copy into
`_internal\static` and relaunch. server.py changes need a full rebuild.

## What landed today, after the earlier handoff

**1. The catalogue work order (ideas.md bottom entry) — steps 1-3 done,
`45355166`.** Multicol REVERTED (it flowed column-major and stacked Primary under
Secondary; the battery now pins grid-in and multicol-out). Card content is
width-agnostic (`.cmd-list` auto-fit grid, `.sb-cols` prose columns): measured
203px wide -> 486px tall, 399px -> 254px, 924px -> 165px, against a tallest
powerset column of 290px. Step 2's `grid-row: 1 / -1` was implemented, measured
and replaced: a grid item with a definite row is placed BEFORE the auto-flow
items, so the cards took tracks 1-2 and shoved Primary to track 3. The cards are
now `.cat-side`, a stretched flex sibling of `.cat-cols` inside `.cat-body`.

**▶ THE GATE'S TEST 2 DOES NOT CLOSE AND IT IS ARITHMETIC — JOEL'S CALL PENDING.**
Wall bottom spread at 1920: cards stacked beside the wall 315px, side by side
498px, **full-width strip 101px** (the only one under his 120px bar, and the only
one that keeps the wall at ONE row of 7 tracks). Seven powerset boxes need ~1400px
of the 1480 available; each card needs ~400px to stay short. They cannot both fit
beside the wall at his window size. The work order's own clause says the strip is
his decision, so it is NOT shipped. One-line flip when he says so:
`.cat-side` -> `card-home` in app.js, plus move `#card-home` above
`#endgame-panel` so the strip sits under the catalogue, not under Accolades.

**2. 🧩 LAYOUT MODE — the design tool he asked for (`e8bf3159`, reworked
`e28d2227`).** View menu or Ctrl+Shift+L. Per-area toolbar: ⠿ pick · ⤵ place
before · ↑ ↓ nudge · ⇄ other column / full width · ✕ hide (reversible from the
panel). Native corner handle resizes. Panel drags by its header and collapses.
Draft (sizes, order, hidden, panel position) persists in localStorage and survives
recomputes. **📋 Copy sizes for Claude** puts the whole draft on the clipboard —
that is the handoff: he pastes it, I bake it into style.css.

⚠ HTML5 drag is BANNED here and the battery pins it out: a ::before badge cannot
be grabbed, and drag cannot scroll the page mid-gesture. Pick-then-place is two
clicks precisely so scrolling in between is just scrolling.

## ▶ Open / next

1. **Joel's word on the card strip** (item 1 above) — everything else on the
   catalogue is done and verified.
2. **His layout draft**: he drags, clicks 📋, pastes it here; I bake the numbers
   into style.css and delete the draft. Layout mode itself should probably be
   hidden from the View menu before a release — it is a design tool, not a
   feature. His call.
3. Set-bonuses-in-force + rule-of-five meter view (concept approved, not built).
4. "Gear this build" shopping list card (pitched, not ordered).
5. Origin plates unplaced; `extract_power_icons.py` i24 glob bug still open.
6. Release when he says: rebuild the frozen exe first (statics + server drift).
7. Standing queue unchanged: verdict-gate legality hole, Iron Man accolade
   in-game check, gaming box silent since 07-29, exploration-log parse.

## Session-local facts worth keeping for one more session

- `saves/poison-defender.json` in the repo is a COPY of his Joinny Healer save,
  put there so the dev copy on 5081 has a real 9-box build to measure. Gitignored.
  (⚠ its stored sets are Poison/Sonic; the app window shows Empathy/Dual Pistols.)
- The measuring loop that finally worked: dev server on 5081 + the Claude Browser
  pane for JS geometry (it lays out and runs JS **only while the pane is
  displayed**, and never screenshots), then the frozen app + computer-use for
  eyes. `WScript.Shell.AppActivate($pid)` is how to front the app window when
  `open_application` resolves to an Edge tab of the same name.
