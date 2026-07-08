"""Sync player-facing power VALUES (recharge / endurance / cast / range) to the
game client snapshot — including the 118 powers only reachable via the alias map.

Context (2026-07-08): the coverage-denominator rule + power_aliases.json exposed 91
stale values confined to the sets whose internal names diverged from the client
(Time Manipulation, Electrical Affinity/Shock Therapy, the renamed epic pools…).
Pattern is consistent with balance passes our frozen Mids base never saw — e.g. the
epic-pool endurance reduction (all Ice Mastery end costs exactly 1.25x the client's)
and real reworks (Defibrillate 26 -> 10.4 end, Black Hole range 10 -> 50).

Rules:
  * only player-facing powers (what the planner slots) are touched
  * snipe conditional cast times are preserved (our > game by > 1.0s = the fast-snipe
    mechanic, NOT drift — same rule as reality_check_powers)
  * idempotent; prints every change; report-only with --dry-run

Run:  python tools/sync_power_values.py [--dry-run]
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
import server as srv  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
SNAP = os.path.join(os.path.dirname(__file__), "gamedata", "power_values.json")
ALIASES = os.path.join(os.path.dirname(__file__), "gamedata", "power_aliases.json")
POWERS_JSON = os.path.join(ROOT, "data", "powers.json")
FIELDS = [("base_recharge", "rech"), ("end_cost", "end"), ("range", "range"),
          ("cast_time", "cast")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    snap = json.load(open(SNAP, encoding="utf-8"))
    aliases = json.load(open(ALIASES, encoding="utf-8")).get("aliases") or {}
    data = json.load(open(POWERS_JSON, encoding="utf-8"))

    player_sets = set()
    for groups in srv.POWERSETS["by_archetype"].values():
        for kind in ("primary", "secondary", "epic"):
            for e in (groups.get(kind) or []):
                player_sets.add(e.get("full_name"))
    player_sets |= {ps for ps in data if ps.startswith(("Pool.", "Inherent."))}

    changed = 0
    per_field = {of: 0 for of, _ in FIELDS}
    for ps in sorted(player_sets):
        for p in data.get(ps) or []:
            fn = p.get("full_name")
            g = snap.get(fn) or snap.get(aliases.get(fn, ""))
            if not g:
                continue
            for of, gf in FIELDS:
                ov, gv = p.get(of), g.get(gf)
                if ov is None or gv is None:
                    continue
                if abs(float(ov) - float(gv)) <= max(0.01, 0.02 * abs(float(gv))):
                    continue
                if of == "cast_time" and float(ov) - float(gv) > 1.0:
                    continue          # fast-snipe conditional cast, not drift
                print(f"  {fn}: {of} {ov} -> {gv}")
                p[of] = gv
                per_field[of] += 1
                changed += 1

    print(f"\nSynced {changed} values ({per_field}).")
    if changed and not args.dry_run:
        json.dump(data, open(POWERS_JSON, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"wrote data/powers.json")
    elif args.dry_run:
        print("(dry run — nothing written)")
    else:
        print("Nothing to do (already synced).")


if __name__ == "__main__":
    main()
