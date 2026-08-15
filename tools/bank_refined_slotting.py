"""Bank population-refined SLOTTING layers into champions.json.

Game-truth ruling (Joel, 2026-08-14): the stored canonical score must describe
the build the app actually serves. champions.json stores picks; serve-time
re-derivation meant a refined slotting had no persistence channel. This tool
is that channel: for each CHALLENGER verdict in a wave_pop verdicts file, it
attaches the production-validated refined build as entry["slotting"], which
`server._champion_slotting` then serves verbatim on the champion-delivery
solve and `evaluate_first` scores directly as canonical.

HARD-FAILS (writes nothing) unless, for every banked context:
  - the verdicts file says CHALLENGER
  - the refined build's non-inherent picks EQUAL the entry's certified picks
    (a slotting for different picks is not this champion's)
  - engine.validate_build is clean and _assign_pick_levels seats it TODAY
  - every set slot's piece still resolves against current data

After banking: run `py tools\\evaluate_first.py --skip-riders --write` (the
canonical refresh — slotting-bearing entries score the stored build) and
`py tools\\validate_champions.py`. A later re-certification that rewrites an
entry drops its layer (learn.save_champion writes picks/score/certificate
only) — correct: stale by definition; the context falls back to solver serve.

Run:  py tools/bank_refined_slotting.py <verdicts.json> <results_dir>
"""
import copy
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv     # noqa: E402
import engine            # noqa: E402

MAIN = os.path.join(ROOT, "benchmarks", "champions.json")


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: bank_refined_slotting.py <verdicts.json> <results_dir>")
    verdicts = json.load(open(sys.argv[1], encoding="utf-8"))
    results_dir = sys.argv[2]
    champs = json.load(open(MAIN, encoding="utf-8"))

    staged = {}
    for row in verdicts:
        key = row.get("key")
        if row.get("verdict") != "CHALLENGER":
            print(f"  skip ({row.get('verdict')}): {key}")
            continue
        if key not in champs:
            raise SystemExit(f"FAIL: {key} not in champions.json — nothing written")
        path = os.path.join(results_dir,
                            key.replace("|", "_").replace(".", "-") + ".json")
        build = json.load(open(path, encoding="utf-8"))["powers"]
        at = key.split("|")[0]
        want = {fn for fn in champs[key]["picks"] if not fn.startswith("Inherent")}
        have = {p["full_name"] for p in build
                if not p["full_name"].startswith("Inherent")}
        if want != have:
            raise SystemExit(f"FAIL: {key} refined picks != certified picks "
                             f"(±{want ^ have}) — nothing written")
        errs = engine.validate_build({"archetype": at, "powers": build})
        if isinstance(errs, dict):
            errs = errs.get("errors") or []
        if errs:
            raise SystemExit(f"FAIL: {key} slotting fails validate_build today: "
                             f"{errs[:3]} — nothing written")
        if not srv._assign_pick_levels(copy.deepcopy(build), archetype=at):
            raise SystemExit(f"FAIL: {key} slotting unseatable on the ladder "
                             f"today — nothing written")
        staged[key] = build

    if not staged:
        raise SystemExit("FAIL: no CHALLENGER rows to bank — nothing written")
    for key, build in staged.items():
        champs[key]["slotting"] = build
        print(f"  BANKED slotting ({sum(len(p.get('slots') or []) for p in build)} "
              f"slots): {key}")
    with open(MAIN, "w", encoding="utf-8") as f:
        json.dump(champs, f, indent=1)
    print(f"\nOK: {len(staged)} slotting layer(s) banked into champions.json "
          f"({len(champs)} contexts). Now run evaluate_first --write and "
          f"validate_champions.")


if __name__ == "__main__":
    main()
