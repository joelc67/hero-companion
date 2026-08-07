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
  2b. DISPLAY-NAME identity inside the candidate sets (added 2026-08-07). Our
     internal names are Mids-derived, the client's are historical and REUSED, so
     the player-facing name is the one thing both sides agree on. Same rung as
     patch_prereq_counts.resolve. It only fires on a UNIQUE unclaimed hit.
  3. explicit RENAMES (documented one-offs the fuzzy pass can't safely reach).
  4. fuzzy basename (difflib >= 0.72) against client powers we don't already hold.
Everything unmatched is classified: inherents (the snapshot omits them) or
ROSTER DIFFS (ours-only powers = stale-roster candidates, the open data question).

⚠ NAME COLLISIONS are the rung nobody had, and the first run found a real
defect nothing else could see. Two of our powers reaching the SAME client
record means one of them is mislabelled, and neither a name check nor a
display check can catch it alone: our Tactical Arrow `Gymnastics` record holds
the client Quickness record's effects (the +25%-to-every-vector defence passive
the game calls Gymnastics) while wearing client Gymnastics' display name AND
header — so the set shows "Oil Slick Arrow" twice, never "Gymnastics", and the
passive carries Oil Slick's 15.6 endurance and 90s recharge instead of 0.13 and
10s. A display-name check passes it (both sides say "Oil Slick Arrow"); a
scalar check passes it (the header matches its name-pair exactly). Only "two of
ours want one of theirs" sees it. Reported, never auto-resolved: which side is
wrong is a data ruling.

Output sections: aliases / inherents_not_in_snapshot / roster_diffs /
name_collisions. reality_check_powers.py consumes the first three.

Run:  python tools/build_power_aliases.py
"""
import difflib
import glob
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
EXPORTS = os.path.join(os.path.dirname(__file__), "gamedata", "bin-crawler",
                       "out_full")

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
# * Tactical Arrow (2026-08-07, Joel's "fix the Tactical Arrow power"): our
#   `Gymnastics` record is the defence passive, which the client keeps under
#   `Quickness` and shows as "Gymnastics"; the client's own `Gymnastics` record
#   is Oil Slick Arrow and pairs with our `Oil_Slick_Arrow`. Proven by effect
#   identity (Melee_Buff_Def 0.25 on all eleven vectors + RechargeTime 0.2),
#   which is what patch_display_name_collisions.py repaired the header from.
#   Pinned here because the same-name match is a coincidence and must lose.
RENAMES = {"Blaster_Support.Tactical_Arrow.Gymnastics":
           "Blaster_Support.Tactical_Arrow.Quickness",
           "Mastermind_Buff.Radiation_Emission.Radiation_Emission":
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


# The residue, each named with the evidence (Joel's "knowing all, not just most"
# rule — an undispositioned diff is a hard failure, never a shrug). These are
# genuine ROSTER differences, not naming: the powers exist on both sides but are
# attached to different records, so aliasing them would hide a real question.
ROSTER_DIFF_DISPOSITIONS = {
    "Mastermind_Pets.Alpha_Wolf_2.Growl":
        "TIER SWAP: the client puts Growl on Alpha_Wolf_3 and Howl on _2; we "
        "have them the other way round. Same power either way — scalars are "
        "identical on both sides (45s / 1.6 cast / 13 end / 15 radius), so this "
        "is placement across the two henchman upgrade tiers, not a value gap.",
    "Mastermind_Pets.Alpha_Wolf_3.Howl":
        "TIER SWAP, the other half of the pair above. Scalars agree except cast "
        "3.67 vs the client's 1.67 — one digit, ordinary drift for sync.",
    "Mastermind_Summon.Beast_Mastery.Pack_Mentality":
        "DIFFERENT RECORD: the client carries Pack Mentality under "
        "Temporary_Powers with radius 60 and two effect templates; ours sits in "
        "Beast_Mastery with radius 30 and no effects at all. Not a rename — the "
        "two records do not describe the same thing, so it stays a question.",
}


def squash(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


# The display name is the only namespace both sides share, so it is compared
# squashed: "Assassin's Whisper" and "Assassins Whisper" are the same power.
_norm_disp = squash


def client_display_index():
    """{client full_name -> squashed display name} from the bin-crawler export.

    The value snapshot (power_values.json) carries scalars only, and the whole
    point of this rung is the name the PLAYER sees, so it has to come from the
    full export. Missing export = an empty index, which simply disables the
    rung rather than crashing the map."""
    out = {}
    for fp in glob.iglob(os.path.join(EXPORTS, "**", "*.json"), recursive=True):
        if os.path.basename(fp).startswith("_"):
            continue
        try:
            rec = json.load(open(fp, encoding="utf-8"))
        except Exception:                                        # noqa: BLE001
            continue
        for r in (rec if isinstance(rec, list) else [rec]):
            if isinstance(r, dict) and r.get("full_name"):
                out[r["full_name"]] = _norm_disp(r.get("display_name"))
    return out


def main():
    snap = json.load(open(SNAP, encoding="utf-8"))
    client_disp = client_display_index()
    print(f"client display-name index: {len(client_disp)} records")
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
            # DISPLAY-NAME identity: the one namespace both sides share.
            ours_disp = _norm_disp((srv.POWER_BY_FULL.get(ours_full) or {})
                                   .get("display_name"))
            if ours_disp:
                claimed = set(aliases.values())
                dhits = [f"{c}.{cb}" for c in cand_names for cb in snap_sets[c]
                         if f"{c}.{cb}" not in claimed
                         and client_disp.get(f"{c}.{cb}") == ours_disp]
                if len(dhits) == 1:
                    aliases[ours_full] = dhits[0]
                    print(f"    display: {b} -> {dhits[0].rsplit('.', 1)[1]}"
                          f"  (both show {ours_disp!r})")
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

    # A pinned RENAME can also correct a power that DOES have a same-name client
    # record, which the loop above never reaches (it only walks powers missing
    # from the snapshot). Tactical Arrow needs exactly that: our `Gymnastics` is
    # the defence passive and the client's `Gymnastics` is Oil Slick Arrow, so
    # the name match is a coincidence and the adjudicated pair must win.
    overrides = 0
    for ours_full, client_full in RENAMES.items():
        if ours_full in player and aliases.get(ours_full) != client_full:
            aliases[ours_full] = client_full
            overrides += 1
            print(f"    rename (pinned, overrides a same-name match): "
                  f"{ours_full} -> {client_full}")

    # NAME COLLISIONS. Every player power that reaches a client record does so
    # either by alias or by having the same full_name; two of ours reaching ONE
    # of theirs means one of our records is mislabelled. See the header note.
    reached = defaultdict(list)
    for p in sorted(player):
        target = aliases.get(p) or (p if p in snap else None)
        if target:
            reached[target].append(p)
    collisions = {t: sorted(v) for t, v in reached.items() if len(v) > 1}
    if collisions:
        print(f"\n⚠ {len(collisions)} NAME COLLISION(S) — two of ours want one "
              f"client record, so one of ours is mislabelled:")
        for t, v in sorted(collisions.items()):
            print(f"    client {t}")
            for p in v:
                d = (srv.POWER_BY_FULL.get(p) or {}).get("display_name")
                print(f"       ours {p}  (shows {d!r})")

    undisposed = [p for p in sorted(roster_diffs)
                  if p not in ROSTER_DIFF_DISPOSITIONS]
    if roster_diffs:
        print(f"\nroster diffs ({len(roster_diffs)}), each with its disposition:")
        for p in sorted(roster_diffs):
            print(f"    {p}\n       {ROSTER_DIFF_DISPOSITIONS.get(p, '*** UNDISPOSITIONED ***')}")
    stale_disp = [p for p in ROSTER_DIFF_DISPOSITIONS if p not in roster_diffs]

    # The denominator is the powers MISSING from the snapshot. A pinned override
    # corrects a power that was never missing, so it is counted apart rather than
    # allowed to inflate the classified total past its own denominator.
    total = sum(len(v) for v in unverified.values())
    classified = len(aliases) - overrides + len(inherents) + len(roster_diffs)
    print(f"\naliased: {len(aliases)}  inherents: {len(inherents)}  "
          f"roster diffs: {len(roster_diffs)}  "
          f"(classified {classified} of {total}"
          f"{f'; +{overrides} pinned override(s) outside the denominator' if overrides else ''})")
    if classified != total:
        print(f"HARD FAIL: {total - classified} power(s) unclassified")
    json.dump({"aliases": aliases,
               "inherents_not_in_snapshot": sorted(inherents),
               "roster_diffs": sorted(roster_diffs),
               "name_collisions": collisions,
               "rename_candidates_awaiting_adjudication": rename_candidates},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {OUT}")
    for p in undisposed:
        print(f"HARD FAIL: roster diff {p} has no disposition — name it in "
              "ROSTER_DIFF_DISPOSITIONS with its evidence, or alias it")
    for p in stale_disp:
        print(f"HARD FAIL: {p} is dispositioned but is no longer a roster diff "
              "— drop its entry in the same change that resolved it")
    return 1 if (undisposed or stale_disp or classified != total) else 0


if __name__ == "__main__":
    sys.exit(main())
