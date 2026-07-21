"""RECERT VERDICT GATE (Joel's standing mechanic, made a tool 2026-07-21).

The v34 wave's lesson, now structural: a re-converged champion is a CANDIDATE,
not a successor. Its in-run score is a within-run ranking (retracted claim,
2026-07-15) — the only portable comparison is fresh-process CANONICAL vs
CANONICAL under the current model. v34 measured: 7 of 9 recerts LOST that
check and the incumbents stood.

Per recert-shard context:
  - evaluate the INCUMBENT's picks (champions.json) canonically
  - evaluate the RECERT's picks (shard) canonically, same process, same model
  - verdict: supersede  iff recert > incumbent + EPS, else keep

Outputs recert_verdicts.json ({context_key: "supersede"|"keep"}) — the file
merge_champion_shards.py --replace now REQUIRES — plus the verdict table for
Joel (champions.json commits only after he has seen it).

Run:   py tools\\recert_verdicts.py champions_shard_par_p0.json [...]
Then:  py tools\\merge_champion_shards.py --replace --verdicts recert_verdicts.json <shards...>
"""
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv  # noqa: E402
import first_principles as fp  # noqa: E402
from evaluate_first import evaluate_picks, EPS  # noqa: E402

MAIN = os.path.join(ROOT, "benchmarks", "champions.json")
OUT = os.path.join(ROOT, "recert_verdicts.json")


def _role_for(at, content):
    return (srv.ai_build.CONTENT_PRESETS.get(content or "", {}).get("default_role")
            or srv._AT_DEFAULT_ROLE.get(at, "damage"))


def main():
    shards = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not shards:
        raise SystemExit("usage: recert_verdicts.py shard1.json [shard2.json ...]")
    incumbents = json.load(open(MAIN, encoding="utf-8"))
    os.environ["HC_SOLVER_BACKEND"] = "cbc"
    verdicts, rows = {}, []
    print(f"verdict gate under model {fp.MODEL_VERSION} "
          f"(fresh-process canonical vs canonical, EPS {EPS})\n")
    for sp in shards:
        sd = json.load(open(sp, encoding="utf-8"))
        for key, cand in sorted(sd.items()):
            parts = key.split("|")
            at, prim, sec, content = parts[:4]
            form = parts[4] if len(parts) > 4 else None
            role = _role_for(at, content)
            name = f"{prim.split('.')[-1]}/{sec.split('.')[-1]}" + (
                f" [{form}]" if form else "")
            inc = incumbents.get(key)
            if not inc:
                # a NEW context has no incumbent — it merges by definition
                verdicts[key] = "supersede"
                rows.append((name, None, None, "NEW"))
                print(f"  NEW (no incumbent)                    {name}")
                continue
            inc_c, _ = evaluate_picks(at, prim, sec, content, inc["picks"],
                                      role, form=form)
            cand_c, _ = evaluate_picks(at, prim, sec, content, cand["picks"],
                                       role, form=form)
            if inc_c is None or cand_c is None:
                verdicts[key] = "keep"       # fail SAFE: unmeasurable → incumbent
                rows.append((name, inc_c, cand_c, "KEEP (eval failed)"))
                print(f"  EVAL FAILED → KEEP incumbent          {name}")
                continue
            win = cand_c > inc_c + EPS
            verdicts[key] = "supersede" if win else "keep"
            rows.append((name, inc_c, cand_c,
                         "SUPERSEDE" if win else "KEEP"))
            print(f"  {'SUPERSEDE' if win else 'KEEP     '}  incumbent "
                  f"{inc_c:9.1f} vs recert {cand_c:9.1f} (Δ {cand_c - inc_c:+8.1f})  {name}")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(verdicts, f, indent=1)
    n_sup = sum(1 for v in verdicts.values() if v == "supersede")
    print(f"\n=== VERDICTS: {n_sup} supersede, "
          f"{len(verdicts) - n_sup} keep, of {len(verdicts)} ===")
    print(f"written: {OUT}  ({time.strftime('%Y-%m-%d %H:%M')})")
    print("TABLE GOES TO JOEL BEFORE champions.json COMMITS (standing order).")


if __name__ == "__main__":
    main()
