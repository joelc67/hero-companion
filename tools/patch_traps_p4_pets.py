"""Additive patcher: Issue 28 Page 4's Traps PET layer, from the client (model v54).

sync_client_delta synced the Traps POWER records but ignores Create_Entity, so
data/summons.json (the summon specs) stayed pre-Page 4. Maelwys (topic 64761,
2026-10-12) pointed at the symptoms; the official notes (patch-notes r47, Traps)
name every change. Each value below is read from the Page 4 client export:

  Trip Mine (Traps x4 ATs + Blaster Gadgets, "now unified with the Devices Trip
    Mine"): a redirect pseudo-pet whose Self_Destruct fires
    Villain_Pets.Traps_Trip_Mine.Trip_Mine once. No entity, so it uses the
    CASTER's AT modifiers ("Now uses AT modifiers"). The summon record now
    carries the blast itself (rows via the calibrated converter, child groups
    included; radius / area / target cap / accuracy from the blast record), so
    it prices as a PBAoE attack of the caster with its procs firing ("Entities
    that have to die to trigger ... now properly trigger procs"). Interrupt:
    patch_interrupt_times.py (cleared to 0).
  Seeker Drones (Traps x4): two Create_Entity templates per cast, StackThenIgnore
    3 each (max 6 alive). Each drone fires its FlashPulse once and dies. The
    summon record carries the pulse x2 (damage + debuffs; the stun is already on
    it), priced at the drone ENTITY's class column (`damage_class`), and
    `proc_rolls` 2: each drone rolls the slotted procs on its own pulse.
  Force Field Generator: duration 99999 = permanent ("eternal duration").
  Triage Beacon: 90 -> 60 s.
  Caltrops (redirect patch): `at_mods` - the patch prices at the caster's column.
  Entities: `power_tags` from the client (Detonator eligibility: the tag
    `Detonator`, target_requires of Mastermind_Buff.Traps.Detonator).

Refuses to write when a client record does not have the shape described above.

  python tools/patch_traps_p4_pets.py           # report
  python tools/patch_traps_p4_pets.py --write
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sync_client_delta as scd  # noqa: E402

SUMMONS = os.path.join(scd.ROOT, "data", "summons.json")
ATS = ("Controller_Buff", "Corruptor_Buff", "Defender_Buff", "Mastermind_Buff")
AREA_SPHERE = 2


def ents(crec):
    return [(t, g) for g in crec.get("effects") or [] for t in g.get("templates") or []
            if t.get("attribs") == ["Create_Entity"]]


def our_rows(crec):
    """Client record -> our row dicts, by bucket (the calibrated converter)."""
    rows, unmapped = scd.convert(crec)
    out = {}
    for b, cnt in rows.items():
        for core, n in cnt.items():
            k = core if core[0] == b else (b,) + core
            out.setdefault(b, []).extend(scd._row_from(k, {}) for _ in range(n))
    return out


def refuse(msg):
    sys.exit(f"REFUSE: {msg}")


def main():
    write = "--write" in sys.argv
    ax = scd.load_export(scd.AFTER)
    data = json.loads(open(scd.POWERS, "rb").read().decode("utf-8"))
    idx = {q["full_name"]: q for r in data.values() if isinstance(r, list)
           for q in r if isinstance(q, dict)}
    summ = json.load(open(SUMMONS, encoding="utf-8"))
    specs, entities = summ["powers"], summ["entities"]
    log = []

    # -- Trip Mine: the blast moves onto the summon record --------------------
    for fn in [f"{a}.Traps.Trip_Mine" for a in ATS] + ["Blaster_Support.Gadgets.Trip_Mine"]:
        c = ax[fn]
        es = ents(c)
        if len(es) != 1 or es[0][0]["params"].get("entity_def"):
            refuse(f"{fn}: expected one redirect Create_Entity, got {es}")
        sd = next((n for n in es[0][0]["params"]["redirects"] if n.endswith("Self_Destruct")), None)
        blast_name = next((n for t, _ in ents_or_exec(ax[sd]) for n in t["params"]["power_names"]),
                          None) if sd else None
        if blast_name != "Villain_Pets.Traps_Trip_Mine.Trip_Mine":
            refuse(f"{fn}: Self_Destruct fires {blast_name}")
        blast = ax[blast_name]
        rows = our_rows(blast)
        p = idx[fn]
        p["damage_effects"] = rows.get("damage_effects") or refuse(f"{blast_name}: no damage")
        p["control_effects"] = rows.get("control_effects") or p.get("control_effects") or []
        p.update(radius=float(blast["radius"]), effect_area=AREA_SPHERE,
                 max_targets=int(blast["max_targets_hit"]), accuracy=float(blast["accuracy"]),
                 is_attack=True, summons=[], pseudo_pet=blast_name)
        specs.pop(fn, None)
        # the blast's own record too (ours carried pre-client Lethal/Fire rows)
        idx[blast_name]["damage_effects"] = p["damage_effects"]
        log.append(f"TRIP MINE  {fn}: blast {[(d['damage_type'], d['scale'], d['probability']) for d in p['damage_effects']]}"
                   f" r{p['radius']} x{p['max_targets']} acc {p['accuracy']}")

    # -- Seeker Drones: two one-shot pulses per cast ---------------------------
    for a in ATS:
        fn = f"{a}.Traps.Seeker_Drones"
        es = ents(ax[fn])
        defs = {t["params"].get("entity_def") for t, _ in es}
        if len(es) != 2 or len(defs) != 1 or None in defs:
            refuse(f"{fn}: expected 2 templates of one entity, got {defs} x{len(es)}")
        if {(t.get("stack"), t.get("stack_limit")) for t, _ in es} != {("StackThenIgnore", 3)}:
            refuse(f"{fn}: stacking changed")
        ent_name = defs.pop()
        ent = json.load(open(os.path.join(scd.AFTER, "entities", ent_name.lower() + ".json"),
                             encoding="utf-8"))
        pulse = next(n for n in ent["defaults"]["power_full_names"] if n.endswith("FlashPulse"))
        prow = our_rows(ax[pulse])
        p = idx[fn]
        dmg = prow.get("damage_effects") or refuse(f"{pulse}: no damage")
        p["damage_effects"] = [dict(d, scale=round(d["scale"] * 2, 4)) for d in dmg]
        p["debuff_effects"] = prow.get("debuff_effects") or []
        p.update(radius=float(ax[pulse]["radius"]), effect_area=AREA_SPHERE,
                 max_targets=int(ax[pulse]["max_targets_hit"]),
                 accuracy=float(ax[pulse]["accuracy"]), is_attack=True,
                 damage_class="Class_" + ent["defaults"]["character_class_name"].title().replace(" ", "_"),
                 proc_rolls=2, pseudo_pet=pulse, summons=[])
        specs.pop(fn, None)
        log.append(f"SEEKERS    {fn}: 2 x {pulse} {[(d['damage_type'], d['scale']) for d in dmg]}"
                   f" debuffs {len(p['debuff_effects'])} class {p['damage_class']}")

    # -- spec durations / patch modifiers -------------------------------------
    for a in ATS:
        for pw, want in (("Force_Field_Generator", None), ("Triage_Beacon", None)):
            fn = f"{a}.Traps.{pw}"
            dur = scd._sec(ents(ax[fn])[0][0].get("duration"))
            sp = specs.get(fn)
            if sp is None:
                log.append(f"SPEC       {fn}: no summon spec (not a summon-priced pet), skipped")
                continue
            perm = dur >= 99999
            if (sp["duration"], sp["permanent"]) != (dur, perm):
                log.append(f"SPEC       {fn}: duration {sp['duration']} -> {dur}"
                           + (" (permanent)" if perm else ""))
                sp.update(duration=float(dur), permanent=perm)
        fn = f"{a}.Traps.Caltrops"
        if fn in specs and not specs[fn].get("at_mods"):
            specs[fn]["at_mods"] = True
            log.append(f"AT MODS    {fn}: patch priced at the caster's column")

    # -- entity power tags (Detonator eligibility) -----------------------------
    tagged = 0
    edir = os.path.join(scd.AFTER, "entities")
    by_name = {}
    for f in os.listdir(edir):
        if f.endswith(".json") and f != "index.json":
            e = json.load(open(os.path.join(edir, f), encoding="utf-8"))
            by_name[e.get("name")] = e.get("power_tags") or []
    # our uids differ from the client's for henchmen (MastermindPets_Thug_Arsonist is
    # our Pets_Arsonist): pair them through the summon powers both sides share
    alias = {}
    for fn, q in idx.items():
        c, ours = ax.get(fn), list(dict.fromkeys(q.get("summons") or []))
        if not c or not ours:
            continue
        defs = list(dict.fromkeys(t["params"]["entity_def"] for t, _ in ents(c)
                                  if t["params"].get("entity_def")))
        if len(defs) == len(ours):
            for cn, on in zip(defs, ours):
                alias.setdefault(on, set()).add(cn)
    for uid, e in entities.items():
        # the summon-power pairing wins: our Pets_Zombie is BOTH the client's
        # MastermindPets_Zombie (Zombie Horde) and Pets_Zombie (Loa Bone temp power)
        names = alias.get(uid) or {uid}
        found = {tuple(by_name[n]) for n in names if n in by_name}
        if len(found) != 1:
            continue                     # unknown or ambiguous (Fallout variants)
        tags = list(found.pop())
        if tags is not None and e.get("power_tags") != tags:
            e["power_tags"] = tags
            tagged += 1
    log.append(f"TAGS       power_tags set on {tagged} entities "
               f"({sum('Detonator' in (e.get('power_tags') or []) for e in entities.values())} Detonator)")

    print("\n".join(log))
    if write:
        with open(scd.POWERS, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        with open(SUMMONS, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(summ, ensure_ascii=False, separators=(",", ":")))
        print(f"wrote {scd.POWERS} and {SUMMONS}")


def ents_or_exec(crec):
    return [(t, g) for g in crec.get("effects") or [] for t in g.get("templates") or []
            if t.get("attribs") == ["Execute_Power"]]


if __name__ == "__main__":
    main()
