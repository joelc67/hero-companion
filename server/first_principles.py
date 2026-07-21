"""first_principles.py — the encounter model: score a build by GAME ARITHMETIC, not targets.

The doctrine (user): "math doesn't mean pick the shortest route to a target — it means teach
add/subtract/multiply and let it derive trigonometry." So NOTHING here says "defense 45" or
"recharge 100" or "controllers care about control." The model knows only the game's arithmetic:

  • HIT CHANCE:  p = clamp(base_tohit − defense, floor=5%, 95%)      ← the 45% softcap EMERGES
    (50% base − 45% def = the 5% floor; past 45 more def buys nothing — a derived kink, not a rule)
  • DAMAGE TAKEN: incoming × p × (1 − resistance)                     ← res value emerges
  • SUSTAIN: effective HP pool + regen/heal HP/s                      ← regen/HP value emerges
  • UPTIME: enhanced_duration / enhanced_recharge, capped at 1        ← "perma" EMERGES at 1.0
  • CONTRIBUTION: damage dealt + team damage amplified (−res multiplies EVERYONE's damage)
    + damage PREVENTED (control locks foes; −tohit/−dmg debuffs shrink incoming; heals restore)
    … all × your AVAILABILITY (dead characters contribute nothing).

An archetype's "role" then FALLS OUT of its modifiers: a Blaster's damage numbers dominate its
contribution; a Controller's prevention dominates; nobody tells them that. The content dropdown
maps to a SCENARIO (what the fight IS — enemy count, team size, damage mix), never to stat targets.

v1 calibration is coarse (documented inline) — the POINT is the shape: every term is the game's
own formula, so improving a number improves the model, never the rulebook.
"""

import math
import os

# Bump on ANY physics/term change. Lessons and champions are stamped with this: proposer BIAS
# (lessons) from an older model version is ignored — conclusions drawn by a blinder model must
# not steer the proposer after the model improves (measured: run 9, blind to Carrion Creepers'
# vine damage, taught autopick to drop it; the fix landed and the stale lesson kept biting).
MODEL_VERSION = 35     # v35 (2026-07-21 — the ENDURANCE batch; endurance-fix-paper.md, Joel's five §8 rulings all landed as recommended): (1) FIGHT-DURATION end_factor — the v10 sqrt haircut + 0.45 FLOOR RETIRED (Q2a: a bar that empties and cannot act earns nothing; the floor guaranteed an end-broken kit 45–72% credit, which is exactly how the tool shipped Nimbus at −5.98/s); replaced by the honest physics of a fixed bar over the scenario's own fight length L: T_empty = E_max/(D−R) of full output, then f_sus = clamp((R−D_tog)/D_chain) — toggles paid first — for the rest of L. ONE code path for ALL scenarios (Q2b): short fights read ≈1.0 on their own, the 240s AV fight collapses Nimbus-class kits to ~11% effective DPS (worked table in the paper; sustainable builds score ~10× higher there, and the solver finally has a REAL reason to stay sustainable only where the game punishes it). (2) v20 end_relief RETIRED (Q4): recovery is BARE build totals — the scenario constants that silently assumed incarnate-era recovery are deleted; a build that declares incarnates carries the credit in its own totals and the ledger STATES it ("incarnate buffs included — recovery is NOT bare"). The v20 mule-vs-Leadership motivation re-derived safe: a real toggle set (~1/s) is nowhere near the >E_max/L deficit needed to trigger any penalty on short fights. (3) END-PROCS at MEASURED average (Q1, tools/measure_end_procs.py on Joel's raw chatlogs, ~4,900 10s roll windows): Performance Shifter 0.497 procs/window × 10.64 end = 0.529 end/s (the client's 3.0 PPM auto-host formula EXACTLY — measured and formula agree to 1%), Panacea 0.398 end/s; PIECE_GLOBALS' flagged estimates (0.10/0.05 recovery-equiv) undershot the field 3–5× and are replaced by measured equivalents (0.317/0.239); Theft of Essence added at the PPM formula with a stated HALF-USAGE assumption (0.25 end/s, PROVISIONAL — unmeasured, absent from the archive). PAPER CORRECTION (log-verified): Power Transfer's proc is a self-HEAL (80.32 HP@50), not an end return — Panacea is the real fourth end proc; PT keeps its Regeneration credit. PS unique flag corrected to game data False (stacks, rule of five). (4) +MaxEnd EXISTS now: 40 Endurance/Max set-bonus records were silently dropped by _apply_effect (the SAME allowlist-gap family as v28 accuracy / v29 heal-strength) — credited into totals.max_end; E_max = 100 + accolade flat + set bonuses, and empty_after_sec uses the real pool. (5) TRAVEL-TOGGLE SPLIT (Q3, the Nimbus 0.46/s gap): Fly/Hover/Mystic Flight drain is tallied separately, ALWAYS displayed (never silently dropped from the ledger again), and joins the SCORED fight only when the build declares a ranged/hover playstyle (exposure "back" → engine stamps travel_in_combat). NEGATIVE CONTROL (mandatory, §7): drain ≤ recovery ⇒ end_factor = 1.0 on every scenario — the model never penalizes a sustainable build. // v34 (2026-07-19 — the Mastermind pet-buff batch, #13): PET-DIRECTED DAMAGE BUFFS now credited on pet DPS (a MM's main damage is its pets, and it buffs them). GAME-FIRST ROUTING LEVER (engine._pet_damage_buff): a DamageBuff in a power's buff_effects reaches affected allies incl. MM pets; a self_effects-only DamageBuff (Musculature Alpha) is caster-only and excluded. Priced: Supremacy +25% (aura), Accelerate-Metabolism/Fulcrum-class (click, uptime-weighted), Temporal Selection (single-target radius 0 → the top-DPS pet only), Assault HYBRID *Radial* incarnate (team/pet; Core self-only excluded — but see gap), Pack Mentality (Beast Mastery charge mechanic, empty effects → priced at Joel's ruling 8 of 10 stacks = +16%, stated on label; the pet-DPS uptime factor already removes idle time, so near-max is scenario-consistent). STATED SIMPLIFICATION (Joel option B): pets modeled as always-hitting → buff ToHit not credited, pet accuracy deferred. NEGATIVE CONTROL verified: an MM with only caster-only buffs (Musculature+Assault Core) reads pet_damage_buff=0. DATA GAPS SURFACED (reported, not silently absorbed): (a) the Assault HYBRID incarnate is ABSENT from incarnate_fx entirely — so the routing for Assault Radial is correct but dormant, and the player's OWN damage misses it too (queued); (b) Fortify Pack is a Def/Regen SURVIVAL buff (reroutes to the v29 henchman machinery, not damage) — charge-scaled, unpriced-and-labeled; (c) the broader expression/kMeter class (Fury/Rage/Domination/Defiance/Gauntlet — headline: BRUTE FURY is unpriced) is queued as its own audit. // v33 (2026-07-16 — the Maelwys round-5 correction batch): (A) 6/23 DATA RE-SYNC — Temperature Protection gained an enhanceable +MaxHP and Heal-enhanceable +Regeneration in the game's June 23 patch and our Mids-era snapshot predated it, so every Fiery Aura build's sustain was computed on stale ground (the shipped Spines/FA champion's public "+3x8 ceiling" claim among them); patched additively from the client bins (tools/patch_temperature_protection_623.py, all 5 ATs) and a NEW structural check (tools/reality_check_effect_structure.py) now diffs effect EXISTENCE/enhanceability against the client, the gap class the scalar reality checks could never see. (B) ACCOLADE ASSUMPTION + LABEL HONESTY — the farm presets model the four standard accolades (the exact four every community reference build carries), sourced game-first from a crawler export EXTENSION (Boosts/Temporary_Powers/Set_Bonus categories were never exported: "accolades are already in our data" was false); the assumption — or its absence — is now PRINTED on every AFK sustain label, never silent. (C) BUFF-PROC SUSTAIN — the Superior/regular Unrelenting Fury ATO grants +Regen via a Boosts->Grant_Power->Set_Bonus chain our data never carried (piece_boosts held only its RechargeTime); priced in the AFK sustain ledger on v32's measured aura machinery (same roll, same AURA_PATCH_AF_MEASURED), credited as the EXACT capped-expectation stack average E[min(cap, Binomial(dur/period, chance))]. Stated: ledger-only scope; template stack_limit 2 vs help-text 5 conflict recorded and resolved conservatively (bounded at 1.5pp of regen); other buff-proc shapes unpriced. (D) FARM_ACTIVE SCENARIO RULING (Joel) — "survival is constraints, not objective": the 45/90 asks stay hard, but availability no longer multiplies the objective for that scenario (survival_is_constraint), so damage throughput decides the picks; the TRUE availability is still measured and reported, we simply stopped scoring it. // v32 (Joel's pricing ruling, 2026-07-15 — measured aura/patch proc rate): the geometric area factor does NOT apply to aura/patch proc rolls — engine.AURA_PATCH_AF_MEASURED = 1.1 replaces the dev-archive AF (1.9 on an 8-radius patch) in aura_proc_dps_per_target ONLY (clicks keep the dev-verified formula). Source: per-proc per-host field measurement on Joel's raw farm chatlogs (tools/measure_ig_procs.py — ToLG/Shield Breaker attribute to Irradiated Ground by set legality; 10.66%/hit-tick measured vs the formula's 6.14%, 26,541 ticks; confirms the 2026-07-07 "auras behave as AF≈1" pure-window finding, 56.7%±3.2 per-proc). v31's formula undershot the field 42% and priced IG out of its own signature content (the farm_active decisive test). STILL-STATED EXCLUSIONS: the IG pet's own BASE damage remains unpriced (measured 7.97/hit/target — the bins-first pricing pass is queued, not rushed); patch double-stacking (measured 1.21s effective cadence vs single-instance 2.0s) unmodeled — single-instance stays the conservative assumption, stated. // v31 (Joel-approved batch, 2026-07-16 — aura/patch procs + farm objectives): (1) AURA/PATCH PROC PRICING, game-first — damage procs in TOGGLE auras roll per the client's own activate_period per target (Blazing Aura/Quills 2.0s from powers.bin; chance = PPM×period/(60×AF), Bopper AF), and PSEUDO-PET PATCHES (Irradiated Ground — summoner carries ZERO damage_effects, its whole output lived unpriced on the pet) price procs on the PET's pulse (Auto, 2.0s, radius 8, 10 targets — bin-extracted via the preserved Bin Crawler; patch uptime taken continuous, 4s recharge ≪ duration, stated). Cross-check: the formula's joint 2-proc window rate (~49–57%) brackets Joel's measured 56.7%. Stated exclusion: the IG pet's own BASE damage remains unpriced (procs were the batch; the base-damage dig is queued). (2) FARM SCENARIOS from Maelwys's encounter math — farm_afk: the asteroid-map AFK case, 17 foes in full melee rotation + the ranged tail at single-attack weight (enemies=27 equivalent, stated derivation), sustained (length 60), +4; farm_active: player-driven (aggro-capped 10, kiting/insps are the player's job — survivability honestly secondary). Presets: farm_afk asks the HARD prerequisites (fire res CAP, fire def 45, per-AT regen floor from the 35–40 HP/s absolute requirement — SIMPLIFICATION, stated in ai_build: floor converts against the AT's BASE HP, so a bigger built pool overshoots the floor, erring safe; the scorer's survival math uses the build's real HP); farm_active asks res CAP + decaying def 45 + recharge (AoE cycling). Certification under declared asks runs the strict A2 guard. // v30 (Joel-approved scope + six-point checklist, 2026-07-10 — the Maelwys round-4 batch): (1) POST-TARGET SOFT DECAY — the ILP objective's threshold cliff removed (a met survival axis was worth literally ZERO more, so core armor toggles became arbitrary global-mule real estate — his TI-muled-vs-RPD-full-set same-build inversion): each Defense/Resistance axis gains a second coverage segment from target to its REAL ceiling (res: AT hard cap; def: the softcap the encounter model derives), weighted by the target weight × ρ where ρ is measured NUMERICALLY from this model's own marginal (availability gain per point past target ÷ at target, at the preset's scenario) — accuracy-term precedent, no invented constants; the armor set-prune keeps options alive on the same live axis. (2) THE 103-RECORD BACK-FILL (patch_empty_bonus_tiers.py, 103/103 hard denominator, game-client source): ten bonus families invisible since launch now exist — KB protection, slow resist, six mez-DURATION families, movement, range, endurance discount, improved slow/KB — engine totals + IO card for ALL (the 'not yet in totals' flag died by data), reality check now verifies 1130/1130 mappable effects. SCORED (this file): KB protection = availability term (knocked-down seconds are dead seconds; threshold mag 4 = the game's own −KB IO grant, client-baked; kb_in scenario physics PROVISIONAL+flagged; also added the 3 stackable −KB piece globals to PIECE_GLOBALS — power-granted KB prot still absent = stated equal-understatement), slow resist = recharge-bound output share (0.5 established elasticity) × slow_in scenario physics (PROVISIONAL+flagged; buff-cycle stretching unmodeled = understatement), mez duration = per-type multiplier inside build_control_output (universal physics, role lens does the gating). DISPLAY-ONLY stated exclusions (reality check prints them): movement/range/end-discount/slow-str/KB-str. // v29 (Joel-approved scope, 2026-07-08 late evening): (1) HENCHMAN SET-BONUS INHERITANCE — bins-verified (client powers.bin: Henchmen-tagged effect groups on Set_Bonus.Set_Bonus.* only; SetBonusPetShareHP[50]=40.159 on the MM class, henchman classes lack the table): henchmen receive 50% of TRUE set bonuses — flat HP from the MM's own base (identical every tier → T1s gain most), half-percentage def/res/regen; piece globals + accolades structurally excluded via engine set_bonus_totals (accumulated inside the set-bonus loop only); consumed as a per-henchman survival availability (same ttl→1−exp shape as the player's own) on pet DPS. Provisional+flagged: uniform spawn-damage spread across squad+MM; henchman innate defenses unmodeled (understatement). +Damage inheritance deferred WITH the player-side +damage%-set-bonus gap (shared plumbing, v30 candidate, stated in reality_check_setbonuses). (2) HEAL STRENGTH — the game's 11 heal-strength set bonuses (Numina 4pc +6%…) back-filled game-first (patch_heal_strength.py; parse_mids allowlist fixed — same root cause as v28's accuracy find) and multiplied onto the build's own heal output (set bonuses bypass ED); lands BEFORE any healer champion per the boundary condition. // v28: THE STABILITY BATCH (Joel + Maelwys round-2 field reports, 2026-07-08) — (1) HitPoints set-bonus UNIT fix, GAME-VERIFIED: values are Melee_HealSelf SCALES (flat HP = value × table ≈ base_hp/10 per AT; Brute 2.01%), the engine had added them raw = every +HP bonus 10x inflated in totals AND ILP targets (masked by the HP cap); tank preset floor 0.30→30 (latent percent-units bug); (2) Reactive Defenses scaling-res unique priced into PIECE_GLOBALS at its +3% always-on floor (was entirely invisible to the solver); (3) toggle END-COST term: a def/res set's endurance aspect relieves the host toggle's REAL drain (end_cost/activate_period — Weave 0.325, Maneuvers 0.39, CJ 0.065 end/s), credited as recovery-equivalent coverage, so expensive toggles are strictly better set hosts; (4) armor-credit recharge gate REMOVED: a toggle is always-on by definition — the old <8 (armor-native) / <=10.5 (squishy) gates silently excluded the POOL armor toggles (Tough/Weave store 10.0s, Maneuvers 15.0s: Maneuvers had NEVER earned the credit on any AT); (5) exact ILP added-slot budget (indicator per empty power + reservations; Hasten's 2-slot standard reserved AND guarded from the junk trim) + value-aware over-budget trim (junk fills → non-attacks → pool attacks → weakest real attacks) — real attacks reach 6 slots (the universal 5-slot attack cap was budget overspend + order-blind trimming, never a preference); (6) 6th-slot damage credit (0.7 of a piece; PROC VEHICLES 2.5 with base weight floored at 0.5) and proc bombs keep their slot count + reserve a Nucleolus Acc/Dam slot; (7) last-piece-swap guards everywhere (−res anchor, FF seating, endurance relief): never overwrite procs/HOs/globals/uniques, never orphan a 2-piece set; ST-hybrid tails stack HOs instead of keeping dead fragments; (8) signature support-set buff clicks are must-set on EVERY role; (9) ACCURACY VALUED END-TO-END (the LotG-x4 gap, Maelwys: "Global Accuracy set bonuses are a big help in capping your hit rate versus +4s and above"): DATA — parse_mids dropped every global-accuracy set bonus (missing "Accuracy" in the Enhancement-relabel allowlist; LotG 4pc +9% parsed to an EMPTY effects list), all 65 accuracy bonuses back-filled from the game-client extraction and the set-bonus reality check extended (name matching fixed too: it silently covered 43 values, now 282, 0 drift); SOLVER — an ("Accuracy",None) objective term derived by linearizing outgoing_hit at the solve baseline: target = accuracy headroom to the 95% ceiling from the scenario's player-vs-+N base-hit table (~4% vs +1s, 41% vs iTrial +3s, 74% vs +4s — content-aware saturation, never overbought), weight = the recharge term's per-fraction weight × the scorer's own marginal ratio (dlnDPS/dacc = 1/(1+acc0) ÷ recharge-bound share 0.5/(1+rech0)); scenario key rides the preset targets; the engine/scorer side already consumed totals["accuracy"] — it had just never been fed; v27: THE REMAINING MAELWYS PROMISES — (1) −res procs for EVERY role that can host them (the anchor sweep was debuffer/control-only; a damage role owns the biggest share of the spawn's damage, so Achilles/Annihilation/Fury multiply HIS output too; Annihilation PPM corrected to the client's 3.0, attuned twins priced, Fury priced at Achilles-class 15); (2) FORCE FEEDBACK +recharge valued for real: seated in the spammiest non-premium knockback attack and priced in engine totals as chance × 5s ÷ actual cycle (multiple copies add uptime, capped at +75%) — flows into everything recharge touches (chains, hasten, debuff uptime, pet cycles); (3) HAMIDON ORIGINS modeled: all 62 special IOs registered as priceable pieces, and the ST proc-hybrid's filler core trades up to 2× Nucleolus (Acc/Dam 33.3% each — ≈66/66 in two recharge-free slots; Endoplasm for pure holds); premium cores stay set pieces; v26: HENCHMEN FOR REAL — pet entities reconciled to the live client (henchman classes were 2.2x hot from the Mids snapshot; the live henchman-family columns didn't even exist), SQUAD counts from EntCreate templates (Soldiers = 2xSoldier+1xMedic; tier squads of 3/2/1), per-power pet class (Controller vs Dominator versions share an entity uid), timed-summon UPTIME (Spiderlings 240s earn duration/cycle credit; recharge slotting shortens the cycle), copy_boosts honored (no phantom damage enhancement on pets the game doesn't boost); the optimizer eats dps_total = each x count x uptime; v25: ST PROC HYBRIDS — a long-recharge single-target attack/hold keeps a 2-3 piece acc/dam core (recharge-free: local recharge divides proc chance) and fills its tail slots with damage procs once the PPM math clears ~50%/roll (the Dominate / Seismic Smash master pattern; capacity counted by distinct proc SETS; pet summons excluded — henchman procs are the pet's own model, task #33) + proc-catalog PPM values now authoritative from the game client (11 fixed; ATO procs were 30-43% undervalued); v24: CURRENT-META CALIBRATION from the 2,255-build Sovereign corpus + the master builder's doctrine — damage-proc PPM pricing in the engine (procs are DEAL, tradeable against set bonuses), typed S/L/F/C-35 default targets (positional-armor builds swap to Melee/Ranged/AoE 35; "classic softcap" goal restores 45s), Hasten hard 2-slot rule; v23: FOCUS SPLIT (role_mix — ask the user their percentage split when sets support multiple roles); v22: role lens × playstyle (solo relaxes to raw physics — 'whole team in one character') + wiki Role Diversity natural-roles table; v21: ROLE LENS (declared role weights the objective — role-based game first, off-role only by explicit pick); v20: scenario end_relief (incarnate-era recovery — mules stop beating Leadership via a phantom endurance crisis); v19: debuffer proc pass = res/anchor procs ONLY (no damage bombing — his damage is 1/9th of the league's; every −res proc placed, last-piece swaps, premium homes protected); v18: no pool/inherent melee in ranged ST chains + pure-ADD moves; v17: attack cast budget; v16: team buffs; v15: team −tohit; v14: ally buffs; v13: Redirects; v12: −def; v11: uptime; v10: enh-aware

# ── Scenario: what the FIGHT is (physics), not what stats to want ────────────
# Units are relative (contribution is compared between builds, so absolute scale cancels).
# shift = enemy level relative to player; rank_acc = avg critter Rank accuracy in the spawn
# (WIKI Attack Mechanics: Minion 1.0, Lt 1.15, Boss/EB 1.30, AV/GM 1.50).
SCENARIOS = {
    #             enemies  enemy_dps  teammates  team_dps_each  fight_len   shift  rank_acc
    # ctrl_land = fraction of the spawn a typical mag-3 player control ACTUALLY lands on, from the
    # wiki-verified Protection table (Minion 1, Lt 2, Boss 3, EB 6, AV 3+50 w/ triangles up, GM 75;
    # applied only when magnitude EXCEEDS protection — a mag-3 hold does NOT hold a Boss in one
    # cast, it needs stacking): weighted by each scenario's rank mix, boss credit ~0.5 for restack.
    # debuff_res = enemy innate DEBUFF resistance (wiki Archvillain Resistance: AVs 0.85 @50,
    # always-on) — applies to −tohit/−def/−dmg/−regen… but NOT to −Resistance (absent from the
    # AV list: −res is unresisted, which is WHY −res rules AV fights). Normal ranks: ~0.
    # enemy_regen = enemy sustain in dps-equivalent units (what −Regen debuffs strip): trash dies
    # too fast for regen to matter; an AV's regen is the wall the fight is fought against.
    # def_debuff_in = incoming −def pressure on a ZERO-DDR squishy (v10): erodes the soft-cap,
    # re-valuing the resistance behind it. Cascade risk scales with how debuff-heavy the content is.
    "general":   dict(enemies=4,  enemy_dps=90,  teammates=0, team_dps=110, length=30.0,  shift=1, rank_acc=1.05, ctrl_land=0.95, debuff_res=0.0,  enemy_regen=5,   def_debuff_in=0.03, kb_in=0.04, slow_in=0.05),
    "team":      dict(enemies=8,  enemy_dps=90,  teammates=7, team_dps=110, length=25.0,  shift=2, rank_acc=1.10, ctrl_land=0.92, debuff_res=0.0,  enemy_regen=8,   def_debuff_in=0.04, kb_in=0.05, slow_in=0.08),
    "itrial":    dict(enemies=10, enemy_dps=130, teammates=7, team_dps=130, length=30.0,  shift=3, rank_acc=1.20, ctrl_land=0.87, debuff_res=0.0,  enemy_regen=15,  def_debuff_in=0.07, kb_in=0.06, slow_in=0.15),
    "fire_farm": dict(enemies=10, enemy_dps=110, teammates=0, team_dps=0,   length=20.0,  shift=4, rank_acc=1.00, ctrl_land=0.95, debuff_res=0.0,  enemy_regen=5,   def_debuff_in=0.05, kb_in=0.02, slow_in=0.0),
    # v31 FARM SCENARIOS (Maelwys's encounter math, given freely on the forum):
    # farm_afk = the open asteroid AFK case — "17 foes in melee range using
    # their full attack rotation, the rest staying back and spamming a single
    # ranged attack": 17 full + ~25 ranged at ~0.4 rotation weight ≈ 27
    # enemy-equivalents (stated derivation), SUSTAINED (no repositioning, no
    # inspirations — length 60s windows), +4 fire-typed pressure.
    "farm_afk":  dict(enemies=27, enemy_dps=110, teammates=0, team_dps=0,   length=60.0,  shift=4, rank_acc=1.00, ctrl_land=0.95, debuff_res=0.0,  enemy_regen=5,   def_debuff_in=0.05, kb_in=0.02, slow_in=0.0),
    # farm_active = player at the wheel (Maelwys: repositioning, buttons,
    # inspirations — building 90/45 there "leaves substantial damage on the
    # table"): aggro-capped spawn, short kill windows; survivability is the
    # player's job, THROUGHPUT is the build's.
    "farm_active": dict(enemies=10, enemy_dps=110, teammates=0, team_dps=0, length=20.0,  shift=4, rank_acc=1.00, ctrl_land=0.95, debuff_res=0.0,  enemy_regen=5,   def_debuff_in=0.05, kb_in=0.02, slow_in=0.0, survival_is_constraint=True),
    "av":        dict(enemies=1,  enemy_dps=220, teammates=0, team_dps=0,   length=240.0, shift=2, rank_acc=1.50, ctrl_land=0.08, debuff_res=0.85, enemy_regen=120, def_debuff_in=0.10, kb_in=0.03, slow_in=0.10),
}
# kb_in (v30, PROVISIONAL scenario physics — flagged like def_debuff_in was at v10):
# fraction of an UNPROTECTED player's action time lost to knockback/knockdown in
# that content (fall + stand ≈ dead seconds). fire_farm lowest (fire attacks
# rarely knock), itrial highest (Ragnarok-class AoE KB everywhere).
# slow_in (v30, PROVISIONAL scenario physics): average incoming −recharge
# pressure on a ZERO-slow-resist player — the winter-content/incarnate lever
# (−recharge auras, quicksands, chill). fire_farm 0 (fire doesn't slow).

# WIKI-VERIFIED "Purple Patch": player effect strength vs HIGHER-level foes — applies to damage,
# debuff strength, mez duration, knockback alike (NOT to base hit chance, which has its own table).
_PP_BELOW = {0: 1.00, 1: 0.90, 2: 0.80, 3: 0.65, 4: 0.48, 5: 0.30}

# ── WIKI-VERIFIED to-hit arithmetic (Homecoming "Attack Mechanics", pasted 2026-07-01) ──
# HitChance = Clamp( AccMods × Clamp( Base + ToHitMods − DefMods ) ), clamp 5–95% BOTH times.
_TOHIT_BASE_VS_PLAYER = 0.50     # critter → player: flat 50% base (verified)
_TOHIT_FLOOR, _TOHIT_CEIL = 0.05, 0.95
# Critter attacking player: level shift is an ACCURACY multiplier (outside the inner clamp).
_LEVEL_ACC = {0: 1.0, 1: 1.1, 2: 1.2, 3: 1.3, 4: 1.4, 5: 1.5}
# Player attacking critter: base hit BY the enemy's relative level (the offense side).
_PLAYER_BASE_VS = {-1: 0.80, 0: 0.75, 1: 0.65, 2: 0.56, 3: 0.48, 4: 0.39, 5: 0.30}
_REGEN_PER_SEC = 0.0042  # base regen: ~5% max HP per 12s at 100% regen
# PROVISIONAL (still unverified): typical slotted per-attack Accuracy enhancement (×1.4).
# (The former 0.5 to-hit-debuff credit is RETIRED — replaced by the wiki-verified Purple Patch ×
# AV-debuff-resistance scaling applied by the caller.)
_ATTACK_ACC_ENH = 1.4


# ── ROLE LENS (v21): City of Heroes is a ROLE-BASED game first (user doctrine). The Role
# picker is the player's DECLARED OBJECTIVE, not a hint: physics stays universal, but the
# role weights WHICH contribution gets maximized. A debuffer "relies on others to do the
# damage" — his own damage barely steers his build. Off-role builds (a "Damage dealer"
# Defender = the classic Offender) happen ONLY when the player explicitly selects that
# role — never by optimizer drift. Weights are role DEFINITIONS (declared intent), not
# physics constants.
ROLE_WEIGHTS = {
    #              deal   amplified  prevented
    "damage":     (1.00,  1.00,      0.25),
    "tank":       (0.25,  0.50,      1.00),
    "controller": (0.25,  0.75,      1.00),
    "control":    (0.25,  0.75,      1.00),
    "debuffer":   (0.15,  1.00,      1.00),
    "buffer":     (0.15,  1.00,      1.00),
    "support":    (0.15,  1.00,      1.00),
    "healer":     (0.15,  0.50,      1.00),
}


def role_contribution(ev, role, teammates=7):
    """Score an encounter_value through the player's declared role — BLENDED BY PLAYSTYLE
    (user, with the wiki Role Diversity page): on a full team you play YOUR role; solo "you
    kind of agree to be the whole team of diversity in one character" — the lens relaxes to
    raw physics (self-sufficiency) as teammates → 0. Linear blend, no extra constants.

    `role` may also be a FOCUS SPLIT dict {role: fraction} — the user's own answer to
    "if we split your focus, what percentage on each role?" (user doctrine: when you don't
    know what the player is building for, ASK THEM). Weight vectors blend by fraction."""
    if isinstance(role, dict) and role:
        tot = sum(v for v in role.values() if v and v > 0) or 1.0
        wd = wa = wp = 0.0
        for r, frac in role.items():
            w = ROLE_WEIGHTS.get((r or "").lower(), (1.0, 1.0, 1.0))
            f = max(frac or 0.0, 0.0) / tot
            wd += w[0] * f; wa += w[1] * f; wp += w[2] * f
        w = (wd, wa, wp)
    else:
        w = ROLE_WEIGHTS.get((role or "").lower())
    if not w:
        return ev["contribution"]
    b = min(max(teammates, 0), 7) / 7.0
    wd, wa, wp = (1.0 + (w[0] - 1.0) * b, 1.0 + (w[1] - 1.0) * b,
                  1.0 + (w[2] - 1.0) * b)
    return ev.get("availability_objective", ev["availability"]) * (
        wd * ev["my_dps"] + wa * ev["amplified"] + wp * ev["prevented"])


def _clamp(x):
    return min(_TOHIT_CEIL, max(_TOHIT_FLOOR, x))


def incoming_hit(defense, tohit_debuff, sc):
    """Chance a scenario critter hits the player — the wiki's exact two-clamp structure.
    `tohit_debuff` arrives already purple-patched and AV-debuff-resisted by the caller."""
    inner = _clamp(_TOHIT_BASE_VS_PLAYER - defense - tohit_debuff)
    return _clamp(sc["rank_acc"] * _LEVEL_ACC.get(sc.get("shift", 0), 1.4) * inner)


def outgoing_hit(tohit_buff, global_acc, sc, def_debuff=0.0):
    """Chance the player's attacks hit the scenario's critters (enemy def ~0 baseline).
    ToHit buffs act inside the clamp; Accuracy (enhancement × global bonuses) multiplies outside —
    this is WHY to-hit/accuracy investment multiplies real DPS at +3/+4. v12: enemy −DEF acts
    inside the clamp exactly like a ToHit buff (wiki Attack Mechanics: Base + ToHit − Def) —
    a def-debuffed spawn is easier for EVERYONE to hit, until the 95% ceiling."""
    base = _PLAYER_BASE_VS.get(sc.get("shift", 0), 0.39)
    inner = _clamp(base + tohit_buff + def_debuff)
    return _clamp(_ATTACK_ACC_ENH * (1.0 + global_acc) * inner)


# Average LEAGUE TEAMMATE hit profile (provisional model constants, flagged): standard slotted
# accuracy is already in _ATTACK_ACC_ENH; assume modest global accuracy bonuses and no ToHit
# buffs of their own. −Def credit = the REAL damage gain from their hit chance rising toward
# the 95% ceiling — derived, not capped by judgment (v12; replaced the flat 0.15 cap).
_TEAM_ACC_AVG = 0.20
_TEAM_TOHIT_AVG = 0.0
# Average teammate DEFENSE (v15): what enemy −ToHit debuffs stack against when protecting the
# TEAM — the Dark Miasma term (Darkest Night/Fearsome Stare floor the spawn's accuracy for all
# 8 people; the model previously credited −tohit only to the CASTER's own survival).
_TEAM_DEF_AVG = 0.25


def _pct(totals, key):
    x = totals.get(key)
    return ((x.get("value", 0) if isinstance(x, dict) else x) or 0) / 100.0


# ── v29 HENCHMAN SET-BONUS INHERITANCE (bins-verified 2026-07-08) ────────────
# Henchmen receive 50% of the Mastermind's TRUE set bonuses: a FLAT hit-point
# amount computed from the MM'S OWN class table (SetBonusPetShareHP[50] = 40.159
# = 803.17 × 10% × 0.5 per scale unit — identical for every tier, so the squishy
# T1s gain the most proportional survivability: Maelwys's point, and the game's),
# and half the percentage for defense/resistance/regeneration. Piece globals
# (Unbreakable Guard, LotG) and accolades carry NO Henchmen effect groups, so the
# exclusion is structural: engine.calculate_build's `set_bonus_totals` is
# accumulated inside the set-bonus loop only. The +damage inheritance family is
# NOT modeled yet — it shares plumbing with the player's own (unvalued) +damage%
# set bonuses and both land together (v30 candidate, stated in the reality check).
# Henchman base HP at 50 from the client's villain_classes.bin (both class-name
# spellings carry identical values).
_HENCH_HP50 = {
    "Class_Minion_Henchman": 578.3, "Class_Henchman_Minion": 578.3,
    "Class_Minion_Henchman_Small": 578.3, "Class_Henchman_Minion_Small": 578.3,
    "Class_Lt_Henchman": 771.0, "Class_Henchman_Lt": 771.0,
    "Class_Boss_Henchman": 963.8, "Class_Henchman_Boss": 963.8,
}
_INHERIT_SHARE = 0.5      # SetBonusPetShare / SetBonusPetShareHP (client tables)


def _henchman_availability(pet, totals, sc, tohit_deb, bodies, owner_base_hp,
                           upgrade_cast=0.0):
    """Fraction of the fight this pet is UP — a RENEWAL process, not a one-death
    gate: a henchman lives ttl seconds, dies, and costs its resummon + re-upgrade
    cast time to bring back, so availability = ttl / (ttl + downtime). Every
    quantity is the game's own: tier HP from the client's villain_classes.bin,
    the inherited 50% share per the bins, cast times from the build's actual
    summon/upgrade powers, the hit math the whole model runs on. The spawn's
    damage spreads uniformly across every body on the field (teammates + MM +
    squad — provisional, flagged); henchman innate defenses, MM aura buffs and
    per-tier summon-level offsets are not modeled (flagged; the first two
    UNDERSTATE availability, the last overstates T1s slightly). The MM's own
    −tohit debuffs protect henchmen exactly as they protect him (game rule)."""
    hp50 = _HENCH_HP50.get(pet.get("pet_class") or "")
    if not hp50:
        return 1.0            # non-henchman pet: no inheritance, no death model
    sb = totals.get("set_bonus_totals") or {}
    # engine stores max_hp as the MM's own +HP fraction of HIS base — the game
    # computes the flat share from exactly that: frac × MM base × 0.5.
    hp = hp50 + (sb.get("max_hp") or 0) / 100.0 * (owner_base_hp or 0) * _INHERIT_SHARE
    dvals = sb.get("defense") or {}

    def _bestdef(keys):
        return max((dvals.get(k) or 0) for k in keys) / 100.0 * _INHERIT_SHARE

    p_ml = incoming_hit(_bestdef(("Melee", "Smashing", "Lethal")), tohit_deb, sc)
    p_rn = incoming_hit(_bestdef(("Ranged", "AoE", "Energy")), tohit_deb, sc)
    res_sl = ((sb.get("resistance") or {}).get("Smashing") or 0) / 100.0 * _INHERIT_SHARE
    incoming = (sc["enemies"] * sc["enemy_dps"] * (0.5 * p_ml + 0.5 * p_rn)
                * (1.0 - min(res_sl, 0.90)) / max(bodies, 1))
    regen = hp * _REGEN_PER_SEC * (1.0 + (sb.get("regeneration") or 0) / 100.0
                                   * _INHERIT_SHARE)
    ttl = hp / max(incoming - regen, 1.0)
    downtime = (pet.get("resummon_cast") or 0.0) + upgrade_cast
    if downtime <= 0:
        return 1.0
    return ttl / (ttl + downtime)


def _def_against(totals, kind_keys):
    """Defense the game would apply: BEST of the applicable typed/positional values."""
    d = totals.get("defense") or {}
    vals = [(d.get(k) or {}).get("value", 0) / 100.0 for k in kind_keys]
    return max(vals) if vals else 0.0


# ── v31 AFK sustain assessment (Joel's ruling, 2026-07-16) ───────────────────
# When a combo cannot meet the AFK regen floor, the certificate does not relax
# the floor and does not hold certification — it states, from this model's own
# arithmetic, the difficulty tier the build DOES sustain. The requirement
# ladder scales Maelwys's +4x8 absolute (35–40 HP/s; we ask 37) by the critter
# accuracy multiplier per shift (_LEVEL_ACC) — at the defense softcap the
# incoming stream is accuracy-bound, and per-hit damage stays the scenario
# constant (stated simplification, the same structure the SCENARIOS table
# itself uses). The sustain ledger: regen + the SINGLE best self-heal power's
# sustained rate (heal-strength multiplied) — AFK play allows exactly ONE
# auto-fire power, so aggregating multiple click heals would certify a rate no
# absent player can click (caught on the very first stamp: Aid Self + Healing
# Flames both priced). Rezzes are excluded — a rez fires when you're already
# dead. Per-power rates use BASE recharge (no recharge credit): conservative,
# stated.
AFK_SUSTAIN_ASK_HPS = 37.0

_BUFF_PROC_TABLE = None


def _buff_proc_table():
    """data/buff_proc_catalog.json (tools/extract_buff_procs.py) — buff procs
    the DAMAGE proc_catalog never covered."""
    global _BUFF_PROC_TABLE
    if _BUFF_PROC_TABLE is None:
        import json as _json
        import sys as _sys
        if getattr(_sys, "frozen", False):
            base = getattr(_sys, "_MEIPASS", os.path.dirname(_sys.executable))
        else:
            base = os.path.join(os.path.dirname(__file__), "..")
        try:
            with open(os.path.join(base, "data", "buff_proc_catalog.json"),
                      encoding="utf-8") as f:
                _BUFF_PROC_TABLE = _json.load(f)
        except Exception:  # noqa: BLE001
            _BUFF_PROC_TABLE = {}
    return _BUFF_PROC_TABLE


def _expected_capped_stacks(n, p, cap):
    """E[min(cap, X)] for X ~ Binomial(n, p) — exact, not the naive n·p.

    The naive expectation ignores the cap and over-credits; at realistic aura
    rates the two barely differ (the distribution's mass sits below the cap),
    but the exact form is cheap and never lies at high PPM."""
    if n <= 0 or p <= 0:
        return 0.0
    from math import comb
    exp = 0.0
    # P(X = k) for k < cap, then the whole tail collapses onto `cap`
    tail = 1.0
    for k in range(0, int(cap)):
        pk = comb(n, k) * (p ** k) * ((1 - p) ** (n - k))
        exp += k * pk
        tail -= pk
    exp += cap * max(0.0, tail)
    return exp


def buff_proc_sustain(powers, ctx):
    """v33 ruling C (Maelwys round 5: the Unrelenting Fury regen proc was
    unpriced sustain). Buff procs slotted in an always-on TOGGLE/AUTO aura roll
    on the client's own activate_period, exactly like v32's damage aura procs —
    same measured area factor (engine.AURA_PATCH_AF_MEASURED), because it is
    the same roll. Each hit grants a +Regen buff for `duration_s`, stacking to
    the record's cap, so the sustained credit is the AVERAGE number of stacks
    alive: E[min(cap, Binomial(duration/period, chance))] × the buff's own
    magnitude (scale × its modifier table, the engine's own unit convention).

    Passive by construction — a proc is not a click, so this never conflicts
    with the one-auto-fire-heal rule.

    ⚠ STATED SCOPE (v33): the credit lands in the AFK SUSTAIN LEDGER only, not
    in general passive totals — so a non-AFK build's survival math does not see
    it. Conservative and deliberate: widening it would move every champion that
    slots the piece, which ruling C did not authorize.
    ⚠ STATED DATA CONFLICT: the effect template's stack_limit (2) disagrees
    with the piece's help text ("stacks up to 5 times"). We use the template —
    the conservative reading, which errs AGAINST our own sustain claim. At
    realistic rates the average sits ~1.1, below either cap.
    ⚠ STATED COVERAGE: the catalog holds the Boosts→Grant_Power→Set_Bonus proc
    shape (both Unrelenting Fury tiers). Other buff-proc shapes (Panacea /
    Performance Shifter class) are NOT in it and stay unpriced — the same
    honest exclusion pattern, extendable when their shape is verified.
    """
    from engine import AURA_PATCH_AF_MEASURED
    table = _buff_proc_table()
    if not table:
        return 0.0, []
    mod_tables = ctx.get("modifier_tables") or {}
    col = ctx.get("at_column")
    pbf = ctx.get("power_by_full") or {}
    regen_pct, details = 0.0, []
    for p in (powers or []):
        rec = pbf.get(p.get("full_name"))
        if not rec:
            continue
        period = rec.get("activate_period") or 0.0
        if period <= 0:          # not an aura/auto tick host
            continue
        for slot in (p.get("slots") or []):
            if not slot:
                continue
            entry = table.get(slot.get("piece_uid"))
            if not entry:
                continue
            scale = (entry.get("effects") or {}).get("Regeneration")
            if not scale:
                continue
            tname = (entry.get("tables") or {}).get("Regeneration")
            row = mod_tables.get(tname)
            if not row or col is None or col >= len(row):
                continue
            chance = min(0.90, (entry.get("ppm") or 0) * period
                         / (60.0 * AURA_PATCH_AF_MEASURED))
            dur = entry.get("duration_s") or 0.0
            cap = entry.get("stack_limit") or 1
            n = int(dur // period)
            stacks = _expected_capped_stacks(n, chance, cap)
            per_stack = scale * row[col]
            add = stacks * per_stack
            regen_pct += add
            details.append({
                "piece": slot.get("piece_uid"),
                "host": (rec.get("full_name") or "").split(".")[-1],
                "period": period, "chance": round(chance, 4),
                "avg_stacks": round(stacks, 3), "cap": cap,
                "per_stack_pct": round(per_stack * 100, 1),
                "regen_pct": round(add * 100, 1),
            })
    return regen_pct, details


_ACCOLADE_TABLE = None

# v33 ruling B: the four accolades the community's farm builds assume (exactly
# the four Maelwys's three reference .mbd files carry). The roster/effects come
# from data/accolades.json — the GAME's own records, which correct the common
# "+HP/+End four" shorthand: The Atlas Medallion is +Endurance ONLY, Task Force
# Commander is +MaxHP ONLY.
FARM_ASSUMED_ACCOLADES = ("Task_Force_Commander", "The_Atlas_Medallion",
                          "Freedom_Phalanx_Reserve", "Portal_Jockey")


def _accolade_table():
    global _ACCOLADE_TABLE
    if _ACCOLADE_TABLE is None:
        import json as _json
        import sys as _sys
        if getattr(_sys, "frozen", False):
            base = getattr(_sys, "_MEIPASS", os.path.dirname(_sys.executable))
        else:
            base = os.path.join(os.path.dirname(__file__), "..")
        try:
            with open(os.path.join(base, "data", "accolades.json"),
                      encoding="utf-8") as f:
                _ACCOLADE_TABLE = _json.load(f)
        except Exception:  # noqa: BLE001
            _ACCOLADE_TABLE = {}
    return _ACCOLADE_TABLE


def accolade_bonus_hp(ctx, names=FARM_ASSUMED_ACCOLADES):
    """Flat +MaxHP the named accolades grant, from the game's own records
    (scale × the effect's modifier table — the engine's unit convention for a
    power's HitPoints effect: flat hit points, not a fraction)."""
    tbl = _accolade_table()
    mod_tables = ctx.get("modifier_tables") or {}
    col = ctx.get("at_column")
    flat = 0.0
    got = []
    for n in names:
        rec = tbl.get(n)
        if not rec:
            continue
        scale = (rec.get("effects") or {}).get("HitPoints")
        if not scale:
            continue
        row = mod_tables.get((rec.get("tables") or {}).get("HitPoints"))
        if not row or col is None or col >= len(row):
            continue
        flat += scale * row[col]
        got.append(rec.get("display") or n)
    return flat, got


def afk_sustain_assessment(powers, totals, arch_row, ctx, role_output_mod=None,
                           assume_accolades=False):
    """The AFK sustain ledger + the sustained tier, for the certification label.

    `assume_accolades` (v33 ruling B): farm presets model the four standard
    accolades because every community reference build assumes them (Maelwys's
    three .mbd files carry exactly these four) — and our numbers read
    artificially low against his without them. The assumption is STATED on the
    label, never silent, and it is OFF everywhere else."""
    base_hp = (arch_row or {}).get("hitpoints") or 1000
    hp = base_hp * (1.0 + _pct(totals, "max_hp"))
    acc_hp, acc_names = (0.0, [])
    if assume_accolades:
        acc_hp, acc_names = accolade_bonus_hp(ctx)
        hp += acc_hp
    # v33 C: buff procs in always-on auras add sustained +Regen the totals have
    # never carried (the Unrelenting Fury ATO — Maelwys round 5). Ledger-only
    # by design; see buff_proc_sustain's stated scope.
    proc_regen_pct, proc_regen_detail = buff_proc_sustain(powers, ctx)
    regen_hps = hp * _REGEN_PER_SEC * (1.0 + _pct(totals, "regeneration")
                                       + proc_regen_pct)
    heal_str = 1.0 + _pct(totals, "heal_strength")
    heal_rates, auto_name, auto_hps = [], None, 0.0
    if role_output_mod:
        pbf = ctx.get("power_by_full") or {}
        for p in (powers or []):
            rec = pbf.get(p.get("full_name"))
            if not rec:
                continue
            _team, self_hps, is_rez = role_output_mod.power_heal_output(rec, ctx)
            if self_hps <= 0 or is_rez:
                continue
            rate = round(self_hps * heal_str, 2)
            name = (rec.get("full_name") or "").split(".")[-1]
            # An INTERRUPTIBLE heal cannot anchor AFK sustain: every hit taken
            # during the interrupt window cancels the cast, and the AFK scrum
            # is nothing but hits (client interrupt_time via
            # patch_interrupt_times.py — Aid Self 1.0s was priced as 15.7 HP/s
            # it cannot deliver before this gate existed).
            interruptible = (rec.get("interrupt_time") or 0) > 0
            heal_rates.append({"power": name, "self_hps": rate,
                               "interruptible": interruptible})
            if not interruptible and rate > auto_hps:
                auto_name, auto_hps = name, rate
    sustain = regen_hps + auto_hps
    reqs = {n: round(AFK_SUSTAIN_ASK_HPS * _LEVEL_ACC[n] / _LEVEL_ACC[4], 1)
            for n in range(5)}
    tier = max((n for n in reqs if sustain >= reqs[n]), default=None)
    auto_part = (f" + {auto_name} on auto-fire {auto_hps:.1f}" if auto_name else "")
    if proc_regen_pct:
        auto_part += f" (incl. +{proc_regen_pct * 100:.0f}% regen from aura procs)"
    # v33 ruling B: the assumptions ride the label itself — a sustain number is
    # only honest if what it assumed is printed beside it.
    assume_part = (f" Assumes the standard accolades ({', '.join(acc_names)}: "
                   f"+{acc_hp:.0f} HP)."
                   if acc_names else
                   " Assumes NO accolades and no incarnate powers.")
    if tier == 4:
        label = (f"AFK-certified at +4x8: {sustain:.1f} HP/s sustained "
                 f"(regen {regen_hps:.1f}{auto_part}) meets the "
                 f"{AFK_SUSTAIN_ASK_HPS:.0f} HP/s asteroid worst case." + assume_part)
    elif tier is not None:
        label = (f"AFK-certified at +{tier}x8 (sustain {sustain:.1f} HP/s: regen "
                 f"{regen_hps:.1f}{auto_part}); the +4x8 asteroid worst case is "
                 f"unreachable for this combo ({reqs[4]:.0f} HP/s needed)." + assume_part)
    else:
        label = (f"Does not sustain AFK play at any shift ({sustain:.1f} HP/s vs "
                 f"{reqs[0]:.0f} needed at +0x8) — active play only." + assume_part)
    return {"hp": round(hp, 1), "regen_hps": round(regen_hps, 2),
            "auto_fire_heal": auto_name, "auto_fire_hps": auto_hps,
            "heal_rates": heal_rates,
            "assumed_accolades": acc_names, "accolade_hp": round(acc_hp, 1),
            "buff_proc_regen_pct": round(proc_regen_pct * 100, 1),
            "buff_proc_detail": proc_regen_detail,
            "sustain_hps": round(sustain, 2), "requirements": reqs,
            "tier": tier, "label": label}


def encounter_value(archetype, powers, ctx, totals, scenario="general", arch_row=None,
                    role_output_mod=None):
    """Expected contribution of this build to the scenario's fight. Pure arithmetic — see header."""
    sc = SCENARIOS.get(scenario) or SCENARIOS["general"]
    off = totals.get("offense") or {}
    ro = role_output_mod
    # Purple Patch (wiki-verified): EVERYTHING the player does to higher foes scales down —
    # damage, debuff strength, mez duration. ×0.65 at +3, ×0.48 at +4.
    pp = _PP_BELOW.get(sc.get("shift", 0), 0.30)
    # AV innate debuff resistance (always-on, 0.85 @50) — hits every debuff EXCEPT −Resistance.
    dres = 1.0 - sc.get("debuff_res", 0.0)
    # CLICK-BUFF RECHARGE (Hasten) — computed up front because debuff UPTIME (v11) needs the
    # build's real recharge: the engine excludes click buffs from passive totals by design,
    # which made dropping Hasten FREE in-model — an unfair trial. First-order physics: Hasten
    # gives +70% recharge with uptime = 120s ÷ its own cycle (450s base ÷ (1 + passive recharge
    # + its own ~+95% slotting)); cycling rates scale with total recharge, so credit the
    # time-averaged bonus to the recharge-bound share of damage (~half) and to control cycling
    # (fully). Elasticities are model constants (flagged), the uptime arithmetic is the game's.
    passive_rech = _pct(totals, "recharge")
    hasten_mult_dmg = hasten_mult_ctrl = 1.0
    h_avg = 0.0
    if any((p.get("full_name") or "").endswith(".Hasten") for p in (powers or [])):
        cycle = 450.0 / (1.0 + passive_rech + 0.95)
        h_avg = 0.70 * min(1.0, 120.0 / max(cycle, 1.0))
        hasten_mult_dmg = 1.0 + 0.5 * h_avg / (1.0 + passive_rech)
        hasten_mult_ctrl = 1.0 + h_avg / (1.0 + passive_rech)
    # ENHANCEMENT- + UPTIME-AWARE debuffs (v10 Envenom fix, v11 crash-nuke fix): −def/−tohit
    # scaled by the host power's own post-ED enhancement, −res procs (Achilles' Heel) priced,
    # click debuffs weighted by duration ÷ enhanced recharge (EMP Pulse/Fallout no longer count
    # as permanent). Falls back to the engine's base summary when role_output isn't supplied.
    edeb = ro.enhanced_debuff_totals(powers, ctx,
                                     global_recharge=passive_rech + h_avg) if ro else None

    def _deb(effect):
        if edeb is not None:
            return (edeb.get(effect) or 0.0) / 100.0
        return sum(abs(d.get("pct", 0)) for d in (off.get("debuffs") or [])
                   if d.get("effect") == effect) / 100.0

    # ── SURVIVAL: how long do I live in this spawn? (hit chance → damage in → HP+sustain) ──
    # Incoming mix (coarse): half melee-ish smash/lethal, half ranged/aoe — defense picks its best
    # applicable value per attack, so evaluate the two halves separately.
    # DDR haircut (v10): a squishy has ZERO defense-debuff resistance — incoming −def erodes the
    # soft-cap and can cascade. Scenario-scaled pressure devalues pure def stacking slightly and
    # re-values the resistance BEHIND it (the backstop when defense cracks).
    ddr_in = sc.get("def_debuff_in", 0.0)
    def_ml = max(_def_against(totals, ["Melee", "Smashing", "Lethal"]) - ddr_in, 0.0)
    def_rn = max(_def_against(totals, ["Ranged", "AoE", "Energy"]) - ddr_in, 0.0)
    tohit_deb = _deb("ToHit") * pp * dres   # enhancement-aware, purple-patched, AV-resisted
    p_ml = incoming_hit(def_ml, tohit_deb, sc)
    p_rn = incoming_hit(def_rn, tohit_deb, sc)
    res_sl = (((totals.get("resistance") or {}).get("Smashing") or {}).get("value", 0) or 0) / 100.0
    incoming = sc["enemies"] * sc["enemy_dps"] * (0.5 * p_ml + 0.5 * p_rn) * (1.0 - min(res_sl, 0.90))
    base_hp = (arch_row or {}).get("hitpoints") or 1000
    hp = base_hp * (1.0 + _pct(totals, "max_hp"))
    regen_hps = hp * _REGEN_PER_SEC * (1.0 + _pct(totals, "regeneration"))
    self_heal_hps = 0.0
    if ro:
        h = ro.build_heal_output(powers, ctx)
        self_heal_hps = h["self_hps"]
        team_heal_hps = h["team_hps"]
        rezzes = h["rez"]
    else:
        team_heal_hps, rezzes = 0.0, 0
    # v29 HEAL STRENGTH: the game's 11 heal-strength set bonuses (Numina 4pc +6%,
    # Doctored Wounds 4pc +4%, Panacea 6pc +6%…) multiply the healing the build's
    # own powers put out — game-verified values back-filled from the client
    # (tools/patch_heal_strength.py). Set bonuses bypass ED, so a plain multiplier
    # on the enhanced heal output is the game's own arithmetic. Boundary condition
    # honored: this term exists BEFORE any healer-role champion is certified.
    heal_str = 1.0 + _pct(totals, "heal_strength")
    self_heal_hps *= heal_str
    team_heal_hps *= heal_str
    net_in = max(incoming - regen_hps - self_heal_hps, 1.0)
    ttl = hp / net_in                                  # time-to-live in this spawn
    # Smooth availability: surviving margin keeps diminishing value (alpha spikes, streaks) —
    # the gradient only STOPS when the to-hit floor stops it. That's how the 45% softcap emerges
    # as a derived kink instead of a coded target.
    availability = 1.0 - math.exp(-ttl / sc["length"])
    # v30 KNOCKBACK PROTECTION (threshold): knocked-down seconds are dead seconds —
    # same units as being dead, so it folds into availability. Standard content KB
    # is mag ≤ 4 (the game's own −KB IOs grant exactly 4 — the design's tell,
    # client-baked in set_details); protection covers proportionally below that.
    # Sources feeding totals: back-filled set bonuses (Kinetic Crash 4pc…) + the
    # three stackable −KB piece globals. STATED EXCLUSION: power-granted KB
    # protection (Acrobatics, armor status toggles) is not in totals yet — armor
    # ATs read as unprotected here; the term UNDERSTATES their builds equally.
    _bx = totals.get("bonus_extras") or {}
    kb_prot = (_bx.get("kb_protection") or {}).get("value") or 0.0
    availability *= 1.0 - sc.get("kb_in", 0.0) * (1.0 - min(kb_prot / 4.0, 1.0))

    # ── OUTPUT: damage I deal + damage I CREATE for the team (−res multiplies everyone) ──
    # Outgoing hit chance (wiki): base 75% at +0 falls to 48%/39% at +3/+4 — recovered by ToHit
    # buffs (Tactics/Kismet, inside the clamp), Accuracy (outside), and (v12) the enemy's OWN
    # debuffed defense — my −def raises MY hit chance too, not just the team's.
    def_deb = _deb("Defense")
    def_deb_eff = def_deb * pp * dres
    p_out = outgoing_hit(_pct(totals, "tohit"), _pct(totals, "accuracy"), sc, def_deb_eff)
    my_dps = (off.get("st_dps") or 0) * 0.4 + (off.get("aoe_dps") or 0) * min(sc["enemies"], 10) * 0.6
    # v30 SLOW RESIST: incoming −recharge (sc slow_in) stretches the attack chain;
    # resist recovers it. Recharge-bound share of output = 0.5, the model's
    # established elasticity (Hasten/team-recharge terms). Buff/debuff CYCLE
    # stretching (Hasten/Farsight uptime under slows — the same lever Joel's
    # Hasten-aversion guards) is additional and unmodeled: honest UNDERSTATEMENT.
    slow_res = ((_bx.get("slow_resist") or {}).get("value") or 0.0) / 100.0
    my_dps *= 1.0 - 0.5 * sc.get("slow_in", 0.0) * (1.0 - min(slow_res, 1.0))
    # pets contribute the SQUAD's uptime-weighted DPS (v26): each × count × uptime —
    # per-pet alone undercounted a 6-henchman Mastermind and overcounted timed summons.
    # v29: each HENCHMAN's contribution is additionally weighted by its survival
    # availability (renewal: alive ttl, dead for the resummon+re-upgrade casts) —
    # dead henchmen deal nothing, and inherited set bonuses (the 50% share,
    # bins-verified) are what keep the squishy tiers alive. Non-henchman pets
    # have no inheritance and keep the pre-v29 always-up assumption.
    _hench_n = sum((p.get("count") or 1) for p in (off.get("pets") or [])
                   if (p.get("pet_class") or "") in _HENCH_HP50)
    _up_cast = 0.0
    if _hench_n:
        # the spawn's damage spreads across every body on the field
        _bodies = sc["teammates"] + 1 + _hench_n
        # re-upgrade overhead: every MM primary carries exactly TWO upgrade
        # powers — effect-less clicks in the summon powerset (grant-power
        # redirects the parser sees as empty). Two lowest casts win the tie
        # when a set also parses a click buff effect-less (Beast Mastery).
        pbf = (ctx or {}).get("power_by_full") or {}
        recs = [pbf.get(p.get("full_name")) for p in (powers or [])]
        summon_sets = {r.get("powerset_full_name") for r in recs
                       if r and r.get("summons")}
        cands = sorted((r.get("cast_time") or 0.0) for r in recs
                       if r and r.get("powerset_full_name") in summon_sets
                       and not r.get("summons") and not r.get("damage_effects")
                       and not r.get("buff_effects") and not r.get("heal_effects")
                       and (r.get("cast_time") or 0) > 0)
        _up_cast = sum(cands[:2])
        my_dps += sum((p.get("dps_total") or p.get("dps_each") or p.get("dps") or 0)
                      * _henchman_availability(p, totals, sc, tohit_deb,
                                               _bodies, base_hp, _up_cast)
                      for p in (off.get("pets") or []))
    else:
        my_dps += sum((p.get("dps_total") or p.get("dps_each") or p.get("dps") or 0)
                      for p in (off.get("pets") or []))
    my_dps *= p_out * pp * hasten_mult_dmg   # hit chance × purple patch × click-recharge credit
    # ENDURANCE ECONOMY v35 (fight-duration model — Joel's §8 rulings 2026-07-21; replaces the
    # v10 sqrt haircut + 0.45 floor AND the v20 silent end_relief): the honest physics of a
    # fixed endurance bar over THIS scenario's own fight length L. Full output until the bar
    # empties at T_empty = E_max/(D−R); after that the player can only spend as fast as it
    # comes in — fixed toggles are paid first, the remainder runs the chain at f_sus.
    #   - Recovery is BARE build totals (Q4): no silent incarnate relief. A build that
    #     declares incarnates carries that credit in its own totals, stated on the label.
    #   - Floor RETIRED (Q2a): a bar that empties and can't act earns nothing — blues/
    #     Ageless are the player's own margin, honest unmodeled upside.
    #   - ONE path for all scenarios (Q2b): short fights read ≈1.0 on their own (the bar
    #     barely empties), a 240s AV fight collapses an end-broken kit to its real output.
    #   - Travel-toggle drain joins the fight only when the build declares a ranged/hover
    #     playstyle (Q3 — engine stamps travel_in_combat; displayed ledger always shows it).
    #   - Mule-vs-Leadership guard (the v20 motivation, re-derived): a real toggle set costs
    #     ~1/s — nowhere near the >E_max/L deficit needed to trigger ANY penalty on short
    #     fights, so the phantom endurance crisis that made mules beat Maneuvers cannot recur.
    # NEGATIVE CONTROL (mandatory, §7): drain ≤ recovery ⇒ end_factor = 1.0, every scenario.
    endb = totals.get("endurance") or {}
    d_chain = endb.get("chain_drain_per_sec") or 0.0
    d_tog = endb.get("toggle_drain_per_sec") or 0.0
    if endb.get("travel_in_combat"):
        d_tog += endb.get("travel_toggle_drain_per_sec") or 0.0
    drain = d_chain + d_tog
    rec_ps = endb.get("recovery_per_sec") or 0.0
    e_max = endb.get("max_end_pool") or 100.0
    fight_len = sc.get("length", 30.0)
    if drain <= max(rec_ps, 0.01):
        end_factor = 1.0                     # sustainable — no penalty, ever
    else:
        t_empty = e_max / (drain - rec_ps)   # seconds of full output before the bar drains
        f_sus = (min(max((rec_ps - d_tog) / d_chain, 0.0), 1.0)
                 if d_chain > 0 else 0.0)    # post-empty chain rate recovery can afford
        if t_empty >= fight_len:
            end_factor = 1.0                 # never empties within this fight
        else:
            end_factor = (t_empty + (fight_len - t_empty) * f_sus) / fight_len
    my_dps *= end_factor
    res_deb = _deb("Resistance")            # incl. Achilles-class −res procs (v10)
    # TEAM BUFFS (v14, the Accelerate-Metabolism fix): sustained, uptime-weighted ally buffs —
    # click buffs like AM (+dmg/+rech to 8 people, 120s per 422s cycle) were priced at ZERO,
    # so the search dropped them. Buffs are unresistible (wiki) — no dres, no purple patch.
    tb = (ro.enhanced_team_buffs(powers, ctx, global_recharge=passive_rech + h_avg)
          if ro else {})
    dmg_buff = (tb.get("DamageBuff") or tb.get("Damage") or 0.0) / 100.0
    team_rech_buff = (tb.get("RechargeTime") or 0.0) / 100.0
    team_res_buff = (tb.get("Resistance") or 0.0) / 100.0
    # v16: Tactics-class +ToHit and Maneuvers-class +Defense for the team — the buff-side
    # mirrors of the −def (v12) and −tohit (v15) terms. Buffs are unresistible, no purple patch.
    team_tohit_buff = (tb.get("ToHit") or 0.0) / 100.0
    team_def_buff = (tb.get("Defense") or 0.0) / 100.0
    team_pool = sc["teammates"] * sc["team_dps"]
    # WIKI Resistance (Mechanics), verified: a resistible −res debuff makes the target take EXACTLY
    # the debuff amount more damage regardless of its own resistance (self-cancelling algebra), and
    # stacks resist against the UNDEBUFFED value → stacking is LINEAR, no cascade, no diminishing.
    # So −res amplification is cleanly additive; the cap (0.90) reflects application/uptime realism
    # (not every stack on every foe at all times), not the game math.
    # −Res: purple-patched but NOT AV-resisted (absent from the AV debuff-resist list — the
    # wiki-verified reason −res is the AV lever while −tohit/−regen get gutted ×0.15).
    amplified = (team_pool + my_dps) * min(res_deb * pp, 0.90) + team_pool * min(dmg_buff, 0.50) * 0.5
    # Team +RECHARGE (v14): cycling rates scale with recharge — same elasticity as the Hasten
    # term (recharge-bound share of damage ≈ half).
    amplified += team_pool * min(team_rech_buff, 0.50) * 0.5

    # ── PREVENTION: control locks foes (their dps → 0 while mezzed); −dmg debuffs shrink it;
    #    team heals restore it. All measured in the same units: enemy damage that never lands. ──
    prevented = 0.0
    if ro:
        # v30 MEZ DURATION: the back-filled duration bonuses ('Ultimate Hold
        # Duration' +N%…) are more mez-seconds per cast — multiplied per mez type
        # inside the control score (universal physics; the role lens already
        # weights control output by declared role, so control roles reap it —
        # invisible-role doctrine: duration × uptime IS the output).
        _mzd = {m: (v or 0.0) / 100.0
                for m, v in (_bx.get("mez_duration") or {}).items()}
        ctrl_score, _ = ro.build_control_output(powers, ctx, mez_dur=_mzd or None)
        # control score ≈ Σ weighted mez-seconds × area per cast cycle, then wiki-verified physics:
        # × pp (Purple Patch shrinks mez DURATION vs +N) × ctrl_land (Protection table: what a
        # mag-3 control actually lands on in this spawn's rank mix — near-nothing on an AV whose
        # triangles put protection at 53). Cap = locking the whole spawn 90% of the time.
        ctrl_score *= pp * sc.get("ctrl_land", 0.9) * hasten_mult_ctrl * (end_factor ** 0.5)
        prevented += min(ctrl_score / 900.0, 0.9) * sc["enemies"] * sc["enemy_dps"]
    dmg_deb = _deb("Damage")
    prevented += sc["enemies"] * sc["enemy_dps"] * min(dmg_deb * pp * dres, 0.5) * 0.5
    # −REGEN: strips the enemy's sustain (dps-equivalent). THE Archvillain lever — AVs resist it
    # (0.85 innate, in the wiki AV list) yet their regen is so large that what survives the resist
    # still decides the fight. Trash barely regens, so it prices near zero there — derived, not ruled.
    regen_deb = _deb("Regeneration")
    prevented += sc.get("enemy_regen", 0) * min(regen_deb * pp * dres, 1.0)
    # −RECHARGE / slows: enemies attack (and act) slower — prevention proportional to the slow,
    # at half credit (enemy AI wanders, not every lost second was an attack). Movement slow
    # (the wiki's -SPD family, incl. huge run-speed floors) counts at quarter weight, capped —
    # it delays repositioning/melee, it does not slow attack animations (provisional, flagged).
    rech_deb = _deb("RechargeTime") + 0.25 * min(_deb("Slow"), 1.0)
    prevented += sc["enemies"] * sc["enemy_dps"] * min(rech_deb * pp * dres, 0.6) * 0.5
    # −DEFENSE (v12, physics-derived): raises the TEAM's hit chance toward the 95% ceiling via
    # the same wiki arithmetic as everything else (Base + ToHit − Def inside the clamp, Accuracy
    # outside). Credit = the ACTUAL damage gain of an average teammate's hit chance, which
    # saturates at the ceiling on its own — no judgment cap. Replaces v9's flat min(deb, 0.15).
    p_team0 = outgoing_hit(_TEAM_TOHIT_AVG, _TEAM_ACC_AVG, sc)
    p_team1 = outgoing_hit(_TEAM_TOHIT_AVG + team_tohit_buff, _TEAM_ACC_AVG, sc, def_deb_eff)
    amplified += team_pool * (p_team1 - p_team0) / max(p_team0, 0.05)
    # Team heals restore HP/s ≈ damage undone — but only for teammates who EXIST: a group
    # heal's area value scales with the scenario's team, zero solo (its self-share is a small
    # understatement, flagged — heal_output splits self vs team by target, not per-power).
    prevented += team_heal_hps * min(1.0, sc["teammates"] / 7.0)
    # ALLY +RES shields (v14: Sonic Dispersion/Barrier/Haven, Cold/Thermal shields): prevent
    # the team's share of incoming damage × the shield's resistance. Buffs are unresistible
    # (wiki); ×0.5 for teammates' own existing resistance (provisional constant, flagged).
    if sc["teammates"]:
        team_in = sc["enemies"] * sc["enemy_dps"] * 0.5 \
            * (sc["teammates"] / (sc["teammates"] + 1.0))
        prevented += team_in * min(team_res_buff, 0.75) * 0.5
        # −TOHIT protects the TEAM (v15, the Dark Miasma term): enemy accuracy floored for
        # everyone — same wiki hit arithmetic as the caster's own survival, applied to an
        # average teammate. Purple-patched + AV-resisted already (tohit_deb upstream).
        p_in0 = incoming_hit(_TEAM_DEF_AVG, 0.0, sc)
        p_in1 = incoming_hit(_TEAM_DEF_AVG + team_def_buff, tohit_deb, sc)
        prevented += sc["enemies"] * sc["enemy_dps"] * (p_in0 - p_in1) \
            * (sc["teammates"] / (sc["teammates"] + 1.0))
    # A rez restores ONE teammate's output for part of the fight — worth ~15% of a teammate's dps
    # per fight (long recharges cap it at ~once), and nothing solo. (The flat 40/s it briefly had
    # was found and farmed by the optimizer — the model must price physics, not constants.)
    prevented += (0.15 * sc["team_dps"] if sc["teammates"] else 1.0) * min(rezzes, 2)

    # v33 SCENARIO RULING (Joel, 2026-07-16 — farm_active): "survival is
    # constraints, not objective." The 45/90 asks stay HARD (the preset declares
    # them; the strict A2 guard enforces them), but above that floor extra
    # survival must buy ~nothing in the objective — DAMAGE THROUGHPUT decides the
    # picks. Availability multiplying the objective is precisely what out-bid
    # Irradiated Ground: every swap toward damage lost on availability/set-bonus
    # economics even when its DPS rose. So for this scenario the objective uses
    # availability 1.0; the TRUE measured availability is still reported (below)
    # for the certificate and display — the honesty is that we state we stopped
    # scoring it, not that we pretend it is 1.
    avail_obj = 1.0 if sc.get("survival_is_constraint") else availability
    contribution = avail_obj * (my_dps + amplified + prevented)
    return {
        "contribution": round(contribution, 1),
        "availability": round(availability, 3),
        "availability_objective": round(avail_obj, 3), "ttl": round(ttl, 1),
        "my_dps": round(my_dps, 1), "amplified": round(amplified, 1),
        "prevented": round(prevented, 1),
        "hit_ml": round(p_ml, 3), "hit_rn": round(p_rn, 3), "hit_out": round(p_out, 3),
    }
