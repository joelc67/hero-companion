# Authoritative game data — reality-check & refresh

Our bulk game data (`data/*.json`) was parsed from a **Mids Reborn** database that
turned out to be ~6 months stale (frozen at DB `2026.1.1242`). A public forum review
(Maelwys, 2026-07-06) caught the symptom: Brute defense read low because the Brute
defense/resist modifiers were bumped 0.075 → 0.085 in a patch our copy never saw.

The fix is to stop trusting a frozen snapshot and check against the **live game client**,
which is the same origin City of Data and Mids are both built from.

## Source of truth

The game client's own binary data, extracted with **Bin Crawler**
(part of [wednesdaywoe/CoH-Planner](https://github.com/wednesdaywoe/CoH-Planner),
which reads the `.pigg` archives via Pigg Wrangler). This is what CoD uses — we just
run it ourselves against the installed client, so there's no scraping or third-party
download in the loop.

`tables/` holds a snapshot of the per-archetype modifier tables (the 15 playable ATs),
extracted from `…/assets/live` on **2026-06-19**.

## Refresh after a game patch

```
git clone https://github.com/wednesdaywoe/CoH-Planner
cd CoH-Planner/tools/bin-crawler
py -m bin_crawler.export_classes  --assets-dir "<CoH>/assets/live" --output-dir out
py -m bin_crawler.export_powers   --assets-dir "<CoH>/assets/live" --output-dir out   # powers, powersets, IO sets
py -m bin_crawler.export_salvage  --assets-dir "<CoH>/assets/live" --output out/salvage.json
py -m bin_crawler.export_entities --assets-dir "<CoH>/assets/live" --output-dir out/entities
```

Copy `out/tables/<playable-at>.json` into `tools/gamedata/tables/`, then:

```
python tools/reality_check_gamedata.py     # lists any archetype modifier that drifted from the live game
```

The reality check compares only **level-independent** (flat) modifiers, where a single
per-AT value is unambiguous. Applying the drift back into `data/modifier_tables.json`
brings us current.

## Status

- **Archetype modifiers:** reality-checked; 10 stale values (Brute/Sentinel/Tanker/Dominator)
  corrected from the 2026-06-19 extract. `reality_check_gamedata.py` = 0 stale.
- **Still to migrate to the game-extract source:** powers, powersets, IO-set slotting
  rules (incl. the Mastermind ATO change), and level-scaling tables. The extraction for
  all of these already works (see refresh commands above); the converter to our schema
  is the remaining work.
