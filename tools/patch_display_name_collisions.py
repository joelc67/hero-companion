"""Additive patcher: repair a record whose HEADER came from the wrong power.

Joel's ruling, 2026-08-07: "fix the Tactical Arrow power".

The defect, found by the alias map's collision rung (build_power_aliases.py) and
pinned by tools/test_display_name_collisions.py: Blaster Tactical Arrow lists
"Oil Slick Arrow" twice and never lists "Gymnastics". Our `Gymnastics` record
holds the Gymnastics passive's EFFECTS (+25% defence on all eleven vectors via
Melee_Buff_Def, plus RechargeTime 0.2 on Melee_Ones - byte-identical to the
client's Quickness record, which is what the game displays as "Gymnastics"),
but its display name, its costs and part of its slotting vocabulary were
overwritten from the client's Gymnastics record, which the game displays as
"Oil Slick Arrow". So the passive was priced at 90s recharge / 15.6 endurance
instead of 10s / 0.13, and it could not hold a defence set.

Nothing here is hardcoded from my reading of the game. Every replacement value
is re-derived, and each has TWO independent signals:

  scalars + display   the client twin whose EFFECT SIGNATURE matches ours
                      uniquely inside the same powerset. Identity is proven by
                      what the power DOES, which is the one thing the overwrite
                      did not touch.
  set categories      our OWN `accepted_set_category_shorts` survived intact
                      (it still carries 'Defense'), so the correct name/id lists
                      are rebuilt from it using the short -> (name, id) mapping
                      learned from every healthy record in the file - and the
                      result is then CHECKED against the client twin's
                      allowed_set_categories. Disagreement is a hard failure,
                      never a silent preference.

⚠ NOT touched, and each for a reason:
  * level_available - ours is deliberately client+1 (Minerals 24/23, Rock Armor
    1/0 in the same sweep), so 24 against the client's 23 is correct.
  * accepted_enhancement_types - already exactly the client's boosts_allowed
    (Buff_Defense / EnduranceDiscount / SpeedFlying / Jump / Recharge /
    SpeedRunning). The overwrite missed this list.
  * the record's NAME. Internal names are identifiers, never identity (the
    three-namespaces rule); renaming it would break saves for no gain. The
    reconciliation lives in build_power_aliases.RENAMES instead.

Champion exposure is ZERO - no certified build holds this power - so no score
moves and no re-certification is owed. Proven again at the end of this run.

Idempotent: a second run reports 0 to repair. Verify with
  py tools\\test_display_name_collisions.py
  py tools\\reality_check_powers.py

Run:  py tools\\patch_display_name_collisions.py [--write]
"""
import glob
import json
import os
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_display_name_collisions as collisions_battery   # noqa: E402

POWERS_JSON = os.path.join(ROOT, "data", "powers.json")
EXPORTS = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
CHAMPS = os.path.join(ROOT, "benchmarks", "champions.json")

# what the overwrite reaches, and where each value comes from on the client side
SCALARS = [("base_recharge", "recharge_time"), ("cast_time", "activation_time"),
           ("end_cost", "endurance_cost"), ("range", "range")]
# the client names a few categories differently; same map as reality_check_powers
CATMAP = {"Universal Damage Sets": "Universal Damage", "Universal Travel": "Travel",
          "Melee AoE Damage": "PBAoE Damage", "Ranged AoE Damage": "Targeted AoE Damage"}
# the travel-set taxonomy genuinely differs between Mids and the client and is
# not comparable name-for-name (reality_check_powers ignores it for the same
# reason), so the client cross-check is applied to the non-travel half.
TRAVEL = {"Travel", "Run (No Sprint)", "Jump (No Sprint)", "Flight (No Sprint)",
          "Teleport (No Sprint)", "Leaping", "Running", "Leaping & Sprints",
          "Running & Sprints", "Universal Travel", "Flight", "Jumping",
          "Teleportation"}


def load_client():
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
                out[r["full_name"]] = r
    return out


def our_sig(q):
    """(table, scale) multiset of everything the power does. Untouched by the
    overwrite, which is why it can prove identity."""
    return {(e.get("modifier_table"), round(float(e.get("scale") or 0), 4))
            for k in ("self_effects", "buff_effects", "debuff_effects",
                      "damage_effects")
            for e in (q.get(k) or [])}


def client_sig(r):
    return {(t.get("table"), round(float(t.get("scale") or 0), 4))
            for eff in (r.get("effects") or [])
            for t in (eff.get("templates") or [])}


def short_vocabulary(powers):
    """short -> (name, id), learned from every record whose three category lists
    are parallel and self-consistent. A short that maps two ways anywhere is
    dropped rather than guessed."""
    seen = defaultdict(set)
    for plist in powers.values():
        for q in plist:
            n = q.get("accepted_set_categories") or []
            i = q.get("accepted_set_category_ids") or []
            s = q.get("accepted_set_category_shorts") or []
            if len(n) == len(i) == len(s) and n:
                for a, b, c in zip(s, n, i):
                    seen[a].add((b, c))
    return {k: next(iter(v)) for k, v in seen.items() if len(v) == 1}


def main():
    write = "--write" in sys.argv
    powers = json.load(open(POWERS_JSON, encoding="utf-8"))
    client = load_client()
    vocab = short_vocabulary(powers)
    print(f"category vocabulary learned from healthy records: {len(vocab)} shorts")

    # 1. find the collisions: two PICKABLE powers in one set showing one name.
    #    The set of player powersets comes from the BATTERY, not a second copy —
    #    if the two ever disagreed, this would repair records nothing polices.
    #    Pet/redirect/machinery sets reuse display names by design and are out.
    sets = collisions_battery.player_sets()
    targets = []
    for ps, plist in powers.items():
        if ps not in sets:
            continue
        by_disp = defaultdict(list)
        for q in plist:
            if q.get("slottable") and (q.get("display_name") or "").strip():
                by_disp[q["display_name"].strip()].append(q)
        for disp, group in by_disp.items():
            if len(group) > 1:
                targets.append((ps, disp, group))
    print(f"display-name collisions among pickable powers: {len(targets)}")

    repaired = failed = 0
    for ps, disp, group in targets:
        print(f"\n  {ps}: {disp!r} <- {[q['full_name'].rsplit('.', 1)[1] for q in group]}")
        for q in group:
            fn = q["full_name"]
            twin = client.get(fn)
            # 2. does this record's own name-pair actually DO what it does?
            if twin and our_sig(q) and our_sig(q) <= client_sig(twin):
                print(f"     {fn.rsplit('.', 1)[1]}: effects match its own "
                      "name-pair — correctly labelled, left alone")
                continue
            # 3. find the client record in this set whose effects ARE ours
            sig = our_sig(q)
            if not sig:
                continue
            hits = [k for k in client
                    if k.rsplit(".", 1)[0] == ps and sig and sig <= client_sig(client[k])]
            if len(hits) != 1:
                # Not a failure by itself. Plenty of our records legitimately
                # cannot be proven this way — a pseudo-pet fold puts the effects
                # on the summoner while the client keeps them on the entity, so
                # no client record in the set contains them. Only an UNRESOLVED
                # collision is a failure, and that is judged after the pass.
                print(f"     {fn.rsplit('.', 1)[1]}: identity not provable from "
                      f"effects ({len(hits)} client records contain them; a "
                      "pseudo-pet fold looks exactly like this) — left alone")
                continue
            src = client[hits[0]]
            print(f"     {fn.rsplit('.', 1)[1]}: effects prove it is client "
                  f"{hits[0].rsplit('.', 1)[1]!r} (shows {src.get('display_name')!r})")

            changes = {}
            if (q.get("display_name") or "") != (src.get("display_name") or ""):
                changes["display_name"] = src.get("display_name")
            for ours_f, cli_f in SCALARS:
                a, b = q.get(ours_f), src.get(cli_f)
                if a is None or b is None:
                    continue
                if abs(float(a) - float(b)) > max(0.01, 0.02 * abs(float(b))):
                    changes[ours_f] = float(b)

            # 4. categories: rebuild from OUR surviving shorts, then cross-check
            shorts = q.get("accepted_set_category_shorts") or []
            if shorts and all(s in vocab for s in shorts):
                names = [vocab[s][0] for s in shorts]
                ids = [vocab[s][1] for s in shorts]
                want = {CATMAP.get(c, c) for c in
                        (src.get("allowed_set_categories") or [])} - TRAVEL
                got = set(names) - TRAVEL
                if want != got:
                    print(f"     HARD FAIL {fn}: categories rebuilt from our "
                          f"shorts are {sorted(got)} but the client says "
                          f"{sorted(want)} — two signals disagree, not patching")
                    failed += 1
                    continue
                if names != (q.get("accepted_set_categories") or []):
                    changes["accepted_set_categories"] = names
                    changes["accepted_set_category_ids"] = ids
            elif shorts:
                print(f"     note: {fn} has shorts outside the learned "
                      "vocabulary; categories left untouched")

            if not changes:
                print("        already correct (nothing to repair)")
                continue
            for k, v in changes.items():
                print(f"        {k}: {q.get(k)!r} -> {v!r}")
            q.update(changes)
            repaired += 1

        # the collision either survives this pass or it does not — that, not the
        # provability of any one record, is what this tool has to deliver
        still = [q["full_name"].rsplit(".", 1)[1] for q in group
                 if (q.get("display_name") or "").strip() == disp]
        if len(still) > 1:
            print(f"     HARD FAIL: {disp!r} is STILL shown by {still} — the "
                  "collision is unresolved, do not ship this")
            failed += 1
        else:
            print(f"     resolved: the set now shows "
                  f"{sorted({(q.get('display_name') or '').strip() for q in group})}")

    # 5. champion exposure, counted rather than assumed
    champ = json.load(open(CHAMPS, encoding="utf-8"))
    touched = {q["full_name"] for _ps, _d, g in targets for q in g}
    exposure = 0
    for c in champ.values():
        for p in (c.get("picks") or []):
            pn = p if isinstance(p, str) else (p.get("full_name") or "")
            if pn in touched:
                exposure += 1
    print(f"\ncertified-champion exposure across {len(champ)} contexts: "
          f"{exposure} pick(s) — {'no score can move' if not exposure else 'RE-CERT QUESTION'}")

    print(f"\nrepaired {repaired}, hard failures {failed}")
    if failed:
        return 1
    if not repaired:
        print("nothing to write (idempotent)")
        return 0
    if not write:
        print("dry run — pass --write to apply")
        return 0
    # compact, newline-preserving: powers.json ships as one line (CLAUDE.md)
    raw = json.dumps(powers, ensure_ascii=False, separators=(",", ":"))
    with open(POWERS_JSON, "wb") as fh:
        fh.write(raw.encode("utf-8"))
    print(f"wrote {POWERS_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
