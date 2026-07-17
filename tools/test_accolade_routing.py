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

# 5) GAME-FIRST ALIGNMENT GATE (Joel's "check the game", 2026-07-17): an accolade
#    applies only when its alignment matches the character. The hero/villain twins
#    never both apply because a character is ONE alignment — that is the game's own
#    reason, not a dedup. No-gate accolades STACK.
hero_pj = engine.calculate_build(
    {"archetype": at, "powers": [], "alignment": "hero",
     "accolades": ["Portal_Jockey"]}, srv.SET_BONUSES, ctx=ctx)
hero_both = engine.calculate_build(
    {"archetype": at, "powers": [], "alignment": "hero",
     "accolades": ["Portal_Jockey", "Born_In_Battle"]}, srv.SET_BONUSES, ctx=ctx)
ok(abs(g(hero_pj.get("max_hp")) - g(hero_both.get("max_hp"))) < 1e-9,
   "hero build: adding the VILLAIN twin (Born In Battle) changes nothing — the "
   "game leaves it dormant")
vil_bb = engine.calculate_build(
    {"archetype": at, "powers": [], "alignment": "villain",
     "accolades": ["Born_In_Battle"]}, srv.SET_BONUSES, ctx=ctx)
ok(abs(g(vil_bb.get("max_hp")) - g(hero_pj.get("max_hp"))) < 1e-9,
   "villain build: Born In Battle grants the SAME bonus its hero twin Portal "
   "Jockey does (same effect, opposite side)")
vil_pj = engine.calculate_build(
    {"archetype": at, "powers": [], "alignment": "villain",
     "accolades": ["Portal_Jockey"]}, srv.SET_BONUSES, ctx=ctx)
ok(abs(g(vil_pj.get("max_hp")) - g(base.get("max_hp"))) < 1e-9,
   "villain build: a HERO accolade (Portal Jockey) is INACTIVE — no effect")
# no-gate accolades legally STACK (the case the effect-signature version broke)
hero_stack = engine.calculate_build(
    {"archetype": at, "powers": [], "alignment": "hero",
     "accolades": ["Portal_Jockey", "Labyrinth_Conqueror"]}, srv.SET_BONUSES, ctx=ctx)
ok(g(hero_stack.get("max_hp")) > g(hero_pj.get("max_hp")) + 1e-6,
   "no-gate Labyrinth Conqueror STACKS on Portal Jockey (both apply — legal to "
   "double up, never greyed)")
# distinct same-alignment accolades still stack (the 4 hero standard)
four = engine.calculate_build(
    {"archetype": at, "powers": [], "alignment": "hero",
     "accolades": list(fp.FARM_ASSUMED_ACCOLADES)}, srv.SET_BONUSES, ctx=ctx)
ok(g(four.get("max_hp")) > g(hero_pj.get("max_hp")) + 1e-6,
   "the four hero standard accolades all STACK")

# 6) alignment gate read from the game data; server marks the standard set +
#    villain equivalents; the panel greys the off-alignment side.
tbl = engine._accolade_table()
ok(tbl["Portal_Jockey"].get("alignment") == "hero"
   and tbl["Born_In_Battle"].get("alignment") == "villain"
   and not tbl["Labyrinth_Conqueror"].get("alignment"),
   "alignment gates read from the game data (hero / villain / none)")
srv_src = open(os.path.join(ROOT, "server", "server.py"), encoding="utf-8").read()
ok("standard_assumed=is_standard(k, v)" in srv_src
   and 'v.get("alignment") == "villain"' in srv_src,
   "/accolades marks the hero standard AND their villain equivalents")
app_src = open(os.path.join(ROOT, "static", "app.js"), encoding="utf-8").read()
ok("_accInactiveAlign(" in app_src and "disabled" in
   app_src.split("function _accRow(")[1].split("\nfunction ")[0],
   "the panel greys + disables an off-alignment accolade")
ok("alignment: charAlignment()" in app_src,
   "the calculate payload sends the character's alignment (gates the totals)")

print(f"\n{checks} checks, {fails} failed")
sys.exit(1 if fails else 0)
