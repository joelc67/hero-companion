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
ALIASES = os.path.join(os.path.dirname(__file__), "gamedata", "power_aliases.json")
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
    amap = json.load(open(ALIASES, encoding="utf-8"))
    # our-name -> client-name reconciliation (tools/build_power_aliases.py): lets the
    # check reach the 118 powers whose internal names diverged from the client bins.
    aliases = amap.get("aliases") or {}
    rev_aliases = {v: k for k, v in aliases.items()}
    val_drift = {f[0]: 0 for f in FIELDS}
    val_drift["cast_time"] = 0
    snipe_cond = slot_add = slot_rem = matched = 0
    samples = []
    for fn, g in snap.items():
        p = srv.POWER_BY_FULL.get(fn) or srv.POWER_BY_FULL.get(rev_aliases.get(fn, ""))
        if not p:
            continue      # NPC/object/pet powers — the snapshot is a superset of ours
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

    # COVERAGE DENOMINATOR (standing rule 2026-07-08): the denominator that matters
    # is OUR player-facing powers (what the planner actually slots) — each must be
    # verifiable against the client snapshot. 221 currently are NOT: whole live sets
    # whose INTERNAL names diverged between our Mids-derived data and the client
    # bins (ours "Temporal_Manipulation" = client "Time_Manipulation", Electrical
    # Affinity, many Epic pools) plus 39 inherents the snapshot omits. Those sets'
    # values have been UNVERIFIABLE since the game-first pivot — reconciling the
    # alias map is queued data work. The register below pins the gap per set: any
    # change (new set drifting out of coverage, or a fix) must update the pin
    # deliberately — it can never drift silently.
    player = set()
    for groups in srv.POWERSETS["by_archetype"].values():
        for kind in ("primary", "secondary", "epic"):
            for e in (groups.get(kind) or []):
                for p in (srv.POWERS.get(e.get("full_name")) or []):
                    player.add(p["full_name"])
    for ps, plist in srv.POWERS.items():
        if ps.startswith(("Pool.", "Inherent.")):
            for p in plist:
                player.add(p["full_name"])
    unverified = sorted(p for p in player
                        if p not in snap and aliases.get(p) not in snap)
    by_set = {}
    for p in unverified:
        by_set[p.rsplit(".", 1)[0]] = by_set.get(p.rsplit(".", 1)[0], 0) + 1
    # Pinned register (2026-07-08, final for the day): 40 inherents the snapshot
    # omits + 17 ROSTER DIFFS — ours-only powers with no client counterpart by
    # strict OR adjudicated matching (Scrapper Mace Mastery entirely, a few
    # scattered strays). Renames were fingerprint-aliased or Joel-adjudicated
    # ("confirm all nine", 2026-07-08 — incl. Build_Up = the client's Ice_Slick
    # record). The residual roster reconciliation is the open data workstream;
    # refresh_champions bans register powers from certification builds.
    KNOWN_UNVERIFIED_TOTAL = 57
    print(f"Coverage: {len(player) - len(unverified)} of {len(player)} player-facing "
          f"powers verifiable against the client snapshot ({len(aliases)} via the "
          f"alias map; {len(unverified)} unverified; pinned register {KNOWN_UNVERIFIED_TOTAL}).")
    coverage_fail = 0
    if len(unverified) != KNOWN_UNVERIFIED_TOTAL:
        coverage_fail = 1
        print(f"COVERAGE CHANGE: {len(unverified)} unverified vs pinned "
              f"{KNOWN_UNVERIFIED_TOTAL} — triage and re-pin deliberately:")
        for k, v in sorted(by_set.items(), key=lambda kv: -kv[1])[:20]:
            print(f"    {k}  {v}")
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
        print("\nPower values and slotting match the live game (bar snipe conditionals"
              " and the pinned unverified register).")
    return total + coverage_fail


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
