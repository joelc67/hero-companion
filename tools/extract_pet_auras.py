"""Extract the Mastermind PET auras from the client into data/pet_auras.json.

What reaches henchmen beyond the inherited set bonuses (Issue 28 Page 4, live
2026-10-06):
  - Inherent.Inherent.Supremacy: groups gated "group target> MastermindPets eq"
    carry pet +AoE defense ("Area"), +resistance (all 8 types) and +regeneration.
  - ATO globals: slotting Mark of Supremacy F / Command of the Mastermind F (and
    the Superior F) auto-grants Set_Bonus.Global_Bonus.<name> (boostsets.json
    `bonuses[].auto_powers`, requires "<piece> PowerBoostsSlotted> 1 >="), an
    Auto power on MyPet: Mark = +res/+regen, Command = +AoE defense.

GAME DATA ONLY: every number is scale x modifier-table value read from the local
Bin Crawler export (tools/gamedata/bin-crawler/out_full, gitignored). Refuses to
write if a table lacks the Mastermind's class column or a pet template carries an
attribute it cannot place.

  python tools/extract_pet_auras.py           # write data/pet_auras.json
  python tools/extract_pet_auras.py --check   # print, write nothing
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
DEST = os.path.join(ROOT, "data", "pet_auras.json")
MOD = json.load(open(os.path.join(ROOT, "data", "modifier_tables.json"), encoding="utf-8"))["tables"]
# the auras are the MASTERMIND's powers: his class column of each table applies
COL = next(a["column"] for a in json.load(open(os.path.join(ROOT, "data", "archetypes.json"),
                                               encoding="utf-8"))["archetypes"]
           if a["name"] == "Class_Mastermind")
DMG8 = {f"{t}_Dmg" for t in ("Smashing", "Lethal", "Fire", "Cold", "Energy",
                             "Negative_Energy", "Psionic", "Toxic")}
GLOBALS = ("Mark_of_Supremacy", "Command_of_the_Mastermind",
           "Superior_Mark_of_Supremacy", "Superior_Command_of_the_Mastermind")


def _val(table):
    row = MOD.get(table)
    if not row or COL is None or COL >= len(row):
        sys.exit(f"REFUSE: table {table!r} has no Mastermind column")
    return row[COL]


def aura_of(rec, gate=None):
    """{aoe_def, res, regen} from one client record's (optionally gated) groups."""
    out = {"aoe_def": 0.0, "res": 0.0, "regen": 0.0}
    for g in rec.get("effects") or []:
        if g.get("is_pvp") == "PVP_ONLY":
            continue
        req = " ".join(g.get("requires_expression") or [])
        if gate is not None and gate not in req:
            continue
        for t in g.get("templates") or []:
            at, asp = set(t.get("attribs") or []), t.get("aspect")
            v = (t.get("scale") or 0.0) * _val(t.get("table"))
            if at == {"Area"} and asp == "Current":
                out["aoe_def"] += v
            elif at == DMG8 and asp == "Resistance":
                out["res"] += v
            elif at == {"Regeneration"} and asp == "Current":
                out["regen"] += v
            elif at == DMG8 and asp == "Strength":
                continue   # pet +damage: already the Supremacy buff_effects lever
            elif at & ({"Area", "Regeneration"} | DMG8):
                sys.exit(f"REFUSE: unplaced pet template {sorted(at)} {asp} in {rec['full_name']}")
    return {k: round(v, 6) for k, v in out.items()}


def main():
    sup = json.load(open(os.path.join(OUT, "inherent", "inherent", "supremacy.json"), encoding="utf-8"))
    data = {"_source": "client export (Bin Crawler out_full), Issue 28 Page 4; "
                       "tools/extract_pet_auras.py",
            "inherent": {"Class_Mastermind": dict(
                aura_of(sup, "group target> MastermindPets eq"),
                power=sup["full_name"], radius=sup.get("radius"))},
            "pieces": {}}
    sets = json.load(open(os.path.join(OUT, "boostsets.json"), encoding="utf-8"))
    sets = sets if isinstance(sets, list) else list(sets.values())
    for s in sets:
        for b in s.get("bonuses") or []:
            for ap in b.get("auto_powers") or []:
                name = ap.rsplit(".", 1)[-1]
                if not ap.startswith("Set_Bonus.Global_Bonus.") or name not in GLOBALS:
                    continue
                req = b.get("requires") or []
                if "PowerBoostsSlotted>" not in req:
                    sys.exit(f"REFUSE: {ap} granted by an unexpected rule {req}")
                rec = json.load(open(os.path.join(OUT, "set_bonus", "global_bonus",
                                                  name.lower() + ".json"), encoding="utf-8"))
                if "MyPet" not in (rec.get("targets_affected") or []):
                    sys.exit(f"REFUSE: {ap} does not target pets")
                data["pieces"][req[0]] = dict(aura_of(rec), power=ap, radius=rec.get("radius"))
    if len(data["pieces"]) != 4:
        sys.exit(f"REFUSE: expected 4 F pieces (2 sets x attuned/superior), got {sorted(data['pieces'])}")
    print(json.dumps(data, indent=1))
    if "--check" not in sys.argv:
        with open(DEST, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=1)
        print(f"wrote {DEST}")


if __name__ == "__main__":
    main()
