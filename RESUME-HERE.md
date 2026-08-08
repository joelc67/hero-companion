# Resume point - 2026-08-08 (later), the families are classified

## STATE
HEAD pushed, tracked tree clean. Nothing running, nothing scheduled. Data
**2026.1.1242**. Models now **v39 · v40 · v41**, none re-certified.

## WHAT THIS PASS DID
The coverage check hard-failed on 104 families. **Residue is now ZERO**, and the
largest family in the client export was a real bug.

- **v41: DEFENCE DEBUFF RESISTANCE, 178 powers** (`39cd0872`, `7e9c1fdf`). The
  game says it in its own words - Agile prints "Res(DeBuff DEF)". The scorer has
  applied incoming -def pressure since v10 under the comment "a squishy has ZERO
  defense-debuff resistance", and that was true of every build it could see
  because DDR is power-granted only. Super Reflexes took a Blaster's haircut.
  **Needed nothing from you** - the pressure term already existed. Measured:
  Agile 6.92%, five SR powers 48.44%, Tough Hide 25%, Elude 6.23% (duty-cycled,
  180s on a 1000s recharge), negative control 0.0.
- **Every other family classified** (`37cbade5`): 269 template instances
  source-excluded (Alpha/Genesis boost DEFINITIONS are enhancement records, not
  powers; pet records), 42 dispositioned with the ruling behind each, **20 real
  gaps PINNED by power count** so they can neither go quiet nor hard-fail
  forever. The pin fails BOTH ways - grown means a new defect, shrunk means a
  stale entry.

## RE-CERT SCOPE, counted from the artifact
v39 **13** · v40 **8** · v41 **9** → **UNION 17 of 24**. (The 13 and 8 reproduce
the earlier handoff exactly, which is what makes the 9 trustworthy.) One wave
over the union, and only after the queue below is settled.

## OPEN - JOEL'S
1. **`mez_in`** - unchanged, and it now blocks FOUR more families: ToHit-debuff
   resistance (13 powers), endurance-drain resistance (8), regen-debuff (7),
   recovery-debuff (3). All real, all the same shape as DDR, all inert because
   **nothing applies that pressure in any scenario**. One scenario number each,
   or one ruling covering the class.
2. **Fury** - a Brute farm log with 3+ single-target attacks.

## OPEN - MINE, IN ORDER (the check now names all of these)
3. **877 powers hold ZERO effect rows while the client populates them.** Gamma
   Boost prints "Auto: Self +Regen, +Recovery, Special" and carries NOTHING; so
   do Master Brawler, Active Defense, Smoke Flash, every Taunt, the Staff
   Fighting Forms. This is the next real piece, and it is a class, not a family.
4. **Absorb is not modelled anywhere** (no engine branch) - Particle Shielding
   and Master Brawler are invisible. A term is owed.
5. **Three data-only fixes on axes that already exist:** +Accuracy on Terra
   Firma and Combat Training: Offensive, Field Medic's +Heal strength.
6. **Power Boost `Set_Mode`** (143 powers; the v39 mode machinery exists).
7. The 8 gated-only powers · ~460 unclassified cap/radius rows · knockback
   protection (now visibly the same class as DDR and slow resist).

## TRAPS ADDED THIS PASS
- **Translate the VOCABULARY, not just the case.** Ours says `AoE` and
  `Negative` where the client says `Area` and `Negative_Energy`; Cloaking Device
  carries all eleven defence vectors and still reported two missing. The
  121-phantom-debuffs lesson in a second coat.
- **A champion's picks live at `champion["picks"]`,** not `["build"]["powers"]`.
  My first exposure count read 0 of 24 for a 178-power family. Counting v39 and
  v40 with the same probe and reproducing the known 13 and 8 is what proved it.
- **`/build/calculate` wants `Class_Scrapper` and `slots: [None]`.** With the
  wrong payload shape every number reads 0.0, including the ones that work.
  Read a known-good axis in the same probe or you cannot tell whose bug it is.
- **A second family carrying v39's `mode` flag exposed a latent dedup bug** -
  the key was (scale, duration, stack) with no effect name. Fixed at the key.

# Resume point - 2026-08-08 (Saturday), the game-knowledge audit

## STATE
HEAD pushed, tracked tree clean. **v0.12.35 released** (stamp `d76c043`, signed,
both assets, installed copy mirrored). Nothing running, nothing scheduled.
Data **2026.1.1242**; client bins are the **July 7 build, which IS the newest
Homecoming patch** - the snapshot is live, not stale.
Models bumped today: **v39** (self +Damage at honest duty cycle) and **v40**
(power-granted slow resistance). Neither has been re-certified yet.

## WHAT TODAY WAS
Joel: "after 30+ releases we keep finding bugs related to in-game based
knowledge. Review EVERYTHING." Root cause found and it is not carelessness:
`reality_check_effect_structure.py` states in its own docstring that its scope is
*deliberately* five survival families and NOT damage/control templates. Every gap
of this class has therefore been found reactively from a field report - accuracy
v28, heal-strength v29, +MaxEnd v35, and today's four.

## SHIPPED (0.12.34 / 0.12.35)
epic swap dropping picks | leveling chart hiding open seats | an apostrophe that
broke 40 enhancement sets **since the first commit** | the export pointer.

## COMMITTED, NOT RELEASED
3 target-cap/radius drifts | self +Damage **275 powers** | slow resistance **126**
| mez protection + resistance **229** | Granite Armor **-30%** and Bio Armor
Defensive Adaptation **-25%** (never modelled) | v39 + v40 | mez availability term
(built, proven, inert) | `reality_check_effect_coverage.py` | 3 sabotage-proven
batteries.

## OPEN - JOEL'S, AND BOTH BLOCK THE RE-CERT
1. **`mez_in`** - how often content mezzes you. In NO bin; 43 MB of logs carry 14
   mez-shaped lines. Cannot be extracted or measured. The mez term multiplies by
   1.0 until it is set (kb_in precedent, PROVISIONAL). Because the design is
   protection-dominant it ONLY governs unprotected builds.
2. **Fury** - needs a Brute farm log whose rotation has 3+ single-target attacks.
   Two clean attacks cannot separate a multiplier from a flat term.

## OPEN - MINE, IN ORDER
3. **104 undispositioned families** in the widened check (hard-fails on them).
   `Melee_Ones` was 1 table of 45 and hid ONE real defect in 4,306 instances.
   Do the rest biggest first, each family fixed or dispositioned with evidence.
4. **Power Boost `Set_Mode`** (143 powers; the v39 mode machinery now exists).
5. **The 8 gated-only powers** (Hardened Carapace, Cosmic Balance, Dark
   Sustenance) - conditional, need the same scenario input mez does.
6. **~460 unclassified cap/radius rows.**
7. **Knockback protection** - pre-existing, filed as a "stated understatement",
   now visibly the SAME CLASS as slow resist and mez. Worth reopening.

## RE-CERT SCOPE when it is finally run
13 contexts for the v39 damage term, 8 for v40 slow resist. NOT 24. Run one wave
over the union AFTER 3 is done, or a family found later forces a re-run.

## TRAPS LEARNED TODAY - these cost real time, do not re-pay
- **A value the engine computes but never SURFACES cannot be verified.**
  `calculate_build` returns a curated 20-key response; `slow_resist` lives at
  `bonus_extras.slow_resist.value`. Probing the top level returns None however
  well the code works - this made me REVERT A CORRECT BRANCH, and the battery had
  the same bad probe baked in, passing 12/12 while blessing anything.
- **Raw scale is not resolved magnitude.** I quoted mez protection as "30" all
  session; through `Melee_Res_Boolean` it is **10.4** (Unyielding's real value),
  20.8 stacked. Coverage 98.4%, not 98.9%.
- **Compare modifier tables CASE-INSENSITIVELY** - ours `Ranged_DeBuff_ToHit`,
  client `Ranged_Debuff_ToHit`. One capital B invented 121 phantom missing debuffs.
- **Ask whether we carry the ATTRIB under any name before calling it absent.**
- **ASPECT is part of the identity** - self RechargeTime is slow RESISTANCE at
  aspect=Resistance and a recharge BUFF at aspect=Strength. 78 records would have
  been corrupted.
- **Zero-scale templates carry no magnitude** - every Blaster blast has one
  (Defiance is derived from cast time), and counting them made 13 champion
  contexts look exposed and stalled a re-cert over a double-count that could
  never fire.
- **Anything an inherent term already DERIVES stays out of the data** (Vigilance,
  Defiance) or it is counted twice.
- ⚠ **I wrote CRLF files as LF again** (`newline=''` on a text write): 3,147
  insertions on a 92-line change. The whitespace-blind `git diff --stat` caught it.

## THE PATTERN WORTH KEEPING
Eight of my own numbers needed correcting today and EVERY ONE was caught by a
check, never by re-reading. Measure before claiming; a probe that looks reasonable
can be wrong in the same way the code is.

# Resume point — 2026-08-07 (new session starts here)

## ✅ CLEAN START. Nothing is running, nothing is owed to a half-finished task.

**v0.12.33 "Knowing what to do next" is RELEASED and ANNOUNCED.**
Build stamp `898653a`, signed, API-verified, both assets. Installed copy mirrored
and relaunched (its header reads 0.12.33). Joel posted the announcement to topic
64761 himself on 2026-08-07. Tree clean and pushed. No scheduled tasks, no
monitors, no dev server, no wave.

Data **2026.1.1242** and model **v38** unchanged, so no certified score has moved
and **no re-cert is owed**.

### ⚠ Three things the post created, all recorded in CLAUDE.md
1. **Nothing public has ever announced that the app stopped being a browser
   tab.** The 0.12.31 and 0.12.32 drafts were never posted, and Joel cut the
   catch-up paragraph ("I never posted about 0.12.31"). If a field report reads
   as "why does this not open in my browser", that is why. Not a bug.
2. **A public correction was made** (the update check runs on launch, not only
   when clicked). That stale-reply watch item is CLOSED.
3. **The post says `/thumbtack` is untested in game.** If anyone confirms the
   marker lands, that is the trigger to strengthen the claim.

### ▶ MINE, unblocked, in the order I would take them
- **Fury meter + Power Boost as ONE piece.** Blocked on data, not on design: it
  needs a THIRD clean single-target attack from a Brute farm log. Only two
  isolate today, and two points cannot separate a multiplier from a flat term.
  ⚠ AoEs can never be reconstructed from this log format.
- **Leveling Companion batch** (shares the Journey surface).
- **pricing #31** (single-claim pairing).
- **strict-dominance solver experiment** (optional).
- Cheap and worthwhile: the **budget/balanced/premium dial** is vestigial and
  Joel wants it to be a real player choice again (his R3 answer, its own item).

### ▶ JOEL'S
- **FP / whitelist submissions** for the 0.12.33 signed artifacts, per
  `docs/signing-runbook.md`. ⚠ Bitdefender often kills the app on release nights.
- **github.com/settings/billing** — the inbox workflows still cannot get a
  runner; both stay `disabled_manually`. Billing needs a gh scope deliberately
  not granted, so this cannot be chased from here.
- **The Iron Man / Adamant badge**: does it actually grant its accolade power?
  A character holding it either shows the HP/End bump or does not.
- **The gaming box** has not woken since 2026-07-29.
- **The i24 torrent** (zone display names ride on it).
- **Design calls still open**: naming which set bonus changed, pairing the wide
  diff tables, whether meters move displayed damage, and whether the app should
  track a character's origin at all.

### Where the detail lives
`session-report.md` (outbound, newest first) has the full account of the last
session. `CLAUDE.md` holds every standing rule; the newest entries are the
per-character state sweep, the tour scene trap, the epic-swap refill, the
PvP-variant disposition and the scripted-write CRLF warning.

# Resume point — 2026-08-06

## ⏸⏸ SESSION CLOSED — 2026-08-06, read THIS block first

**HEAD `226b6db0`, pushed, tracked tree clean. Published `v0.12.32`. Installed
copy frozen stamp `e164fd1`. App not running. Nothing scheduled, no monitors.**

⚠ **The installed copy's STATICS are ahead of its stamp** (the button-cap CSS
went in via `push_statics.py` after the 0.12.32 build). Do not read the stamp as
"what the app contains". A rebuild resolves it whenever one happens next.

### The ONE staged item
CHANGELOG "Unreleased" holds a single entry: **action buttons share one width**
(`button { max-width: 420px }` + a row-control opt-out). It is in Joel's app but
not in any release. Everything else shipped in 0.12.32.

### ⚠⚠ TWO RETRACTIONS FROM THIS SESSION — do not act on the old versions
1. **−recharge debuff pinning: ALREADY DONE** (`6b503c0c`, 2026-08-05). The
   "Slow enhancements / under-credited" line was stale; I chased finished work
   because of it. Recharge is credited both directions, verified live
   (Neurotoxic Breath −81.2% unslotted → −102.6% slotted).
2. **"Radiation Melee per-attack damage is wrong": FALSE, retracted same day.**
   I compared ENHANCED engine damage to BASE client scales on differently
   slotted attacks. Our base is exact (74.1 / 154.2 = client 1.48 / 3.08 ×
   50.07/50.06; base ratio 0.481 = client 0.481). No data bug.

**The lesson both share, and it is the expensive one: check what a number
MEASURED before repeating it, and close an item in the records the same commit
that closes it in the code.**

### Where Fury actually stands
`tools/measure_fury_residual.py` v2 is built (component-summed swing
reconstruction, the v36 memo's named instrument). Spread **228% → 25.2%**.
Blocked, precisely: **only two attacks isolate cleanly, and two points cannot
separate a multiplier from a flat term** (`expected×F + C = observed` gives
F≈0.995 / C≈48.9 with nothing left to validate). **Needs a THIRD clean
single-target attack** — farm logs from a Brute whose rotation has 3+ of them.
AoEs can NEVER be reconstructed from this log format: farm mobs share display
names, so grouping merges hits on different enemies (Atom Smasher logs up to 18
components for a 2-component attack).
⚠ **New trap recorded:** 86 of 108 Brute melee attacks carry a `Fire_Dmg`
template with an EMPTY gate in the export. That is **Fiery Embrace**; our data
correctly omits it. Never "fix" it by trusting `requires_expression == ""`.

### Power Boost — untouched, and it is the same work as Fury
The client shows it is a `Set_Mode` (BoostPower, 15s), not a flat bonus, so it
belongs with the meter/mode capability. Zero champion exposure, so it can never
move a certified score. The displayed-damage half is Joel's ruling.

## ⏸ PLACE SAVED — 2026-08-06 late, after the button fix

**HEAD `d54415f0`, pushed, tracked tree clean. Published `v0.12.32`. App not
running. Nothing scheduled.**

⚠ **The installed copy's STATICS are ahead of its stamp.** Frozen stamp is
`e164fd1` (the 0.12.32 build); the button-cap CSS reached it via
`push_statics.py` afterwards. That is fine — the change is CSS only with no
server dependency — but do not read the stamp as "what the app contains".

**▶ ONE ITEM STAGED FOR THE NEXT RELEASE** (CHANGELOG "Unreleased"): the action
buttons now share one width. See the `button { max-width: 420px }` block in
style.css for why it is a CAP and not `width: auto` — that choice is the entire
no-layout-break guarantee, and the comment carries the measurement (246 buttons
snapshotted with and without the cap; exactly one changed).

## ⏸ PLACE SAVED — 2026-08-06 night, after v0.12.32

**HEAD `e164fd13`, pushed, tracked tree clean. Published `v0.12.32`. Installed
copy = `e164fd1` and reports 0.12.32. App not running. Nothing scheduled.**
Two releases landed today: 0.12.31 (the desktop app) and 0.12.32 (everything
from Joel's review after it). Data 2026.1.1242 and model v38 both unchanged in
0.12.32, so no certified score moved and no re-cert is owed.

**▶ FIRST THINGS NEXT SESSION**
1. **The 0.12.32 announcement post is written and NOT posted** — it is in the
   chat transcript, ready for topic 64761. ⚠ Its badge sentence is deliberately
   weak: it says `/thumbtack` is the command the client registers for placing a
   minimap marker, and does NOT claim the marker lands correctly. Nobody has
   confirmed that in game (Joel said skip it). Strengthen only after someone has.
2. **FP / whitelist submissions** for the new signed 0.12.32 artifacts, per
   docs/signing-runbook.md. ⚠ Bitdefender often kills the app on release nights.
3. **The render watch was armed and never fired** (monitor `bev2z5b0h`, baseline
   run 31128638583). The Pages deploy-job removal (`0c06b9df`) is proven by ONE
   good build; confirm the next few scheduled renders still publish cleanly.

**▶ MINE AND UNBLOCKED, in the order I would take them**
- ~~Pin the −recharge-debuff question~~ **ALREADY DONE — `6b503c0c`, 2026-08-05.**
  The Slow hypothesis was disproven by the client and Recharge is credited in
  both directions; verified live (Neurotoxic Breath −81.2% unslotted → −102.6%
  slotted). This line was stale and sent a session chasing finished work.
- **Fury meter + Power Boost as ONE piece** — the client shows Power Boost is a
  `Set_Mode`, not the flat bonus it was queued as. Zero champion exposure. Only
  the displayed-damage half needs Joel.
- ~~the 8 irreducible Chrono_Shift rows~~ **CLOSED 2026-08-07** — PvP variants
  (`pv_mode 2`), exactly 5.33× the client's own timed heal scales on all four AT
  variants. Gated off in PvE, proven live. The census instrument gained the
  class it was missing: residue 240 → 184. See CLAUDE.md.
- ~~alias-map roster reconciliation~~ **CLOSED 2026-08-07** — a display-name
  rung took roster diffs 12 → 3 with zero existing aliases changed; the 3 left
  are real roster differences, each named with its evidence and hard-failed if
  left undispositioned. It surfaced a real defect — Blaster Tactical Arrow
  showed "Oil Slick Arrow" twice and never "Gymnastics" — **✅ FIXED the same
  day on Joel's word** (`patch_display_name_collisions.py`: 1 record, 7 fields,
  verified through the served `/powers` route; zero champion exposure, no
  re-cert owed). See CLAUDE.md for the two follow-ons the fix required.
- Leveling Companion batch · pricing #31 · strict-dominance experiment
  (optional).

**▶ JOEL'S, UNCHANGED** — github.com/settings/billing (inbox runner block, both
workflows stay `disabled_manually`) · the Iron Man badge look · the gaming box,
silent since 2026-07-29 · the i24 torrent · and five open design calls (name
which set bonus, pair the wide diff tables, meters on displayed damage,
budget/balanced/premium, whether the app tracks character origin at all).

## ▶▶ AGENDA SWEEP (2026-08-06 night) — two solved, two closed, two re-scoped

**SOLVED**
- **Exploration-log parse** (`9360ae81`): `marginals()` streamed instead of
  loading 2.2 GB into dicts. Measured on the real log: **89.3 s → 29.3 s, 6,174
  MB → 393 MB peak (15.7×)**, result byte-identical (SHA-256 compared). Cost
  fix only, moves no number, no re-cert. Battery `test_learn_stream.py` (11),
  3 sabotages. ⚠ The pre-filter's danger is a FALSE NEGATIVE — `ctx_key` still
  decides membership, the substring test only pre-rejects.
- **Reduced motion** (`55d40c67`): the CSS block existed, but
  `scroll-behavior: auto !important` cannot override a `behavior:"smooth"`
  passed in JS — 11 sites did. One `scrollBehavior()` helper, read at call time.
  test_desktop_app 129 → 132, sabotage-proven.

**CLOSED — nothing to fix, do not re-open**
- **18 inherent icons.** All seven player-visible granted inherents already have
  icons. The 40 unmapped ones are internal machinery (`AutoLevel20`,
  `COMBO_LEVEL_1`, `SR_HP_Slider`, `FAST_MODE`) that the CLIENT gives no icon
  name — inventing art there breaks the game-first rule.
- **Origin plates.** Extracted and unreferenced because **the app has no
  character-origin concept at all**. "Placing" them means inventing an origin
  field + picker + persistence — a product decision, not art placement. Joel's.

**RE-SCOPED**
- **Power Boost + the Fury meter class are ONE piece of work** — see the
  CLAUDE.md entry. Power Boost is a `Set_Mode`, not a flat bonus. Display half
  is already Joel's ruling. Zero champion exposure either way.
- **Zone display names** stay blocked game-first until the i24 pass.

## ✅ THE PAGES RACE IS FIXED (`0c06b9df`) — and the inbox is still Joel's

**Fixed:** two deployers had been racing since 07-27 (GitHub's per-push legacy
build + a `deploy` job in `render-pulse.yml` left behind by a half-revert of the
07-20 change). The job is removed; the render's commit publishes. **Proven:** a
dispatched render succeeded (one job, 11 steps), its board commit produced the
first SUCCESSFUL Pages build in hours, and Pages status went `errored` → `built`.
Board live, current date. See the CLAUDE.md entry for the standing rule that the
source setting and the deploy job are one decision.
⚠ Watch the next few scheduled renders — one good build is encouraging, not
proof. The daily freshness canary is the backstop.

**NOT fixed, and not mine:** the inbox workflows still cannot get a runner
(proving run 31127012557: queued 55.9 min, cancelled, zero steps, `runner: ""`).
Both remain `disabled_manually` so the daily failure mail stays off.
**github.com/settings/billing is Joel's** — billing needs a gh scope
deliberately not granted; do not re-auth to chase it.

## ⏸ SAVED PLACE — 2026-08-06 evening (Joel headed home)

**HEAD = `de80a2b0`, pushed, tracked tree clean.** Installed app is frozen stamp
`bdc7f48` and holds ALL the code (the two commits after it are docs only). The
app is not currently running. Release still HELD at 0.12.31; everything below is
staged under CHANGELOG "Unreleased".

**✅ RESOLVED, and the answer was no.** Proving run 31127012557 sat **QUEUED for
55.9 minutes and was cancelled with ZERO steps** — it never got a runner. The
allowance has NOT reset, so both workflows are `disabled_manually` again (done
the same evening, so tomorrow's failure mail does not resume). **The next move
is Joel's: github.com/settings/billing** — a declined payment method would not
self-heal on a monthly reset, and nothing was consumed in August because the
workflows were off all month, so "ran out of minutes" does not fit. Do not
re-auth gh to chase this. Boards verified unaffected (200, current date).

**What today's inbox finding was:** Joel's Companion Lite 0.1.18 on his gaming PC
is uploading fine (captures every ~5 min). But `Collect mailbox` and `Inbox
maintenance` were STILL `disabled_manually` — five days past the recorded
2026-08-01 re-enable date — and the inbox had accumulated **2,633 commits since
07-27**, which is what the weekly squash exists to prevent (8.4 MB, ~288
commits/day). Both are `active` again. The boards were never affected: the
render lives in the PUBLIC repo and reads the inbox directly.

**Still owed, none blocking:**
1. **Paste a `/thumbtack` in game and watch the X land** — the one claim in the
   badge work nobody has confirmed. Joel's eyes only.
2. The diff says "Set bonuses 41 → 42" without naming WHICH bonus. Offered to
   him, not built, he has not asked.
3. The forum reply (v5 draft) is still unsent, and the 0.12.31 announcement post
   was handed to him in chat but not posted to topic 64761.
4. FP/whitelist submissions for the 0.12.31 signed artifacts.

## ▶▶ LATEST: the picker refuses what the game refuses (`bdc7f488`)

**⚠ SERVER CHANGE → REBUILT.** dist rebuilt (stamp `bdc7f48`), frozen smoke PASS
+ gold 24/24, mirrored to the installed copy (uninstaller preserved), relaunched,
and `/meta` verified shipping the override in the LIVE app. VERSION still the
released 0.12.31, ISCC NOT run, `dist\HeroCompanion-Setup-0.12.31.exe` intact.

A unique held in ANOTHER power is now greyed with the reason naming that power,
and `pickPiece` enforces it as well as the greying. ⚠⚠ The over-blocking guard
is the important half: `/meta` ships `engine.NON_UNIQUE_OVERRIDES` (LotG global
recharge) and the check FAILS OPEN with no meta. Verified live on a solved
Claws/SR. Battery `test_slot_rules.js` (9, four sabotages).

## the swap picker prices every replacement (`47c52dfb`)

**⚠ THIS ONE CHANGED `server.py`, so it needed a REBUILD, not a statics push.**
dist rebuilt + frozen smoke PASS + gold 24/24, mirrored to the installed copy
(stamp `47c52df`, `unins000.exe` preserved), relaunched, and the route verified
live in the running app. VERSION is still the released 0.12.31 and ISCC was NOT
run, so `dist\HeroCompanion-Setup-0.12.31.exe` is untouched.

New `POST /build/slot_compare`: every candidate priced by rebuilding the
character with it in the slot, in one batched request (4.9 ms each, measured
first — 165 candidates < 1s). Axis = the selected stat, set-bonus count always
alongside. See the CLAUDE.md entry for the four traps.
⚠ On an optimised build every swap on the optimised stat is a deficit — the
truth; the gain direction is separately proven. Battery `test_slot_compare.py`.

## every edit reports itself + Undo (`3871f25c`)

"What changed" appears on Stats after ANY build-mutating edit — the hook is
`recordEdit` (called by every surface), not the popover's buttons, so it is
universal by construction; proven with a plain `clearSlot`. Carries **↶ Undo
this change**. Measured: Remove → Lethal 27.5→23.8, bonuses 42→41 marked as
losses; Undo → piece back, 42, Lethal 27.51, no second receipt.
⚠ `_placeIoPop` re-centres when its anchor chit is destroyed (closing would take
the Undo with it). ⚠ `renderImproveDiff` labels are per-caller now
(`opts.labels`); test_improve_diff 13 → 15, sabotage-proven.

## Stats is the MANUAL surface (`ec1f09d6`)

Joel's framing: Powers & Slots owns the Assistant's global "more X, Y, Z"
re-solve; **Stats is where a player changes one piece at a time**. So the
popover now carries **Swap this enhancement… / Remove it**, on the same
`openSlot`/`clearSlot` every other surface uses — no second editing path.
Verified the prediction IS the outcome: predicted Without-it Lethal 23.8 /
Smashing 23.8 / Melee 45.1 / bonuses 41 → Remove delivered 23.76 / 23.76 /
45.08 / 41. Swap opens the picker on the right slot with the popover closed.

## the per-IO answer is a popover at the chit (`2548a27f`)

Clicking an enhancement used to answer into `#stat-breakdown`, below the wall —
so the answer was off screen. His stated purpose ("what to sacrifice for the
LEAST impact") is a comparison, so the page must not move: `#io-worth-pop`
anchors to the chit, follows chit-to-chit clicks with zero page scroll, clamps
to the viewport, closes on ✕ or an outside click (never Escape — it does not
reach the page in this shell). **The stat breakdown underneath is untouched**,
so a stat can stay selected with its contributors ringed while each is probed.
Measured at 1240: 6px under the chit, 287px tall, right-edge clamp holds
(chit x=1153 → popover right 1232 of 1240), 6px again after a scroll settles.
⚠ Per-power table opens FOLDED, or the popover wants its own scrollbar.

## the contributions column is back at his width (`23fbe8e6`)

⚠ **I got his previous message wrong first.** "Display along side what is
clicked" meant *the right-hand column, where it used to be, with the arrow* —
not a new inline position. The fault was the BREAKPOINT: `.stats-provlayout`
collapsed below 1400px and the 1.6× shell zoom put his effective width under it,
so the column was switched off. It holds to **1000px** now (that side column is
real content, not a void, unlike the powers rail which keeps 1400). Measured at
1240: two columns 811+380, panel beside the row, green ➜ intact, 8 power cards.
Below 1000 it still stacks and the JS keeps it under the clicked row (2px).
`test_desktop_app` 128 → 129; the "both collapse at 1400" pin now pins each at
its own width + a sabotage-proven negative control.

## the breakdown follows the clicked row below 1000px (`e4248462`)

Joel's screenshot: the right-hand contributions column was "missing". It was
1750px below the row — `#stat-breakdown` is the last child of the stats grid,
and the 1400px rule had collapsed that grid to ONE column. **His window is wide;
the 1.6× shell zoom is what pushes the EFFECTIVE width under the threshold.**
One column now re-homes the panel directly after the selected row (2px gap,
follows the selection); two columns is unchanged. ⚠ Re-homing puts it inside the
rows container that gets innerHTML-rewritten every recompute — `_breakdownHost()`
holds the element and re-attaches it, proven by driving a real recompute.
Also fixed: the mini-wall header rendered twice (lengthened past 26 words →
`collapseLongExplanations`; it has `.keep-whole` now).

## per-IO worth + the green-marks legend (`fa8d9506`, `b867df72`)

Both in **both frozen copies** and the app relaunched (statics only; frozen
stamp stays the release `b2161e1`). Staged under CHANGELOG "Unreleased".

- **Click any enhancement in the Stats miniature wall → what it is worth**,
  measured by rebuilding the character without it. See the CLAUDE.md entry for
  why the analytic shortcut is wrong and for the two traps (`buildPayload()`,
  and `/build/calculate` returning totals directly).
- **The two green marks have a legend** — a ring on an enhancement vs a box on a
  power's NAME. It was only ever explained in a footnote that appeared solely on
  powers that had the built-in contribution.
- Batteries: `test_improve_diff` 9 → 13 (2 sabotages), `test_journey_macro` 35.
- ⚠ **Open, worth offering him:** the diff says "Set bonuses 41 → 42" without
  naming WHICH bonus. Naming it needs the applied-bonus list diffed by name, not
  just counted. Small, not built, and he has not asked.

## ▶▶ THE BADGE CATALOGUE REBUILD + FLASHBACK LANDING (`04219ff3`)

Joel's two follow-up orders, built, verified live, pushed, and **in both frozen
copies** (statics only; the frozen stamp stays the release `b2161e1`).

- **Every badge is on the surface and its name is the button.** 390 chips under
  57 zones, 382 clickable, 8 inert-by-design (no coordinates → plain text, never
  a fake control). The drawer keeps the prose and names what it holds; the
  how-to is stated once at the catalogue head. Copy handler now keys on
  `[data-cmd]` so chip and wide row are ONE mechanism — see the CLAUDE.md entry.
- **Flashback lands on Praetoria** when you arrive from a stop outside its 1–20
  range, and hands your stop back when you leave (`_praeSnapIndex`, pure and
  battery-driven). Verified: hero L50 → Flashback (Nova Praetoria) → hero L50.
- Battery `tools/test_journey_macro.js` **35 checks, 9 sabotages proven**.
- ⚠ **STILL UNCONFIRMED IN GAME: nobody has pasted a `/thumbtack` and watched
  the X land.** That is the one open question on all of this work.
- ⚠ Visible in his screenshot and NOT fixed (it is a standing ruling): zone keys
  are raw internal prefixes, so the grid shows `AbSewerNetwork` and both
  `CapAuDiable` and `CapauDiable`. Display names ride the i24 server-data pass.

## (earlier the same evening) badge macros + the Flashback art empty state (`12bc2b63`)

Post-0.12.31 work from Joel's two observations. Committed and pushed, staged
under CHANGELOG "Unreleased".

**⚠ NOW IN BOTH FROZEN COPIES (pushed 2026-08-05 late, after Joel went looking
for it).** I first withheld the statics so his app would match the release, said
so at the end of a long reply, and offered a choice — he went to the desktop
shortcut to look instead and reported "nothing was updated." He was right, and
the friction was mine. **Generalize: when someone has just asked about a fix,
the default is to put it where they can see it, not to hand them a choice about
plumbing.** `push_statics.py` (2 of 3123 files → both copies) + relaunch;
statics-only, no server dependency (the coordinate and zone data were already
being served), so no half-update lie. Installed copy still reads *installed*
and its frozen stamp is still the release `b2161e1` — only the statics moved.

- **`/thumbtack <x> <y> <z>` is the game's own map-marker command**, pinned from
  `cityofheroes.exe`'s command table — see the CLAUDE.md game-facts entry for
  why the pairing is self-proving and why `/loc` must NOT be claimed from the
  same dump. Every badge with coordinates (382 of 390) carries a click-to-copy
  row reusing the shipped `.cmd-row` handler.
- **⚠ UNCONFIRMED IN GAME:** nobody has pasted one and watched the X land.
  Joel's eyes settle it — that is the one open question on this work.
- **The Flashback art slot stopped claiming "zone art pending"** above level 20,
  where Praetoria simply ends; the range is derived from the zone data.
- **25 badges were hiding their coordinates** because the numbers were nested in
  the directions block. Fixed at the root.
- Battery `tools/test_journey_macro.js` — 20 checks, proven against 6 sabotages.
  Regressions green: tour, tabs 10/10, links, desktop app, improve-diff 9/9,
  `demo_single_build_fixes` 24/24.
- ⚠ Known, NOT changed: `/journey/badges` serves only `locations[0]`, so the 39
  badges with more than one spot show one. Say so before "fixing" it.

## 🚀 v0.12.31 "The desktop app" IS PUBLISHED (2026-08-05 8:35 PM ET)

Joel reviewed the installed app, gave the thumbs-up, and the full release
procedure ran clean: VERSION + both smoke pins bumped, CHANGELOG's stale
Unreleased block rewritten as the real 0.12.31 entry, docs/index.html
disclosure flipped to the window truth (the recorded release step), help PDF
rebuilt, clean-stamp frozen build `b2161e1` (release-prep committed FIRST so
the stamp is not "-dirty"), frozen smoke PASS, gold 24/24 SERVED, exe +
installer signed and verified (CN=Joel Andrew Chambers), portable zip built,
`gh release create v0.12.31` with both assets, API-verified. Installed copy
mirrored from dist (robocopy /MIR, unins000.* preserved) and relaunched —
Joel's shortcut now opens the released build. Release announcement post
handed to Joel in chat + session-report (no em dashes). Remaining his-hand
items: post it to topic 64761, FP/whitelist submissions per signing runbook,
watch for the Bitdefender release-night kill (verify the app relaunches once).

## ✅ POWER-ICON PASS: the i24 glob bug is fixed — `7a67c48c`

The two-line fix and the finding that made it pay: `extract_power_icons.py`
globbed `texture_*.pigg` (zero matches in the i24 set — its archives are
`tex*`/`stage*`), and the still-missing `e_icon_gen_*` names live under
`GUI/Icons/Enhancements` (i24 stage2.pigg), a prefix the tool never searched.
23 textures extracted, **94 Incarnate Alpha boost sub-powers** now carry the
game's own generic enhancement art (coverage 6033→6122). 7 textures are absent
from BOTH asset sets and stay reported, not faked. Gate 24/24. Data + statics
change — rides the next rebuild; nothing pushed to the frozen copies (a
missing icon renders the fallback, so no half-update lie is possible).

⚠ Stale-queue note: the **verdict-gate legality hole is ALREADY CLOSED**
(`07ce596e` + `tools/test_verdict_legality.py`) — older open-queue lines
naming it are superseded.

**HEAD = `c78f552b`, pushed, tracked tree clean. Nothing running.** Release still
HELD at 0.12.30.

## ✅ RECHARGE IS CREDITED, and the client settled it — `6b503c0c`

Joel: "lets give recharge its accreditation." My exclusion was a GUESS (that
−recharge rides Slow enhancements) and the client disproves it AND answers the
question properly:
- `Crafted_Curtail_Speed_A`, a Slow IO, enhances RunningSpeed / FlyingSpeed /
  JumpingSpeed + Accuracy. **No RechargeTime — Slow is not the route.**
- Neurotoxic Breath's −recharge is `attribs ['RechargeTime'], aspect Strength,
  target AnyAffected`, and its `boosts_allowed` carries `Recharge`.
- Speed Boost and Accelerate Metabolism hold the same template pointed at
  allies and allow `Recharge` too — so it is credited in BOTH directions.

Measured: the saved Poison build has no recharge in Neurotoxic Breath so its
−recharge row correctly does not move; add one recharge IO and it goes
**−83.2 → −117.4**. Both arms are pinned, so the positive case cannot pass by
accident. The three remaining exclusions now cite the game's own per-power
allow-lists rather than "no such category exists". `test_buff_debuff_enh` 9 → 11.

## 🖥 HIS INSTALLED APP IS CURRENT (stamp `116d1ce`)

Joel, 2026-08-06: *"The deliberately means nothing to me, its giberish without
context."* Fair — the dist/installed split is my plumbing, not his problem.
**The installed copy is now updated from the smoked dist build by robocopy /MIR
(excluding `unins000.*`, so the uninstaller and ARP entry survive).** Do this
after any server-side change rather than explaining a distinction to him.
⚠ Statics and PYZ must move TOGETHER — see the CLAUDE.md rule.

## ✅ THE SLOT INVITATION IS A CLAIM NOW — `018b539d`

Joel: *"This appears no matter if slots are all filled or not."* "All 24 powers
picked. **Now slot them**" was decoration on a full pick list. It shows only when
the pool has free slots or a **real** power holds an empty one, and it names the
reason; otherwise "All 24 powers picked, every slot filled" with no CTA.
⚠ **The seven granted inherents are excluded** — Brawl/Sprint/Rest carry a base
slot the solver is capped out of by design, so counting them makes the nag
permanent. Negative-controlled on screen (emptying Health does nothing; emptying
a real power brings it back). His build genuinely has two empty slots (Alkaloid,
Weave), so his line now says why.

## ⛔ THE CLASS-ART FILLER IS REMOVED AT HIS WORD — `018b539d`

*"Remove the one image, from your attempts. I will try and find something."*
The CSS rule, the `--at-art` variable and all 15 PNGs (3.8 MB) are gone from the
repo **and from both frozen copies**. ⚠ `extract_gui_emblems.py` keeps the
capability behind an explicit **`--art`** flag — finding the art was the work
(`charectercreationui/archetypescreenshotsassets`, 512×314 after crop, 3 shots
per archetype, 15 of 16; Guardian has none) — but a routine emblem run must
never drop unused megabytes back into `static/`. **He is sourcing his own art.**

## (superseded) THE CLASS-ART FILLER — `c9265561`

His idea: *"some filler graphics representing each class being worked on while
picking powers might be nice."* Half done, and the half that failed is stated.

- ✅ **The game has real art for this**: `charectercreationui/
  archetypescreenshotsassets`, 512×512, three shots per archetype.
  `extract_gui_emblems.py` now pulls shot 0 → `static/icons/at_art/` (15 of 16;
  **Guardian has none in the client**, reported not faked). The 32px emblems in
  `icons/at/` are ICONS — at panel size they are mush, which is why this needed
  its own source.
- ❌ **It would not paint in the frozen shell.** Three mechanisms tried (panel
  background + blend mode; absolute `::after` at 0.16; same at 0.55, no mask).
  In the dev copy every measurement says it is there — var resolves, box
  computes 291×176, image loads — and the real window shows nothing. Stopped at
  three rather than ship a fourth shape for one feature in one evening.
- ⚠ **The idea has now been tried TWICE**: a dead `.cat-art` rule (archetype
  watermark in the catalogue, rendered by nothing) was found and removed.
- **Nothing references the art**, so nothing changed on screen. It is committed
  because extracting it was the hard part.
- ✅ **FIXED after his "I saw one image for one build but it was small":** it was
  painting all along, anchored to `#powers-list` — which holds the wall **and the
  catalogue**, so bottom-right of it is the bottom of the CATALOGUE. Now anchored
  to **`.powers-wall`**, sized to the measured 978×152 hole its last row leaves,
  at `z-index: -1` inside the wall's own stacking context so the opaque cards
  mask it (a fuller last row just covers more — no card count in the CSS).
- ⚠ **The textures are a ~512×314 picture padded to a power of two with a flat
  blue block under it.** `contain` fitted the pad too and put a blue slab on
  screen. The extractor crops now (detector + a 314-row fallback for three shots
  whose pad the sampler can't separate from their dark sky); all 15 verified.
- ⚠ **A cropped BAND filled the strip but decapitated half the roster** — the
  Defender floats in the upper third and lost its legs, the Brute fills its frame
  and lost its heads. So it fits by HEIGHT and shows whole: correct for all 15,
  **at ~245px rather than filling the strip. Joel's call if he wants it bigger**
  — that needs either a per-class crop focal point or more vertical room.

## ✅ DONE: the buff/debuff panel reads enhancement — `be8641db`

Joel's ruling, acted on. `_debuff_buff_summary` priced every row at base scale ×
modifier table with no slot boosts; it now multiplies by the host power's own
post-ED enhancement in the aspect of the effect's name.

- **The rule needs no table:** effect names and enhancement-aspect names are the
  same client vocabulary, and whether a power may hold an enhancement is already
  answered by its own slots.
- **Four exclusions, the game's own:** across 3,650 powersets the client ships no
  resistance-debuff, no −regeneration and no −damage category, because those
  enhancements do not exist. RechargeTime was excluded separately at first, then
  ✅ **CREDITED the next day (`6b503c0c`)** — the Slow hypothesis was wrong and
  the client settled it (a Slow IO carries no RechargeTime; the −recharge
  template's own `boosts_allowed` includes Recharge).
- Measured (Poison/Sonic): Envenom −Def **68.8 → 106.3**, Neurotoxic Breath Slow
  **768.8 → 1099.3**; −res / −regen / −damage do not move at all. −recharge DOES
  move as of `6b503c0c`: Neurotoxic Breath **−81.2% → −102.6%**.
- **NO MODEL BUMP, NO RE-CERT — traced, not assumed.** `first_principles._deb()`
  reads `role_output.enhanced_debuff_totals` whenever a role_output module is
  supplied and every serving call site supplies one, so this summary is only its
  fallback; role_output was untouched and `encounter_value` is identical to nine
  decimals (contribution 1672.0 → 1672.0). ⚠ The other consumer,
  `payoff_metrics["support"]`, is reachable ONLY from `joint_refine(scorer=
  "payoff")` — **which has no callers anywhere**; wire it up again and that path
  starts moving with slotting.
- Copy follows the numbers: both headers now say "with your slotting", and the
  stat breakdown no longer claims "not from IOs".
- Battery `tools/test_buff_debuff_enh.py` (9, negative-controlled both ways).

⚠⚠ **STATICS WERE DELIBERATELY NOT PUSHED TO THE INSTALLED COPY.** Its server is
still `297ddcf`, so pushing the new wording there would put "with your slotting"
above numbers that are still unenhanced — a lie on his machine. The installed
copy stays wholly on the old text until he chooses to install. **`dist` has
both halves and is the copy to open** (`be8641d`, smoke PASS, gold 24/24).

## 🔨 THE FROZEN REBUILD IS DONE — but only `dist` has it

`dist\HeroCompanion` is rebuilt and stamped **`c78f552`** (was `297ddcf`), so the
2026-08-05 server work finally exists in a frozen artifact: the portable-update
refusal (`_install_kind`) and the special-origin names in `PIECE_BY_UID`.
Frozen smoke PASS · frozen gold **24 of 24 SERVED**.

⚠ **The INSTALLED copy is still `297ddcf`** — `%LOCALAPPDATA%\Programs\HeroCompanion`
carries statics from today but the OLD server inside its PYZ, and that is the
copy Joel's shortcut opens. Getting the server fixes there means running the
installer (ISCC + install), which **overwrites `dist\HeroCompanion-Setup-0.12.30.exe`**
— the released signed installer, preserved as `.released-signed.exe` — and
changes how the app lives on his machine. **His call, not mine.** Until then:
launch `dist\HeroCompanion\HeroCompanion.exe` to see the server-side fixes.

## ✅ DONE, last thing before Joel left: no side bar on Powers & Slots — `809c9190`

His words: *"The output of a build assistant is terrible on the far right. Why
not put it and the whole epic and incarnate right below the All 24 powers picked
section. Epic and incarnate first, then Build Assistant. Let it take up the
entire horizontal width so no side bar appears at all, unless IO details are
asked to be displayed."* Built and eyes-verified on the installed window.

- `#endgame-plan-panel` then `#assistant` are full-width sections under the
  builder. `.powers-side` keeps the ⓘ card and nothing else.
- The column is opened **by the card, in CSS** —
  `.powers-layout:has(#power-info:not(.hidden))`. ⚠ The 1400px and 980px
  overrides must REPEAT that whole selector (`:has()` takes its argument's
  specificity, so a bare `.powers-layout` loses to the id inside it).
- Dead `has-info` class deleted; the grout rule retired with the second column.
- Measured: wall 4 cards → 6, catalogue's 7 powerset columns in ONE row, the
  improvement table 1489px wide with every row a single 22px line (it used to
  wrap in the 340px column — that WAS his complaint).
- `test_desktop_app` 121 → 126, every new check sabotage-proven.

**▶ Two things worth his eye next session:**
1. The two diff tables (totals + power-by-power) now each span ~1490px, which is
   generous for four numeric columns. Offer to pair them side by side.
2. ⚠ His app was left showing **Hero**; it was on Villain when the session
   started. Alignment lives in localStorage and I cycled all four verifying the
   wordmarks — set it back if he notices.
⚠ Relaunch the app: statics were pushed to both frozen copies AFTER the window
he last had open.

---

## ✅ DONE: per-power deltas in the improvement report — `10a7ed0b`

The last ❌ in the big-ask table below is closed. Every attack the engine priced
is diffed by its **Cycled DPS** (the same number the ⓘ card shows) plus a
per-hit row, and **pets are credited to the power that summons them** ("Jack
Frost → Ice Elemental, 72.4 → 78.3 DPS"). Own `<details>` table under the
totals; it stands alone when a per-power move is too small to shift any total.

- ⚠ **Buffs/debuffs are deliberately NOT diffed per power.** The rows carry
  provenance (`_debuff_buff_summary`'s dsrc/bsrc → `row.sources`) but the
  magnitudes come from `_resolve_mag` — base scale × table, **no slot boosts** —
  so a re-solve can never move them and every row would read 0.
- ⚠ **That is also a real gap worth ruling on:** the whole buff/debuff panel is
  unenhanced, so a debuffer who slots accurate defence-debuff or −regen sets
  sees nothing move anywhere. It hits the invisible-role doctrine hardest.
  Engine work, not display work — not started.
- Battery `tools/test_improve_diff.js` (**node**, 9 checks) lifts the REAL
  function out of app.js and drives it; takes an alternative app.js as `argv[2]`
  and was **proven against six sabotaged copies**, each caught by the right
  check. Verified end-to-end in the running app on a real Poison/Sonic solve.

## ✅ DONE: the four alignment wordmarks — `3a01bcf3`

Joel's `C:\Users\joelc\Downloads\Art\Hero Companion Wordmarks.html` is **not
four images** — it is text in **Anton** with a treatment per alignment, and it
ships its own header-size row. The app wears it as TEXT.

- Anton vendored (`static/vendor/anton-latin.woff2` + `anton-OFL.txt`, credited).
  ⚠ Vendored, never linked: the app has no network, a Google Fonts href renders
  nothing.
- **Each alignment needs its own `body.align-<key>` class** — theme-hero /
  theme-villain / align-mid make only three states and the two middles are
  different marks.
- **Sized to the space that was there** (his instruction). Sheet = 30px = 171px
  wide; old title = 136px; shipped at **20px = 132px**, masthead unchanged at
  47.5px. Widest name within 3px of before.
- Verified with EYES on the installed window, all four cycled via the View menu.
- ⚠⚠ **`push_statics.py` was copying static/'s TOP LEVEL ONLY** — `vendor/` and
  `icons/` never synced. The CSS reached both frozen copies, the font reached
  neither, and it printed "2 of 2 known copies updated" over the miss. Fixed to
  walk the tree ("N of 3100 files written"). Anything that ever lands in a
  static SUBDIRECTORY was previously invisible to both frozen copies.

Verification at close: `demo_single_build_fixes` 24/24 · `test_desktop_app`
121/121 · `audit_tour` all · `audit_tabs` 10/10 · `audit_links` 177 refs with 5
planted defects caught · `test_improve_diff` 9/9 + 6 sabotages.

# Resume point — 2026-08-05 late

## ▶▶ START HERE: the ROLE / OUTPUT arc, and the one thing left in it

Joel's live thread of work. Everything below is committed and pushed.

**Shipped today, in order:** role descriptions verified already-done · Split role
(renamed from "Mixed / Generalist", N-way not 2-way, every role offered grouped,
shares forced to total 100, new rows pick nothing) · the **"What this build
delivers today"** panel (real numbers per named job) · the **invitation** when a
build has no role · the **Enhancement Unslotter** footer (client-verified) · tour
cards for split-role, the output panel and the unslotter (63 steps) · and the
**improvement report generalised** to diff every measured axis.

**▶ THE BIG ASK — where it stands (Joel's own framing: "tell them how their
choices actually came out at the end", in real numbers, per power).**

| Piece | State |
|---|---|
| Before/after on every solve | ✅ EXISTS (`solveBefore` → `renderImproveDiff`) |
| Diff covers ANY measured axis | ✅ DONE today (`653d94f0`) — typed def/res, scalars, v30 families, ST/AoE DPS, **pet DPS**, every buff/debuff row |
| "Nothing moved" explains itself | ✅ DONE today (names locked-power count) |
| **Per-power deltas** ("Empty Clips +18 DPS") | ✅ DONE 2026-08-06 (`10a7ed0b`) — attacks by Cycled DPS + per hit, pets by their summoning power. Buffs/debuffs excluded on purpose (unenhanced magnitudes); see the 08-06 block at the top. |
| Preview a split WITHOUT committing | ❌ Not built. Today a solve commits; Ctrl+Z undoes and names the edit. **Design decision, not coding** — Joel's steer was to see whether (1)+(2) make it unnecessary. |

⚠ Cost of a comparison: one solve, ~1-2s, doubled by serve-time physics
arbitration. Fine behind a button; **never on slider drag.**
⚠ Joel's constraint on all of it: only what the game really offers, never an
invented scenario. The generalised diff satisfies that by construction — a row
can only appear if the engine measured it from game data.

# Resume point — 2026-08-05 evening

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

## ✉️ THE FORUM THREAD (topic 64761) — v5 REPLY DRAFTED, NOT SENT

⚠⚠ **THE v4 DRAFT (session-report, 2026-08-02) IS NOW DANGEROUS TO POST** — the
rebuild made four of its claims false ("The app lives in your system tray", "the
update check only runs when you click it", "the planner does not understand
exemping at all", plus two promises now delivered). **Use v5** (session-report,
2026-08-05), written in the cheeky-Australian voice Joel asked for, no em dashes.

⚠ **Governing fact for anything posted: 0.12.30 shipped 7/31, Basilisk posted
8/2, and every fix landed after. Nothing he can download today has any of it.**
The reply must say "next release" and never imply otherwise.

**✅ RETRACTED — THE ROLE PROMISE WAS KEPT, AND I SAID OTHERWISE.** I reported it
as the one unkept promise on the strength of a grep that searched lowercase for a
constant named `ROLE_HELP`. It was all done on 2026-08-02, and better than
promised — **screenshot-verified live**: `ROLE_HELP` gives every role a plain
sentence with the solver's REAL floors ("Mixed role: no specialisation on
purpose. Just a safety floor, recharge 70%, recovery 40%…"), rendered under the
picker with the numbers beside it; `renderRoleOptions` GROUPS the list per
archetype ("Natural for a Defender" / "Off-role — allowed, but it will fight
you" / "No single focus"); **the Mixed nag is exempted** (`if (role === "mixed")
return;`) so a Generalist no longer earns a warning it could never clear; and
`renderRoleFocusSplit` answers his Corruptor split-attention question with an
actual percentage slider. Sonic Resonance is answered too: Debuffer and Buffer
carry IDENTICAL weights in `ROLE_WEIGHTS` (0.15 / 1.00 / 1.00), so a set that
does both does not force a wrong choice.
⚠ **Lesson, twice today: a grep is a hypothesis.** Run the app before reporting
something missing.

**❌ Still genuinely open:** Troo's "manually selecting enhancements is harder
than it needs to be". ⚠ Unverified: his "low-contrast greys on light blues" — no
contrast audit exists, so do NOT claim it fixed.

✅ Everything else he raised is fixed and waiting on the release: tray, portable
update, tabs, assistant placement, type scale, verbose text, export button,
targeted level, Mighty Leap/Speed of Sound, Panacea. The separate Web3Forms
report (D:\CoH\Homecoming accounts folder) was already fixed 2026-08-03 — the
folder was found and the MESSAGE lied about it.

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
