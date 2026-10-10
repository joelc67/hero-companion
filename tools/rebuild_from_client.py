"""Rebuild named buckets of named powers from the CURRENT client export (Issue 28
Page 4 AFTER), keeping our pv_mode 2 rows - the sync's "rebuild" adjudication,
run alone so the full sync is not re-applied to an already-synced powers.json.

Used for powers our record never matched the client on (old Mids rows), where
the patch reworked them and the difference sync could not apply (2026-10-10):
  Epic.Pyre_Mastery.Char            Page 4 doubled the damage; ours carried Melee_*
                                    tables and pre-patch scales
  Epic.Sentinel_Fire_Mastery.Char   Page 4 moved it to Ranged_* tables at 0.22;
                                    ours carried a Melee 0.1 row and a 12 hold scale

  python tools/rebuild_from_client.py           # report
  python tools/rebuild_from_client.py --write
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sync_client_delta as scd  # noqa: E402

REBUILD = {
    "Epic.Pyre_Mastery.Char": ("damage_effects", "control_effects"),
    "Epic.Sentinel_Fire_Mastery.Char": ("damage_effects", "control_effects"),
}


TABLES = os.path.join(scd.ROOT, "data", "modifier_tables.json")
ARCH = os.path.join(scd.ROOT, "data", "archetypes.json")
# Sentinel Char's rebuilt row reads Ranged_InherentDamage (unconditional, the client's
# own second damage row). Melee_InherentDamage stays ABSENT on purpose: 238 Scrapper/
# Stalker crit_row duplicates read it, and their crits are priced by probability rows.
ADD_TABLES = ("Ranged_InherentDamage",)


def _class_tables(cdir, names):
    """{table: [level-50 value per column]} from bin_crawler.export_classes, per
    playable column; verified by rebuilding Ranged_Damage against ours first."""
    # PLAYABLE columns only: the one row reading the table is on a player power
    # (read at the AT's own column); pet/critter columns stay 0.0
    cols = {a["column"]: a["name"] for a in json.load(open(ARCH, encoding="utf-8"))["archetypes"]
            if a.get("column") is not None and a.get("playable")}
    mod = json.load(open(TABLES, encoding="utf-8"))
    n = len(mod["tables"]["Ranged_Damage"])

    def col_vals(table):
        out = []
        for c in range(n):
            cls = cols.get(c)
            f = os.path.join(cdir, (cls or "")[6:].lower() + ".json") if cls else None
            if not f or not os.path.exists(f):
                out.append(0.0)
                continue
            nt = json.load(open(f, encoding="utf-8")).get("named_tables") or {}
            out.append(round(nt[table][49], 4) if len(nt.get(table) or []) > 49 else 0.0)
        return out
    check = col_vals("Ranged_Damage")
    bad = [c for c, (x, y) in enumerate(zip(check, mod["tables"]["Ranged_Damage"]))
           if cols.get(c) and abs(x - y) > 0.005 * max(1.0, abs(y))]
    if bad:
        sys.exit(f"REFUSE: export Ranged_Damage disagrees with ours at columns {bad[:8]}")
    return mod, {t: col_vals(t) for t in names}


def main():
    write = "--write" in sys.argv
    cdir = sys.argv[sys.argv.index("--classes") + 1] if "--classes" in sys.argv else None
    if not cdir:
        sys.exit("REFUSE: --classes <bin_crawler.export_classes dir> (Ranged_InherentDamage)")
    mod, add = _class_tables(cdir, ADD_TABLES)
    for t, v in add.items():
        print(f"  TABLE {t}: {sum(1 for x in v if x)} non-zero columns")
        mod["tables"][t] = v
    data = json.loads(open(scd.POWERS, "rb").read().decode("utf-8"))
    ours = {p["full_name"]: p for v in data.values() for p in v}
    ax = scd.load_export(scd.AFTER)
    res = dict(ax)
    res.update(scd.load_redirects(scd.AFTER))
    for fn, buckets in REBUILD.items():
        p = ours[fn]
        ra, _ = scd.convert(ax[fn], res, patch=True)
        for b in buckets:
            keep = [e for e in (p.get(b) or []) if e.get("pv_mode") == 2]
            old = [e for e in (p.get(b) or []) if e.get("pv_mode") != 2]
            p[b] = keep + [scd._row_from(k, None) for k in ra.get(b, scd.Counter()).elements()]
            print(f"  {fn} {b}: {len(old)} rows -> {len(p[b]) - len(keep)} from client")
            for e in p[b][len(keep):]:
                print(f"      {e.get('damage_type') or e.get('mez')} {e['scale']} {e['modifier_table']}")
        p[scd.MARK] = scd.TAG
    if write:
        with open(scd.POWERS, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        with open(TABLES, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(mod, ensure_ascii=False, separators=(",", ":")))
        print(f"wrote {scd.POWERS}, {TABLES}")


if __name__ == "__main__":
    main()
