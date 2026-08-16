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

# ── 3b. level-1 creation rule (field report #2: "only Shriek and Scream") ────
print("\n── level-1 creation composition ──")
l1 = [p for p in real if int(p["pick_level"]) == 1]
l1_sets = sorted((p.get("powerset_full_name") or "").split(".")[-1] for p in l1)
check("exactly two L1 picks", len(l1) == 2, ", ".join(l1_sets))
check("one primary + one secondary at L1",
      l1_sets == ["Poison", "Sonic_Attack"], ", ".join(l1_sets))
ok_f2 = all(p["full_name"] in srv._set_first_two(p["powerset_full_name"]) for p in l1)
check("both L1 picks are their set's first two", ok_f2,
      ", ".join(p["full_name"].split(".")[-1] for p in l1))
# validator: a build with neither of the secondary's first two must be flagged
f2 = srv._set_first_two("Defender_Ranged.Sonic_Attack")
stripped = [p for p in sol["powers"] if p["full_name"] not in f2]
verrs = srv._l1_pick_errors(stripped, "Class_Defender")
check("validator flags a missing creation pick", len(verrs) == 1 and "creation" in verrs[0],
      (verrs or ["?"])[0][:80])
check("validator quiet on the legal build", not srv._l1_pick_errors(sol["powers"], "Class_Defender"))

# ── 4. leveling walk agrees ──────────────────────────────────────────────────
print("\n── leveling walk on the solved build ──")
ls = c.post("/build/leveling-steps", json={"archetype": "Defender",
                                           "powers": sol["powers"]}).get_json()
check("walk ok", ls.get("ok"))
picks49 = [pk for st in ls["steps"] if st.get("level") == 49 for pk in (st.get("picks") or [])]
names49 = {pk.get("full_name") for pk in picks49}
heavy49 = [p for p in real if p["full_name"] in names49 and srv._sched_added(p) > 3]
check("no heavy power picked at 49 in the walk", not heavy49)
st1 = next((st for st in ls["steps"] if st.get("level") == 1), None)
check("walk L1 has two picks", st1 and len(st1.get("picks") or []) == 2)
l1names = [pk["powerset"] for pk in (st1.get("picks") or [])]
check("walk L1 asks the SECONDARY first (in-game creation order)",
      l1names == ["Sonic_Attack", "Poison"], " -> ".join(l1names))
creation_tips = [t for t in (st1.get("tips") or []) if "creation" in t.lower()]
check("walk L1 explains the creation choices", len(creation_tips) == 2,
      creation_tips[0][:80] if creation_tips else "none")

# ── 5. stuck save heals: both Poison powers stored at level 1 ─────────────────
print("\n── old-save healing (Alkaloid AND Envenom stored at L1) ──")
stuck = []
for p in sol["powers"]:
    q = dict(p)
    if q["full_name"].endswith((".Alkaloid", ".Envenom")):
        q["pick_level"] = 1
    stuck.append(q)
calc = c.post("/build/calculate", json={"archetype": "Class_Defender",
                                        "powers": stuck}).get_json()
pl = calc.get("pick_levels") or {}
check("calculate returns corrected pick levels", bool(pl))
alk = pl.get("Defender_Buff.Poison.Alkaloid")
env = pl.get("Defender_Buff.Poison.Envenom")
shr = pl.get("Defender_Ranged.Sonic_Attack.Shriek")
check("only ONE Poison power at level 1", (alk == 1) != (env == 1), f"Alkaloid@{alk}, Envenom@{env}")
check("a Sonic power shares level 1", shr == 1 or pl.get("Defender_Ranged.Sonic_Attack.Scream") == 1,
      f"Shriek@{shr}")

# ── 6. field case 2026-08-15: the APP'S payload shape (full_name + pick_level
# ONLY — buildPayload() sends no powerset_full_name / level_available). The heal
# used to no-op its creation-pair logic on that shape and stamp BOTH primary T1s
# onto level 1 (Ice/Ice Brute bug report). Test through the real payload shape,
# never an enriched one — check 5 above passed for a year while the field failed,
# because its dicts carried the solve's powerset_full_name.
print("\n── payload-shape heal (no powerset_full_name in the dicts) ──")
_brute = [("Brute_Melee.Ice_Melee.Frozen_Fists", 1),
          ("Brute_Melee.Ice_Melee.Ice_Sword", 1),          # illegal: 2nd primary @1
          ("Brute_Melee.Ice_Melee.Frost", 2),
          ("Brute_Defense.Ice_Armor.Chilling_Embrace", 8),
          ("Brute_Defense.Ice_Armor.Ice_Armor", 49)]       # secondary T1 dead last
bare = [{"full_name": fn, "pick_level": lv, "slots": [None]} for fn, lv in _brute]
check("_l1_seating_ok refuses two same-set L1s on the bare shape",
      not srv._l1_seating_ok([dict(p) for p in bare], "Class_Brute"))
calc = c.post("/build/calculate", json={"archetype": "Class_Brute",
                                        "primary": "Brute_Melee.Ice_Melee",
                                        "secondary": "Brute_Defense.Ice_Armor",
                                        "powers": bare}).get_json()
pl = calc.get("pick_levels") or {}
l1 = sorted(k for k, v in pl.items() if v == 1)
check("bare-shape heal returns exactly two L1 picks", len(l1) == 2, ", ".join(l1))
check("bare-shape heal seats one PRIMARY + one SECONDARY at L1",
      {k.rsplit(".", 1)[0] for k in l1} ==
      {"Brute_Melee.Ice_Melee", "Brute_Defense.Ice_Armor"}, ", ".join(l1))

# ── 7. never-pick self-heal (field report 2026-08-16): a saved build holding an
# auto-granted set mechanic as a pick gets it NAMED for client-side removal.
print("\n── never-pick self-heal ──")
stancey = [{"full_name": "Tanker_Defense.Bio_Organic_Armor.Hardened_Carapace", "pick_level": 1, "slots": [None]},
           {"full_name": "Tanker_Melee.Radiation_Melee.Contaminated_Strike", "pick_level": 1, "slots": [None]},
           {"full_name": "Tanker_Defense.Bio_Organic_Armor.Defensive_Adaptation", "pick_level": 4, "slots": [None]}]
calc = c.post("/build/calculate", json={"archetype": "Class_Tanker",
                                        "primary": "Tanker_Defense.Bio_Organic_Armor",
                                        "secondary": "Tanker_Melee.Radiation_Melee",
                                        "powers": stancey}).get_json()
nv = calc.get("never_picks") or []
check("calculate names the stance for removal",
      nv == ["Tanker_Defense.Bio_Organic_Armor.Defensive_Adaptation"], str(nv))
clean = c.post("/build/calculate", json={"archetype": "Class_Tanker",
                                         "primary": "Tanker_Defense.Bio_Organic_Armor",
                                         "secondary": "Tanker_Melee.Radiation_Melee",
                                         "powers": stancey[:2]}).get_json()
check("NEGATIVE CONTROL: a clean build carries no never_picks",
      not clean.get("never_picks"))
# The swap half: dropping stances also hands back the set's real unlock pick.
tf = calc.get("take_free") or []
check("the heal offers the set's unlock pick in the stances' place",
      any(t["full_name"].endswith(".Evolution") for t in tf), str([t["full_name"] for t in tf]))
check("NEGATIVE CONTROL: no take_free without never_picks", not clean.get("take_free"))

# ── 8. set-unlock picks are STRUCTURAL in autopick (field report 2026-08-16:
# a generated Bio build carried no Adaptation) ─────────────────────────────
print("\n── autopick takes the set unlock ──")
ap = c.post("/build/autopick", json={"archetype": "Class_Tanker",
                                     "primary": "Tanker_Defense.Bio_Organic_Armor",
                                     "secondary": "Tanker_Melee.Radiation_Melee",
                                     "content": "itrial"}).get_json()
apn = [p["full_name"] for p in (ap.get("powers") or [])]
check("generated Bio build takes the Adaptation unlock",
      any(n.endswith(".Evolution") for n in apn))
ap2 = c.post("/build/autopick", json={"archetype": "Class_Scrapper",
                                      "primary": "Scrapper_Melee.Staff_Fighting",
                                      "secondary": "Scrapper_Defense.Super_Reflexes",
                                      "content": "itrial"}).get_json()
ap2n = [p["full_name"] for p in (ap2.get("powers") or [])]
check("generated Staff build takes Staff Mastery (same class, not a Bio hack)",
      any(n.endswith(".Staff_Mastery") for n in ap2n))
# coaching advises an already-healed build that lacks the unlock
val3 = c.post("/build/validate", json={"archetype": "Class_Tanker",
    "primary": "Tanker_Defense.Bio_Organic_Armor",
    "secondary": "Tanker_Melee.Radiation_Melee",
    "powers": stancey[:2]}).get_json()
check("coaching advises taking the missing unlock (advise, never override)",
      any("Adaptation" in n and "isn't taken" in n for n in (val3.get("coaching") or [])),
      str((val3.get("coaching") or [])[:1]))

print(f"\n══ {'ALL PASS' if not fails else f'{len(fails)} FAILURE(S): ' + ', '.join(fails)} ══")
sys.exit(1 if fails else 0)
