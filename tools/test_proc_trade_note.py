"""Piece 1 check (2026-07-28): the proc-vs-set trade ledger.

The optimizer already made the proc-vs-set trade when it slotted a power; Piece 1
surfaces WHY on the ⓘ card, from the engine's own numbers. This proves the chain:

  1. proc_pass records _proc_trade (kind + displaced slots) on powers it changed
  2. the engine's offense rows carry proc_dmg / proc_n / proc_per, and a traded
     power's row carries trade_kind / trade_sets / trade_set_dmg
  3. NEGATIVE CONTROL: an attack with no damage procs reads proc_dmg 0 and no
     trade fields (the note renders nothing — nothing invented)
  4. INVARIANCE: the fields are display-only — a second engine pass with every
     _proc_trade stripped yields byte-identical damage numbers

Run:  py tools\\test_proc_trade_note.py
"""
import copy
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv  # noqa: E402
import proc_pass  # noqa: E402

# A known proc-bomb context: SS/WP Brute, offense role — Foot Stomp is the
# classic AoE nuke the pass bombs (also the guided tour's example).
AT, PRIM, SEC, CONTENT = "Class_Brute", "Super_Strength", "Willpower", "general"

checks = 0
fails = []


def check(name, ok, detail=""):
    global checks
    checks += 1
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    if not ok:
        fails.append(name)


def main():
    role = srv._AT_DEFAULT_ROLE.get(AT, "damage")
    arch_row = srv.ARCH_BY_NAME.get(AT)
    res_cap = round((arch_row.get("res_cap") or 0.75) * 100, 1)
    pre = srv.ai_build.preset_targets(CONTENT, role, res_cap=res_cap)
    ctx = srv._stat_ctx(AT)
    ctx["power_by_full"] = srv.POWER_BY_FULL

    client = srv.app.test_client()
    ap_res = client.post("/build/autopick", json={
        "archetype": AT, "primary": PRIM, "secondary": SEC,
        "content": CONTENT}).get_json()
    assert ap_res and ap_res.get("powers"), "autopick failed"

    r = srv._assess_solve(AT, copy.deepcopy(ap_res["powers"]),
                          copy.deepcopy(pre["targets"]), "premium",
                          pre["perk_focus"], pre["roles"], False, False, False,
                          with_powers=True)
    assert r, "solve failed"
    _tot, solved = r
    solved = proc_pass.apply_proc_pass(solved, srv.POWER_BY_FULL, role=role,
                                       content=CONTENT)
    tot = srv.engine.calculate_build({"archetype": AT, "powers": solved},
                                     srv.SET_BONUSES, res_cap=res_cap, ctx=ctx)
    attacks = (tot.get("offense") or {}).get("attacks") or []
    assert attacks, "no offense rows"
    by_name = {a["name"]: a for a in attacks}

    # 1. the pass recorded trades
    traded = [p for p in solved if p.get("_proc_trade")]
    kinds = sorted({p["_proc_trade"]["kind"] for p in traded})
    check("proc_pass records _proc_trade on changed powers",
          bool(traded), f"{len(traded)} powers, kinds={kinds}")

    # 2. the engine ledger carries the fields
    ledger_ok = all(("proc_dmg" in a and "proc_n" in a and "proc_per" in a)
                    for a in attacks)
    check(f"every offense row carries the proc ledger ({len(attacks)} of "
          f"{len(attacks)} rows)", ledger_ok)
    traded_rows = []
    for p in traded:
        a = by_name.get((srv.POWER_BY_FULL.get(p["full_name"]) or {})
                        .get("display_name"))
        if a is not None:
            traded_rows.append((p, a))
    with_fields = [a for _p, a in traded_rows if a.get("trade_kind")]
    check("traded powers' rows carry trade_kind/trade_sets/trade_set_dmg",
          bool(traded_rows) and len(with_fields) == len(traded_rows),
          f"{len(with_fields)} of {len(traded_rows)} traded attack rows")
    bombed = [(p, a) for p, a in traded_rows
              if a.get("trade_kind") in ("bomb", "hybrid")]
    check("a bombed/hybrid row prices BOTH sides (proc_dmg > 0, sets named)",
          any(a.get("proc_dmg", 0) > 0 and a.get("trade_sets")
              for _p, a in bombed) if bombed else bool(traded_rows),
          f"{len(bombed)} bomb/hybrid rows")

    # 3. negative control — an un-traded, proc-free attack shows nothing
    clean = [a for a in attacks
             if a.get("proc_n") == 0 and "trade_kind" not in a]
    neg_ok = all(a.get("proc_dmg") == 0 for a in clean)
    check(f"NEGATIVE CONTROL: proc-free attacks read proc_dmg 0, no trade "
          f"fields ({len(clean)} rows)", bool(clean) and neg_ok)

    # 4. display-only invariance: strip every note, re-run the engine —
    # damage numbers must be identical (the note never feeds the math)
    stripped = copy.deepcopy(solved)
    for p in stripped:
        p.pop("_proc_trade", None)
    tot2 = srv.engine.calculate_build({"archetype": AT, "powers": stripped},
                                      srv.SET_BONUSES, res_cap=res_cap, ctx=ctx)
    a2 = {a["name"]: a for a in (tot2.get("offense") or {}).get("attacks") or []}
    inv = all(a["damage"] == a2[a["name"]]["damage"]
              and a.get("dps_spam") == a2[a["name"]].get("dps_spam")
              for a in attacks if a["name"] in a2)
    check("INVARIANCE: stripping notes changes no damage number", inv)

    # sanity: the note's proc number never exceeds the row's total damage
    sane = all((a.get("proc_dmg") or 0) <= (a.get("damage") or 0) + 1e-6
               for a in attacks)
    check("sanity: proc_dmg <= total damage on every row", sane)

    # 5. THE REAL APP PATH: /build/solve's response must carry both halves the
    # UI reads — _proc_trade on powers, the proc ledger on offense rows (a
    # route that strips either would pass every internal check and still ship
    # a silent note).
    pre = [{"full_name": p["full_name"], "slots": p.get("slots"),
            "earned_slot_count": p.get("earned_slot_count")}
           for p in ap_res["powers"]]
    sol = client.post("/build/solve", json={
        "archetype": AT, "goal": "", "tier": "premium", "content": CONTENT,
        "preserve": False, "keep_layout": False, "powers": pre}).get_json()
    sp = (sol or {}).get("powers") or []
    sa = (((sol or {}).get("totals") or {}).get("offense") or {}).get("attacks") or []
    check("REAL PATH: /build/solve ships _proc_trade + the proc ledger",
          any(p.get("_proc_trade") for p in sp)
          and sa and all("proc_dmg" in a for a in sa),
          f"{sum(1 for p in sp if p.get('_proc_trade'))} traded powers, "
          f"{len(sa)} ledger rows in the route response")

    print(f"\n{checks} of 8 expected checks ran")
    if checks != 8:
        fails.append("coverage denominator")
    print("══ ALL CHECKS PASS ══" if not fails
          else "FAILURES: " + ", ".join(fails))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
