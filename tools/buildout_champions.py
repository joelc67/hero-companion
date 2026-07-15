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
    # Joel's third correction (2026-07-12): "make a champion for each form."
    # 5-part keys: the 5th part is the FORM — the form power is PINNED (never
    # dropped, seeded in) and the OTHER form banned, so each champion is a
    # committed one-form build. The 4-part Kheldian keys above stay the
    # HUMAN-form champions (all forms banned there).
    "Class_Peacebringer|Peacebringer_Offensive.Luminous_Blast|Peacebringer_Defensive.Luminous_Aura|itrial|dwarf",
    "Class_Peacebringer|Peacebringer_Offensive.Luminous_Blast|Peacebringer_Defensive.Luminous_Aura|itrial|nova",
    "Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial|dwarf",
    "Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial|nova",
    # Joel (2026-07-12): "people might play a combo, using all form types" —
    # TRI-FORM is the classic Kheldian playstyle. Both form powers pinned;
    # the build carries all three shapes.
    "Class_Peacebringer|Peacebringer_Offensive.Luminous_Blast|Peacebringer_Defensive.Luminous_Aura|itrial|triform",
    "Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial|triform",
]

_PB_DWARF = "Peacebringer_Defensive.Luminous_Aura.White_Dwarf"
_PB_NOVA = "Peacebringer_Offensive.Luminous_Blast.Bright_Nova"
_WS_DWARF = "Warshade_Defensive.Umbral_Aura.Black_Dwarf"
_WS_NOVA = "Warshade_Offensive.Umbral_Blast.Dark_Nova"
# (archetype, form) -> the form power SET that champion is BUILT AROUND.
FORM_POWERS = {
    ("Class_Peacebringer", "dwarf"): {_PB_DWARF},
    ("Class_Peacebringer", "nova"): {_PB_NOVA},
    ("Class_Peacebringer", "triform"): {_PB_DWARF, _PB_NOVA},
    ("Class_Warshade", "dwarf"): {_WS_DWARF},
    ("Class_Warshade", "nova"): {_WS_NOVA},
    ("Class_Warshade", "triform"): {_WS_DWARF, _WS_NOVA},
}
KHELDIAN_FORMS = {_PB_DWARF, _PB_NOVA, _WS_DWARF, _WS_NOVA}


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
    ap.add_argument("--keys", default="",
                    help="comma-separated EXACT context keys — finer-grained "
                         "than --only (used by tools/converge_parallel.py to "
                         "partition arbitrarily); overrides --only")
    ap.add_argument("--recert", action="store_true",
                    help="RE-certification mode (the evaluate-first wave): the "
                         "--keys given are certified movers being deliberately "
                         "re-converged — the certified-skip ignores main/sibling "
                         "shards for them (this worker's OWN shard still resumes). "
                         "Keys may name any certified context, not just "
                         "NEW_CONTEXTS.")
    args = ap.parse_args()
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    keys = {s.strip() for s in args.keys.split(",") if s.strip()}
    if args.recert and not keys:
        raise SystemExit("--recert requires explicit --keys (never re-certify "
                         "by wildcard)")
    known = set(NEW_CONTEXTS)
    if args.recert:
        known |= set(json.load(open(os.path.join(ROOT, "benchmarks",
                                                 "champions.json"),
                                    encoding="utf-8")))
    unknown = keys - known
    if unknown:
        # honest denominator: a mistyped key must fail loudly, never silently shrink
        raise SystemExit(f"unknown context key(s): {sorted(unknown)}")

    client = srv.app.test_client()
    # Skip-check reads the REAL champions.json (main roster), EVERY root shard
    # (2026-07-14 lesson: a context certified in an UNMERGED sibling shard is
    # still certified — without this, a new worker re-converged PB/WS human at
    # full 25k-solve cost and would have collided at merge), and this worker's
    # own shard — an interrupted worker resumes cleanly.
    import glob
    champs = json.load(open(os.path.join(ROOT, "benchmarks", "champions.json"),
                            encoding="utf-8"))
    for sp in sorted(glob.glob(os.path.join(ROOT, "champions_shard_*.json"))):
        try:
            champs.update(json.load(open(sp, encoding="utf-8")))
        except Exception:  # noqa: BLE001 — an unreadable shard never blocks a run
            pass
    # Gate-PULLED contexts (champions_held_ladderfix.json) linger in their
    # original shards but are NOT certified — they must re-converge, so they
    # never count as done here.
    _held = os.path.join(ROOT, "champions_held_ladderfix.json")
    if os.path.exists(_held):
        for _k in json.load(open(_held, encoding="utf-8")):
            champs.pop(_k, None)
    shard = os.environ.get("HC_CHAMPIONS_PATH")
    if shard and os.path.exists(shard):
        champs.update(json.load(open(shard, encoding="utf-8")))
    if args.recert:
        # Re-certification: only this worker's OWN shard skips (interrupt
        # resume); prior certificates are exactly what's being replaced.
        champs = {}
        if shard and os.path.exists(shard):
            champs = json.load(open(shard, encoding="utf-8"))
        pool = sorted(keys)
    elif keys:
        pool = [k for k in NEW_CONTEXTS if k in keys]
    else:
        pool = [k for k in NEW_CONTEXTS if not only or k.split("|")[0] in only]
    todo = [k for k in pool if k not in champs]
    skipped = [k for k in pool if k in champs]
    for k in skipped:
        print(f"already certified, skipping: {k}")
    print(f"{len(todo)} of {len(pool) if args.recert else len(NEW_CONTEXTS)} "
          f"contexts to converge" + (" [RECERT]" if args.recert else ""))

    # Same harden-before-certify guard as refresh_champions: stale-roster
    # powers can never anchor a gold standard.
    try:
        _reg = json.load(open(os.path.join(os.path.dirname(__file__), "gamedata",
                                           "power_aliases.json"), encoding="utf-8"))
        stale_roster = set(_reg.get("roster_diffs") or [])
    except Exception:  # noqa: BLE001
        stale_roster = set()
    # KHELDIAN FORMS, per Joel's per-form ruling (2026-07-12, superseding the
    # blanket ban): each champion commits to ONE form story. HUMAN contexts
    # (4-part keys) ban every form power — the scope their certificate
    # describes. FORM contexts (5-part keys) PIN their own form and ban the
    # other, so a dwarf champion can never wander into nova. Form-SWAPPING
    # remains unmodeled either way — every Kheldian certificate certifies the
    # one form it names, priced as what the model measures (the form toggle's
    # own stats + the human powers). MEASURED history: an unpinned, unvalued
    # White Dwarf in the seed ground 24h without converging (the plateau the
    # heartbeat now makes visible); its form-less twin converged in 2.3h.

    t0 = time.time()
    results = []
    for key in todo:
        parts = key.split("|")
        at, prim, sec, content = parts[:4]
        form = parts[4] if len(parts) > 4 else None
        pin = set(FORM_POWERS[(at, form)]) if form else set()
        # Kheldians: human contexts ban all forms; a form context bans the
        # forms it did NOT pin. Everyone else: just the stale roster.
        ban = set(stale_roster)
        if at in ("Class_Peacebringer", "Class_Warshade"):
            ban |= KHELDIAN_FORMS - pin
        el = (time.time() - t0) / 60
        print(f"[{el:6.1f}m] {key}"
              + (f"  [pin {'+'.join(p.split('.')[-1] for p in sorted(pin))}]" if pin else ""),
              flush=True)
        ap_res = client.post("/build/autopick", json={
            "archetype": at, "primary": prim, "secondary": sec,
            "content": content}).get_json()
        if not (ap_res and ap_res.get("powers")):
            results.append((key, "AUTOPICK FAILED", None))
            print("   -> AUTOPICK FAILED", flush=True)
            continue
        banned_picks = sorted({p.get("full_name") for p in ap_res["powers"]} & ban)
        if banned_picks:
            print(f"   seed picked banned powers {banned_picks} — stripped from "
                  f"the certification build (harden-before-certify)", flush=True)
        try:
            _, info = srv.deep_optimize(at, prim, sec, None, content,
                                        ap_res["powers"],
                                        max_solves=args.max_solves,
                                        restarts=args.restarts,
                                        ban=ban, pin=pin, form=form)
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
