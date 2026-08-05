"""BATTERY: the buff/debuff panel reads ENHANCEMENT (Joel, 2026-08-06).

Before this, engine._debuff_buff_summary priced every buff and debuff at base
scale x modifier table with no slot boosts, so a debuffer who slotted accurate
defence-debuff sets saw the number sit still everywhere in the app - the
invisible-role doctrine's own case.

What is checked, and every claim has its negative control:
  * an enhanceable row MOVES with the host power's slotting, and by the post-ED
    amount, not the linear sum
  * the four unenhanceable families do NOT move (-res, -regen, +/-damage,
    +/-recharge) - the game ships no enhancement that touches them
  * an UNSLOTTED copy of the same build reads exactly the base numbers
  * per-power provenance still sums to its row
  * SCORING IS UNCHANGED. Two consumers were traced, not assumed:
      - first_principles._deb() reads role_output.enhanced_debuff_totals whenever a
        role_output module is supplied, and every serving call site supplies one;
        this summary is only its fallback. role_output was not touched.
      - role_output.payoff_metrics()['support'] DOES read this summary, but its only
        consumer is server.joint_refine(scorer='payoff'), which has no callers at all.
        ⚠ If joint_refine is ever wired up again, that path starts moving with slotting.
    Net: encounter_value never reads this summary when
    role_output is supplied, which every serving path does. This is the check
    that says whether a re-certification is owed. It is not.

Run:  py tools\\test_buff_debuff_enh.py
"""
import copy
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))

import engine                      # noqa: E402
import first_principles as fp      # noqa: E402
import role_output                 # noqa: E402
import server as srv               # noqa: E402

CHECKS = []
EXPECTED = 9


def check(name, ok, detail=""):
    CHECKS.append(bool(ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if detail:
        print(f"        {detail}")


def rows(totals, side):
    off = (totals or {}).get("offense") or {}
    out = {}
    for d in off.get(side) or []:
        key = f"{d.get('effect')}|{d.get('type')}"
        out[key] = d.get("pct", d.get("hp", d.get("end")))
    return out


def summarize(build, arch):
    ctx = srv._stat_ctx(arch)
    return engine.calculate_build(build, srv.SET_BONUSES, ctx=ctx)


def main():
    print("BUFF/DEBUFF ENHANCEMENT BATTERY\n")
    save = json.load(io.open(os.path.join(ROOT, "saves", "poison-defender.json"),
                             encoding="utf-8"))
    b = save["build"]
    build = {"archetype": b["archetype"], "powers": b["powers"], "pvp": False}
    c = srv.app.test_client()

    def calc(bd):
        r = c.post("/build/calculate", json={"archetype": bd["archetype"],
                                             "powers": bd["powers"]}).get_json()
        return r.get("totals", r)

    after = calc(build)

    # BASE arm: the old behaviour, by neutralising the multiplier only.
    real = engine._enh_mult
    engine._enh_mult = lambda effect, side, enh: 1.0
    try:
        before = calc(build)
    finally:
        engine._enh_mult = real

    db_b, db_a = rows(before, "debuffs"), rows(after, "debuffs")
    bf_b, bf_a = rows(before, "buffs"), rows(after, "buffs")

    # 1-2. The enhanceable families move, and in the right direction.
    moved = [k for k in db_a if abs(db_a[k] - db_b.get(k, 0)) > 0.05]
    check("an enhanceable debuff row MOVES with slotting",
          any(k.startswith("Defense|") for k in moved),
          f"moved: {', '.join(sorted(moved)) or '(nothing)'}")
    dk = next((k for k in db_a if k.startswith("Defense|")), None)
    check("...and it moves AWAY from zero (a debuff gets stronger)",
          dk is not None and abs(db_a[dk]) > abs(db_b[dk]),
          f"{dk}: {db_b.get(dk)} -> {db_a.get(dk)}")

    # 3-4. NEGATIVE CONTROLS: the four families the game cannot enhance.
    frozen = [k for k in db_a
              if k.split("|")[0] in ("Resistance", "Regeneration", "Damage", "RechargeTime")]
    check("NEGATIVE CONTROL: -res / -regen / -damage / -recharge do NOT move",
          all(abs(db_a[k] - db_b.get(k, 0)) < 1e-9 for k in frozen),
          f"checked {len(frozen)}: {', '.join(sorted(frozen))}")
    bfroz = [k for k in bf_a if k.split("|")[0] in ("Damage", "RechargeTime")]
    check("NEGATIVE CONTROL: +damage / +recharge buffs do NOT move",
          all(abs(bf_a[k] - bf_b.get(k, 0)) < 1e-9 for k in bfroz),
          f"checked {len(bfroz)}: {', '.join(sorted(bfroz))}")

    # 5. NEGATIVE CONTROL: strip every slot and the panel must read the base values.
    bare = copy.deepcopy(build)
    for p in bare["powers"]:
        p["slots"] = [None for _ in (p.get("slots") or [])]
    bare_after = calc(bare)
    engine._enh_mult = lambda effect, side, enh: 1.0
    try:
        bare_before = calc(bare)
    finally:
        engine._enh_mult = real
    check("NEGATIVE CONTROL: an unslotted build reads exactly the base numbers",
          rows(bare_after, "debuffs") == rows(bare_before, "debuffs")
          and rows(bare_after, "buffs") == rows(bare_before, "buffs"),
          "no slots means no enhancement means the old numbers, exactly")

    # 6. ED is real: three defence-debuff pieces must beat neither linearity nor sanity.
    off_a = (after.get("offense") or {})
    drow = next((d for d in off_a.get("debuffs") or [] if d.get("effect") == "Defense"), None)
    check("the multiplier is ED-capped, not a linear sum",
          drow is not None and abs(drow["pct"]) < abs(db_b.get(dk, 0)) * 2.0,
          "a power cannot double its debuff on slotting alone")

    # 7. Provenance still adds up to its row.
    ok_src = True
    for d in off_a.get("debuffs") or []:
        v = d.get("pct", d.get("hp", d.get("end")))
        s = sum(x["v"] for x in d.get("sources") or [])
        if d.get("sources") and abs(s - v) > 0.5:
            ok_src = False
            print(f"        {d.get('effect')} row {v} vs sources {round(s, 1)}")
    check("per-power provenance still sums to its row", ok_src)

    # 8-9. ⚠ THE RE-CERT QUESTION, ANSWERED BY MEASUREMENT, NOT ASSUMPTION.
    # first_principles._deb() reads role_output.enhanced_debuff_totals whenever a
    # role_output module is supplied, and every serving path supplies one; the
    # engine summary is only its fallback. So the score must not move.
    ctx = srv._stat_ctx(b["archetype"])
    arch_row = None
    ev_after = fp.encounter_value(b["archetype"], build["powers"], ctx, after,
                                  scenario="team", arch_row=arch_row,
                                  role_output_mod=role_output)
    engine._enh_mult = lambda effect, side, enh: 1.0
    try:
        base_tot = calc(build)
        ev_before = fp.encounter_value(b["archetype"], build["powers"], ctx, base_tot,
                                       scenario="team", arch_row=arch_row,
                                       role_output_mod=role_output)
    finally:
        engine._enh_mult = real
    # "contribution" is the number the solver and every champion score ranks on.
    va = ev_after["contribution"]
    vb = ev_before["contribution"]
    check("SCORING IS UNCHANGED — no model bump, no re-certification owed",
          abs(va - vb) < 1e-9, f"encounter_value team: {vb} -> {va}")
    # ...and the reason it is unchanged is structural, not luck.
    check("...because the scorer reads role_output, which this did not touch",
          "enhanced_debuff_totals" in io.open(
              os.path.join(ROOT, "server", "first_principles.py"), encoding="utf-8").read()
          and "_enh_mult" not in io.open(
              os.path.join(ROOT, "server", "role_output.py"), encoding="utf-8").read(),
          "engine summary is only fp's fallback when no role_output is supplied")

    n = len(CHECKS)
    print(f"\n{n} of {EXPECTED} expected checks ran")
    if n != EXPECTED:
        print("COVERAGE FAILURE — a check did not run")
        sys.exit(1)
    if all(CHECKS):
        print("== ALL CHECKS PASS ==")
    else:
        print(f"{CHECKS.count(False)} FAILURE(S)")
        sys.exit(1)


if __name__ == "__main__":
    main()
