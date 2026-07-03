# Hero Companion — What's New

## 0.10.0 — July 3, 2026

**The installer release** — Hero Companion now behaves like a proper Windows app.

- **Real installer**: download `HeroCompanion-Setup-0.10.0.exe`, run it, done. It
  installs to a standard location, offers a desktop icon, adds a Start Menu entry,
  registers in Add/Remove Programs with a working uninstaller, and upgrades in
  place. (The portable zip still exists for folder-preferring folks.)
- **No more console window**: the app runs in the background with a tray icon (the
  lime pulse, next to your clock). Right-click it to open the app or quit. Closing
  the browser tab no longer strands a mystery window.
- **⟳ Updates button in the header** — check for updates on demand, whatever you
  answered at startup.
- Your saves live in %APPDATA%\HeroCompanion as always — installing, upgrading, or
  uninstalling never touches your characters.

## 0.9.1 — July 3, 2026

- **Update prompts (opt-in)**: on first run the app asks once whether to check for
  updates at startup. Say yes and new releases show an "Update now / Remind me
  later" banner; say no and only the manual footer button ever checks.
- **Standalone builds are truly AI-free**: no more "AI: checking…" chip or "Ask
  Claude" box that could never work without a paid key. The panel is now the
  Build Assistant — presets, goals, and instant Solve, all fully offline.
  (Advanced: set HC_AI=1 with your own Claude key to re-enable the assistant.)
- **The app has its own icon** — the lime pulse badge, in the taskbar where it
  belongs, instead of the generic packaging icon.
- **Fixed**: the build wizard could clip its lower content on short windows with
  no way to scroll; it now scrolls within the dialog.
- **Fixed**: launching a second copy (or anything else holding port 5000) no longer
  kills the app — it moves to the next free port and says so.

## 0.9.0 — July 3, 2026

**The "Hero Companion" release** — the app has a name, a face, its papers in order,
and a PC body to live in.

- **Standalone PC version**: Hero Companion now packages as a Windows executable — no
  Python, no setup; run it and the app opens in your browser. Your saves live in
  %APPDATA%\HeroCompanion.
- **🐞 Report a bug**: one click opens a pre-filled report (versions auto-included) on
  the project's GitHub page. Nothing is ever sent without your click.
- **🏆 Submit champion**: beat a shipped champion build? Export your candidate and post
  it to the submission queue — verified wins become the next shipped champion, with
  credit.
- **Check for updates**: compares your version against the latest GitHub release.
  Never automatic, never forced.
- **Hero/Villain reskin**: the app is now *Hero Companion* (or *Villain Companion* — flip
  alignment from the banner). Themed corners, colors, and cards; your choice is remembered.
- **Soldiers & Widows leveled honestly**: the level-1-to-50 walk now follows the real VEAT
  career — base powers only until the mandatory level-24 respec, then the full re-place
  order with your Crab/Bane or Night Widow/Fortunata branch.
- **Kheldians leveled honestly**: single-path sets auto-select, inherent flight means "no
  extra travel" by default, and the epic-pool step is gone (they don't get one).
- **Enhancement Converter planner + haul appraiser**: paste your drops (recipes included)
  and get keep/convert/sell verdicts with concrete converter paths and merit costs.
- **Origin pool rule enforced**: only one of Sorcery / Experimentation / Force of Will /
  Gadgetry / Utility Belt per build — the optimizer and validator both know the game
  won't allow a second.
- **Optimizer explores all pools**: Sorcery, Experimentation, and friends are now real
  candidates in the search, not just Fighting/Leadership/Speed/Leaping.
- **Terms, License, Credits**: CC BY-NC-SA 4.0 (free & noncommercial forever), Terms of
  Use, and full credits — including Guyver [SoV] of Sovereign, whose master builds were
  this tool's calibration standard.
- **This help system**: the ❓ Help button and this document.

## Earlier (the road here)

- Physics/encounter model v23: wiki-verified to-hit, resistance, purple patch, mez
  protection, and archvillain rules; role-weighted scoring; scenario coverage.
- Deep optimizer: full-neighborhood search that runs to convergence with honest
  certificates, warm-started from champion builds, learning across runs.
- Leveling companion: per-level walk of the exact Homecoming schedule with cost-smart
  enhancement advice, deviation tracking, and end-game re-fit.
- Mids Reborn import/export compatibility.
