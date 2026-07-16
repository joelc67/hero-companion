"""ACCOLADE roster + effects, GAME-FIRST (v33 ruling B; also the data floor for
v34's accolade panel).

Joel's data-source ruling (2026-07-16): "the accolade list and descriptions
come right from the game, no half baked wiki." This reads the client bins only.

Source: tools/gamedata/bin-crawler/out_extra_623 (gitignored), exported
2026-07-16 from C:/Games/HC2/assets/live via:
    python -m bin_crawler.export_powers --assets-dir C:/Games/HC2/assets/live \\
        --output-dir <dir> --categories Boosts Temporary_Powers Set_Bonus
(Our standard export ships 34 of the bins' 204 categories and carried NO
accolade records at all — the gap that made "accolades are already in our
export" false.)

Emits data/accolades.json: every Temporary_Powers.Accolades.* record with its
display name, description text (the game's own), self effects + modifier
tables, and a tier:
  "passive"    — grants an always-on self buff we can price (+MaxHP/+MaxEnd)
  "click"      — a click/temporary accolade power (Recovery-burst class);
                 listed, NOT priced into passive totals (honest, stated)
  "badge_only" — no self effect we price; pure checklist row for the panel

⚠ The roster is the DATA's, not anyone's memory — and the data corrects a
common assumption: The Atlas Medallion grants +Endurance only (no +MaxHP),
Task Force Commander grants +MaxHP only.

Run:  py tools\\extract_accolades.py  [--dry-run]
"""
import argparse
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_extra_623")
OUT = os.path.join(ROOT, "data", "accolades.json")

PRICED = ("HitPoints", "Endurance")          # always-on fit effects
CLICKY = ("Recovery", "Regeneration")        # burst/click accolade powers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not os.path.isdir(EXPORT):
        print(f"HARD FAIL: export missing at {EXPORT} (recipe in docstring)")
        sys.exit(1)

    out = {}
    for fp in glob.iglob(os.path.join(EXPORT, "**", "*.json"), recursive=True):
        if os.path.basename(fp).startswith("_"):
            continue
        try:
            r = json.load(open(fp, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(r, dict):
            continue
        fn = r.get("full_name") or ""
        if not fn.startswith("Temporary_Powers.Accolades."):
            continue
        eff, tabs = {}, {}

        def w(effs):
            for e in effs or []:
                for t in e.get("templates", []):
                    if t.get("target") != "Self":
                        continue
                    for a in (t.get("attribs") or []):
                        if a in PRICED + CLICKY:
                            eff[a] = t.get("scale")
                            tabs[a] = t.get("table")
                w(e.get("child_effects"))
        w(r.get("effects"))

        if any(k in eff for k in PRICED):
            tier = "passive"
        elif any(k in eff for k in CLICKY):
            tier = "click"
        else:
            tier = "badge_only"
        name = fn.split(".")[-1]
        out[name] = {
            "full_name": fn,
            "display": r.get("display_name") or name.replace("_", " "),
            "description": (r.get("description") or r.get("short_help")
                            or "").strip(),
            "tier": tier, "effects": eff, "tables": tabs,
            "source": "client bins via out_extra_623 export 2026-07-16",
        }

    tiers = {}
    for v in out.values():
        tiers[v["tier"]] = tiers.get(v["tier"], 0) + 1
    print(f"accolades: {len(out)}  tiers={tiers}")
    for k, v in sorted(out.items()):
        if v["tier"] == "passive":
            print(f"  passive  {k:28s} {v['effects']}")
    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
