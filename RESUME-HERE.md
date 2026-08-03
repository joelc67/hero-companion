# Resume point — 2026-08-03 (handoff: the tabbed-layout / desktop-app arc)

Working tree clean, master in sync, **HEAD = `add31d66`**. Nothing running that
this session started; no scheduled tasks armed.

**Installed and working: `%LOCALAPPDATA%\Programs\HeroCompanion`, build stamp
`add31d6`, UNSIGNED.** The desktop shortcut opens it. Closing the window quits it.

**Read `coh-builder/CLAUDE.md` first** — standing rules and verified game facts.
This file is the live handoff.

---

## ⚠⚠ THE FIRST THING: GET YOUR EYES BACK

Joel's sharpest correction this session was *"I feel like you are going about
this blind. Is there a third party tool we can integrate to give you eyes?"* He
was right, and the answer is **computer-use**:

```
ToolSearch: "computer-use"  →  mcp__computer-use__request_access
            apps: ["Hero Companion", "MidsReborn"]
```

Then `screenshot` / `zoom` / `left_click` drive the REAL installed window. Every
layout fix after that point was seen, not inferred — and roughly half of them
were things measurement said were fine.

⚠ **The Claude browser pane is NOT a substitute.** It fires no layout callbacks
at all (no resize, no matchMedia, no ResizeObserver — measured), collapses to a
0×0 viewport where `elementFromPoint` returns null and every hit-test reads as a
pass, and times out at 30s so a long driven sequence must be detached and polled.
It is fine for *logic* (call a function, read state), useless for *appearance*.

---

## The iteration loop (this is the fast one)

**Static-only change** (app.js / style.css / index.html) — no rebuild:

```
Stop-Process HeroCompanion; copy the file(s) into
%LOCALAPPDATA%\Programs\HeroCompanion\_internal\static\ ; relaunch the exe
```

**Any server.py or run_app.py change needs a FULL rebuild** — the frozen build
carries `server.py` inside the PYZ archive, so copying it does nothing. Cost me
one confused verification round:

```
PyInstaller HeroCompanion.spec --noconfirm  →  ISCC installer\HeroCompanion.iss
→ run dist\HeroCompanion-Setup-0.12.30.exe /SILENT  →  launch the desktop shortcut
```

⚠ Installing overwrites `dist\HeroCompanion-Setup-0.12.30.exe`. The RELEASED
SIGNED 0.12.30 is preserved as `HeroCompanion-Setup-0.12.30.released-signed.exe`
— do not delete it.

---

## What this session built (22 commits, `0d3eb420..add31d66`)

**The app is now a five-tab desktop application, not a browser page.**

| area | state |
|---|---|
| Window | pywebview → WebView2, no tray, close = quit, sized to 92% of the actual screen |
| Shell | build tile (identity) + tab strip, both sticky; Character / Build / View / Help menu bar |
| Powers & Slots | a **respec screen**: level-ordered picks, game prereqs, power catalogue, detail card |
| Stats | multi-column board + Vitals / Set Bonuses / Uniques |
| End Game | Epic + Incarnates + Accolades |
| Leveling Guide | the 1-50 road (moved out of its modal), art on top |
| Logging | Play Log + Pulse consent |

Fit is by **zoom**, solved once for the whole app from the tallest tab, floor
1.00 (never shrink — that is what made everything tiny), ceiling 1.60.

---

## ⚠ TRAPS EARNED THIS SESSION — each cost real time

- **`evaluate_js` from inside pywebview's `closing` handler DEADLOCKS the app.**
  The handler runs ON the GUI thread; evaluate_js dispatches to that thread and
  waits. Shipped it, hit "Hero Companion (Not Responding)" on the first close.
  Fix: the page PUSHES its dirty flag via `js_api`, and the prompt fires from a
  worker thread. The veto is one-time so no dialog can trap the user.
- **A z-index on a child cannot escape its parent's stacking context.**
  `#masthead` at 30 with sticky bars at 40/39 meant its dropdown (z-index 120)
  was clipped — the top two Build menu items rendered and were off-screen.
- **CSS escapes did not survive my scripted writes.** `content: "\2003 "` came
  out as a box plus a literal `3`. Use real characters, or padding + a real tick.
- **`collapseLongExplanations` eats any muted block over 26 words** and folds it
  behind "more". It ate a rules line the moment it was written. Rules lines carry
  `.keep-whole` now and the helper skips them.
- **These are CRLF files and scripted inserts default to LF.** Normalise before
  committing or the diff is a line-ending storm (the guard in CLAUDE.md).
- **Disabling options instead of removing them changes what "first option"
  means.** The pool cascade then picked Concealment four times — an illegal
  build. Take the first *available* option.
- **The Bash tool's cwd drifts after a `cd`-chained command.** Bit me three
  times; use absolute paths or `git -C`.

---

## ▶ OPEN, in the order I would take them

0. **THE NAVIGATION REBUILD IS NOT DONE (Joel, 2026-08-03).** The tabbed shell
   exists but navigation work continues. **Do not raise or prompt about the tour
   rebuild until Joel says navigation is complete** — the tour describes whatever
   navigation ends up being, so redoing it earlier is wasted twice.
   **Layer pass done 2026-08-03 evening (installed build stamp `df6c894`):**
   audit_tabs.py built and green (caught autopick silently dropping wizard
   exposure/travel — fixed), Switch-character fix, Name field on the build
   tile, desktop export FIXED (ALLOW_DOWNLOADS ate it; now a real Save As via
   js_api — verified: valid .mbd from the frozen exe), honest save badges
   (needs the rebuilt server, now installed), autosave named-stamp fix + save
   repair.
   **Second polish round same evening (`3869b135`, statics deployed to the
   installed copy):** tabs moved to the very top (above the build tile), active
   tab = solid accent block, header Journey pill DELETED (alignment mis-click),
   Leveling Guide reordered art → level banner → road, green ✓-ringed completed
   levels, 50-kits show the whole road green + "Level 50 — finished build"
   banner (fixes the stale-placeholder read; the road also rebuilds when the
   remembered tab is Leveling Guide). Sticky offsets for tabbar/build-tile are
   ESTIMATES (40/78px) — fine while the page never scrolls; re-measure if an
   overlap shows at the zoom floor.
   **Still open from the pass:** (a) **"targeted level" / exemplar-aware
   planning** — design paper WRITTEN 2026-08-03 at
   `C:\Users\joelc\code\exemplar-target-level-paper.md`, awaiting Joel's
   rulings R1-R4. Key finding: Mids Reborn's exemplar support is a text label
   (ExempHigh/Low feed one string, zero math) — nothing to align with, clear
   room to be better. Layers: (1) "Played at level N" honest view, (2) advice
   card in numbers, (3) solver objective = MODEL BUMP + recert, gated on R3.
   Game rules in §2 are TO-PIN (wiki-verify) before any code trusts them. (b) **At release time the forum reply
   needs two edits**: "right-click the tray icon → Quit" (the tray is gone —
   window close quits) and "the update check only runs when you click it"
   (it runs automatically on launch since 2026-08-02). Both statements are
   still TRUE for the released 0.12.30, so they only go stale when this
   update publishes.
1. **The guided tour is stale and `audit_tour` is RED (57 of 58 targets)** —
   GATED behind item 0, do not prompt. It walks a mock of the OLD single-page
   layout. Joel ruled: *"all the tour slides will have to be redone completely.
   But they can exist in the menu, perhaps under Help."* It is already under
   Help. **I deliberately did NOT patch the audit to pass** — a tour describing
   a dead screen should read as red.
2. **The advanced path is unverified against the new shell.** I drove the
   beginner path hard (open → pick → 24-pick ladder → save → quit → reopen) and
   an imported build, but NOT solve → respec → custom targets → export.
3. **Release is still 0.12.30 and every build since 7/31 is UNSIGNED.** Signing
   needs Joel's `az login` (`TRUSTED_SIGNING_PROFILE` unset). A large batch is
   staged under "Unreleased" in the changelog. Version bump and publish are his
   call.
4. **The forum reply is still factually wrong** — it says the update check "only
   runs when you click it"; it has run on launch since 2026-08-02.
5. Parked from before: champion re-cert (his word), `extract_power_icons.py` i24
   glob bug, origin plates unplaced, gaming box silent since 2026-07-29.

## Design decisions Joel made this session (do not re-litigate)

- No default *character*; a default **position** in every list. Changing the
  archetype re-cascades everything.
- Powers & Slots behaves like the **in-game respec**: level order, real prereqs,
  then slot it all up.
- **Grey out, never hide**, anything the rules forbid — the greyed row is what
  teaches the rule.
- The window **zooms**, it does not rearrange. "Not a break a working screen
  layout."
- **No scrollbar inside the app.** One at the window edge if a tab is genuinely
  taller than the screen.
- Characters get **names**; the app must never invent one.
