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
# Mids named MM Radiation Emission's heal after the SET; the client calls it
# Radiant_Aura (matches every other Rad Emission AT variant).
RENAMES = {"Mastermind_Buff.Radiation_Emission.Radiation_Emission":
           "Mastermind_Buff.Radiation_Emission.Radiant_Aura"}


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
            # (Power_of_the_Depths = client Call_Depths). If exactly ONE unclaimed
            # client power in the candidate sets shares rech/end/cast/range, treat
            # it as the same power renamed. A REWORK (our Ice Mastery Build_Up vs
            # the client's Ice_Slick) fingerprints differently and stays a roster
            # diff — those must never be silently aliased.
            ours_rec = srv.POWER_BY_FULL.get(ours_full) or {}
            fp_hits = []
            for c in cand_names:
                claimed = {a.rsplit(".", 1)[1] for o, a in aliases.items()
                           if a.rsplit(".", 1)[0] == c}
                for cb in snap_sets[c] - ours_roster - claimed:
                    g = snap.get(f"{c}.{cb}") or {}
                    same = all(
                        abs(float(ours_rec.get(of) or 0) - float(g.get(gf) or 0))
                        <= max(0.01, 0.02 * abs(float(g.get(gf) or 0)))
                        for of, gf in (("base_recharge", "rech"), ("end_cost", "end"),
                                       ("cast_time", "cast"), ("range", "range")))
                    if same:
                        fp_hits.append(f"{c}.{cb}")
            if len(fp_hits) == 1:
                aliases[ours_full] = fp_hits[0]
                print(f"    fingerprint: {b} -> {fp_hits[0]}")
            else:
                roster_diffs.append(ours_full)

    total = sum(len(v) for v in unverified.values())
    print(f"\naliased: {len(aliases)}  inherents: {len(inherents)}  "
          f"roster diffs: {len(roster_diffs)}  (classified {len(aliases) + len(inherents) + len(roster_diffs)} of {total})")
    json.dump({"aliases": aliases,
               "inherents_not_in_snapshot": sorted(inherents),
               "roster_diffs": sorted(roster_diffs)},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
