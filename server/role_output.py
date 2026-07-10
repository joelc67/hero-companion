"""role_output.py — measure a build's CONTROL and DEBUFF *output*, the thing the solver
was blind to. This is the Phase-1 scorecard for the invisible-role ATs (controllers,
dominators, defenders, corruptors): what they actually DO, not how survivable they are.

Control output model (grounded in the real Mids numbers):
  - magnitude = nMag (mez mag: 3 holds a boss, 4 an EB); duration = scale * AttribMod[table][AT].
  - TYPE weight reflects real value: a Hold/Confuse (stops everything / turns the foe) beats an
    Immobilize (stops only movement — but sets up Containment). Sleep is fragile (breaks on hit).
  - AoE control (Glacier, Frostbite) multiplies by targets hit — locking a spawn >> one foe.
  - Toggle auras (Arctic Air) apply continuously, so they're scored as always-on.
  - PvP-only effect variants are excluded for PvE scoring.
Numbers are a defensible PROXY (mez-seconds x magnitude x area x uptime), calibrated to rank
powers/builds sensibly and to quantify tool-vs-master gaps — not a frame-exact sim.
"""

# Control VALUE by mez type (a hold that stops all actions > an immobilize that stops only movement).
CONTROL_WEIGHT = {
    # WIKI-VERIFIED ("Control" + "Status Effect" pages):
    #   Held = no move, no powers (full stop) → 1.0.
    #   Confused (PvE) = the critter ATTACKS ITS ALLIES — its dps isn't just prevented, it's
    #     REDIRECTED at the spawn → worth more than a hold → 1.1.
    #   Disorient/Stunned = no powers, staggers → 0.9.
    #   Sleep = SOFT: "ends early if the target receives damage, is healed, is knocked…" → 0.3.
    #   Immobilized = "may not move, but CAN still use their powers" — positional value only
    #     (melee can't reach you; Containment doubling is priced in the damage side) → 0.35.
    #   Terrorize = cowers; breaks ~every 5s on damage for one action → 0.6.
    #   Knock* = time-to-stand mitigation, per application → ~0.4.
    "Held": 1.0, "Confused": 1.1, "Stunned": 0.9, "Sleep": 0.3,
    "Immobilized": 0.35, "Terrorized": 0.6, "Afraid": 0.45, "Intangible": 0.6,
    "Knockback": 0.4, "Knockup": 0.45, "Repel": 0.2,
}
# Mez APPLICATION is BINARY (wiki Status Effect): magnitude vs target's protection — affected only
# if summed magnitudes EXCEED protection; stacks ADD and re-evaluate as they wear. The mag_factor
# below is a smooth proxy for "how often does this mag beat spawn protection"; the exact per-rank
# protection values are a wiki-ask ("Status Effect Protection" + "Purple Triangles" pages).
_KNOCK = {"Knockback", "Knockup", "Repel"}


def _table_val(mod_tables, name, col):
    row = mod_tables.get(name) if name else None
    if not row or col is None or col < 0 or col >= len(row):
        return 0.0
    return row[col]


def _is_pvp_variant(c):
    return c.get("pv_mode") == 2 or "pvp" in (c.get("modifier_table") or "").lower()


def power_control_output(power, ctx, mez_dur=None):
    """Control-output score for ONE power. mez-seconds x magnitude-factor x area x (toggle uptime).
    mez_dur: optional {mez type: +duration fraction} from the build's set bonuses
    (v30 back-fill — 'Ultimate Confuse Duration' etc.): a duration bonus is more
    mez-seconds per cast, the exact quantity this score measures. Knock* types are
    per-application (time-to-stand), untouched by duration."""
    ce = power.get("control_effects") or []
    if not ce:
        return 0.0
    mod_tables = ctx.get("modifier_tables") or {}
    col = ctx.get("at_column")
    # AoE control locks a spawn; single-target locks one foe.
    radius = power.get("radius") or 0
    area = min(int(power.get("max_targets") or 1), 16) if radius > 0 else 1
    # A toggle aura reapplies continuously → treat its control as always-on (uptime multiplier).
    is_toggle = (power.get("activate_period") or 0) > 0
    by_type = {}          # take the representative (strongest) effect per mez type — avoids
    for c in ce:          # double-counting a hold modeled as stacked magnitude/chance components.
        if _is_pvp_variant(c):
            continue
        mez = c.get("mez")
        w = CONTROL_WEIGHT.get(mez, 0.2)
        mag = c.get("nmag") or 1.0
        mag_factor = max(0.4, min(mag / 3.0, 1.4))       # mag-3 holds a boss = 1.0
        if mez in _KNOCK:
            dur = 3.0                                     # knockdown ≈ per-application mitigation
            mag_factor = 1.0
        else:
            dur = abs(c.get("scale") or 0.0) * _table_val(mod_tables, c.get("modifier_table"), col)
            if dur <= 0:
                dur = c.get("duration") or 0.0
            if mez_dur:
                dur *= 1.0 + (mez_dur.get(mez) or 0.0)
        val = w * mag_factor * dur * (c.get("probability") or 1.0)
        by_type[mez] = max(by_type.get(mez, 0.0), val)
    score = sum(by_type.values()) * area
    if is_toggle:
        score *= 3.0                                     # always-on aura ≈ 3x a one-shot of the same tick
    return round(score, 2)


# ── TRUE control UPTIME (Phase 2b) ──────────────────────────────────────────
# The invisible-role payoff isn't "has a hold" — it's "the hold is ALWAYS up" (perma-control).
# Uptime = enhanced DURATION / enhanced RECHARGE. Enhanced duration = base × (1 + Mez enhancement
# in the power). Enhanced recharge = base_recharge / (1 + global recharge + the power's own recharge
# enhancement). A toggle control aura (Arctic Air) is always-on = 100%. This makes the score
# recharge- AND slotting-aware, so the solver can be aimed at ACTUAL perma-control.
_ED = {"Defense": 1, "Resistance": 1, "ToHit": 1, "Range": 1, "Interrupt": 2, "Mez": 0}


def _apply_ed(sched, val, mult_ed):
    ed = (mult_ed or {}).get(str(sched)) or (mult_ed or {}).get(sched)
    if not ed or val <= ed[0]:
        return val
    edm1 = ed[0] + (ed[1] - ed[0]) * 0.9
    edm2 = edm1 + (ed[2] - ed[1]) * 0.7
    if val > ed[2]:
        return edm2 + (val - ed[2]) * 0.15
    if val > ed[1]:
        return edm1 + (val - ed[1]) * 0.7
    return ed[0] + (val - ed[0]) * 0.9


def _power_enh(power, ctx, aspects):
    """Post-ED enhancement the power's OWN slotting gives per aspect (RechargeTime, Mez…)."""
    pb = ctx.get("piece_boosts") or {}
    tot = {a: 0.0 for a in aspects}
    for slot in (power.get("slots") or []):
        if not slot:
            continue
        for b in pb.get(slot.get("piece_uid")) or []:
            if b["aspect"] in tot:
                tot[b["aspect"]] += b["value"]
    return {a: _apply_ed(_ED.get(a, 0), tot[a], ctx.get("mult_ed")) for a in aspects}


def power_control_uptime(power, ctx, global_recharge_frac):
    """Uptime of one control power. None if it isn't a real hard-control power."""
    hard = [c for c in (power.get("control_effects") or [])
            if c.get("kind") == "hard" and not _is_pvp_variant(c)]
    if not hard:
        return None
    if (power.get("activate_period") or 0) > 0:      # toggle aura — continuously applied
        return {"mez": hard[0].get("mez"), "uptime": 1.0, "perma": True, "toggle": True}
    mod_tables = ctx.get("modifier_tables") or {}
    col = ctx.get("at_column")

    def dur(c):
        return abs(c.get("scale") or 0.0) * _table_val(mod_tables, c.get("modifier_table"), col)
    prim = max(hard, key=dur)
    base_dur = dur(prim)
    base_rech = power.get("base_recharge") or 0.0
    if base_dur <= 0 or base_rech <= 0:
        return None
    enh = _power_enh(power, ctx, ("RechargeTime", "Mez"))
    enh_rech = base_rech / (1.0 + global_recharge_frac + enh["RechargeTime"])
    enh_dur = base_dur * (1.0 + enh["Mez"])
    uptime = min(1.0, enh_dur / enh_rech) if enh_rech > 0 else 1.0
    return {"mez": prim.get("mez"), "uptime": round(uptime, 2), "perma": uptime >= 0.98,
            "enh_recharge": round(enh_rech, 1), "enh_duration": round(enh_dur, 1),
            "base_recharge": round(base_rech, 1)}


def build_control_uptime(powers, ctx, global_recharge_pct):
    """Per-control-power uptime + a summary (how much of the control kit is PERMA)."""
    g = (global_recharge_pct or 0) / 100.0
    rows = []
    for p in powers:
        rec = ctx["power_by_full"].get(p.get("full_name")) if ctx.get("power_by_full") else p
        if not rec:
            continue
        merged = dict(rec, slots=p.get("slots") or rec.get("slots") or [])
        u = power_control_uptime(merged, ctx, g)
        if u:
            rows.append(dict(u, power=rec.get("power_name") or p.get("full_name")))
    perma = sum(1 for r in rows if r["perma"])
    avg = round(sum(r["uptime"] for r in rows) / len(rows), 2) if rows else 0.0
    return {"controls": rows, "perma_count": perma, "control_count": len(rows), "avg_uptime": avg}


# ── PAYOFF: each archetype's core metrics — ONE definition shared by the benchmark and the
# joint optimizer, so the solver literally optimizes what the validation judges (what masters
# are judged on). This is the "final position evaluation" of the think-ahead loop.
AT_PAYOFF = {
    "Class_Blaster": ["st_dps", "aoe_dps", "recharge"],
    "Class_Scrapper": ["st_dps", "aoe_dps", "self_heal"],
    "Class_Stalker": ["st_dps", "aoe_dps", "self_heal"],
    "Class_Brute": ["st_dps", "aoe_dps", "res_sl", "self_heal"],
    "Class_Tanker": ["res_sl", "def_ranged", "st_dps", "self_heal"],
    "Class_Sentinel": ["st_dps", "aoe_dps", "res_sl", "self_heal"],
    "Class_Controller": ["control", "recharge"],
    "Class_Dominator": ["control", "st_dps", "recharge"],
    "Class_Defender": ["support", "heal", "recharge"],
    "Class_Corruptor": ["st_dps", "aoe_dps", "recharge"],
    "Class_Mastermind": ["pet_dps", "recharge"],
    "Class_Peacebringer": ["st_dps", "aoe_dps", "res_sl"],
    "Class_Warshade": ["st_dps", "aoe_dps"],
    "Class_Arachnos_Soldier": ["st_dps", "aoe_dps", "recharge"],
    "Class_Arachnos_Widow": ["st_dps", "aoe_dps"],
}


def payoff_metrics(archetype, powers, ctx, totals):
    """All payoff metrics for a build, from calculate_build display totals + role_output scores."""
    off = totals.get("offense") or {}
    def scal(k):
        x = totals.get(k)
        return round((x.get("value", 0) if isinstance(x, dict) else x) or 0, 2)
    def dv(kind, ty):
        return round((totals.get(kind) or {}).get(ty, {}).get("value", 0), 2)
    ctrl, _ = build_control_output(powers, ctx)
    heal = build_heal_output(powers, ctx)
    return {
        "st_dps": round(off.get("st_dps", 0) or 0, 2),
        "aoe_dps": round(off.get("aoe_dps", 0) or 0, 2),
        "pet_dps": round(sum((p.get("dps_each") or p.get("dps") or 0)
                             for p in (off.get("pets") or [])), 2),
        "control": round(ctrl, 2),
        "support": build_support_output(off),
        "heal": heal["score"], "self_heal": heal["self_hps"],
        "recharge": scal("recharge"), "recovery": scal("recovery"),
        "regen": scal("regeneration"), "max_hp": scal("max_hp"),
        "def_ranged": dv("defense", "Ranged"), "def_aoe": dv("defense", "AoE"),
        "def_melee": dv("defense", "Melee"), "res_sl": dv("resistance", "Smashing"),
    }


def payoff_score(archetype, metrics, baseline=None):
    """One number for 'is this build better for what this AT is FOR' — the payoff metrics
    relative to a baseline (each capped at 2x so one runaway metric can't buy out the rest),
    plus a small survival tiebreaker so payoff gains never come from going glass."""
    keys = AT_PAYOFF.get(archetype, ["st_dps", "aoe_dps"])
    s = 0.0
    for k in keys:
        v = metrics.get(k, 0) or 0
        b = (baseline or {}).get(k, 0) or 0
        s += min(v / b, 2.0) if b > 1e-6 else (1.0 if v > 0 else 0.0)
    tie = 0.0
    for k in ("def_ranged", "def_aoe", "res_sl", "recharge"):
        v = metrics.get(k, 0) or 0
        b = (baseline or {}).get(k, 0) or 0
        tie += min(v / b, 1.5) if b > 1e-6 else 0.0
    return round(s + 0.05 * tie, 4)


# ── SUPPORT output (buff / debuff) — the Defender/Corruptor/support payoff ───
# A support AT's job is buff/debuff MAGNITUDE on the team + foes. Value weights: -Resistance is the
# team's damage force-multiplier; -Regen kills AVs; +Damage/+Recharge buffs multiply team output;
# +Def/+Res shields keep the team alive. Scored from the engine's resolved base magnitudes
# (`offense.debuffs`/`offense.buffs` = {effect, type, pct}).
DEBUFF_W = {"Resistance": 1.3, "Regeneration": 1.0, "ToHit": 0.8, "Defense": 0.8,
            "RechargeTime": 0.7, "Recovery": 0.6, "Slow": 0.5, "Endurance": 0.5, "Damage": 0.9}
# NOTE: "Heal" is deliberately absent — direct healing is scored by build_heal_output (area/uptime/
# self-vs-ally aware), so counting it here too would double-count. Regeneration (sustained heal) stays.
BUFF_W = {"Damage": 1.3, "RechargeTime": 1.1, "Defense": 1.0, "Resistance": 1.0,
          "Recovery": 0.7, "Regeneration": 0.6, "ToHit": 0.7, "HitPoints": 0.6}


# −Res PROCS ("Chance for Res Debuff") — the base debuff summary can't see procs. Priced as
# time-averaged −res on a cycled debuff power (PROVISIONAL constants: Achilles' Heel −20% at
# ~75% effective uptime ≈ 15; Annihilation/Fury-class −12.5% ≈ 10). Detection by piece UID from
# the proc catalog (proc_pass names its pieces just "proc") plus the piece-name fallback.
_RES_PROC_VALUES = {"achilles": 15.0, "annihilation": 8.0, "fury": 15.0}
_RES_PROC_UIDS = None


def _res_proc_uids():
    global _RES_PROC_UIDS
    if _RES_PROC_UIDS is None:
        import json as _json
        import os as _os
        _RES_PROC_UIDS = {}
        try:
            path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                                 "data", "proc_catalog.json")
            cat = _json.load(open(path, encoding="utf-8"))
            for plist in (cat.get("res_procs") or {}).values():
                for p in plist or []:
                    nm = (p.get("set") or "").lower()
                    val = next((v for k, v in _RES_PROC_VALUES.items() if k in nm), 10.0)
                    uid = p.get("uid")
                    _RES_PROC_UIDS[uid] = val
                    if uid and uid.startswith("Crafted_"):
                        # hand-slotted attuned copies price identically
                        _RES_PROC_UIDS["Attuned_" + uid[len("Crafted_"):]] = val
        except Exception:  # noqa: BLE001
            _RES_PROC_UIDS = {}
    return _RES_PROC_UIDS


def enhanced_debuff_totals(powers, ctx, global_recharge=0.0):
    """{effect: total pct} SUSTAINED enemy debuffs — ENHANCEMENT- and UPTIME-AWARE.
    v10 (Envenom fix): −Defense/−ToHit magnitudes scaled by (1 + the host power's own post-ED
    Defense/ToHit enhancement); −res/−regen/−dmg are unenhanceable and stay base. Typed spreads
    (−res to all 8 types) collapse to the per-type value (max). −res procs priced by piece_uid.
    v11 (crash-nuke fix): a CLICK debuff is weighted by its UPTIME — duration ÷ enhanced recharge
    (own post-ED RechargeTime slotting + global_recharge), capped 1 — so a 300s EMP Pulse/Fallout
    no longer counts as a permanent debuff (toggles/autos stay uptime 1). Effect probability is
    clamped to [0,1] — raw Mids rows carry corrupt values >1 (Fallout: 2..9; PROVISIONAL until a
    wiki page settles what that field means)."""
    mod_tables = ctx.get("modifier_tables") or {}
    col = ctx.get("at_column")
    by_type = {}
    proc_res = 0.0
    # CAST-TIME BUDGET (v17, the animation economy): attack-carried debuffs (Sonic's −res
    # chain) only apply while the attack is actually CAST, and there is one animation bar —
    # if the picked attacks demand more than 100% busy time, every attack's debuff share
    # scales down. Ends the "every extra blast stacks its full −res forever" fiction.
    busy = 0.0
    for p in powers:
        rec = ctx["power_by_full"].get(p.get("full_name")) if ctx.get("power_by_full") else p
        if not rec or not rec.get("is_attack") or (rec.get("power_type") or 0) != 0:
            continue
        ct = rec.get("cast_time") or 1.0
        br = rec.get("base_recharge") or 0.0
        enh = _power_enh(dict(rec, slots=p.get("slots") or []), ctx, ("RechargeTime",))
        cyc = max(br / (1.0 + global_recharge + enh["RechargeTime"]), ct) if br > 0 else ct
        busy += ct / max(cyc, 0.01)
    attack_share = min(1.0, 1.0 / busy) if busy > 1.0 else 1.0
    for p in powers:
        rec = ctx["power_by_full"].get(p.get("full_name")) if ctx.get("power_by_full") else p
        if not rec:
            continue
        merged = dict(rec, slots=p.get("slots") or [])
        enh = _power_enh(merged, ctx, ("Defense", "ToHit", "RechargeTime"))
        base_rech = rec.get("base_recharge") or 0.0
        is_click = (rec.get("power_type") or 0) == 0
        is_attack_click = bool(rec.get("is_attack")) and is_click
        enh_rech = base_rech / (1.0 + global_recharge + enh["RechargeTime"]) \
            if base_rech > 0 else 0.0
        for d in rec.get("debuff_effects") or []:
            if d.get("pv_mode") == 2:
                continue
            row = mod_tables.get(d.get("modifier_table"))
            if not row or col is None or col >= len(row):
                continue
            prob = min(max(d.get("probability") or 1.0, 0.0), 1.0)
            mag = abs((d.get("scale") or 0) * (d.get("nmag") or 1.0)
                      * row[col] * prob) * 100.0
            et = d.get("effect")
            if et == "Defense":
                mag *= (1.0 + enh["Defense"])
            elif et == "ToHit":
                mag *= (1.0 + enh["ToHit"])
            dur = d.get("duration") or 0.0
            if is_click and enh_rech > 0 and dur > 0:
                mag *= min(1.0, dur / enh_rech)
            if is_attack_click:
                mag *= attack_share          # one animation bar (v17)
            key = (et, d.get("damage_type") or "None")
            by_type[key] = by_type.get(key, 0.0) + mag
        for s in (p.get("slots") or []):
            uid = (s or {}).get("piece_uid")
            if uid and uid in _res_proc_uids():
                proc_res += _res_proc_uids()[uid]
            elif "res debuff" in ((s or {}).get("piece_name") or "").lower():
                nm = ((s or {}).get("set_name") or "").lower()
                proc_res += next((v for k, v in _RES_PROC_VALUES.items() if k in nm), 8.0)
    out = {}
    for (et, _dt), v in by_type.items():
        out[et] = max(out.get(et, 0.0), v)     # typed spread → the per-type value, not ×8
    if proc_res:
        out["Resistance"] = out.get("Resistance", 0.0) + proc_res
    return out


def enhanced_team_buffs(powers, ctx, global_recharge=0.0):
    """{effect: sustained pct} TEAM buffs — the buff-side mirror of enhanced_debuff_totals
    (v14, the Accelerate-Metabolism fix: click team buffs were priced at 0 — deep chains were
    literally dropping AM). Ally-facing buff_effects only; CLICK buffs weighted by uptime =
    duration ÷ enhanced recharge (own post-ED RechargeTime + global), toggles/autos uptime 1;
    typed spreads collapse to the per-type value (max). Keys of interest to the encounter
    model: Damage (AM/Fulcrum-class), RechargeTime (AM), Resistance (Dispersion/shields)."""
    mod_tables = ctx.get("modifier_tables") or {}
    col = ctx.get("at_column")
    by_type = {}
    for p in powers:
        rec = ctx["power_by_full"].get(p.get("full_name")) if ctx.get("power_by_full") else p
        if not rec:
            continue
        merged = dict(rec, slots=p.get("slots") or [])
        enh = _power_enh(merged, ctx, ("RechargeTime",))
        base_rech = rec.get("base_recharge") or 0.0
        is_click = (rec.get("power_type") or 0) == 0
        enh_rech = base_rech / (1.0 + global_recharge + enh["RechargeTime"]) \
            if base_rech > 0 else 0.0
        for d in rec.get("buff_effects") or []:
            if d.get("pv_mode") == 2:
                continue
            row = mod_tables.get(d.get("modifier_table"))
            if not row or col is None or col >= len(row):
                continue
            prob = min(max(d.get("probability") or 1.0, 0.0), 1.0)
            mag = abs((d.get("scale") or 0) * (d.get("nmag") or 1.0)
                      * row[col] * prob) * 100.0
            dur = d.get("duration") or 0.0
            if is_click and enh_rech > 0 and dur > 0:
                mag *= min(1.0, dur / enh_rech)
            key = (d.get("effect"), d.get("damage_type") or "None")
            by_type[key] = by_type.get(key, 0.0) + mag
    out = {}
    for (et, _dt), v in by_type.items():
        out[et] = max(out.get(et, 0.0), v)     # typed spread → the per-type value, not ×8
    return out


def support_output(debuffs, buffs):
    """Total buff+debuff output score from the engine's resolved {effect,type,pct} lists."""
    d = sum(abs(x.get("pct", 0)) * DEBUFF_W.get(x.get("effect"), 0.5) for x in (debuffs or []))
    b = sum(abs(x.get("pct", 0)) * BUFF_W.get(x.get("effect"), 0.5) for x in (buffs or []))
    return round(d + b, 1)


def build_support_output(offense):
    """Support output from a calculate_build `offense` block (debuffs/buffs already resolved)."""
    off = offense or {}
    return support_output(off.get("debuffs"), off.get("buffs"))


# ── HEAL output — first-class, for ANY class that takes heals ────────────────
# Healing is a distinct payoff, not one buff weight. It splits by WHO and scales by AREA + UPTIME:
#   • ally heal (to_who=1)  -> TEAM support throughput = heal × targets ÷ recharge  (a group heal
#     that hits the whole team >> a single-target heal of the same size)
#   • self heal (to_who=2)  -> SURVIVAL throughput (armored ATs' Reconstruction/Healing Flames —
#     invisible before). Kept separate: it's mitigation, not team support.
#   • resurrect             -> flat clutch-utility credit (no magnitude; a team save).
# Heal magnitude = scale × nMag × AttribMod[table][AT] (fraction of the AT's base HP-ish); recharge
# gives throughput per second. (+Regen buffs = sustained healing, counted under Regeneration.)
def _heal_mag(h, mod_tables, col):
    return abs(h.get("scale") or 0.0) * (h.get("nmag") or 1.0) \
        * _table_val(mod_tables, h.get("modifier_table"), col) * (h.get("probability") or 1.0)


def power_heal_output(power, ctx):
    """(team_hps, self_hps, is_rez) for one power. hps = heal × area ÷ recharge."""
    he = power.get("heal_effects") or []
    if not he and not power.get("is_resurrect"):
        return 0.0, 0.0, False
    mod_tables = ctx.get("modifier_tables") or {}
    col = ctx.get("at_column")
    rech = power.get("base_recharge") or 0.0
    radius = power.get("radius") or 0
    group = min(int(power.get("max_targets") or 6), 16) if radius > 0 else 1
    team = self_ = 0.0
    for h in he:
        mag = _heal_mag(h, mod_tables, col)                      # per-target heal
        # AREA applies ONLY to an ALLY group heal (Healing Aura hits the team). A SELF heal (to_who=2)
        # always heals just you, even on a radius power (Siphon Energy's radius is its debuff, not the heal).
        a = group if h.get("to_who") == 1 else 1
        hps = (mag * a / rech) if rech > 0 else (mag * a)        # heal × targets ÷ recharge
        if h.get("to_who") == 2:
            self_ += hps
        else:
            team += hps
    return round(team, 3), round(self_, 3), bool(power.get("is_resurrect"))


def build_heal_output(powers, ctx):
    """Team-heal throughput, self-heal (survival) throughput, and rez count for a build."""
    team = self_ = 0.0
    rez = 0
    for p in powers:
        rec = ctx["power_by_full"].get(p.get("full_name")) if ctx.get("power_by_full") else p
        if not rec:
            continue
        t, s, r = power_heal_output(rec, ctx)
        team += t; self_ += s
        rez += 1 if r else 0
    # Score: team throughput is the support payoff; self-heal credited at half (survival, not team);
    # each rez a flat clutch-utility credit.
    score = round(team + 0.5 * self_ + 8.0 * rez, 1)
    return {"team_hps": round(team, 2), "self_hps": round(self_, 2), "rez": rez, "score": score}


def build_control_output(powers, ctx, mez_dur=None):
    """Total control output of a build + per-power breakdown (sorted)."""
    rows = []
    for p in powers:
        rec = ctx["power_by_full"].get(p.get("full_name")) if ctx.get("power_by_full") else p
        if not rec:
            continue
        s = power_control_output(rec, ctx, mez_dur)
        if s > 0:
            rows.append((rec.get("power_name") or p.get("full_name"), s))
    rows.sort(key=lambda r: -r[1])
    return round(sum(s for _, s in rows), 1), rows
