"""Layer-3 battery: the solver optimizing FOR a target level, real routes only.

Pins, in order of importance:
  1. ABSENT PARAM = BYTE-IDENTICAL SOLVE (the certification safety pin: a solve
     without target_level, and one with target_level=null, match exactly).
  2. A target-level solve states itself (response field + understood echo).
  3. Emission rule: every solver-placed piece of a NON-exempt set that survives
     the target only attuned ships attuned=True.
  4. End-to-end: evaluated AT the target level, the target solve keeps at least
     as many set-bonus tiers as the plain solve (the whole point).
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))
import server as srv  # noqa: E402

client = srv.app.test_client()
CHECKS, FAILS = 0, []
TL = 27


def check(ok, label):
    global CHECKS
    CHECKS += 1
    print(("  OK  " if ok else "  FAIL") + " " + label)
    if not ok:
        FAILS.append(label)


def canon(powers):
    return json.dumps([{"f": p["full_name"], "s": p.get("slots")} for p in powers],
                      sort_keys=True)


ap = client.post("/build/autopick", json={
    "archetype": "Class_Brute", "primary": "Brute_Melee.Spines",
    "secondary": "Brute_Defense.Fiery_Aura", "content": "general"}).get_json()
pre = [{"full_name": q["full_name"], "slots": q.get("slots"),
        "earned_slot_count": q.get("earned_slot_count"),
        "pick_level": q.get("pick_level")} for q in ap["powers"]]


def solve(**extra):
    body = {"archetype": "Class_Brute", "goal": "", "tier": "premium",
            "content": "general", "preserve": False, "keep_layout": False,
            "powers": json.loads(json.dumps(pre))}
    body.update(extra)
    return client.post("/build/solve", json=body).get_json()


print("[1] absent param = byte-identical (certification safety pin)")
plain1 = solve()
plain2 = solve()
nulled = solve(target_level=None)
check(canon(plain1["powers"]) == canon(plain2["powers"]), "plain solve deterministic")
check(canon(plain1["powers"]) == canon(nulled["powers"]), "target_level null == absent")
check(plain1.get("target_level") is None, "no target_level echoed on a plain solve")

print(f"[2] a target-level solve states itself (level {TL})")
tsol = solve(target_level=TL)
check(tsol.get("ok"), "target solve succeeds")
check(tsol.get("target_level") == TL, "response carries target_level")
check(any("Optimized FOR level" in u for u in tsol.get("understood") or []),
      "understood echoes the target-level statement")

print("[3] emission: surviving non-exempt sets ship attuned")
viol, attuned_n = [], 0
for p in tsol["powers"]:
    if p.get("locked"):
        continue
    for s in p.get("slots") or []:
        if not (s and s.get("set_uid")):
            continue
        uid = s["set_uid"]
        if uid.startswith("HO_") or uid in srv._EXEMPLAR_EXEMPT_UIDS:
            continue
        pn = (s.get("piece_name") or "").lower()
        # PROC-PASS placements are out of the attune promise: damage/debuff
        # PROCS keep firing when exemplared (the game's proc rule — why proc
        # builds exemplar well), and Hamidon cores carry no set bonuses. The
        # ILP's attune pass runs before the proc pass by construction.
        if "chance" in pn:
            continue
        sb = (srv.SET_BY_UID.get(uid) or {})
        if not (srv.SET_BONUSES.get(uid) or {}).get("bonuses"):
            continue
        if (srv._EXEMPLAR_SET_MIN.get(uid) or 10) - 3 <= TL:
            if s.get("attuned"):
                attuned_n += 1
            else:
                viol.append(f"{p['full_name']}:{s.get('piece_name')}")
check(attuned_n > 0, f"attuned pieces were emitted ({attuned_n})")
check(not viol, f"no surviving non-exempt piece shipped un-attuned (bad: {viol[:4]})")

print(f"[4] end-to-end: better AT level {TL} than the plain solve")


def tiers_at(powers, exl):
    r = client.post("/build/calculate", json={
        "archetype": "Class_Brute", "powers": powers,
        "exemplar_level": exl}).get_json()
    return r.get("applied_bonus_count") or 0


t_t, t_p = tiers_at(tsol["powers"], TL), tiers_at(plain1["powers"], TL)
check(t_t >= t_p, f"target solve keeps >= tiers at {TL} ({t_t} vs plain {t_p})")
t50_t, t50_p = tiers_at(tsol["powers"], None), tiers_at(plain1["powers"], None)
print(f"       (context: tiers at 50 — target-solve {t50_t}, plain {t50_p})")

print(f"\n{CHECKS - len(FAILS)} of {CHECKS} checks passed")
if FAILS:
    sys.exit(1)
print("test_target_level_solve: PASS")
