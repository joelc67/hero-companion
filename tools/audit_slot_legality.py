"""Audit slot LEGALITY of generated builds: every slotted set piece must belong to
a set category the power actually accepts (the game's TypeGrades rule — same table
the in-game slotting UI enforces). Covers regular sets, uniques, procs, winter/ATO,
and inherents (Health/Stamina accept Healing / EndMod sets legitimately).

Run:  python tools/audit_slot_legality.py
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
import server as srv

COMBOS = [
    ("Class_Blaster", "Blaster_Ranged.Fire_Blast", "Blaster_Support.Fire_Manipulation"),
    ("Class_Defender", "Defender_Buff.Poison", "Defender_Ranged.Sonic_Attack"),
    ("Class_Scrapper", "Scrapper_Melee.Martial_Arts", "Scrapper_Defense.Super_Reflexes"),
    ("Class_Tanker", "Tanker_Defense.Invulnerability", "Tanker_Melee.Super_Strength"),
    ("Class_Controller", "Controller_Control.Earth_Control", "Controller_Buff.Storm_Summoning"),
    ("Class_Mastermind", "Mastermind_Summon.Demon_Summoning", "Mastermind_Buff.Radiation_Emission"),
]

c = srv.app.test_client()
total_slots = violations = solved = 0
vio_list = []
for at, pri, sec in COMBOS:
    ap = c.post("/build/autopick", json={"archetype": at, "primary": pri, "secondary": sec,
                                         "role": "damage", "content": "general"}).get_json()
    if not ap.get("ok", True) or not ap.get("powers"):
        print(f"  ! autopick failed for {at}")
        continue
    sv = c.post("/build/solve", json={"archetype": at, "powers": ap["powers"],
                                      "goal": "general play", "tier": "premium",
                                      "content": "general", "role": "damage",
                                      "preserve": False}).get_json()
    if not sv.get("ok"):
        print(f"  ! solve failed for {at}: {str(sv)[:120]}")
        continue
    solved += 1
    for p in sv["powers"]:
        rec = srv.POWER_BY_FULL.get(p.get("full_name"))
        if not rec:
            continue
        accepted = set(rec.get("accepted_set_category_ids") or [])
        seen_pieces = set()
        for s in (p.get("slots") or []):
            if not s or not s.get("set_uid"):
                continue          # empty or common IO / HO (no set category)
            total_slots += 1
            srec = srv.SET_BY_UID.get(s["set_uid"])
            cat = srec.get("category_id") if srec else s.get("category_id")
            if cat is not None and cat not in accepted:
                violations += 1
                vio_list.append((at.replace("Class_", ""), rec.get("display_name"),
                                 s.get("set_name"), cat, sorted(accepted)))
            # In-game rule: a SET piece appears at most once per power (field
            # report 2026-07-09 — the manual picker allowed repeats; the
            # solver never should, and now the audit proves it). HO/D-Sync
            # uids never reach here (no set_uid on those slots).
            pid = s.get("piece_uid") or s.get("piece_name")
            if pid and not str(pid).startswith(("Hamidon_", "Titan_", "Hydra_",
                                                "DSync_", "Dsync_")):
                if pid in seen_pieces:
                    violations += 1
                    vio_list.append((at.replace("Class_", ""), rec.get("display_name"),
                                     f"DUPLICATE piece {pid}", "-", []))
                seen_pieces.add(pid)
    print(f"  {at.replace('Class_', ''):12} audited")

# PINNED VALIDATION SELF-CHECK (field report 2026-07-09): the legality layer
# must ERROR on a duplicated set piece and stay SILENT on stacked HOs — both
# pinned here so the audit can't pass while validation sleeps.
pin_pass = 0
PIN_EXPECT = 2
dup_build = {"archetype": "Class_Scrapper", "powers": [{
    "full_name": "Pool.Fighting.Weave", "power_type": 2,
    "slots": [{"set_uid": "Luck_of_the_Gambler", "set_name": "Luck of the Gambler",
               "piece_uid": "Crafted_Luck_of_the_Gambler_A",
               "piece_name": "Defense", "io_level": 50},
              {"set_uid": "Luck_of_the_Gambler", "set_name": "Luck of the Gambler",
               "piece_uid": "Crafted_Luck_of_the_Gambler_A",
               "piece_name": "Defense", "io_level": 50}]}]}
v = c.post("/build/validate", json=dup_build).get_json() or {}
if any("won't allow a set piece" in e for e in v.get("errors", [])):
    pin_pass += 1
else:
    print("  ✗ PIN: duplicate set piece did NOT produce a validation error")
ho_build = {"archetype": "Class_Scrapper", "powers": [{
    "full_name": "Scrapper_Melee.Martial_Arts.Storm_Kick", "power_type": 0,
    "slots": [{"set_uid": "Hamidon_Origin", "set_name": "Hamidon Origin",
               "piece_uid": "Hamidon_Damage_Accuracy",
               "piece_name": "Nucleolus Exposure"},
              {"set_uid": "Hamidon_Origin", "set_name": "Hamidon Origin",
               "piece_uid": "Hamidon_Damage_Accuracy",
               "piece_name": "Nucleolus Exposure"}]}]}
v = c.post("/build/validate", json=ho_build).get_json() or {}
if not any("won't allow" in e for e in v.get("errors", [])):
    pin_pass += 1
else:
    print("  ✗ PIN: stacked identical HOs wrongly flagged as duplicates")

# COVERAGE DENOMINATOR (standing rule 2026-07-08): a failed autopick/solve used to
# just print '!' and shrink the audit — it could pass on ZERO builds.
print(f"\n{solved} of {len(COMBOS)} expected builds solved; "
      f"set-slotted pieces audited: {total_slots}; "
      f"validation pins: {pin_pass} of {PIN_EXPECT}")
print(f"LEGALITY VIOLATIONS: {violations}")
for at, pw, sn, cat, acc in vio_list[:20]:
    print(f"  ✗ {at}: {pw} ← {sn} (cat {cat}, accepts {acc})")
if solved < len(COMBOS):
    print(f"COVERAGE FAILURE: only {solved} of {len(COMBOS)} builds audited.")
    sys.exit(1)
if pin_pass < PIN_EXPECT:
    print(f"PIN FAILURE: {pin_pass} of {PIN_EXPECT} validation pins passed.")
    sys.exit(1)
if not violations:
    print("Every placement respects the game's set-category rules — including "
          "inherents — and no set piece repeats within a power.")
sys.exit(1 if violations else 0)
