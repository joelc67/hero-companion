# Game-data converter — plan

Goal: make the **current game data** (not a frozen Mids snapshot) the authoritative
source for `data/*.json`, refreshable each patch, with a reality-check that flags what
drifted. The extraction already works and produces per-category reference data; this doc
scopes turning that into a validated refresh of our whole dataset.

## Already done (banked)
- **Archetype modifiers** — fully reconciled to the live game (0 drift across 1,500
  level-50 values), via `reality_check_gamedata.py` + `tools/gamedata/tables/`.
- **Mastermind ATO slotting** — 37 powers corrected from the extract.

Those two were the confirmed public errors; they're fixed and audited. The rest below is
the bulk migration, done carefully so we don't trade "stale but known" for "fresh but
broken".

## The semantic traps (why this is a converter, not a diff-and-overwrite)

Reality-checking surfaced exactly where a naive sync would corrupt data:

1. **Category-name convention.** The extract names set categories differently from us
   ("Universal Damage Sets" vs our "Universal Damage"), producing ~2,100 phantom
   slotting "diffs" that are pure renames. A category-name map is required before any
   slotting comparison is meaningful. (The MM ATO fix was safe because that one category
   name matches verbatim.)
2. **Conditional mechanics.** Snipes store the *fast* `activation_time` (1.33) plus a
   `requires`/`activate_requires` condition (fast only above a to-hit threshold). Copying
   the number would make every snipe fast-cast unconditionally. Any value with a
   `requires`/mode condition must be interpreted, not copied.
3. **Endurance representation.** ~800 powers show endurance drift with *varying* ratios —
   part real rebalance, part per-AT endurance-modifier application. Needs the modifier
   applied consistently, not a blind overwrite.
4. **Level indexing.** Our per-AT modifier value = level 50 = index 49 of the game's
   105-entry arrays. Confirmed and used by the reality check.
5. **Representation conventions.** Some tables differ on *every* AT (e.g.
   `Melee_Uniqueness` 1.0 vs 100.0) — a units convention, not drift. Rule: all-ATs-differ
   ⇒ convention (leave); a subset ⇒ real drift (fix).

## Phased plan (each phase: convert → diff vs current → re-solve the champion corpus and
## compare stats → run all audits → only then replace)

- **Phase 1 — power slotting rules.** Build the category-name map, then reconcile every
  power's accepted set categories to the game (catches any slotting drift beyond MM ATO).
  Low math risk; validated by the slot-schedule + coherence audits.
- **Phase 2 — power values.** Recharge / endurance / cast / range, *with* the conditional
  handling above (snipes, modes) and the endurance modifier. Validate by re-solving the
  champion corpus and diffing DPS/endurance totals — no build should move except where the
  game genuinely changed.
- **Phase 3 — set bonuses & set data.** From the extracted IO-set (boostset) data; verify
  bonus values and rule-of-5 signatures against our set_bonuses.
- **Phase 4 — flip the source & wire the update-check.** Make the extract the primary
  input, keep Mids only as a cross-check, and surface "game data updated — N values
  drifted" from the reality-check.

## Validation gate (every phase)
1. Structural: converted file loads, same keys/shape our engine expects.
2. Diff vs current data: enumerate every change; a human-readable report.
3. Corpus: re-solve the champion builds; totals must not move except at genuinely-changed
   powers/sets.
4. Audits: epic tiers, slot schedule, gamelog, slotting coherence, reality check — all green.

Nothing replaces live data until its phase clears all four.
