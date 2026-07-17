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

# ⚠ CORRECTED 2026-07-16 (Joel's "find the join key" push — the fix is smaller
# and better than the workaround it replaces). The earlier claim here, "the
# power records carry NO description text (measured: 0 of 28)", was OUR BUG,
# not the client's gap: this tool read r["description"] / r["short_help"] —
# field names the exporter never emits. It emits **display_help** and
# **display_short_help**, already resolved through the message table
# (export_powers.py: `pw.display_help = msgs.resolve(pw.display_help)`).
# Reading the RIGHT field yields the game's own sentence for 28 of 28.
#
# So the fragile fallback that used to live here — scraping clientmessages for
# a string containing the accolade's name plus a grant-ish phrase, which
# matched only 5 of 28 and could in principle mis-bind — is DELETED. The record
# hands us its own text directly. Fewer moving parts, no matching heuristic, and
# every row is the game's, verbatim.
#
# (What the record does NOT carry is the badge REQUIREMENT text — demonstrated
# at the raw-byte level; see tools/extract_accolade_attainment.py. That is a
# different field on a different object, and it is why attainment has its own
# tool and its own honest fallback.)


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


def _alignment(req):
    """hero / villain / None from a record's activate_requires expression."""
    s = (req or "").lower()
    if "villain" in s:
        return "villain"
    if "hero" in s:
        return "hero"
    return None


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
            # GAME-FIRST alignment gate (Joel: "check the game", 2026-07-17): the
            # record's activate_requires ("type char> hero eq" / "villain eq")
            # says a character only gets this accolade's effect while that
            # alignment. This is the GAME's own reason only ONE of a hero/villain
            # twin ever applies (Portal Jockey = hero, Born In Battle = villain —
            # a character is one or the other), and why the NO-gate accolades
            # (Labyrinth Conqueror, Mazebreaker) legally STACK. None = no gate.
            "alignment": _alignment(r.get("activate_requires")),
            # the GAME's own sentence, straight off the record (display_help
            # is the field the exporter emits, already message-resolved)
            "description": (r.get("display_help") or "").strip(),
            "description_source": "game (power record display_help)",
            "short": (r.get("display_short_help") or "").strip(),
            "tier": tier, "effects": eff, "tables": tabs,
            "source": "client bins via out_extra_623 export 2026-07-16",
        }

    # Every row's description is now the GAME's own display_help, read straight
    # off the record — no matching heuristic, no computed fallback needed.
    n_game = sum(1 for v in out.values() if v["description"])
    for v in out.values():
        if not v["description"]:                    # belt-and-braces only
            v["description"] = effect_line(v["effects"])
            v["description_source"] = ("computed from the game's own effect "
                                       "scales" if v["effects"] else "")
    print(f"descriptions: {n_game} of {len(out)} are the game's own sentence "
          f"from the power record (display_help); no row is guessed. Badge "
          f"REQUIREMENT text is a different object — see "
          f"extract_accolade_attainment.py.")

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
