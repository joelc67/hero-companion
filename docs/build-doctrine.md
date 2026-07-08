# CoH Build Doctrine — Damage / Fire-Farm (Brute-centric, extensible)

**Purpose:** the COMPLETE picture of what makes a great damage/farm build, so the
planner builds *correctly* instead of experimentally. This is the spec the solver,
autopicker, and incarnate recommender must satisfy. Implement against this — don't
patch ad hoc.

**GOVERNING PRINCIPLE (Joel, 2026-07-08): every build is unique unto itself.**
All builds draw from one shared pool of game-engineered rules — the physics, the
slot schedule, ED, PPM, the rule of five never bend. But within that scope the
planner must treat each archetype + powerset + play-style combination as its own
problem with its own perfect answer: what a Bots/Marine team Mastermind's slots
serve is not what a Katana/Regen soloist's serve. One-size-fits-all templates
(fixed pool picks, uniform slot shapes, role-blind targets) are the enemy; the
rules are universal, the build is not.

**Confidence tags** — please audit these, Joel:
- `[✓TW]` proven by your TW/Fire master · `[✓RAD]` proven by your Rad/Fire master
- `[THEORY]` established CoH knowledge, NOT yet seen in your builds — **confirm or correct**
- `[?]` I'm unsure — **needs your ruling**

---

## 0. The core failure the tool keeps making
The engine only totals SURVIVAL stats (def/res/rech/hp), so the solver optimizes survival
and merely *fills* offense. A great build optimizes **both**. Damage throughput =
**base damage** (sets/+dmg) + **procs** (fixed dmg, loves recharge) + **-resistance**
(spawn-wide multiplier) + **uptime** (recharge → more attacks/aura ticks). The tool
currently sees only the first and ignores the other three. `[✓TW][✓RAD]`

---

## 1. Power selection
- Take **every damage aura**: Blazing Aura (Fiery Aura) + the primary's aura
  (Irradiated Ground / Quills / Death Shroud / Lightning Field). These are the farm engine. `[✓RAD]`
- Take **Burn** — the top fire-farm patch. `[✓TW][✓RAD]`
- Take the primary's **big AoEs** (Atom Smasher, Whirling Smash, Arc of Destruction…). `[✓TW][✓RAD]`
- **Damage enablers**: Build Up / Fiery Embrace / Fusion — always. `[✓TW][✓RAD]`
- **Epic by NEED, not a fixed pick:**
  - Endurance-hungry proc build → **Energy Mastery** (Conserve Power + Physical Perfection). `[✓RAD]`
  - Want spawn-wide -res + a nuke → **Pyre Mastery** (Melt Armor + Fire Ball). `[✓TW]`
  - Always grab the epic's **AoE** (Fire Ball / Energy Torrent) as another proc vehicle. `[✓RAD]`
  - **NEVER** take single-target control epics (Ring of Fire, Char) on a farmer. `[✓TW][✓RAD]`
- **Survival**: shields, Tough/Weave, Healing Flames. `[✓TW][✓RAD]`
- **Pools**: Speed (Hasten), Fighting (Tough/Weave), Leadership (**Maneuvers** for def +
  LotG mule `[✓RAD]`; or **Assault** for +dmg `[THEORY]`), Leaping (CJ / LotG mule). `[✓RAD]`

---

## 2. Slotting strategy — decided by each power's JOB
- **Survival powers** (shields, Tough, Weave, Maneuvers, Health) → **set bonuses**:
  resist sets (Aegis, Unbreakable Guard), def sets (LotG, Shield Wall, Reactive Defenses),
  and the unique globals (Steadfast +def, Gladiator's Armor +def, Shield Wall +res, LotG +rech). `[✓TW][✓RAD]`
- **Damage vehicles** (damage auras + big AoEs) → **PROC-BOMB** (see §3). `[✓TW][✓RAD]`
- **Key hard-hitters** → **purple sets** (Hecatomb ST, Armageddon AoE, Ragnarok ranged AoE)
  for damage + recharge + their own proc; or **ATOs** (Brute's Fury, Unrelenting Fury). `[✓TW][✓RAD]`
- **Heal** (Healing Flames) → Panacea / Doctored Wounds / Preventive Medicine. `[✓RAD]`
- **Endurance** → Performance Shifter +End + Power Transfer (Stamina), Panacea (Health). `[✓RAD]`
- A weak attack with no set is fine as a **global mule** (1 proc, or LotG/Kismet). `[✓TW][✓RAD]`

---

## 3. Proc-bombing — the #1 damage lever (currently 0% implemented)
**Mechanic:** a power can hold **one %Damage proc per DISTINCT accepted set-category**
(each is a different set's unique → no rule-of-5 clash). More accepted categories = more
procs. `[✓RAD]`
- Atom Smasher accepts 6 categories → **6 procs**; Irradiated Ground (PBAoE + Defense
  Debuff) → **5**; Blazing Aura → **4**. `[✓RAD]`
- **CONTROL powers are proc vehicles too** `[✓FTA]`: AoE controls accept their control
  category (Holds / Immobilize / Stuns) **plus Targeted-AoE-Damage + Universal-Damage + the
  Controller ATO** → 4-5 procs each (Flashfire, Fire Cages, Acid Arrow, Char). On a
  **Controller this proc damage lands DOUBLED via Containment** — it IS the controller's
  primary damage engine (low base damage scalar 30.6, but Containment + procs make controls
  hit hard). Debuff powers (Acid Arrow) are proc vehicles for the same reason.
- **PPM rule** `[THEORY — confirm]`: proc chance per activation ≈ `PPM × (recharge + 0.25×AoE_radius_factor) / 60`,
  capped 90%; pulsing auras use a ~10s effective period. ⇒ high-recharge AoEs and
  constant auras are the best proc homes.

**Proc catalog by category** (which set's %Dam proc fits where) — audit/extend:
| Category | %Damage procs |
|---|---|
| PBAoE Damage | Scirocco's Dervish (Lethal), Eradication (Energy), Obliteration (Smashing), **Armageddon** (Fire, purple) `[✓RAD]` |
| Targeted AoE Damage | Positron's Blast (Energy), Bombardment (Fire), **Annihilation (-Res!)** `[THEORY]` |
| Melee Damage | Touch of Death (Negative), Mako's Bite (Lethal), **Hecatomb** (Neg, purple) `[✓RAD]` |
| Defense Debuff | Touch of Lady Grey (Negative) `[✓RAD]`, **Achilles' Heel (-Res!)** `[✓PAIN]` |
| Accurate Defense Debuff | Shield Breaker (Lethal) `[✓RAD]` |
| Threat Duration (taunt) | Perfect Zinger (Psi) `[✓RAD]` |
| To-Hit Debuff | Cloud Senses (Energy) `[THEORY]` |
| Brute ATO | Brute's Fury, Unrelenting Fury `[✓RAD]` |

**-Resistance procs** (spawn-wide force multipliers — go in auras / AoEs / -def debuffs) —
ALL now confirmed across builds: Achilles' Heel (-20% res, Defense Debuff) `[✓PAIN]`,
Fury of the Gladiator (-res, in Quills aura) `[✓TW][✓SPINES]`, Annihilation (-res, Targeted
AoE) `[✓MAR]`.

---

## 4. Incarnates — by build + content (resolve the tensions)
- **Alpha** = decided by which DAMAGE SOURCE DOMINATES (not just "any procs"):
  procs are the *primary* damage (proc-bombed auras carrying the build) → **Spiritual**
  (recharge = more proc cycles) `[✓RAD]`; **base attack damage** dominates (even WITH some
  proc-bombed AoEs) → **Musculature** `[✓TW][✓FFB]` (the master Fire/Fire proc-bombs Inferno
  & FSC yet runs Musculature, because its base blasts are the bulk of its damage);
  endurance-starved → Cardiac `[THEORY]`.
- **Hybrid**: Assault (sustained +dmg) or Melee (survival + dmg). `[✓RAD = Melee]`
- **VALIDATED "general damage" loadout** (non-farm ranged/melee, seen on BOTH the Fire
  Blaster and Ice Sentinel): **Musculature / Assault / Degenerative / Ageless**. Use as the
  default damage-incarnate set outside fire-farm content. `[✓FFB][✓ICE]`
- **Interface** = CONTENT-dependent (NOT universally Reactive — corrected by `[✓FFB]`):
  **Reactive** (-res + fire DoT) for trash/farm clear; **Degenerative** (-max-hp / -regen)
  for hard targets / AV / general play (the master Fire/Fire ran Degenerative). `[✓FFB]`
- **Destiny**: Ageless (rech + end, pairs with proc/recharge — master FFB ran it) or Barrier (survival). `[✓FFB partial]`
- **Judgement**: any AoE (Pyronic/Ion) for burst clear. `[THEORY]`
- **Lore**: any (pets = free dmg). `[THEORY]`

---

## 5. Survival floor, THEN redirect to damage
Fire farm: cap **Fire resistance** (90% brute) + high S/L res; soft-cap melee/ranged/AoE
def where possible; Healing Flames + auras for the rest. Hit the floor FIRST, then every
remaining slot/incarnate goes to offense. `[✓TW][✓RAD]`

---

## 6. Mechanics to respect
- **Fury** (brute): attacks must LAND + chain → accuracy matters; never taunt-mule an attack. `[✓TW]`
- **Momentum** (Titan Weapons): wind-up tax; TW is burst, not constant-pulse → a weaker *farmer* than aura sets. `[✓TW]`
- **ED**: dmg/acc/rech enhancement caps ~95%; Alpha + procs go past ED. `[THEORY]`
- Rule-of-5, unique-once, 4-pool cap, 67 added slots. `[✓TW][✓RAD]`

---

## 7. Implementation map (what each rule touches)
- §1 power picks → `server.py` `_auto_pick_powers` / `_pick_epic` / `_ps_priority`
- §2–3 slotting + procs → `solver.py` (new proc-pass + proc catalog) + `engine.py` (proc-dmg PPM model)
- §3 -res + aura dmg → `engine.py` pseudo-pet/linked-power damage fix
- §4 incarnates → `ai_build.py` `recommend_incarnates`
- §5 targets → `ai_build.py` presets
- A trustworthy "this build underperforms" **warning** becomes possible only once §3 dmg is modeled.

---

## 8. Control / Support / UNIVERSAL techniques — MEASURED from 25+ masters (2026-06-30)
Imported every .mbd via `/build/import` and read the actual slotting top-to-bottom. These are
**observed across nearly every modern master**, not theory. `[✓MEASURED]` = seen in many builds.

**8.1 Reconciliation — what the masters DON'T do (corrects my prior assumptions):**
- Support/control ATs do **NOT softcap defense** — they run **~25–36% def** (plant-poison 32, fire-ta 32,
  emp-fire 35, pain-storm 35) and let **debuffs + control** carry survival. The def-toggle epic lands them
  at ~30, not 45. The tool already hits 38–44 — it was OVER-defending. `[✓MEASURED]`
- Recharge varies **49→99** with no single target; plant-poison master is **48%**. The "recharge gap" was a phantom. `[✓MEASURED]`

**8.2 UNIVERSAL slotting (every AT):**
- **Fitness fully slotted** — Health = Panacea + Numina + Miracle (+Preventive Medicine/Regen Tissue);
  Stamina = Performance Shifter + Power Transfer (×1–2 each). The recovery/regen/+End engine. `[✓MEASURED]`
- **INHERENT POWERS AS MULES** — **Brawl** is slotted with a damage proc OR a full set (Gladiator's Strike proc,
  Hecatomb ×5, S.Blistering Cold ×6, Touch of Death) for free bonuses; Sprint → Celerity. The tool NEVER does
  this. This is "inherent powers exploited for needs." `[✓MEASURED]`
- **PROC-BOMB everything that pulses/AoEs** — auras, AoE attacks, AND **AoE controls** (Fire Cages, Flashfire,
  Stone Cages, Cinders, Choking Cloud, EMP Arrow) — on a controller this is Containment-doubled = the damage. `[✓MEASURED]`
- **-Res procs FIRST** on debuffs/AoEs/auras — Achilles' Heel, Fury of the Gladiator, Touch of Lady Grey,
  Annihilation, Shield Breaker. Often **DOUBLE-layered** (ToLG + Achilles on one power). `[✓MEASURED]`
- **WINTER sets harvest def+recharge+recovery from ATTACK/CONTROL slots** — S.Winter's Bite & S.Blistering Cold
  on ranged/ST attacks, S.Frozen Blast & S.Avalanche on AoEs. This is how a squishy gets def+recharge WITHOUT
  spending survival slots. The single most common set in the masters. The tool picks control sets instead. `[✓MEASURED]`
- **ATOs** (Superior <AT>) on signature powers, often **SPLIT across pets** (MM: S.Mark of Supremacy +
  S.Command of the Mastermind across 3 henchmen). `[✓MEASURED]`
- **PET sets on pets/henchmen** — Mark of Supremacy, Sovereign Right, Edict, Commanding Presence, Call to Arms,
  Expedient Reinforcement, Command of the Mastermind. (Tool wrongly gave Fly Trap a debuff set.) `[✓MEASURED]`
- **Hami-Os on toggle debuffs / buff toggles / utility** — Radiation Infection, Darkest Night, Tactics, Focused
  Accuracy, Farsight, Flash Arrow, Aim, Fortitude — dual-aspect (Acc/DefDebuff, Acc/ToHit) in 1–3 slots. `[✓MEASURED]`
- **Def toggle slotting is FIXED**: Weave / Scorpion Shield → **LotG ×4 + Reactive Defenses + Shield Wall**. `[✓MEASURED]`
- **Heal/buff/recovery powers** → Panacea ×5, Power Transfer ×6, Preventive Medicine ×6, Numina ×6 (Recovery
  Aura, Adrenalin Boost, the Circuits, Temporal Mending, Repair). `[✓MEASURED]`

**8.3 Squishy SUPPORT/CONTROL epic = the DEFENSE TOGGLE** — Scorpion Shield (Mace) almost universally
(dark-elec, earth-rad, fire-ta, emp-fire), slotted LotG ×4. Lands ~30 def w/ Weave + Winter bonuses. `[✓MEASURED]`

**8.4 TOOL GAPS vs masters:** ~~the exact Fitness uniques~~ ✅ DONE 2026-06-30 (Principle 1, global arm) —
added Performance Shifter +End, Power Transfer, Panacea to `engine.PIECE_GLOBALS` (the tool was BLIND: no
parseable FX). Master plant-poison re-measured rec 85→100 / regen 76→93; solver now places them in Stamina.
Values CONSERVATIVE `[ESTIMATE — audit vs Mids]`. STILL TODO: Brawl/Sprint inherent mules · Winter-set harvest ·
-Res double-proc layering · Hami-O dual debuffs · pet sets on pets · ATO-split on pets.

---

### Open questions for Joel (so the doctrine isn't itself experimental)
1. `[?]` -Res: how much does a farmer prioritize -res procs (Achilles/FotG/Annihilation) vs pure %Dam procs? Your Rad build leaned %Dam; your TW build had one FotG -res.
2. `[?]` Interface — is **Reactive** the near-universal farm pick, or do you vary it?
3. `[?]` Is the PPM formula above right, or do you slot procs by feel/rules-of-thumb?
4. `[?]` Any sets/procs missing from the §3 catalog that you always use?
