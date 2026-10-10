"""Additive patcher: AURA PROC PETS (enhancement procs that summon a damage aura).

Issue 28 Page 4 (live 2026-10-06) raised the Dominator ATO procs - Dominating
Grasp: RechargeTime/Fiery Orb and Overpowering Presence: RechargeTime/Energy Font -
to PPM 2 (attuned) / 3 (superior) and gave the pet a 25s life (stack limit 3).
The app carried the piece -> pet link (data/summons.json, Mids snapshot) with
duration 0 and no proc rate, so the pets were never priced.

This writes, per Boosts.<piece> summons entry whose pet runs a periodic damage
aura, a `proc` block from the CLIENT's boost record (out_full/boosts/...):
  ppm          the Create_Entity group's ppm
  life         the Create_Entity template's duration (seconds)
  stack_limit  the template's stack_limit
and the template's level shell as `level_shift` (patch_summon_level_shift rule).
It also adds any pet ENTITY the snapshot lacks (Pets_Dominating_Grasp_Pet) from
the client's villaindef export (bin_crawler.export_entities -> out_entities):
class via tools/gamedata/critter_classes.json, powersets from its power list.

One-shot proc pets (Defender's Bastion, Scourging Blast, Vigilant Assault) get an
`ally_proc` block instead (_ally_proc): heal / +endurance / absorb on friends.

  python tools/patch_proc_pets.py           # report
  python tools/patch_proc_pets.py --write
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUMMONS = os.path.join(ROOT, "data", "summons.json")
POWERS = os.path.join(ROOT, "data", "powers.json")
GD = os.path.join(ROOT, "tools", "gamedata")
OUT = os.path.join(GD, "bin-crawler", "out_full")
ENTS = os.path.join(GD, "bin-crawler", "out_entities")


def _shift(table):
    return 2 if re.search(r"Levelminus2$", table) else 1 if re.search(r"Levelminus$", table) else 0


def _arg(flag):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else None


def _ally_proc(uid, pet, erec, pfns):
    """ONE-SHOT ALLY PROC (Defender's Bastion / Scourging Blast / Vigilant Assault F):
    the piece spawns a 1s pet whose power hits Friends in a radius once (heal,
    +endurance, absorb). Read from the client, never assumed:
      ppm                   the boost's Create_Entity group
      radius / max_targets  the pet power
      heal / end            scale x table; copy_creator_mods=True -> the CREATOR's
                            class column (the engine resolves it at the AT column)
      absorb_hp             `Max.kHitPoints source> F *`: source is the PET (the client
                            writes source.owner> when it means the creator), so F x the
                            pet class's level-50 hit_points from the classes export
                            (--classes DIR, bin_crawler.export_classes)."""
    brec = json.load(open(os.path.join(OUT, "boosts", uid.lower(), uid.lower() + ".json"),
                          encoding="utf-8"))
    ce = [g for g in brec["effects"] for t in g["templates"]
          if "Create_Entity" in t["attribs"] and (t.get("params") or {}).get("entity_def") == pet]
    if len(ce) != 1 or not (ce[0].get("ppm") or 0) > 0:
        sys.exit(f"REFUSE: {uid} Create_Entity groups {len(ce)}")
    fx, radius, maxt = [], None, None
    for f in pfns:
        if f.startswith("Pets.ResistAll"):
            continue
        rec = json.load(open(os.path.join(OUT, *[s.lower() for s in f.split(".")]) + ".json",
                             encoding="utf-8"))
        if "Friend" not in (rec.get("targets_affected") or []):
            sys.exit(f"REFUSE: {f} does not target friends")
        radius, maxt = rec.get("radius"), rec.get("max_targets_hit")
        for g in rec["effects"]:
            for t in g["templates"]:
                at, asp, e = t["attribs"], t["aspect"], t.get("magnitude_expression") or []
                if at == ["Heal_Dmg"] and asp == "Absolute":
                    fx.append({"kind": "heal", "scale": t["scale"], "table": t["table"]})
                elif at == ["Endurance"] and asp == "Current" and t["table"] == "Melee_Ones":
                    fx.append({"kind": "end_frac", "value": t["scale"]})
                elif at == ["Absorb"] and e[:2] == ["Max.kHitPoints", "source>"] and len(e) == 4:
                    cdir = _arg("--classes")
                    if not cdir:
                        sys.exit(f"REFUSE: {f} absorb needs --classes <export_classes dir>")
                    cls = json.load(open(os.path.join(cdir, erec["defaults"]["character_class_name"]
                                                      + ".json"), encoding="utf-8"))
                    hp50 = cls["attribs"]["hit_points"][49]     # index = level - 1
                    fx.append({"kind": "absorb", "value": round(float(e[2]) * hp50, 2),
                               "frac": float(e[2]), "pet_hp50": round(hp50, 2)})
                else:
                    sys.exit(f"REFUSE: unplaced ally-proc template {at} {asp} in {f}")
    if not erec.get("copy_creator_mods"):
        sys.exit(f"REFUSE: {pet} lacks copy_creator_mods; heal column unknown")
    return {"ppm": ce[0]["ppm"], "radius": radius, "max_targets": maxt, "effects": fx} if fx else None


def main():
    write = "--write" in sys.argv
    raw = open(SUMMONS, "rb").read()
    data = json.loads(raw)
    powers = json.load(open(POWERS, encoding="utf-8"))
    sets = {k: v for k, v in powers.items()}
    classes = json.load(open(os.path.join(GD, "critter_classes.json"), encoding="utf-8"))
    classes = classes["entity_class"]          # entity name -> client class
    ents = data["entities"]
    done, skipped, added = [], [], []
    for key, spec in data["powers"].items():
        if not key.startswith("Boosts."):
            continue
        uid = key.split(".")[1]
        pet = spec["pets"][0]["uid"]
        ef = os.path.join(ENTS, pet.lower() + ".json")
        if not os.path.exists(ef):
            sys.exit(f"REFUSE: no client entity export for {pet} (run bin_crawler.export_entities)")
        erec = json.load(open(ef, encoding="utf-8"))
        pfns = erec["defaults"]["power_full_names"]
        auras = [p for ps in {f.rsplit(".", 1)[0] for f in pfns} for p in sets.get(ps, [])
                 if p["full_name"] in pfns and p.get("damage_effects")
                 and (p.get("activate_period") or 0) > 0 and (p.get("power_type") or 0) != 0]
        if not auras:
            ap = _ally_proc(uid, pet, erec, pfns)
            if ap:
                spec["ally_proc"] = ap
                done.append(f"{uid}: {pet} ally proc {ap}")
            else:
                skipped.append(f"{uid} ({pet}: no damage aura and no ally effect)")
            continue
        brec = json.load(open(os.path.join(OUT, "boosts", uid.lower(), uid.lower() + ".json"),
                              encoding="utf-8"))
        ce = [(g, t) for g in brec["effects"] for t in g["templates"]
              if "Create_Entity" in t["attribs"]
              and (t.get("params") or {}).get("entity_def") == pet]
        if len(ce) != 1:
            sys.exit(f"REFUSE: {uid} has {len(ce)} Create_Entity templates for {pet}")
        g, t = ce[0]
        life = float(str(t["duration"]).split()[0])
        if not (g.get("ppm") or 0) > 0 or life <= 0:
            sys.exit(f"REFUSE: {uid} ppm={g.get('ppm')} life={life}")
        spec["proc"] = {"ppm": g["ppm"], "life": life, "stack_limit": t.get("stack_limit") or 1}
        spec["duration"] = life
        spec["level_shift"] = _shift(t.get("table") or "")
        done.append(f"{uid}: {pet} ppm {g['ppm']} life {life}s stack {spec['proc']['stack_limit']}")
        if pet not in ents:
            cls = classes.get(pet)
            if not cls:
                sys.exit(f"REFUSE: no client class for {pet}")
            names = erec.get("levels", [{}])[0].get("display_names") or [pet]
            ents[pet] = {"display_name": names[0] or pet, "class_name": cls,
                         "powerset_full_names": sorted({f.rsplit(".", 1)[0] for f in pfns
                                                        if not f.startswith("Pets.ResistAll")}),
                         "upgrade_powers": []}
            added.append(f"{pet} -> {ents[pet]}")
    for d in done:
        print("  PROC PET  " + d)
    for a in added:
        print("  ENTITY+   " + a)
    for s in skipped:
        print("  EXCLUDED  " + s)
    if write:
        out = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        with open(SUMMONS, "w", encoding="utf-8", newline="\n") as f:
            f.write(out)
        print(f"wrote {SUMMONS}")


if __name__ == "__main__":
    main()
