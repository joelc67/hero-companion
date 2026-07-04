"""Slot-schedule feasibility: a power picked at level L can only hold slots the
game still grants at levels >= L (a 49 pick maxes at 4 slots). Tests the new
_assign_pick_levels / _schedule_feasible / _slot_schedule_errors trio, then the
field case: Defender Poison/Sonic + Ice Mastery, autopick -> solve.

Run:  python tools/test_slot_schedule.py
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
import server as srv

fails = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        fails.append(name)


# ── 1. validator: 5 slots on a level-49 pick must be flagged ─────────────────
print("── validator: impossible late slotting ──")
bad = [{"full_name": "Epic.Ice_Mastery_DefCorr.Ice_Elemental", "pick_level": 49,
        "display_name": "Ice Elemental", "slots": [None] * 5}]
errs = srv._slot_schedule_errors(bad)
check("5-slot @49 flagged", len(errs) == 1 and "at most 4" in errs[0], errs[0][:90] if errs else "no error")
ok4 = [{"full_name": "Epic.Ice_Mastery_DefCorr.Ice_Elemental", "pick_level": 49,
        "display_name": "Ice Elemental", "slots": [None] * 4}]
check("4-slot @49 passes", not srv._slot_schedule_errors(ok4))

# suffix rule: 47+49 picks together only get 6 added slots (48 + 50 grants)
pair = [{"full_name": "A.B.C1", "pick_level": 47, "display_name": "P47", "slots": [None] * 5},
        {"full_name": "A.B.C2", "pick_level": 49, "display_name": "P49", "slots": [None] * 4}]
errs = srv._slot_schedule_errors(pair)   # 4+3 added = 7 > 6
check("47+49 overweight tail flagged", len(errs) >= 1, (errs or ["?"])[0][:90])

# ── 2. assignment repairs a heavy late power ─────────────────────────────────
print("\n── assignment: heavy power re-seated earlier ──")
POW = srv.POWERS.get("Epic.Ice_Mastery_DefCorr") or []
ice = next(p for p in POW if p["full_name"].endswith("Ice_Elemental"))
lows = [p for p in POW if p != ice][:2]
mock = ([{"full_name": ice["full_name"], "level_available": ice.get("level_available"),
          "slots": [None] * 6}]                                       # 6-slotted pet
        + [{"full_name": q["full_name"], "level_available": q.get("level_available"),
            "slots": [None]} for q in lows]                           # its 2 prereqs
        + [{"full_name": f"Primary.Fake.P{i}", "level_available": 1,
            "slots": [None] * n} for i, n in enumerate([6, 6, 6, 5, 5, 5, 4, 4, 3, 3,
                                                        2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1])])
feas = srv._assign_pick_levels(mock)
by = {p["full_name"]: p["pick_level"] for p in mock}
ice_lv = by[ice["full_name"]]
check("assignment feasible", feas)
check("schedule check agrees", srv._schedule_feasible(mock))
check("6-slot pet no longer at 49", ice_lv <= 47, f"picked at {ice_lv}")
check("pet within its level's ceiling", 5 <= srv._grants_from(ice_lv), f"@{ice_lv}")
check("prereqs before the pet", all(by[q["full_name"]] < ice_lv for q in lows),
      ", ".join(f"{q['full_name'].split('.')[-1]}@{by[q['full_name']]}" for q in lows))
check("validator clean on the repaired mock", not srv._slot_schedule_errors(mock))

# ── 3. the field case: autopick -> solve, then audit every power ─────────────
print("\n── field case: Defender Poison/Sonic + solve ──")
c = srv.app.test_client()
ap = c.post("/build/autopick", json={"archetype": "Defender", "primary": "Defender_Buff.Poison",
                                     "secondary": "Defender_Ranged.Sonic_Attack",
                                     "role": "debuffer", "content": "general"}).get_json()
sol = c.post("/build/solve", json={"archetype": "Defender", "powers": ap["powers"],
                                   "role": "debuffer", "content": "general",
                                   "preserve": False}).get_json()
check("solve ok", sol.get("ok"))
real = [p for p in sol["powers"] if not p["full_name"].startswith("Inherent")]
check("every real power has pick_level", all(p.get("pick_level") for p in real))
per_power_bad = [p for p in real
                 if srv._sched_added(p) > srv._grants_from(int(p["pick_level"]))]
check("no power over its level's slot ceiling", not per_power_bad,
      ", ".join(f"{p['full_name'].split('.')[-1]}@{p['pick_level']}:{1+srv._sched_added(p)}sl"
                for p in per_power_bad))
check("whole schedule feasible", srv._schedule_feasible(real))
check("validator clean on the solved build",
      not srv._slot_schedule_errors(sol["powers"]))
late = sorted(real, key=lambda p: -int(p["pick_level"]))[:4]
print("  late picks: " + ", ".join(
    f"{p['full_name'].split('.')[-1]}@{p['pick_level']} ({1 + srv._sched_added(p)} slots)" for p in late))

# ── 4. leveling walk agrees ──────────────────────────────────────────────────
print("\n── leveling walk on the solved build ──")
ls = c.post("/build/leveling-steps", json={"archetype": "Defender",
                                           "powers": sol["powers"]}).get_json()
check("walk ok", ls.get("ok"))
picks49 = [pk for st in ls["steps"] if st.get("level") == 49 for pk in (st.get("picks") or [])]
names49 = {pk.get("full_name") for pk in picks49}
heavy49 = [p for p in real if p["full_name"] in names49 and srv._sched_added(p) > 3]
check("no heavy power picked at 49 in the walk", not heavy49)

print(f"\n══ {'ALL PASS' if not fails else f'{len(fails)} FAILURE(S): ' + ', '.join(fails)} ══")
sys.exit(1 if fails else 0)
