"""Route-coverage battery: every server route is either EXERCISED here with a
real-shaped payload or NAMED in EXCLUSIONS with the reason — a new route that
is neither fails the run (coverage-denominator rule, 2026-08-04: built after
two field defects lived in surfaces no battery touched).

This does NOT re-test what dedicated batteries own (solve physics, exemplar,
accolade routing, gamelog, desktop shell) — it proves every OTHER surface
answers its real request shape without a 500.
"""
import io
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

os.environ["APPDATA"] = tempfile.mkdtemp()  # scratch saves/gamelog — never Joel's
import server as srv  # noqa: E402

C = srv.app.test_client()
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    print(f"  {'✓' if ok else '✗ FAIL'} {name}{(' — ' + str(detail)[:90]) if (detail and not ok) else ''}")


def j(resp):
    return resp.get_json(silent=True) or {}


# Routes exercised below (path pattern → covered). EXCLUSIONS are named.
EXCLUSIONS = {
    "/app/shutdown": "kills the process under test",
    "/app/autostart": "writes a real registry Run key",
    "/update/install": "downloads + swaps the installed app",
    "/gamelog/feed": "POST arm records real share consent (GET arm tested)",
    "/gamelog/ingest": "owned by test_gamelog.py",
    "/gamelog/insights": "owned by test_gamelog.py",
    "/gamelog/link": "owned by test_gamelog.py",
    "/gamelog/pulse": "owned by test_gamelog.py",
    "/gamelog/scan": "owned by test_gamelog.py",
    "/gamelog/watch": "owned by test_gamelog.py",
    "/build/solve": "owned by demo_single_build_fixes.py (the 24-check gate)",
    "/build/calculate": "owned by the gate + test_stat_attribution.py",
    "/build/validate": "owned by audit_pool_prereq_validator.py",
    "/build/autopick": "owned by audit_autopick_legality.py (used here as a fixture)",
    "/build/assess": "owned by the gate",
    "/accolades": "owned by test_accolade_routing.py",
    "/ai/generate-build": "AI seam off in client (refusal shape tested via /ai/query)",
    "/ai/generate-solved": "AI seam off in client",
    "/ai/interpret-goal": "AI seam off in client",
    "/ai/refine-build": "AI seam off in client",
    "/static/<path:fname>": "flask static file serving",
}

TESTED = set()


def T(path):
    TESTED.add(path)


# ── fixtures: a REAL build via the same route the app uses ──────────────────
print("fixture: autopick Blaster Fire/Fire …")
r = C.post("/build/autopick", json={"archetype": "Class_Blaster",
                                    "primary": "Blaster_Ranged.Fire_Blast",
                                    "secondary": "Blaster_Support.Fire_Manipulation",
                                    "content": "general", "role": "damage"})
BUILD = {"archetype": "Class_Blaster", "primary": "Blaster_Ranged.Fire_Blast",
         "primary_display": "Fire Blast", "secondary": "Blaster_Support.Fire_Manipulation",
         "secondary_display": "Fire Manipulation", "pools": [], "pools_display": [],
         "powers": j(r).get("powers") or []}
check("fixture autopick returns powers", BUILD["powers"], j(r))

# ── read-only catalogs ──────────────────────────────────────────────────────
T("/"); check("/ serves the app shell", C.get("/").status_code == 200)
T("/health"); check("/health ok", j(C.get("/health")).get("ok"))
T("/archetypes"); ats = j(C.get("/archetypes")).get("archetypes") or []
check("/archetypes lists 15", len(ats) == 15, len(ats))
T("/powersets/<archetype>")
ps = j(C.get("/powersets/Class_Blaster"))
check("/powersets has primary+secondary+pools+epic",
      all(k in ps for k in ("primary", "secondary", "pools", "epic")))
T("/powers/<path:powerset_full_name>")
pw = j(C.get("/powers/Blaster_Ranged.Fire_Blast")).get("powers") or []
check("/powers returns powers with prereq_need", pw and all("prereq_need" in p for p in pw))
T("/meta"); meta = j(C.get("/meta"))
check("/meta carries pool_rules (max 4, epic separate)",
      (meta.get("pool_rules") or {}).get("max") == 4
      and (meta.get("pool_rules") or {}).get("epic_counts") is False)
T("/meta/update-check")
check("/meta/update-check answers", C.get("/meta/update-check").status_code == 200)
T("/incarnates"); check("/incarnates answers", C.get("/incarnates").status_code == 200)
T("/journey/places")
places = j(C.get("/journey/places"))
check("/journey/places has zones", places)
T("/journey/badges")
check("/journey/badges answers", C.get("/journey/badges").status_code == 200)
T("/docs/<page>")
check("/docs/terms serves", C.get("/docs/terms").status_code == 200)
check("/docs traversal refused", C.get("/docs/..%2f..%2fserver").status_code != 200)
T("/sets/<category>")
check("/sets/Defense answers", C.get("/sets/Defense").status_code == 200)
T("/setbonuses/<path:setname>")
check("/setbonuses answers for LotG",
      C.get("/setbonuses/Luck_of_the_Gambler").status_code == 200)
T("/targets/preset")
check("/targets/preset answers", C.get("/targets/preset").status_code == 200)

# ── converter (the planner tool, untested since it shipped) ─────────────────
T("/converter/catalog")
cat = j(C.get("/converter/catalog"))
check("/converter/catalog answers", cat)
T("/converter/from"); T("/converter/to"); T("/converter/plan"); T("/converter/assign")
r = C.post("/converter/plan", json={"want": "Luck of the Gambler: Defense/Increased Global Recharge Speed"})
check("/converter/plan answers a real want", r.status_code == 200, r.status_code)
_uid = next(iter(srv.SET_BY_UID))   # any real set uid — the routes key on set_uid
check("/converter/from answers a real set_uid",
      C.post("/converter/from", json={"set_uid": _uid}).status_code == 200)
check("/converter/to answers a real set_uid",
      C.post("/converter/to", json={"set_uid": _uid}).status_code == 200)
check("/converter/from refuses an unknown set (404, not 500)",
      C.post("/converter/from", json={"set_uid": "no-such-set"}).status_code == 404)
check("/converter/assign answers", C.post("/converter/assign", json={"build": BUILD}).status_code == 200)

# ── export → import round-trip (Mids .mbd) ──────────────────────────────────
T("/build/export"); T("/build/import")
r = C.post("/build/export", json=BUILD)
exp = j(r)
check("/build/export mbd succeeds", r.status_code == 200 and exp.get("mbd"), r.status_code)
r2 = C.post("/build/import", json={"mbd": exp.get("mbd")})
imported = j(r2).get("build") or {}
picked = [p for p in (BUILD.get("powers") or [])
          if not (p.get("full_name") or "").startswith("Inherent.")]
got = len(imported.get("powers") or [])
check("mbd round-trip preserves picked powers", got >= len(picked), f"{got} back of {len(picked)}")

# ── in-game import ──────────────────────────────────────────────────────────
T("/ingame/read"); T("/ingame/scan")
check("/ingame/scan answers", C.get("/ingame/scan").status_code == 200)
r = C.post("/ingame/read", json={"path": "C:\\Windows\\system32\\drivers\\etc\\hosts"})
check("/ingame/read refuses a non-build path outside its root", r.status_code != 200 or not j(r).get("ok"))

# ── build helper routes the UI calls every session ──────────────────────────
T("/build/trays")
check("/build/trays lays out a real build",
      C.post("/build/trays", json={"build": BUILD}).status_code == 200)
T("/build/leveling-steps")
check("/build/leveling-steps answers",
      C.post("/build/leveling-steps", json={"build": BUILD}).status_code == 200)
T("/build/preset")
check("/build/preset answers", C.post("/build/preset", json={"content": "general", "role": "damage",
      "archetype": "Class_Blaster"}).status_code == 200)
T("/build/interpret")
check("/build/interpret answers", C.post("/build/interpret", json={"text": "soft-cap ranged defense"}).status_code == 200)
T("/build/explain_intent")
check("/build/explain_intent answers",
      C.post("/build/explain_intent", json={"build": BUILD, "content": "general", "role": "damage"}).status_code == 200)
T("/enhancement/detail")
check("/enhancement/detail answers", C.post("/enhancement/detail",
      json={"name": "Luck of the Gambler: Defense"}).status_code == 200)
T("/sets/for-power")
check("/sets/for-power answers", C.post("/sets/for-power",
      json={"power": (BUILD.get("powers") or [{}])[0].get("full_name", "")}).status_code == 200)
T("/discover")
check("/discover answers", C.post("/discover", json={"build": BUILD}).status_code == 200)
T("/champion/bundle")
check("/champion/bundle answers", C.post("/champion/bundle",
      json={"archetype": "Class_Blaster", "primary": "Blaster_Ranged.Fire_Blast",
            "secondary": "Blaster_Support.Fire_Manipulation", "content": "general"}).status_code == 200)
T("/build/slot_compare")
r = C.post("/build/slot_compare", json={**BUILD, "power_index": 0, "slot_index": 0,
                                        "candidates": [None], "keys": ["defense.AoE"]})
sc = j(r)
check("/build/slot_compare returns 200 ok with one result",
      r.status_code == 200 and sc.get("ok") is True and len(sc.get("results") or []) == 1, r.status_code)
r = C.post("/build/slot_compare", json={**BUILD, "slot_index": 0,
                                        "candidates": [None], "keys": ["defense.AoE"]})
sc = j(r)
check("/build/slot_compare missing power_index → ok false (not 500)",
      r.status_code == 200 and sc.get("ok") is False, r.status_code)

# ── AI refusal shape (client ships AI-free) ─────────────────────────────────
T("/ai/query")
r = C.post("/ai/query", json={"question": "hi"})
check("/ai/query answers without a 500 when AI is off", r.status_code in (200, 400, 403, 503), r.status_code)

# ── saves: rename keeps id; picks field; respec worksheet; delete ───────────
T("/saves"); T("/saves/<sid>"); T("/saves/<sid>/respec")
r = C.post("/saves", json={"name": "Route Test", "build": BUILD, "plan": {"named": True}})
sid = j(r).get("id")
check("save create ok", sid)
r = C.post("/saves", json={"name": "Route Test Renamed", "id": sid, "build": BUILD, "plan": {"named": True}})
check("rename keeps the id (slug)", j(r).get("id") == sid, j(r).get("id"))
lst = j(C.get("/saves")).get("saves") or []
mine = next((s for s in lst if s["id"] == sid), None)
check("saves list carries picks for the Continue badge", mine and "picks" in mine)
check("save GET returns the renamed name",
      j(C.get(f"/saves/{sid}")).get("save", {}).get("name") == "Route Test Renamed")
check("respec worksheet POST ok", C.post(f"/saves/{sid}/respec", json={"ws": {"step": 1}}).status_code == 200)
check("respec worksheet DELETE ok", C.delete(f"/saves/{sid}/respec").status_code == 200)
check("save DELETE ok", C.delete(f"/saves/{sid}").status_code == 200)
check("deleted save is gone", C.get(f"/saves/{sid}").status_code != 200)

# ── target preset CRUD ──────────────────────────────────────────────────────
T("/target_presets"); T("/target_presets/<name>")
check("target_presets POST ok", C.post("/target_presets",
      json={"name": "rt", "targets": {"def_ranged": 45}}).status_code == 200)
check("target_presets GET lists it", "rt" in (j(C.get("/target_presets")).get("presets") or {}))
check("target_presets DELETE ok", C.delete("/target_presets/rt").status_code == 200)

# ── the private/public board pages (read-only renders) ──────────────────────
T("/gamelog/board"); T("/gamelog/board/public")
check("/gamelog/board renders", C.get("/gamelog/board").status_code == 200)
check("/gamelog/board/public renders", C.get("/gamelog/board/public").status_code == 200)

# ── coverage denominator: every route tested or excluded ────────────────────
src = open(os.path.join(os.path.dirname(__file__), "..", "server", "server.py"),
           encoding="utf-8").read()
routes = set(re.findall(r'@app\.route\("([^"]+)"', src))
missing = sorted(r for r in routes if r not in TESTED and r not in EXCLUSIONS)
check(f"coverage: {len(TESTED)} tested + {len(EXCLUSIONS)} named exclusions "
      f"cover all {len(routes)} routes", not missing, f"UNCOVERED: {missing}")

fails = [c for c in CHECKS if not c[1]]
print(f"\n{len(CHECKS) - len(fails)} of {len(CHECKS)} checks pass "
      f"({len(TESTED)}+{len(EXCLUSIONS)} of {len(routes)} routes covered)")
if fails:
    print("FAILURES:")
    for name, _, detail in fails:
        print(f"  ✗ {name} — {detail}")
    sys.exit(1)
print("== ALL ROUTE CHECKS PASS ==")
