# Hero Companion — What's New

## 0.12.5 — unreleased

- **The Incarnates brick.** Your six incarnate choices (the solver's
  recommendations, or your own picks) now live in a card of their own — same
  shape as the in-game power trays and docked right above them, with the real
  in-game incarnate icons (family art + rarity ring) and the full ability name
  on hover. Slots you haven't filled show as dashed placeholders.

## 0.12.4 — July 4, 2026

- **Level 1 always satisfies the creation requirement: one primary power AND one
  secondary power**, each from that set's first two — the basics come before
  anything else, on every archetype (same treatment as the epic-pool prerequisite
  rule). A Poison/Sonic Defender's level 1 is Shriek/Scream + Alkaloid/Envenom;
  Envenom-and-Alkaloid-both-at-1 can't happen anymore, anywhere it's displayed.
- **Old saves fix themselves.** A character saved by an earlier version could carry
  an impossible level-1 arrangement that survived every update because it was
  stored with the build. The app now re-checks the pick order every time it
  recalculates and quietly corrects it — open the build and it's right, no
  re-solve needed.

## 0.12.3 — July 4, 2026

- **Only one copy of the app can run.** Launching Hero Companion while it's already
  running now just opens the running copy's page instead of silently starting a
  second (or third) hidden copy on another port — the cause of "the app shows no
  difference after an update" reports: the browser was talking to a leftover old
  copy the whole time. After a self-update, any leftover old copies are shut down
  so the new version is the one you see.

- **Fixed: a generated build's pick levels were dropped when loading an
  AI-designed tier**, so the build grid fell back to naive level badges (Alkaloid
  AND Envenom both shown at level 1). The seated pick levels now survive the load.

## 0.12.2 — July 4, 2026

- **Fixed: slots the game could never grant.** An enhancement slot is earned at a
  specific level and can only be placed in a power you already have — so a power
  picked at level 49 can hold at most 4 slots (its free one plus the 3 earned at
  50), and the 47 + 49 picks share just 6. The optimizer now seats heavily-slotted
  powers earlier in the pick order, re-solves with tighter budgets when even
  reordering can't fit (dense melee epics), and the validator calls out any
  hand-made arrangement the game would refuse ("picked at level 49 — it can hold
  at most 4 slots").

- **Smoother one-click updates.** The tab you click "Update now" in simply becomes
  the new version when the install finishes — the app no longer opens a duplicate
  tab while the old one lingers on the old version. (If that tab was closed, a
  fresh one still opens after a short wait.)

- **Level 1 is now framed as character creation.** In game your level-1 powers are
  one of the first two powers of your primary AND one of the first two of your
  secondary (verified against 2,255 master builds) — the plan now always seats a
  legal creation pair at level 1, the leveling walk says which choice was made and
  what the other option was, and the validator flags a build that skipped both of
  a set's first two powers.

## 0.12.1 — July 4, 2026

- **The decorative frame corners are gone.** The hero/villain identity now lives
  entirely in the color themes; the app uses the full window edge to edge.

- **Fixed: epic-pool pets taken without their prerequisites.** The game requires two
  other powers from an epic pool before its top-tier powers (Ice Elemental, Summon
  Spiderlings…) and one before the mid tier — the optimizer now takes the lower
  powers first, the search respects the ladder, and the validator counts precisely
  ("requires 2 other Ice Mastery powers — this build has 1").

- **Fixed: inherent powers shown as picks.** Health, Stamina, and other inherents are
  granted automatically by the game — the respec order no longer tells you to "take"
  them at a level (they get their own "automatic" footer line with slot counts), and
  their cards wear an "auto" badge instead of a level. Real picks' derived levels no
  longer shift to make room for them.

## 0.12.0 — July 4, 2026

**The layout release** — a complete redesign around one idea: a tight, horizontal,
Sidekick-shaped workspace where every block fits snugly and every gap holds
useful information.

- **The powers wall**: your build is a grid of uniform icon cards — power icon, name,
  level badge, enhancement icons with IO levels — flowing in pick order. No columns,
  no holes.
- **The build summary course**: beneath the wall, three equal bricks — Build Vitals
  (a labeled DEF/RES table plus recharge/recovery/HP/DPS), active Set Bonuses with
  stack counts and rule-of-five warnings, and the Uniques Carried checklist.
- **One tight masthead**: identity and icon-only actions in a single 40px strip.
- **Power Info panel**: click any power's name and a detail column opens on the
  right — type, availability, endurance cost, cast time, live damage/DPA/cycled-DPS
  (proc contributions included), allowed enhancement categories, and what's slotted
  in it right now. Numbers update with every change.
- **Horizontal-first layout**: character setup (archetype, sets, pools, epic,
  incarnates) is a compact left rail with Stats and the Build Assistant stacked
  beneath it; the powers icon grid owns the entire wide side. The masthead is one
  tight strip — identity, vitals, icon-only actions — that stays pinned as you scroll.
- **No AI anywhere.** The panel is simply the Build Assistant — deterministic presets,
  goals, and instant Solve. (The AI seam still exists for those who bring their own
  key, but it's opt-in and invisible otherwise.)
- **The build is now an icon grid** (Sidekick-style): taken powers appear as compact
  cards — power icon, name, level badge — with their slotted enhancements as an icon
  row (IO level under each), arranged in three level columns (1–12 / 14–28 / 30–49).
  Add-power choices moved below the build. Same clicks as before: click a slot to
  change it, right-click to clear.
- **Overview bar**: your build's vitals — typed and positional defense, resistance,
  recharge, HP, ST/AoE DPS — in one color-coded line that stays visible while you
  scroll. Green means you've hit the current-meta mark.
- **Tighter layout**: on wide screens the stats and controls panels sit side by side
  (three columns total), paddings and text are denser — much more of the build fits
  in one view.
- During a one-click update, the old browser tab now says plainly that the app
  reopens in a new tab and this one can be closed — and it refreshes itself into
  the new version the moment you look at it (browsers throttle background tabs,
  which is why it previously seemed stuck on the old version).

## 0.11.1 — July 3, 2026

- **The optimizer now completes winter sets to 6 pieces** when typed defense is the
  goal — the big fire/cold defense bonuses the master builder flagged as missed are
  now chased properly (typed-defense targets carry full priority in the solver).
- **Wizard-built kits include procs by default.** A freshly generated build has no
  slotting to "preserve", so the proc pass now always runs on it.

## 0.11.0 — July 3, 2026

**The master-class release** — the optimizer went to school on 4,000+ builds shared
by one of the community's best builders, plus his direct coaching.

- **Damage procs are now priced.** The engine computes each slotted %Damage proc's
  real contribution (PPM math: recharge, cast time, area factor), so the optimizer
  can genuinely trade set bonuses against procs — the core trade of the current meta.
- **Current-meta defense targets.** Presets now aim for ~35% Smashing/Lethal/Fire/Cold
  (typed) defense — or 35% Melee/Ranged/AoE for positional-armor characters — with the
  freed slots buying damage. Want the old 45% style? Put "classic softcap" in your goal.
  (Fire farm keeps its hard 45% fire floor — farms are still farms.)
- **Hasten gets 2 slots, never 3** — the third recharge IO is worth ~13% of face value
  after diminishing returns. A wasted slot, now unwasted.
- **One-click updates** — "Update now" downloads and installs the new version for you;
  the app closes, updates, and restarts itself. No more trips to the download page.
- Model v24; scoring is stamped, so older champion scores aren't compared to new ones.

## 0.10.1 — July 3, 2026

- **Fixed: power tray icons missing in the installed app.** Three data files (power
  icons, the proc catalog, incarnate magnitudes) were loaded with a path that only
  worked when running from source — in the packaged app they silently loaded empty.
  The tray now shows real power icons, and the solver's proc pass has its full
  catalog back.
- **The app finds your in-game saves for you.** After `/build_save_file` in game,
  click "Find my characters for me" — Hero Companion scans the usual Homecoming
  install locations, lists every character save it finds (newest first), and
  imports on click. Unusual install? Paste your game folder once and it's
  remembered. The manual file picker remains as a fallback.

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
