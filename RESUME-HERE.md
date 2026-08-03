# Resume point — 2026-08-02 evening (desktop-app night)

Nothing is running that this session started. No scheduled tasks armed. Working
tree clean, master in sync, **HEAD = `f5415132`**. One stray `python server/server.py`
(PID 30776, Joel's own dev copy on 5080) predates this session — it is not mine and
was left alone; a reboot clears it.

**Hero Companion is INSTALLED from tonight's source**, not from a release:
`%LOCALAPPDATA%\Programs\HeroCompanion`, build stamp `f541513`, **UNSIGNED**. The
desktop shortcut opens it. Closing its window quits it — there is no tray any more.

**Read `coh-builder/CLAUDE.md` first** — standing rules and verified game facts.
This file is current state, the open queue, and the traps earned.

---

## ▶ WHERE TO PICK UP TOMORROW

Joel: *"Save progress, I am shutting down and we can explore this tomorrow."* The
desktop batch is built, installed and working; what is left is judgement calls on
how it now looks, plus the release chores it created.

1. **Look at the balanced layout on a real screen.** The balancer moved the
   Assistant into the wide column, above the powers grid. That is a visible change
   to the app's primary layout and Joel has not seen it yet — measured good
   (imbalance 1745px → 275px) but never eyeballed. If the wide Assistant reads
   badly, the tile list is one array: `_TILES` in app.js.
2. **The 275px residual.** Whole tiles are the unit, so that is the floor with the
   current three cards. Going lower means splitting a card (e.g. the stats rows in
   columns when the card is wide) — not started, may not be worth it.
3. **Signing.** Tonight's installer is unsigned because `TRUSTED_SIGNING_PROFILE`
   is unset and it needs Joel's `az login`. The copy he replaced WAS signed. The
   released signed 0.12.30 installer is preserved as
   `dist\HeroCompanion-Setup-0.12.30.released-signed.exe` (verified Valid) — do
   not delete it; ISCC overwrites the unsuffixed name every build.
4. **The forum sentence** — see below. Still uncorrected, now false in code.
5. **Version.** Still 0.12.30 with a large batch of unreleased work under
   "Unreleased" in the changelog. A bump is Joel's call.

⚠ **`extract_power_icons.py` i24 glob bug** and the champion re-cert are still
parked exactly where they were. **No wave was started.**

---

## ⚠ THE ONE THING THAT MUST HAPPEN FIRST

**Joel's forum reply is now factually wrong in one sentence.** It says:

> "The planner is fully offline, and the update check only runs when you click it."

**As of 2026-08-02 that is FALSE in the code** — the launch check shipped
(`initUpdateFlow` runs it unconditionally). The post has NOT been corrected;
BasiliskXVIII is exactly the reader who will check. **Correct it when the
desktop build publishes.** Accurate replacement: the planner still contacts
nothing but GitHub's releases API, it compares version numbers only, it sends
nothing about the user or their builds, and it can be turned off in
About & Settings.

---

## 🧩 LAYOUT: TILES, NEVER A SCROLLBAR (`f5415132`)

Joel: *"I do not like the split, I mean it makes sense, but there is obvious
imbalance, and there is no desire for a scroll bar in the middle of this app.
Think of the spaces on the left as tiles that can be shuffled to make it all
balanced."*

- **⚠ NEVER cap the rail with its own scroll.** That fix worked and was rejected
  on sight. `.rail` carries a comment saying so; the battery has a negative
  control that fails if `overflow-y: auto` or `max-height` reappears on it.
- `balanceColumns()` in app.js places `_TILES` (assistant, stats) in whichever
  column minimises `max(left,right) + 0.5·|left−right|`, **measured for real** —
  tile heights depend on column width, so no arrangement can be predicted.
  1900×1150: imbalance **1745px → 275px**, page 3992 → 3268.
- **⚠ The Assistant's slot is ABOVE `#builder`, never below.** It was moved to the
  top of the rail on 2026-08-01 after a field report could not find it at 78% down
  the page. Shuffling must not quietly undo a placement someone already complained
  about.
- Below 980px the grid is one column: every tile goes home in documented order.
- Triggers: `resize` + a **width-guarded** ResizeObserver on `main` (the
  power-info column changes main's width while resizing nothing; the guard exists
  because re-tiling changes main's HEIGHT and would re-notify forever).

## ⚠⚠ THE CLAUDE PANE FIRES NO LAYOUT CALLBACKS AT ALL (measured 2026-08-02)

Not `resize`, not matchMedia `change`, not ResizeObserver — **not even the initial
observation, and not for a width change forced in script.** This is the same class
as its known 0×0-viewport geometry blindness, and it cost a wrong diagnosis: a
viewport change failed to re-tile, I called the resize listener broken and rewrote
it, then discovered nothing fires there. **Corollary for every future layout job:**
`resize_window` first (or `elementFromPoint` returns null and every hit-test reads
as a pass), verify the FUNCTION by calling it directly at each viewport, and treat
any event-driven trigger as unverifiable here — it needs Joel's window.

## ✅ THE DESKTOP BATCH — DONE 2026-08-02, TRAY DELETED, EXE BUILT

**Joel's verdict on the first prototype: "it appears to be a browser still, and
obviously a python executable, its not a self contained application like Mids
Reborn."** He was right on both counts and both are fixed:

- **The python/console half was my scaffolding, not the product.** A `.bat` that
  runs `python run_app.py` with a visible console is not what ships. The answer
  is the frozen build: `dist\HeroCompanion\HeroCompanion.exe` — one icon, no
  console, no Python on the user's machine. **Built and verified**: one process
  named HeroCompanion, `MainWindowTitle "Hero Companion"`, serving on 5000, and
  **closing the window exits the process** (proven with a WM_CLOSE: `HasExited
  True`, port dead). Judge the app from the exe, never from the .bat.
- **The browser half was real and is fixed in `_run_window`.** pywebview's
  defaults are a *browser's* defaults: `SHOW_DEFAULT_MENUS` gave WebView2's
  right-click Back/Reload/Save-as/View-source menu (the loudest tell), the
  background flashed white on a dark app, and downloads were live. All off.
- **⚠⚠ The bug that mattered most: `private_mode` defaults to TRUE**, which
  throws localStorage away on every launch — the alignment theme, the update
  switch, the tour's saved spot and finished flag, all silently forgotten each
  time. Now `private_mode=False` with a `storage_path` beside the app's state.
- **⚠ The window icon MUST be a `.ico`.** A `.png` throws inside
  `System.Drawing.Icon` on a .NET thread, OUTSIDE the try/except, so the app
  dies with no window and no fallback message. Cost one silent exit today.

**The tray is DELETED** (`_run_tray`, the first-run notice, the autostart
MessageBox, `app_state.json`, pystray in the spec, and
`tools/test_tray_first_run_notice.py`). The window is the DEFAULT; `HC_WINDOW=0`
is the escape hatch to a browser tab. The self-update hook survived the deletion.

Battery `tools/test_desktop_app.py` **36/36**.

### Superseded: the original one-step-left note

All five pieces are in. `pywebview 6.2.1` + `pythonnet 3.1.0` installed; the
window was launched for real on port 5083 and served the app through WebView2
with no fallback message, and `/meta/update-check` fired on its own in that
same launch (both proofs in the server log). Battery:
`tools/test_desktop_app.py` **28/28**, standing gate 24/24, tour 10/10, tray
battery still 9/9.

- **1. Window** — `run_app._run_window(port)`, selected by `HC_WINDOW=1` in
  BOTH source and frozen runs. `main()` tries it before any browser open and
  falls through to browser+tray if pywebview or WebView2 is missing.
  Spec updated (`webview`, `webview.platforms.edgechromium`, `clr_loader`,
  `pythonnet`).
- **2. Tray** — window mode is already tray-free: no icon, no autostart
  MessageBox, and `server.SHUTDOWN_HOOK = _quit` keeps the self-update path
  (`POST /app/shutdown`, `_graceful_self_exit_for_update`) working. The exit is
  immediate because there is no icon to un-ghost.
- **3. Update check** — automatic; the first-run "check at startup?" banner is
  deleted. Off switch moved to About & Settings.
- **4. Autostart** — `POST /app/autostart` + `server.AUTOSTART_SET_FN`
  (`run_app` supplies `_set_autostart`); the checkbox renders from a live
  registry read-back, so a refused write shows the truth.
- **5. Share prompt** — `#share-modal`, fired from `hideEntry()` so it never
  stacks on the entry screen. Asks only when a key is present and
  `asked_here` is false (new `pulse_feed.feed_status` field: absent vs.
  explicit-no were indistinguishable before). ✕ stores nothing.
  `client_config.json` boards URL → `https://hero-companion.com/pulse/`.

**▶ THE ONE STEP LEFT, and it is Joel's look:** run
`set HC_WINDOW=1` then `python run_app.py` (or the desktop shortcut with that
env set). When he approves, flipping the default is one line — make `_WINDOW`
default true — and then **DELETE** `_run_tray`, the pystray spec entries, and
`tools/test_tray_first_run_notice.py`. They are deliberately still alive until
he has seen the window, so the flag-off path is never a no-UI app.

### The original brief (kept for the detail)

## ▶ THE ACTIVE BATCH: DESKTOP APP (approved, NOT started)

Joel, 2026-08-02: *"go ahead with the desktop app, keep the update check
automatic on launch. No tray icon for Hero Companion, but Companion Lite remains
a desktop app. One can easily enable/disable launching when windows starts."*

**Nothing has been installed or changed for this yet.** A `pip install pywebview`
was proposed and Joel interrupted before it ran, to get this handoff written. His
machine is untouched.

### The five pieces, and where each lives

1. **Native window instead of a browser** — `run_app.py`.
   Route: `pywebview` + WebView2. **WebView2 runtime is CONFIRMED present on
   Joel's box (150.0.4078.105)** and ships with Win10/11, so end users need
   nothing extra. Flask keeps serving on localhost; the window points at it.
   ⚠ Needs `pywebview` and (Windows backend) `pythonnet`. Joel has APPROVED the
   dependency. It still means PyInstaller spec changes (`HeroCompanion.spec`) and
   a fresh Bitdefender FP submission per docs/signing-runbook.md.
   ⚠ Prototype behind a flag first so he can see it before it is the default.

2. **No tray icon for Hero Companion** — `run_app.py:_run_tray()` (~line 203).
   The whole tray goes: `pystray.Icon`, the menu (Open / autostart / updates /
   Quit), and `server.SHUTDOWN_HOOK = _graceful_quit`. Closing the window quits.
   ⚠ `_graceful_quit` also serves the SELF-UPDATE path (`/app/shutdown`,
   `server._graceful_self_exit_for_update`) — the window build must still expose
   an equivalent, or in-place updates break.
   ⚠ The first-run tray notice shipped TODAY (`270f03bb`) becomes dead code when
   the tray goes. Remove it with the tray, and remove
   `tools/test_tray_first_run_notice.py` with it.

3. **Automatic update check on launch** — the endpoint already exists,
   `/meta/update-check` (`server.py:857+`, `update_check()`). Today it is only
   called by a click (`app.js checkUpdates()`, wired at the `#update-check`
   listener). Make it fire on launch. See the warning at the top of this file.

4. **Autostart toggle moves into the app** — currently ONLY in the tray menu
   ("Start automatically at login" → `_toggle_autostart` / `_autostart_enabled`
   / `_set_autostart` in `run_app.py`). With no tray it must appear in the UI.
   Joel: *"One can easily enable/disable launching when windows starts."*

5. **Share prompt on launch, with SPECIFICS** — `server/pulse_feed.py`.
   Joel wants the user asked whether to share, with the anonymity spelled out and
   a link to the boards (**hero-companion.com/pulse**).
   Current state, verified in code: sharing is OFF unless something explicitly
   writes `feed_disabled = False` (`pulse_feed.py:165` — *"Absent = this app was
   never asked = it does not upload"*), gated on `accept_terms()`.

   **What is actually shared** (read from `pulse_feed.py` + `TERMS`, quote this
   accurately — being vague here is what started the whole thread):
   - Captured locally, only while `/logchat` is on: your own rewards (XP,
     influence, drops, merits, badges, defeats); recruitment facts from PUBLIC
     channels (what is forming + the recruiting CHARACTER name); auction-house
     sale prices. **Never raw chat. Never tells.**
   - Before upload, the account login name is replaced by a SHA-256-derived code
     (`_pseudonym`) — the real name never leaves the machine. Uploads carry an
     anonymous install id.
   - **Character names ARE included** and are not shown publicly today. That is
     the one thing a user should consciously agree to.
   - Never read at all: machine names, file paths, anything outside the game log.
   - The public board shows what is forming and when, public-channel recruiter
     character names, and per-item sale prices. Never account names, money
     totals, who sold what, or machine details.

6. **Companion Lite is UNCHANGED** — `run_lite.py`. Joel: *"Companion Lite
   remains a desktop app."* Do not touch its tray or its lifecycle.

---

## ✅ SHIPPED TODAY (all pushed, all green)

Field-report batch from BasiliskXVIII (forum topic 64761) plus Joel's own finds.

| what | commit |
|---|---|
| Activation-gated procs pay only where they fire (Panacea family) | `053c76bd` |
| Verdict gate: legality outranks score | `07ce596e` |
| Travel powers: one list, six bugs | `e95e23f4` |
| Roles explain themselves; Generalist stops nagging | `275c8b16` |
| Type ladder + quieter export button | `a505d183` |
| Grouped role picker | `f680c47a` |
| Movers measured (20 of 24 moved) | `98098e5f` |
| Wall of text: progressive disclosure + folded panels | `dcfb27c8` |
| Assistant unburied (78% → 25% down page) + contrast | `eb34dacd` |
| Motion/feedback pass (design doctrine audit) | `5879c5b6` |
| Wordmark: gradient → solid | `cc095592` |
| Tour diagram overlap + geometry check in audit_tour | `699b7df2` |
| Exemplar report on the level plan | `0fd077ae`, `a1361956` |
| Enhancement level rule pinned from client bins | `276cf249` |

Earlier the same arc: four-way alignment (`3d62f4fa`, `eb1aa204`), archetype
emblems (`e99524e1`, `59e25203`).

**Reverted deliberately, do not resurrect without a new decision:** the alignment
backdrop (`b6baa53b` reverts three commits) and the gold-forward palette "depth
pass" (`0608986a`). Joel's verdict on the latter: *"This just looks like you
messed with theme colors, put it back."*

### Batteries added today
`tools/test_proc_host_gate.py` (15) · `tools/test_verdict_legality.py` (7) ·
`tools/audit_travel_powers.py` (14) · `tools/test_exemplar_levels.py` (8) ·
`tools/test_tray_first_run_notice.py` (9, dies with the tray) ·
`tools/measure_proc_host_movers.py` · `tools/extract_boost_level_tables.py` ·
`tools/extract_gui_emblems.py`. Standing gate 24/24, `audit_tour` now 10/10.

---

## ⏸ PARKED, NEEDS JOEL

- **Champion re-cert.** The proc fix moved **20 of 24** contexts (11 up, 9 down,
  median ±70, range +243.9 to −161.0; 19 of 20 are `itrial`). Re-run
  `tools/measure_proc_host_movers.py` to reproduce. A wave needs his word, and
  the gaming box has not woken since 2026-07-29 11:51.
- **Iron Man accolade grant** — only his in-game look settles it.
- **Exemplared stat totals.** Now possible because the enhancement rule is
  pinned: recompute def/res/recharge at level L with only surviving powers,
  slots, and working enhancements.

---

## ⚠ TRAPS EARNED TODAY (each cost real time)

- **Client art is split across TWO asset sets with different naming.** live =
  `texture_*.pigg`, issue24 = `tex*.pigg` / `stage*.pigg`. A `texture_*` glob
  matches ZERO files in i24. Always glob `*.pigg` across both.
- **`extract_power_icons.py` still has that glob bug** — its documented i24
  fallback has never run. May close some of the 38 missing power icons.
- **Never classify a power by its internal name.** `Leap` displays as
  *Acrobatics*; `Long_Jump` is the real Super Jump; `Invisibility` is reused by
  Illusion Control. Four of six travel-list entries were ghosts.
- **`totals` holds floats and dicts ONLY.** Putting a list in it broke Force
  Feedback seating downstream and the standing gate caught it.
- **A bisect that reverts the wrong file proves nothing.** Testing "solver only"
  reverted `engine.py`, where the FLAGS live, so the solver gate was inert and
  passed for the wrong reason.
- **Measure the composited backdrop, not the translucent overlay.** My first
  contrast pass claimed 17 failures with ratios near 1.0 (i.e. invisible text
  that is plainly readable). The real answer was 6.
- **Minimum contrast lift is not enough** — a value computed at exactly 4.5 read
  4.48 on a differently-nested card. Give margin.
- **A check that cannot fail is worse than no check.** My first tour-geometry
  check reported PASS on the exact bug it was written for; my first attempt to
  prove that printed "bug re-introduced" *unconditionally* without verifying the
  edit applied. Both now carry built-in negative controls.
- **Scripted writes must be binary-preserving.** A text-mode write rewrote CRLF
  across two files: 4,132 insertions for a 42-line change. The guard caught it.
- **Verify what a number measured.** I nearly reported "5.4 screens / 4,096
  words" as an improvement — measured while two panels were broken and rendering
  nothing.
- **The dev server does NOT reload Python.** `debug=False`. It ran for hours
  serving pre-change server code while I told Joel to reload. Restart it after
  every server-side edit.

---

## How to work here

- Dev copy: `PORT=5080 python server/server.py` in the background, then
  **http://127.0.0.1:5080**. The installed tray app owns 5000 — never touch it.
- ⚠ Getting into the app requires an entry-modal choice; "Continue where you left
  off" → Resume is fastest.
- ⚠ The Claude browser pane **cannot screenshot** (no compositing) but CAN load
  the page and run JS. `getComputedStyle` over the live DOM is the verifiable
  half — pull real values and render them into an image to actually look.
- Batteries: `tools/demo_single_build_fixes.py` (24, the standing gate),
  `tools/audit_tour.py` (10), plus the ones listed above.
- `session-report.md` (outside the repo) is outbound; `ideas.md` is inbound;
  chat is 10 lines max.
