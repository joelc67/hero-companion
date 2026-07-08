"""Patch the 65 ACCURACY set bonuses into data/ from the game client snapshot.

Root cause (2026-07-08): parse_mids.resolve_bonus_effects relabels Enhancement-type
set bonuses to the stat they modify, but its allowlist was missing "Accuracy" — so
every global-accuracy set bonus in the game (LotG 4pc +9%, Thunderstrike, ATOs…)
parsed to an EMPTY effects list and was invisible to the engine totals, the scorer
and the solver. The parser rule is fixed; this script back-fills the two data files
the app ships (data/enhancement_sets.json + data/set_bonuses.json) with the values
from the authoritative game-client extraction (tools/gamedata/setbonuses.json,
Bin Crawler) — GAME-FIRST, not Mids.

Matching rule (universal, no per-set cases): a game accuracy effect (attrib
"Accuracy", aspect "Strength") at piece count N patches OUR bonus record at the
same piece count whose display text names an Accuracy bonus and whose effects are
empty (the double-tier PvE/PvP sets make text matching necessary). Idempotent:
already-patched records are left alone.

Run:  python tools/patch_accuracy_bonuses.py
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.join(os.path.dirname(__file__), "..")
SNAP = os.path.join(os.path.dirname(__file__), "gamedata", "setbonuses.json")


def norm(s):
    """Set-name normalizer matching the game snapshot's keys: lowercase,
    apostrophes dropped, every other non-alphanumeric run -> '_'."""
    s = (s or "").strip().lower().replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def game_accuracy_tiers():
    """set-name-key -> [(pieces, value)] from the client extraction."""
    game = json.load(open(SNAP, encoding="utf-8"))
    out = {}
    for nm, rec in game.items():
        for t in rec.get("tiers", []):
            for e in t.get("effects", []):
                if (any(a.lower() == "accuracy" for a in e.get("attribs", []))
                        and (e.get("aspect") or "").lower() == "strength"):
                    out.setdefault(nm, []).append((t["pieces"], round(e["scale"], 5)))
    return out


def _acc_effect(value):
    return {"effect": "Accuracy", "damage_type": "None", "aspect": "Str",
            "modifies": "Accuracy", "value": value, "to_who": 2}


def patch_bonus_list(bonuses, tiers, label, report):
    """Fill empty accuracy tiers in one set record's bonus list."""
    changed = 0
    for pc, val in tiers:
        cands = [b for b in bonuses if b.get("pieces_required") == pc
                 and any("accuracy bonus" in (t or "").lower()
                         for t in b.get("bonuses", []))]
        if not cands:
            report.append(f"  MISSING TIER: {label} {pc}pc (game says +{val*100:.0f}%)")
            continue
        for b in cands:
            if b.get("effects"):
                vals = [e.get("value") for e in b["effects"] if e.get("effect") == "Accuracy"]
                if vals and abs(vals[0] - val) > 1e-6:
                    report.append(f"  VALUE DRIFT: {label} {pc}pc ours={vals[0]} game={val}")
                continue
            b["effects"] = [_acc_effect(val)]
            changed += 1
    return changed


def main():
    tiers_by_key = game_accuracy_tiers()
    total_game = sum(len(v) for v in tiers_by_key.values())
    report = []

    es_path = os.path.join(ROOT, "data", "enhancement_sets.json")
    sb_path = os.path.join(ROOT, "data", "set_bonuses.json")
    es = json.load(open(es_path, encoding="utf-8"))
    sb = json.load(open(sb_path, encoding="utf-8"))

    matched_sets = set()
    n_es = 0
    for s in es:
        tiers = tiers_by_key.get(norm(s.get("name")))
        if tiers:
            matched_sets.add(norm(s.get("name")))
            n_es += patch_bonus_list(s.get("bonuses", []), tiers, s.get("name"), report)
    n_sb = 0
    for rec in sb.values():
        tiers = tiers_by_key.get(norm(rec.get("name")))
        if tiers:
            n_sb += patch_bonus_list(rec.get("bonuses", []), tiers, rec.get("name"), report)

    unmatched = sorted(set(tiers_by_key) - matched_sets)
    if unmatched:
        report.append(f"  GAME SETS NOT FOUND IN OUR DATA: {unmatched}")

    print(f"Game accuracy bonuses: {total_game} across {len(tiers_by_key)} sets.")
    print(f"Patched: {n_es} in enhancement_sets.json, {n_sb} in set_bonuses.json.")
    for line in report:
        print(line)
    if n_es or n_sb:
        json.dump(es, open(es_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(sb, open(sb_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("Data files written.")
    else:
        print("Nothing to do (already patched).")
    return 1 if report else 0


if __name__ == "__main__":
    sys.exit(main())
