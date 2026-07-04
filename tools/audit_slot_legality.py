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
total_slots = violations = 0
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
    for p in sv["powers"]:
        rec = srv.POWER_BY_FULL.get(p.get("full_name"))
        if not rec:
            continue
        accepted = set(rec.get("accepted_set_category_ids") or [])
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
    print(f"  {at.replace('Class_', ''):12} audited")

print(f"\nset-slotted pieces audited: {total_slots}")
print(f"LEGALITY VIOLATIONS: {violations}")
for at, pw, sn, cat, acc in vio_list[:20]:
    print(f"  ✗ {at}: {pw} ← {sn} (cat {cat}, accepts {acc})")
if not violations:
    print("Every placement respects the game's set-category rules — including inherents.")
