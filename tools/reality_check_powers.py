"""Reality-check our POWER data (values + set-slotting) against authoritative game data.

Companion to reality_check_gamedata.py (which does archetype modifiers). Compares our
powers to a compact snapshot of the current game values in tools/gamedata/power_values.json
(full_name -> recharge / endurance / cast / range / allowed set categories). The snapshot is
refreshed from the current game client with Bin Crawler (github.com/wednesdaywoe/CoH-Planner)
— see tools/gamedata/README.md.

Report-only: it lists what drifted so a human can review before applying. It bakes in the
two traps we mapped:

  * Cast time: snipes store the FAST/conditional cast in the game data (activation_time
    ~1.3 with a to-hit condition). A large our>game cast gap is that mechanic, NOT drift —
    reported separately, never treated as a value to copy.
  * Set-category names: the game names a few categories differently ("Universal Damage Sets"
    vs our "Universal Damage", "Melee/Ranged AoE Damage" vs "PBAoE/Targeted AoE Damage").
    Normalized before comparison; the travel-set taxonomy differs and is ignored.

Set BONUS values are NOT in the extract (the set data exposes slottable-power lists and
rarity only), so they are not checked here.

Run:  python tools/reality_check_powers.py
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
import server as srv  # noqa: E402

SNAP = os.path.join(os.path.dirname(__file__), "gamedata", "power_values.json")
CATMAP = {"Universal Damage Sets": "Universal Damage", "Universal Travel": "Travel",
          "Melee AoE Damage": "PBAoE Damage", "Ranged AoE Damage": "Targeted AoE Damage"}
TRAVEL = {"Travel", "Run (No Sprint)", "Jump (No Sprint)", "Flight (No Sprint)",
          "Teleport (No Sprint)", "Leaping", "Running", "Leaping & Sprints",
          "Running & Sprints", "Universal Travel", "Flight", "Jumping", "Teleportation"}
FIELDS = [("base_recharge", "rech"), ("end_cost", "end"), ("range", "range")]


def _cats(cats):
    return {CATMAP.get(c, c) for c in (cats or [])} - TRAVEL


def main():
    snap = json.load(open(SNAP, encoding="utf-8"))
    val_drift = {f[0]: 0 for f in FIELDS}
    val_drift["cast_time"] = 0
    snipe_cond = slot_add = slot_rem = matched = 0
    samples = []
    for fn, g in snap.items():
        p = srv.POWER_BY_FULL.get(fn)
        if not p:
            continue
        matched += 1
        for of, gf in FIELDS:
            ov, gv = p.get(of), g.get(gf)
            if ov is None or gv is None:
                continue
            if abs(float(ov) - float(gv)) > max(0.01, 0.02 * abs(float(gv))):
                val_drift[of] += 1
        ov, gv = p.get("cast_time"), g.get("cast")
        if ov is not None and gv is not None and abs(float(ov) - float(gv)) > 0.02:
            if float(ov) - float(gv) > 1.0:
                snipe_cond += 1
            else:
                val_drift["cast_time"] += 1
        gc, oc = _cats(g.get("cats")), _cats(p.get("accepted_set_categories"))
        add, rem = gc - oc, oc - gc
        slot_add += len(add)
        slot_rem += len(rem)
        if (add or rem) and len(samples) < 15:
            samples.append(f"  {fn.split('.', 1)[-1]:34s} +{sorted(add)} -{sorted(rem)}")

    total = sum(val_drift.values()) + slot_add
    print(f"Reality-checked {matched} powers against current game data.")
    print(f"VALUE drift: {val_drift}")
    print(f"SLOTTING drift: +{slot_add} categories the game allows and we don't, "
          f"-{slot_rem} we allow and the game doesn't (minus travel-set taxonomy)")
    print(f"snipe conditional cast-times (expected, not drift): {snipe_cond}")
    if samples:
        print("\nslotting samples:")
        for s in samples:
            print(s)
    if not total:
        print("\nPower values and slotting match the live game (bar snipe conditionals).")
    return total


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
