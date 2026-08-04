"""Remove the 31 set-slotting categories the game does not allow (2026-08-04).

reality_check_powers found 31 categories across 23 power records that OUR data
offers and the game client refuses. Verified GAME-FIRST twice before this
patch existed: the July-7 Bin Crawler snapshot AND a fresh 2026-08-04 partial
re-export from C:\\Games\\HC2\\assets\\live agree on every record (23/23) —
including the odd-looking ones (the client really does give Lightning Clap the
damage-aura categories and Lightning Field the stun/KB ones; the game enforces
what its records say, so the planner must offer exactly that). Champion
exposure measured before patching: ZERO slots use a removed category on these
powers — no movers, no recert.

Additive-patcher family rules apply: binary read/write, the file's own compact
serialization (round-trip identity asserted BEFORE any write), coverage
denominator (exactly 31 removals on 23 records, hard-fail otherwise), and a
reconstruction check — re-inserting every removal at its recorded position
must reproduce the original file byte-for-byte.

Idempotent: a second run finds 0 of 31 remaining and exits 0 changing nothing.
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.join(os.path.dirname(__file__), "..")
POWERS = os.path.join(ROOT, "data", "powers.json")

# (power full_name, [category names to remove]) — the bins-verified list.
REMOVALS = {
    "Blaster_Support.Electricity_Manipulation.Lightning_Clap": ["Knockback", "Stuns"],
    "Blaster_Support.Electricity_Manipulation.Lightning_Field": [
        "Blaster Archetype Sets", "Endurance Modification", "Healing",
        "PBAoE Damage", "Universal Damage"],
    "Blaster_Support.Tactical_Arrow.Gymnastics": ["Defense Sets"],
    "Brute_Defense.Dark_Armor.Soul_Transfer": ["Brute Archetype Sets"],
    "Brute_Melee.Electrical_Melee.Chain_Induction": ["Melee Damage"],
    "Brute_Melee.Fiery_Melee.Breath_of_Fire": ["Targeted AoE Damage"],
    "Controller_Control.Gravity_Control.Gravity_Distortion_Field": [
        "Targeted AoE Damage", "Universal Damage"],
    "Controller_Control.Mind_Control.Total_Domination": [
        "Targeted AoE Damage", "Universal Damage"],
    "Mastermind_Summon.Necromancy.Zombie_Horde": ["Accurate Healing", "Healing"],
    "Scrapper_Defense.Dark_Armor.Soul_Transfer": ["Scrapper Archetype Sets"],
    "Scrapper_Melee.Electrical_Melee.Chain_Induction": ["Melee Damage"],
    "Scrapper_Melee.Fiery_Melee.Breath_of_Fire": ["Targeted AoE Damage"],
    "Sentinel_Defense.Dark_Armor.Soul_Transfer": ["Sentinel Archetype Sets"],
    "Stalker_Defense.Dark_Armor.Soul_Transfer": ["Stalker Archetype Sets"],
    "Stalker_Defense.Ninjitsu.Smoke_Flash": ["Threat Duration"],
    "Stalker_Defense.Shield_Defense.Battle_Agility": ["Defense Sets"],
    "Stalker_Defense.Shield_Defense.Deflection": ["Resist Damage"],
    "Stalker_Defense.Willpower.Resurgence": ["Endurance Modification"],
    "Stalker_Melee.Electrical_Melee.Chain_Induction": ["Melee Damage"],
    "Stalker_Melee.Fiery_Melee.Breath_of_Fire": ["Targeted AoE Damage"],
    "Tanker_Defense.Dark_Armor.Soul_Transfer": ["Tanker Archetype Sets"],
    "Tanker_Defense.Energy_Aura.Energy_Drain": ["Threat Duration"],
    "Tanker_Melee.Electrical_Melee.Chain_Induction": ["Melee Damage"],
}
EXPECTED_TOTAL = 31


def main():
    raw = open(POWERS, "rb").read()
    data = json.loads(raw)
    compact = json.dumps(data, ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
    if compact != raw:
        print("ABORT: powers.json does not round-trip byte-identically with the "
              "compact serializer — refusing to write anything.")
        return 1

    # category name -> id, from the data's own table (never a second copy)
    cats = json.load(open(os.path.join(ROOT, "data", "set_categories.json"),
                          encoding="utf-8"))
    name_to_id = {}
    entries = cats if isinstance(cats, list) else cats.get("categories") or []
    for c in entries:
        if isinstance(c, dict) and c.get("name"):
            name_to_id[c["name"]] = c.get("id")

    removed = []          # (full_name, cat_name, name_index, id, id_index)
    seen_powers = 0
    for plist in data.values():
        for p in plist:
            wants = REMOVALS.get(p.get("full_name"))
            if not wants:
                continue
            seen_powers += 1
            names = p.get("accepted_set_categories") or []
            ids = p.get("accepted_set_category_ids") or []
            for cat in wants:
                if cat not in names:
                    continue        # already removed (idempotent re-run)
                ni = names.index(cat)
                names.pop(ni)
                cid = name_to_id.get(cat)
                ii = ids.index(cid) if cid in ids else None
                if ii is not None:
                    ids.pop(ii)
                removed.append((p["full_name"], cat, ni, cid, ii))

    if not removed:
        print(f"Nothing to do — all {EXPECTED_TOTAL} categories already removed "
              f"({seen_powers} of {len(REMOVALS)} records seen). OK.")
        return 0
    if seen_powers != len(REMOVALS) or len(removed) != EXPECTED_TOTAL:
        print(f"ABORT: expected {EXPECTED_TOTAL} removals on {len(REMOVALS)} "
              f"records, found {len(removed)} on {seen_powers} — powers.json "
              "shape changed; re-verify against the bins before patching.")
        return 1

    # Reconstruction check: putting every removal back must reproduce the file.
    recon = json.loads(json.dumps(data))
    by_full = {p["full_name"]: p for pl in recon.values() for p in pl
               if p.get("full_name") in REMOVALS}
    for full, cat, ni, cid, ii in reversed(removed):
        rp = by_full[full]
        rp["accepted_set_categories"].insert(ni, cat)
        if ii is not None:
            rp["accepted_set_category_ids"].insert(ii, cid)
    if json.dumps(recon, ensure_ascii=False,
                  separators=(",", ":")).encode("utf-8") != raw:
        print("ABORT: reconstruction mismatch — the removal is not clean; "
              "nothing written.")
        return 1

    with open(POWERS, "wb") as f:
        f.write(json.dumps(data, ensure_ascii=False,
                           separators=(",", ":")).encode("utf-8"))
    print(f"Removed {len(removed)} of {EXPECTED_TOTAL} game-refused categories "
          f"across {seen_powers} of {len(REMOVALS)} records; reconstruction "
          "check passed before write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
