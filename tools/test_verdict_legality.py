"""BATTERY: the recert verdict gate must refuse to trade legality for score.

WHY THIS EXISTS. 0.12.30 shipped 8 of 24 champions that could not be built in
game. The verdict gate had "kept" every one of them because it compared SCORE
ONLY, and the illegal incumbents outscored their legal replacements. Joel's
ruling: legality outranks score.

The branch that actually matters is the counter-intuitive one - a LEGAL
challenger must supersede an ILLEGAL incumbent even when it scores LOWER. A
score-only gate gets that exactly backwards, which is how the defect shipped.

Coverage denominator: all five branches of _legality_verdict plus the real
_illegality callable against a genuinely illegal and a genuinely legal build.
Negative controls throughout - a check that cannot fail proves nothing:
  - the "legal" build must come back CLEAN (else the illegal case is vacuous)
  - two legal builds must return None, i.e. legality abstains and score decides
    (else the gate would be deciding everything and score would be dead)

Run:  py tools\\test_verdict_legality.py
"""
import importlib.util as ilu
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "server"))

spec = ilu.spec_from_file_location(
    "recert_verdicts", os.path.join(ROOT, "tools", "recert_verdicts.py"))
rv = ilu.module_from_spec(spec)
spec.loader.exec_module(rv)
srv = rv.srv

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if detail:
        print(f"        {detail}")


def find_case():
    """A real pool power the game gates behind 2 others, plus its companions.

    Taken from the game's own prerequisite counts rather than hardcoded, so the
    battery keeps testing a REAL rule if the data is re-derived.
    """
    for ps in sorted(srv.POWERS):
        if not ps.startswith("Pool."):
            continue
        for rec in srv.POWERS[ps]:
            fn = rec["full_name"]
            need = srv._prereq_need(fn, ps)
            if need < 2:
                continue
            comps = sorted((r["full_name"] for r in srv.POWERS[ps]
                            if r["full_name"] != fn),
                           key=lambda c: (srv._prereq_need(c, ps),
                                          srv._pool_tiers(ps).get(c, 0)))[:need]
            if len(comps) == need:
                return fn, comps, need
    return None, None, 0


def main():
    print("VERDICT-GATE LEGALITY BATTERY\n")
    fn, comps, need = find_case()
    if not fn:
        print("HARD FAIL: no pool power with need>=2 found — the battery cannot "
              "exercise a real game rule.")
        sys.exit(1)
    illegal = [fn]                 # the gated power, held alone
    legal = [fn] + comps           # the same power with its prerequisites
    print(f"  case: {fn} needs {need} — testing alone (illegal) vs with "
          f"{len(comps)} companions (legal)\n")

    bad_illegal = rv._illegality(illegal)
    bad_legal = rv._illegality(legal)

    check("the real callable FLAGS an unbuildable build",
          bool(bad_illegal),
          f"{len(bad_illegal or [])} violation(s): {(bad_illegal or ['-'])[0][:70]}")
    # NEGATIVE CONTROL: without this, "flags everything" would pass above.
    check("NEGATIVE CONTROL: the legal build comes back clean",
          bad_legal == [],
          f"{len(bad_legal or [])} violations on the legal build (must be 0)")

    v, note = rv._legality_verdict([], ["x"])
    check("challenger illegal, incumbent legal -> KEEP", v == "keep", note)

    v, note = rv._legality_verdict(["x"], [])
    check("THE 0.12.30 CASE: incumbent illegal, challenger legal -> SUPERSEDE",
          v == "supersede", note)

    v, note = rv._legality_verdict(["x"], ["y"])
    check("both illegal -> KEEP, and says the roster ships an unbuildable one",
          v == "keep" and "BOTH" in note, note)

    v, note = rv._legality_verdict(None, [])
    check("legality unmeasurable -> KEEP (fail safe)", v == "keep", note)

    # NEGATIVE CONTROL: legality must ABSTAIN when both are legal, or score
    # would be dead code and every verdict would come from this gate.
    v, note = rv._legality_verdict([], [])
    check("NEGATIVE CONTROL: both legal -> legality abstains, score decides",
          v is None, f"returned {v!r} (must be None)")

    expected = 7
    ran = len(CHECKS)
    failed = [c for c in CHECKS if not c[1]]
    print(f"\n{ran} of {expected} expected checks ran")
    if ran != expected:
        print("HARD FAIL: coverage denominator not met.")
        sys.exit(1)
    if failed:
        print(f"{len(failed)} FAILURE(S) — legality is not outranking score.")
        sys.exit(1)
    print("== ALL CHECKS PASS — legality outranks score ==")


if __name__ == "__main__":
    main()
