# Resume point — 2026-08-05 (new session starts here)

Tracked tree clean, master pushed, **HEAD = `03c09ea2`** (work commit
`d026c05f`). Nothing running; no scheduled tasks armed.

⚠ **Stage commits BY NAME here, never `git add -A`** — the tree carries hundreds
of untracked benchmark artifacts (swap sweeps, pyspy SVG, stray .bat launchers).
`-A` staged all of them on 2026-08-05; caught by the `--stat` size check.

**Installed app: `%LOCALAPPDATA%\Programs\HeroCompanion`, UNSIGNED dev build,
frozen stamp `297ddcf` + statics copied through HEAD.** Release still HELD at
0.12.30.

⚠ **Statics load at LAUNCH only** (F5/Ctrl+R do nothing in WebView2): copy into
`_internal\static`, then relaunch. server.py changes need a full rebuild.
`WScript.Shell.AppActivate($pid)` fronts the window when `open_application` grabs
an Edge tab of the same name.

## ✅ DONE: the forum report (BasiliskXVIII, topic 64761) — `d026c05f`

Both claims closed, plus the disclosure pages and the Lite framing. Detail in
session-report.md. What survives as live state:

- **⏰ RELEASE STEP for 0.12.31:** `docs/index.html` currently discloses **0.12.30's**
  behaviour ("keeps running in your notification area after you close the window",
  Joel's ruling: today's truth, flip on release). That paragraph is wrong the
  moment 0.12.31 publishes — replace it with the window truth (close = quit) as
  part of the release.
- **✅ SETTLED: what a PORTABLE copy gets = the refusal + the download page, and
  nothing more** (Joel, 2026-08-05: "I am following your lead").
  `server._install_kind()` tells them apart by Inno's `unins000.exe` beside the
  exe (unreadable dir reads *portable*, so the failure mode is a refusal);
  `/update/install` refuses upstream of the Popen with the unzip-over-the-folder
  remedy. No installer button beside a routine update prompt, no zip
  self-update. ⚠ **Server-side ⇒ needs a frozen rebuild; reaches users only in
  0.12.31.**
- **The forum reply's "the update check only runs when you click it" is still
  uncorrected in public.** Accurate replacement drafted in session-report.md.
- Full app's logging choice now lives on the Logging tab (`gamelogChoiceRow()`):
  a visible "Turn it off" (the "on" state used to be a one-way door) and the
  start-with-Windows checkbox with a live clause saying what each state means.
  Same `playlogConsent`/`setAutostart` as before — no second copy of the choice.
  ⚠ `setAutostart` must re-render the surface it was clicked from; an
  unconditional `showAbout()` opens the About modal on top of the Logging tab.

## ✅ DONE: one import door + the Mids round trip — `e56b8f4c`

- The menu's two import items were the same thing; one remains, and it opens a
  panel that TEACHES both routes instead of throwing an OS file dialog.
- The Mids round trip is now pinned at 9 checks and is sound: pieces, order,
  engine totals and set bonuses all survive, and it converges at hop 2.
- **Fixed: special origins (HO/Hydra/Titan/D-Sync) came back labelled with their
  internal uid.** Root was `PIECE_BY_UID` being built from `ENH_SETS` only; all
  62 now register there, which fixes the in-game .txt path at the same time.
- ⚠ `server.py` changed ⇒ the HO fix needs a **frozen rebuild** to reach the
  installed app. The static half (panel, menu, tour) is already copied in.

## What landed the session before (all pushed)

- **Tabs are manila folders** in a filing cabinet: filed tabs sit lower in a darker
  color-mix of the active accent, the pulled one stands proud, labels typed on.
- **The tab's line owns its content**: `var(--accent)`, along the BOTTOM of the
  strip, down the sides through the build tile, closing under the panel — nothing
  drawn above the tabs, no gap. All four alignments carry it.
- **Menus**: right-anchored so they cannot clip; an open menu draws a dimmed
  per-theme edge that meets its panel; nothing at all until one is opened.
- **No sideways scrolling**: incarnate selects were 137px boxes holding 275px of
  option text. The road and the tab strip stay the only horizontal surfaces.
- **Alignment**: all four listed in the View menu under a heading, floating picker
  deleted; the middles' bright masthead line darkened to their own `--border`.
- **Stats**: every row is name · one-line meaning · number (49 rows, none blank),
  one type scale (was 6 sizes, now 4), and the offense board matches.
- **Stats ⓘ** now opens where the user is (it was rendering onto a hidden tab),
  breakdown slots say they are live, and **Ctrl+Z asks and names the edit** it will
  take back, skipping no-op snapshots.
- Tour caught up to 61 steps; layout mode is resize + hide only.

## ▶ Open queue

1. The catalogue's last empty cell (leave / one row of seven / epic spans it).
2. His layout draft whenever he wants: drag corners, ✕ hide, 📋 Copy, paste to me.
3. Set-bonuses-in-force + rule-of-five meter; "Gear this build" card; origin
   plates; `extract_power_icons.py` i24 glob bug.
4. Release when he says: rebuild the frozen exe first (statics + server drift),
   and flip the 0.12.30 disclosure paragraph in `docs/index.html` in the same pass.
5. Standing: verdict-gate legality hole, Iron Man accolade check, gaming box silent
   since 07-29, exploration-log parse.

## Session-local facts worth keeping

- `saves/poison-defender.json` in the repo is a COPY of his Joinny Healer save so
  the dev copy on 5081 has a real 9-box build to measure. Gitignored.
- Loop: dev server on 5081 + the Claude Browser pane for JS geometry (it lays out
  and runs JS **only while the pane is displayed**, never screenshots, and **never
  runs transitions or ResizeObservers**), then the frozen app + computer-use for
  eyes.
- ⚠ **Measure the width the USER has** (a rule set from a 1920 pane did the
  opposite of what he asked at his 1250 window).
- ⚠ **A var() inside a custom property resolves where it is DECLARED** — a `:root`
  token built on `var(--accent)` cannot follow a body-level theme.
- ⚠ **Test input with a real mouse**, never `dispatchEvent`; Escape never reaches
  the page in this shell.
