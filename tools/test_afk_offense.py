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
check("MODEL_VERSION is 45", fp.MODEL_VERSION == 45, str(fp.MODEL_VERSION))

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
i = src.index('if scenario == "farm_afk":')
seg = src[i:i + 400]
check("first_principles gates on scenario farm_afk and reads afk_ aggregates",
      "afk_st_dps" in seg and "afk_aoe_dps" in seg)
check("the general branch still reads the general aggregates",
      'off.get("st_dps")' in src and 'off.get("aoe_dps")' in src)

n = 8
print(f"\n{n} of {n} expected checks ran")
print(f"══ {'ALL PASS' if not fails else f'{len(fails)} FAILURE(S): ' + ', '.join(fails)} ══")
sys.exit(1 if fails else 0)
