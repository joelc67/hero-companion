# Resume point — 2026-08-05 evening (new session starts here)

Tracked tree clean, master pushed, **HEAD = `0966af1d`**. Nothing running; no
scheduled tasks armed. A 25-point sweep at close confirmed every deliverable of
the day is present in the tree; full audit suite green (see below).

⚠ **Stage commits BY NAME here, never `git add -A`** — the tree carries hundreds
of untracked benchmark artifacts (swap sweeps, pyspy SVG, stray .bat launchers).
`-A` staged all of them on 2026-08-05; caught by the `--stat` size check.

**Installed app: `%LOCALAPPDATA%\Programs\HeroCompanion`, UNSIGNED dev build,
frozen stamp `297ddcf` + statics current with HEAD.** Release still HELD at
0.12.30.

⚠⚠ **TWO frozen copies exist** — the installer's (Joel's shortcut targets this
one) and `dist\HeroCompanion`. **Use `py tools\push_statics.py`**, which writes
both and prints a coverage denominator; a hand copy reaches one and makes
"verified" a lie. Then RELAUNCH — statics load at LAUNCH only (F5/Ctrl+R do
nothing in WebView2). **server.py / run_app.py changes need a full rebuild.**
`WScript.Shell.AppActivate($pid)` fronts the window.

## 🔨 A FROZEN REBUILD IS OWED BEFORE ANY OF TODAY'S SERVER WORK REACHES JOEL

`server.py` changed twice on 2026-08-05 and the frozen build predates both:
1. `_install_kind()` + the portable refusal in `/update/install`
2. `_SPECIAL_ORIGIN_SETS` → Hamidon/Hydra/Titan/D-Sync in `PIECE_BY_UID`
   (imported HOs showing their internal name)
Everything else from the day is static and is already live in both copies.

## Verification at close (2026-08-05)

`demo_single_build_fixes` 24/24 · `test_desktop_app` 121/121 ·
`test_mbd_alignment` 9/9 · `test_exemplar_view` 18/18 · `audit_tour` (12, incl.
2 new content checks) · `audit_tabs` 10/10 · `audit_links` 178 refs with 5
planted defects caught.

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

## ✅ DONE: the 2026-08-05 UI pass (all pushed; detail in session-report.md)

- **Build menu**: Refine with AI removed (dead in an AI-free client); every gated
  item now says WHY it is greyed. ⚠ The reported "cancel greys the menu" was NOT
  a state bug — reproduced identical before and after cancelling; the silence was
  the defect.
- **View menu**: End Game and Layout mode removed; **Exemplared view opens a
  dialog** that explains exemplaring before asking for a level.
- **Help menu**: Settings / Credits / About as three doors; Settings gained the
  Play Log switch. No tray toggle — the app has no icon and says so.
- **Pop-ups wear the alignment** (one `--accent` rule, all three shapes).
- **Leveling Guide**: side-preview menu moved under the title, Flashback
  explained; preview resets on leaving the tab AND yields to the real toggle.
- **Inherent → Archetype bonus stat** above Defence.
- **Small displays**: both two-column regions collapse below 1400px.
- **Level warning carries its own input**, and the crash it hit is fixed.
- **Tour**: 4 stale bodies + a misplaced mock element corrected; audit_tour now
  checks CONTENT, not just structure.

**▶ OPEN, needing Joel:**
1. **"Build this for me"** is dead in the shipped client for the same reason the
   AI item was (`gen-btn` hides whenever `AI_ON` is false). Point it at the
   wizard, or remove it. His call.
2. **Applying a meter to DISPLAYED damage** (Vigilance +30% solo). It is in the
   SCORE, not the shown DPS. Team-size dependent, so it needs a ruling —
   recommended: ride alongside, never replace (suppression precedent).
3. **"What changed?" / per-change history** — his idea of a change log per
   character with individually revertible entries. Not built; needs scoping.

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
