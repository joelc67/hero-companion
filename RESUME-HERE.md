# Resume point — 2026-07-31 4:09 PM (handoff to a new session)

Nothing is running. No scheduled tasks armed. Working tree clean, zero
unpushed commits, HEAD = `b594ea7f`. Safe to start fresh.

**Read `coh-builder/CLAUDE.md` first** — it carries the standing rules and the
verified game facts. This file is only the current state and the open queue.

---

## Where the project stands

**Shipped today: v0.12.30 "Accuracy pass"** —
https://github.com/joelc67/hero-companion/releases/tag/v0.12.30
Both assets signed, API-verified. Model v38, game data 2026.1.1242 unchanged.

**The engine-accuracy work order is COMPLETE.** Items 1-6 all done:
prerequisites now come from the game's own `requires` expression (467 of 467,
zero held), the user-facing validator checks pool prerequisites, the tie-break
plateau is fixed with a two-stage/eps solve plus physics arbitration, and the
whole 24-champion roster was re-certified — 8 supersede, 16 keep, all merged.

**The release caught a real defect on the way out**, worth knowing because it
shows the gates working: 8 of 24 bundled champions could not be built in game
(Wall of Force / Misdirection / Weave held with one pool power where the game
wants two). The verdict gate had "kept" them because it compares SCORE ONLY and
the illegal incumbents outscored their legal replacements. Joel's ruling:
legality outranks score. Fixed, gold went 16/24 -> 24/24 SERVED.
⚠ **The verdict gate still has no legality dimension** — worth closing before
the next wave.

---

## Open — needs Joel

1. **The four-way alignment** (designed, not built). Joel wants the app toggle
   to become 🦸 Hero / 🛡️ Vigilante / 😈 Rogue / 🦹 Villain, with both middle
   choices themed the **wizard section's yellow**, giving access to both sides'
   information. **It is BUILD-NEUTRAL** — verified: Vigilante is hero-type and
   Rogue villain-type for the accolade activation gate, so this changes what a
   user SEES and nothing about what their build scores. The four alignments
   already exist Journey-local (`_ALIGNMENTS`, `_contentSide()` in app.js) with
   exactly this model; the work is promoting them app-wide.
   ⚠ This overturns a prior ruling in CLAUDE.md ("the app toggle stays
   Hero/Villain; the Journey's 5-way is PREVIEW only") — Joel has knowingly
   changed his mind, so update that note when the work lands.

2. **❓ Iron Man accolade — the one open game question.** Does the Adamant /
   Iron Man badge actually GRANT its power (+10% Max HP, +10 Max End)? The
   BADGE is real and game-corroborated (badge id 10 `Adamant`, villain display
   `Iron{Hero.gender=male man|woman}`). Only the power grant is unverified, and
   +10/+10 would outsize every documented accolade. **Joel's in-game check
   settles it** — a character holding the badge either shows the HP/End bump or
   does not. The record STAYS until then; do not "clean it up".

3. **Posts drafted, not sent** (full text in `session-report.md`): a Homecoming
   forum post for the 0.12.30 release with a PS announcing hero-companion.com
   and /pulse; and a two-part Discord DM to Guyver.

4. **Homecoming Discord announcement** — Joel asked whether the app is stable
   enough. My read: not yet. Eight releases in eleven days is a project still
   stabilising, and 0.12.30 changed build outputs substantially. Wait for the
   gaming-box install, the FP/whitelist submissions, and ~a week of quiet. If
   0.12.30 needs no follow-up, that silence is the evidence. Announce Companion
   Lite separately and later — its consent story needs room a Discord scroll
   will not give it.

5. **The gaming box has not woken since 2026-07-29 11:51.** Its order sat
   unclaimed 4h15m overnight and its six contexts were run on the laptop
   instead. Check it before any wave counts on it.

6. Smaller, offered and not started: `prefers-reduced-motion` (three views
   animate infinitely with no escape hatch), custom easing tokens, a static
   check for the CSS contrast trap below, the exploration-log parse (RAM), and
   the strict-dominance solver experiment.

---

## What changed in the UI today (design pass, eyes on the running app)

Joel installed the emilkowalski design skills and asked for a real evaluation.
Shipped: `9f18f52d`, `1ace58c3`, `99f926f0`, `f775c194`, `b594ea7f`.

- **Bug reporting meets people at the failure.** "Report this" now appears on
  real breakages (unreadable file, import threw, import refused, respec preview
  failed) and opens the form pre-filled with the actual error. Deliberately NOT
  on validation output — a build the game would refuse is the app working
  correctly, and inviting reports there would poison the signal.
- **Every header control carries its name**: Journey · Tour · Save │ Guide ·
  Report │ Champion · Updates · Villain · Switch, grouped by hairline.
- **"Partial set"** got its own colour and its own ◎ glyph (it had NO css rule
  at all and fell through to the neutral fallback, sharing 🎯 with "Full set").
- **Power-card controls**: `−`/`+` are one segmented stepper; ✕ (which deletes a
  power with no confirm) moved 2px -> 10.5px clear, quiet at rest, red on hover.
- **Alignment is a perspective, not an edit**: switching sides no longer DELETES
  the other side's ticked accolades. They stay remembered, render greyed +
  disabled + "hero-side only", and contribute zero because the engine gates them.
  Verified live: tick 3 hero accolades -> switch to villain -> all 3 remembered
  and inert -> switch back -> all 3 live again.

---

## Traps recorded today (each cost something)

- ⚠ **`activate_requires` is a DIFFERENT field from `requires`.** Accolades gate
  at runtime on `type char> hero|villain eq`. I reported "both sides stack, pool
  doubles" from `requires`/`num_allowed`/no-mutex and was wrong — you can EARN
  and HOLD both sides, but only your current side's APPLY. `engine.py:602-620`
  already had this right since 2026-07-17.
- ⚠ **Badge displays carry gender templates.** Iron Man is stored as `Adamant`
  with villain display `Iron{Hero.gender=male man|woman}`, so a substring search
  for "iron man" returns zero. I reported "no such badge in 2,396 records" off
  that and recommended dropping a real badge.
- ⚠ **Any CSS rule that restyles a button's `background` must restate `color`.**
  The base `button` rule pairs near-black text with the light accent background;
  override only the background and you get 1.27:1. Measured, not eyeballed.
- ⚠ **Never register a scheduled task with a near-future trigger AND call
  `Start-ScheduledTask`** — it double-fires. Cost a duplicate wave on colliding
  shard names (caught before any shard was written).
- ⚠ **Never state a clock time or countdown without a same-turn `Get-Date`.**
  Monitor ticks are not a clock; they queue and lag.
- ⚠ **The tour's mock header is hand-built from the real markup** and drifts
  silently. `audit_tour` checks ids and anchors, NOT copy or mock parity —
  walking the tour is the only way to catch that class.

**The through-line, worth stating plainly:** almost every error today came from
asserting what users see after reading source, or from a single search returning
zero. Drive the real app in a browser (Edge via the Chrome connector — the
Claude pane will not composite frames), measure rather than eyeball, and read
whatever prior verification is attached to data before contradicting it.

---

## How to work here

- Dev copy: `PORT=5080 python server/server.py` in the background, then Edge to
  http://localhost:5080. The installed tray app owns 5000 — never touch it.
- ⚠ Getting into the app requires picking an entry-modal choice; "Continue where
  you left off" -> Resume is fastest. Nothing is reachable until you do.
- ⚠ `ACCOLADES_ROWS` and friends are script-scoped, not on `window` — read the
  bare identifier when probing from the console.
- Batteries: `tools/demo_single_build_fixes.py` (24 checks, the standing gate),
  `tools/audit_tour.py` (8), `tools/test_plateau_twostep.py` (6), plus
  test_ho_solver / test_proc_trade_note / test_pet_hit_v38 /
  test_mbd_alignment / audit_pool_prereq_validator.
- Waves launch DETACHED via a scheduled task + `launch_hidden.vbs`. Shards are
  the save file. Merge by context with `--verdicts`, never wholesale, and only
  on Joel's explicit word.
- `session-report.md` (outside the repo, never committed) is the outbound
  channel; `ideas.md` is inbound; chat is 10 lines max.
