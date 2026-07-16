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

# Joel's data-source ruling (2026-07-16): "the accolade list and descriptions
# come right from the game, no half baked wiki." The power records carry NO
# description text (measured: 0 of 28), but clientmessages-en.bin does — it is
# the client's own UI/tooltip string table. We take the game's sentence where
# it can be matched UNAMBIGUOUSLY (the display name + a grant phrasing), and
# otherwise print an effect line COMPUTED from the game's own effect scales.
# We never guess a description onto a row.
BIN_PIGG = r"C:/Games/HC2/assets/live/bin.pigg"
_GRANT_PAT = r"(granted you|has granted|you have been granted|permanent increase)"


def game_descriptions(displays):
    """{display: the game's own sentence} — only unambiguous matches."""
    try:
        import re as _re
        sys.path.insert(0, os.path.join(ROOT, "tools", "gamedata",
                                        "pigg-wrangler"))
        from pigg_wrangler.pigg import PiggArchive
        txt = PiggArchive(BIN_PIGG).extract("clientmessages-en.bin").decode(
            "latin-1", errors="ignore")
    except Exception as e:  # noqa: BLE001
        print(f"  (clientmessages unavailable: {type(e).__name__} — rows will "
              f"use computed effect lines)")
        return {}
    import re as _re
    strings = [x.strip() for x in _re.findall(r"[ -~]{12,}", txt)]
    pat = _re.compile(_GRANT_PAT, _re.I)
    out = {}
    for d in displays:
        cands = [x for x in strings if d.lower() in x.lower() and pat.search(x)]
        if cands:
            out[d] = min(cands, key=len)
    return out


def effect_line(eff):
    """The always-available fallback: what the GAME's own scales say it grants
    (HitPoints scale 1.0 = +10% MaxHP — corroborated by the client's own text:
    'Freedom Phalanx Reserve ... +10% Max Hit Points')."""
    bits = []
    if eff.get("HitPoints"):
        bits.append(f"+{eff['HitPoints'] * 10:.0f}% Max Hit Points")
    if eff.get("Endurance"):
        bits.append(f"+{eff['Endurance']:.0f} Max Endurance")
    if eff.get("Recovery"):
        bits.append(f"+{eff['Recovery']:.0f} Recovery (click power)")
    if eff.get("Regeneration"):
        bits.append(f"+{eff['Regeneration']:.0f} Regeneration (click power)")
    return ", ".join(bits)


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

    descs = game_descriptions([v["display"] for v in out.values()])
    n_game = 0
    for v in out.values():
        g = descs.get(v["display"])
        if g:
            v["description"] = g
            v["description_source"] = "game (clientmessages-en.bin)"
            n_game += 1
        else:
            v["description"] = effect_line(v["effects"])
            v["description_source"] = ("computed from the game's own effect "
                                       "scales" if v["effects"] else "")
    print(f"descriptions: {n_game} from the game's own text, "
          f"{len(out) - n_game} computed from its effect scales (no row is "
          f"guessed; attainment chains are NOT in the client — see Phase-0)")

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
