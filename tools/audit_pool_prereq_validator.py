"""AUDIT: the user-facing validator must flag EVERY pool/epic prereq violation.

WHY THIS EXISTS (2026-07-30, engine-accuracy work order §1.2). The validator's
prereq check filtered on `powerset_full_name.startswith("Epic.")`, so `Pool.`
sets were never examined: a user taking Vengeance with one Leadership power got
no warning, while `_picks_legal` refused the identical roster in search. Same
bug shape as Crab Spider — the knowledge existed in one place and the enforcing
path didn't consult it. The fix widens `_epic_prereq_errors` to Pool.+Epic.;
this audit proves it for EVERY pool and epic set (all archetypes' epic variants
included), through the REAL /build/validate route.

Coverage denominator: every Pool.*/Epic.* power whose `_prereq_need` > 0 gets
BOTH arms — a violation build (the power alone) that MUST be flagged, and a
legal build (the power + enough need-0 same-set companions) that MUST NOT flag
it. Hard-fails if any case is missed or wrong.

Negative control: if zero Pool.* violations are detected, this audit is not
exercising the defect it exists for — hard fail (that is exactly what the
pre-fix code would produce).

Run:  py tools\\audit_pool_prereq_validator.py [--champions]
      --champions additionally REPORTS (never gates) which shipping champions
      the fixed validator now flags — the §1.1 list, re-derived, not trusted.
"""
import importlib.util as ilu
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = ilu.spec_from_file_location("cohserver", os.path.join(ROOT, "server", "server.py"))
srv = ilu.module_from_spec(spec)
spec.loader.exec_module(srv)

FLAG = "can't be taken yet"          # the prereq message's fixed phrase


def prereq_errors_for(client, fns):
    r = client.post("/build/validate", json={
        "archetype": "Class_Scrapper",
        "powers": [{"full_name": fn} for fn in fns]}).get_json() or {}
    return [e for e in (r.get("errors") or []) if FLAG in e]


def main():
    client = srv.app.test_client()
    cases = []                        # (full_name, ps, need, display_name)
    for ps in sorted(srv.POWERS):
        if not ps.startswith(("Pool.", "Epic.")):
            continue
        for rec in srv.POWERS[ps]:
            need = srv._prereq_need(rec["full_name"], ps)
            if need > 0:
                cases.append((rec["full_name"], ps, need,
                              rec.get("display_name") or rec["full_name"]))
    expected = len(cases)
    checked = 0
    fails = []
    pool_flags = 0
    for fn, ps, need, disp in cases:
        # violation arm: the power alone must be flagged
        errs = prereq_errors_for(client, [fn])
        checked += 1
        if not any(disp in e for e in errs):
            fails.append((fn, f"violation NOT flagged (needs {need}, held alone)"))
        elif ps.startswith("Pool."):
            pool_flags += 1
        # legal arm: power + `need` need-0 companions must not flag it
        comps = sorted((r["full_name"] for r in srv.POWERS[ps]
                        if r["full_name"] != fn),
                       key=lambda c: (srv._prereq_need(c, ps),
                                      srv._pool_tiers(ps).get(c, 0)))[:need]
        if len(comps) < need:
            fails.append((fn, f"set too small for a legal build (need {need})"))
            continue
        errs = prereq_errors_for(client, [fn] + comps)
        if any(disp in e for e in errs):
            fails.append((fn, f"LEGAL build flagged (power + {need} companions)"))

    print(f"\nPOOL/EPIC PREREQ VALIDATOR AUDIT — {checked} of {expected} "
          f"expected violation cases checked (both arms each)")
    if checked < expected:
        print("HARD FAIL: coverage denominator not met.")
        sys.exit(1)
    if pool_flags == 0:
        print("NEGATIVE CONTROL FAILED: zero Pool.* violations detected — this "
              "is the pre-fix behavior; the audit cannot see the defect it "
              "exists for.")
        sys.exit(1)
    print(f"negative control PASSES: {pool_flags} Pool.* violations detected "
          "(the pre-fix validator detected 0)")
    if fails:
        print(f"\n{len(fails)} FAILURE(S):")
        for fn, why in fails:
            print(f"  {fn:60} {why}")
        sys.exit(1)
    print(f"ALL {checked} cases correct — every violation flagged, every "
          "legal build clean.")

    if "--champions" in sys.argv:
        path = os.path.join(ROOT, "benchmarks", "champions.json")
        champs = json.load(open(path, encoding="utf-8"))
        print("\nREPORT ONLY — shipping champions the fixed validator flags:")
        n = 0
        for key, ch in sorted(champs.items()):
            errs = srv._epic_prereq_errors(
                [{"full_name": fn} for fn in ch.get("picks") or []])
            if errs:
                n += 1
                print(f"  {key}")
                for e in errs:
                    print(f"    - {e}")
        print(f"  {n} of {len(champs)} champions flagged (quarantined per the "
              "engine-accuracy work order; re-run at recert, no gating here).")


if __name__ == "__main__":
    main()
