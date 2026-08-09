# Adding Wind Control — the mapping, fully pinned (2026-08-08)

Wind Control is a shipping Homecoming powerset (Controller + Dominator, 10
powers each) that our Mids-derived data does not carry, so the tool cannot plan
it. This is the specification for adding it: **every mapping below was derived
and measured, not assumed**, so the build is mechanical. What is NOT settled is
named at the bottom, and one of it is Joel's call.

## The set (levels are ours, i.e. the client's +1)

| power | L | type | what it is |
|---|---|---|---|
| Clear Skies | 1 | Auto | Self +ToHit, +Rech, +Rec, −EndCost |
| Downdraft | 1 | Click | Hold, −movement, −rech, −fly |
| Updraft | 1 | Click | High DMG(Smashing), Knockup, −fly |
| Breathless | 2 | Click | Targeted AoE, minor Lethal, Immobilize |
| Wind Shear | 6 | Toggle | PBAoE −speed, −fly, −ToHit |
| Thundergust | 8 | Click | Cone, minor Smashing, Knockdown |
| Microburst | 12 | Click | Targeted AoE, minor Smashing, Stun |
| Keening Winds | 18 | Click | Targeted AoE, Confuse, EndDrain |
| Vacuum | 22 | Click | Targeted AoE, Hold, Lethal DoT, **summons** |
| Vortex | 26 | Click | **summons** (the tier 9) |

## The mappings, each with the evidence that pinned it

| field | rule | evidence |
|---|---|---|
| `level_available` | client `available_level` **+1** | the client is 0-based; **5,478 of 5,589** matched powers agree |
| scalars (recharge, endurance, cast, accuracy, radius, arc, max_targets) | client verbatim | same fields Boomerang Slice used |
| `damage_effects` | templates **and `child_effects`**, critter-gated → `pv_mode 1`, player-gated → `pv_mode 2` | the Boomerang Slice pattern; ⚠ `child_effects` is where damage hides |
| `control_effects` | client `scale` → our `scale`, client `magnitude` → our `nmag`, critter group → `pv_mode 1` | **539 powers agree** vs 29 that do not (see the open item below) |
| `control_effects.kind` | by mez name: **hard** = Held, Stunned, Immobilized, Confused, Terrorized, Intangible; **soft** = Knockback, Knockup, Sleep, Repel, Afraid | unanimous across all 5,000+ existing rows — no mez name ever carries both |
| `accepted_set_categor*` | client `allowed_set_categories` → our ids by NAME, with two aliases: **"Universal Damage Sets" → "Universal Damage"** and **"Ranged AoE Damage" → "Targeted AoE Damage"** | derived empirically from powers we already hold: 1,128 and 452 occurrences |
| `summons` | client `entity_def` → our entity key, **normalising underscores** (`Pets_WindControl_Vacuum_Controller` → `Pets_Wind_Control_Vacuum_Controller`) | 570 exact + 7 via normalisation across the existing corpus |
| `power_type` | client `type`: Click → 0, Auto → 1, Toggle → 2 | matches every sibling record |

The pet side already exists: `Pets_Wind_Control_Vacuum_Controller`,
`Pets_Wind_Control_Vacuum_Dominator` and `Pets_Wind_Control_Vortex` are all in
`summons.json`, and `Pets.Wind_Control_Vortex.Hail_of_Debris` is a power we hold.

## ⚠ NOT SETTLED — and the first one is Joel's

1. **The Controller's Vortex pet.** The client distinguishes
   `Pets_WindControl_Vortex_Controller` from `Pets_WindControl_Vortex`; our data
   has **one** Vortex entity. Sharing one entity across Controller and Dominator
   is a documented pattern in this project (the v26 pet work says so
   explicitly), so pointing both at `Pets_Wind_Control_Vortex` is probably
   right — but it is an assumption about the game, on a **tier 9**, and this
   project's rule is that those get ruled on rather than guessed.
2. **Exposing a new powerset is a bigger act than any data patch.** Adding it to
   `powersets.json` makes it selectable, and a mis-priced set is worse than an
   absent one: the solver would optimise into it and the player would trust the
   numbers. That switch should be flipped deliberately, not as a side effect.

## Worth knowing before the build

- **29 existing control powers disagree with the client** on (mez, scale, mag) —
  Hymn of Dissonance reads mag 1 where the client says 3, Entangle 4 vs 3,
  Synaptic Overload's whole ladder is shifted. That is pre-existing drift in
  data we already ship, unrelated to Wind Control, and it deserves its own pass.
- **269 of our `summons[]` entries do not resolve** to an entity in
  summons.json. Most are pseudo-pets (`PL_StaticObject` class), but the number
  has never been classified.

## ⚠⚠ CORRECTION, 2026-08-08: the first Wind Control records were INFLATED

Both archetypes' records shipped earlier the same day counting effect groups
the game gates behind a MODE. Found while adding the Gadgetry and Utility Belt
pools, whose attacks are written once per archetype and so made the same defect
unmissable (Wrist Blaster carries 23 damage groups for one attack).

Two signals separate a real row from a variant, both now read by
`effects_from` and both measured across the whole client:

1. **`tags` is the client's own mode gate, and it always was.** 349 effect
   groups across 342 powers carry `tags: ["FieryEmbrace"]`, plus Containment
   (119), Domination (90), Overpower (86), the Scrapper crit trio, Defiance,
   PowerBoostA/B. ⚠ This **falsifies** the standing note that the crawler was
   not capturing the Fiery Embrace gate: the gate is in the export, in a field
   nothing had read. A tagged group is skipped and COUNTED, never silently.
2. **Targeting is not a condition.** A `requires_expression` mixes "who may
   this land on" with "when does it apply", and only the second makes a group
   conditional. Strike out the pure-targeting clauses (`enttype target>`,
   `entref target.owner>`, `target.isFriend?`, the operators) and 5,123 of the
   7,323 expression-carrying groups reduce to nothing; every residue is a real
   condition (archetype variants, `kMeter`, `Source.Mode?`, random rolls,
   token ownership). Testing for `critter`/`player` alone let all 22 of Wrist
   Blaster's variants through, because they name `critter` or `player` too.

Also corrected in the same pass: **`chance: 0.0` means UNSET**, not "never" —
the crawler writes 0.0 for an absent field, and Poisoned Dagger's -DMG group
reads 0.0 while the game's own short help states the -DMG. Corpus-wide only 64
untagged chance-0 groups exist and every one carries a real, help-stated effect.

Effect of the correction on Wind Control: 18 row-sets changed, all downward
(Breathless 4 damage rows to 1, Vacuum's Lethal DoT to 0 — it is gated on
holding 6 stacks of the set's own Pressure mechanic, which is REPORTED rather
than credited or silently dropped). Champion exposure zero, so no score moved.

⚠ Item 1 of "NOT SETTLED" above is CLOSED: Joel ruled the Vortex entity shared.
