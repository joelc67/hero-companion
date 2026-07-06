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

# Bump on ANY physics/term change. Lessons and champions are stamped with this: proposer BIAS
# (lessons) from an older model version is ignored — conclusions drawn by a blinder model must
# not steer the proposer after the model improves (measured: run 9, blind to Carrion Creepers'
# vine damage, taught autopick to drop it; the fix landed and the stale lesson kept biting).
MODEL_VERSION = 25     # v25: ST PROC HYBRIDS — a long-recharge single-target attack/hold keeps a 2-3 piece acc/dam core (recharge-free: local recharge divides proc chance) and fills its tail slots with damage procs once the PPM math clears ~50%/roll (the Dominate / Seismic Smash master pattern; capacity counted by distinct proc SETS; pet summons excluded — henchman procs are the pet's own model, task #33) + proc-catalog PPM values now authoritative from the game client (11 fixed; ATO procs were 30-43% undervalued); v24: CURRENT-META CALIBRATION from the 2,255-build Sovereign corpus + the master builder's doctrine — damage-proc PPM pricing in the engine (procs are DEAL, tradeable against set bonuses), typed S/L/F/C-35 default targets (positional-armor builds swap to Melee/Ranged/AoE 35; "classic softcap" goal restores 45s), Hasten hard 2-slot rule; v23: FOCUS SPLIT (role_mix — ask the user their percentage split when sets support multiple roles); v22: role lens × playstyle (solo relaxes to raw physics — 'whole team in one character') + wiki Role Diversity natural-roles table; v21: ROLE LENS (declared role weights the objective — role-based game first, off-role only by explicit pick); v20: scenario end_relief (incarnate-era recovery — mules stop beating Leadership via a phantom endurance crisis); v19: debuffer proc pass = res/anchor procs ONLY (no damage bombing — his damage is 1/9th of the league's; every −res proc placed, last-piece swaps, premium homes protected); v18: no pool/inherent melee in ranged ST chains + pure-ADD moves; v17: attack cast budget; v16: team buffs; v15: team −tohit; v14: ally buffs; v13: Redirects; v12: −def; v11: uptime; v10: enh-aware

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
    "general":   dict(enemies=4,  enemy_dps=90,  teammates=0, team_dps=110, length=30.0,  shift=1, rank_acc=1.05, ctrl_land=0.95, debuff_res=0.0,  enemy_regen=5,   def_debuff_in=0.03),
    "team":      dict(end_relief=0.25, enemies=8,  enemy_dps=90,  teammates=7, team_dps=110, length=25.0,  shift=2, rank_acc=1.10, ctrl_land=0.92, debuff_res=0.0,  enemy_regen=8,   def_debuff_in=0.04),
    "itrial":    dict(end_relief=0.5, enemies=10, enemy_dps=130, teammates=7, team_dps=130, length=30.0,  shift=3, rank_acc=1.20, ctrl_land=0.87, debuff_res=0.0,  enemy_regen=15,  def_debuff_in=0.07),
    "fire_farm": dict(enemies=10, enemy_dps=110, teammates=0, team_dps=0,   length=20.0,  shift=4, rank_acc=1.00, ctrl_land=0.95, debuff_res=0.0,  enemy_regen=5,   def_debuff_in=0.05),
    "av":        dict(end_relief=0.5, enemies=1,  enemy_dps=220, teammates=0, team_dps=0,   length=240.0, shift=2, rank_acc=1.50, ctrl_land=0.08, debuff_res=0.85, enemy_regen=120, def_debuff_in=0.10),
}

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
    return ev["availability"] * (wd * ev["my_dps"] + wa * ev["amplified"]
                                 + wp * ev["prevented"])


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


def _def_against(totals, kind_keys):
    """Defense the game would apply: BEST of the applicable typed/positional values."""
    d = totals.get("defense") or {}
    vals = [(d.get(k) or {}).get("value", 0) / 100.0 for k in kind_keys]
    return max(vals) if vals else 0.0


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
    net_in = max(incoming - regen_hps - self_heal_hps, 1.0)
    ttl = hp / net_in                                  # time-to-live in this spawn
    # Smooth availability: surviving margin keeps diminishing value (alpha spikes, streaks) —
    # the gradient only STOPS when the to-hit floor stops it. That's how the 45% softcap emerges
    # as a derived kink instead of a coded target.
    availability = 1.0 - math.exp(-ttl / sc["length"])

    # ── OUTPUT: damage I deal + damage I CREATE for the team (−res multiplies everyone) ──
    # Outgoing hit chance (wiki): base 75% at +0 falls to 48%/39% at +3/+4 — recovered by ToHit
    # buffs (Tactics/Kismet, inside the clamp), Accuracy (outside), and (v12) the enemy's OWN
    # debuffed defense — my −def raises MY hit chance too, not just the team's.
    def_deb = _deb("Defense")
    def_deb_eff = def_deb * pp * dres
    p_out = outgoing_hit(_pct(totals, "tohit"), _pct(totals, "accuracy"), sc, def_deb_eff)
    my_dps = (off.get("st_dps") or 0) * 0.4 + (off.get("aoe_dps") or 0) * min(sc["enemies"], 10) * 0.6
    # engine emits 'dps_each' — the old 'dps' read was silently 0 (pet damage never counted!)
    my_dps += sum((p.get("dps_each") or p.get("dps") or 0) for p in (off.get("pets") or []))
    my_dps *= p_out * pp * hasten_mult_dmg   # hit chance × purple patch × click-recharge credit
    # ENDURANCE ECONOMY (v10): a build that bottoms out can't sustain its output — the engine
    # already measures the drain (attack chain + toggles) vs recovery. Sustainable → full credit;
    # unsustainable → sqrt-scaled (fights have gaps; blues/Ageless soften) with a 0.45 floor.
    # This is what stops the model from leaning on Ageless by silent assumption.
    endb = totals.get("endurance") or {}
    drain = endb.get("drain_per_sec") or 0.0
    rec_ps = endb.get("recovery_per_sec") or 0.0
    # Scenario endurance relief (v20): INCARNATE content is played by incarnates — Destiny /
    # accolades / base buffs raise real recovery well above bare build totals. Without this
    # the sustain tax made real toggles (Maneuvers/Tactics) lose to zero-cost dead picks —
    # the model preferred mules because it thought the build couldn't afford Leadership.
    # (provisional constant, flagged: ~+50% recovery at 50+ content.)
    rec_ps *= 1.0 + sc.get("end_relief", 0.0)
    end_factor = 1.0 if drain <= max(rec_ps, 0.01) else max(0.45, (rec_ps / drain) ** 0.5)
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
        ctrl_score, _ = ro.build_control_output(powers, ctx)
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

    contribution = availability * (my_dps + amplified + prevented)
    return {
        "contribution": round(contribution, 1),
        "availability": round(availability, 3), "ttl": round(ttl, 1),
        "my_dps": round(my_dps, 1), "amplified": round(amplified, 1),
        "prevented": round(prevented, 1),
        "hit_ml": round(p_ml, 3), "hit_rn": round(p_rn, 3), "hit_out": round(p_out, 3),
    }
