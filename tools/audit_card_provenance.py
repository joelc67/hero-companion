"""PINS for v34 item 5 — per-power-card provenance (Joel's ruling 2026-07-17
+ the 5:35 AM amendment's THREE LAWS). RELEASE-BLOCKING for the next cut.

The amendment's constraint, pinned so it can never drift: attribution is a
DISPLAY of the engine's own ledger, never new math.

  LAW 1 — READ, NEVER RE-ADD. The per-card line reads engine ledgers
    (atk.global_dmg_raw / global_dmg_eff, totals.damage_buff); the feature
    adds ZERO arithmetic to totals. Pin: the displayed attack `damage` is
    identical whether or not the ledger fields are emitted (they are pure
    read-outs), and on an uncapped build effective == raw == damage_buff.
  LAW 2 — NO PER-CARD MULTIPLICATION. A global on N cards is ONE source, not
    N additions. Pin: global_dmg_raw is identical on every attack card, and
    no card's effective contribution exceeds that single raw global.
  LAW 3 — GAME BOUNDARIES STATED, NOT SUPERSEDED. Where the game's damage cap
    bites, the card shows the EFFECTIVE value the engine applied and says so.
    Pin: at a cap boundary (enh+global over cap) the attack's global_dmg_eff
    is < global_dmg_raw and >= 0 — the number the card prints.

Plus the class boundary (accolade +MaxHP never a per-card damage share) and
the live-flip rail rule, and the static composition pins.

Run:  py tools\\audit_card_provenance.py
"""
import copy
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import engine  # noqa: E402
import first_principles as fp  # noqa: E402
import server as srv  # noqa: E402

checks = 0
fails = 0


def ok(cond, msg):
    global checks, fails
    checks += 1
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        fails += 1


AT = "Class_Brute"
ctx = srv._stat_ctx(AT)
ctx["power_by_full"] = srv.POWER_BY_FULL
ATTACKS = [{"full_name": "Brute_Melee.Battle_Axe.Chop"},
           {"full_name": "Brute_Melee.Battle_Axe.Gash"}]

alpha_full = None
for full, fx in (ctx.get("incarnate_fx") or {}).items():
    if "Musculature" in full and any(e.get("effect") == "DamageBuff" for e in fx):
        alpha_full = full
        break
ok(alpha_full is not None,
   f"a DamageBuff Musculature Alpha exists in incarnate_fx ({alpha_full})")


def offense(build_extra):
    b = {"archetype": AT, "powers": copy.deepcopy(ATTACKS)}
    b.update(build_extra)
    t = engine.calculate_build(b, srv.SET_BONUSES, ctx=ctx)
    return {a["name"]: a for a in (t.get("offense") or {}).get("attacks") or []}, t


def dmg(a):
    return float(str(a.get("damage", 0)).split()[0] or 0)


base_atk, base_t = offense({})
on_atk, on_t = offense({"include_incarnates": True,
                        "incarnates_full": {"Alpha": alpha_full}})

# ── LAW 1: read, never re-add ───────────────────────────────────────────────
ok(not base_t.get("damage_buff"), "incarnates OFF -> no damage_buff ledger")
gb = on_t.get("damage_buff") or 0
ok(gb > 0.2, f"incarnates ON (Musculature) -> damage_buff ledger = {gb}")
# every attack's displayed damage rises, and the card reads the ledger the
# engine ALREADY used to produce that number (no second computation)
rose = [n for n in base_atk if dmg(on_atk[n]) > dmg(base_atk[n]) + 1e-6]
ok(len(rose) == len(base_atk),
   f"EVERY attack's damage/hit rises under the flip ({len(rose)}/{len(base_atk)})")
uncapped_eff_eq_raw = all(
    abs(a.get("global_dmg_eff", 0) - a.get("global_dmg_raw", 0)) < 1e-9
    and abs(a.get("global_dmg_raw", 0) - gb) < 1e-9 for a in on_atk.values())
ok(uncapped_eff_eq_raw,
   "uncapped build: every card's effective == raw == the build damage_buff "
   "(the card is a pure read-out)")

# ── LAW 2: no per-card multiplication (one source, N cards) ──────────────────
raws = {round(a.get("global_dmg_raw", 0), 6) for a in on_atk.values()}
ok(len(raws) == 1 and abs(next(iter(raws)) - gb) < 1e-9,
   "global_dmg_raw is IDENTICAL on every card = one source, not N additions")
ok(all(a.get("global_dmg_eff", 0) <= a.get("global_dmg_raw", 0) + 1e-9
       for a in on_atk.values()),
   "no card's effective contribution exceeds the single raw global")

# ── LAW 3: game boundaries stated, not superseded ───────────────────────────
# inject a small damage cap so enh+global exceeds it: the engine must report a
# reduced effective global on the capped attack (the number the card prints).
capped_ctx = copy.deepcopy(ctx)
capped_ctx["power_by_full"] = srv.POWER_BY_FULL   # deepcopy drops the ref
capped_ctx["at_damage_cap"] = 0.2                 # 20% total damage-boost ceiling
b = {"archetype": AT, "powers": copy.deepcopy(ATTACKS),
     "include_incarnates": True, "incarnates_full": {"Alpha": alpha_full}}
cap_t = engine.calculate_build(b, srv.SET_BONUSES, ctx=capped_ctx)
cap_atk = {a["name"]: a for a in (cap_t.get("offense") or {}).get("attacks") or []}
some = next(iter(cap_atk.values()))
ok(some.get("global_dmg_raw", 0) > some.get("global_dmg_eff", 0) + 1e-6,
   f"at the damage cap: raw {some.get('global_dmg_raw')} > effective "
   f"{some.get('global_dmg_eff')} (the card states the capped value)")
ok(some.get("global_dmg_eff", -1) >= 0,
   "effective global never goes negative under the cap")

# ── class boundary: accolades move MaxHP, never an attack's damage ──────────
FARM4 = list(fp.FARM_ASSUMED_ACCOLADES)
acc_atk, acc_t = offense({"accolades": FARM4})
g = lambda x: (x.get("value", 0) or 0) if isinstance(x, dict) else (x or 0)
ok(g(acc_t.get("max_hp")) > g(base_t.get("max_hp")) + 5,
   "accolades ticked -> MaxHP rises (build-scope)")
ok(all(abs(dmg(acc_atk[n]) - dmg(base_atk[n])) < 1e-6 for n in base_atk),
   "accolades ticked -> NO attack damage moves (never a per-card share)")

# ── static composition + live-flip pins ─────────────────────────────────────
app = open(os.path.join(ROOT, "static", "app.js"), encoding="utf-8").read()
rpi = app.split("async function renderPowerInfo()")[1].split("\nfunction ")[0]
ok("cardAttributionHtml(atk)" in rpi,
   "renderPowerInfo composes the card-scope attribution line")
ok("cardProvenanceFooterHtml()" in rpi,
   "renderPowerInfo composes the provenance footer on every ⓘ card")
card_body = app.split("function cardAttributionHtml(")[1].split("\nfunction ")[0]
ok("global_dmg_raw" in card_body and "global_dmg_eff" in card_body,
   "the card line reads the engine's per-attack ledger (raw + effective)")
ok("damage cap holds it to" in card_body,
   "law 3: the card states the capped value in words when raw != effective")
rec_body = app.split("async function recompute(")[1].split("\nasync function ")[0]
ok("renderRail()" in rec_body,
   "recompute() re-renders the rail — an open ⓘ card updates live on any flip")

print(f"\n{checks} checks, {fails} failed")
sys.exit(1 if fails else 0)
