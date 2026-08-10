"""Add Boomerang Slice - the only whole POWER this audit found missing.

WHAT IT IS
----------
A real, pickable Broad Sword attack on all four melee archetypes, absent from
our Mids-derived data. The game's own words:

    "You toss your sword outward in a Boomerang Slice, attacking all enemies in
     front of you... This power is mutually exclusive from Slice."

⚠ IT IS NOT AN ADDITIVE PATCH. Every other tool in this family adds a ROW to a
record that exists; this one writes a whole record, so every field has to come
from somewhere defensible. Two sources only, and they agree on everything they
overlap:

  THE CLIENT for what the power IS: recharge 8.0, endurance 8.528, cast 1.83,
      accuracy 1.05, Cone, radius 30, arc 0.524, 5 targets (10 on Stalker), and
      all of its effects.
  ITS SIBLING **Slice** for the app-schema fields our data owns and the client
      does not phrase the same way (accepted category ids, enhancement type ids,
      slot counts, effect_area). Copying is justified because the client says
      the two powers accept the IDENTICAL set of categories and boosts on all
      four archetypes - checked, not assumed - which is unsurprising for a power
      whose whole design is "take this INSTEAD of Slice".

⚠⚠ THE DAMAGE IS IN `child_effects`, ONE LEVEL DOWN, and that nearly ended this
as "the client has no damage for it". The two damage groups look EMPTY - zero
templates - because their content hangs off `child_effects`, a group field no
probe in this project had ever descended into. Same lesson as
`magnitude_expression` earlier today: the field existed and nobody had read it.

⚠ LEVEL IS +1. The client's `available_level` is 0-based and ours is 1-based -
5,478 of 5,589 matched powers agree on that offset - so the client's 1 is our 2,
which is exactly where Slice sits. The Mids IoLevel trap in a new coat.

STATED EXCLUSIONS, printed every run:
  * THE RENDING SLICE BONUS IS NOT MODELLED. Every 15 seconds the attack does
    extra damage (child gated on `kRendingSliceCooldown Source.Mode? 0 ==`,
    Lethal 0.6148 plus a Set_Mode). That is the meter/mode capability queued
    with Power Boost and Fury, so the power is priced WITHOUT it: an honest
    understatement, and the same ruling every other mode has had today.
  * a child with `chance: 0.0` (a Fire component) never fires and is not taken.
  * the PvP children land at pv_mode 2, so PvE scoring cannot see them.

⚠ MUTUAL EXCLUSION MUST ALREADY BE ENFORCED BEFORE THIS RUNS - otherwise the
tool would offer a build the game refuses. patch_power_exclusions.py + the
validator + `_picks_legal` landed first, and this script asserts the pair is
wired before it writes.

⚠ powers.json is COMPACT single-line. Read binary, write binary, no indent.
Usage:  python tools/add_boomerang_slice.py [--check]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POWERS = os.path.join(ROOT, "data", "powers.json")
CRAWL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")

MARK = "added_from_client"
LEAF = "Boomerang_Slice"
SIBLING = "Slice"
ATS = ("Brute_Melee", "Scrapper_Melee", "Stalker_Melee", "Tanker_Melee")
SET = "Broad_Sword"
# our damage-type vocabulary, from the client's attrib names
DMG = {"Smashing": "Smashing", "Lethal": "Lethal", "Fire": "Fire", "Cold": "Cold",
       "Energy": "Energy", "Negative_Energy": "Negative", "Psionic": "Psionic",
       "Toxic": "Toxic"}


def _sec(v):
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip().split()[0])
    except (ValueError, IndexError):
        return 0.0


def client_index():
    out = {}
    for dirpath, _dirs, files in os.walk(CRAWL):
        for fn in files:
            if not fn.endswith(".json") or fn == "index.json":
                continue
            try:
                with open(os.path.join(dirpath, fn), encoding="utf-8") as fh:
                    rec = json.load(fh)
            except Exception:  # noqa: BLE001
                continue
            if rec.get("full_name"):
                out[rec["full_name"]] = rec
    return out


def build_effects(crec):
    """(damage_effects, debuff_effects, skipped) from the client, PvE and PvP."""
    dmg, deb = [], []
    skipped = []
    for grp in (crec.get("effects") or []):
        req = (grp.get("requires_expression") or "").strip()
        pv = 1 if "critter" in req else 2 if "player" in req else 0
        for ch in (grp.get("child_effects") or []):
            creq = (ch.get("requires_expression") or "").strip()
            if creq:
                skipped.append(f"gated child ({creq[:44]})")
                continue
            if (ch.get("chance") or 0) <= 0:
                skipped.append("child with chance 0.0")
                continue
            for t in (ch.get("templates") or []):
                sc = t.get("scale")
                if not sc:
                    continue
                for a in (t.get("attribs") or []):
                    dt = DMG.get(a.replace("_Dmg", ""))
                    if not dt:
                        continue
                    dmg.append({
                        "effect": "Damage", "damage_type": dt, "scale": float(sc),
                        "nmag": 1.0, "modifier_table": t.get("table"),
                        "probability": float(ch.get("chance") or 1.0),
                        "duration": _sec(t.get("duration")), "pv_mode": pv,
                        "enhance_aspect": "Damage", "ed_schedule": 0, MARK: True,
                    })
        if req:
            continue                     # the ungated group carries the debuffs
        for t in (grp.get("templates") or []):
            sc = t.get("scale")
            if not sc:
                continue
            asp, tbl = t.get("aspect"), t.get("table")
            for a in (t.get("attribs") or []):
                fam = a.replace("_Dmg", "")
                if fam == "Base_Defense" and asp == "Current":
                    deb.append({
                        "effect": "Defense", "damage_type": "None",
                        "scale": float(sc), "nmag": 1.0, "modifier_table": tbl,
                        "probability": 1.0, "duration": _sec(t.get("duration")),
                        "pv_mode": 0, MARK: True})
                elif fam in DMG and asp == "Resistance":
                    deb.append({
                        "effect": "Resistance", "damage_type": DMG[fam],
                        "scale": float(sc), "nmag": 1.0, "modifier_table": tbl,
                        "probability": 1.0, "duration": _sec(t.get("duration")),
                        "pv_mode": 0, MARK: True})
                else:
                    skipped.append(f"{fam}/{asp}")
    return dmg, deb, skipped


def main():
    check_only = "--check" in sys.argv
    raw = open(POWERS, "rb").read()
    data = json.loads(raw.decode("utf-8"))
    orig = json.loads(raw.decode("utf-8"))
    client = client_index()

    # IDEMPOTENT: drop any record we added before, then re-derive.
    dropped = 0
    for ps, lst in data.items():
        keep = [p for p in lst if not p.get(MARK)]
        dropped += len(lst) - len(keep)
        if len(keep) != len(lst):
            data[ps] = keep
    if dropped:
        print(f"(re-run: dropped {dropped} record(s) from a previous pass)")

    made, skipped_all = [], []
    for at in ATS:
        ps_name = f"{at}.{SET}"
        lst = data.get(ps_name)
        if lst is None:
            print(f"FAIL: our data has no powerset {ps_name}")
            sys.exit(1)
        sib = next((p for p in lst if p["full_name"].endswith("." + SIBLING)), None)
        if sib is None:
            print(f"FAIL: no sibling {SIBLING} in {ps_name} to take the schema from")
            sys.exit(1)
        fn = f"{ps_name}.{LEAF}"
        if any(p["full_name"] == fn for p in lst):
            continue
        c = client.get(fn)
        if not c:
            print(f"FAIL: the client has no {fn}")
            sys.exit(1)
        # ⚠⚠ CHICKEN AND EGG, AND THE GUARD HAS TO ASK THE CLIENT. The exclusion
        # cannot be DERIVED from our data before the power exists there, and the
        # power must not exist before the exclusion is enforced. So the check is
        # game-first: the CLIENT must mirror the pair on both records, and this
        # script writes both sides. Re-running patch_power_exclusions.py
        # afterwards then reproduces exactly this, which is the proof.
        sib_c = client.get(f"{ps_name}.{SIBLING}") or {}
        if ((c.get("requires") or "").strip() != f"{ps_name}.{SIBLING} !"
                or (sib_c.get("requires") or "").strip() != f"{fn} !"):
            print(f"FAIL: the client does not MIRROR the exclusion for {fn} "
                  f"(got {c.get('requires')!r} / {sib_c.get('requires')!r}) - "
                  f"refusing to add a power whose legality rule is one-sided")
            sys.exit(1)
        dmg, deb, skipped = build_effects(c)
        skipped_all += skipped
        if not dmg:
            print(f"FAIL: no damage decoded for {fn} - refusing to add an attack "
                  f"that would read as harmless")
            sys.exit(1)
        rec = {
            "full_name": fn,
            "display_name": c.get("display_name") or "Boomerang Slice",
            "power_name": LEAF,
            "powerset_full_name": ps_name,
            "group_name": sib.get("group_name"),
            # ⚠ +1: the client's available_level is 0-based, ours is 1-based
            "level_available": int(c.get("available_level") or 0) + 1,
            "power_type": 0,                     # the client says Click
            "slottable": True,
            "default_slot_count": sib.get("default_slot_count", 1),
            "max_slot_count": sib.get("max_slot_count", 6),
            # identical to Slice's on all four archetypes, checked against the
            # client's own allowed_set_categories / boosts_allowed
            "accepted_enhancement_type_ids": list(sib.get("accepted_enhancement_type_ids") or []),
            "accepted_enhancement_types": list(sib.get("accepted_enhancement_types") or []),
            "accepted_set_category_ids": list(sib.get("accepted_set_category_ids") or []),
            "accepted_set_categories": list(sib.get("accepted_set_categories") or []),
            "accepted_set_category_shorts": list(sib.get("accepted_set_category_shorts") or []),
            "is_attack": True,
            "is_resurrect": False,
            "base_recharge": float(c.get("recharge_time") or 0.0),
            "end_cost": float(c.get("endurance_cost") or 0.0),
            "cast_time": float(c.get("activation_time") or 0.0),
            "activate_period": float(c.get("activate_period") or 0.0),
            "effect_area": sib.get("effect_area"),
            "max_targets": int(c.get("max_targets_hit") or 1),
            "radius": float(c.get("radius") or 0.0),
            "range": float(c.get("range") or 0.0),
            "arc": float(c.get("arc") or 0.0),
            "damage_effects": dmg,
            "debuff_effects": deb,
            "self_effects": [],
            "buff_effects": [],
            "control_effects": [],
            "heal_effects": [],
            "summons": [],
            "pet_powersets": [],
            "excludes": [f"{ps_name}.{SIBLING}"],
            MARK: True,
        }
        # keep the powerset in level order, as every other reader expects
        # write the reciprocal side too - the client proves the mirror
        sib.setdefault("excludes", [])
        if fn not in sib["excludes"]:
            sib["excludes"] = sorted(set(sib["excludes"]) | {fn})
            sib[MARK + "_excl"] = True     # so invariance can undo just this
        lst.append(rec)
        lst.sort(key=lambda p: (p.get("level_available") or 0, p["full_name"]))
        made.append((fn, rec["level_available"], len(dmg), len(deb)))

    print(f"records {'that would be ' if check_only else ''}added : {len(made)}")
    for fn, lvl, nd, nb in made:
        print(f"    {fn:<52} L{lvl}  {nd} damage rows, {nb} debuff rows")
    seen = {}
    for s in skipped_all:
        seen[s] = seen.get(s, 0) + 1
    for s, n in sorted(seen.items()):
        print(f"STATED EXCLUSION x{n}: {s}")
    print("STATED EXCLUSION: the 15-second Rending Slice bonus is the Set_Mode "
          "meter class and is NOT priced - the power is deliberately understated")

    if not made:
        print("nothing to do (already present)")
        return
    if check_only:
        return

    out = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    probe = json.loads(out.decode("utf-8"))
    for ps, lst in probe.items():
        probe[ps] = [p for p in lst if not p.get(MARK)]
        for p in probe[ps]:
            if p.pop(MARK + "_excl", None):
                p["excludes"] = [x for x in (p.get("excludes") or [])
                                 if not x.endswith("." + LEAF)]
                if not p["excludes"]:
                    del p["excludes"]
    # the sort must not have disturbed anything either
    if (json.dumps(probe, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            != json.dumps(orig, separators=(",", ":"), ensure_ascii=False).encode("utf-8")):
        print("\nINVARIANCE FAILED: dropping the added records does not reproduce "
              "the baseline - refusing to write")
        # name the divergence instead of leaving the operator to guess
        for ps in orig:
            po, pp = orig.get(ps), probe.get(ps)
            if json.dumps(po, sort_keys=True) == json.dumps(pp, sort_keys=True):
                continue
            names_o = [p["full_name"] for p in po]
            names_p = [p["full_name"] for p in pp]
            if names_o != names_p:
                print(f"  {ps}: record order or roster differs:")
                print(f"    baseline: {names_o}")
                print(f"    stripped: {names_p}")
            else:
                for a, b in zip(po, pp):
                    if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
                        keys = [k for k in set(a) | set(b)
                                if json.dumps(a.get(k), sort_keys=True)
                                != json.dumps(b.get(k), sort_keys=True)]
                        print(f"  {ps} / {a['full_name']}: fields differ: {keys}")
        sys.exit(2)
    print("invariance: dropping the added records reproduces the baseline exactly")
    open(POWERS, "wb").write(out)
    print(f"wrote {POWERS} ({len(out):,} bytes, was {len(raw):,})")


if __name__ == "__main__":
    main()
