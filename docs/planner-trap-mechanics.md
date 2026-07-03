# Planner-Trap Mechanics Catalog

Mechanics in City of Heroes: Homecoming whose leveling structure, play style, or
enhancement rules break standard build-planner assumptions — the VEAT/Kheldian class of
problem, cataloged game-wide. Synthesized 2026-07-03 from a verified research sweep
(sources: homecoming.wiki, City of Data v2 (cod.uberguy.net), Homecoming forums, official
patch notes; every claim below survived 3-vote adversarial verification unless marked).

Legend for tool status: ✅ handled · 🟡 partially · ❌ open.

---

## 1. Epic Archetypes (structural rules)

### Kheldians (Peacebringer / Warshade)
- **One primary, one secondary** (Luminous/Umbral Blast + Aura). No set choice. ✅ (auto-selected)
- **NO epic/ancillary AND no patron pools at all.** A planner offering an epic pool slot
  at 35+ produces a build the game won’t allow. ❌ VERIFY: our autopick/deep_optimize must never
  assign an Epic.* set to PB/WS.
- **Inherent, SLOTTABLE travel** outside the pick budget: PB Energy Flight (L1, Flight/
  Universal Travel sets) + Combat Flight (L10, **accepts Defense sets → LotG mule!**);
  WS Shadow Step (L1, Teleport/UT sets) + Shadow Recall (L10). But the linked Quantum
  Acceleration toggle takes NO enhancements. ✅ travel-off default; 🟡 slotting these
  inherents (Combat Flight LotG) not exploited by the solver.
- **Historical Flight/Teleport pool ban is LIFTED on Homecoming** — they may take those
  pools now (masters do take 4 pools). ✅
- **Forms**: Nova (L4) grants 5 slottable sub-attacks; Dwarf (~L20) packs taunt + heal +
  teleport + AoE + melee attacks into one pick. Human eye blasts usable in Nova.
  Human toggles are **suppressed, not dropped**, while shapeshifted (Homecoming change).
  Form damage scales differ (human melee 0.85 vs Dwarf 1.0; human ranged 0.80 vs Nova
  1.20). Form toggle itself is a LOW slotting priority; the granted attacks are the
  slot homes. Dwarf can be entered while mezzed (mez escape). ❌ the known form-aware
  feature (per-form chains, form-committed slotting) — spec already captured.
- **Cosmic Balance / Dark Sustenance**: unslottable, team-composition-scaling, active in
  all forms. 🟡 (we exclude from slotting; team-scaling buff unmodeled).

### VEATs (Arachnos Soldier / Widow)
- Locked to base sets until 24; **mandatory respec at 24**; then all six sets pickable
  retroactively from level 1; **branch lockout** (any Crab power bars both Bane sets and
  vice versa; Night Widow vs Fortunata likewise). ✅ (branch pairing auto-selects mates;
  sweep skips cross-branch).
- **Dual base+branch access**: base primary has only 8 powers (L1-18); all 24+ primary
  picks must come from the branch. The real in-game build mixes BASE + ONE BRANCH —
  our planner models pri=branch, sec=branch; the base sets' powers should ALSO be
  available in the same build. ❌ (base+branch dual-set access unmodeled — a Crab build
  may legally take base Wolf Spider powers).
- **Base-vs-branch duplicate powers are mutually exclusive** (Frag Grenade, Venom
  Grenade base vs Crab versions). ❌ not enforced.
- **Branch-conditional damage**: base melee (Bayonet/Pummel) crits only with Bane powers
  (Placate/Cloaking Device); Night Widow/Bane crit-from-Hidden needs supplemental
  -perception vs bosses. 🟡 (crit synergies unmodeled).
- **No ancillary pools; patron pools only** (villain-alignment unlock — access persists
  after alignment change). ✅ data-level (VEAT_Soul_Mastery etc.); alignment gate is
  meta, N/A for planning.
- Cosmetic trap: any build taking a Crab power puts the backpack on ALL builds
  (verified, unfixed). Worth a UI note someday.

## 2. Homecoming vs live-2012 divergences (i27p5, Oct 2022 — verified shipped & current)
- **Power availability moved earlier**: primary T8 26→22, T9 32→26; secondary T2 at
  creation (level 1!), T7 28→24, T8 35→28, T9 38→30 (non-epic ATs). Epic/patron pool
  tier-3 41→38. Some powers moved off pure tier mapping (per-power data needed).
  ✅ mostly (we read level_available from the current Mids DB) — 🟡 VERIFY our hardcoded
  progression/pool-tier assumptions match (esp. mids_export level walk).
- **Pools**: unlock at 4; travel pools' first THREE powers all at 4 with no prereq;
  standard pools' 3rd power needs L14 + 1 prior pick, 4th/5th L14 + 2. 🟡 (our tier rule
  approximates; level gates unchecked).
- **Origin pools (Sorcery / Experimentation / Force of Will (+ Gadgetry, Utility Belt)):
  ONLY ONE per build.** ❌ NOT ENFORCED — autopick/deep_optimize could pick two. Real
  invalid-build risk (the game would refuse it).
- **Stealth toggles are no longer mutually exclusive** (strongest applies). ✅-ish (we
  never modeled the exclusivity).
- Fitness inherent at level 1 (four auto powers, slottable, restricted categories:
  Health=Healing only, Stamina=EndMod only). ✅
- Patron choice respec-swappable since i13; all ATs can take patron pools since i18. ✅

## 3. Archetype inherents that redirect value
- **Mastermind** (the big one):
  - Fixed unlock skeleton: T1 pets L1, T2 L12, T3 L22 (Homecoming levels), upgrades L6
    + L26 — upgrades are mandatory infrastructure, near-zero slots. 🟡
  - Pet counts/levels scale with COMBAT level (T1: 1@=, 2@-1 from 6, 3@-2 from 18;
    T2: 1 then 2@-1 from 24) — exemplar-sensitive. ❌ (we model dps_each only).
  - **Enhancement pass-through is per-pet-power acceptance** (CoD v2, triple-verified):
    damage passes; RECHARGE NEVER reaches pets (affects only the summon); endrdx affects
    both; accuracy pass-through disputed in testing; set bonuses do NOT apply to pets
    except pet-aura uniques (Command of the Mastermind etc. — global pet auras). Procs
    fire off individual pet attacks (match proc to pets' effect components).
    🟡 engine passes dmg_boost only ✓ correct-ish; pet-aura uniques unmodeled.
  - Supremacy: proximity-conditional pet damage + bodyguard sharing. ❌
  - **All MM powers cost +25% endurance.** ❌ VERIFY engine end costs.
- **Dominator — Domination**: 90s/200s; **recharge cannot be slotted — only global
  recharge reduces it** (perma-dom ≈ +120% global). Doubles own mez magnitude + refills
  endurance. 🟡 (control modeled; domination uptime physics absent).
- **Sentinel — Opportunity/Vulnerability**: reworked i27p5 (inherent click consuming 50%
  bar); **updated AGAIN Feb 10 2026 (i28p3.2): Vulnerability chains up to 5 targets,
  meter builds only in combat, sent res/def modifiers 70→75%.** ❌ VERIFY our Mids DB
  (2026.1.1242) predates/includes the Feb 2026 patch.
- Kheldian inherents: see §1.

## 4. In-set mechanics that change chains/slotting (future model terms)
- **Titan Weapons — Momentum**: every attack has two animation states (slow/fast);
  Follow Through + Whirling Smash REQUIRE Momentum (not openers); Build Momentum is a
  click buff (ToHit sets only, no damage sets); reworked i27p1 (live-2012 data stale);
  per-AT unlock levels and Tanker AoE radius/caps differ.
- **Dual Blades — combos**: Begin→Continue→Finish with 5s windows; out-of-order set
  powers break combos; **combo effects are enhanced by the FINISHER's slots** (slotting
  priority shift); combo tables DIFFER for Stalkers (Ablating Strike changes roles);
  conditional finisher damage invisible to base-damage ranking.
- **Street Justice — combo levels**: builders (+1) vs finishers (consume); finishers
  gain new EFFECT TYPES at CL3 (Crushing Uppercut disorient→Hold — which is why it
  accepts Hold sets!); Combat Readiness sets CL3 instantly; Stalker AS builds +2;
  crits don't scale with combo level.
- **Staff Fighting — forms + Perfection**: three mutually exclusive form toggles;
  Stalkers get ONLY Form of the Body (per-AT power lists differ); Perfection stacks
  (0-3) spent by finishers; Soul/Mind forms are leveling-phase tools (<20).
- **Bio Armor — Adaptation stances**: three mutually exclusive toggles; stance bonuses
  are UNENHANCEABLE (don't multiply by slotting); stances add/REMOVE whole effects
  (Defensive drops Evolving Armor's -res debuff); zero endurance; per-AT power lists;
  half of Inexhaustible's +HP unenhanceable.
- **Beam Rifle — Disintegrate**: keystone spread-state; standalone-DPS ranking
  undervalues it; slot recharge to keep the state up.
- (Also known: Water/Ice/Savage combo points — same family, not separately verified.)

## 5. Data-layer facts (parser/solver relevant)
- **Effect Groups (i25 engine)**: multiple effects share ONE probability roll (black-
  outlined groups in CoD with a "required" condition). Live-2012 rolled each effect
  separately. 🟡 VERIFY parser doesn't treat grouped probabilities as independent.
- **Zero-chance leftover effects** exist fully-defined in data (all classic MM upgrade
  powers, Sentinel Opportunity_Lock…) — deliberately neutered; must filter, not model.
  ✅ benign (probability multiplies to 0), but confirm no path ignores probability.
- **LotG/Preventive Medicine 6th-piece "effects" are nulls** — the global is applied as
  a set bonus by external logic. ✅ (engine does globals via set-bonus path).
- Requirements Expressions gate power usability (form locks, exclusivity) — evaluate,
  don't assume owned=usable. ❌ (not parsed).
- Per-power "Valid Enhancements and Sets" is the authority for slotting whitelists. ✅
  (we read accepted categories).
- Enhancement basics (confirmed): 6-slot cap ✅, ED ✅, no duplicate identical set IO in
  one power ✅ (VERIFY solver enforces), 4 schedules ✅, IOs never expire ✅; standard vs
  Superior version of the same ATO are mutually exclusive in one build ❌ VERIFY.
- P2W run powers (Ninja/Beast/Athletic Run): unslottable, detoggle pool travel. N/A.

## 6. Priority actions — status as of 2026-07-03
1. ✅ DONE: single-origin-pool rule enforced in _picks_legal + /build/validate error.
2. ✅ VERIFIED: Kheldians offered zero Epic.* sets (API + autopick).
3. ✅ DONE: VEAT base+branch dual access (autopick candidates, deep-optimize adds/drops,
   L1 seats, fill-to-cap, UI "Add from" rows incl. base sets) + Frag/Venom Grenade
   base-vs-branch exclusions in _picks_legal. Bonus: cured the Night Widow 23-pick
   residual — all VEAT pairs now fill 24/24.
4. ⚠ FINDING: our Mids DB is 2026.1.1242; the user's master was built on 2026.2.1309 —
   our data PREDATES the Feb 10 2026 patch (i28p3.2 Sentinel chain-Vulnerability etc.).
   USER ACTION: update Mids Reborn install → re-run tools/parse_mids.py.
5. ✅ VERIFIED: MM +25% endurance is baked into per-AT power data (Envenom 10.4 vs 13.0)
   — no engine multiplier needed; engine already passes ONLY Damage to pets (correct).
   🟡 remaining: pet-aura unique IOs (needs a pet-survivability model someday).
6. ✅ RESOLVED, no action: effect-group shared probability only changes the CORRELATION
   of effects, not their expected values — E[p·(a+b)] = p·a + p·b either way, and the
   whole model is expected-value math. Grouping matters only for variance.
7. ❌ Form-aware Kheldian feature (existing spec, enriched by §1 findings).
8. ❌ Combo/stance model terms (TW/DB/StJ/Staff/Bio/BR) — ties into cast-time budget (v17).
