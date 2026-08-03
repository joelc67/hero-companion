"""Attribution-ledger battery (Stats provenance, phase 1) — real route only.

The two laws:
  1. CONSERVATION: for every stat, the ledger's deltas sum to the displayed
     total (the ledger is a decomposition, not an estimate).
  2. INERTNESS: the ledger changes nothing — totals with the flag off are
     byte-identical, and the flag-off response carries no ledger at all.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))
import server as srv  # noqa: E402
import engine  # noqa: E402

C = srv.app.test_client()
CHECKS, FAILS = 0, []


def check(ok, label):
    global CHECKS
    CHECKS += 1
    print(("  OK  " if ok else "  FAIL") + " " + label)
    if not ok:
        FAILS.append(label)


def pieces_of(set_name, n=6):
    out = [dict(s, io_level=50) for s in srv.PIECE_BY_UID.values()
           if s["set_name"].lower() == set_name.lower()][:n]
    assert out, set_name
    return out


lotg_g = [dict(s, io_level=50) for s in srv.PIECE_BY_UID.values()
          if s["set_name"] == "Luck of the Gambler"
          and "global" in s["piece_name"].lower()][:1]

build = {"archetype": "Class_Blaster", "powers": [
    {"full_name": "Pool.Fighting.Weave", "pick_level": 30,
     "include_in_totals": True, "slots": lotg_g + [None]},
    {"full_name": "Blaster_Ranged.Archery.Snap_Shot", "pick_level": 1,
     "include_in_totals": False, "slots": pieces_of("Crushing Impact")},
]}

res = C.post("/build/calculate", json=build).get_json()
attr = res.get("attribution")

print("[1] the ledger exists and knows its layers")
check(isinstance(attr, list) and attr, f"attribution present ({len(attr or [])} rows)")
kinds = {r.get("kind") for r in (attr or [])}
check("power" in kinds, "power self-buff rows (Weave)")
check("set_bonus" in kinds, "set-bonus rows (Crushing Impact)")
check("global" in kinds, "piece-global rows (LotG +rech)")
g = next((r for r in attr if r.get("kind") == "global"), {})
check(g.get("power") == "Pool.Fighting.Weave" and g.get("slot") == 0,
      "global row names its power AND slot index")

print("[2] CONSERVATION: ledger sums == displayed totals")
sums = {}
for r in attr or []:
    for k, v in (r.get("effects") or {}).items():
        sums[k] = sums.get(k, 0.0) + v


def shown(key):
    if ":" in key:
        bucket, t = key.split(":", 1)
        row = (res.get(bucket) or {}).get(t) or {}
        return row.get("raw", row.get("value"))
    v = res.get(key)
    if isinstance(v, dict):
        return v.get("raw", v.get("value"))
    return v


checked_keys = 0
for key in ("defense:Smashing", "defense:Melee", "resistance:Smashing",
            "recharge", "recovery", "regeneration", "accuracy", "max_hp"):
    disp = shown(key)
    if disp is None:
        continue
    ledger_pct = round(sums.get(key, 0.0) * 100.0, 2)
    ok = abs(ledger_pct - disp) <= 0.03
    checked_keys += 1
    check(ok, f"{key}: ledger {ledger_pct} == shown {disp}")
check(checked_keys >= 6, f"conservation covered enough stats ({checked_keys})")

print("[3] INERTNESS: the ledger never changes the math")
ctx = srv._stat_ctx("Class_Blaster")
on = engine.calculate_build(json.loads(json.dumps(build)), srv.SET_BONUSES,
                            ctx=dict(ctx, attribution=True))
off = engine.calculate_build(json.loads(json.dumps(build)), srv.SET_BONUSES, ctx=ctx)
check("attribution" not in off, "no ledger without the flag")
on.pop("attribution", None)
check(json.dumps(on, sort_keys=True) == json.dumps(off, sort_keys=True),
      "totals byte-identical with the flag on")

print(f"\n{CHECKS - len(FAILS)} of {CHECKS} checks passed")
if FAILS:
    sys.exit(1)
print("test_stat_attribution: PASS")
