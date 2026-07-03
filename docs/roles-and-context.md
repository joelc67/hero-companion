# CoH Build Doctrine — Role & Context (solo / team / league / farm)

**Purpose:** a build is only "good" **relative to its context**. The context supplies
some of the four pillars (offense / defense / buff / debuff+control) and *demands* the
rest. The planner must know which context a build is for, then balance survival-vs-offense
to match. Companion to `archetypes.md` + `build-doctrine.md`.

Tags: `[✓DATA]` from tool scalars · `[THEORY]` established CoH knowledge — **confirm** · `[?]` unsure.

---

## 1. The core principle
Every build needs all four pillars **covered** — but not all by *itself*. What the build
doesn't bring, the context must, or it fails.
- **Self-sufficient ATs** (Scrapper, Brute, Tanker, Sentinel) bring their own defense →
  fine solo, flexible anywhere.
- **Glass cannons / pure support** (Blaster, Defender, Controller, Mastermind, Corruptor)
  bring one pillar to *the table* and **borrow the others from the team** — or must buy
  them with heavy IO investment to function alone.

A recommendation is only correct once you know: **solo, small team, full team, league, or farm?**

---

## 2. What each context PROVIDES vs DEMANDS `[THEORY]`
| Context | Provides you | Demands of you | Survival need |
|---|---|---|---|
| **Solo** | nothing — you are everything | cover ALL pillars yourself | **high** (self-sufficiency or softcap+sustain) |
| **Duo / small team** | partial cover (1–2 roles) | pull your weight + patch gaps | medium |
| **Full team (8)** | aggro anchor + support + heals | do your ONE job extremely well | **low** (offload survival to tank/support) |
| **League (raid)** | everything, redundantly | -res/-regen, AoE, force-multiply | low personal, but enemies **debuff you** → overcap cushion matters |
| **Fire farm** | nothing (you solo a rigged map) | aggro aura + AoE + capped survival | **very high** (you tank a whole map) |

**Takeaway:** the *same* character should be built differently per context. Full-team →
all-in on its pillar. Solo/farm → buy back the missing defensive pillar first.

---

## 3. The enabler ↔ enabled relationship (the Fire/Fire lesson)
Damage that never lands = 0. Glass cannons are **enabled** by:
- **Aggro management** — a Tanker/Brute taunt aura pulls the alpha off the squishy. `[THEORY]`
- **Debuffs** — -to-hit / -damage (Dark, Cold, Storm, Rad) make enemies miss/hit softer. `[THEORY]`
- **Buffs** — +def/+res/+absorb (Cold, Sonic, Thermal, Force Field) plug the missing wall. `[THEORY]`
- **Heals** — undo the hits that do land.

**Worked example — Fire/Fire Blaster:**
- *Deadly:* ranged scalar **62.6** `[✓DATA]` (top) + Fire DoT + a 2nd damage set (Fire
  Manipulation: Build Up, Combustion, Hot Feet, FSC) + Defiance (blast through mez). `[THEORY]`
- *Fragile:* secondary is Manipulation, **not armor** — no res/def/mez protection; res cap
  .75 `[✓DATA]` but nothing fills it. Whole budget went to offense. `[THEORY]`
- *So:* TEAM/LEAGUE → tank taunts, support debuffs → it deletes everything safely =
  devastating. SOLO → must self-build a mitigation floor or die to the alpha. FARM →
  **wrong tool** (no taunt aura, no resistance vs the swarm). `[✓FFB]`
- **What the master Fire/Fire actually did `[✓FFB-DATA]`** (corrects my earlier "ranged
  softcap" guess): it built **LAYERED partial mitigation**, not a single softcap —
  ~34% **S/L + Melee + AoE + Fire defense** *plus* **54% S/L / 61% Fire resistance** *plus*
  Preventive Medicine **sustain/absorb** *plus* Defiance *plus* kill-speed. The defense
  vector matches **where it fights**: Fire Manipulation is a melee "blapper" secondary
  (Fire Sword, Combustion, FSC, Burn), so it stacks **S/L/melee/AoE** defense — NOT ranged.
  Epic (Flame Mastery) was taken for **survival** (Fire Shield = resistance) + **Melt Armor**
  (-res). Lesson: a squishy's defense vector follows its playstyle (ranged sets → ranged def;
  melee-blapper secondaries → S/L/melee def + resist), and "good enough" is a *layered floor*
  (~30-35% def + ~50% res + sustain + offense-as-defense), not necessarily the 45% softcap.

---

## 4. Team / league composition theory `[THEORY]`
A balanced team wants these JOBS filled (one char can cover several):
- **Aggro anchor** — Tanker/Brute (taunt aura, survives the alpha).
- **Damage** — Blaster/Scrapper/Stalker/Corruptor/Dom (the kill speed).
- **Force-multiplier** — Defender/Corruptor/Controller (buffs + the big **-res/-regen** debuffs).
- **Control** — Controller/Dominator (lock bosses, prevent incoming damage at the source).
- **Heal/sustain** — usually folded into the support slot.
**Leagues** scale this up and add: enemies that **-resist/-defense YOU** (→ overcap res
cushion, mez protection, and -regen on AVs become critical). A league rarely needs more raw
damage; it needs **debuff/control/sustain** to survive the spike content.

**Farm "team" = a team of one:** the farmer must self-cover aggro + AoE + capped survival,
which is why it's a Brute/Tanker with a damage aura + Fiery Aura, never a Blaster.

---

## 5. How this changes the BUILD (the actionable part)
- **Solo / farm context** → buy the missing defensive pillar FIRST (softcap def or cap res
  + sustain), *then* offense. A fragile AT here needs more IO investment to be playable.
- **Full-team / league context** → offload survival to the team; lean the build hard into
  its pillar (max damage, or max debuff/buff), take the team-friendly tools (Leadership,
  -res procs, Vengeance, etc.).
- **Always** cover mez protection somehow for solo/league (break-frees, Clarion, sets, or
  an armor secondary) — being mezzed = doing nothing.

---

## 6. How the planner should USE this
- The existing `content` preset (fire_farm / itrial / team / general) should map to a
  **survival-vs-offense balance** AND a context profile (what's provided vs demanded).
- **Warn on mismatch:** fragile AT + solo/farm context with no self-survival = "this build
  has no defensive layer and nothing here will tank for you — expect to faceplant unless we
  add ranged-def softcap + sustain." (This is the *honest* version of the warning Joel asked
  for — context-aware, not just a DPS number.)
- **Cite the relationship in `why` text:** "Blaster brings top-tier damage but no armor —
  in a team that's ideal (the tank holds aggro); solo we must build defense to compensate."

### Open questions for Joel
1. Is my context→survival-need mapping right (esp. league: how much does enemy -res/-def to YOU drive the build)?
2. For a SOLO squishy, what's the real bar — ranged-def softcap (45%) + sustain, or do you push further?
3. Should the planner refuse/strongly-warn a Blaster-type for a "fire farm" goal, or just inform and let you proceed?
