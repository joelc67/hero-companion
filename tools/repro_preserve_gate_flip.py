"""REPRO: preserve-mode solve oscillates (period 2) since 053c76bd.

The activation-gated-proc host rule (HC_PROC_HOST_GATE, correct in itself)
interacts with preserve mode: pressing "solve" repeatedly on a fully-imported
preserve=True build flips Blazing Aura between {Perfect Zinger, Overwhelming
Force} and {Fury of the Gladiator, Eradication} procs on EVERY press — locked
slots are supposed to be byte-identical. Decisive A/B: HC_PROC_HOST_GATE=0
makes all three presses byte-stable, gate on flips A->B->A.
Standing detector: audit_slot_conservation.py (arm 2) stays RED until fixed.
Found by the 2026-08-04 full-sweep; bisected v0.12.30 (green) -> 053c76bd (red).
"""
import sys, os, json, copy, tempfile
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
os.environ["APPDATA"] = tempfile.mkdtemp()
import server as srv
client = srv.app.test_client()

ap = client.post("/build/autopick", json={
    "archetype": "Class_Brute", "primary": "Brute_Melee.Spines",
    "secondary": "Brute_Defense.Fiery_Aura", "content": "fire_farm"}).get_json()
r0 = client.post("/build/solve", json={
    "archetype": "Class_Brute", "content": "fire_farm",
    "powers": ap["powers"], "tier": "premium", "preserve": False}).get_json()
full = [{"full_name": p["full_name"], "slots": p.get("slots"),
         "earned_slot_count": len(p.get("slots") or [])} for p in r0["powers"]]

def press(powers):
    body = {"archetype": "Class_Brute", "content": "fire_farm",
            "powers": copy.deepcopy(powers), "tier": "premium",
            "preserve": True, "keep_layout": False}
    r = client.post("/build/solve", json=body).get_json()
    return r["powers"]

p1 = press(full)
p2 = press([{"full_name": p["full_name"], "slots": p.get("slots"),
             "earned_slot_count": len(p.get("slots") or [])} for p in p1])
p3 = press([{"full_name": p["full_name"], "slots": p.get("slots"),
             "earned_slot_count": len(p.get("slots") or [])} for p in p2])

def sig(powers):
    return {p["full_name"]: [(s or {}).get("piece_uid") for s in (p.get("slots") or [])]
            for p in powers}

s1, s2, s3 = sig(p1), sig(p2), sig(p3)
for a, b, tag in ((s1, s2, "press1->press2"), (s2, s3, "press2->press3")):
    diffs = {k: (a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k)}
    print(f"\n== {tag}: {len(diffs)} power(s) changed ==")
    for k, (x, y) in list(diffs.items())[:6]:
        print(f"  {k}\n    was: {x}\n    now: {y}")
