# CoH Archetype Doctrine — what each AT *is* and why it's unique

**Purpose:** the planner can't reason about good builds without understanding archetype
identity. This captures it. Companion to `build-doctrine.md`.

**Confidence tags:** `[✓DATA]` = pulled from the tool's own modifier tables (rigorous,
not opinion) · `[THEORY]` = established CoH knowledge, **Joel please confirm/correct** ·
`[?]` = unsure.

---

## 1. The mechanic that explains everything: ARCHETYPE MODIFIERS
The same powerset performs **differently on different ATs** because every effect is
`base_scale × the AT's modifier for that effect type`. An AT is essentially a *profile of
modifiers* + a damage/res cap + an inherent power. This is why "who should take Empathy"
has a real answer, not a vibe. `[✓DATA]`

### The numbers (lvl-50 scalars, magnitudes — straight from `modifier_tables.json`) `[✓DATA]`
| AT | MeleeDmg | RangedDmg | Heal | Buff-Def | Debuff-Def | Dmg-Cap | Res-Cap |
|---|--:|--:|--:|--:|--:|--:|--:|
| Blaster | 55.6 | **62.6** | 96.4 | 0.070 | 0.070 | 5.0 | .75 |
| Scrapper | **62.6** | 27.8 | 96.4 | 0.075 | 0.075 | 5.0 | .75 |
| Sentinel | 61.2 | 61.2 | 96.4 | 0.070 | 0.070 | 5.0 | .75 |
| Dominator | 58.4 | 52.8 | 117.8 | 0.085 | 0.100 | 4.0 | .75 |
| Stalker | 55.6 | 33.4 | 96.4 | 0.075 | 0.075 | 5.0 | .75 |
| Brute | 41.7 | 41.7 | 96.4 | 0.075 | 0.075 | **7.0** | **.90** |
| Corruptor | 41.7 | 41.7 | 96.4 | 0.085 | 0.075 | 5.0 | .75 |
| Tanker | 52.8 | 44.5 | 96.4 | **0.100** | 0.070 | 5.0 | **.90** |
| Controller | 30.6 | 30.6 | 117.8 | 0.090 | 0.100 | 4.0 | .75 |
| Mastermind | 30.6 | 30.6 | 117.8 | 0.090 | 0.100 | 4.0 | .75 |
| **Defender** | 30.6 | 36.1 | **133.9** | **0.100** | **0.125** | 4.0 | .75 |
| Peacebringer | 47.3 | 44.5 | 96.4 | 0.075 | 0.090 | 4.0 | .85 |
| Warshade | 47.3 | 44.5 | 96.4 | 0.075 | 0.090 | 4.0 | .85 |
| Widow (VEAT) | 55.6 | 55.6 | 80.3 | 0.100 | 0.075 | 4.0 | .85 |
| Soldier (VEAT) | 55.6 | 55.6 | 80.3 | 0.100 | 0.075 | 4.0 | .85 |

**Reading it:** damage ATs cap at 5.0 (Brute 7.0 via Fury); only Brute/Tanker reach the
.90 res cap. Defender owns the support columns (Heal 133.9, Buff 0.100, Debuff 0.125).

### ⭐ Your Empathy question, answered with data `[✓DATA]`
Heal scalar: **Defender 133.9 > Controller / Mastermind / Dominator 117.8 > everyone
else 96.4 > VEAT 80.3.** The identical Empathy power heals **~14% more** on a Defender
than a Controller, **~39% more** than a Corruptor/Scrapper. Same story for buffs (0.100 vs
0.085) and debuffs (−0.125 vs −0.075). Defender is *mechanically* the best at any
buff/debuff/heal set it shares — that's not preference, it's the modifier table.

---

## 2. The game's four effect pillars (how power "paths" work) `[THEORY]`
- **Offense** — damage (S/L/F/C/E/N/Psi/Tox types), delivered as burst, **DoT**, or
  **procs** (fixed, PPM-based). Scales with the AT damage scalar + caps + inherent.
- **Defense layer** — *Defense* (chance to be missed, soft-cap 45%) vs *Resistance*
  (damage reduction, capped .75/.85/.90 by AT). Two independent walls; best builds stack both.
- **Buffs** — raise allies' def/res/dmg/rech/to-hit/regen/recovery. Scaled by Buff modifier.
- **Debuffs** — lower enemies' def/res/to-hit/regen/dmg/speed. Scaled by Debuff modifier.
  **-Resistance and -Regen are the strongest team/AV levers in the game.**
- **Control** — mez (hold/stun/sleep/immob/confuse/fear/KB) + duration/magnitude. Bosses
  need stacked magnitude; controllers/doms specialize.

A great build commits to **≥1 pillar hard** and supports a second; trying to do all four
equally = mediocre at all.

---

## 3. Per-archetype identity (inherent + what it's FOR)
Scalars `[✓DATA]`; inherents/identity `[THEORY]` — confirm.

**DAMAGE / MELEE**
- **Scrapper** — *Critical Hit*. Highest melee scalar (62.6) + crits. Solo king, self-sufficient
  (armor secondary). `[✓SPINES]` Validated by Spines/Invuln: layered self-mitigation (S/L res ~70%,
  regen ~135%, softcap def via Invincibility+LotG) + a **proc-bombed Quills damage aura carrying
  Fury of the Gladiator -Res**. Path: single-target & AoE damage. Less team utility.
- **Brute** — *Fury* (build to +200% dmg by attacking). 41.7 base but **7.0 dmg cap + .90 res cap** → tanky bruiser. The **farm/aggro** AT. Path: sustained AoE + survivability.
- **Tanker** — *Gauntlet* (taunt aura, hits a wider radius). .90 res, **0.100 buff**, best survival + good AoE reach. Path: hold aggro, survive anything, surprising AoE.
- **Stalker** — *Assassination/Hide*. Burst single-target (Assassin Strike + crits from Hide), stealth. Path: ST assassination, ambush; weaker sustained AoE.

**RANGED**
- **Blaster** — *Defiance* (keep attacking even mezzed; dmg buff from attacks). **Highest ranged (62.6)** + a *Support/Manipulation* secondary for utility. Glass cannon. Path: ranged burst + DoT.
- **Sentinel** — *Opportunity*. Ranged **with a real armor secondary** — the defining
  difference from a Blaster. `[✓ICE]` A master Ice/SR sits at **~35-37% melee/ranged/AoE
  defense + Practiced Brawler mez protection + SR scaling-resist** → durable & survivable
  solo with little fuss, where a Blaster must scrape a layered floor. The trade is a lower
  damage **ceiling** (ST-DPS ~121, mid-tier; AoE strong but the engine under-reads rain/proc
  powers). **Niche = durable ranged / comfort solo**: trades the Blaster's damage ceiling for
  a survivability floor. Not a handicap — a different risk/reward. `[✓ICE]`

**SUPPORT / CONTROL**
- **Defender** — *Vigilance* (more buff/less end cost as team gets hurt). **Top buff/debuff/heal
  scalars in the game.** Support primary + ranged secondary. `[✓PAIN]` Validated by Pain/Storm:
  heals → Panacea/Preventive Medicine, regen aura + ally buffs (Painbringer) → self-buffs to
  +127% regen, team +res via World of Pain; the -def debuff (Anguishing Cry) carries the
  **Achilles' Heel -Res proc** force-multiplier. A *solo* Defender leans offense incarnates
  (Musculature/Assault) + Scorpion Shield + blast-secondary procs to self-sustain. Path: team
  force-multiplier (buffs + -res/-regen trivialize hard targets); solo = slow but self-sufficient.
- **Corruptor** — *Scourge* (bonus damage scaling as targets drop below ~50% hp). Damage primary + support secondary, **0.085 buff** (below Defender). Path: damage **and** debuff — the best "selfish support," strong solo + team.
- **Controller** — *Containment* (DOUBLE damage to mezzed targets). Control primary + buff/debuff
  secondary; low damage scalar (30.6) but Containment + **proc-bombed controls** = real damage,
  and perma-control = safety. **117.8 heal, 0.090 buff.** `[✓FTA]` Validated by Fire/Trick Arrow:
  damage engine = procs in Flashfire/Fire Cages/Char ×Containment; survival = control lockdown +
  -ToHit debuffs (Flash/Smoke Arrow) + **Scorpion Shield** (Mace epic +def) + Weave/Maneuvers +
  perma-recharge (Hasten+Ageless); incarnates **Nerve / Control / Degenerative / Ageless**. Path:
  lock the spawn + buff/debuff force-multiply. Premier team safety.
- **Mastermind** — *Supremacy* (pets near you hit harder). Pets ARE the damage; support secondary
  (0.090 buff). `[✓MM]` Validated by Beasts/Rad + Bots/Time: pets slotted with the pet ATOs
  (Mark of Supremacy + Command of the Mastermind) + Expedient Reinforcement; survival = pet
  bodyguard + Tough/Weave/epic armor + Scorpion-type shield; Alpha varies (Agility for def/rech
  vs Musculature for pet damage). Path: pet army + buff/debuff. Strong solo & team.
- **Dominator** — *Domination* (perma → mez bosses + mez protection). Control primary + **Assault**
  secondary (58.4 melee — strong control + real damage). `[✓DOM]` Validated by Dark/Radioactive:
  proc-bombed AoE controls (Living Shadows, Shadow Field, Heart of Darkness) + an Assault chain
  loaded with **purples** (Apocalypse, Armageddon, Hecatomb); **Nerve** Alpha (like a Controller).
  Path: lock-down + burst. The offensive controller.

**EPIC ARCHETYPES (unlock at 50)**
- **Peacebringer / Warshade (Kheldians)** — *Cosmic Balance / Dark Sustenance* + shapeshift (Human/Nova/Dwarf). Flexible all-in-one (blast/melee/tank forms), .85 res. Path: versatility. `[?]` complexity tax — the "challenge for flexibility" pick.
- **Arachnos Soldier / Widow (VEATs)** — strong **Leadership** auras (0.100 buff), pets, mez. .85 res, 55.6 dmg. Path: team force-multiplier + solid personal performance. Widely "no bad build" ATs. `[THEORY]`

---

## 4. "Why X over Y?" — the decision logic `[THEORY]`
- **Defender vs Controller (both can buff/debuff):** Defender = stronger buffs/debuffs +
  a ranged attack secondary → *pure force-multiplier*. Controller = trades buff strength
  for **control + Containment damage** → *safety + lockdown*. Pick Defender to amplify a
  team's output; Controller to neutralize the threat.
- **Corruptor vs Defender:** Corruptor sacrifices ~15% buff strength for a real damage
  primary + Scourge → better solo. Defender for raw support ceiling (leagues/hard content).
- **Brute vs Scrapper vs Tanker:** Scrapper = most solo DPS; Brute = AoE + tank-lite +
  aggro (farms); Tanker = max survival + team aggro + AoE reach. Same armor sets, different
  scalar/cap/inherent profile.
- **Dominator vs Controller:** Dominator adds burst damage + boss-mez via Domination;
  Controller adds buff/debuff + Containment. Offense-control vs support-control.

## 5. Are any ATs "just for the challenge"? `[THEORY] — Joel, your ruling?`
Honest read: **no AT is a pure handicap** on Homecoming — each owns a niche above.
The closest to "you're choosing difficulty":
- **Sentinel** — `[✓ICE]` confirmed a *real niche*, not a handicap: durable ranged (armor
  secondary softcaps/floors defense + mez protection) at the cost of a lower damage ceiling.
  The "comfort/safety" pick — survive-and-blast solo — not the top-DPS pick.
- **Kheldians (PB/WS)** — high skill/keybind tax for their flexibility; reward real but earned. `[?]`
- **Solo pure-support Defender** — strongest support ceiling, but slow kill times alone.

Everything else has a clear competitive home in solo / team / league / farm.

---

## 6. How the planner should USE this
- Autopicker/recommender should know each AT's **pillar(s)** and lean the build there
  (don't build a Defender like a damage dealer; don't slot a Controller for pure DPS).
- The `why` text on recommendations can cite the **modifier advantage** ("Defender heals
  ~14% more than a Controller with this set") — grounded, persuasive, educational.
- Role presets should map to the AT's strong pillar by default, with the off-pillar as an
  opt-in (a Corruptor *can* go heavy debuff; a Brute *can* aim survival-first for a farm).

### Open questions for Joel
1. Sentinel + Kheldians — fair to flag as "comfort/challenge" picks, or do they have a competitive niche I'm underrating?
2. Any AT whose *best* path I've mislabeled?
3. Should the tool ever *steer away* from an AT/set combo for a stated goal (e.g., "Empathy on a Corruptor heals 28% less than on a Defender — sure?"), or just inform?
