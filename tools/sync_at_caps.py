"""Sync data/archetypes.json's per-archetype limits from the live client export.

Issue 28 Page 4 (live 2026-10-06) raised the damage cap 4.0 -> 5.0 (+300% -> +400%)
for Defender, Controller, Dominator, Mastermind, Arachnos Soldier, Arachnos Widow,
Peacebringer and Warshade. The change lives in classes.bin's `damage_cap` SCALAR;
the first PATCH-WATCH pass compared only per-level lists and missed it.

Source: tools/gamedata/bin-crawler/out_full/<archetype>.json (Bin Crawler
export_classes of the installed client), level-50 values. Field map:

  hitpoints <- hit_points[49]    hp_cap <- hp_cap[49]     res_cap <- resistance_cap
  recharge_cap <- recharge_cap   damage_cap <- damage_cap recovery_cap <- recovery_cap
  base_recovery <- recovery_base base_regen <- regeneration_base
  (regen_cap is in different units, x4 - checked as a ratio, never written)

HOLD lists fields NOT written even when they differ: a difference there predates the
patch and changes certified work, so it is Joel's ruling (CLAUDE.md), not this tool's.

  python tools/sync_at_caps.py           # report + write
  python tools/sync_at_caps.py --check   # report only
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH = os.path.join(ROOT, "data", "archetypes.json")
OUT = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
MAP = {"hitpoints": "hit_points", "hp_cap": "hp_cap", "res_cap": "resistance_cap",
       "recharge_cap": "recharge_cap", "damage_cap": "damage_cap",
       "recovery_cap": "recovery_cap", "base_recovery": "recovery_base",
       "base_regen": "regeneration_base"}
# Brute base HP: app 1499, client 1606.3 in every export since 2026-06-06 (not Page 4).
HOLD = {("Class_Brute", "hitpoints"): "client 1606.3 since at least 2026-06-06 - awaiting Joel's ruling"}


def _l50(v):
    return v[49] if isinstance(v, list) else v


def main():
    check = "--check" in sys.argv
    raw = open(ARCH, "rb").read()
    data = json.loads(raw.decode("utf-8"))
    if json.dumps(data, ensure_ascii=False).encode("utf-8") != raw:
        print("FAIL: cannot reproduce archetypes.json byte-for-byte - refusing to write")
        sys.exit(2)
    changes, held = [], []
    for r in data["archetypes"]:
        if not r.get("playable"):
            continue
        f = os.path.join(OUT, r["name"].replace("Class_", "").lower() + ".json")
        if not os.path.exists(f):
            print(f"FAIL: no client table for {r['name']} ({f})")
            sys.exit(1)
        c = json.load(open(f, encoding="utf-8"))["attribs"]
        for ours, cl in MAP.items():
            v = _l50(c.get(cl))
            if v is None:
                continue
            tol = max(0.6, abs(float(v)) * 0.001) if ours in ("hitpoints", "hp_cap") else 1e-4
            if abs(float(r[ours]) - float(v)) <= tol:
                continue
            new = round(float(v), 4) if ours not in ("hitpoints",) else round(float(v))
            if (r["name"], ours) in HOLD:
                held.append((r["name"], ours, r[ours], new, HOLD[(r["name"], ours)]))
                continue
            changes.append((r["name"], ours, r[ours], new))
            r[ours] = new
        rc = _l50(c.get("regeneration_cap"))
        if rc and abs(r["regen_cap"] / rc - 4.0) > 1e-3:
            print(f"WARN {r['name']} regen_cap {r['regen_cap']} vs client {rc} (expected x4) - not written")
    for n, k, a, b in changes:
        print(f"  {n:24} {k:13} {a} -> {b}")
    for n, k, a, b, why in held:
        print(f"  HELD {n:19} {k:13} {a} (client {b}) - {why}")
    print(f"{len(changes)} change(s), {len(held)} held")
    if check or not changes:
        return
    out = json.dumps(data, ensure_ascii=False).encode("utf-8")
    json.loads(out.decode("utf-8"))
    with open(ARCH, "wb") as fh:
        fh.write(out)
    print(f"wrote {ARCH}")


if __name__ == "__main__":
    main()
