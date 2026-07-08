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
    """Set-name normalizer applied to BOTH sides (snapshot keys carry their own
    quirks, e.g. 'gaussians_synchronized_fire-control'). Without this only
    single-word set names ever matched — the check silently covered 43 values
    instead of the full data (found 2026-07-08)."""
    s = (s or "").strip().lower().replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def _squash(s):
    """Separator-free form — fallback that reconciles 'timespace_manipulation'
    (snapshot) with 'Time & Space Manipulation' (ours)."""
    return _norm(s).replace("_", "")


# The snapshot's own key spellings that differ from the game set's real name —
# a reconciliation table for the extract, NOT data drift.
_SNAP_ALIASES = {"debiliative_action": "debilitative_action"}


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
    # KNOWN MODEL GAP (stated, not hidden): the game's 11 heal-strength set bonuses
    # (Numina 4pc +6% heal etc., attrib Heal_Dmg/Strength) are untracked — the
    # engine has no Heal-strength stat yet. Same class of gap as the 2026-07-08
    # Accuracy find; queued for v29 (adding it mid-refresh would shift champion
    # scores). Counted and printed separately so it can never silently vanish.
    if a0 == "heal_dmg":
        return "UNTRACKED_HEAL", None
    # An X_Dmg attrib is DamageBuff only at aspect Strength — at aspect Resistance
    # it IS typed resistance (Bonesnap 2pc Fire_Dmg/Resistance = +1.5% fire res).
    # Misrouting those to DamageBuff hid 224 checkable resistance values.
    if a0 in DMG or "_dmg" in a0:
        if asp == "strength": return "DamageBuff", dt
        if asp == "resistance": return "Resistance", dt
        return None, None
    if a0 in DEFRES and asp == "current": return "Defense", dt
    if a0 in DEFRES and asp == "resistance": return "Resistance", dt
    return None, None


def main():
    game = json.load(open(SNAP, encoding="utf-8"))
    # our bonuses: {(set, pieces, kind, dtype): value} — keyed by BOTH the normalized
    # and the squashed set name so every snapshot key resolves. A global-kind effect
    # stores damage_type "None"; normalize that to "" (the game side has no dtype
    # there) — this mismatch silently skipped every recharge/HP/regen/accuracy bonus.
    ours = {}
    for rec in srv.SET_BONUSES.values():
        for b in rec.get("bonuses", []):
            pc = b.get("pieces_required")
            for e in b.get("effects", []):
                if e.get("effect") and e.get("value"):
                    dt = str(e.get("damage_type") or "").lower().replace("negative_energy", "negative")
                    if dt in ("none", "special"):
                        dt = ""
                    for nm in {_norm(rec["name"]), _squash(rec["name"])}:
                        ours[(nm, pc, e["effect"], dt)] = round(e["value"], 4)

    drift = []
    missing = []
    damage_conv = matched = expected = untracked_heal = 0
    for gkey, g in game.items():
        nm = _norm(_SNAP_ALIASES.get(gkey, gkey))
        if not any(k[0] == nm for k in ours):
            nm = _squash(gkey)
        for tier in g.get("tiers", []):
            pc = tier["pieces"]
            for e in tier["effects"]:
                kind, dt = _gkind(e["attribs"], e["aspect"])
                if not kind:
                    continue
                if kind == "UNTRACKED_HEAL":
                    untracked_heal += 1
                    continue
                expected += 1
                gv = round(e["scale"], 4)
                ov = ours.get((nm, pc, kind, dt or ""))
                if ov is None and dt:
                    ov = ours.get((nm, pc, kind, ""))
                if ov is None:
                    # COVERAGE (standing rule 2026-07-08): a game bonus we can map
                    # but don't HOLD is a data hole, not a skip — this exact silent
                    # `continue` hid the 65 missing accuracy bonuses for a day.
                    missing.append((nm, pc, kind, dt, gv))
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

    covered = matched + damage_conv + len(drift)
    print(f"Coverage: {covered} of {expected} mappable game set-bonus effects found in our data.")
    print(f"KNOWN UNTRACKED: {untracked_heal} heal-strength bonuses "
          f"(no Heal stat in the model yet — queued v29, see _gkind comment).")
    print(f"Set-bonus values matched to the live game: {matched} "
          f"(+ {damage_conv} damage-buff at the known x2.5 convention).")
    print(f"REAL DRIFT: {len(drift)}")
    for nm, pc, k, dt, ov, gv in drift[:30]:
        print(f"  {nm:22s} {pc}pc {k}/{dt}: ours={ov} game={gv}")
    print(f"MISSING FROM OUR DATA: {len(missing)}")
    for nm, pc, k, dt, gv in missing[:30]:
        print(f"  {nm:22s} {pc}pc {k}/{dt}: game={gv}, ours=ABSENT")
    if not drift and not missing:
        print("Every mappable game set bonus is present and matches the live game.")
    return len(drift) + len(missing)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
