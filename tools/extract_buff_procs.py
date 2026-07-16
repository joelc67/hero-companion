"""BUFF-PROC catalog (v33 ruling C, 2026-07-16) — game-first.

proc_catalog.json covers DAMAGE procs. Buff procs (the Superior Unrelenting
Fury class: "chance for +Regen/+End Discount", which Maelwys round 5 flagged
as unpriced sustain) were invisible to us entirely: our piece_boosts for the
piece carried ONLY its RechargeTime component, because the proc's actual
effect lives in a `Boosts.*` record that grants a separate
`Set_Bonus.Global_Bonus.*` buff power — and NEITHER category was in our
crawler export (the export ships 34 of the bins' 204 categories).

Source: the extended export at tools/gamedata/bin-crawler/out_extra_623
(gitignored), produced 2026-07-16 from C:/Games/HC2/assets/live via:
    python -m bin_crawler.export_powers --assets-dir C:/Games/HC2/assets/live \\
        --output-dir <dir> --categories Boosts Temporary_Powers Set_Bonus

The chain this walks, per piece:
    Boosts.<piece>.<piece>   (ppm, template attrib Grant_Power)
        -> params.power_names -> Set_Bonus.Global_Bonus.<buff>
            -> that buff's SELF templates = the real magnitudes + duration

Emits data/buff_proc_catalog.json:
    {piece_uid: {ppm, grants, duration_s, stack_limit, effects:{attrib: scale},
                 tables:{attrib: modifier_table}, help_stack_limit, source}}

⚠ RECORDED DATA CONFLICT (Superior Unrelenting Fury): the effect template says
stack_limit 2; the piece's own help text says "stacks up to 5 times". Both are
client-derived. We store BOTH (stack_limit from the template = what the engine
enforces, help_stack_limit parsed from the help text) and the consumer uses the
template value — the conservative reading, which errs AGAINST our own sustain
claim. At realistic aura proc rates the average stack count sits ~1.1, below
either cap, so the choice barely moves the number (quantified in the C tests).

Run:  py tools\\extract_buff_procs.py  [--dry-run]
"""
import argparse
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_extra_623")
OUT = os.path.join(ROOT, "data", "buff_proc_catalog.json")
SET_DETAILS = os.path.join(ROOT, "data", "set_details.json")

# the sustain/utility attribs a buff proc can grant that we can price
WANTED = {"Regeneration", "Recovery", "EnduranceDiscount", "HitPoints",
          "Endurance"}


def load_export():
    by_name = {}
    for fp in glob.iglob(os.path.join(EXPORT, "**", "*.json"), recursive=True):
        if os.path.basename(fp).startswith("_"):
            continue
        try:
            r = json.load(open(fp, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if isinstance(r, dict) and r.get("full_name"):
            by_name[r["full_name"]] = r
    return by_name


def walk_templates(rec):
    out = []

    def w(effs):
        for e in effs or []:
            for t in e.get("templates", []):
                out.append((e, t))
            w(e.get("child_effects"))
    w(rec.get("effects"))
    return out


def help_stack_limit(piece_uid):
    """The piece's own help text ('stacks up to N times') — the second,
    disagreeing client source. Recorded, not used."""
    if not os.path.exists(SET_DETAILS):
        return None
    sd = json.load(open(SET_DETAILS, encoding="utf-8"))
    for s in sd.values():
        for p in s.get("pieces", []):
            if p.get("piece_uid") == piece_uid:
                m = re.search(r"stacks up to (\d+) times",
                              p.get("help_template") or "", re.I)
                return int(m.group(1)) if m else None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not os.path.isdir(EXPORT):
        print(f"HARD FAIL: export missing at {EXPORT} — re-run the crawler "
              f"(recipe in this file's docstring).")
        sys.exit(1)
    by_name = load_export()
    print(f"export records: {len(by_name)}")

    catalog = {}
    for fn, rec in by_name.items():
        if not fn.startswith("Boosts."):
            continue
        for e, t in walk_templates(rec):
            if "Grant_Power" not in (t.get("attribs") or []):
                continue
            ppm = e.get("ppm") or 0
            if not ppm:
                continue
            granted = ((t.get("params") or {}).get("power_names") or [])
            for g in granted:
                grec = by_name.get(g)
                if not grec:
                    continue
                effects, tables, dur, slim = {}, {}, None, None
                for _ge, gt in walk_templates(grec):
                    if gt.get("target") != "Self":
                        continue
                    for a in (gt.get("attribs") or []):
                        if a not in WANTED:
                            continue
                        effects[a] = gt.get("scale")
                        tables[a] = gt.get("table")
                        d = gt.get("duration")
                        if isinstance(d, str):
                            m = re.match(r"([\d.]+)", d)
                            if m:
                                dur = float(m.group(1))
                        slim = gt.get("stack_limit") or slim
                if not effects:
                    continue
                piece = fn.split(".")[1]
                catalog[piece] = {
                    "ppm": ppm, "grants": g, "duration_s": dur,
                    "stack_limit": slim,
                    "help_stack_limit": help_stack_limit(piece),
                    "effects": effects, "tables": tables,
                    "source": "client bins via out_extra_623 export "
                              "2026-07-16 (Boosts -> Grant_Power -> Set_Bonus)",
                }
    print(f"buff procs found: {len(catalog)}")
    for k, v in sorted(catalog.items()):
        conflict = ""
        if v["help_stack_limit"] and v["help_stack_limit"] != v["stack_limit"]:
            conflict = (f"  ⚠ stack conflict: template {v['stack_limit']} vs "
                        f"help {v['help_stack_limit']}")
        print(f"  {k}: {v['ppm']} PPM, {v['effects']}, dur {v['duration_s']}s, "
              f"cap {v['stack_limit']}{conflict}")
    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=1, ensure_ascii=False)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
