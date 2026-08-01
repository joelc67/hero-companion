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

RUN-HEALTH COLUMN (Joel's addition, 2026-07-21 evening — from the WS-triform
counterfeit-convergence catch, 8a91b2c): a KEEP is ambiguous — "honest
challenger lost" and "challenger never searched" read identically. Every row
therefore carries the run's health: sweeps, restarts, converged flag (from the
shard certificate) and total/average solves mined from the worker log beside
the shard. PIN (the sanity floor): a run whose exploration falls below the
floor renders ⚠ COLLAPSED regardless of verdict — a collapsed KEEP means
"re-run me", never "incumbent fairly defended".

Run:   py tools\\recert_verdicts.py champions_shard_par_p0.json [...]
Then:  py tools\\merge_champion_shards.py --replace --verdicts recert_verdicts.json <shards...>
"""
import json
import os
import re
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


# SANITY FLOOR (pinned): below either bound the run is COLLAPSED — the search
# never really explored. Calibration: the WS-triform counterfeit run totaled 1
# solve across 7 sweeps; every honest run in the same wave totaled thousands
# (~24-600 per sweep). The floor sits far below honest and far above broken.
FLOOR_TOTAL_SOLVES = 50
FLOOR_AVG_PER_SWEEP = 5.0


# ── LEGALITY (Joel's ruling, 2026-07-31: "legality outranks score") ──────────
# 0.12.30 shipped 8 of 24 champions that could NOT be built in game - Wall of
# Force / Misdirection / Weave held with one pool power where the game wants
# two. This gate had "kept" every one of them, because it compared SCORE ONLY
# and the illegal incumbents outscored their legal replacements. A gate that
# cannot see legality will make that same trade again on the next wave.
#
# Same callable the user-facing validator uses, so the gate and the app can
# never disagree about what the game allows.
def _illegality(picks):
    """[] when the build is buildable in game; a list of reasons when it is not.

    None means the check itself could not run - deliberately distinct from [],
    because "no violations" and "could not tell" must not collapse together.
    """
    try:
        return srv._epic_prereq_errors(
            [{"full_name": fn} for fn in (picks or [])]) or []
    except Exception:  # noqa: BLE001
        return None


def _legality_verdict(inc_bad, cand_bad):
    """The four branches, in Joel's order. Returns (verdict|None, note).

    None = legality has nothing to say, fall through to the score comparison.
    ⚠ The second branch is the whole point: a LEGAL challenger supersedes an
    ILLEGAL incumbent even when it scores LOWER. That is exactly the 0.12.30
    case, and a score-only gate gets it backwards every time.
    """
    if inc_bad is None or cand_bad is None:
        return "keep", "legality UNMEASURABLE — keeping incumbent (fail safe)"
    if cand_bad and not inc_bad:
        return "keep", "challenger is NOT BUILDABLE in game — refused regardless of score"
    if inc_bad and not cand_bad:
        return "supersede", "incumbent is NOT BUILDABLE — legality outranks score"
    if inc_bad and cand_bad:
        return "keep", ("⚠ BOTH are NOT BUILDABLE — incumbent kept, but this "
                        "context ships an unbuildable champion and needs a fix")
    return None, ""


def _run_health(shard_path, key, cert):
    """Health summary for one recert run: certificate facts + solve counts
    mined from the worker log that sits beside the shard (same basename).
    Returns (text, collapsed_bool). Missing log → certificate-only fallback
    (collapse signature there: every restart 'converging' in ~one sweep)."""
    sweeps = (cert or {}).get("sweeps") or 0
    restarts = (cert or {}).get("restarts_done") or 0
    conv = bool((cert or {}).get("converged"))
    trunc = bool((cert or {}).get("budget_truncated"))
    refusal = (cert or {}).get("error") or ""
    total = None
    log = os.path.splitext(shard_path)[0] + ".log"
    try:
        txt = open(log, encoding="utf-8", errors="replace").read()
        # the context's block: from its header line to its '-> score' line
        blk = txt.split(key, 1)[1]
        blk = blk.split("-> score", 1)[0]
        # cumulative-per-restart counters: total = sum of each restart's max
        per_restart = {}
        for m in re.finditer(r"sweep\s+\d+\s+r(\d+)\s+best=\S+\s+cur=\S+\s+"
                             r"solves=(\d+)/", blk):
            r, s = int(m.group(1)), int(m.group(2))
            per_restart[r] = max(per_restart.get(r, 0), s)
        if per_restart:
            total = sum(per_restart.values())
    except Exception:  # noqa: BLE001 — health degrades to cert-only, never crashes
        pass
    if total is not None:
        avg = total / max(sweeps, 1)
        collapsed = total < FLOOR_TOTAL_SOLVES or avg < FLOOR_AVG_PER_SWEEP
        text = (f"{sweeps} sweeps · {total} solves (~{avg:.0f}/sweep) · "
                f"{restarts} restarts · "
                f"{'converged' if conv else 'TRUNCATED' if trunc else 'stopped'}")
    else:
        # cert-only: a run whose every restart 'converged' in ~one sweep is the
        # empty-neighborhood signature even without solve counts
        ratio = sweeps / max(restarts + 1, 1)
        collapsed = ratio < 2.0
        text = (f"{sweeps} sweeps · solves n/a (no log) · {restarts} restarts · "
                f"{'converged' if conv else 'TRUNCATED' if trunc else 'stopped'}")
    if refusal:
        collapsed = True
        text += f" · REFUSED: {refusal}"
    if collapsed:
        text = "⚠ COLLAPSED RUN — re-run before trusting this row · " + text
    return text, collapsed


def main():
    shards = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not shards:
        raise SystemExit("usage: recert_verdicts.py shard1.json [shard2.json ...]")
    incumbents = json.load(open(MAIN, encoding="utf-8"))
    os.environ["HC_SOLVER_BACKEND"] = "cbc"
    verdicts, rows = {}, []
    print(f"verdict gate under model {fp.MODEL_VERSION} "
          f"(fresh-process canonical vs canonical, EPS {EPS})\n")
    n_collapsed = 0
    n_illegal_inc = 0
    for sp in shards:
        sd = json.load(open(sp, encoding="utf-8"))
        for key, cand in sorted(sd.items()):
            parts = key.split("|")
            at, prim, sec, content = parts[:4]
            form = parts[4] if len(parts) > 4 else None
            role = _role_for(at, content)
            name = f"{prim.split('.')[-1]}/{sec.split('.')[-1]}" + (
                f" [{form}]" if form else "")
            health, collapsed = _run_health(sp, key, cand.get("certificate"))
            n_collapsed += 1 if collapsed else 0
            inc = incumbents.get(key)
            if not inc:
                # a NEW context has no incumbent — it merges by definition
                # (unless its own run collapsed: a broken NEW entry must not
                # enter the roster either — pinned floor beats convenience)
                verdicts[key] = "keep" if collapsed else "supersede"
                rows.append((name, None, None, "NEW", health))
                print(f"  {'BLOCKED (collapsed NEW run)' if collapsed else 'NEW (no incumbent)':38s}{name}")
                print(f"      run: {health}")
                continue
            # LEGALITY FIRST — before score, because it can decide on its own
            # and because it stays reportable even when evaluation fails.
            inc_bad, cand_bad = _illegality(inc["picks"]), _illegality(cand["picks"])
            if inc_bad:
                n_illegal_inc += 1
            leg_verdict, leg_note = _legality_verdict(inc_bad, cand_bad)
            if leg_verdict:
                verdicts[key] = leg_verdict
                rows.append((name, None, None, leg_verdict.upper() + " (legality)", health))
                print(f"  {leg_verdict.upper():9s}  {name}")
                print(f"      LEGALITY: {leg_note}")
                for e in (cand_bad or [])[:2]:
                    print(f"        challenger: {e}")
                for e in (inc_bad or [])[:2]:
                    print(f"        incumbent:  {e}")
                print(f"      run: {health}")
                continue

            inc_c, _ = evaluate_picks(at, prim, sec, content, inc["picks"],
                                      role, form=form)
            cand_c, _ = evaluate_picks(at, prim, sec, content, cand["picks"],
                                       role, form=form)
            if inc_c is None or cand_c is None:
                verdicts[key] = "keep"       # fail SAFE: unmeasurable → incumbent
                rows.append((name, inc_c, cand_c, "KEEP (eval failed)", health))
                print(f"  EVAL FAILED → KEEP incumbent          {name}")
                print(f"      run: {health}")
                continue
            win = cand_c > inc_c + EPS
            verdicts[key] = "supersede" if win else "keep"
            rows.append((name, inc_c, cand_c,
                         "SUPERSEDE" if win else "KEEP", health))
            print(f"  {'SUPERSEDE' if win else 'KEEP     '}  incumbent "
                  f"{inc_c:9.1f} vs recert {cand_c:9.1f} (Δ {cand_c - inc_c:+8.1f})  {name}")
            print(f"      run: {health}")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(verdicts, f, indent=1)
    n_sup = sum(1 for v in verdicts.values() if v == "supersede")
    print(f"\n=== VERDICTS: {n_sup} supersede, "
          f"{len(verdicts) - n_sup} keep, of {len(verdicts)}"
          + (f" — ⚠ {n_collapsed} COLLAPSED RUN(S): those contexts need a "
             f"RE-RUN, their verdicts prove nothing" if n_collapsed else "")
          + (f" — ⚠ {n_illegal_inc} INCUMBENT(S) NOT BUILDABLE in game"
             if n_illegal_inc else "")
          + " ===")
    print(f"written: {OUT}  ({time.strftime('%Y-%m-%d %H:%M')})")
    print("TABLE GOES TO JOEL BEFORE champions.json COMMITS (standing order).")


if __name__ == "__main__":
    main()
