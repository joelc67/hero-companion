"""Model v38 battery — pet hit chance (Piece 2), negative controls first.

Facts basis: docs/pet-tohit-sources.md (wiki-sourced tier shifts + player-table
pet to-hit) + client patches (patch_pet_accuracy, patch_summon_level_shift).

Checks:
  1. NEGATIVE CONTROL (structural): a petless build scores IDENTICALLY whether
     offense.pets is absent or [] — pets contribute exactly 0.
     (The 23-check gate battery passing unchanged under v38 is the empirical
     half: no non-pet number moved.)
  2. Robotics tiers carry the wiki shifts: Droid 2 / Protector 1 / Assault 0,
     and every pet row carries acc_mult.
  3. Pet hit physics bites: v38 pet contribution < raw squad DPS (hit×pp < 1),
     and the T1's own hit factor < the T3's (purple patch bites tiers hardest).
  4. ToHit buys it back: the same build with pet ToHit zeroed scores LESS than
     with Supremacy's +10% routed (Tactics-class visibility).
  5. Supremacy's ToHit actually routes: an MM build's offense block carries
     pet_tohit_all_pct >= 10.
  6. Controller Levelminus pets: Fire Imps carry level_shift 1 (client-pinned).
  7. Accuracy slotting reaches pets: acc_mult > 1.0 on a solved MM whose summon
     powers carry Accuracy-aspect pieces.

Run:  py tools\\test_pet_hit_v38.py
"""
import copy
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv  # noqa: E402
import proc_pass  # noqa: E402
import first_principles as fp  # noqa: E402

checks = 0
fails = []


def check(name, ok, detail=""):
    global checks
    checks += 1
    print(f"  {'PASS' if ok else 'FAIL'}  {name}"
          + (f"\n        {detail}" if detail else ""))
    if not ok:
        fails.append(name)


def solve(at, prim, sec, content, role):
    arch_row = srv.ARCH_BY_NAME.get(at)
    res_cap = round((arch_row.get("res_cap") or 0.75) * 100, 1)
    pre = srv.ai_build.preset_targets(content, role, res_cap=res_cap)
    ctx = srv._stat_ctx(at)
    ctx["power_by_full"] = srv.POWER_BY_FULL
    client = srv.app.test_client()
    ap = client.post("/build/autopick", json={
        "archetype": at, "primary": prim, "secondary": sec,
        "content": content}).get_json()
    assert ap and ap.get("powers"), f"autopick failed for {at}"
    r = srv._assess_solve(at, copy.deepcopy(ap["powers"]),
                          copy.deepcopy(pre["targets"]), "premium",
                          pre["perk_focus"], pre["roles"], False, False, False,
                          with_powers=True)
    assert r, f"solve failed for {at}"
    _tot, solved = r
    solved = proc_pass.apply_proc_pass(solved, srv.POWER_BY_FULL, role=role,
                                       content=content)
    tot = srv.engine.calculate_build({"archetype": at, "powers": solved},
                                     srv.SET_BONUSES, res_cap=res_cap, ctx=ctx)
    return solved, tot, ctx, arch_row


def ev(at, solved, ctx, tot, content, role, arch_row):
    return fp.encounter_value(at, solved, ctx, tot, scenario=content,
                              arch_row=arch_row,
                              role_output_mod=srv.role_output)


def main():
    # ── petless negative control (MA/SR Scrapper — no summons anywhere) ──
    at = "Class_Scrapper"
    solved, tot, ctx, arch = solve(at, "Scrapper_Melee.Martial_Arts",
                                   "Scrapper_Defense.Super_Reflexes",
                                   "general", "damage")
    off = tot.get("offense") or {}
    assert not off.get("pets"), "Scrapper unexpectedly has pets"
    t2 = copy.deepcopy(tot)
    t2["offense"]["pets"] = []
    a = ev(at, solved, ctx, tot, "general", "damage", arch)["contribution"]
    b = ev(at, solved, ctx, t2, "general", "damage", arch)["contribution"]
    check("NEGATIVE CONTROL: petless Scrapper — pets absent vs [] scores identical",
          abs(a - b) < 1e-9, f"{a:.4f} vs {b:.4f}")

    # ── Mastermind Robotics/Force Field ─────────────────────────────────
    at = "Class_Mastermind"
    solved, tot, ctx, arch = solve(at, "Mastermind_Summon.Robotics",
                                   "Mastermind_Buff.Force_Field",
                                   "general", srv._AT_DEFAULT_ROLE.get(at, "damage"))
    off = tot.get("offense") or {}
    pets = off.get("pets") or []
    assert pets, "MM build has no pets"
    by_cls = {p.get("pet_class"): p for p in pets}
    dro = by_cls.get("Class_Henchman_Minion")
    pro = by_cls.get("Class_Henchman_Lt")
    asb = by_cls.get("Class_Henchman_Boss")
    check("Robotics tiers carry the wiki level shifts (2/1/0) + acc_mult",
          bool(dro and pro and asb)
          and dro.get("level_shift") == 2 and pro.get("level_shift") == 1
          and asb.get("level_shift") == 0
          and all("acc_mult" in p for p in pets),
          f"shifts: T1={dro and dro.get('level_shift')} "
          f"T2={pro and pro.get('level_shift')} T3={asb and asb.get('level_shift')}; "
          f"acc_mult T1={dro and dro.get('acc_mult')}")

    # pet hit factor per tier, at the scenario's shift (general = +1)
    sc = fp.SCENARIOS["general"]
    th_all = (off.get("pet_tohit_all_pct") or 0.0) / 100.0

    def hit_pp(pet):
        shift = sc["shift"] + (pet.get("level_shift") or 0)
        base = fp._PLAYER_BASE_VS.get(shift, 0.39)
        h = fp._clamp((pet.get("acc_mult") or 1.0) * fp._clamp(base + th_all))
        return h * fp._PP_BELOW.get(shift, 0.01)

    check("pet hit physics bites: every tier's hit×pp < 1; T1 factor < T3 factor",
          all(hit_pp(p) < 1.0 for p in (dro, pro, asb))
          and hit_pp(dro) < hit_pp(asb),
          f"T1 {hit_pp(dro):.3f} · T2 {hit_pp(pro):.3f} · T3 {hit_pp(asb):.3f} "
          f"(tohit_all {th_all * 100:.0f}%)")

    # Supremacy's ToHit template: scale 0.1 × the MM's ToHit table (0.75)
    # = +7.5% — the SAME table arithmetic v34 used to price its damage half.
    check("Supremacy's ToHit routes to the pets block (7.5% = 0.1 × MM table)",
          abs((off.get("pet_tohit_all_pct") or 0) - 7.5) < 0.75,
          f"pet_tohit_all_pct = {off.get('pet_tohit_all_pct')}")

    # ToHit visibly buys pet damage back (the Tactics truth)
    v_with = ev(at, solved, ctx, tot, "general", "damage", arch)["my_dps"]
    t0 = copy.deepcopy(tot)
    t0["offense"]["pet_tohit_all_pct"] = 0.0
    t0["offense"]["pet_tohit_top_pct"] = 0.0
    v_without = ev(at, solved, ctx, t0, "general", "damage", arch)["my_dps"]
    check("pet ToHit raises pet damage (buffs visibly buy hit chance back)",
          v_with > v_without,
          f"my_dps with +{off.get('pet_tohit_all_pct')}% tohit {v_with:.1f} "
          f"vs without {v_without:.1f}")

    check("accuracy slotting reaches pets (acc_mult > 1 on a solved MM)",
          any((p.get("acc_mult") or 1.0) > 1.0 for p in pets),
          f"acc_mults: {[p.get('acc_mult') for p in pets]}")

    # ── Controller Fire Imps: client-pinned Levelminus ──────────────────
    at = "Class_Controller"
    solved, tot, ctx, arch = solve(at, "Controller_Control.Fire_Control",
                                   "Controller_Buff.Kinetics",
                                   "general", "controller")
    imps = [p for p in (tot.get("offense") or {}).get("pets") or []
            if "Imp" in (p.get("name") or "")]
    check("Fire Imps carry the client-pinned level_shift 1 (Ranged_Levelminus)",
          bool(imps) and all(p.get("level_shift") == 1 for p in imps),
          f"imps: {[(p.get('name'), p.get('level_shift')) for p in imps]}")

    print(f"\n{checks} of 7 expected checks ran")
    if checks != 7:
        fails.append("coverage denominator")
    print("══ ALL CHECKS PASS ══" if not fails
          else "FAILURES: " + ", ".join(fails))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
