"""Exemplar-view battery — every check through the real /build/calculate route.

Rules under test (wiki-pinned 2026-08-03, both wikis agree):
  - powers received above exemplar level + 5 stop contributing;
  - set bonuses live while level >= IO level - 3 (boundary tested exactly);
  - attuned pieces follow the SET's minimum level instead;
  - purple / PvP / Winter / Archetype sets are exempt at every level;
  - LotG-class piece globals follow the same per-piece rule;
  - no exemplar_level -> byte-identical behavior (the negative control).
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))
import server as srv  # noqa: E402

C = srv.app.test_client()
CHECKS, FAILS = 0, []


def check(ok, label):
    global CHECKS
    CHECKS += 1
    print(("  OK  " if ok else "  FAIL") + " " + label)
    if not ok:
        FAILS.append(label)


def pieces_of(set_name, n=6):
    out = [dict(s) for s in srv.PIECE_BY_UID.values()
           if s["set_name"].lower() == set_name.lower()][:n]
    assert out, f"no pieces found for set {set_name!r}"
    for s in out:
        s["io_level"] = 50
    return out


def calc(powers, exemplar=None):
    body = {"archetype": "Class_Blaster", "powers": powers}
    if exemplar is not None:
        body["exemplar_level"] = exemplar
    r = C.post("/build/calculate", json=body)
    assert r.status_code == 200, r.status_code
    return r.get_json()


def canon(res):
    # the Layer-2 advice companion rides every exemplared response by design —
    # identity checks compare the TOTALS, so it is stripped here
    res = dict(res)
    res.pop("exemplar_advice", None)
    return json.dumps(res, sort_keys=True)


# fixture: one early power hosting the set, one LATE defense toggle (Weave)
def host_power(slots, pick_level=1):
    return {"full_name": "Blaster_Ranged.Archery.Snap_Shot", "pick_level": pick_level,
            "include_in_totals": False, "slots": slots}


WEAVE = {"full_name": "Pool.Fighting.Weave", "pick_level": 41,
         "include_in_totals": True, "slots": [None]}

normal = pieces_of("Crushing Impact")       # ordinary set, bonuses NOT exempt
purple = pieces_of("Ragnarok")              # Very Rare: exempt at every level
# the GLOBAL piece specifically ("Defense/Increased Global Recharge Speed") —
# a 'recharge' substring match once grabbed the plain Defense/Recharge piece
# and check 6 silently tested nothing
lotg = [dict(s, io_level=50) for s in srv.PIECE_BY_UID.values()
        if s["set_name"] == "Luck of the Gambler"
        and "global" in s["piece_name"].lower()][:1]
assert lotg, "LotG global piece not found"

print("[1] determinism / negative control")
b = [host_power(normal)]
check(canon(calc(b)) == canon(calc(b)), "same payload twice -> identical result")
check(canon(calc(b)) == canon(calc(b, exemplar=None)), "exemplar_level null == absent")

print("[2] ordinary set bonuses die past IO level - 3 (exact boundary)")
base = canon(calc(b))
check(canon(calc(b, exemplar=47)) == base, "level 47 (= 50-3): bonuses alive, identical")
check(canon(calc(b, exemplar=46)) != base, "level 46: bonuses dead, totals move")

print("[3] exempt sets keep bonuses at every level")
bp = [host_power(purple)]
check(canon(calc(bp, exemplar=27)) == canon(calc(bp)), "purple set identical at 27")

print("[4] attuned pieces follow the set minimum")
att = [dict(s, attuned=True, io_level=None) for s in normal]
ba = [host_power(att)]
set_min = srv._EXEMPLAR_SET_MIN.get(normal[0]["set_uid"]) or 10
alive_at, dead_at = set_min - 3, set_min - 4
check(canon(calc(ba, exemplar=alive_at)) == canon(calc(ba)),
      f"attuned alive at set_min-3 ({alive_at})")
if dead_at >= 1:
    check(canon(calc(ba, exemplar=dead_at)) != canon(calc(ba)),
          f"attuned dead below ({dead_at})")

print("[5] a late power stops contributing past level+5")
bw = [WEAVE]
base_w = calc(bw)
ex_w = calc(bw, exemplar=27)                 # Weave picked at 41 > 27+5
check(canon(base_w) != canon(ex_w), "level-41 Weave: totals move at 27")
check(canon(calc(bw, exemplar=36)) == canon(base_w), "alive at 36 (41 <= 36+5)")
check(canon(calc(bw, exemplar=35)) != canon(base_w), "dead at 35 (41 > 35+5)")

print("[6] LotG global follows the piece rule")
bl = [host_power(lotg + [None] * 5)]
check(canon(calc(bl, exemplar=47)) == canon(calc(bl)), "LotG(50) global alive at 47")
check(canon(calc(bl, exemplar=46)) != canon(calc(bl)), "LotG(50) global dead at 46")

print("[7] Layer-2 advice companion (numbers, not vibes)")
adv = calc([host_power(normal), WEAVE], exemplar=27).get("exemplar_advice") or {}
check(adv.get("level") == 27, "advice states its level")
check(any("Weave" in p for p in adv.get("lost_powers", [])), "Weave named as lost at 27")
check((adv.get("bonuses_full") or 0) > (adv.get("bonuses_now") or 0),
      f"tiers drop ({adv.get('bonuses_full')} -> {adv.get('bonuses_now')})")
check((adv.get("bonuses_attuned") or 0) > (adv.get("bonuses_now") or 0),
      "attuned counterfactual regains tiers (set min 30 -> alive at 27 attuned)")
check(bool(adv.get("deltas")), "stat deltas present")
check("exemplar_advice" not in calc([host_power(normal)]),
      "no advice without exemplar (negative control)")

print(f"\n{CHECKS - len(FAILS)} of {CHECKS} checks passed")
if FAILS:
    sys.exit(1)
print("test_exemplar_view: PASS")
