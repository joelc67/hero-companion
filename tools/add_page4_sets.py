"""Add LIGHT AFFINITY and SONIC AURA - the two powersets Homecoming Issue 28 Page 4
(live 2026-10-06) shipped. 9 archetype sets x 9 powers, absent from our data.

Built from the patched live client (the same Bin Crawler export tools/sync_client_delta.py
reads as AFTER) through that tool's calibrated converter - the one that reproduced our
pre-patch records for 93 of 101 changed powers - so a new power is read exactly the way
the reworked ones were. Conventions are MEASURED on our own records, never assumed:

  click self DamageBuff rows  -> mode + host_recharge   (1,762 of 1,762 click mode rows
                                                          are DamageBuff/DDR; v39 duty cycle)
  click Absorb rows           -> host_recharge           (re-arms on the power's recharge)
  every other click self row  -> plain                   (Unstoppable/Elude/Power Surge:
                                                          clicks are not always-on)
  self + team auras           -> buff_effects            (Assault: team rows only)
  heals                       -> self Heal on a self-only power, else buff Heal
  is_attack                   -> exactly "has damage rows"

Prismatic Shield's buffs ride a placed field (Create_Entity, 45s lifetime) whose
aura powers ARE in the client (Redirects.Light_Affinity.SanctuaryPatch_*): they fold
with duration = the field's lifetime (sync_client_delta._field_life), so the
scorer's click uptime prices the time the field is up (2026-10-09).

STATED EXCLUSIONS (printed every run): mode-gated
groups (Radiance's "Radiant" bonuses, Spotlight's Radiance bonus) are skipped the
same way Fury/Domination modes are; combat-suppression bits came from the Mids
database and do not exist for these sets.

REFUSES rather than guesses: an enhancement or set-category name the maps cannot
place aborts the run and names it. Idempotent; invariance-checked like
add_wind_control (removing the new sets must reproduce both files byte-for-byte).

Usage:  python tools/add_page4_sets.py [--check]
"""
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sync_client_delta as sd   # noqa: E402  - ONE converter for patch + new sets

ROOT = sd.ROOT
POWERS = sd.POWERS
PSETS = os.path.join(ROOT, "data", "powersets.json")
MARK = "added_from_client"
TAG = "I28P4"
SETS = {
    "Defender_Buff.Light_Affinity": ("Class_Defender", "primary", "Light Affinity"),
    "Controller_Buff.Light_Affinity": ("Class_Controller", "secondary", "Light Affinity"),
    "Corruptor_Buff.Light_Affinity": ("Class_Corruptor", "secondary", "Light Affinity"),
    "Mastermind_Buff.Light_Affinity": ("Class_Mastermind", "secondary", "Light Affinity"),
    "Tanker_Defense.Sonic_Aura": ("Class_Tanker", "primary", "Sonic Aura"),
    "Brute_Defense.Sonic_Aura": ("Class_Brute", "secondary", "Sonic Aura"),
    "Scrapper_Defense.Sonic_Aura": ("Class_Scrapper", "secondary", "Sonic Aura"),
    "Stalker_Defense.Sonic_Aura": ("Class_Stalker", "secondary", "Sonic Aura"),
    "Sentinel_Defense.Sonic_Aura": ("Class_Sentinel", "secondary", "Sonic Aura"),
}


def _widest_area(c, resolve, depth=0):
    """(effect_area, radius, max_targets) of the widest sub-power this click fires.
    Protective Beam targets ONE ally, but its Defense lands on everyone in 25ft
    through Refracted_ProtectiveBeam - the record must say who the buff reaches."""
    best = (sd.AREA.get(c.get("effect_area"), 1), float(c.get("radius") or 0.0),
            int(c.get("max_targets_hit") or 0))
    if depth >= 3:
        return best
    def scan(gs):
        nonlocal best
        for g in gs or []:
            req = sd._req(g).strip().replace("enttype target> critter eq", "").strip()
            if req:
                continue
            for t in g.get("templates") or []:
                prm = t.get("params") or {}
                names = list(prm.get("power_names") or [])
                if "Create_Entity" in (t.get("attribs") or []):
                    own = float(c.get("recharge_time") or 0.0)
                    names += [n for n in (prm.get("redirects") or [])
                              if resolve.get(n) and (resolve[n].get("type") == "Click" or (
                                  own > 0 and float(resolve[n].get("activate_period") or 0) >= own))]
                for name in names:
                    sub = resolve.get(name)
                    if sub and not name.endswith("_FX"):
                        cand = _widest_area(sub, resolve, depth + 1)
                        if cand[1] > best[1]:
                            best = cand
            scan(g.get("child_effects"))
    scan(c.get("effects"))
    return best


def build_record(fn, c, ps_name, eid, cid, refuse, notes, resolve):
    rows, unmapped = sd.convert(c, resolve)
    for k, n in unmapped.items():
        notes[f"unmapped {k}"] += n
    ptype = sd.PTYPE.get(c.get("type"), 0)
    rech = float(c.get("recharge_time") or 0.0)
    self_only = set(c.get("targets_affected") or []) <= {"Self"}
    out = {b: [] for b in ("damage_effects", "control_effects", "debuff_effects",
                           "self_effects", "buff_effects")}
    for b, cnt in rows.items():
        for k in cnt.elements():
            if b == "heal":
                r = sd._row_from(("buff_effects",) + k[1:], None)
                if self_only:
                    r = sd._row_from(("self_effects",) + k[1:], None)
                    out["self_effects"].append(r)
                else:
                    out["buff_effects"].append(r)
                continue
            r = sd._row_from(k, None)
            if b == "self_effects" and ptype == 0:
                if r["effect"] == "DamageBuff":
                    r.update({"mode": True, "host_recharge": rech, "stack": "Stack",
                              "penalty": False})
                elif r["effect"] == "Absorb":
                    r["host_recharge"] = rech
            out[b].append(r)
    boosts = []
    for name in c.get("boosts_allowed") or []:
        n = sd.BOOST.get(name)
        if n is None or n not in eid:
            if name in ("Hamidon", "Magic", "Natural", "Mutation", "Science", "Technology"):
                continue                       # enhancement ORIGINS, not types
            refuse.add(f"boost {name!r} ({fn})")
            continue
        if n not in boosts:
            boosts.append(n)
    boosts.sort(key=lambda n: eid[n])
    cats = []
    for name in c.get("allowed_set_categories") or []:
        n = sd.CAT.get(name, name)
        if n not in cid:
            refuse.add(f"set category {name!r} ({fn})")
            continue
        if n not in cats:
            cats.append(n)
    cats.sort(key=lambda n: cid[n][0])
    leaf = fn.split(".")[-1]
    area, radius, targets = _widest_area(c, resolve)
    rec = {
        "full_name": fn, "display_name": c.get("display_name") or leaf,
        "power_name": leaf, "powerset_full_name": ps_name,
        "group_name": ps_name.split(".")[0],
        "level_available": int(c.get("available_level") or 0) + 1,
        "power_type": ptype, "slottable": True, "default_slot_count": 1,
        "max_slot_count": 6,
        "accepted_enhancement_type_ids": [eid[n] for n in boosts],
        "accepted_enhancement_types": boosts,
        "accepted_set_category_ids": [cid[n][0] for n in cats],
        "accepted_set_categories": cats,
        "accepted_set_category_shorts": [cid[n][1] for n in cats],
        "self_effects": out["self_effects"],
        "is_attack": bool(out["damage_effects"]),
        "cast_time": float(c.get("activation_time") or 0.0),
        "base_recharge": rech,
        "end_cost": float(c.get("endurance_cost") or 0.0),
        "range": float(c.get("range") or 0.0),
        "activate_period": float(c.get("activate_period") or 0.0),
        "effect_area": area,
        "radius": radius,
        "arc": float(c.get("arc") or 0.0),
        "max_targets": targets,
        "damage_effects": out["damage_effects"],
        "debuff_effects": out["debuff_effects"],
        "buff_effects": out["buff_effects"],
        "control_effects": out["control_effects"],
        "heal_effects": [], "is_resurrect": False, "summons": [], "pet_powersets": [],
        MARK: TAG,
    }
    return rec


def main():
    check_only = "--check" in sys.argv
    raw = open(POWERS, "rb").read()
    data = json.loads(raw.decode("utf-8"))
    orig = json.loads(raw.decode("utf-8"))
    praw = open(PSETS, "rb").read()
    psets = json.loads(praw.decode("utf-8"))
    porig = json.loads(praw.decode("utf-8"))
    # IDEMPOTENT: strip a previous pass from the data AND the baselines
    for d_ in (data, orig):
        for ps in [x for x in d_ if x in SETS]:
            del d_[ps]
    for d_ in (psets, porig):
        for _at, entry in d_.get("by_archetype", {}).items():
            for kind in ("primary", "secondary"):
                if entry.get(kind):
                    entry[kind] = [s for s in entry[kind] if s["full_name"] not in SETS]
    ours = {p["full_name"]: p for v in data.values() for p in v}
    eid, cid = sd._enh_maps(ours)
    print(f"reading client {sd.AFTER}")
    client = sd.load_export(sd.AFTER)
    resolve = dict(client)
    resolve.update(sd.load_redirects(sd.AFTER))     # Execute_Power targets

    refuse, notes, made = set(), Counter(), []
    for ps_name, (at, slot, display) in SETS.items():
        leaves = sorted(f for f in client if f.startswith(ps_name + "."))
        if len(leaves) != 9:
            print(f"FAIL: the client has {len(leaves)} powers in {ps_name}, expected 9")
            sys.exit(1)
        recs = [build_record(fn, client[fn], ps_name, eid, cid, refuse, notes, resolve)
                for fn in leaves]
        recs.sort(key=lambda p: (p["level_available"], p["full_name"]))
        data[ps_name] = recs
        made.append((ps_name, recs))
        entry = psets.setdefault("by_archetype", {}).setdefault(at, {})
        lst = entry.setdefault(slot, [])
        idx = lst[0].get("archetype_index") if lst else 0
        lst.append({"full_name": ps_name, "display_name": display,
                    "set_type": slot.capitalize(), "archetype_index": idx})
        lst.sort(key=lambda s: s["display_name"])

    if refuse:
        print("FAIL - refusing to write a partly-understood powerset. Unmapped:")
        for r in sorted(refuse):
            print(f"    {r}")
        sys.exit(1)
    for k, n in sorted(notes.items(), key=lambda x: -x[1]):
        print(f"STATED EXCLUSION x{n:<4} {k}")
    for ps_name, recs in made:
        print(f"{ps_name}: {len(recs)} powers")
        for r in recs:
            print(f"    L{r['level_available']:<3}{r['display_name']:<22}"
                  f"{['click', 'auto', 'toggle'][r['power_type']] if r['power_type'] < 3 else r['power_type']:<7}"
                  f"{'atk' if r['is_attack'] else '   '} dmg={len(r['damage_effects'])} "
                  f"ctrl={len(r['control_effects'])} deb={len(r['debuff_effects'])} "
                  f"self={len(r['self_effects'])} buff={len(r['buff_effects'])} "
                  f"enh={len(r['accepted_enhancement_types'])} sets={len(r['accepted_set_categories'])}")
    if check_only:
        return

    out = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    probe = json.loads(out.decode("utf-8"))
    for ps in [x for x in probe if x in SETS]:
        del probe[ps]
    if (json.dumps(probe, separators=(",", ":"), ensure_ascii=False)
            != json.dumps(orig, separators=(",", ":"), ensure_ascii=False)):
        print("INVARIANCE FAILED on powers.json - refusing to write")
        sys.exit(2)
    _CRLF, _LF = b"\r\n", b"\n"
    pout = json.dumps(psets, indent=1, ensure_ascii=False).encode("utf-8")
    pout = pout.replace(_CRLF, _LF).replace(_LF, _CRLF)
    pprobe = json.loads(pout.decode("utf-8"))
    for _at, entry in pprobe.get("by_archetype", {}).items():
        for kind in ("primary", "secondary"):
            if entry.get(kind):
                entry[kind] = [s for s in entry[kind] if s["full_name"] not in SETS]
    if (json.dumps(pprobe, separators=(",", ":"), ensure_ascii=False)
            != json.dumps(porig, separators=(",", ":"), ensure_ascii=False)):
        print("INVARIANCE FAILED on powersets.json - refusing to write")
        sys.exit(2)
    print("invariance: removing the new sets reproduces both baselines exactly")
    for _path, _bytes in ((POWERS, out), (PSETS, pout)):
        with open(_path, "wb") as _fh:
            _fh.write(_bytes)
    print(f"wrote powers.json ({len(out):,}) and powersets.json ({len(pout):,})")


if __name__ == "__main__":
    main()
