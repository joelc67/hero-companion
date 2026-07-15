"""E-experiment holdout sample (Joel's E-run work order, 2026-07-15).

Generates the PRE-REGISTERED sample: ~28 contexts NO champion covers,
stratified by distance from the nearest champion, with a fixed seed —
committed to the repo BEFORE the first ground-truth solve so nothing can be
cherry-picked after results. The acceptance bar is pre-registered in the
same file (Cowork's default stood — Joel did not override):
derived >= 97% of the converged canonical score on >= 90% of the sample,
ZERO invariant-battery failures on derived builds, worst case reported
regardless.

Strata:
  adjacent  — same AT as a champion, shares exactly ONE powerset with one
  distant   — same AT as a champion, shares NEITHER powerset
  thin      — the ATs with the fewest certified champions
  content   — a champion's exact combo under a DIFFERENT content preset
(EAT/Kheldian forced-pair ATs are excluded from adjacent/distant — their
powerset space is a single pair, so "distance" is meaningless there.)

Run:  py tools\\e_holdout_sample.py          (prints; --write commits the file)
"""
import argparse
import json
import os
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))

SEED = 20260715
OUT = os.path.join(ROOT, "benchmarks", "e_holdout.json")
BAR = {"derived_over_converged_min_ratio": 0.97,
       "sample_share_meeting_ratio": 0.90,
       "battery_failures_allowed": 0,
       "note": "pre-registered before the first ground-truth solve; "
               "worst case (min, p10, median) reported regardless of pass/fail"}
EATS = {"Class_Peacebringer", "Class_Warshade",
        "Class_Arachnos_Widow", "Class_Arachnos_Soldier"}
N_ADJACENT, N_DISTANT, N_THIN, N_CONTENT = 8, 8, 6, 6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    import server as srv
    champs = json.load(open(os.path.join(ROOT, "benchmarks", "champions.json"),
                            encoding="utf-8"))
    covered = set()
    champ_sets = {}          # at -> set of powerset full names used by champions
    champ_combos = []        # (at, prim, sec) of champions
    for key in champs:
        at, prim, sec, content = key.split("|")[:4]
        covered.add((at, prim, sec))
        champ_sets.setdefault(at, set()).update((prim, sec))
        champ_combos.append((at, prim, sec))
    by_at = srv.POWERSETS["by_archetype"]
    rng = random.Random(SEED)

    def combos_for(at):
        d = by_at.get(at) or {}
        prims = sorted(p["full_name"] for p in d.get("primary", []))
        secs = sorted(s["full_name"] for s in d.get("secondary", []))
        return [(at, p, s) for p in prims for s in secs
                if (at, p, s) not in covered]

    champ_ats = sorted({at for at, _, _ in champ_combos} - EATS)
    adjacent, distant = [], []
    for at in champ_ats:
        used = champ_sets[at]
        for c in combos_for(at):
            share = (c[1] in used) + (c[2] in used)
            if share == 1:
                adjacent.append(c)
            elif share == 0:
                distant.append(c)
    # thin = the non-EAT ATs with the fewest champion contexts
    counts = {}
    for at, _, _ in champ_combos:
        counts[at] = counts.get(at, 0) + 1
    thin_ats = sorted((at for at in champ_ats), key=lambda a: (counts[a], a))[:3]
    thin_pool = [c for at in thin_ats for c in combos_for(at)]
    # content axis: champion combos verbatim, different content
    alt_contents = ["general", "team", "av"]
    content_pool = sorted(
        (at, prim, sec, rng.choice(alt_contents))
        for at, prim, sec in sorted(set(champ_combos)) if at not in EATS)

    sample = []
    for stratum, pool, n in (("adjacent", sorted(adjacent), N_ADJACENT),
                             ("distant", sorted(distant), N_DISTANT),
                             ("thin", sorted(thin_pool), N_THIN)):
        picks = rng.sample(pool, min(n, len(pool)))
        sample += [{"key": f"{at}|{p}|{s}|itrial", "stratum": stratum}
                   for at, p, s in picks]
    picks = rng.sample(content_pool, min(N_CONTENT, len(content_pool)))
    sample += [{"key": f"{at}|{p}|{s}|{ct}", "stratum": "content"}
               for at, p, s, ct in picks]

    # no duplicates, nothing covered
    keys = [row["key"] for row in sample]
    assert len(keys) == len(set(keys)), "duplicate context in sample"
    for row in sample:
        at, p, s = row["key"].split("|")[:3]
        assert (at, p, s) not in covered or row["stratum"] == "content", row

    doc = {"seed": SEED, "acceptance_bar": BAR,
           "champion_roster_size": len(champs),
           "strata_counts": {st: sum(1 for r in sample if r["stratum"] == st)
                             for st in ("adjacent", "distant", "thin", "content")},
           "contexts": sample}
    print(json.dumps(doc["strata_counts"]))
    for row in sample:
        print(f"  {row['stratum']:9s} {row['key']}")
    print(f"total: {len(sample)}")
    if args.write:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=1)
        print(f"written: {OUT}")


if __name__ == "__main__":
    main()
