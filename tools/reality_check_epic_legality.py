"""STANDING GUARD (Joel's #13 item-5 pin, 2026-07-19): every epic/ancillary pool
the app OFFERS an archetype must appear in that archetype's GAME-DERIVED legality
set. Game-first: the authority is each epic power's `requires` clause in the
client bins (`@Class_X` tokens gate the pool to an archetype). Compares the app's
by_archetype epic offering against it; HARD-FAILS on any pool offered to an AT the
game does not grant (coverage-denominator rule: N of M offered entries checked,
fail if N<M or any leak).

Context: the 2026-07-19 MM field report suspected a "phantom Field Mastery" epic
leak. The game said otherwise — Field Mastery IS a real MM ancillary (display
"Energy Mastery"); the visible defect was a stale display name (fixed separately).
The audit found ZERO gating leaks across all offered pools. This guard pins that
clean state so a future data sync can't silently introduce a leak — the same class
of insurance as reality_check_names.py.

Run:  py tools\\reality_check_epic_legality.py
"""
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BINS = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
_CLASS_RE = re.compile(r"@(Class_[A-Za-z_]+)")


def game_legality():
    """pool full_name -> set of Class_ tokens (game-granted ATs), + display map."""
    pool_classes, pool_disp = {}, {}
    for idx in glob.glob(os.path.join(BINS, "epic", "*", "index.json")):
        d = os.path.dirname(idx)
        r = json.load(open(idx, encoding="utf-8"))
        key = r.get("key")
        if not key:
            continue
        pool_disp[key] = r.get("display_name")
        classes = set()
        for pj in glob.glob(os.path.join(d, "*.json")):
            if pj.endswith("index.json"):
                continue
            req = json.load(open(pj, encoding="utf-8")).get("requires") or ""
            classes.update(_CLASS_RE.findall(req))
        pool_classes[key] = classes
    return pool_classes, pool_disp


def main():
    pool_classes, pool_disp = game_legality()
    if not pool_classes:
        print("no epic pools found in the bin export — cannot verify")
        sys.exit(1)
    # (display, Class) -> bins key, for resolving Mids-vs-bins internal-name
    # divergence (app offers Epic.Dark_Mastery_Mastermind; bins key it
    # Epic.Mastermind_Dark_Mastery — same pool, same display, same AT gate).
    disp_class = {}
    for k, cl in pool_classes.items():
        for c in cl:
            disp_class[(pool_disp.get(k), c)] = k
    ap = os.path.join(ROOT, "tools", "gamedata", "power_aliases.json")
    alias = {}
    if os.path.exists(ap):
        alias = json.load(open(ap, encoding="utf-8")).get("aliases", {})

    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "server"))
    import server as srv  # noqa: E402
    by = srv.POWERSETS.get("by_archetype") or {}

    checked = 0
    fails = []
    for at, cats in by.items():
        for e in (cats.get("epic") or []):
            fn = e.get("full_name")
            disp = e.get("display_name")
            checked += 1
            # 1) direct: the offered full_name is a bins epic key
            if fn in pool_classes:
                if at not in pool_classes[fn]:
                    fails.append((at, fn, disp, "WRONG-AT; game grants "
                                  + str(sorted(pool_classes[fn]))))
                continue
            # 2) name divergence: resolve via alias map, then (display, AT)
            gk = alias.get(fn)
            if gk and at in pool_classes.get(gk, set()):
                continue
            if (disp, at) in disp_class:
                continue
            fails.append((at, fn, disp, "no game epic pool legal for this AT"))

    print(f"epic legality checked vs the game bins: {checked} of {checked} "
          f"offered pool entries")
    if fails:
        print(f"\nEPIC LEGALITY LEAKS — {len(fails)}:")
        for at, fn, disp, why in fails:
            print(f"  [{at}] {fn} '{disp}': {why}")
        print("\nFAIL")
        sys.exit(1)
    print("\nPASS — every offered epic pool is game-legal for its archetype.")


if __name__ == "__main__":
    main()
