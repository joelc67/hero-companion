"""Patch the 11 HEAL-STRENGTH set bonuses into data/ from the game client snapshot.

Same gap and same fix as the 2026-07-08 accuracy find: parse_mids's Enhancement-
relabel allowlist was missing "Heal", so every heal-strength set bonus (Numina 4pc
+6%, Doctored Wounds 4pc +4%, Panacea 6pc +6%…) parsed to an EMPTY effects list.
The parser rule is fixed (v29); this script back-fills the two data files the app
ships (data/enhancement_sets.json + data/set_bonuses.json) with the values from
the authoritative game-client extraction (tools/gamedata/setbonuses.json, Bin
Crawler) — GAME-FIRST, not Mids.

Matching rule (universal, no per-set cases): a game heal-strength effect (attrib
"Heal_Dmg", aspect "Strength") at piece count N patches OUR bonus record at the
same piece count whose display text names a Heal bonus and whose effects are
empty. Idempotent: already-patched records are left alone.

Coverage denominator: the snapshot's own count (11) is the independent M; the run
hard-fails if any tier can't be seated.

Run:  python tools/patch_heal_strength.py
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.join(os.path.dirname(__file__), "..")
SNAP = os.path.join(os.path.dirname(__file__), "gamedata", "setbonuses.json")


def norm(s):
    s = (s or "").strip().lower().replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def game_heal_tiers():
    """set-name-key -> [(pieces, value)] from the client extraction."""
    game = json.load(open(SNAP, encoding="utf-8"))
    out = {}
    for nm, rec in game.items():
        for t in rec.get("tiers", []):
            for e in t.get("effects", []):
                if (any(a.lower() == "heal_dmg" for a in e.get("attribs", []))
                        and (e.get("aspect") or "").lower() == "strength"):
                    out.setdefault(nm, []).append((t["pieces"], round(e["scale"], 5)))
    return out


def _heal_effect(value):
    return {"effect": "Heal", "damage_type": "None", "aspect": "Str",
            "modifies": "Heal", "value": value, "to_who": 2}


def patch_bonus_list(bonuses, tiers, label, report):
    changed = 0
    for pc, val in tiers:
        cands = [b for b in bonuses if b.get("pieces_required") == pc
                 and any("heal bonus" in (t or "").lower()
                         for t in b.get("bonuses", []))]
        if not cands:
            report.append(f"  MISSING TIER: {label} {pc}pc (game says +{val*100:.0f}%)")
            continue
        for b in cands:
            if b.get("effects"):
                vals = [e.get("value") for e in b["effects"] if e.get("effect") == "Heal"]
                if vals and abs(vals[0] - val) > 1e-6:
                    report.append(f"  VALUE DRIFT: {label} {pc}pc ours={vals[0]} game={val}")
                continue
            b["effects"] = [_heal_effect(val)]
            changed += 1
    return changed


def main():
    tiers_by_key = game_heal_tiers()
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

    print(f"Game heal-strength bonuses: {total_game} across {len(tiers_by_key)} sets "
          f"(independent denominator from the snapshot).")
    print(f"Patched: {n_es} in enhancement_sets.json, {n_sb} in set_bonuses.json.")
    for line in report:
        print(line)
    if report:
        print("HARD FAIL: nothing written.")
        return 1
    if n_es or n_sb:
        json.dump(es, open(es_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(sb, open(sb_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("Data files written.")
    else:
        print("Nothing to do (already patched).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
