"""Audit EVERY epic/patron pool on every archetype for tier-prerequisite correctness.

Three passes:
 1. DATA SANITY — does each set's tier order (data order, what _pool_tiers uses)
    agree with its level_available ladder? A mismatch would enforce the wrong rule.
 2. VALIDATOR BOUNDARIES — for every set: its top-tier power with too few
    prerequisites must be flagged, and with enough must pass. Both directions.
 3. AUTOPICK SWEEP — every playable AT x content: generated epic picks must satisfy
    their own ladder.

Run:  python tools/audit_epic_tiers.py
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
import server as srv

c = srv.app.test_client()
problems = []

# ── collect every epic set per archetype ─────────────────────────────────────
at_epics = {}
for at, groups in srv.POWERSETS["by_archetype"].items():
    eps = [e["full_name"] for e in (groups.get("epic") or [])]
    if eps:
        at_epics[at] = eps
n_sets = sum(len(v) for v in at_epics.values())
print(f"{len(at_epics)} archetypes, {n_sets} epic/patron pools\n")

# ── pass 1: data sanity ──────────────────────────────────────────────────────
print("── pass 1: tier order vs level ladder ──")
bad_order = 0
for at, eps in at_epics.items():
    for ps in eps:
        allp = srv.POWERS.get(ps) or []
        tiers = srv._pool_tiers(ps)
        seq = sorted(allp, key=lambda p: tiers.get(p["full_name"], 0))
        lvls = [p.get("level_available") or 35 for p in seq]
        if lvls != sorted(lvls):
            bad_order += 1
            problems.append(f"ORDER MISMATCH {at} {ps}: tier order {lvls}")
print(f"  sets with tier/level disagreement: {bad_order}")

# ── pass 2: validator boundaries on every set ────────────────────────────────
print("\n── pass 2: validator boundaries (every set) ──")


def _boundary_eligible(ps):
    """A set is boundary-testable when its top tier requires 2 prerequisites."""
    allp = srv.POWERS.get(ps) or []
    if len(allp) < 3:
        return False
    tiers = srv._pool_tiers(ps)
    top = max(allp, key=lambda p: tiers.get(p["full_name"], 0))
    return srv._epic_prereq_count(tiers.get(top["full_name"], 0)) >= 2


# COVERAGE DENOMINATOR (standing rule 2026-07-08): count the testable sets FIRST,
# independent of the test loop, so a loop that silently skips can't pass.
expected_boundary = sum(1 for eps in at_epics.values() for ps in eps
                        if _boundary_eligible(ps))
checked = fails = 0
for at, eps in at_epics.items():
    for ps in eps:
        allp = srv.POWERS.get(ps) or []
        if len(allp) < 3:
            continue
        tiers = srv._pool_tiers(ps)
        top = max(allp, key=lambda p: tiers.get(p["full_name"], 0))
        t = tiers.get(top["full_name"], 0)
        need = srv._epic_prereq_count(t)
        if need < 2:
            continue                      # no 2-prereq tier in this set (tiny set)
        lows = [p for p in allp if p["full_name"] != top["full_name"]]
        checked += 1
        # under-prereq'd: top + (need-1) others -> MUST error
        under = [{"full_name": top["full_name"]}] + [{"full_name": p["full_name"]} for p in lows[:need - 1]]
        r = c.post("/build/validate", json={"archetype": at, "powers": under}).get_json()
        flagged = any(top["display_name"] in e for e in (r.get("errors") or []))
        # satisfied: top + need others -> must NOT error
        okp = [{"full_name": top["full_name"]}] + [{"full_name": p["full_name"]} for p in lows[:need]]
        r2 = c.post("/build/validate", json={"archetype": at, "powers": okp}).get_json()
        over = any(top["display_name"] in e for e in (r2.get("errors") or []))
        if not flagged or over:
            fails += 1
            problems.append(f"BOUNDARY {at} {ps.split('.')[-1]}: under-flagged={flagged} over-flagged={over}")
print(f"  sets boundary-tested: {checked} of {expected_boundary} expected, failures: {fails}")
if checked < expected_boundary:
    problems.append(f"COVERAGE pass 2: {checked} of {expected_boundary} boundary-testable sets checked")

# ── pass 3: autopick sweep ───────────────────────────────────────────────────
print("\n── pass 3: autopick sweep (every AT x 3 contents) ──")
eligible_ats = [at for at, g in srv.POWERSETS["by_archetype"].items()
                if (g.get("primary") or [{}])[0].get("full_name")
                and (g.get("secondary") or [{}])[0].get("full_name")]
expected_runs = len(eligible_ats) * 3
runs = vio = 0
for at, groups in srv.POWERSETS["by_archetype"].items():
    prim = (groups.get("primary") or [{}])[0].get("full_name")
    sec = (groups.get("secondary") or [{}])[0].get("full_name")
    if not (prim and sec):
        continue
    for content in ("general", "fire_farm", "av"):
        ap = c.post("/build/autopick", json={"archetype": at, "primary": prim, "secondary": sec,
                                             "role": "damage", "content": content}).get_json()
        if not ap.get("powers"):
            problems.append(f"COVERAGE pass 3: autopick returned no powers for {at}/{content}")
            continue
        runs += 1
        epics = [p["full_name"] for p in ap["powers"]
                 if (p.get("powerset_full_name") or "").startswith("Epic.")]
        if not epics:
            continue
        ps = epics[0].rsplit(".", 1)[0]
        tr = srv._pool_tiers(ps)
        for fn in epics:
            need = srv._epic_prereq_count(tr.get(fn, 0))
            if len(epics) - 1 < need:
                vio += 1
                problems.append(f"AUTOPICK {at}/{content}: {fn} needs {need}, has {len(epics)-1}")
print(f"  autopick runs: {runs} of {expected_runs} expected, ladder violations: {vio}")
if runs < expected_runs:
    problems.append(f"COVERAGE pass 3: {runs} of {expected_runs} expected autopick runs")

print(f"\n══ RESULT: {len(problems)} problem(s) ══")
for p in problems[:25]:
    print(" ", p)
if not problems:
    print("Every epic/patron pool on every archetype enforces its tier ladder correctly.")
sys.exit(1 if problems else 0)
