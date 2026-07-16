"""Stamp every certificate with WHAT IT ACTUALLY CLAIMS (Joel's gate ruling,
2026-07-16 — the IG flip).

The certificates in champions.json say `converged: True, restarts_done: 6,
budget_truncated: False`. Every one of those is TRUE — and together they were
read (by us, publicly) as "this build is the best one". They are not that
claim. They say the SEARCH stopped improving ON ITS OWN OBJECTIVE (the in-run
score, computed over search-constructed candidate dicts). The number we
PUBLISH is the canonical score, from a different chain — and the farm_active
proof case shows the two disagree enough to change the picks:

    farm_active champion   in-run 497.6 / canonical 432.1
    same build, Long_Jump -> Irradiated Ground   canonical 473.0  (+40.9)
    (reproduced fresh-process, twice, identical to the decimal;
     certificate said sweeps 30 / restarts 6 / truncated False / node cap never bound)

So the certificate was honest about the search and SILENT about the
divergence. This annotates the silence away. It changes NO picks, NO scores
and NO model — it is wording, applied to what already shipped.

Root-cause work order (queued behind the cut): one objective, not two — make
the search optimise the number we certify, or certify the number the search
optimises. When that lands, `canonical_optimality_checked` becomes meaningful
and the swap-sweep fills it in.

Run:  py tools\\annotate_certificate_claims.py  [--dry-run]
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, "benchmarks", "champions.json")

CLAIM = ("converged on the SEARCH objective (in-run scoring); canonical_score "
         "is the portable number and is NOT claimed optimal — see the "
         "one-objective work order (2026-07-16 IG flip)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    data = json.load(open(MAIN, encoding="utf-8"))

    stamped = 0
    for k, v in data.items():
        cert = v.get("certificate")
        if not isinstance(cert, dict):
            continue
        if cert.get("claim") == CLAIM and "canonical_optimality_checked" in cert:
            continue
        cert["claim"] = CLAIM
        cert.setdefault("canonical_optimality_checked", False)
        stamped += 1

    print(f"certificates stamped: {stamped} of {len(data)} contexts")
    missing = [k for k, v in data.items()
               if not (v.get("certificate") or {}).get("claim")]
    if missing:
        print(f"HARD FAIL: {len(missing)} context(s) left without a claim: "
              f"{missing[:3]}")
        sys.exit(1)
    print("every context carries an explicit claim ✓ "
          f"(coverage {len(data)} of {len(data)})")

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return
    with open(MAIN, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    print(f"\nwrote {MAIN}")


if __name__ == "__main__":
    main()
