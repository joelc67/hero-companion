# Authoritative game data — reality-check & refresh

Our bulk game data (`data/*.json`) was parsed from a **Mids Reborn** database that
turned out to be ~6 months stale (frozen at DB `2026.1.1242`). A public forum review
(Maelwys, 2026-07-06) caught the symptom: Brute defense read low because the Brute
defense/resist modifiers were bumped 0.075 → 0.085 in a patch our copy never saw.

The fix: stop trusting a frozen snapshot and reality-check against the **live game
client**, which is the same origin City of Data and Mids are both built from.

## Source of truth

The game client's own binary data (`bin.pigg` / `bin_powers.pigg` under
`<CoH install>/assets/live`), extracted with the community's open tooling —
**[Bin Crawler + Pigg Wrangler](https://github.com/wednesdaywoe/CoH-Planner)** (Bin
Crawler parses the Cryptic `.bin` records; Pigg Wrangler reads the `.pigg` archives).
This is exactly what City of Data is generated from — we just run it ourselves against
the installed client. The snapshots in this folder are current as of **2026-06-19**:

- `tables/` — per-archetype modifier tables (15 playable ATs)
- `power_values.json` — every power's recharge / endurance / cast / range / set categories
- `setbonuses.json` — all 227 IO sets' bonus tiers and values

## Refresh after a game patch

```
git clone https://github.com/wednesdaywoe/CoH-Planner
cd CoH-Planner/tools/bin-crawler
py -m bin_crawler.export_classes --assets-dir "<CoH>/assets/live" --output-dir out
py -m bin_crawler.export_powers  --assets-dir "<CoH>/assets/live" --output-dir out
```

Copy `out/tables/<playable-at>.json` into `tables/`, and regenerate `power_values.json` /
`setbonuses.json` (the boostset+powers parsers give set bonus tiers -> `Set_Bonus.*`
powers -> effect values). Then run the reality checks:

```
python tools/reality_check_gamedata.py      # archetype modifiers
python tools/reality_check_powers.py        # power values + set slotting
python tools/reality_check_setbonuses.py    # IO set bonuses
```

Each is report-only; review the drift, then apply it back into `data/*.json`.

## Status (2026-07-06 — all reconciled to the live game)

- **Archetype modifiers:** 0 drift (10 stale fixed: Brute/Sentinel/Tanker/Dominator).
- **Power values:** recharge/endurance/range/cast synced (snipe conditional casts held aside).
- **Set slotting:** category-name map built; game-allowed categories added (incl. Mastermind ATO).
- **Set bonuses:** verified current (defense/HP/recovery/recharge/regen match exactly; damage-buff
  is a known ×2.5 representation convention, left as-is).

## Representation conventions (differ from the raw game values on purpose — do NOT "fix")

- `Melee_Uniqueness`: our `1.0` vs the game's `100.0` (all archetypes).
- Damage-buff set bonuses: our value = game "Strength" scale × 2.5.
