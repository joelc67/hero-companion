# Hero Companion — What's New

## 0.12.22 — 2026-07-20

- **This is the first digitally signed Hero Companion release.** The installer
  and app now carry a Microsoft-verified signature ("Joel Andrew Chambers"), so
  Windows shows a named publisher instead of an "unknown publisher" warning.
  Every release from here on ships signed. (SmartScreen's "not commonly
  downloaded" prompt is reputation-based and fades as downloads accrue — that
  part takes time, not more paperwork.)
- **The engine now values a Mastermind's pet buffs (model v34).** A Mastermind's
  main damage is its pets, and the buffs it casts on them — Supremacy (+25%),
  Accelerate Metabolism-class ally buffs, Temporal Selection (single-target, on
  your biggest pet), Beast Mastery's Pack Mentality (assuming 8 of 10 stacks
  with pets engaged, stated on the build) — now raise pet damage in every score
  and label. Caster-only buffs (like the Musculature Alpha) correctly do not.
  A new "Pet damage buffs" section on the offense panel shows exactly which
  buffs applied, at what strength and uptime. Stated simplification: pets are
  modeled as always hitting; pet accuracy is a named next step. Two champions
  genuinely improved under the corrected math and were re-certified (the
  Radiation/Sonic and Radiation/Radiation Defenders); every other certified
  build re-verified with its score updated. Making the search fully exploit
  the new term is the named next engineering item.
- **Every power, powerset, and epic pool now uses the game's current names.**
  The client's own files are the authority — 74 power names and 4 pool names
  that had drifted (the old "Field Mastery" is the game's "Energy Mastery",
  "Breath of Fire" is "Fiery Breath", and so on) now match what you see in
  game. A standing check keeps them matched. The suspected "phantom epic pool"
  turned out to be a real Mastermind ancillary wearing its stale name — every
  epic offered to every archetype was verified against the game's own
  eligibility rules (zero leaks; a standing check now pins that too).
- **No more silent dead pages.** If the app's local server isn't running (or a
  page action fails), the page now says so plainly with a Reload button instead
  of buttons that silently do nothing — the field report that found this also
  added an interaction test to every release so it can't ship again. Uncaught
  page errors surface the same visible banner, and older saved characters that
  a newer version can't fully read load safely with an honest note instead of
  deadening the page.
- **Imported builds with empty slots say so.** An import now flags "in
  progress" powers ("4 empty slots: Dark Consumption") so an unfinished
  character never reads as a finished plan.
- **Honest slotting labels.** "Full set" now means the set is actually
  complete. A partial set mixed with procs reads "Frankenslot"; a clean
  partial set (plus universal globals like Luck of the Gambler) reads
  "Partial set". The globals list also learned knockback protection (Karma,
  Blessing of the Zephyr), slow resistance (Winter's Gift), and the Theft of
  Essence +endurance proc.
- **The content picker's farm section is now two honest choices** — AFK Fire
  Farm (passive) and Active Fire Farm. The old generic "Fire Farm" is retired;
  saved builds that used it get a prompt to pick the one that matches how they
  play (never silently remapped).
- **Four more dead-air fixes from release-night testing.** The build button now
  names the exact field you're missing and highlights it in red instead of
  repeating gray text; the Solve button does the same when Content isn't picked,
  and honestly says "no changes" when your slotting already meets the goal. The
  biggest one: Solve's "are you sure about this role?" question was being asked
  in a hidden panel on every installed copy — Solve would silently wait forever
  for an answer you couldn't see. It now asks where you can see it. And the
  import file dialog no longer strands you on an empty page if you cancel it.
  A set's own proc piece now counts toward its "Full set" label (a 6-piece
  Javelin Volley is a full set, not a mix).
- Data currency: game-client data re-exported 2026-07-15; current through the
  game's July 7 patch.

## 0.12.21 — 2026-07-17

- **The AFK fire-farm champion's label was corrected upward — publicly owed,
  now delivered.** The game's June 23 patch made Temperature Protection's
  +MaxHP and +Regeneration enhanceable; our data snapshot predated it. With
  the data re-synced to the current client, the same shipped Spines/Fiery
  Aura build certifies at **+4x8, sustaining 42.5 HP/s** (the old label said
  +3x8). Thanks to Maelwys for the correction. A new structural check now
  diffs effect existence and enhanceability against the client so this
  class of staleness can't hide again.
- **Accolades are no longer invisible.** Below the powers and IO sets you'll
  find every build-affecting accolade from the game data, with a search box.
  Checking one moves your build's real numbers; a press-and-hold preview
  shows what all of them together would do without committing anything.
  Each row's ⓘ shows the game's own description, and 26 of 28 explain how
  to earn it (full badge chains on 20); the rest say plainly that the
  requirements aren't documented from game data yet. New level-50 builds
  assume the four standard accolades and say so right on the build — untick
  any you don't have and the totals follow. Nothing is ever applied without
  you choosing it. And it follows the game's own rule: every accolade is
  hero-side, villain-side, or neither, read straight from the game data — and
  your character is one alignment, so the other side's accolades are greyed
  out as unavailable, exactly as in game (Portal Jockey and Born In Battle are
  the same bonus, one hero, one villain). Switch sides with the alignment
  button and the panel flips and re-assumes that side's standard set. The
  accolades that aren't side-locked stack normally, and so does every distinct
  bonus.
- **The numbers now say what's in them.** A line above Build Vitals states
  exactly which assumptions are folded in (accolades applied, incarnates on
  or off), and named contribution lines appear beneath the stats they touch
  ("↳ Accolades +321 HP", "↳ Alpha (Musculature) +45.0% damage") — read from
  the engine's own ledgers, never re-guessed on the page.
- **Incarnate choices our math doesn't price yet are marked "not yet
  modeled"** in the picker instead of silently doing nothing.
- **The Unrelenting Fury regen proc is priced** in the AFK sustain ledger
  (it was invisible to the sustain math before), and the active-farm
  objective now treats survival as hard requirements rather than a score —
  damage throughput decides the picks, exactly as active farmers build.
- **Certificates state exactly what they prove.** Every certified build's
  card now says its score comes from a converged search and prints the
  canonical number, without claiming more than that.
- **Fixes from Joel's field walks:** power-card summary strips render at
  full height again (no more crushed green sliver); a failed accolade load
  now says "Couldn't load — try again" instead of silently disabling the
  feature forever; accolade checkmarks no longer leak between characters;
  and every build entry point (new character, optimize, respec) applies the
  standard-accolade preselect consistently.
- **Every power card now shows what reaches its own numbers.** Open a power's
  ⓘ and, where a global buff actually multiplies into that power's damage (an
  Alpha like Musculature, a Hybrid, both together), a named line states the
  amount folded in — and where the game's damage cap holds it below the raw
  buff, the card says the effective value, not the raw one. Every card also
  carries an honest footer: build-wide bonuses such as accolades don't change
  a single power's numbers, so they're pointed to Build Vitals rather than
  faked onto the card. Untick the incarnate preview and the line and the
  numbers drop together. All of it is read from the engine's own ledger —
  when several incarnates stack, each is named, never lumped under one.
- **Incarnates and Epics are treated by their real unlock rules.** While
  you're leveling a character, the tool now warns when you preview endgame
  content you haven't earned yet: incarnate abilities unlock at level 50, and
  Epic / Ancillary powers at level 35 (Patron pools also need their Patron
  arc completed). Nothing is blocked — you can still preview your finished
  build — but a plain note tells you these aren't available at your current
  level, and the totals say "endgame preview" instead of implying you have
  them. A level-50 build never sees the warning.
- **Iron Man's accolade tells you how to earn it, sourced from the game.**
  It's the one-million-damage badge (shown as Adamant, Iron Man, or Ironwoman
  depending on your alignment and body type); the pop-up now states that,
  confirmed against the game's own text.

## Companion Lite 0.1.18 — Unreleased (signing pending Joel's cert profile)

- **A real Windows installer.** Companion Lite now ships as a proper per-user
  install (Start Menu entry, clean uninstall, no admin prompt) instead of a
  loose exe. Under the hood it moved from a single packed file to a folder
  layout, which starts faster and stops tripping antivirus "packer" heuristics.
- **Signed with a verified publisher.** The installer and app are code-signed,
  so Windows shows "Joel Andrew Chambers" as the publisher instead of an
  "unknown publisher" warning. (SmartScreen's "not commonly downloaded" notice
  fades on its own as more people install — signing removes the scary warning
  immediately, and reputation does the rest.)
- **Auto-start is your choice.** On first run it asks, once, whether to start
  with Windows — never silently on — and you can flip it any time from the
  tray. Uninstalling removes it cleanly.

## Companion Lite 0.1.17 — 2026-07-15

- **The feed tells you the truth when it can't upload.** Errors now lead with
  the human reason ("getaddrinfo failed" means no network/DNS, "timed out",
  "connection refused") instead of a bare class name, and the tray status
  shows a visible retry line — "RETRYING, N failures since HH:MM" — so a dead
  feed is never two green icons over silence.
- **One machine, one uploader.** When the full Hero Companion app runs
  alongside Lite, exactly one of them feeds the board (a shared lock — the
  same pattern that already keeps them from double-capturing). No more racing
  the upload bookmark.
- **Your remembered "no" now covers Lite too.** Turning the feed off in the
  full app's Play Log silences Lite's uploads as well — one choice, honored
  everywhere, reversible in the same place. The tray says plainly when the
  feed is off and why.

## 0.12.20 — 2026-07-15

- **Custom build targets now survive to the finish line.** When you set your
  own numbers (the fire-farm 45% defense / 90% resistance case), no later
  optimization step may trade them away — the solver meets your ask and the
  finishing passes are held to it. (Work order A: the proc pass was breaking
  a target-serving set after the solve had already met the number.)
- **Repeated Optimize presses are stable and honest.** The same button now
  gives the same build from the first press, and when your imported
  character owns fewer slots than the level-50 plan places, the result says
  so plainly instead of silently showing slots you don't have yet. (The
  reported "slot inflation" was measured everywhere and never existed —
  slot conservation is now a standing audit anyway.)
- **No impossible defense numbers.** Where a total includes out-of-combat
  stealth defense (Hide's big AoE layer), the fight value prints right
  beside it — "90% ⚔ 30% in combat" — with the explanation on hover.
- **High-cap archetypes get their real resistance ceiling.** Tanker and
  Brute resistance targets were quietly clamped to 75% in some solve paths
  (their real cap is 90%); Kheldians and Arachnos soldiers were clamped
  under their 85%. Every target now uses your archetype's actual cap.
- **The public Pulse board is honest about BOTH kinds of quiet.** The page
  now shows "Data through <time>" always, warns "no new game data since
  <time>" when the feed goes quiet, and separately warns when the render
  pipeline itself stops. (Field lesson: a healthy renderer over a dead feed
  kept re-stamping the page "fresh" while the numbers froze for 19 hours.)

- **Peacebringers and Warshades: pick your form, get its champion.** The
  level-50 wizard asks Kheldians one more question — Human, Dwarf, Nova,
  or all three (tri-form) — and serves that form's own certified champion
  build as the base to build under. Each form champion is a committed build
  for the way you actually play, honestly labeled: form-swapping play isn't
  modeled yet, so each certificate covers exactly what it names. Other
  archetypes never see the question.
- **The Kheldian champions are here — and the whole roster passed a harder
  legality bar to ship.** Eight new certified builds (Peacebringer and
  Warshade, all four forms each), plus re-converged Night Widow and
  Water/Kinetics Corruptor. Every champion now has to be BUILDABLE from
  level 1 exactly as picked — the game grants your third power pick at
  level 2, and builds with nothing legal to take there are refused. That
  gate caught and rebuilt several champions, including two that shipped in
  0.12.19. Twenty-four certified reference builds ship in this release.
- **A certified AFK fire-farm champion (Spines/Fiery Aura Brute) — with an
  honest difficulty label.** Two new Content choices in the wizard: AFK
  Fire Farm (passive — the build must hold 45% Fire defense, capped Fire
  resistance, and out-heal the spawn while you're away from the keyboard)
  and Active Fire Farm (you're at the wheel; the build spends its budget on
  damage). The AFK champion's certificate states exactly what it sustains:
  certified at +3x8 — the +4x8 asteroid worst case is out of reach for this
  combo, and the label says so with the numbers instead of hoping you won't
  notice. (An interruptible heal can never count toward AFK sustain — the
  game cancels the cast when you're hit, so the math refuses it too.)
- **Damage procs in auras and patch powers now count.** Procs slotted in a
  damage aura (Blazing Aura, Quills) or a ground patch's summoning power
  (Irradiated Ground) were priced at zero since launch; they now earn their
  keep on the pulse rate the game client's own records state. The active
  fire-farm champion is deliberately NOT in this release: our own field
  measurements say these procs may be worth even more than the formula
  gives, and that champion waits until the numbers are settled rather than
  shipping a build we'd have to walk back.
- **Reset means reset — every start-over path.** The upper-right ↺ and every
  "start over" entry point now genuinely clear every answer, preset, and
  leftover; the wizard opens blank. (Found in the field: one path kept old
  answers alive.)
- **Nobody ever needs Ctrl+F5 again.** Every release and dev restart reaches
  your browser on a plain reload — fixes can't hide behind a stale cache.
- **Power cards read like power cards.** The full power name owns the top
  line (no more "Radioac…"), and the ⓘ details button is always visible
  instead of appearing only when you hover over where it would be.
- **Clicking Build never looks like nothing happened.** A large "Your build
  is ready" button leads the result and scrolls into view — and while a
  build is still baking, a live seconds counter now ticks instead of
  silence. Most combinations solve in about a second; some are genuinely
  hard math, and after a few seconds the counter says plainly that it's
  still working, not stuck. No fake progress bars — the old "(~1s)" promise
  is gone because it wasn't always true.
- **The header finally shows a version you care about.** It leads with the
  app version; click it for a plain-language About — what the app is, what
  a "build model" version means, where the game data comes from, how many
  certified reference builds you're running with, and the links that matter
  (forum thread, releases, Pulse Boards, credits).

## 0.12.19 — 2026-07-13

- **Eight new champion builds — nearly every archetype now has a certified
  anchor.** Brute (Battle Axe/Fiery Aura), Tanker (Invulnerability/Super
  Strength), Scrapper (Broad Sword/Super Reflexes), Stalker (Radiation
  Melee/Dark Armor), Sentinel (Fire Blast/Willpower), Blaster (Fire
  Blast/Energy Manipulation), Dominator (Mind Control/Fiery Assault), and
  Arachnos Soldier (Crab Spider) join the five existing champions — thirteen
  converged, certified level-50 builds served automatically when you pick
  those combinations. Peacebringer, Warshade, Night Widow, and one Corruptor
  combo arrive later this week (the Kheldians with their full form set).

- **Everything Companion Lite does, the full app now does too.** The Play Log
  tab gains the Pulse Boards: "My private board" builds your personal board
  (scorecards, market ledger, raids seen) from your own capture store, right
  in the app — local data, never uploaded. "What sharing shows" previews the
  sanitized public variant, so the choice to share is an informed one. And
  the live-board feed itself: an explicit, reversible opt-in behind the full
  terms (shown in the app before anything ever uploads), with the same
  privacy guarantees as Lite — account names replaced with meaningless codes
  before upload, private messages never captured, no machine details ever.
  Capture itself was always shared between the two apps; if you run Lite
  alongside, they coordinate exactly as before.

- **"Mixed role / Generalist" now appears everywhere a role is asked.** It was
  always in the main Role dropdowns, but the "Start a new character" discovery
  flow ("I want to…") never offered it — now "do a bit of everything
  (generalist)" is a first-class answer there, with its own archetype
  recommendations (the sets-span-roles picks, Kheldians included). Also fixed
  on the way: choosing "control / lock down" or "command pets" in discovery
  used to silently blank the wizard's Role question while marking it answered —
  control now carries over as Controller/Lockdown, and pets honestly leaves
  Role for you to pick (commanding pets is an archetype, not a role).

## 0.12.18 — 2026-07-10

- **Your core armor toggles are enhanced like they deserve (model v30).** The
  optimizer used to treat a met survival target as "done" — past that point,
  enhancing your strongest shields was worth literally nothing to it, so
  powers like Fire Shield or Temp Invulnerability could end up as two-slot
  parking spots for global IOs while a free minor power got a full set.
  That threshold is gone: survival keeps its real, continuously-measured
  value all the way to your archetype's caps, so the strongest armor powers
  get their resistance and defense aspects enhanced first — with endurance
  reduction riding along — and the weaker or free powers take the mule duty.
  Global IOs now also prefer the cheapest hosts, so an expensive toggle
  like Weave keeps its slots for real enhancement. (Thanks to Maelwys for
  the precise field report that pinned this down.)
- **Ten set-bonus families the planner literally could not see now count
  (model v30):** knockback protection, slow resistance, all six mez-duration
  bonuses (confuse, hold, stun, sleep, immobilize, fear), movement speed,
  range, and endurance discount — 103 bonus tiers back-filled straight from
  the game client's own data, verified value-for-value. They appear in your
  totals and on every enhancement card (the "not yet in totals" note is
  gone), and the optimizer's scoring now values knockback protection, slow
  resistance, and your controls' longer mez durations. The three stackable
  −knockback IOs (Karma, Steadfast Protection, Blessing of the Zephyr) are
  priced too — mag 4 each, exactly as the game grants them.
- **Preview toggles now stack — every combination the game allows.** The
  one-preview-at-a-time rule blocked real play: Build Up + Aim is the classic
  opener, Farsight + Group Invisibility + Power Boost is how a Time build
  checks its soft cap, Meltdown + Shadow Meld is a genuine defensive layer.
  All of it now stacks freely. Honesty replaced restriction: short strike
  windows (Build Up class) wear their own 💥 chip, and while any are checked
  the totals panel says loudly that you're looking at a BURST VIEW — a window
  of seconds, not what the build sustains. Cycling buffs (Hasten, Farsight
  class) keep the ⟳ chip with their real uptime at your build's recharge —
  and a short-window power your recharge makes effectively permanent (Parry
  spam) earns the cycle label its math deserves. Also fixed: unchecking
  behavior could leave a chip LOOKING checked while its power no longer
  counted — chips now always repaint with their true state.

## 0.12.17 — 2026-07-10

- **The "count in totals" checkbox now matches what the game actually allows.**
  It used to be one uniform Σ checkbox on every power — which lied for most of
  them. Now there are three honest states, each with its own color and glyph
  (never color alone): always-on powers (autos, passives, inherents) show a
  locked 🔒 badge with no control at all, since the game gives them no
  off-switch; toggles keep a checkbox (⏻, green, default ON) as their real
  home — uncheck a mule host or run a quick "what if Weave were off"; timed
  self-buff clicks (Hasten, Build Up, and their kind) get a preview toggle
  (⟳, orange, default OFF) that previews one window at a time, since the game
  only ever has one of these running as a meaningful "on" state — checking one
  switches any other preview off. Plain attacks get no chip at all. Also: the
  endurance-sustainability warning now respects your checkbox choices (an
  unchecked toggle no longer counts against your endurance), and it actually
  shows up in the totals panel when your checked toggles + attack chain would
  run you dry.

- **Customize the targets the solver chases.** "Customize build targets…"
  (on the play-style summary and next to the Content/Role pickers) opens an
  editor seeded from your chosen preset: typed AND positional defense,
  per-type resistance, recharge, recovery, regeneration, and max HP. Set a
  number to chase it, clear it to drop it — a resistance-primary set like
  Fiery Aura can finally chase 90% S/L/F resistance plus recharge and HP
  instead of being held to defense-shaped preset thresholds. Values clamp to
  game reality (your archetype's own resistance cap); when the ask exceeds
  what 67 slots can buy, the solve gets as close as it can and says so.
  Custom targets persist with the save, and you can keep them as named
  presets of your own to reuse on any build. Honest labeling throughout: a
  custom-target build is YOURS — it never reads as a certified champion
  build. Also fixed on the way: resuming a saved character now restores its
  Content/Role picks into the dropdowns (they used to come back empty, so a
  re-solve could silently run against different targets).

- **The same set piece can no longer be slotted twice in one power.** The
  game doesn't allow it, and now neither does the picker: pieces already in
  the power show "✔ slotted here" and can't be picked again. If a build
  arrives with duplicates anyway, validation flags it as a real error, the
  duplicate no longer conjures set-bonus tiers (tiers count distinct
  pieces, so the card's "N of 6" and your totals always agree), and
  stackable globals like Luck of the Gambler +recharge now respect the
  game's rule of five — a sixth copy grants nothing, exactly like in-game.
  Identical Hamidon/Titan/Hydra Origins and D-Syncs still stack freely (the
  game's actual rule).

- **Preview Enhancement Boosters before you buy them.** Every boostable
  enhancement's detail card now carries a booster stepper: walk it from +1 to
  +5 one level at a time and watch your real totals move — "+3 reaches the
  soft cap, +4 and +5 buy nothing here" is now something you can see instead
  of guess. Previewed pieces show their level exactly like imports do
  ("50+3") but in a distinct preview color, and the totals panel says plainly
  that previews are not saved as owned. Pieces that can't boost say why:
  attuned enhancements (including ATOs and Winter sets) scale with your level
  instead and keep exemplaring down, and Hamidon/Titan/Hydra Origins and
  D-Syncs get their strength from their own level. The card also explains
  where boosters come from and the exemplar trade-off in plain English.

- **Power Boost previews for real.** Powers that amplify your other buffs
  (Power Boost, Power Build Up) now have their own preview chip (⚡): switch
  one on and your buffable defense and ToHit values amplify exactly the way
  the game does it — effects the game marks "Ignores Buffs" are skipped,
  verified per-effect against the game's own data. Combine it with one buff
  preview (Power Boost + Farsight) to answer the real question: does this
  build actually hit the soft cap in its burst window? The totals panel
  labels the result as a burst view, never sustained. (Clarion Radial isn't
  modeled yet — its incarnate data doesn't carry a verifiable amplifier
  record; the tool says so rather than guessing.)

- **Running toggles are no longer called "mules."** A toggle or always-on
  power that hosts global uniques (Fire Shield with a Steadfast, Weave with a
  Luck of the Gambler) now reads "Global host — this toggle runs; its slots
  carry build-wide bonuses" instead of "Global mules," which implied the
  power was dead weight. True set-real-estate powers keep honest mule
  wording.

- **The detail card grew into a real rail.** The right-side panel now scrolls
  on its own (a long six-piece card browses in place while your build stays on
  screen), every slotted enhancement carries its own ⓘ — hover the chit — so
  the full detail card is one click away without entering the change-picker,
  and both rail views are LIVE: slot a new piece of the displayed set and the
  roster chips and lit bonus tiers update in place, no reopening. The power
  info panel now shows the full merchant-style set view too: one set in a
  power renders its card inline; a mixed-set power gets one compact row per
  set ("Shield Breaker 1/6 — next: +2.5% recovery") that expands to the full
  card. Set-bonus tiers also read cleaner — repeated per-type values collapse
  to one line, and bonuses the game grants but the totals can't count yet
  (slow resist, movement, range, mez duration) say so honestly instead of
  showing a bare name.

- **The true in-game enhancement experience.** Click a slotted enhancement and
  open its full detail card: the game's own description text with honest
  numbers at YOUR piece's level and boost state ("Enhances the defense debuff
  potential of a power by 17.4%…"), the attuned and unique rules, and the
  complete parent set — every piece marked slotted-here / elsewhere / missing,
  and every set-bonus tier lit as you attain it, with "← next piece" showing
  exactly what one more piece buys. All text extracted from the game client
  itself (227 sets, every piece and tier), not paraphrased. The picker now
  shows what's currently slotted with a "Full details" button, and power cards
  reveal a ⓘ hint so the info panels are discoverable.

## 0.12.16 — 2026-07-09

- **Every "How do you play?" question explains itself the moment you answer
  it.** The Role and "You fight from" pop-ups were silent on the first pass
  through the wizard (they come before "Mostly in", and the explainers waited
  for that answer). Now each question pops its tailored explanation as soon as
  YOU answer it, on every surface that asks — Start New, Respec 50, and Change
  how you started — while the combined summary still waits until your Role and
  Content are actually chosen. Also: the import screen now says plainly that
  in-game /build_save_file exports carry no boost levels — import a Mids .mbd
  to bring +1..+5 and HO levels across.

- **Henchmen inherit your set bonuses — and the optimizer knows.** The game
  gives Mastermind henchmen half of your true set bonuses (verified straight
  from the game client): +Max HP arrives as a flat amount from the
  Mastermind's own hit points, identical for every henchman, so your squishy
  tier-1s gain the most staying power — exactly the effect the forum
  discussion described. Builds are now scored with each henchman's real
  survival in the fight (tier hit points from the game's own tables, deaths
  cost the actual resummon and re-upgrade cast times), so +HP, defense and
  resistance bonuses carry honest extra value on a Mastermind. Globals like
  Unbreakable Guard and accolade HP do NOT reach henchmen (also the game's
  rule), and the planner never credits them there.
- **Heal-strength set bonuses exist now.** The game's 11 heal-strength bonuses
  (Numina's 4-piece +6% heal, Doctored Wounds +4%, Panacea's 6-piece +6%…) had
  parsed to nothing — same story as the accuracy bonuses fixed in 0.12.15. All
  11 are restored from the game client, the totals panel shows your +% Heal
  strength, and the optimizer values what they do to your actual healing
  output.

- **Slot anything by hand.** The enhancement picker now offers the single
  enhancements a power accepts alongside its sets: common crafted IOs, Hamidon
  / Titan / Hydra Origins, and D-Syncs. Identical copies stack freely (that's
  the game's rule for these), totals price them exactly, and they round-trip
  through Mids export/import.
- **In-combat view (suppression).** A new Stats toggle shows your totals as
  they are mid-fight: powers like Stealth lose their suppressible defense the
  moment you attack or get hit, exactly per each effect's own suppression
  flags — same as Mids' Options > Effects and Maths > Suppression. Display
  only: builds are optimized on the same numbers either way.
- **Real enhancement levels from imports.** Boosted IOs (50+5) and level-53
  Hamidon Origins now import with their true levels, show as "50+5" / "53" on
  the slot, and count in the totals at the game's real math (+5% per boost
  level; a 53 HO is worth 38.3%, not 33.3%). Fixed a one-off: Mids stores
  levels 0-based, so every imported IO used to read one level low. Exports to
  Mids now carry boosters back too.
- **Cards say where the −res job went.** A base-slotted power that carries its
  own −resistance debuff (Melt Armor and friends) now names the power actually
  holding the −res procs and why it won the job, instead of a vague "budget
  went elsewhere."
- **No more duplicate epic pools.** Three pools leaked into the wrong
  archetypes' dropdowns by stale upstream data (Stalkers and Dominators each
  saw two same-named "Mastery" pools). The game client's own eligibility rules
  say who gets what; the extra entries are gone.

## 0.12.15 — 2026-07-08

- **Fresh gold-standard champions, certified on verified game data.** All five
  champion builds were re-converged from scratch under this release's corrected
  model and data — every value they stand on now checks against the game client
  itself. Old champion scores looked bigger; these are the honest numbers.
- **The wizard never chooses for you.** All four "How do you play?" questions
  start unanswered and the Build button waits until you've answered them — the
  planner never invents your playstyle. Each answer is tagged with where it came
  from ("your pick" / "from your setup"), and reopening the wizard restores what
  you chose — including your travel power. Travel is never auto-picked: endgame
  content entry can require specific travel (BAF and Lambda admit only Flight or
  Teleport), so that call is always yours.
- **New Role option: Mixed role / Generalist.** The honest choice when you don't
  specialize — balanced targets for your content, judged by overall contribution
  instead of one role's lens. Its pop-up explains the trade plainly.
- **Slotting notes are easier to find and use.** The whole note chip on a power
  card is now the button (hover for the bonus summary, click for the reasoning),
  with a one-time hint on your first build. Power-card tooltips lead with the
  full power name, so truncated names are readable. The − / + slot buttons
  explain the shared 67-slot pool, and the slot counter tells you when you have
  free slots to spend. The power-info panel closes on Esc or a click outside.
- **Global Accuracy set bonuses now exist — and are valued.** A parser gap had
  dropped every global-accuracy set bonus in the game (Luck of the Gambler's
  4-piece +9%, Adjusted Targeting, the archetype sets' +15%…) — 65 bonuses,
  invisible to the totals and the optimizer alike. All 65 are restored straight
  from the game client's own data, the totals panel shows your +% Accuracy, and
  the optimizer now prices accuracy by the game's to-hit math: against +3/+4
  enemies (iTrials, hard content) accuracy multiplies your real damage until you
  reach the 95% hit ceiling, so builds for that content chase it — and builds for
  even-level content don't waste slots on it. The data reality-check now verifies
  282 set-bonus values against the live game (a name-matching bug had silently
  limited it to 43), all matching.
- **The "How do you play?" questions now explain themselves.** Every choice in the
  build wizard pops a detailed explanation written for YOUR character — a
  Mastermind's "Damage dealer" talks about henchmen and pet sets, a Super Reflexes
  scrapper's iTrial preset explains why it chases positional instead of typed
  defense. A new summary panel shows exactly what your combined answers make the
  planner chase (the real defense, resistance, and recharge targets), so nothing
  about the build's direction is a mystery before you hit Build.
- **Credits: Maelwys.** His expert reviews on the Homecoming forums caught what our
  own tests missed, round after round. Added to the in-app credits and CREDITS.md.

- **Common IO icons are back.** 0.12.13 accidentally dropped every common IO's icon,
  so a generated build's Accuracy/Damage/Endurance IOs rendered as empty-looking
  slots next to expensive globals. The same defect gave Hamidon Origins a level they
  don't have, which scaled imported low-level HOs toward zero. Both fixed, and the
  audit now fails hard if any slotted piece ever ships icon-less again.
- **Hamidon Origins stack legally.** The validator warned "duplicate piece slotted
  2x" on double-Nucleolus cores. HOs, Titan/Hydra Origins, and D-Syncs are not set
  pieces — the game lets you slot as many identical copies as you like, and the
  planner now agrees.
- **Real attacks reach 6 slots.** The optimizer always wanted six, but a budget
  accounting gap plus an order-blind trim kept every real attack at exactly five
  while filler powers kept six. Attacks now get their sixth slot; any trimming falls
  on junk fills and filler powers first, never the rotation.
- **Proc bombs carry accuracy.** Big proc bombs reserve a slot for a Nucleolus
  Exposure (Accuracy/Damage, recharge-free so every proc keeps its full chance) —
  and bombs no longer shrink a 6-slot power down to the proc count.
- **No more orphaned set pieces.** The −res anchor, Force Feedback seating, and the
  endurance-relief pass all refuse swaps that would strand a lone set piece with no
  bonus, eat a global, or overwrite a proc. Force Feedback now lands in a spammed
  knockback attack's spare slot instead of cannibalizing a proc bomb.
- **Signature support buffs always work.** A damage-role Mastermind's Barrier Reef
  shipped as a bare 1-slot mule; signature buff clicks from a support set now always
  carry a working set, whatever role the build solves for.
- **Max HP totals are honest.** A /Regen build displayed "+58913% Max HP" (flat
  hit points summed as a percent). Totals now show the real number — "+79.9% =
  2410 HP (capped; 3286 uncapped)" — plus regeneration in HP/sec and recovery in
  end/sec, the way the game reports them.
- **+HP set bonuses were 10x too big.** Verified against the game client's own
  set-bonus powers: a "Large Increased Health Bonus" is ~1.88% of base HP, not
  18.75%. Every +HP set bonus was inflated tenfold in the totals and in the
  optimizer's HP math. Two Touch of the Nictus pieces now read +1.87%, a third
  Luck of the Gambler +1.12% — matching the live game exactly.
- **Card notes now describe the actual decision.** Slotting chips say "5 of 6 Red
  Fortune — earns +5% recharge, +1.5% fire resistance" instead of a vague "full
  set for its bonuses"; a couple of procs is labeled "Procs", not "Proc bomb";
  and Hamidon-Origin proc hybrids get their own "Proc hybrid" note explaining
  the pattern (these cards previously showed nothing and could wrongly trigger
  the respec nag — that misfire is gone).

## 0.12.14 — July 7, 2026

- **Synced with the game's July 7 update (Issue 28, Page 3).** The patch normalized
  Dark Armor's Obscure Sustenance to a 60 second recharge for every archetype; our
  data carried the old 180 seconds for Brute, Scrapper, Stalker, and Tanker. A full
  diff of all 10,708 powers against the patched client confirmed these four values
  were the patch's only data change — archetype tables, pet classes, and proc rates
  all verified unchanged.

## 0.12.13 — July 7, 2026

- **−Resistance procs for every role that can carry them.** Achilles' Heel,
  Annihilation, and Fury of the Gladiator multiply the whole spawn's incoming damage —
  and a damage role owns the biggest share of that damage. The optimizer now hunts a
  home for each −res proc in every build (debuff toggles first, then the biggest
  eligible power), not just on debuffers and controllers. Annihilation's proc rate was
  also corrected against the game's own data.

- **Force Feedback: Chance for +Recharge finally counts.** The famous knockback proc is
  seated in your spammiest knockback attack and honestly valued: the average recharge
  it sustains (chance per cast × 5 seconds ÷ how often you actually fire) flows into
  everything recharge touches — attack chains, Hasten uptime, debuff cycling, pet
  resummons. The build totals show exactly how much of your recharge it carries.

- **Hamidon Origin enhancements modeled.** All 62 special enhancements are now priced
  correctly when slotted, and the optimizer uses the master pattern: a proc-hybrid
  attack's filler core trades up to two Nucleolus Exposures (about 66% accuracy and
  66% damage in two slots, with no recharge to depress the proc rates). Premium set
  cores are left intact — those bonuses are build-defining.

- **Champion builds re-converged** under the corrected model and shipping in this
  update, plus a fix to pet resummon timing that slightly undercredited global
  recharge on timed summons.

## 0.12.12 — July 7, 2026

- **Henchmen and pets priced like the live game (the big Mastermind fix).** Pet damage
  was built on a stale snapshot that rated henchmen more than twice as hard-hitting as
  the real game, counted a single pet where the game spawns a squad, and treated every
  summon as permanent. All three are fixed from the game's own data: henchman damage
  now uses the live tables, Soldiers count as 2 Soldiers + 1 Medic (tier squads of
  3/2/1 across all six Mastermind primaries), timed summons like Spiderlings earn only
  the share of a fight they're actually up (recharge slotting shortens the resummon
  wait), and powers whose pets don't inherit slotting no longer get phantom
  enhancement. The optimizer values pets on the squad's real, uptime-weighted output —
  the "healing mule" Mastermind builds die here.

- **Champion builds re-converged under the corrected model.** Every gold-standard
  champion was re-solved to full convergence with the accurate pet math and ships in
  this update.

- **Live play capture improvements** (shared with Companion Lite): the server pulse
  counts formations rather than repeated recruiting shouts, Positron Parts 1 and 2
  are distinguished in every spelling, your characters' servers are detected
  automatically from the game's roster file, and the recruitment-channel list ships
  in the updatable content pack.

- **Your server shows on the board — detected automatically.** The game itself keeps a
  roster file (playerslot.txt) naming each character's server; Lite looks your
  characters up there the moment they appear in the log, so the live board's "Servers
  reporting" line fills in with zero configuration. Only the characters actually seen
  in your logs are recorded — the roster itself is never stored or uploaded.

- **Positron Parts 1 and 2 finally count separately.** Recruiting-alias matching is
  now longest-first, so "posi 2" no longer collapses into generic Positron — in every
  spelling recruiters use (posi2, pos 1, 1st posi, ...). The same fix protects every
  multi-word alias (ice mistral, mort kal, kmitf).

- **The recruitment-channel list ships in the content pack**, so shard global channels
  (where iTrials and raids organize) can be added as data. Private channels (tells,
  whispers) remain excluded unconditionally.

## Companion Lite 0.1.13 — July 7, 2026

- **Companion Lite now feeds the live Pulse Boards directly.** No accounts, no tokens,
  no setup, no publish button: while it runs, captured play uploads over HTTPS to the
  project's locked storage and the board pipeline imports it into the live page within
  minutes. Uploads are incremental (only new play), tagged by an anonymous install
  id — account login names are replaced with meaningless codes before anything leaves
  the machine, and machine names or paths are never read at all. The only thing that
  ever becomes public is the rendered board itself.

- **The terms are the consent.** First start shows the terms (also under About):
  using Companion Lite means you accept that your captured play feeds the live board.
  If you don't accept, quit and uninstall. Turning game logging off (/logchat) stops
  capture any time.

- **A simpler tray.** Open the live Pulse Board, the in-game logging setup, Status,
  About (terms), Check for updates, Quit. The local board page and every publish or
  connect control are gone — Lite captures and feeds, the live board is the board.

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
