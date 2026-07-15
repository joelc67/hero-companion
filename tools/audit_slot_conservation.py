"""SLOT-COUNT CONSERVATION AUDIT (work order C, yellowthief1 find #3 —
root-caused 2026-07-15): repeated Optimize must never inflate slots, and the
level-50 plan must announce itself on a sub-50 import.

The measured truth behind the report: slot conservation against the level-50
allotment held in every arm (server and UI, stable across repeated presses) —
the real defect was the SILENT level-50 plan on an imported character owning
fewer slots ("more slots than what you have"). This audit pins both: the
conservation invariants AND the honesty warning.

Invariants per arm, per press:
  1. no power exceeds 6 slots
  2. added slots (all powers incl. inherents, beyond each base) <= 67
  3. repeated presses are BYTE-STABLE (press N == press N+1)
  4. the sub-50 preserve-off arm carries the level_plan warning; the
     at-level arms carry none

Run:  py tools\\audit_slot_conservation.py
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

client = srv.app.test_client()
PRESSES = 3
problems = []
checked = 0


def counts(powers):
    per = {}
    added = 0
    for p in powers:
        n = len([s for s in (p.get("slots") or [None])])
        per[p.get("full_name")] = n
        added += max(0, n - 1)
    return per, added


def canon(powers):
    return json.dumps([[p.get("full_name"),
                        [(s or {}).get("piece_uid") for s in (p.get("slots") or [])]]
                       for p in powers], sort_keys=True)


def hammer(label, body_fn, powers, expect_level_warning=False):
    global checked
    checked += 1
    prev = None
    # the real app KEEPS each power's earned_slot_count across solves (the
    # merge-back updates slots only) — the harness must do the same
    earned0 = {p.get("full_name"): p.get("earned_slot_count") for p in powers}
    for press in range(1, PRESSES + 1):
        carry = []
        for p in copy.deepcopy(powers):
            p["earned_slot_count"] = earned0.get(p.get("full_name"))
            carry.append(p)
        body = body_fn(carry)
        r = client.post("/build/solve", json=body).get_json()
        if not (r and r.get("ok")):
            problems.append(f"{label}: press {press} solve failed: "
                            f"{(r or {}).get('response')}")
            return
        powers = r["powers"]
        per, added = counts(powers)
        over = {k: v for k, v in per.items() if v > 6}
        if over:
            problems.append(f"{label}: press {press} power(s) over 6 slots: {over}")
        if added > 67:
            problems.append(f"{label}: press {press} added slots {added} > 67")
        sig = canon(powers)
        if prev is not None and sig != prev:
            problems.append(f"{label}: press {press} CHANGED the build "
                            f"(repeat presses must be stable)")
        prev = sig
        has_warn = any((w or {}).get("kind") == "level_plan"
                       for w in (r.get("warnings") or []))
        if expect_level_warning and not has_warn:
            problems.append(f"{label}: press {press} missing the level-50-plan "
                            f"warning on a sub-50 import")
        if not expect_level_warning and has_warn:
            problems.append(f"{label}: press {press} spurious level-plan warning")
    _, added = counts(powers)
    print(f"  OK {label}: stable across {PRESSES} presses, added={added} <= 67")


# ── arm 1: generated level-50 farmer with custom targets (the reported flow)
ap = client.post("/build/autopick", json={
    "archetype": "Class_Brute", "primary": "Brute_Melee.Spines",
    "secondary": "Brute_Defense.Fiery_Aura", "content": "fire_farm"}).get_json()
hammer("generated 50 + custom targets",
       lambda pw: {"archetype": "Class_Brute", "content": "fire_farm",
                   "powers": [{"full_name": p.get("full_name"),
                               "slots": p.get("slots"),
                               "earned_slot_count": p.get("earned_slot_count")}
                              for p in pw],
                   "tier": "premium", "preserve": False, "keep_layout": False,
                   "custom_targets": {"defense": {"Fire": 45},
                                      "resistance": {"Fire": 90}}},
       ap["powers"])

# ── arm 2: imported level-50 (full earned), preserve ON
r0 = client.post("/build/solve", json={
    "archetype": "Class_Brute", "content": "fire_farm",
    "powers": ap["powers"], "tier": "premium", "preserve": False}).get_json()
full = [{"full_name": p["full_name"], "slots": p.get("slots"),
         "earned_slot_count": len(p.get("slots") or [])}
        for p in r0["powers"]]
hammer("imported 50, preserve on",
       lambda pw: {"archetype": "Class_Brute", "content": "fire_farm",
                   "powers": pw, "tier": "premium", "preserve": True,
                   "keep_layout": False},
       full)

# ── arm 3: imported SUB-50 (fewer earned slots), preserve OFF — the level-50
# plan is legitimate but must ANNOUNCE itself (the actual find)
sub = []
for i, p in enumerate(r0["powers"]):
    keep = min(len(p.get("slots") or []), 3 if i % 3 == 0 else 1)
    sub.append({"full_name": p["full_name"],
                "slots": (p.get("slots") or [])[:keep],
                "earned_slot_count": keep})
hammer("imported sub-50, preserve off (level-plan warning)",
       lambda pw: {"archetype": "Class_Brute", "content": "fire_farm",
                   "powers": pw, "tier": "premium", "preserve": False,
                   "keep_layout": False},
       sub, expect_level_warning=True)

print(f"\n{checked} of 3 expected arms hammered x{PRESSES}")
if checked != 3:
    print("== COVERAGE FAILURE ==")
    sys.exit(1)
if problems:
    print("== PROBLEMS ==")
    for p in problems:
        print("  " + p)
    sys.exit(1)
print("== SLOT CONSERVATION: ALL ARMS PASS ==")
