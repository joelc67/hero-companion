"""Reality-check our archetype modifier data against AUTHORITATIVE game data.

Source of truth: the game client's own bins, extracted with Bin Crawler + Pigg
Wrangler (github.com/wednesdaywoe/CoH-Planner) — the same origin City of Data is
built from — NOT Mids (which we found frozen ~6 months stale). A snapshot of the
per-archetype tables lives in tools/gamedata/tables/, current as of 2026-06-19.
See tools/gamedata/README.md for the refresh procedure.

Comparison: our modifier_tables store one value per archetype = the LEVEL-50
value, which aligns to index 49 of the game's per-level arrays. So we compare
our[at] against game[at][49] across every table.

A table where EVERY archetype disagrees is a representation/units convention
(e.g. Melee_Uniqueness: our 1.0 vs the game's 100.0), not drift — those are
reported separately and never "corrected". A subset disagreeing is real drift.

Run:  python tools/reality_check_gamedata.py
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
import server as srv  # noqa: E402

TABLES = os.path.join(os.path.dirname(__file__), "gamedata", "tables")
LVL50 = 49


def _norm(n):
    return (n[6:] if n.lower().startswith("class_") else n).lower()


def main():
    mt = srv.MODIFIER_TABLES
    ats = [a for a in srv.ARCH_BY_NAME.values()
           if a.get("playable") and a.get("column") is not None]
    per_table = {}          # table -> list of (at, ours, game) mismatches
    n_ats = checked = 0
    missing_tables = []
    for a in ats:
        f = os.path.join(TABLES, _norm(a["name"]) + ".json")
        if not os.path.exists(f):
            # COVERAGE (standing rule 2026-07-08): a missing table file silently
            # shrank the check — every playable AT must have its snapshot.
            missing_tables.append(a["name"])
            continue
        n_ats += 1
        ex = json.load(open(f, encoding="utf-8")).get("named_tables", {})
        for t, vals in ex.items():
            if not vals or LVL50 >= len(vals):
                continue
            our = mt.get(t)
            if our is None or a["column"] >= len(our):
                continue
            checked += 1
            ov, gv = our[a["column"]], vals[LVL50]
            if abs(ov - gv) > max(0.005, 0.005 * abs(gv)):
                per_table.setdefault(t, []).append((a["display_name"], ov, gv))

    drift = {t: h for t, h in per_table.items() if len(h) < n_ats}
    convention = {t: len(h) for t, h in per_table.items() if len(h) >= n_ats}

    print(f"Coverage: {n_ats} of {len(ats)} playable archetypes have game-table snapshots"
          + (f" — MISSING: {missing_tables}" if missing_tables else "") + ".")
    print(f"Compared {checked} (archetype x modifier) values at level 50.")
    print(f"REAL DRIFT (should be corrected from game data): "
          f"{sum(len(h) for h in drift.values())}")
    for t, hits in sorted(drift.items()):
        for disp, ov, gv in hits:
            print(f"  {disp:16s} {t:22s} ours={ov:+.4f}  game={gv:+.4f}")
    if convention:
        print(f"\nrepresentation conventions (ALL archetypes differ - NOT drift, left as-is): "
              f"{', '.join(convention)}")
    if not drift and not missing_tables:
        print("\nEvery archetype modifier matches the live game (bar the known conventions).")
    return sum(len(h) for h in drift.values()) + len(missing_tables)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
