"""Audit EVERY archetype's generated build for slot-schedule feasibility.

The rule: an enhancement slot is granted at a specific level and can only be
placed in a power already picked — so e.g. a level-49 pick holds at most 4 slots.
For each playable AT: autopick -> solve, then check (a) every power is within its
own pick level's slot ceiling, (b) the whole suffix schedule is placeable,
(c) the validator raises nothing.

Run:  python tools/audit_slot_schedule.py
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
import server as srv

c = srv.app.test_client()
problems, runs = [], 0

for at, groups in srv.POWERSETS["by_archetype"].items():
    prim = (groups.get("primary") or [{}])[0].get("full_name")
    sec = (groups.get("secondary") or [{}])[0].get("full_name")
    if not (prim and sec):
        continue
    ap = c.post("/build/autopick", json={"archetype": at, "primary": prim, "secondary": sec,
                                         "content": "general"}).get_json()
    if not (ap or {}).get("powers"):
        problems.append(f"{at}: autopick returned no powers")
        continue
    sol = c.post("/build/solve", json={"archetype": at, "powers": ap["powers"],
                                       "content": "general", "preserve": False}).get_json()
    if not (sol or {}).get("ok"):
        problems.append(f"{at}: solve failed")
        continue
    runs += 1
    real = [p for p in sol["powers"] if not p["full_name"].startswith("Inherent")]
    missing = [p["full_name"] for p in real if not p.get("pick_level")]
    if missing:
        problems.append(f"{at}: no pick_level on {missing[:3]}")
        continue
    over = [f"{p['full_name'].split('.')[-1]}@{p['pick_level']}:{1 + srv._sched_added(p)}sl"
            for p in real if srv._sched_added(p) > srv._grants_from(int(p["pick_level"]))]
    if over:
        problems.append(f"{at}: over per-level ceiling — {', '.join(over)}")
    if not srv._schedule_feasible(real):
        problems.append(f"{at}: suffix schedule infeasible")
    verrs = srv._slot_schedule_errors(sol["powers"])
    if verrs:
        problems.append(f"{at}: validator — {verrs[0][:100]}")
    l1e = srv._l1_pick_errors(sol["powers"], at)
    if l1e:
        problems.append(f"{at}: L1 creation rule — {l1e[0][:100]}")
    if srv.leveling_schedule.eat_type(at) is None:
        l1 = [p for p in real if int(p["pick_level"]) == 1]
        if len(l1) != 2 or not all(
                p["full_name"] in srv._set_first_two(p.get("powerset_full_name") or "") for p in l1):
            problems.append(f"{at}: bad L1 seating — "
                            + ", ".join(p["full_name"].split(".")[-1] for p in l1))
        # creation ORDER (universal rule, all ATs): the walk asks the SECONDARY first
        ls = c.post("/build/leveling-steps",
                    json={"archetype": at, "powers": sol["powers"]}).get_json()
        st1 = next((s for s in (ls or {}).get("steps") or [] if s.get("level") == 1), None)
        picks1 = (st1 or {}).get("picks") or []
        secs = {e["full_name"] for e in (srv.POWERSETS["by_archetype"][at].get("secondary") or [])}
        first_is_sec = bool(picks1) and any(
            p.get("powerset_full_name") in secs and p["full_name"] == picks1[0]["full_name"]
            for p in real)
        if len(picks1) != 2 or not first_is_sec:
            problems.append(f"{at}: walk L1 order — "
                            + " -> ".join(pk.get("powerset", "?") for pk in picks1))
    tail = sorted(real, key=lambda p: -int(p["pick_level"]))[:2]
    print(f"  {at:18s} ok — last picks: " + ", ".join(
        f"{p['full_name'].split('.')[-1]}@{p['pick_level']}({1 + srv._sched_added(p)}sl)" for p in tail))

print(f"\n══ {runs} archetypes solved, {len(problems)} problem(s) ══")
for p in problems:
    print(" ", p)
if not problems:
    print("Every generated build's pick levels can actually receive their slots in game.")
sys.exit(1 if problems else 0)
