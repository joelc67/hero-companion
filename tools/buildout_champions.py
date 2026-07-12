"""ROSTER BUILD-OUT: converge NEW champion contexts to the gold standard —
one continuous run, certification identical to refresh_champions (fresh
L1-legal autopick seed, deep_optimize converge + restarts under the generous
budget, stale-roster ban, learn.save_champion stores each result with its
honest certificate the moment its context finishes).

Joel's overnight run order (2026-07-10, corrected twice: nonstop until done,
and ALL 12 missing archetypes — "If we are set to do 12, do them all"):
level-50 champions for every archetype missing one, armor ATs first.

Kheldian/VEAT honesty, resolved by evidence (probe 2026-07-10 night):
- VEAT seeds are BRANCH-LEGAL: autopick picks base tree + the context's one
  branch (in-game-correct; zero Fortunata picks in the Night Widow seed,
  zero Bane in the Crab seed) — the unverified concern is now verified.
- Kheldian certificates carry a SCOPE LIMIT stated in the report: form-
  SWAPPING play is unmodeled; a picked form power (White Dwarf) scores as
  its raw toggle effects only. The certificate certifies the human-form
  rotation the model actually measures — said plainly, never hidden.

The context list lives HERE, ordered — Joel vetoes by editing/reordering;
only unstarted contexts can swap once a run is live. Contexts already in
champions.json are skipped (safe to re-run after an interrupt).

Run:  py tools\buildout_champions.py
"""
import argparse
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv  # noqa: E402

# Armor ATs first (the v30-reshaped region), then the rest. One context per
# missing archetype, each anchoring mechanically DISTINCT territory —
# reasoning per pick in session-report.md 2026-07-10 night.
NEW_CONTEXTS = [
    "Class_Brute|Brute_Melee.Battle_Axe|Brute_Defense.Fiery_Aura|itrial",
    "Class_Tanker|Tanker_Defense.Invulnerability|Tanker_Melee.Super_Strength|itrial",
    "Class_Scrapper|Scrapper_Melee.Broad_Sword|Scrapper_Defense.Super_Reflexes|itrial",
    "Class_Stalker|Stalker_Melee.Radiation_Melee|Stalker_Defense.Dark_Armor|itrial",
    "Class_Sentinel|Sentinel_Ranged.Fire_Blast|Sentinel_Defense.Willpower|itrial",
    "Class_Blaster|Blaster_Ranged.Fire_Blast|Blaster_Support.Energy_Manipulation|itrial",
    "Class_Corruptor|Corruptor_Ranged.Water_Blast|Corruptor_Buff.Kinetics|itrial",
    "Class_Dominator|Dominator_Control.Mind_Control|Dominator_Assault.Fiery_Assault|itrial",
    # Joel's second correction: all 12. VEATs branch-legal (probe-verified);
    # Kheldians carry the human-form scope limit (see docstring).
    "Class_Arachnos_Widow|Widow_Training.Night_Widow_Training|Teamwork.Widow_Teamwork|itrial",
    "Class_Arachnos_Soldier|Arachnos_Soldiers.Crab_Spider_Soldier|Training_Gadgets.Crab_Spider_Training|itrial",
    "Class_Peacebringer|Peacebringer_Offensive.Luminous_Blast|Peacebringer_Defensive.Luminous_Aura|itrial",
    "Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-solves", type=int, default=25000,
                    help="solve budget per context (default 25000 = certification)")
    ap.add_argument("--restarts", type=int, default=6,
                    help="perturb-and-reclimb restarts per context (default 6)")
    ap.add_argument("--only", default="",
                    help="comma-separated archetype class names — this worker "
                         "converges ONLY those contexts (parallel sharding; "
                         "pair with HC_CHAMPIONS_PATH so workers never share "
                         "a write file)")
    args = ap.parse_args()
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    client = srv.app.test_client()
    # Skip-check reads the REAL champions.json (main roster) AND, when sharded,
    # this worker's own shard — an interrupted worker resumes cleanly.
    champs = json.load(open(os.path.join(ROOT, "benchmarks", "champions.json"),
                            encoding="utf-8"))
    shard = os.environ.get("HC_CHAMPIONS_PATH")
    if shard and os.path.exists(shard):
        champs.update(json.load(open(shard, encoding="utf-8")))
    pool = [k for k in NEW_CONTEXTS if not only or k.split("|")[0] in only]
    todo = [k for k in pool if k not in champs]
    skipped = [k for k in pool if k in champs]
    for k in skipped:
        print(f"already certified, skipping: {k}")
    print(f"{len(todo)} of {len(NEW_CONTEXTS)} contexts to converge")

    # Same harden-before-certify guard as refresh_champions: stale-roster
    # powers can never anchor a gold standard.
    try:
        _reg = json.load(open(os.path.join(os.path.dirname(__file__), "gamedata",
                                           "power_aliases.json"), encoding="utf-8"))
        stale_roster = set(_reg.get("roster_diffs") or [])
    except Exception:  # noqa: BLE001
        stale_roster = set()
    # KHELDIAN FORM POWERS: same honesty boundary, same mechanism (2026-07-12).
    # Form-SWAPPING is unmodeled — a power whose defining mechanic the model
    # cannot represent cannot anchor a gold standard (the stale-roster
    # precedent, not an optimizer ban list). MEASURED cost of leaving one in:
    # the PB seed's White Dwarf (5 set categories / 20 candidate sets vs a
    # normal shield's 1/8, plus a big base-res armor the v30 credit binds)
    # ran 24h WITHOUT converging while the form-less Warshade twin converged
    # in 2.3h. Both Kheldian champions certify as HUMAN-FORM builds — the
    # scope limit already declared; the WS certificate is form-less already.
    # Lift this ban WITH the form-modeling work, never before.
    stale_roster |= {
        "Peacebringer_Defensive.Luminous_Aura.White_Dwarf",
        "Peacebringer_Offensive.Luminous_Blast.Bright_Nova",
        "Warshade_Defensive.Umbral_Aura.Black_Dwarf",
        "Warshade_Offensive.Umbral_Blast.Dark_Nova",
    }

    t0 = time.time()
    results = []
    for key in todo:
        at, prim, sec, content = key.split("|")
        el = (time.time() - t0) / 60
        print(f"[{el:6.1f}m] {key}", flush=True)
        ap_res = client.post("/build/autopick", json={
            "archetype": at, "primary": prim, "secondary": sec,
            "content": content}).get_json()
        if not (ap_res and ap_res.get("powers")):
            results.append((key, "AUTOPICK FAILED", None))
            print("   -> AUTOPICK FAILED", flush=True)
            continue
        stale_picks = sorted({p.get("full_name") for p in ap_res["powers"]}
                             & stale_roster)
        if stale_picks:
            print(f"   seed picked stale-roster powers {stale_picks} — banned from "
                  f"the certification build (harden-before-certify)", flush=True)
        try:
            _, info = srv.deep_optimize(at, prim, sec, None, content,
                                        ap_res["powers"],
                                        max_solves=args.max_solves,
                                        restarts=args.restarts,
                                        ban=stale_roster)
            cert = info.get("certificate")
            results.append((key, f"score {info.get('score'):.1f}", cert))
            print(f"   -> score {info.get('score'):.1f}  certificate: {cert}", flush=True)
        except Exception as e:  # noqa: BLE001
            results.append((key, f"ERROR {type(e).__name__}: {e}", None))
            print(f"   -> ERROR {e}", flush=True)

    print("\n=== ROSTER BUILD-OUT SUMMARY ===")
    done = 0
    for key, status, cert in results:
        conv = "CONVERGED" if (cert or {}).get("converged") else "truncated/FAILED"
        done += 1 if (cert or {}).get("converged") else 0
        print(f"  {conv:16s} {status:16s} {key}")
    print(f"{done} of {len(todo)} new contexts converged "
          f"({len(pool)} in this worker's pool of {len(NEW_CONTEXTS)} ordered, "
          f"{len(skipped)} pre-existing)")
    print(f"total: {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
