"""PREREQ REALITY CHECK — the game's OWN RULE vs what the app enforces.

STANDARD RE-BASED 2026-07-30 (engine-accuracy work order §1.4). The original
check compared our model to the help PROSE and treated "this power has no
prerequisite sentence" as "it needs 0". That was an inference, not a game
statement — 219 of 488 client pool/epic powers carry no sentence at all, and
for every one of them the prose check was silently guessing (wrong for at
least Jaunt, Translocation, and Blaster Black Hole).

The standard is now the client's `requires` EXPRESSION — the boolean rule the
game actually executes — evaluated for its minimum satisfying count by
tools/prereq_from_requires.py (validated against 7 controls whose player-facing
text states the count). Prose is CORROBORATION only: conflicts are reported,
never enforced. An empty expression IS the game's statement (no gate).

FULL ACCOUNTING (Joel's ruling 2026-07-30: "knowing all, not just most"):
the denominator is every Pool./Epic. power in data/powers.json. Each must be
either (a) resolved to a client record — exact name, set bridge, or unique
display-name identity (tools/patch_prereq_counts.resolve, namespace-honest) —
and compared, or (b) named with a reason in
tools/prereq_unmatched_dispositions.json. Anything else is a hard failure.

GATE MODE: converge_parallel runs `--gate` before spawning a worker; it fails
only on disagreements NEW since tools/prereq_disagreement_baseline.json.
`--write-baseline` regenerates the baseline deliberately.

Run:  py tools\\reality_check_prereqs.py [--verbose] [--gate [--write-baseline]]
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import server as srv  # noqa: E402 — what the APP enforces
import patch_prereq_counts as ppc  # noqa: E402 — the shared client resolver
import prereq_from_requires as pfr  # noqa: E402 — the expression evaluator

VERBOSE = "--verbose" in sys.argv
GATE = "--gate" in sys.argv
BASELINE = os.environ.get("HC_PREREQ_BASELINE") or os.path.join(
    ROOT, "tools", "prereq_disagreement_baseline.json")
DISPOSITIONS = os.path.join(ROOT, "tools", "prereq_unmatched_dispositions.json")


def main():
    idx, by_set = ppc.client_index()
    bridge = ppc.set_bridge()
    disp = (json.load(open(DISPOSITIONS, encoding="utf-8"))
            if os.path.exists(DISPOSITIONS) else {})
    data = json.load(open(os.path.join(ROOT, "data", "powers.json"),
                          encoding="utf-8"))

    expected = compared = agree = 0
    mismatches, inexact, unaccounted, dispositioned = [], [], [], []
    prose_conflicts = []
    for ps, lst in sorted(data.items()):
        if not ps.startswith(("Pool.", "Epic.")):
            continue
        for p in lst:
            fn = p["full_name"]
            expected += 1
            rec = ppc.resolve(fn, p.get("display_name"), idx, by_set, bridge)
            if rec is None:
                (dispositioned if fn in disp else unaccounted).append(fn)
                continue
            cfn = rec["full_name"]
            expr = (rec.get("requires") or "").strip()
            siblings = [r["full_name"] for r in by_set[cfn.rsplit(".", 1)[0]]
                        if r["full_name"] != cfn]
            if expr:
                game, status = pfr.min_others(expr, siblings)
                if status != "exact":
                    inexact.append((fn, status, expr))
                    continue
            else:
                game = 0                      # empty expression = the game gates nothing
            compared += 1
            ours = srv._prereq_need(fn, ps)
            if ours == game:
                agree += 1
                if VERBOSE:
                    print(f"  ok   {fn}: both say {ours}")
            else:
                mismatches.append((fn, ours, game, expr))
            # prose corroboration only — both sides CLIENT namespace
            hc = pfr.help_count(pfr.help_sentence(rec))
            if hc is not None and hc != game:
                prose_conflicts.append((fn, cfn, game, hc))

    print("\nPREREQ REALITY CHECK — the game's requires expression vs what "
          "the app enforces")
    print(f"  {expected} Pool/Epic powers in our data (the denominator)")
    print(f"  {compared} compared against the game's own rule, {agree} agree")
    print(f"  {len(inexact)} expression(s) not reducible to an exact count")
    print(f"  {len(dispositioned)} unmatched WITH a named disposition")
    print(f"  {len(unaccounted)} unmatched with NO disposition (hard failure)")
    for fn, ours, game, expr in mismatches:
        print(f"\n  MISMATCH {fn}\n    app enforces {ours}, the game's "
              f"expression needs {game}: {expr[:140]}")
    for fn, status, expr in inexact:
        print(f"\n  {status.upper()} {fn}: {expr[:140]}")
    for fn in unaccounted:
        print(f"\n  UNACCOUNTED {fn}: no client record and no disposition — "
              "add one to tools/prereq_unmatched_dispositions.json or fix the data")
    if prose_conflicts:
        print(f"\n  prose corroboration: {len(prose_conflicts)} sentence(s) "
              "state a different count than the expression (client prose vs "
              "client expression — the expression is what the game executes):")
        for fn, cfn, game, hc in prose_conflicts:
            print(f"    {fn} (client {cfn}): expression {game}, sentence {hc}")

    if unaccounted:
        print(f"\nHARD FAIL: {len(unaccounted)} power(s) neither verified nor "
              "dispositioned — full accounting is the rule.")
        sys.exit(1)

    seen = sorted([f"{fn}|{ours}|{game}" for fn, ours, game, _ in mismatches]
                  + [f"{fn}|{status}" for fn, status, _ in inexact])
    if GATE:
        base = (json.load(open(BASELINE, encoding="utf-8"))
                if os.path.exists(BASELINE) else [])
        if "--write-baseline" in sys.argv:
            with open(BASELINE, "w", encoding="utf-8") as f:
                json.dump(seen, f, indent=1)
            print(f"\nbaseline written: {len(seen)} accepted disagreement(s)")
            sys.exit(0)
        for s in [s for s in base if s not in seen]:
            print(f"  baseline entry now AGREES (stale, harmless): {s}")
        new = [s for s in seen if s not in base]
        if new:
            print("\nPREREQ GATE FAILED — disagreement(s) NEW since the baseline:")
            for s in new:
                print(f"   {s}")
            print("harden-before-certify: settle these against the game's own "
                  "rule (or re-baseline deliberately) before any wave starts.")
            sys.exit(1)
        print(f"\nPREREQ GATE OK — {agree} of {compared} agree; {len(seen)} "
              f"known disagreement(s), none new; {len(dispositioned)} "
              "dispositioned. Safe to certify.")
        sys.exit(0)

    bad = bool(mismatches or inexact)
    print("\n" + ("REALITY CHECK FAILED — the game disagrees with our model above"
                  if bad else
                  f"ALL {compared} COMPARED POWERS AGREE with the game's own "
                  f"rule ({len(dispositioned)} dispositioned by name)"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
