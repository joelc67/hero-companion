"""v34 deliverable #1 regression pins: accolades route through game data, the
engine and scoring paths AGREE, amplifiers are split off, and the hardcoded
+10% is gone.

Run:  py tools\\test_accolade_routing.py
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import engine  # noqa: E402
import first_principles as fp  # noqa: E402
import server as srv  # noqa: E402

FARM4 = list(fp.FARM_ASSUMED_ACCOLADES)
checks = 0
fails = 0


def ok(cond, msg):
    global checks, fails
    checks += 1
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        fails += 1


# 1) the hardcoded +10% accolade approximation is retired
src = open(os.path.join(ROOT, "server", "engine.py"), encoding="utf-8").read()
amp_block = src.split("AMPLIFIER_BUFFS = [")[1].split("]")[0]
ok('"effect": "HitPoints"' not in amp_block,
   "no HitPoints (accolade) effect inside the AMPLIFIER_BUFFS list")
ok("EXTERNAL_BUFFS = [" not in src, "the bundled EXTERNAL_BUFFS list is gone")

# 2) engine's accolade HP == scoring-path accolade HP, per AT (the parity pin)
for at in ("Class_Brute", "Class_Tanker", "Class_Blaster", "Class_Controller"):
    ctx = srv._stat_ctx(at)
    mod_tables = ctx["modifier_tables"]
    col = ctx["at_column"]
    eng_hp = 0.0
    for k in FARM4:
        rec = engine._accolade_table().get(k)
        if rec:
            eng_hp += engine.accolade_flat(rec, mod_tables, col)[0]
    fp_hp, _names = fp.accolade_bonus_hp(ctx)
    ok(abs(eng_hp - fp_hp) < 0.05,
       f"{at}: engine accolade HP {eng_hp:.1f} == scoring path {fp_hp:.1f}")

# 3) checked accolades MOVE the displayed total; unchecked move nothing
at = "Class_Brute"
ctx = srv._stat_ctx(at); ctx["power_by_full"] = srv.POWER_BY_FULL
base = engine.calculate_build({"archetype": at, "powers": []},
                              srv.SET_BONUSES, ctx=ctx)
with_acc = engine.calculate_build({"archetype": at, "powers": [],
                                   "accolades": FARM4}, srv.SET_BONUSES, ctx=ctx)
g = lambda x: (x.get("value", 0) or 0) if isinstance(x, dict) else (x or 0)
# display max_hp is already in PERCENT
d_hp = g(with_acc.get("max_hp")) - g(base.get("max_hp"))
ok(10.0 < d_hp < 30.0, f"4 checked accolades raise MaxHP by {d_hp:.1f}% "
                       f"(~21% expected on a Brute)")
ok(with_acc.get("accolade_ledger") and len(with_acc["accolade_ledger"]) >= 3,
   "attribution ledger surfaced to the display (>=3 HP-bearing accolades named)")
none = engine.calculate_build({"archetype": at, "powers": [], "accolades": []},
                              srv.SET_BONUSES, ctx=ctx)
ok(abs(g(none.get("max_hp")) - g(base.get("max_hp"))) < 1e-9,
   "empty accolade list moves nothing")

# 4) amplifiers are independently toggleable and no longer imply accolades
amp = engine.calculate_build({"archetype": at, "powers": [],
                              "include_amplifiers": True}, srv.SET_BONUSES, ctx=ctx)
ok(abs(g(amp.get("max_hp")) - g(base.get("max_hp"))) < 1e-9,
   "amplifiers ON, accolades OFF -> MaxHP unchanged (split proven; the old "
   "bundle would have added +10% here)")

# 5) Joel's ruling (2026-07-17): a same-EFFECT accolade applies ONCE no matter
#    how many of its names are checked (hero/villain twins are one accolade) —
#    NEGATIVE CONTROL: Portal Jockey + Born In Battle are +HP0.5/+End5.0 twins.
one = engine.calculate_build({"archetype": at, "powers": [],
                              "accolades": ["Portal_Jockey"]},
                             srv.SET_BONUSES, ctx=ctx)
twin = engine.calculate_build({"archetype": at, "powers": [],
                               "accolades": ["Portal_Jockey", "Born_In_Battle"]},
                              srv.SET_BONUSES, ctx=ctx)
ok(abs(g(one.get("max_hp")) - g(twin.get("max_hp"))) < 1e-9
   and abs((one.get("max_end_bonus") or 0) - (twin.get("max_end_bonus") or 0)) < 1e-9,
   "same-effect twins (Portal Jockey + Born In Battle) apply ONCE — the "
   "second name adds nothing (no double-count)")
duprec = [x for x in twin.get("accolade_ledger", []) if x.get("duplicate_of")]
ok(len(duprec) == 1 and duprec[0]["hp"] == 0.0,
   "the deduped twin is recorded in the ledger as a 0-value duplicate (honest, "
   "not hidden)")
# distinct accolades STILL stack (the 4 standard are all distinct signatures)
four = engine.calculate_build({"archetype": at, "powers": [],
                               "accolades": list(fp.FARM_ASSUMED_ACCOLADES)},
                              srv.SET_BONUSES, ctx=ctx)
ok(g(four.get("max_hp")) > g(one.get("max_hp")) + 1e-6,
   "distinct accolades still STACK — dedup only collapses identical effects, "
   "never real ones")

print(f"\n{checks} checks, {fails} failed")
sys.exit(1 if fails else 0)
