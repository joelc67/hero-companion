"""Add the GADGETRY and UTILITY BELT power pools from the game client.

The last two absences the missing-powers check was pinning. Six client records
each, of which five are pickable; the sixth is an auto-issue free rider.

⚠ THE MAPPINGS ARE NOT RE-DERIVED HERE - they are IMPORTED from
add_wind_control, which measured every one of them against the powers we already
hold. Two copies of a mapping table is two things to drift.

WHAT A POOL NEEDS THAT AN ARCHETYPE SET DOES NOT
------------------------------------------------
1. PREREQUISITES, and the client states them outright. Blaster Barrage reads

     Nano_Net Wrist_Blaster && Nano_Net Jetpack && || Wrist_Blaster Jetpack && ||

   which is "any TWO of the three". That is `prereq_count: 2`, and setting it
   matters: `server._prereq_need` prefers the data and falls back to a tier
   proxy, and `_picks_legal` refuses a pool pick whose prerequisites are unmet.
   Counting the distinct sibling powers named in the expression gives the number
   the game enforces, so it is read rather than assumed.

2. THE NEVER-PICKABLE FREE RIDER. Turbo Boost and Athletics carry
   available_level 4294967296 - the auto-issue sentinel, the Afterburner class.
   The game never offers them as a pick, so neither do we; this is the
   documented `Pool.Flight.Fly_Boost` ruling applied again.

3. AN ARCHETYPE GATE. Jetpack's requires excludes Peacebringers and Warshades
   ($archtype @Class_Peacebringer == !). Kheldians have their own flight, and
   the tool has no per-power archetype gate for pool powers, so the exclusion is
   RECORDED on the record and REPORTED - not silently dropped, not faked.

⚠ ONE-PER-BUILD: both pools are origin-themed and were already in
`server._EXCLUSIVE_POOLS`, so the four-pool cap and the one-origin-pool rule
cover them the moment they exist. Checked, not assumed - see the test battery.

⚠ powers.json is COMPACT; powersets.json is indent=1 with CRLF. Match each.
Usage:  python tools/add_origin_pools.py [--check]
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from add_wind_control import (  # noqa: E402  - one source of truth for mappings
    AREA, PTYPE, CAT_ALIAS, CAT_ALSO, BOOST_ALIAS, client_index,
    effects_from, skip_reason, _sec)

POWERS = os.path.join(ROOT, "data", "powers.json")
PSETS = os.path.join(ROOT, "data", "powersets.json")
CATS = os.path.join(ROOT, "data", "set_categories.json")

MARK = "added_from_client"
NEVER_PICKABLE = 4294967295          # and anything above it
POOLS = {"Pool.Gadgetry": "Gadgetry", "Pool.Utility_Belt": "Utility Belt"}
_POWER_REF = re.compile(r"\bPool\.[A-Za-z_]+\.[A-Za-z_]+\b")


def prereq_count(crec, pool):
    """How many OTHER powers of this pool the game demands, from `requires`.

    The expression is RPN and names the siblings that satisfy it; the game's
    rule is "any N of them", and N is what the tier ladder calls the
    prerequisite count. Counting DISTINCT siblings named gives 3 for an
    any-two-of-three expression, so the count is (named - 1).
    """
    req = (crec.get("requires") or "")
    named = {m for m in _POWER_REF.findall(req)
             if m.startswith(pool + ".") and m != crec.get("full_name")}
    if not named:
        return 0
    return max(1, len(named) - 1)


def main():
    check_only = "--check" in sys.argv
    raw = open(POWERS, "rb").read()
    data = json.loads(raw.decode("utf-8"))
    orig = json.loads(raw.decode("utf-8"))
    praw = open(PSETS, "rb").read()
    psets = json.loads(praw.decode("utf-8"))
    porig = json.loads(praw.decode("utf-8"))
    client = client_index()
    sc = json.load(open(CATS, encoding="utf-8"))
    cat_id = {c["name"].lower(): c for c in sc["categories"]}
    enh_id = {c["name"].lower(): c for c in sc["enhancement_classes"]}

    # IDEMPOTENT, on both files and both baselines
    for store in (data, orig):
        for ps in [x for x in store if x in POOLS]:
            del store[ps]
    for store in (psets, porig):
        store["pools"] = [p for p in store.get("pools", [])
                          if p["full_name"] not in POOLS]

    refuse, skipped, made, notes = set(), {}, [], []
    for pool, display in POOLS.items():
        leaves = sorted(f for f in client if f.startswith(pool + "."))
        if not leaves:
            print(f"FAIL: the client has no {pool}")
            sys.exit(1)
        recs = []
        for fn in leaves:
            c = client[fn]
            lvl = int(c.get("available_level") or 0)
            if lvl >= NEVER_PICKABLE:
                notes.append(f"{fn.split('.')[-1]}: auto-issue free rider "
                             f"(available_level {lvl}) - never a pick, so not added")
                continue
            cats, boosts = [], []
            for name in (c.get("allowed_set_categories") or []):
                for ours_name in ([CAT_ALIAS.get(name, name)]
                                  + ([CAT_ALSO[name]] if name in CAT_ALSO else [])):
                    hit = cat_id.get(ours_name.lower())
                    if hit and hit not in cats:
                        cats.append(hit)
                    elif not hit:
                        refuse.add(f"set category {name!r}")
            for name in (c.get("boosts_allowed") or []):
                hit = enh_id.get((BOOST_ALIAS.get(name) or "").lower())
                if hit:
                    boosts.append(hit)
                else:
                    refuse.add(f"boost {name!r}")
            dmg, ctrl, deb, selff, buff, heal = effects_from(c, refuse, skipped)
            need = prereq_count(c, pool)
            rec = {
                "full_name": fn,
                "display_name": c.get("display_name") or fn.split(".")[-1],
                "power_name": fn.split(".")[-1],
                "powerset_full_name": pool,
                "group_name": "Pool",
                "level_available": lvl + 1,
                "power_type": PTYPE.get(c.get("type"), 0),
                "slottable": True,
                "default_slot_count": 1,
                "max_slot_count": 6,
                "accepted_enhancement_type_ids": [b["id"] for b in boosts],
                "accepted_enhancement_types": [b["name"] for b in boosts],
                "accepted_set_category_ids": [x["id"] for x in cats],
                "accepted_set_categories": [x["name"] for x in cats],
                "accepted_set_category_shorts": [x["short"] for x in cats],
                "is_attack": bool(dmg),
                "is_resurrect": False,
                "base_recharge": float(c.get("recharge_time") or 0.0),
                "end_cost": float(c.get("endurance_cost") or 0.0),
                "cast_time": float(c.get("activation_time") or 0.0),
                "activate_period": float(c.get("activate_period") or 0.0),
                "effect_area": AREA.get(c.get("effect_area"), 1),
                "max_targets": int(c.get("max_targets_hit") or 1),
                "radius": float(c.get("radius") or 0.0),
                "range": float(c.get("range") or 0.0),
                "arc": float(c.get("arc") or 0.0),
                "damage_effects": dmg,
                "control_effects": ctrl,
                "debuff_effects": deb,
                "self_effects": selff,
                "buff_effects": buff,
                "heal_effects": heal,
                "summons": [],
                "pet_powersets": [],
                # ⚠ THE GAME STATES IT: read from the requires expression, never
                # left to the tier proxy - `_picks_legal` enforces this number.
                "prereq_count": need,
                MARK: True,
            }
            # an archetype gate the tool cannot express: record and report it
            if "@Class_" in (c.get("requires") or ""):
                gated = sorted(set(re.findall(r"@(Class_\w+)", c["requires"])))
                rec["archetype_excluded"] = gated
                notes.append(f"{fn.split('.')[-1]}: the game bars {', '.join(gated)} "
                             f"- recorded on the record; the tool has no per-power "
                             f"archetype gate for pool powers, so it is REPORTED")
            recs.append(rec)
        recs.sort(key=lambda p: (p["level_available"], p["full_name"]))
        data[pool] = recs
        made.append((pool, recs))
        psets.setdefault("pools", []).append(
            {"full_name": pool, "display_name": display,
             "set_type": "Pool", "archetype_index": -1})
    psets["pools"].sort(key=lambda s: s["display_name"])

    if refuse:
        print("FAIL - refusing to write a partly-understood pool. Unmapped:")
        for r in sorted(refuse):
            print(f"    {r}")
        sys.exit(1)
    for fam, n in sorted(skipped.items(), key=lambda x: -x[1]):
        print(f"STATED EXCLUSION x{n:<4} {fam}: {skip_reason(fam)}")
    for pool, recs in made:
        print(f"{pool}: {len(recs)} pickable powers")
        for r in recs:
            print(f"    L{r['level_available']:<3}{r['display_name']:<18}"
                  f"{'atk' if r['is_attack'] else '   '} prereq={r['prereq_count']} "
                  f"dmg={len(r['damage_effects'])} ctrl={len(r['control_effects'])} "
                  f"deb={len(r['debuff_effects'])} self={len(r['self_effects'])}")
    for n in notes:
        print(f"NOTE: {n}")
    if check_only:
        return

    out = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    probe = json.loads(out.decode("utf-8"))
    for ps in [x for x in probe if x in POOLS]:
        del probe[ps]
    if (json.dumps(probe, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            != json.dumps(orig, separators=(",", ":"), ensure_ascii=False).encode("utf-8")):
        print("INVARIANCE FAILED on powers.json - refusing to write")
        sys.exit(2)
    _CRLF, _LF = b"\r\n", b"\n"
    pout = json.dumps(psets, indent=1, ensure_ascii=False).encode("utf-8")
    pout = pout.replace(_CRLF, _LF).replace(_LF, _CRLF)
    pprobe = json.loads(pout.decode("utf-8"))
    pprobe["pools"] = [p for p in pprobe["pools"] if p["full_name"] not in POOLS]
    if (json.dumps(pprobe, sort_keys=True) != json.dumps(porig, sort_keys=True)):
        print("INVARIANCE FAILED on powersets.json - refusing to write")
        sys.exit(2)
    print("invariance: removing both pools reproduces the baselines exactly")
    for path, payload in ((POWERS, out), (PSETS, pout)):
        with open(path, "wb") as fh:
            fh.write(payload)
    print(f"wrote powers.json ({len(out):,}) and powersets.json ({len(pout):,})")


if __name__ == "__main__":
    main()
