# Hero Companion — What's New

## Unreleased — Companion Lite 0.1.13

- **The "Publish" menu entry is gone.** The board was never supposed to need a publish
  button — it lives online and keeps itself current. What remains is a one-time "Set up
  online board (owner)" entry that only appears until a token is in place, then
  disappears.

## Companion Lite 0.1.12 — July 7, 2026

- **Your Pulse Board now lives online, not on the game machine.** On the owner's machine
  (the one with a publish token), Companion Lite keeps the live web page current
  automatically — publishing at most every 15 minutes and only when new play was
  captured — and "Open Pulse Boards" opens the online page directly. Machines without a
  token are untouched: their board stays a private local page and Lite never talks to
  the network.

- **Published boards are scrubbed before they leave the machine.** The public variant
  drops the local file path and never shows account login names — an unnamed character
  appears as "Unnamed character #1" until capture learns its name. Character names
  (which are public in game) are kept.

- **The server pulse counts formations, not shouts.** A recruiter repeating "lf2m dfb"
  until the team fills is one formation, not a sighting per shout: repeated asks for
  the same content collapse into one, the recruiter saying "full" closes it (their next
  ask is a new run), and 10 minutes of silence does too. Dual-boxing is covered by the
  same rule — two of your clients logging the same shout count it once.

- **Money stays off the public board.** Influence earned/spent and market flow show
  only on your private local board — how much anyone makes is not community data. The
  future price board will use per-item prices, never personal wealth.

- **Levels, badges, and merits wait for the character sync.** A fresh capture only sees
  a sliver of a multi-year character, so achievement state stays off the public board
  until a one-time in-game character sync (level, badges, accolades, vet levels) can
  bring a character over whole. Public character cards show play since capture began:
  days seen, XP, drops, defeats.

- **"Recent formations" actually shows recent ones.** The card was frozen on the first
  20 sightings ever captured; it now rolls with the latest 20.

## 0.12.11 — July 6, 2026

- **Sharper end-game builds from a fully re-converged optimizer.** The best-known build
  for each context was re-solved to true convergence under the current model and the
  corrected proc data, so the head start the tool builds from is stronger.

- **Live play capture (opt-in, private messages excluded).** With chat logging on, the
  app turns your sessions into insight — your own rewards and drops, plus what's forming
  on your shard from the public recruitment channels. It learns your server's shorthand
  as it reads. Private messages (tells and whispers) are never captured, and nothing
  leaves your machine.

- **Long-recharge attacks and holds now get the proc treatment (model v25).** A
  single-target power like Seismic Smash or Dominate keeps a 2-3 piece accuracy/damage
  core and fills its remaining slots with damage procs when the proc math favors it —
  the classic expert pattern. The kept core avoids recharge pieces on purpose (slotted
  recharge lowers proc rates). Pet summons are never raided; their slots stay the pet's.

- **Proc rates corrected from the game itself.** Every damage proc's rate now comes
  straight from the current game data; 11 were wrong, including the archetype set procs,
  which were undervalued by up to 43%.

- **The respec suggestion now notices when the optimizer has learned.** Resuming a build
  made under an older version offers "Built under an older optimizer — see what's
  improved?" even when nothing is structurally wrong with the slotting. Build the plan to
  see whether a respec is worth it; if nothing meaningful improves, it says so. Saying
  "no" is remembered for that character until the optimizer actually changes again.

- **IO levels show on resumed builds again.** Resuming a saved character could show set
  pieces without the level badge under their icons (while common IOs still showed 50).
  Saves are now healed as they load, so every existing save gets its levels and icons
  back without re-saving.

## 0.12.10 — July 6, 2026

- **Pet summons are slotted for the pet now.** A summon power — Mastermind henchmen, a
  controller or Arachnos pet, Gang War, Phantom Army — was sometimes being used as a parking
  spot for the player's own always-on healing IOs (Numina, Miracle, Panacea) instead of a set
  that actually helps the pet. Those healing IOs belong in Health, where they buff you, so
  that's where they go now. Every pet summon is reserved for a real pet set — its accuracy,
  damage, and the pet enhancement bonuses (and the Mastermind archetype IOs) — and is forced
  to take one rather than sitting on filler. Thanks again to Maelwys for the example. Deeper
  slotting quality (procs versus full sets by attack, minus-resistance procs, when recharge in
  a summon actually matters) is still being tuned.

## 0.12.9 — July 6, 2026

- **Game data brought current.** Our numbers came from a Mids database that turned out to be
  about six months old, so recent balance patches were missing. We now reality-check against
  the live game and fixed everything that had drifted: the Brute, Sentinel, Tanker, and
  Dominator defense/resist/damage modifiers (this is why Brute defense was reading low), a
  batch of power endurance/recharge/range values, and slotting rules — including Mastermind
  archetype IOs now being slottable in personal attacks. Set bonuses were checked and are
  current. Thanks to Maelwys on the Homecoming forums for catching the stale data.

- **The slotting tags now show on any build, not just after Solve.** Resume or import a
  build and each power shows why it's slotted the way it is (full set / proc bomb / global
  mules) right away — previously those tags only appeared right after solving, which made a
  loaded build look like the update hadn't taken.

- **Respec worksheet.** When you resume a build with slots not earning set bonuses, a small
  bar appears at the top of the build — "Ready for respec?" — that opens the full plan as a
  pop-up (so it's there when you want it, out of the way when you don't). The plan shows
  every change power by power — the old slotting struck through, the new below it — the stat
  gains, and a grocery list split two ways: what to craft or buy, and what to unslot and sell
  (with a note on each item's worth). Every line has a checkbox to track your progress, and
  the whole thing is saved to the character, so you can work it over several sessions of
  crafting (the bar shows "N/M done"). Apply it to your build when ready, Undo to revert, or
  mark it completed. It never appears on a build that's already well slotted.

- **Explanations everywhere.** The slotting tags (proc bomb, full set, frankenslot, global
  mules) and the respec card now have a **?** that opens a plain-language explanation of what
  the term means, why that approach is used, and your options — including why, for example, a
  frankenslot can beat a single six-piece set.

- **Updating no longer leaves a ghost tray icon, for real this time.** When the app
  updates itself, it now removes its own tray icon cleanly before the installer takes
  over, instead of being force-killed and leaving a dead icon behind that only clears
  when you mouse over it. (0.12.8 improved this for extra copies; this closes the main
  path — the app replacing itself.)

## 0.12.8 — July 6, 2026

- **Watch multiple accounts at once — per-character stat cards.** Dual-boxers can now
  tick more than one account, and the Play Log shows a card per character side by side
  (Rattle's kills and haul next to your farmer's), each with its own fit link. Accounts
  are toggle chips — click to add or remove one from what's watched.

- **The Play Log moved up into the main workspace.** Instead of a detached strip far
  below everything, it now docks in the wide build column — filling that space when no
  build is loaded, and sitting neatly under the build when one is. On narrow screens it
  still stacks full-width like the rest.

- **Cleaner haul advice.** Incarnate salvage and crafting materials no longer get a
  "KEEP" tag — there's no decision to make (you bank them and spend later), so the
  haul now saves its keep/sell verdicts for the drops that actually warrant one
  (enhancement recipes and salvage). Incarnate materials are still counted in your
  loot summary.

- **The Play Log now knows who you're playing — and links to their fit.** It reads
  the character name from the log ("playing Rattle") instead of only showing the
  account, tracks it across character switches, and attributes your stats to the
  right character. If that character has a saved build in Hero Companion, a
  one-click **"load their fit"** link appears — so switching from Rattle to Lime
  Juice brings up Lime Juice's build, not whoever you had open. (The game only names
  your character on a fresh login, so if it says "not detected yet," log out to
  character select and back in.) Because players sometimes rename characters,
  the fit link is one you can set explicitly — "link the open fit to this
  character" — so it sticks through a rename and fixes any wrong name-guess. No
  fit for a character yet? It offers to import their build straight from the game.

- **The Play Log's account switch is now obvious.** Which account you're watching
  shows as a row of chips (the active one highlighted with ●), and switching is one
  click on another chip — no more hunting for a "change account" link. For
  dual-boxers this matters: each account is its own log, so you flip between your
  two characters' stats instantly, and a note says so.

- **Your farm haul now knows your build.** When the Play Log is watching a character
  that has a saved fit, any drop whose set your build actually uses gets starred and
  floated to the top of the haul as a **"keep — for your build,"** naming the power
  that wants it. A standard set you would normally vendor becomes a keep when it is in
  your plan. Drops that do not fit still get the usual keep-or-sell advice.

- **Every power now explains how it is slotted.** Each power in a generated or solved
  build wears a small tag saying *why* it is slotted the way it is — 🎯 a full set for
  its bonuses, 💥 a proc bomb (more AoE damage than a set here), 🌐 global mules
  (uniques that each work from one slot), or a deliberate frankenslot. Hover it for the
  full reasoning. High-end slotting can look like scatter until you know the plan; now
  the build tells you the plan.

- **Fixed some warnings that were plain wrong.** The off-role check used to tell a Brute
  or Mastermind its powers "do not extend to damage dealer," which is nonsense — those
  are damage dealers and are now recognized as such. The "no damage enhancement" warning
  no longer fires on a power that is carrying a real set or damage procs. And Physical
  Perfection (and the epic-pool tier rules around it) now require the correct number of
  prerequisite powers, verified against a large corpus of real builds.

- **Better proc choices.** When the optimizer proc-bombs a power, it now ranks the
  available procs by actual expected damage, so the strongest procs land instead of
  whichever the data happened to list first.

- **The tray icon behaves.** Updating no longer leaves a "ghost" tray icon that only
  clears when you mouse over it — the old copy now shuts down cleanly and removes its own
  icon before the new one takes over. The tray menu also gains **Check for updates…**
  (it tells you right there whether a new version is out) alongside Open and Quit. Hero
  Companion keeps running in the tray after you close the browser tab so reopening is
  instant; the tray menu is how you drive or quit it.

## 0.12.7 — July 5, 2026

- **The Play Log parser is now built on real logs.** The first cut guessed at line
  formats; this version is validated against tens of thousands of lines of actual
  Homecoming chat logs. It reads XP and influence, enemies defeated (a real kill
  count), every drop sorted into recipes / salvage / incarnate materials / crafting
  mats with keep-or-sell advice, and Consignment House sales and purchases — while
  correctly ignoring the wall of combat, heal, and chat spam around them. Recipe
  drops map to their enhancement set for a proper verdict. (Veteran levels aren't
  written to the chat log by the game, so post-50 progress is shown as the
  incarnate materials you earn instead — that's what the log actually records.)

- **The Play Log reads live and walks you through setup.** Once you pick an account
  it now updates on its own as you play (a "● live" marker shows it's watching), so
  you don't have to keep clicking refresh. A built-in guide spells out the one-time
  in-game setup — make a chat tab named "Companion", add all channels to it, and turn
  on `/logchat` — so the only thing you have to remember is turning the log on. If
  there's no chat log for the day, the app says so and tells you how to start it. The
  opening screen is now framed simply: turn your sessions into *your* stats, all
  private and local — with any future community sharing kept as a separate choice.
  A plain privacy note spells out the promise: the tool only ever handles game
  data (prices, drops, stats), never your real name, email, location, IP, or
  account login, and never anything about the other players in your chat log.

- **The Play Log now asks before touching anything.** It read game files without
  asking and without saying what happens to the data — against this app's own
  rules. Now the section opens with a plain statement: what it reads (the chat
  logs your game writes), what you get (insights), and the promise — everything
  stays on this computer, nothing is uploaded or shared, and any future optional
  sharing will be a separate, clearly labeled, anonymous opt-in. Until you click
  "Enable the Play Log", the app doesn't even look at the game's folders. "No
  thanks" is remembered and reversible.

- **Fixed: the Play Log could dead-end.** Clicking "Read new log entries" before
  choosing an account replaced the account choices with an error message that
  told you to pick an account — with nothing left to pick. Now the read button
  simply doesn't exist until you're watching an account (it appears the moment
  you pick one), errors always bring the choices back, and the account choices
  look like buttons ("▶ Watch filofinfain") instead of plain text.

## 0.12.6 — July 5, 2026

- **The Play Log (first cut).** A new full-width section at the bottom of the app
  reads your in-game chat logs (type `/logchat` in game once to start writing
  them) and turns them into insight — no raw log ever shown. Pick which account
  to watch (multi-account players choose their main), hit "Read new log entries"
  after a session, and get: session totals (XP, influence in/out, merits,
  defeats), progress (level-ups, badges), and your recent haul with
  keep-vs-convert/sell verdicts on every drop. Reading is incremental — only new
  lines since last time. The line formats are provisional until validated against
  real logs, and the tool says so: it reports how much it parsed and shows any
  data-looking lines it didn't recognize, so early users help perfect it.

## 0.12.5 — July 5, 2026

- **Power trays now follow the community standard** (researched from player forums):
  Tray 1 is your active rotation — openers, then the single-target chain in slots
  1-3 (the muscle-memory keys), then AoEs and cones, with the nuke pinned at the
  end. Tray 2 is mid-fight clicks — self-buffs, then heals, then endurance
  recovery grouped together at the end. Tray 3 is set-and-forget — toggles in
  switch-on order (your armors first, then pools), utility, and Rest parked last.
  Tray 4 is travel and sprints, deliberately away from the combat keys. The same
  kind of power lands in the same place on every character, so your muscle memory
  transfers between alts — the way experienced players actually set up their bars.

- **The Incarnates brick.** Your six incarnate choices (the solver's
  recommendations, or your own picks) now live in a card of their own — same
  shape as the in-game power trays and docked right above them, with the real
  in-game incarnate icons (family art + rarity ring) and the full ability name
  on hover. Slots you haven't filled show as dashed placeholders.

- **Every IO icon now shows its level.** Set pieces the optimizer slots (and ones
  you pick by hand) carry the level to buy or craft them at — the set's maximum,
  so a Cloud Senses piece reads 30, an Achilles' Heel proc 20, premium sets 50 —
  right under the icon, the same way common IOs already did.

- **Procs are named properly.** Slots the proc pass fills used to read just
  "Annihilation: proc" — they now carry the real piece name ("Annihilation:
  Chance for Res Debuff"), so you know exactly what to buy.

- **Ctrl+Z undoes your last edit.** Mis-clicked a slot? One keystroke takes it
  back — same as the ↶ Undo button (power picks, slot changes, enhancement
  swaps, pool changes). Typing in a text box keeps its normal Ctrl+Z.

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
