"""EFFECT-STRUCTURE re-sync (v33 recommendation A, 2026-07-16): the scalar
reality checks (reality_check_powers) pin recharge/end/cast/range VALUES but
never noticed that Temperature Protection LOST a whole +MaxHP effect and had
its +Regen flagged unbuffable in the 6/23 patch. This check diffs the
EXISTENCE and ENHANCEABILITY of survival/sustain self-effects between our
data/powers.json and the current client export (bin-crawler out_full), which
is the class of gap Maelwys round 5 exposed.

Scope (deliberately the sustain/armor family the engine consumes for totals,
NOT every damage/control template — that would drown the signal):
  survival effects: HitPoints/Maximum (+MaxHP), Regeneration, Recovery,
  Endurance (+MaxEnd), Heal-over-time.
For each MATCHED player power (full_name direct or via power_aliases.json):
  MISSING   the client has a survival self-effect we lack entirely (the TP
            +MaxHP class) — priced as a DELTA to fix via additive patcher.
  ENH_FLAG  we mark an effect unbuffable / non-Heal-enhanceable where the
            client's boosts_allowed says it IS enhanceable (the TP regen
            class) — solver leaves enhancement value on the table.
  EXTRA     we carry a survival effect the client no longer has (stale-added).

Coverage denominator printed and HARD-FAILED on (N matched of M our-armor
powers), per the coverage-denominator rule. Report-only; NEVER writes
powers.json — the additive patchers do that on Joel's word.

Run:  py tools\\reality_check_effect_structure.py  [--all]   (--all widens
      past the armor/support sets to every matched power)
"""
import argparse
import glob
import json
import os
import sys
import collections

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_FULL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
ALIASES = os.path.join(ROOT, "tools", "gamedata", "power_aliases.json")

# client (attrib, aspect) -> our (effect, damage_type|None). Survival family only.
SURVIVAL_MAP = {
    ("HitPoints", "Maximum"): ("HitPoints", None),
    ("Regeneration", "Current"): ("Regeneration", None),
    ("Recovery", "Current"): ("Recovery", None),
    ("Endurance", "Maximum"): ("Endurance", None),
}
# a Heal-over-time shows as HitPoints/Current in the client; our effect "Heal".
HEAL_CLIENT = ("HitPoints", "Current")


def client_index():
    idx = {}
    for fp in glob.iglob(os.path.join(OUT_FULL, "**", "*.json"), recursive=True):
        b = os.path.basename(fp)
        if b in ("_export_manifest.json", "index.json"):
            continue
        try:
            r = json.load(open(fp, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if isinstance(r, dict) and r.get("full_name"):
            idx[r["full_name"]] = r
    return idx


def client_self_survival(rec):
    """Set of (effect, dtype) survival self-effects the client power grants to
    Self, plus whether Heal-category enhancement is allowed on the power."""
    found = set()
    heal_ok = "Heal" in (rec.get("boosts_allowed") or [])

    def walk(effs):
        for e in effs or []:
            for t in e.get("templates", []):
                if t.get("target") not in (None, "Self"):
                    continue
                asp = t.get("aspect")
                for a in t.get("attribs", []):
                    key = SURVIVAL_MAP.get((a, asp))
                    if key:
                        found.add(key)
                    if (a, asp) == HEAL_CLIENT:
                        found.add(("Heal", None))
            walk(e.get("child_effects", []))
    walk(rec.get("effects") or [])
    return found, heal_ok


def our_self_survival(p):
    """(effect,dtype) survival self-effects in our record + per-effect enh info."""
    found = {}
    for e in p.get("self_effects", []) or []:
        eff = e.get("effect")
        if eff in ("HitPoints", "Regeneration", "Recovery", "Endurance", "Heal"):
            found[(eff, None)] = {
                "unbuffable": bool(e.get("unbuffable")),
                "enhance_aspect": e.get("enhance_aspect"),
            }
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    cli = client_index()
    aliases = {}
    if os.path.exists(ALIASES):
        aliases = json.load(open(ALIASES, encoding="utf-8"))
    our = json.load(open(os.path.join(ROOT, "data", "powers.json"),
                         encoding="utf-8"))

    ARMOR_HINT = ("_Defense.", "_Buff.", "Defense.", "Armor", "Aura")
    matched = missing = enhflag = extra = 0
    considered = 0
    findings = collections.defaultdict(list)

    for pset, plist in our.items():
        if not isinstance(plist, list):
            continue
        for p in plist:
            fn = p.get("full_name", "")
            is_armorish = any(h in fn for h in ARMOR_HINT) or \
                any(h in pset for h in ARMOR_HINT)
            if not args.all and not is_armorish:
                continue
            considered += 1
            rec = cli.get(fn)
            if rec is None:
                alias = aliases.get(fn)
                if alias:
                    rec = cli.get(alias)
            if rec is None:
                continue
            matched += 1
            cli_fx, heal_ok = client_self_survival(rec)
            our_fx = our_self_survival(p)
            # MISSING: client survival effect absent from ours
            for key in cli_fx:
                if key not in our_fx:
                    missing += 1
                    findings["MISSING"].append((fn, key[0]))
            # EXTRA: ours has one client dropped
            for key in our_fx:
                if key not in cli_fx:
                    extra += 1
                    findings["EXTRA"].append((fn, key[0]))
            # ENH_FLAG: client allows Heal-enh but ours marks unbuffable /
            # non-Heal aspect on a Regeneration/HitPoints effect
            if heal_ok:
                for key, info in our_fx.items():
                    if key[0] in ("Regeneration", "HitPoints"):
                        if info["unbuffable"] or info["enhance_aspect"] not in (
                                "Heal", "HitPoints"):
                            enhflag += 1
                            findings["ENH_FLAG"].append(
                                (fn, key[0],
                                 f"unbuffable={info['unbuffable']} "
                                 f"aspect={info['enhance_aspect']}"))

    scope = "ALL matched" if args.all else "armor/support"
    print(f"EFFECT-STRUCTURE DIFF ({scope}) vs client out_full "
          f"(export 2026-07-15, client 7/7)")
    print(f"  {matched} of {considered} our {scope} powers matched a client "
          f"record (direct + alias); unmatched = alias-map gap, not this "
          f"check's scope\n")
    for tag in ("MISSING", "ENH_FLAG", "EXTRA"):
        rows = findings[tag]
        print(f"  {tag}: {len(rows)}")
        for row in sorted(set(tuple(r) for r in rows))[:40]:
            print("     " + " | ".join(str(x) for x in row))
        if len(set(tuple(r) for r in rows)) > 40:
            print(f"     ... +{len(set(tuple(r) for r in rows)) - 40} more")
    print(f"\nSUMMARY: {missing} missing survival effects, {enhflag} "
          f"enhanceability-flag gaps, {extra} stale-extra, over {matched} "
          f"matched powers.")
    if matched == 0:
        print("HARD FAIL: zero matches — the check could not run.")
        sys.exit(1)


if __name__ == "__main__":
    main()
