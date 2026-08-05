# Resume point — 2026-08-05 09:02 ET (new session starts here)

Tracked tree clean, master pushed, **HEAD = `5309e1a7`**. Nothing running; no
scheduled tasks armed. Dev server and scratch browser windows closed.

**Installed app: `%LOCALAPPDATA%\Programs\HeroCompanion`, UNSIGNED dev build,
frozen stamp `297ddcf` + statics copied through HEAD.** Release still HELD at
0.12.30.

⚠ **Statics load at LAUNCH only** (F5/Ctrl+R do nothing in WebView2): copy into
`_internal\static`, then relaunch. server.py changes need a full rebuild.
`WScript.Shell.AppActivate($pid)` fronts the window when `open_application` grabs
an Edge tab of the same name.

## ▶ NEXT SESSION STARTS HERE: the forum report (BasiliskXVIII, topic 64761)

Joel's instruction: "see if we can accommodate actual bugs in this latest post."
Two claims. I checked both against the code; here is what is true.

### 1. "Closing the window leaves the server running in the tray" — ALREADY FIXED, NOT RELEASED
The tray is **deleted in the current tree** (`grep -c pystray run_app.py` = 0;
window close = quit, 2026-08-02 desktop-app work). He is describing **0.12.30**,
released 2026-07-31, which still has it. So the code answer is "fixed, shipping in
the next release" — but two things are still owed:
- **His disclosure point stands for the shipped build.** Nothing on the landing or
  download page said the app keeps running. `docs/index.html` and
  `docs/companion-lite.md` still mention the tray — Lite legitimately keeps its
  tray (do not touch `run_lite.py`), the main app no longer does, so the pages need
  to say which is which.
- **The forum reply Joel already posted says "the update check only runs when you
  click it", which is FALSE in the current code** (it runs on launch). That was
  flagged in CLAUDE.md and is still uncorrected in public.

### 2. "Portable's Check for updates installs the installer" — REAL, UNFIXED
`server.py` `/update/install` gates on `sys.frozen` ONLY. It then always picks the
release asset whose name ends `.exe` and contains `setup`, and runs it
`/SILENT /RELAUNCH=1`. A portable user gets silently converted into an installed
one. He is right, and his framing (the tool clearly can tell the difference) is the
fix: detect portable vs installed — the exe's directory versus
`%LOCALAPPDATA%\Programs\HeroCompanion`, or the presence of the uninstaller — and
then either hand the portable **.zip** asset (the release carries one) or refuse
with a plain sentence and a link. **Minimum honest fix: never silently convert.**
Joel's call on which.

⚠ Both of these are RELEASE-gated: the fix for #1 only reaches users when 0.12.31
ships, and #2 needs a server.py change, so it needs a **frozen rebuild**, not a
static copy.

## What landed this session (all pushed)

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

1. **The two forum items above** — Joel's next order.
2. The catalogue's last empty cell (leave / one row of seven / epic spans it).
3. His layout draft whenever he wants: drag corners, ✕ hide, 📋 Copy, paste to me.
4. Set-bonuses-in-force + rule-of-five meter; "Gear this build" card; origin
   plates; `extract_power_icons.py` i24 glob bug.
5. Release when he says: rebuild the frozen exe first (statics + server drift).
6. Standing: verdict-gate legality hole, Iron Man accolade check, gaming box silent
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
