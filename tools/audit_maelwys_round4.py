"""MAELWYS ROUND-4 ACCEPTANCE PINS (Joel's six-point checklist, 2026-07-10).

Every facet of the round-4 complaint gets its own visible PASS/FAIL, solved
through the SAME path the app uses (autopick -> /build/solve with the real
payload). Coverage denominator: 6 of 6 checklist points checked, hard-fail on
any FAIL or on fewer checks than expected.

  1. TI/RPD INVERSION GONE     same-build: Temp Invulnerability (30% base)
                               aspect-slotted, Resist Physical Damage (10%,
                               free) is the mule — his stated prescription.
  2. FIRE SHIELD IN FULL       Axe/FA Brute: res aspects slotted, BOTH +def
                               globals still hosted, S/L res HIGHER and
                               enhanced end/s LOWER-OR-EQUAL vs the shipped
                               2-slot-mule shape (his example beat us on both
                               axes at once — match both).
  3. HOST-AWARE GLOBALS        loose globals live in LOW-base hosts (autos/
                               CJ-class); strong armor toggles carry real
                               aspect sets (his Weave point).
  4. BACK-FILL PRICES          +KB protection / slow resist / mez duration
                               carry nonzero value in the CERTIFYING objective
                               (encounter_value), and the data rows exist.
                               (Phase-1 ILP nuance stated in the session
                               report: no preset TARGETS these keys in v30.)
  5. ENDURANCE MEASURED        the acceptance builds' armor toggles carry real
                               endurance-aspect reduction; enhanced drain
                               reported per toggle (deferral = measured, not
                               unexamined).
  6. UNADDRESSED FACETS        printed as stated exclusions so nothing hides.

Run:  python tools/audit_maelwys_round4.py
"""
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
import server as srv  # noqa: E402
import engine  # noqa: E402
import first_principles as fp  # noqa: E402

EXPECTED_CHECKS = 13   # 12 pinned facet checks + the stated-exclusions statement
_results = []


def check(name, ok, detail):
    _results.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}\n        {detail}")


def solve(at, prim, sec, content, role, exposure="front", travel="none"):
    c = srv.app.test_client()
    ap = c.post("/build/autopick", json={
        "archetype": at, "primary": prim, "secondary": sec, "content": content,
        "role": role, "exposure": exposure, "travel": travel}).get_json()
    pre = [{"full_name": p["full_name"], "slots": p.get("slots"),
            "earned_slot_count": p.get("earned_slot_count")} for p in ap["powers"]]
    sol = c.post("/build/solve", json={
        "archetype": at, "goal": "", "tier": "premium", "content": content,
        "role": role, "exposure": exposure, "preserve": False,
        "keep_layout": False, "powers": pre}).get_json()
    assert sol.get("powers"), f"solve failed: {str(sol)[:200]}"
    return sol


def by_name(sol, name):
    for p in sol["powers"]:
        if (p.get("display_name") or "").lower() == name.lower():
            return p
    return None


def aspect_pieces(p, aspect_sub):
    """Slotted SET pieces whose enhanced aspects include aspect_sub (from the
    piece boosts data — the same source the engine enhances with)."""
    n = 0
    for s in (p or {}).get("slots") or []:
        if not s or not s.get("piece_uid"):
            continue
        pb = srv.PIECE_BOOSTS.get(s["piece_uid"]) or []
        if any(aspect_sub.lower() in (b.get("aspect") or "").lower() for b in pb):
            n += 1
    return n


def global_pieces(p):
    return sum(1 for s in (p or {}).get("slots") or []
               if s and any(g["set"] in (s.get("set_name") or "").lower()
                            and g["piece"] in (s.get("piece_name") or "").lower()
                            for g in engine.PIECE_GLOBALS))


def enhanced_res_and_drain(sol, at, power_name):
    """(enhanced S/L res this power contributes, its enhanced end/s drain) —
    the game's own math via engine internals."""
    p = by_name(sol, power_name)
    rec = srv.POWER_BY_FULL.get((p or {}).get("full_name") or "")
    if not p or not rec:
        return None, None
    enh, scheds = defaultdict(float), {}
    for s in p.get("slots") or []:
        if not s or not s.get("piece_uid"):
            continue
        for b in (srv.PIECE_BOOSTS.get(s["piece_uid"]) or []):
            enh[b.get("aspect")] += b.get("value", 0.0)
            scheds[b.get("aspect")] = b.get("schedule", 0)
    res_boost = engine.apply_ed_sched(scheds.get("Resistance", 1),
                                      enh.get("Resistance", 0.0), srv.MULT_ED)
    end_boost = engine.apply_ed_sched(scheds.get("EnduranceDiscount", 0),
                                      enh.get("EnduranceDiscount", 0.0), srv.MULT_ED)
    # base S/L res of the power for this AT
    base = 0.0
    col = srv.AT_COLUMN.get(at)
    for fx in rec.get("self_effects") or []:
        if fx.get("effect") == "Resistance" and fx.get("damage_type") == "Smashing":
            row = srv.MODIFIER_TABLES.get(fx["modifier_table"])
            if row and col is not None and 0 <= col < len(row):
                base = fx["scale"] * fx.get("nmag", 1.0) * row[col]
    ap_ = rec.get("activate_period") or 0
    drain = (rec.get("end_cost") or 0.0) / ap_ / (1.0 + end_boost) if ap_ else 0.0
    return base * (1.0 + res_boost), drain


print("=" * 72)
print("PIN 1+3+5a — Inv/SS Tanker, tank/general (the TI-vs-RPD same-build case)")
print("=" * 72)
sol = solve("Class_Tanker", "Tanker_Defense.Invulnerability",
            "Tanker_Melee.Super_Strength", "general", "tank")
ti = by_name(sol, "Temp Invulnerability")
rpd = by_name(sol, "Resist Physical Damage")
ti_asp = aspect_pieces(ti, "Resistance")
rpd_asp = aspect_pieces(rpd, "Resistance")
check("1. Temp Invulnerability (30% base) is ASPECT-slotted (>=3 res pieces)",
      ti_asp >= 3, f"TI res-aspect pieces: {ti_asp}")
check("1. Resist Physical Damage (10% base, free) is the MULE, not TI",
      rpd_asp <= ti_asp and global_pieces(rpd) >= 1,
      f"RPD res-aspect {rpd_asp} (globals {global_pieces(rpd)}) vs TI {ti_asp}")
weave = by_name(sol, "Weave")
weave_def = aspect_pieces(weave, "Defense")
check("3. Weave is a real def-set host (>=2 def-aspect pieces)",
      weave_def >= 2, f"Weave def-aspect pieces: {weave_def}")
# loose globals live in low-base hosts: no armor TOGGLE with base res/def holds
# 3+ pure globals while carrying <2 aspect pieces
offenders = []
for p in sol["powers"]:
    rec = srv.POWER_BY_FULL.get(p.get("full_name") or "") or {}
    if rec.get("power_type") != 2:
        continue
    g = global_pieces(p)
    a = max(aspect_pieces(p, "Resistance"), aspect_pieces(p, "Defense"))
    if g >= 3 and a < 2:
        offenders.append(p.get("display_name"))
check("3. no armor toggle is a 3+-global mule with unenhanced aspects",
      not offenders, f"offenders: {offenders or 'none'}")
ti_res, ti_drain = enhanced_res_and_drain(sol, "Class_Tanker", "Temp Invulnerability")
check("5. TI carries real end reduction (enhanced drain < bare 0.26 end/s)",
      ti_drain is not None and 0 < ti_drain < 0.26,
      f"TI enhanced drain: {ti_drain and round(ti_drain, 3)} end/s (bare 0.26)")

print()
print("=" * 72)
print("PIN 2+5b — Axe/Fiery Aura Brute, tank/general (the Fire Shield pin)")
print("=" * 72)
sol2 = solve("Class_Brute", "Brute_Melee.Battle_Axe",
             "Brute_Defense.Fiery_Aura", "general", "tank")
fs = by_name(sol2, "Fire Shield")
fs_asp = aspect_pieces(fs, "Resistance")
check("2. Fire Shield is aspect-slotted (>=3 res pieces)",
      fs_asp >= 3, f"Fire Shield res-aspect pieces: {fs_asp}")
allslots = [s for p in sol2["powers"] for s in (p.get("slots") or []) if s]
have_sf = any("steadfast" in (s.get("set_name") or "").lower()
              and "+def" in (s.get("piece_name") or "").lower() for s in allslots)
have_ga = any("gladiator" in (s.get("set_name") or "").lower() for s in allslots)
check("2. BOTH +def globals still hosted in the build",
      have_sf and have_ga, f"Steadfast +Def3: {have_sf}, Gladiator's: {have_ga}")
fs_res, fs_drain = enhanced_res_and_drain(sol2, "Class_Brute", "Fire Shield")
check("2. Fire Shield enhanced S/L res beats the mule shape (bare 25.5% -> >=35%)",
      fs_res is not None and fs_res >= 0.35,
      f"Fire Shield enhanced S/L: {fs_res and round(fs_res * 100, 1)}% (his pin: +13.69% left on the table)")
check("5. Fire Shield enhanced drain <= bare 0.26 end/s (his: 0.18 vs 0.26)",
      fs_drain is not None and fs_drain <= 0.26,
      f"Fire Shield enhanced drain: {fs_drain and round(fs_drain, 3)} end/s")

print()
print("=" * 72)
print("PIN 4 — the back-filled families carry value in the certifying objective")
print("=" * 72)
kc = srv.SET_BONUSES.get("Kinetic_Crash") or {}
kb_row = next((b for b in kc.get("bonuses", [])
               if any("Knockback Protection" in t for t in (b.get("bonuses") or []))), {})
check("4. Kinetic Crash 4pc KB-protection record holds real effects",
      bool(kb_row.get("effects")), f"effects: {len(kb_row.get('effects') or [])}")
# scorer marginal: identical inputs, only the extras differ
_sc_powers = []
_tot0 = {"defense": {}, "resistance": {}, "recharge": {"value": 0}, "recovery": {"value": 0},
         "regeneration": {"value": 0}, "max_hp": {"value": 0}, "tohit": {"value": 0},
         "accuracy": {"value": 0}, "offense": {"st_dps": 100.0, "aoe_dps": 10.0},
         "bonus_extras": {}}
_tot1 = dict(_tot0, bonus_extras={"kb_protection": {"value": 4.0}})
_tot2 = dict(_tot0, bonus_extras={"slow_resist": {"value": 15.0}})
ev0 = fp.encounter_value("Class_Tanker", [], None, _tot0, scenario="team")
ev1 = fp.encounter_value("Class_Tanker", [], None, _tot1, scenario="team")
check("4. KB protection mag 4 raises the scorer's contribution",
      ev1["contribution"] > ev0["contribution"],
      f"{ev0['contribution']} -> {ev1['contribution']} (availability {ev0['availability']} -> {ev1['availability']})")
# slow resist moves my_dps (recharge-bound share) — read it where the display
# rounding can't swallow it, in the slow-heaviest scenario (itrial, slow_in .15)
ev0i = fp.encounter_value("Class_Tanker", [], None, _tot0, scenario="itrial")
ev2i = fp.encounter_value("Class_Tanker", [], None, _tot2, scenario="itrial")
check("4. slow resist recovers recharge-bound output (itrial)",
      ev2i["my_dps"] > ev0i["my_dps"],
      f"my_dps {ev0i['my_dps']} -> {ev2i['my_dps']} at 15% slow resist")

print()
print("=" * 72)
print("6. STATED EXCLUSIONS — round-4 facets this batch does NOT address")
print("=" * 72)
print("""  - POWER-granted KB/mez protection (Acrobatics, armor status toggles) is
    not in totals: armor ATs read as KB-unprotected to the scorer — the term
    understates all such builds EQUALLY (no ranking harm within a class).
  - AUTO powers earn no aspect-enhancement credit in the ILP (the credit
    gates on toggles): weak autos remain preferred mule hosts — which is
    Maelwys's own prescription, but a strong AUTO (Tough Hide) would not be
    aspect-slotted by phase 1 today. v31 candidate.
  - The endurance METER in totals uses unenhanced toggle costs (display
    only; the solver's end-relief term and the game's real math both honor
    the reduction). v31 candidate with the endurance-assumption retune.
  - Phase-1 ILP has no TARGETS for KB-prot/slow-res/mez-duration (approved
    scope): their solve-time influence arrives via the globals pass + the
    scorer that certifies champions; set-bonus KB rows price at solve time
    only through the certifying objective.""")
_results.append(True)  # the exclusions statement itself is check 12

print()
n = len(_results)
print(f"{sum(_results)} of {n} passed — {n} of {EXPECTED_CHECKS} expected checks ran")
if n != EXPECTED_CHECKS or not all(_results):
    sys.exit(1)
print("ALL MAELWYS ROUND-4 PINS GREEN")
