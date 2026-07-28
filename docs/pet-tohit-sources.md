# Pet to-hit facts — wiki-sourced (fetched 2026-07-28, Joel's machine, Edge)

Source pages (Unofficial Homecoming Wiki, read via the real browser after the
site added bot verification that now 403s every scripted fetch path):

- https://homecoming.wiki/wiki/Attack_Mechanics
- https://homecoming.wiki/wiki/Mastermind
- https://homecoming.wiki/wiki/Purple_Patch

These are the TWO facts the client bins are structurally silent on (the summon
templates carry `Ranged_Ones` for every MM tier — swept 8 sets × 3 tiers on
2026-07-28 — and villaindef.bin entity records carry no fixed level). Order of
authority honored: bins searched first and found silent; wiki is the sanctioned
last resort, labelled. Everything below is restated fact, cited to the pages
above.

## 1. Player-summoned pets roll like PLAYERS, not critters

Per Attack_Mechanics ("Pet Accuracy" + "Data Tables"):

- Base hit chance for a player pet follows the PLAYER table (75% vs even), not
  the critter 50% base. Rank-based accuracy multiplier for "player Pet" = 1.00.
- Player-vs-critter base hit by relative enemy level (the table the model
  already holds as `_PLAYER_BASE_VS`, re-confirmed on this fetch):
  −4:95, −3:90, −2:85, −1:80, 0:75, +1:65, +2:56, +3:48, +4:39, +5:30, +6:20, +7:8 (%).
- AccMods for the pet's own attacks = the pet POWER's inherent accuracy
  (client field on every pet attack record — swept 559 MM pet attack exports,
  values 0.8–1.35, mostly 1.0) × (1 + Accuracy enhancement).
- Two-clamp structure unchanged: Clamp(AccMods × Clamp(Base + ToHit − Def)),
  clamps 5–95% both times.
- Beginner's Luck (+ToHit under combat level 20) applies to pets AT THE PET'S
  level — irrelevant at 50, noted for any future leveling-view use.
- Streak breaker: each pet tracks its own — no model impact (expected-value
  math unchanged).

## 2. Mastermind henchman levels (the count-gated rule)

Per Mastermind ("Henchmen vs. Pets"): a henchman power's summon count grows
with MM combat level and the henchmen's level drops as the count grows.
At full strength (MM ≥ 24, the endgame case every scenario models):

| Tier | Count | Level vs MM |
|------|-------|-------------|
| 1    | 3     | −2          |
| 2    | 2     | −1          |
| 3    | 1     | −0          |

This is Combat-Level-gated behavior (the client summon template itself carries
no offset — consistent with the bins sweep). Controller-class pets are separate
and ARE client-pinned: their summon templates carry `Ranged_Levelminus`
(Fire Imps → −1) or `Ranged_Level`/`Ranged_Ones` (→ caster level).

## Consumption (model v38)

Pet hit chance vs a scenario at shift S:
`clamp(acc_inherent × (1 + acc_enh) × clamp(_PLAYER_BASE_VS[S + tier_shift] + tohit_buffs))`
where tier_shift = 2/1/0 for henchman Minion/Lt/Boss classes (wiki-sourced),
1 for Levelminus-template pets (client-pinned), else 0; acc_inherent from the
pet attack record (client); acc_enh from summon-power slotting via copy_boosts
(client); tohit_buffs via the buff_effects routing lever (client: Supremacy
ToHit scale 0.1 × the MM's ToHit table 0.75 = +7.5% as priced, Tactics, etc. —
self_effects-only powers excluded).
