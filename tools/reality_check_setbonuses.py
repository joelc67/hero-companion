"""Reality-check our IO-set bonuses against authoritative game data.

Set bonuses ARE extractable (each set's tiers reference Set_Bonus.* powers whose effects
hold the values). A snapshot of all 227 sets' bonuses lives in tools/gamedata/setbonuses.json,
extracted from the game client with Bin Crawler (github.com/wednesdaywoe/CoH-Planner) — see
tools/gamedata/README.md.

Comparison is per (set, piece-count, effect-kind, damage-type). Findings when this was built
(2026-07-06): defense/HP/recovery/recharge/regeneration match the live game exactly. Damage-
buff bonuses differ by a constant ×2.5 — a representation convention (our engine's form,
corpus-validated), NOT drift — so DamageBuff is reported separately and not flagged.

Report-only.  Run:  python tools/reality_check_setbonuses.py
"""
import json
import os
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
import server as srv  # noqa: E402

SNAP = os.path.join(os.path.dirname(__file__), "gamedata", "setbonuses.json")
DMG = {"smashing_dmg", "lethal_dmg", "fire_dmg", "cold_dmg", "energy_dmg",
       "negative_energy_dmg", "psionic_dmg", "toxic_dmg"}
DEFRES = {"smashing", "lethal", "fire", "cold", "energy", "negative", "negative_energy",
          "toxic", "psionic", "melee", "ranged", "aoe"}
DAMAGE_BUFF_FACTOR = 2.5   # known representation convention (game Strength -> our DamageBuff)


def _norm(s):
    """Set-name normalizer matching the snapshot's snake_case keys (apostrophes
    dropped). Without this only single-word set names ever matched — the check
    silently covered 43 values instead of the full data (found 2026-07-08)."""
    s = (s or "").strip().lower().replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def _gkind(attribs, aspect):
    a0 = (attribs[0] if attribs else "").lower()
    asp = (aspect or "").lower()
    dt = a0.replace("_dmg", "").replace("negative_energy", "negative")
    if a0 == "regeneration": return "Regeneration", None
    if a0 == "recovery": return "Recovery", None
    if a0 == "rechargetime": return "RechargeTime", None
    if a0 == "hitpoints": return "HitPoints", None
    if a0 == "tohit": return "ToHit", None
    if a0 == "accuracy" and asp == "strength": return "Accuracy", None
    if a0 in DMG or ("_dmg" in a0 and asp == "strength"): return "DamageBuff", dt
    if a0 in DEFRES and asp == "current": return "Defense", dt
    if a0 in DEFRES and asp == "resistance": return "Resistance", dt
    return None, None


def main():
    game = json.load(open(SNAP, encoding="utf-8"))
    # our bonuses: {(set, pieces, kind, dtype): value}
    ours = {}
    for rec in srv.SET_BONUSES.values():
        nm = _norm(rec["name"])
        for b in rec.get("bonuses", []):
            pc = b.get("pieces_required")
            for e in b.get("effects", []):
                if e.get("effect") and e.get("value"):
                    dt = str(e.get("damage_type") or "").lower().replace("negative_energy", "negative")
                    ours[(nm, pc, e["effect"], dt)] = round(e["value"], 4)

    drift = []
    damage_conv = matched = 0
    for nm, g in game.items():
        for tier in g.get("tiers", []):
            pc = tier["pieces"]
            for e in tier["effects"]:
                kind, dt = _gkind(e["attribs"], e["aspect"])
                if not kind:
                    continue
                gv = round(e["scale"], 4)
                ov = ours.get((nm, pc, kind, dt or ""))
                if ov is None and dt:
                    ov = ours.get((nm, pc, kind, ""))
                if ov is None:
                    continue
                if kind == "DamageBuff":
                    if abs(ov - gv * DAMAGE_BUFF_FACTOR) < max(0.001, 0.03 * gv * DAMAGE_BUFF_FACTOR):
                        damage_conv += 1
                    else:
                        drift.append((nm, pc, kind, dt, ov, gv))
                    continue
                if abs(ov - gv) > max(0.0005, 0.02 * abs(gv)):
                    drift.append((nm, pc, kind, dt, ov, gv))
                else:
                    matched += 1

    print(f"Set-bonus values matched to the live game: {matched} "
          f"(+ {damage_conv} damage-buff at the known x2.5 convention).")
    print(f"REAL DRIFT: {len(drift)}")
    for nm, pc, k, dt, ov, gv in drift[:30]:
        print(f"  {nm:22s} {pc}pc {k}/{dt}: ours={ov} game={gv}")
    if not drift:
        print("Every checkable set bonus matches the live game.")
    return len(drift)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
