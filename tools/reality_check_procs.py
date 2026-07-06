"""Reality-check the engine's proc catalog (data/proc_catalog.json) against the
authoritative PPM rates extracted from the game client (tools/gamedata/proc_ppm.json —
every Boosts.* power's ProcsPerMinute, see tools/gamedata/README.md).

Catalog uid maps exactly: uid "Crafted_Hecatomb_F" = game "Boosts.Crafted_Hecatomb_F.
Crafted_Hecatomb_F". First sync (2026-07-06) confirmed 29 and fixed 11 — the ATO procs
were undervalued 30-43% (Ascendency of the Dominator 3.5 vs the game's 5.0/6.0).

The proc-chance FORMULA (area factor, caps) stays provisional until the Bopper-guide
paste; this check covers the VALUES.

Report-only.  Run:  python tools/reality_check_procs.py
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "data", "proc_catalog.json")
SNAP = os.path.join(os.path.dirname(__file__), "gamedata", "proc_ppm.json")


def main():
    cat = json.load(open(CATALOG, encoding="utf-8"))
    game = json.load(open(SNAP, encoding="utf-8"))["ppm"]
    matched = drift = missing = provisional = 0
    for procs in cat.get("damage_procs", {}).values():
        for p in procs:
            uid = p.get("uid")
            gv = game.get(f"Boosts.{uid}.{uid}")
            if p.get("provisional"):
                provisional += 1
            if gv is None:
                missing += 1
                continue
            if isinstance(gv, list):
                continue                      # multi-effect boost — review by hand
            if abs((p.get("ppm") or 0) - gv) > 0.01:
                drift += 1
                print(f"  DRIFT {p.get('set')}: catalog={p.get('ppm')} game={gv}")
            else:
                matched += 1
    print(f"Proc PPM values matched to the live game: {matched}.")
    print(f"REAL DRIFT: {drift}  (not in game snapshot: {missing}, still provisional: {provisional})")
    if not drift:
        print("Every catalog proc's PPM matches the game client.")
    return drift


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
