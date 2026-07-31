# Resume point — 2026-07-31 4:16 PM (laptop closing, resuming at home)

Nothing is running. No scheduled tasks armed. Working tree clean (tracked),
zero unpushed commits, HEAD = `c2265c6b`, master in sync with origin.
Safe to close the lid and pick up anywhere.

**Read `coh-builder/CLAUDE.md` first** — standing rules and verified game facts.
This file is the current state and the open queue.

---

## Joel's work order (given 2026-07-31 afternoon, in this order)

1. ✅ **DONE — fold in the CLAUDE.md staleness.** `c2265c6b`, pushed.
2. ▶ **IN PROGRESS — build the four-way alignment.** Design settled below, ZERO
   code written yet. This is where the next session starts.
3. ⏸ **Close the verdict gate's legality hole.** Not started.

Plus Joel's standing instruction for this batch, in his words:

> **Drive the real app in Edge before claiming anything visual.** Most of my
> errors today came from reading source and asserting what a user would see.

Not optional and not satisfied by a JS probe. It means: dev server up, Edge via
the Chrome connector, click through the actual control, look at it.

---

## Item 1 — what changed in CLAUDE.md (`c2265c6b`)

Four blocks, all the same class: a gate or a hold, discharged, still written in
the present tense.

- The 🛑 engine-accuracy work-order banner ("NO champion work, NO waves, NO
  merges") → marked **CLOSED / freeze LIFTED**; the work order stays on disk as
  the record of what was fixed, it is no longer a gate.
- The ⛔ 2026-07-28 release hold → **discharged**; everything staged shipped in
  0.12.30. The latest-release line (still said 0.12.29) now says 0.12.30, and in
  the hold's place is the defect that is NOT closed — the verdict gate's
  score-only comparison, with Joel's ruling recorded: **legality outranks score.**
- The Journey ruling "the app toggle stays Hero/Villain" → struck through and
  marked **OVERTURNED by Joel 2026-07-31**, with the four-way design and its
  build-neutrality proof written in beside it.
- The v38+HO wave's "NOTHING MERGED / awaits Joel's word" → merged.

CURRENT STATE re-dated 2026-07-31 and given the open queue in Joel's order.

---

## Item 2 — the four-way alignment: everything found, nothing built

**The design (Joel's):** the app toggle becomes 🦸 Hero / 🛡️ Vigilante /
😈 Rogue / 🦹 Villain. Both middles themed the **wizard section's yellow**. Each
gives access to both sides' information. It is **BUILD-NEUTRAL** — verified
game-first: Vigilante is hero-type and Rogue villain-type for the accolade
`activate_requires` gate, so this changes what a user SEES and nothing about
what their build scores.

### The one insight that makes it build-neutral — do not lose this

Everything hinges on **one function**, `charAlignment()` at `static/app.js:5325`.
It currently returns the raw stored value, and it feeds four consumers:

| consumer | line | what it does |
|---|---|---|
| `buildPayload()` | app.js:5676 | sends `alignment:` **to the server** — the engine gates accolades on it |
| `_accInactiveAlign()` | app.js:5161 | greys off-side accolades |
| `_accRow()` | app.js:5174 | the tooltip wording |
| `preselectStandardAccolades()` | app.js:5337 | auto-ticks the standard set |

**So: make `charAlignment()` return `_contentSide(raw)` — hero or villain,
never vigilante/rogue — and every build path stays byte-identical by
construction.** Add a separate `rawAlignment()` for theme and display. That one
change IS the build-neutrality guarantee; everything else is presentation.

`_contentSide()` already exists (app.js:857) and already maps
vigilante→hero, rogue→villain. It is the function to reuse, not to rewrite.

### What already exists (reuse, don't rebuild)

- `_ALIGNMENTS` — app.js:864. All five entries with labels, css classes, tips,
  in Null-the-Gull order. `praetorian` is 🌀 Flashback and is **Journey-only**
  (Praetoria is not startable on Homecoming) — the app toggle takes the **first
  four only**.
- `_contentSide()` — app.js:857. The alignment→content-road map.
- `_journeyAlign()` — app.js:850. Reads `cohAlignment` directly and **already
  handles all four keys**. No change needed; it starts working app-wide for free
  the moment the stored value can be a middle alignment.
- `_alignNote()` — app.js:876. Plain-English sentence per alignment, already
  written for vigilante and rogue.

### What has to change

- `applyAlignment()` — app.js:2232. Today: two theme classes, a hardcoded
  `al === "villain" ? … : …` for name/glyph/tag/title, and it writes
  `cohAlignment`. Needs four keys, theme picked off the **content side**, plus
  the yellow treatment for the two middles.
- `window.toggleAlignment` — app.js:2278. A two-way flip. Needs to become a
  four-way cycle (or a small menu — **ask Joel which he wants**; a 4-cycle
  button is 3 clicks to get back, a menu is one click plus a pick).
- `#alignment-btn` — index.html:236, and its label logic at app.js:2247. ⚠ That
  label was *just* fixed today (it used to eat its own label span); keep the
  `glyph + <span>name</span>` shape.
- Entry cards — index.html:19-22. Two `.align-card` buttons today; the four-way
  probably belongs here too, and `applyAlignment` already syncs their `.on`
  state via `data-align`.
- CSS — style.css:1089-1139 (`body.theme-hero` / `body.theme-villain` and the
  `#alignment-btn` colour pairs). The middles need the wizard yellow.
  ⚠ **Any rule that restyles a button's `background` must restate `color`** —
  the base `button` rule pairs near-black text with the light accent background;
  override only the background and you get 1.27:1. This bit today, measured.
  ⚠ There are already amber-ish alignment colours in the Journey switcher at
  style.css:1835-1836 (`.al-vig` #7fc7e0, `.al-rogue` #e0a63c) — **those are the
  Journey's palette, not necessarily Joel's "wizard yellow"**; find the actual
  wizard section colour before picking (the wizard CSS starts at style.css:743).

### Open question for Joel

Cycle button or small menu for the four-way? Everything else is decided.

---

## Item 3 — the verdict gate's legality hole (not started)

`recert_verdicts` compares **canonical score only**. That is what let 8 of 24
bundled champions ship unbuildable in 0.12.30 (Wall of Force / Misdirection /
Weave held with one pool power where the game wants two): the illegal incumbents
outscored their legal replacements, so the gate "kept" them.

The fix Joel described: run the pool-prereq check over **both sides** and refuse
to supersede with an illegal build. The checker already exists —
`tools/audit_pool_prereq_validator.py` (both arms through the real
/build/validate route, negative-controlled, and its `--champions` mode already
re-derives the illegal list independently). This is wiring an existing check
into the gate, which is the pattern CLAUDE.md already names: *a lesson that
lives only in a docstring is a note — wire it into the thing it protects.*

---

## Still open, needs Joel (unchanged from this morning)

- **❓ Iron Man accolade** — does the Adamant / Iron Man badge actually GRANT its
  power (+10% Max HP, +10 Max End)? The badge is real and game-corroborated;
  only the grant is unverified, and +10/+10 would outsize every documented
  accolade. **One look at a character holding it settles it.** The record STAYS
  until then; do not "clean it up".
- **Posts drafted, not sent** (full text in `session-report.md`): the Homecoming
  forum post for 0.12.30 with a PS announcing hero-companion.com and /pulse, and
  a two-part Discord DM to Guyver.
- **Homecoming Discord announcement** — my read stands: not yet. Eight releases
  in eleven days is a project still stabilising. Wait for the gaming-box install,
  the FP/whitelist submissions, and about a week of quiet.
- **The gaming box has not woken since 2026-07-29 11:51.** Orders unclaimed.
  Check it before any wave counts on it.
- Smaller, offered and not started: `prefers-reduced-motion` (three views animate
  infinitely with no escape hatch), custom easing tokens, a static check for the
  CSS contrast trap, the exploration-log parse (RAM), the strict-dominance
  solver experiment.

---

## Traps recorded 2026-07-31 (each cost something)

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
  Measured, not eyeballed: 1.27:1.
- ⚠ **Never register a scheduled task with a near-future trigger AND call
  `Start-ScheduledTask`** — it double-fires. Cost a duplicate wave on colliding
  shard names (caught before any shard was written).
- ⚠ **Never state a clock time or countdown without a same-turn `Get-Date`.**
  Monitor ticks are not a clock; they queue and lag.
- ⚠ **The tour's mock header is hand-built from the real markup** and drifts
  silently. `audit_tour` checks ids and anchors, NOT copy or mock parity —
  walking the tour is the only way to catch that class.

**The through-line:** almost every error came from asserting what users see
after reading source, or from a single search returning zero. Drive the real app
in a browser (Edge via the Chrome connector — the Claude pane will not composite
frames), measure rather than eyeball, and read whatever prior verification is
attached to data before contradicting it.

---

## How to work here

- Dev copy: `PORT=5080 python server/server.py` in the background, then Edge to
  http://localhost:5080. The installed tray app owns 5000 — never touch it.
- ⚠ Getting into the app requires picking an entry-modal choice; "Continue where
  you left off" → Resume is fastest. Nothing is reachable until you do.
- ⚠ `ACCOLADES_ROWS` and friends are script-scoped, not on `window` — read the
  bare identifier when probing from the console.
- ⚠ Static-file changes need NO restart (F5 on the ROOT url); **server-side
  changes DO** — the server runs `debug=False`.
- Batteries: `tools/demo_single_build_fixes.py` (24 checks, the standing gate),
  `tools/audit_tour.py` (8), `tools/test_plateau_twostep.py` (6), plus
  test_ho_solver / test_proc_trade_note / test_pet_hit_v38 /
  test_mbd_alignment / audit_pool_prereq_validator.
- Waves launch DETACHED via a scheduled task + `launch_hidden.vbs`. Shards are
  the save file. Merge by context with `--verdicts`, never wholesale, and only
  on Joel's explicit word.
- `session-report.md` (outside the repo, never committed) is the outbound
  channel; `ideas.md` is inbound; chat is 10 lines max.
