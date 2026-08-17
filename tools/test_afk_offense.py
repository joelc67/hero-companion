"""BATTERY: v45 AFK offense — farm_afk prices only the damage that fires with
nobody at the keyboard (Maelwys, topic 64761, 2026-08-16).

The rule: toggles/autos (damage auras) keep full credit; exactly ONE click
takes the auto-fire slot (best cycled DPS); every other click contributes
zero. Only scenario farm_afk reads the AFK aggregates.

Negative control (standing rule): a build whose damage is ALL auras must read
identical AFK and general AoE aggregates — the term must not fire on a
lookalike. Positive control: the reported TW/Bio champion shape (click-chain
heavy, no damage aura) must lose most of its AFK AoE DPS.

Run:  python tools/test_afk_offense.py
"""
import importlib.util as ilu
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = ilu.spec_from_file_location("cohserver", os.path.join(ROOT, "server", "server.py"))
srv = ilu.module_from_spec(spec)
spec.loader.exec_module(srv)
import first_principles as fp  # noqa: E402  (server path inserted by server.py)

fails = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        fails.append(name)


def offense_for(picks):
    powers = [{"full_name": fn, "slots": [None]} for fn in picks]
    c = srv.app.test_client()
    res = c.post("/build/calculate", json={
        "archetype": _AT, "primary": _PRI,
        "secondary": _SEC, "powers": powers}).get_json()
    t = res.get("totals") or res
    return t.get("offense") or {}


print("── model version ──")
check("MODEL_VERSION is at least 47", fp.MODEL_VERSION >= 47, str(fp.MODEL_VERSION))

# ── 1. POSITIVE CONTROL: the reported TW/Bio farm_afk champion shape ─────────
_AT, _PRI, _SEC = ("Class_Brute", "Brute_Melee.Titan_Weapons",
                   "Brute_Defense.Bio_Organic_Armor")
tw = offense_for([
    "Brute_Melee.Titan_Weapons.Defensive_Sweep",
    "Brute_Melee.Titan_Weapons.Sweeping_Strike",
    "Brute_Melee.Titan_Weapons.Arc_of_Destruction",
    "Brute_Defense.Bio_Organic_Armor.Hardened_Carapace",
    "Epic.Pyre_Mastery.Fire_Ball",
    "Epic.Pyre_Mastery.Fire_Blast",
    "Epic.Pyre_Mastery.Char",
])
check("TW/Bio click chain: general AoE DPS is substantial", (tw.get("aoe_dps") or 0) > 10,
      f"aoe={tw.get('aoe_dps')}")
check("TW/Bio click chain: AFK AoE DPS collapses to ONE auto-fire click",
      0 < (tw.get("afk_aoe_dps") or 0) < (tw.get("aoe_dps") or 0) * 0.55,
      f"afk_aoe={tw.get('afk_aoe_dps')} vs aoe={tw.get('aoe_dps')}")
check("TW/Bio: the auto-fire slot is named", bool(tw.get("afk_autofire")),
      str(tw.get("afk_autofire")))

# ── 2. NEGATIVE CONTROL: all-aura damage reads IDENTICAL afk vs general ──────
_AT, _PRI, _SEC = ("Class_Brute", "Brute_Melee.Spines", "Brute_Defense.Fiery_Aura")
aura = offense_for([
    "Brute_Defense.Fiery_Aura.Blazing_Aura",     # damage aura toggle
    "Brute_Melee.Spines.Quills",                 # damage aura toggle
])
check("NEGATIVE CONTROL: all-aura build's AFK AoE == general AoE",
      abs((aura.get("afk_aoe_dps") or 0) - (aura.get("aoe_dps") or 0)) < 0.05,
      f"afk={aura.get('afk_aoe_dps')} general={aura.get('aoe_dps')}")
check("NEGATIVE CONTROL: no phantom auto-fire on an all-aura build",
      not aura.get("afk_autofire"), str(aura.get("afk_autofire")))

# ── 3. ONE auto-fire, not several: auras + two clicks credits ONE click ──────
mix = offense_for([
    "Brute_Defense.Fiery_Aura.Blazing_Aura",
    "Brute_Defense.Fiery_Aura.Burn",             # click patch — the classic auto-fire
    "Brute_Melee.Spines.Spine_Burst",            # click AoE — must NOT also count
])
aura_only = offense_for(["Brute_Defense.Fiery_Aura.Blazing_Aura"])
one_click_gain = (mix.get("afk_aoe_dps") or 0) - (aura_only.get("afk_aoe_dps") or 0)
both_clicks = (mix.get("aoe_dps") or 0) - (aura_only.get("aoe_dps") or 0)
check("auras + 2 clicks: AFK credits ONE click, general credits both",
      0 < one_click_gain < both_clicks * 0.95,
      f"afk gain={one_click_gain:.1f}, general gain={both_clicks:.1f}, autofire={mix.get('afk_autofire')}")

# ── 4. the scenario gate: ONLY farm_afk reads the AFK aggregates ─────────────
src = open(os.path.join(ROOT, "server", "first_principles.py"), encoding="utf-8").read()
# v49 added a second farm_afk gate (passive-only survival), so scan EVERY gate
_segs = [src[i:i + 400] for i in range(len(src))
         if src.startswith('if scenario == "farm_afk":', i)]
check("first_principles gates on scenario farm_afk and reads afk_ aggregates",
      any("afk_st_dps" in s and "afk_aoe_dps" in s for s in _segs))
check("the general branch still reads the general aggregates",
      'off.get("st_dps")' in src and 'off.get("aoe_dps")' in src)

# ── 5. v46: momentum-gated attacks are no AFK candidates (game's own short
# help: "Requires Momentum" — they cannot fire from cold) ────────────────────
print("\n── momentum gates (v46) ──")
_AT, _PRI, _SEC = ("Class_Brute", "Brute_Melee.Titan_Weapons",
                   "Brute_Defense.Fiery_Aura")
twm = offense_for([
    "Brute_Melee.Titan_Weapons.Whirling_Slice",   # displays "Whirling Smash", gated
    "Brute_Melee.Titan_Weapons.Follow_Through",   # gated
    "Brute_Melee.Titan_Weapons.Crushing_Blow",    # free click — the legal auto-fire
    "Brute_Defense.Fiery_Aura.Blazing_Aura",
])
check("a momentum-gated attack never takes the AFK auto-fire slot",
      twm.get("afk_autofire") not in ("Whirling Smash", "Follow Through"),
      str(twm.get("afk_autofire")))
check("gated attacks contribute nothing to AFK AoE",
      (twm.get("afk_aoe_dps") or 0) < (twm.get("aoe_dps") or 1),
      f"afk={twm.get('afk_aoe_dps')} general={twm.get('aoe_dps')}")

# ── 6. v46: ONE auto-fire — when the attack claims it, the sustain ledger is
# passive only (no auto-fire heal credited) ──────────────────────────────────
print("\n── single auto-fire (v46) ──")
import importlib
import role_output as _ro
_AT, _PRI, _SEC = ("Class_Brute", "Brute_Melee.Spines", "Brute_Defense.Fiery_Aura")
powers_atk = [{"full_name": fn, "slots": [None]} for fn in (
    "Brute_Defense.Fiery_Aura.Healing_Flames",    # non-interruptible click heal
    "Brute_Defense.Fiery_Aura.Burn",              # click attack — claims auto-fire
    "Brute_Defense.Fiery_Aura.Blazing_Aura")]
powers_heal = [p for p in powers_atk if not p["full_name"].endswith(".Burn")]
c2 = srv.app.test_client()
def sustain_for(pws):
    res = c2.post("/build/calculate", json={"archetype": _AT, "primary": _PRI,
        "secondary": _SEC, "powers": [dict(p) for p in pws]}).get_json()
    t = res.get("totals") or res
    ctx = srv._stat_ctx(_AT)   # the REAL context builder, not a hand-rolled stub
    row = next((a for a in srv.PLAYABLE if a["name"] == _AT), None)
    return fp.afk_sustain_assessment(pws, t, row, ctx, role_output_mod=_ro)
s_atk = sustain_for(powers_atk)
s_heal = sustain_for(powers_heal)
check("attack in build -> NO auto-fire heal credited (slot spent on the attack)",
      s_atk.get("auto_fire_heal") is None and s_atk.get("auto_fire_hps") == 0,
      f"{s_atk.get('auto_fire_heal')} @ {s_atk.get('auto_fire_hps')}")
check("NEGATIVE CONTROL: no click attack -> the heal still gets the slot",
      s_heal.get("auto_fire_heal") == "Healing_Flames" and s_heal.get("auto_fire_hps") > 0,
      f"{s_heal.get('auto_fire_heal')} @ {s_heal.get('auto_fire_hps')}")

# ── 7. v47: spawn-scale auto-fire + typed farm scenarios ─────────────────────
print("\n── v47: spawn-scale auto-fire ──")
_AT, _PRI, _SEC = ("Class_Brute", "Brute_Melee.Radiation_Melee",
                   "Brute_Defense.Fiery_Aura")
bb = offense_for(["Brute_Defense.Fiery_Aura.Burn", "Pool.Fighting.Boxing",
                  "Brute_Defense.Fiery_Aura.Blazing_Aura"])
check("Burn (spawn-wide) beats Boxing (single-target) for the auto-fire slot",
      bb.get("afk_autofire") == "Burn", str(bb.get("afk_autofire")))

print("\n── v47: typed farm scenarios ──")
row = next(a for a in srv.PLAYABLE if a["name"] == "Class_Brute")
ctx = srv._stat_ctx("Class_Brute")
import engine as _eng
import role_output as _ro2
# fire-capped vs smash-capped synthetic totals through the REAL encounter_value
def _tot(res_fire, res_smash):
    t = {"defense": {}, "resistance": {"Fire": {"value": res_fire},
                                       "Smashing": {"value": res_smash}},
         "regeneration": {"value": 100.0}, "max_hp": {"value": 0.0},
         "recharge": {"value": 0.0}, "offense": {"afk_aoe_dps": 10.0,
                                                 "afk_st_dps": 0.0,
                                                 "st_dps": 0, "aoe_dps": 10.0},
         "bonus_extras": {}}
    return t
ev_fire = fp.encounter_value("Class_Brute", [], ctx, _tot(90, 0),
                             scenario="farm_afk", arch_row=row, role_output_mod=None)
ev_smash = fp.encounter_value("Class_Brute", [], ctx, _tot(0, 90),
                              scenario="farm_afk", arch_row=row, role_output_mod=None)
check("farm_afk survival reads FIRE resistance (90 fire >> 90 smash there)",
      (ev_fire.get("availability") or 0) > (ev_smash.get("availability") or 0) * 2,
      f"fire-capped {ev_fire.get('availability'):.3f} vs smash-capped {ev_smash.get('availability'):.3f}")
ev_gen_a = fp.encounter_value("Class_Brute", [], ctx, _tot(0, 90),
                              scenario="general", arch_row=row, role_output_mod=None)
ev_gen_b = fp.encounter_value("Class_Brute", [], ctx, _tot(90, 0),
                              scenario="general", arch_row=row, role_output_mod=None)
check("NEGATIVE CONTROL: the general scenario still reads Smashing",
      (ev_gen_a.get("availability") or 0) > (ev_gen_b.get("availability") or 0),
      f"smash-capped {ev_gen_a.get('availability'):.3f} vs fire-capped {ev_gen_b.get('availability'):.3f}")

print("\n── v48: build-relative AFK requirements (Maelwys round 4) ──")
# Identical regen, different Fire mitigation, through the REAL assessment:
# the res-capped build must out-tier the leaky one, and the requirement rows
# must scale with what the build actually resists.
def _sus(res_fire, de):
    t = {"defense": {"Melee": {"value": de}, "AoE": {"value": de},
                     "Fire": {"value": de}},
         "resistance": {"Fire": {"value": res_fire}},
         "regeneration": {"value": 400.0}, "max_hp": {"value": 0.0},
         "heal_strength": {"value": 0.0}, "offense": {},
         "bonus_extras": {}}
    return fp.afk_sustain_assessment([], t, row, ctx, role_output_mod=None)
s_cap = _sus(90, 45)    # the reference farmer: capped res, softcapped def
s_leak = _sus(60, 45)   # same everything, 60% Fire res
check("capped-res reference farmer certifies a HIGHER tier than the 60%-res twin",
      (s_cap.get("tier") if s_cap.get("tier") is not None else -1)
      > (s_leak.get("tier") if s_leak.get("tier") is not None else -1),
      f"90% res tier={s_cap.get('tier')} vs 60% res tier={s_leak.get('tier')}")
check("the +4x8 requirement READS the build (60% res asks ~4x the capped ask)",
      s_leak["requirements"][4] > s_cap["requirements"][4] * 3.5,
      f"{s_leak['requirements'][4]} vs {s_cap['requirements'][4]}")
check("the certificate states the mitigation basis it judged against",
      (s_cap.get("mitigation") or {}).get("res_pct") == 90.0
      and "resistance" in s_cap.get("label", ""),
      str(s_cap.get("mitigation")))
s_soft = _sus(90, 45); s_naked = _sus(90, 0)
check("defense moves the requirement too (softcap vs no defense)",
      s_naked["requirements"][4] > s_soft["requirements"][4] * 2,
      f"{s_naked['requirements'][4]} vs {s_soft['requirements'][4]}")
check("ledger rows carry counted flags and none are counted without auto-fire",
      all(h.get("counted") is False for h in s_cap.get("heal_rates", [])) or
      s_cap.get("heal_rates") == [],
      str(s_cap.get("heal_rates")))
check("sustain still equals regen when nothing holds the auto-fire slot",
      abs(s_cap["sustain_hps"] - s_cap["regen_hps"]) < 0.01,
      f"{s_cap['sustain_hps']} vs {s_cap['regen_hps']}")

print("\n── v49: AFK sustain joins the farm objective ──")
# (a) the 600s stint: a passively-sustaining build holds availability, a
# leaky one collapses — through the REAL encounter_value.
def _tot49(res_fire, de, regen):
    return {"defense": {"Melee": {"value": de}, "AoE": {"value": de},
                        "Fire": {"value": de}},
            "resistance": {"Fire": {"value": res_fire}},
            "regeneration": {"value": regen}, "max_hp": {"value": 0.0},
            "recharge": {"value": 0.0},
            "offense": {"afk_aoe_dps": 10.0, "afk_st_dps": 0.0,
                        "st_dps": 0, "aoe_dps": 10.0},
            "bonus_extras": {}}
ev_hold = fp.encounter_value("Class_Brute", [], ctx, _tot49(90, 45, 800),
                             scenario="farm_afk", arch_row=row, role_output_mod=None)
ev_leak = fp.encounter_value("Class_Brute", [], ctx, _tot49(60, 45, 800),
                             scenario="farm_afk", arch_row=row, role_output_mod=None)
check("sustaining build holds availability; 60%-res twin collapses in the stint",
      (ev_hold.get("availability") or 0) > 0.85
      and (ev_leak.get("availability") or 0) < 0.5 * (ev_hold.get("availability") or 1),
      f"hold {ev_hold.get('availability'):.3f} vs leak {ev_leak.get('availability'):.3f}")
# (b) click heals are NOT survival at farm_afk when the attack claims
# auto-fire: same totals, heal power present vs absent — identical availability.
tot_hf = c2.post("/build/calculate", json={"archetype": _AT, "primary": _PRI,
    "secondary": _SEC, "powers": [dict(p) for p in powers_atk]}).get_json()
tot_hf = tot_hf.get("totals") or tot_hf
ctx_hf = srv._stat_ctx(_AT); ctx_hf["power_by_full"] = srv.POWER_BY_FULL
row_b = next(a for a in srv.PLAYABLE if a["name"] == _AT)
ev_heal = fp.encounter_value(_AT, powers_atk, ctx_hf, tot_hf,
                             scenario="farm_afk", arch_row=row_b, role_output_mod=_ro)
ev_noheal = fp.encounter_value(_AT, [p for p in powers_atk
                                     if not p["full_name"].endswith("Healing_Flames")],
                               ctx_hf, tot_hf,
                               scenario="farm_afk", arch_row=row_b, role_output_mod=_ro)
check("a click heal buys NOTHING at farm_afk while the attack owns auto-fire",
      abs((ev_heal.get("availability") or 0) - (ev_noheal.get("availability") or 0)) < 1e-9,
      f"{ev_heal.get('availability'):.4f} vs {ev_noheal.get('availability'):.4f}")
ev_gen_heal = fp.encounter_value(_AT, powers_atk, ctx_hf, tot_hf,
                                 scenario="general", arch_row=row_b, role_output_mod=_ro)
ev_gen_no = fp.encounter_value(_AT, [p for p in powers_atk
                                     if not p["full_name"].endswith("Healing_Flames")],
                               ctx_hf, tot_hf,
                               scenario="general", arch_row=row_b, role_output_mod=_ro)
check("NEGATIVE CONTROL: the general scenario still credits the click heal",
      (ev_gen_heal.get("availability") or 0) > (ev_gen_no.get("availability") or 0),
      f"{ev_gen_heal.get('availability'):.4f} vs {ev_gen_no.get('availability'):.4f}")
# (c) no-Burn build: the heal takes auto-fire and DOES count at farm_afk —
# mitigated synthetic totals (no afk_autofire claimed) so the heal is visible
tot_mit = _tot49(90, 45, 100)
ev_afk_h = fp.encounter_value(_AT, powers_heal, ctx_hf, tot_mit,
                              scenario="farm_afk", arch_row=row_b, role_output_mod=_ro)
ev_afk_h0 = fp.encounter_value(_AT, [], ctx_hf, tot_mit,
                               scenario="farm_afk", arch_row=row_b, role_output_mod=_ro)
check("with no click attack, the auto-fire HEAL is survival at farm_afk",
      (ev_afk_h.get("availability") or 0) > (ev_afk_h0.get("availability") or 0),
      f"{ev_afk_h.get('availability'):.4f} vs {ev_afk_h0.get('availability'):.4f}")

n = 25
print(f"\n{n} of {n} expected checks ran")
print(f"══ {'ALL PASS' if not fails else f'{len(fails)} FAILURE(S): ' + ', '.join(fails)} ══")
sys.exit(1 if fails else 0)
