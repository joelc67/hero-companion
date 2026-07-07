"""Pet-entity reconciliation (task #33 step 1) — make the LIVE GAME the source for
pet identity, exactly like the AT-modifier converter did for player classes.

The shipped data/summons.json came from the stale Mids snapshot: entities carry
Mids-era class names (Pets_Soldier -> Class_Minion_Henchman, ranged scale 26.09@50)
while the live client says MastermindPets_Soldier -> Class_Henchman_Minion (11.63) —
per-pet damage more than 2x hot. The snapshot also has no spawn counts and no
durations, so squads and uptime could not be priced at all.

What this does (add-only where possible, never guesses):
1. JOIN by summon-power full name: our power records name the same powers as the
   client's EntCreate templates (tools/gamedata/summons.json). Within one power the
   pet entities match by suffix (Pets_Soldier <-> MastermindPets_Soldier) — ambiguity
   is impossible inside a single power's pet list; anything unmatched is left alone
   and reported.
2. FIX each matched entity's class_name to the live one (critter_classes.json
   entity_class, parsed from villaindef.bin).
3. ADD missing class columns: the live henchman-family classes don't exist in the
   Mids-derived archetypes/modifier tables at all. Each new class gets the next
   column, valued from the client's 105-level arrays at index 49 (= level 50, the
   same convention the tables already use; damage stays in the game's negative-HP
   representation). Tables the class doesn't define get 0.0 — verified exact:
   MM pet attacks use only Melee_Damage/Ranged_Damage, which all four classes carry.
4. WRITE data/summons.json v2 with a new "powers" map:
   power full_name -> {pets: [{uid, count}], duration, permanent, copy_boosts}
   so the engine can finally price squads (Soldiers = 2xSoldier+1xMedic) and uptime
   (Spiderlings 240s; permanent henchmen forever).

Run:  py tools\\gamedata\\convert_pet_entities.py          (report only)
      py tools\\gamedata\\convert_pet_entities.py --write  (apply)
Then: py tools\\gamedata\\reality_check_pets.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data")
GD = os.path.join(ROOT, "tools", "gamedata")

sys.stdout.reconfigure(encoding="utf-8")


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def norm(uid):
    """'Pets_Soldier' / 'MastermindPets_Soldier' -> 'soldier'."""
    low = uid.lower()
    if "pets_" in low:
        low = low.rsplit("pets_", 1)[1]
    return re.sub(r"[^a-z0-9]", "", low)


def main(write=False):
    shipped = _load(os.path.join(DATA, "summons.json"))
    entities = shipped["entities"]
    powers = _load(os.path.join(DATA, "powers.json"))
    auth = _load(os.path.join(GD, "summons.json"))["summons"]
    cc = _load(os.path.join(GD, "critter_classes.json"))
    ent_class, cls_tables = cc["entity_class"], cc["classes"]
    arch_doc = _load(os.path.join(DATA, "archetypes.json"))
    mt_doc = _load(os.path.join(DATA, "modifier_tables.json"))
    tables = mt_doc["tables"]

    existing_cols = {}
    for a in arch_doc["archetypes"]:
        existing_cols.setdefault(a["name"], a.get("column"))   # FIRST wins (dupe trap)

    power_specs, class_fix, conflicts = {}, {}, []
    covered = uncovered = unmatched_app = unmatched_auth = 0
    for ps, plist in powers.items():
        for p in plist:
            uids = p.get("summons") or []
            if not uids:
                continue
            a = auth.get(p.get("full_name"))
            if not a:
                uncovered += 1
                continue
            covered += 1
            auth_pets = a.get("pets") or {}
            by_norm = {}
            for ed in auth_pets:
                by_norm.setdefault(norm(ed), []).append(ed)
            spec = []
            matched_defs = set()
            for uid in uids:
                cands = by_norm.get(norm(uid)) or []
                if len(cands) != 1 and len(uids) == 1 and len(auth_pets) == 1:
                    # one app pet, one client pet, same power: unambiguous by position
                    cands = list(auth_pets)
                if len(cands) != 1:
                    unmatched_app += 1
                    spec.append({"uid": uid, "count": 1})      # engine fallback shape
                    continue
                ed = cands[0]
                matched_defs.add(ed)
                live = ent_class.get(ed)
                entry = {"uid": uid, "count": int(auth_pets[ed])}
                if live:
                    # class rides IN THE POWER SPEC: the same entity uid can be a
                    # Controller pet in one power and a Dominator pet in another
                    entry["class"] = live
                spec.append(entry)
                if live and uid in entities:
                    old = entities[uid].get("class_name")
                    prev = class_fix.get(uid)
                    if prev and prev != live:
                        conflicts.append((uid, prev, live))   # display fallback: first wins
                    elif old != live:
                        class_fix[uid] = live
            unmatched_auth += len(set(auth_pets) - matched_defs)
            power_specs[p["full_name"]] = {
                "pets": spec,
                "duration": a.get("duration"),
                "permanent": bool(a.get("permanent")),
                "copy_boosts": bool(a.get("copy_boosts")),
            }

    # classes referenced by fixes that have NO column yet
    needed = sorted({c for c in class_fix.values() if c not in existing_cols})
    addable = [c for c in needed if c in cls_tables]
    skipped_cls = [c for c in needed if c not in cls_tables]
    # entities whose live class can't get a column stay on their old class
    if skipped_cls:
        class_fix = {u: c for u, c in class_fix.items() if c not in set(skipped_cls)}

    width = len(next(iter(tables.values())))
    print(f"summon powers: {covered} joined to the client, {uncovered} not in the "
          f"client's EntCreate set (left as-is)")
    print(f"entity class fixes: {len(class_fix)}; unmatched app uids: {unmatched_app}; "
          f"client pets with no app entity: {unmatched_auth}; conflicts: {len(conflicts)}")
    print(f"new class columns to add: {addable or 'none'}"
          + (f"; SKIPPED (no client tables): {skipped_cls}" if skipped_cls else ""))
    for uid in ("Pets_Soldier", "Pets_Medic"):
        if uid in class_fix:
            print(f"  {uid}: {entities[uid]['class_name']} -> {class_fix[uid]}")
    sol = power_specs.get("Mastermind_Summon.Mercenaries.Soldiers")
    print(f"  Soldiers spec: {json.dumps(sol)}")

    if not write:
        print("\n(report only — rerun with --write to apply)")
        return

    for i, cls in enumerate(addable):
        col = width + i
        for tname, row in tables.items():
            arr = cls_tables[cls].get(tname)
            row.append(float(arr[49]) if arr and len(arr) > 49 else 0.0)
        template = next(a for a in arch_doc["archetypes"]
                        if a["name"] == "Class_Minion_Pets")
        entry = dict(template)
        entry["name"] = cls
        entry["display_name"] = cls.replace("Class_", "").replace("_", " ")
        entry["column"] = col
        arch_doc["archetypes"].append(entry)
        print(f"added {cls} as column {col}")
    for uid, cls in class_fix.items():
        entities[uid]["class_name"] = cls
    shipped["powers"] = power_specs
    shipped["_source"] = ("entities: Mids snapshot, classes/counts/durations "
                          "reconciled to game client 2026-06-19 "
                          "(tools/gamedata/summons.json + critter_classes.json) by "
                          "convert_pet_entities.py")
    for name, doc in (("summons.json", shipped), ("archetypes.json", arch_doc),
                      ("modifier_tables.json", mt_doc)):
        with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
            json.dump(doc, f)
        print(f"wrote data/{name}")


if __name__ == "__main__":
    main(write="--write" in sys.argv)
