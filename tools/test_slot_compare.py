"""Battery for /build/slot_compare — "what would each replacement do?"
(Joel, 2026-08-06: "can there be a % increase or deficit shown in the list of
replacement IOs?").

    py tools\\test_slot_compare.py

The route prices every candidate by REBUILDING the character with it in the
slot, through the real /build/calculate. These checks pin the properties that
make that trustworthy: the direction is real in BOTH directions (a gain is not
merely absent), a set tier shows up as a bonus-count move, the refusals hold,
and the numbers agree with a plain calculate of the same build.

Negative-controlled: the "gain" arm is built by emptying the slot first, so a
route that always returned the base numbers would fail it.
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv  # noqa: E402

CHECKS = []
EXPECTED = 9          # coverage denominator — hard-fail if a check silently skips


def check(label, ok, why=""):
    CHECKS.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    if not ok and why:
        print(f"        {why}")


def main():
    c = srv.app.test_client()
    ap = c.post("/build/autopick", json={
        "archetype": "Class_Scrapper", "primary": "Scrapper_Melee.Claws",
        "secondary": "Scrapper_Defense.Super_Reflexes",
        "content": "general", "role": "damage"}).get_json()
    pw = [{"full_name": p["full_name"], "slots": []} for p in ap["powers"]
          if not p["full_name"].startswith("Incarnate")]
    sol = c.post("/build/solve", json={
        "archetype": "Class_Scrapper", "powers": pw, "content": "general",
        "role": "damage", "preserve": False}).get_json()
    powers = sol["powers"]

    pi = si = None
    for a, p in enumerate(powers):
        for b, s in enumerate(p.get("slots") or []):
            if s and s.get("piece_uid") and s.get("set_uid"):
                pi, si = a, b
                break
        if pi is not None:
            break
    assert pi is not None, "fixture: no set piece slotted"
    piece = powers[pi]["slots"][si]
    KEYS = ["defense.Melee", "applied_bonus_count"]

    def call(pws, cands, **extra):
        body = {"archetype": "Class_Scrapper", "powers": pws,
                "power_index": pi, "slot_index": si,
                "candidates": cands, "keys": KEYS}
        body.update(extra)
        return c.post("/build/slot_compare", json=body).get_json()

    # ── 1-3. THE GAIN ARM. Base = the slot EMPTY, so putting the real piece
    # back must read as a gain on both axes. A route that echoed the base
    # numbers, or that only ever subtracted, fails here.
    import copy
    emptied = copy.deepcopy(powers)
    emptied[pi]["slots"][si] = None
    r = call(emptied, [piece])
    check("gain arm answers", bool(r and r.get("ok")), r)
    got, base = (r.get("results") or [None])[0], r.get("base") or {}
    check("re-adding the piece GAINS defence",
          got and got["defense.Melee"] - base["defense.Melee"] > 0.5,
          f"base {base} vs {got}")
    check("...and gains the set bonus it completes",
          got and got["applied_bonus_count"] - base["applied_bonus_count"] >= 1,
          "a set TIER is the cost an analytic guess cannot see")

    # ── 4-5. THE DEFICIT ARM, from the real build: emptying the slot must lose
    # exactly what the gain arm won. Same numbers, opposite sign — if the two
    # arms disagree the route is not measuring one build.
    r2 = call(powers, [None])
    lost, base2 = (r2.get("results") or [None])[0], r2.get("base") or {}
    check("emptying the slot LOSES defence",
          lost and base2["defense.Melee"] - lost["defense.Melee"] > 0.5)
    check("the two arms agree to a hundredth",
          lost and abs((base2["defense.Melee"] - lost["defense.Melee"])
                       - (got["defense.Melee"] - base["defense.Melee"])) < 0.01,
          "the gain and the deficit are the same swap seen from either side")

    # ── 6. AGREES WITH A PLAIN CALCULATE of the same build — the route must not
    # be a second opinion about the character the Stats page is showing.
    plain = c.post("/build/calculate", json={"archetype": "Class_Scrapper",
                                             "powers": powers}).get_json()
    pv = (plain.get("totals") or plain).get("defense", {}).get("Melee")
    pv = pv.get("raw", pv.get("value")) if isinstance(pv, dict) else pv
    check("base matches a plain /build/calculate",
          pv is not None and abs(pv - base2["defense.Melee"]) < 0.01,
          f"plain {pv} vs route {base2.get('defense.Melee')}")

    # ── 7-9. REFUSALS. Each is a way to hang or mislead the picker.
    check("refuses too many candidates",
          call(powers, [piece] * 401).get("ok") is False,
          "400+ would stall the picker rather than answer it")
    check("refuses an out-of-range power_index",
          c.post("/build/slot_compare", json={
              "archetype": "Class_Scrapper", "powers": powers,
              "power_index": 9999, "slot_index": 0,
              "candidates": [None], "keys": KEYS}).get_json().get("ok") is False)

    check("refuses a missing slot_index",
          c.post("/build/slot_compare", json={
              "archetype": "Class_Scrapper", "powers": powers,
              "power_index": pi, "candidates": [None],
              "keys": KEYS}).get_json().get("ok") is False)

    print(f"\n{len(CHECKS)} of {EXPECTED} expected checks ran")
    if len(CHECKS) != EXPECTED:
        raise SystemExit("COVERAGE FAILURE — a check did not run")
    bad = CHECKS.count(False)
    print("══ ALL CHECKS PASS ══" if not bad else f"{bad} FAILURE(S)")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
