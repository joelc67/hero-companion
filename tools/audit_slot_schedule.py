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
        # COMPOSITION, not just membership: one primary + one secondary, each from its
        # set's first two (the earlier membership-only check passed two Poison powers).
        if not srv._l1_seating_ok(real, at):
            l1 = [p for p in real if int(p["pick_level"]) == 1]
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

    # ── tray-order standard (community-researched): bands must be monotonic ──
    tr = c.post("/build/trays", json={"archetype": at, "powers": sol["powers"],
                                      "incarnates": {}, "role": None}).get_json()
    if not (tr or {}).get("ok"):
        problems.append(f"{at}: trays failed")
    else:
        by_group = {}
        for t in tr["trays"]:
            by_group.setdefault(t.get("group") or t["n"], []).extend(
                s for s in t["slots"] if not s.get("macro"))
        for g, slots in by_group.items():
            bands = [s.get("_o", 0) for s in slots]
            if bands != sorted(bands):
                problems.append(f"{at}: tray {g} band order broken — {bands}")
        # within tray 1's same band: single-target before AoE
        for s1, s2 in zip(by_group.get(1, []), by_group.get(1, [])[1:]):
            if (s1.get("_o") == s2.get("_o")
                    and (s1.get("_aoe") or 0) > (s2.get("_aoe") or 0)):
                problems.append(f"{at}: tray 1 AoE '{s1['short']}' before ST '{s2['short']}'")
                break

# ── Pinned field case: the exact combo from the report, WITHOUT champions ────
# The standalone app ships no champions.json, so end users always get the
# heuristic picker — audit that path explicitly (champions masked this once).
print("\n── pinned: Defender Poison/Sonic debuffer (heuristic path, no champion) ──")
_orig_champ = srv._champion_picks
srv._champion_picks = lambda *a, **k: None
try:
    ap = c.post("/build/autopick", json={"archetype": "Class_Defender",
                                         "primary": "Defender_Buff.Poison",
                                         "secondary": "Defender_Ranged.Sonic_Attack",
                                         "role": "debuffer", "content": "itrial",
                                         "travel": "fly"}).get_json()
    sol = c.post("/build/solve", json={"archetype": "Class_Defender", "powers": ap["powers"],
                                       "role": "debuffer", "content": "itrial",
                                       "preserve": False}).get_json()
    _real = [p for p in sol["powers"] if not p["full_name"].startswith("Inherent")]
    _l1 = sorted(p["full_name"].split(".")[-1] for p in _real if int(p["pick_level"]) == 1)
    print("  heuristic L1:", ", ".join(_l1))
    if not srv._l1_seating_ok(_real, "Class_Defender"):
        problems.append(f"pinned heuristic case: bad L1 — {_l1}")
    if srv._l1_pick_errors(sol["powers"], "Class_Defender"):
        problems.append("pinned heuristic case: validator flags the generated build")
finally:
    srv._champion_picks = _orig_champ

print(f"\n══ {runs} archetypes solved, {len(problems)} problem(s) ══")
for p in problems:
    print(" ", p)
if not problems:
    print("Every generated build's pick levels can actually receive their slots in game.")
sys.exit(1 if problems else 0)
