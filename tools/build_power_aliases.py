"""Build tools/gamedata/power_aliases.json — our power full_names -> client names.

Our power/set INTERNAL names come from the Mids snapshot; the client bins name a
number of sets and powers differently (ours 'Blaster_Support.Temporal_Manipulation'
= client 'Blaster_Support.Time_Manipulation'; Mids 'Radiation_Emission' the-power
= client 'Radiant_Aura'). Without a reconciliation map those powers are
UNVERIFIABLE against the client snapshot (found 2026-07-08 by the coverage-
denominator rule: 221 of 3,987 player-facing powers).

Matching, in order (universal — no per-set hand cases except the RENAMES table):
  1. whole-set alias: same group prefix, client set unknown to our data, ranked by
     roster overlap + set-name similarity (tie-break keeps AT variants honest:
     Def_Flame_Mastery -> DEFENDER_Fire_Mastery, not Corruptor_).
  2. exact power basename within the aliased set.
  3. explicit RENAMES (documented one-offs the fuzzy pass can't safely reach).
  4. fuzzy basename (difflib >= 0.72) against client powers we don't already hold.
Everything unmatched is classified: inherents (the snapshot omits them) or
ROSTER DIFFS (ours-only powers = stale-roster candidates, the open data question).

Output sections: aliases / inherents_not_in_snapshot / roster_diffs.
reality_check_powers.py consumes all three.

Run:  python tools/build_power_aliases.py
"""
import difflib
import json
import os
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
import server as srv  # noqa: E402

SNAP = os.path.join(os.path.dirname(__file__), "gamedata", "power_values.json")
OUT = os.path.join(os.path.dirname(__file__), "gamedata", "power_aliases.json")

# Documented one-off renames (same power, name too different for fuzzy):
# * Mids named MM Radiation Emission's heal after the SET; the client calls it
#   Radiant_Aura (matches every other Rad Emission AT variant).
# * Evasive Maneuvers lives at the client's internal "Afterburner" record (the
#   i27 flight-pool rework reused the record — City of Data keeps the power at
#   pool.flight.afterburner): rosters are congruent (ours lacks Afterburner,
#   the client lacks Evasive_Maneuvers), rech/cast/range identical, end cost
#   rebalanced 0.13 -> 0.052 (flows to sync_power_values as ordinary drift).
# * The nine pairs below were relaxed-fingerprint CANDIDATES adjudicated by Joel
#   ("confirm all nine", 2026-07-08). Evidence per pair in session-report.md:
#   identical client set-categories (functional identity) + identical rech/cast/
#   range with only endurance rebalanced; two were proven by our own records'
#   display names (our Chum_Spray displays "Arctic Breath", our Kinetic_Transfer
#   displays "Fulcrum Shift"). Includes Build_Up = the client's "Ice_Slick"
#   record (still a To-Hit-Buff self click — internal name is misleading).
RENAMES = {"Mastermind_Buff.Radiation_Emission.Radiation_Emission":
           "Mastermind_Buff.Radiation_Emission.Radiant_Aura",
           "Pool.Flight.Evasive_Maneuvers": "Pool.Flight.Afterburner",
           "Controller_Control.Pyrotechnic_Control.Sparkling_Chain":
           "Controller_Control.Pyrotechnic_Control.Sparkling_Field",
           "Dominator_Control.Pyrotechnic_Control.Sparkling_Chain":
           "Dominator_Control.Pyrotechnic_Control.Sparkling_Field",
           "Epic.Dark_Mastery_Controller.Midnight_Grasp":
           "Epic.Controller_Dark_Mastery.Gather_Shadows",
           "Epic.Dark_Mastery_Controller.Umbral_Torrent":
           "Epic.Controller_Dark_Mastery.Torrent",
           "Epic.Dark_Mastery_Dominator.Umbral_Torrent":
           "Epic.Dominator_Dark_Mastery.Torrent",
           "Epic.Ice_Mastery_DefCorr.Build_Up":
           "Epic.Defender_Ice_Mastery.Ice_Slick",
           "Epic.Sentinel_Lev_Mastery.Chum_Spray":
           "Epic.Sentinel_Leviathan_Mastery.Arctic_Breath",
           "Mastermind_Buff.Kinetics.Kinetic_Transfer":
           "Mastermind_Buff.Kinetics.Fulcrum_Shift",
           "Peacebringer_Defensive.Luminous_Aura.Quantum_Maneuvers":
           "Peacebringer_Defensive.Luminous_Aura.Quantum_Acceleration"}


def squash(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def main():
    snap = json.load(open(SNAP, encoding="utf-8"))
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

    unverified = defaultdict(set)
    for p in sorted(player):
        if p not in snap:
            s, base = p.rsplit(".", 1)
            unverified[s].add(base)

    snap_sets = defaultdict(set)
    for fn in snap:
        s, base = fn.rsplit(".", 1)
        snap_sets[s].add(base)

    aliases, inherents, roster_diffs = {}, [], []
    rename_candidates = {}
    for ours_set, bases in sorted(unverified.items()):
        if ours_set.startswith("Inherent."):
            inherents.extend(f"{ours_set}.{b}" for b in sorted(bases))
            continue
        group = ours_set.split(".")[0]
        ours_roster = {p["full_name"].rsplit(".", 1)[1]
                       for p in (srv.POWERS.get(ours_set) or [])}
        # rank candidate client sets: roster overlap + set-name similarity
        cands = []
        if ours_set in snap_sets:
            cands.append((2.0, ours_set))       # same set both sides: renames inside
        for cand, cbases in snap_sets.items():
            if cand == ours_set or not cand.startswith(group + ".") or cand in srv.POWERS:
                continue
            ov = len(ours_roster & cbases) / max(len(ours_roster), 1)
            sim = difflib.SequenceMatcher(None, squash(ours_set), squash(cand)).ratio()
            if ov >= 0.5 or squash(cand) == squash(ours_set):
                cands.append((ov + sim, cand))
        cands.sort(reverse=True)
        cand_names = [c for _, c in cands]
        if cand_names and cand_names[0] != ours_set:
            print(f"SET {ours_set}  ->  {cand_names[0]}")
        for b in sorted(bases):
            ours_full = f"{ours_set}.{b}"
            if ours_full in RENAMES:
                aliases[ours_full] = RENAMES[ours_full]
                print(f"    rename (pinned): {b} -> {RENAMES[ours_full].rsplit('.', 1)[1]}")
                continue
            hit = next((c for c in cand_names if b in snap_sets[c] and c != ours_set), None)
            if hit:
                aliases[ours_full] = f"{hit}.{b}"
                continue
            best, best_r, best_set = None, 0.0, None
            for c in cand_names:
                for cb in snap_sets[c] - ours_roster:
                    r = difflib.SequenceMatcher(None, squash(b), squash(cb)).ratio()
                    if r > best_r:
                        best, best_r, best_set = cb, r, c
            if best_r >= 0.72:
                aliases[ours_full] = f"{best_set}.{best}"
                print(f"    fuzzy: {b} -> {best_set}.{best}  (r={best_r:.2f})")
                continue
            # VALUE FINGERPRINT: an internal-name rename keeps the power's numbers
            # (Power_of_the_Depths = client Call_Depths). STRICT tier only for
            # auto-aliasing — rech/end/cast/range ALL equal + a unique hit.
            # A relaxed tier (end free — a rename + endurance rebalance looks like
            # this) proved able to pair UNRELATED powers on timing coincidences, so
            # it only nominates CANDIDATES for human adjudication (Joel knows the
            # live game; confirmed pairs graduate to the pinned RENAMES table).
            # A REWORK (our Ice Mastery Build_Up vs the client's Ice_Slick) matches
            # neither and stays a roster diff — never silently aliased.
            ours_rec = srv.POWER_BY_FULL.get(ours_full) or {}

            def _match(g, fields):
                return all(abs(float(ours_rec.get(of) or 0) - float(g.get(gf) or 0))
                           <= max(0.01, 0.02 * abs(float(g.get(gf) or 0)))
                           for of, gf in fields)

            STRICT = (("base_recharge", "rech"), ("end_cost", "end"),
                      ("cast_time", "cast"), ("range", "range"))
            RELAXED = (("base_recharge", "rech"), ("cast_time", "cast"),
                       ("range", "range"))

            def _unique_hit(fields):
                hits = []
                for c in cand_names:
                    claimed = {a.rsplit(".", 1)[1] for o, a in aliases.items()
                               if a.rsplit(".", 1)[0] == c}
                    for cb in snap_sets[c] - ours_roster - claimed:
                        if _match(snap.get(f"{c}.{cb}") or {}, fields):
                            hits.append(f"{c}.{cb}")
                return hits[0] if len(hits) == 1 else None

            hit = _unique_hit(STRICT)
            if hit:
                aliases[ours_full] = hit
                print(f"    fingerprint: {b} -> {hit}")
                continue
            cand = _unique_hit(RELAXED)
            if cand:
                rename_candidates[ours_full] = cand
                print(f"    CANDIDATE (needs adjudication): {b} -> {cand}")
            roster_diffs.append(ours_full)

    total = sum(len(v) for v in unverified.values())
    print(f"\naliased: {len(aliases)}  inherents: {len(inherents)}  "
          f"roster diffs: {len(roster_diffs)}  (classified {len(aliases) + len(inherents) + len(roster_diffs)} of {total})")
    json.dump({"aliases": aliases,
               "inherents_not_in_snapshot": sorted(inherents),
               "roster_diffs": sorted(roster_diffs),
               "rename_candidates_awaiting_adjudication": rename_candidates},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
