"""Merge parallel-worker champion SHARDS into benchmarks/champions.json.

The roster build-out runs 2-3 certification workers, each saving to its own
shard (HC_CHAMPIONS_PATH) so no two processes ever rewrite the same file.
This merges them: union of the real champions.json + every shard given on the
command line. HARD-FAILS on any key collision (workers hold disjoint context
lists by construction — a collision means the sharding was misconfigured, and
guessing which certificate wins would be a counterfeit).

Prints the coverage denominator (contexts in = contexts out) and refuses to
write anything on failure. Run AFTER the workers finish, BEFORE
validate_champions.

Run:  python tools/merge_champion_shards.py shard1.json shard2.json ...
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, "benchmarks", "champions.json")


def main():
    shards = sys.argv[1:]
    if not shards:
        raise SystemExit("usage: merge_champion_shards.py shard1.json [shard2.json ...]")
    data = json.load(open(MAIN, encoding="utf-8"))
    n_main = len(data)
    n_in = n_main
    for sp in shards:
        sd = json.load(open(sp, encoding="utf-8"))
        n_in += len(sd)
        for k, v in sd.items():
            if k in data:
                raise SystemExit(f"FAIL: context {k} exists in more than one "
                                 f"source (shard {sp}) — nothing written")
            if not (v.get("picks") and v.get("certificate")):
                raise SystemExit(f"FAIL: {k} in {sp} lacks picks/certificate "
                                 f"— nothing written")
            data[k] = v
        print(f"merged {len(sd):2d} champion(s) from {os.path.basename(sp)}")
    with open(MAIN, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    print(f"OK: {n_main} existing + {n_in - n_main} from shards = {len(data)} "
          f"contexts written ({n_in} in = {len(data)} out)")


if __name__ == "__main__":
    main()
