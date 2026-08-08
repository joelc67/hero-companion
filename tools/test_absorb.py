"""v42 absorb: faithful data, two numbers kept apart, and a live sustain term.

The traps this pins, each paid for while building it:
  * a CLICK's self rows are dropped from totals, so the absorb row has to be
    admitted beside the v39 mode buffs - without that a correct back-fill
    measures 0.0 through the real route (it did, twice, for two different
    reasons: this one and power_type).
  * the pool and the sustain value are DIFFERENT QUESTIONS and must never be
    added: a 401.6 HP shield on a 120-second recharge is worth 3.35 HP/s, and
    crediting the pool itself would score it as permanently up.
  * only heal-table absorb has known units. A literal 1.0 on a *_Ones table
    cannot be one hit point, so 19 records are pinned, not guessed.
  * absorb is point-valued (the `_POINT_HP` rule) - never formatted as a percent.

Usage: python tools/test_absorb.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))

PASS = FAIL = 0


def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}")
    if detail:
        print(f"        {detail}")


def main():
    import server as srv          # noqa: E402
    import first_principles as fp  # noqa: E402

    powers = json.load(open(os.path.join(ROOT, "data", "powers.json"), encoding="utf-8"))
    by = {p["full_name"]: p for _ps, lst in powers.items() for p in lst}
    rows = {fn: [e for e in (p.get("self_effects") or []) if e.get("absorb_row")]
            for fn, p in by.items()}
    carried = {fn for fn, r in rows.items() if r}

    PS = "Scrapper_Defense.Radiation_Armor.Particle_Shielding"
    MB = "Sentinel_Defense.Super_Reflexes.Master_Brawler"

    ok("back-fill covers the 6 heal-table absorb powers", len(carried) == 6,
       f"{len(carried)}: {sorted(x.split('.')[-1] for x in carried)}")
    ps = rows[PS]
    ok("Particle Shielding carries the client's 3.0 on Melee_HealSelf",
       len(ps) == 1 and ps[0]["scale"] == 3.0
       and ps[0]["modifier_table"] == "Melee_HealSelf")
    ok("...enhanced through the Absorb aspect, which is how a Heal IO reaches it",
       ps[0]["enhance_aspect"] == "Absorb",
       "Crafted_Heal boosts Heal, HitPoints, Regeneration AND Absorb - writing "
       "\"Heal\" here looks right and enhances nothing")
    ok("...and carries its own cadence for the sustain maths",
       ps[0]["host_recharge"] == 120.0 and ps[0]["duration"] == 60.0)
    ok("Master Brawler took ONE row, not both PvE/PvP groups",
       len(rows[MB]) == 1 and rows[MB][0]["scale"] == 4.0)

    # ---- NEGATIVE CONTROLS: what must NOT have been taken ----
    ok("NEGATIVE CONTROL: the units-unknown *_Ones absorb was not taken "
       "(Bio Armor's Ablative Carapace)",
       not rows.get("Scrapper_Defense.Bio_Organic_Armor.Ablative_Carapace"))
    ok("NEGATIVE CONTROL: ally-targeted absorb was not taken (Spirit Ward)",
       not rows.get("Pool.Sorcery.Spirit_Ward"))
    ok("NEGATIVE CONTROL: a heal power gained no absorb row",
       not rows.get("Scrapper_Defense.Radiation_Armor.Radiation_Therapy"))

    # ---- LIVE, through the real route ----
    c = srv.app.test_client()

    def calc(names, at, slots=None):
        pw = [{"full_name": n, "slots": slots or [None],
               "slotCount": len(slots or [None])} for n in names]
        return c.post("/build/calculate",
                      json={"archetype": at, "powers": pw}).get_json()

    def bx(r, k):
        return ((r.get("bonus_extras") or {}).get(k) or {}).get("value")

    base = ["Scrapper_Melee.Martial_Arts.Thunder_Kick"]
    a, b = calc(base, "Class_Scrapper"), calc(base + [PS], "Class_Scrapper")
    ok("v42: the shield REACHES the totals at the resolved point value",
       bx(a, "absorb") == 0.0 and abs(bx(b, "absorb") - 401.6) < 0.2,
       f"{bx(a, 'absorb')} -> {bx(b, 'absorb')} HP  (3.0 x Melee_HealSelf 133.86)")
    ok("...and its SUSTAIN value is the pool over the cadence, not the pool",
       abs(bx(b, "absorb_hps") - 3.35) < 0.02,
       f"{bx(b, 'absorb_hps')} HP/s = 401.6 / 120s recharge")
    t = calc(["Tanker_Melee.Battle_Axe.Chop",
              "Tanker_Defense.Radiation_Armor.Particle_Shielding"], "Class_Tanker")
    ok("...the archetype column moves it, as it must",
       abs(bx(t, "absorb") - 562.2) < 0.2, f"Tanker {bx(t, 'absorb')} HP")
    s = calc(["Sentinel_Ranged.Fire_Blast.Flares", MB], "Class_Sentinel")
    ok("Master Brawler: a bigger pool on a shorter cadence is worth more",
       abs(bx(s, "absorb") - 481.9) < 0.2 and abs(bx(s, "absorb_hps") - 8.03) < 0.02,
       f"{bx(s, 'absorb')} HP / 60s = {bx(s, 'absorb_hps')} HP/s")
    ok("NEGATIVE CONTROL: a build with no absorb power reads 0.0 both ways",
       bx(a, "absorb") == 0.0 and bx(a, "absorb_hps") == 0.0)

    # ---- slotting moves both numbers, in the right direction each ----
    heal = [{"piece_uid": "Crafted_Heal", "level": 50}]
    rech = [{"piece_uid": "Crafted_Recharge", "level": 50}]
    h = calc(base + [PS], "Class_Scrapper", slots=heal)
    r = calc(base + [PS], "Class_Scrapper", slots=rech)
    ok("a HEAL enhancement grows the shield itself",
       bx(h, "absorb") > bx(b, "absorb") + 1,
       f"{bx(b, 'absorb')} -> {bx(h, 'absorb')} HP")
    ok("a RECHARGE enhancement leaves the pool alone and raises the sustain "
       "(it re-arms sooner)",
       abs(bx(r, "absorb") - bx(b, "absorb")) < 0.01
       and bx(r, "absorb_hps") > bx(b, "absorb_hps") + 0.05,
       f"pool {bx(r, 'absorb')}, hps {bx(b, 'absorb_hps')} -> {bx(r, 'absorb_hps')}")

    # ---- the scorer consumes it ----
    src = open(os.path.join(ROOT, "server", "first_principles.py"),
               encoding="utf-8").read()
    ok("first_principles subtracts absorb from incoming, beside regen and heals",
       "incoming - regen_hps - self_heal_hps - absorb_hps" in src)
    ok("...reading it from bonus_extras, never the curated top level",
       'get("bonus_extras") or {}).get("absorb_hps")' in src)
    ok("MODEL_VERSION moved with the scoring change", fp.MODEL_VERSION == 42,
       f"MODEL_VERSION = {fp.MODEL_VERSION}")

    # ---- the recharge-aspect fix that rode along, and its mechanical guard ----
    import engine  # noqa: E402
    aspects = {b["aspect"] for v in (srv.PIECE_BOOSTS or {}).values() for b in v}
    ok("the recharge aspect the engine asks for EXISTS in the served vocabulary",
       engine._RECH_ASPECT in aspects,
       f"_RECH_ASPECT={engine._RECH_ASPECT!r}; 'Recharge' present: "
       f"{'Recharge' in aspects} - three sites asked for that name and no piece "
       f"has ever carried it")
    eng = open(os.path.join(ROOT, "server", "engine.py"), encoding="utf-8").read()
    ok("...and no site spells it the dead way any more",
       '"Recharge", 0' not in eng and 'asp == "Recharge"' not in eng)
    rech3 = [{"piece_uid": "Crafted_Recharge", "level": 50}] * 3
    rage = "Brute_Melee.Super_Strength.Rage"
    plain = calc(["Brute_Melee.Super_Strength.Punch", rage], "Class_Brute")
    slot = calc(["Brute_Melee.Super_Strength.Punch", rage], "Class_Brute", slots=rech3)
    ok("recharge slotting now reaches a mode buff's duty cycle",
       (slot.get("damage_buff") or 0) > (plain.get("damage_buff") or 0) + 0.2,
       f"Rage damage_buff {plain.get('damage_buff')} -> {slot.get('damage_buff')}")

    # ---- exposure, counted not assumed ----
    ch = json.load(open(os.path.join(ROOT, "benchmarks", "champions.json"),
                        encoding="utf-8"))
    hit = [k for k, v in ch.items()
           if any((p.get("full_name") if isinstance(p, dict) else p) in carried
                  for p in (v.get("picks") or []))]
    ok("champion exposure is ZERO, so no certified score moved", not hit,
       f"{len(ch)} contexts checked, {len(hit)} hold an absorb power")

    print(f"\nabsorb battery: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
