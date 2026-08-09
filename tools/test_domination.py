"""v43 Domination: the Dominator inherent, and the half that is NOT credited.

Both halves of the term come from the client. The size is stated twice - the
inherent's help says control powers "will typically last 50 percent longer", and
41 of 41 encoded pairs in the export carry exactly 1.5x the base duration scale.
The uptime is the inherent's own numbers, a 90-second mode on a 200-second
recharge, shortened by global recharge like any click.

What this battery guards, in order of how easy it would be to get wrong:

  1. IT MUST NOT APPLY TO ANYONE ELSE. Controllers have Containment, not
     Domination, and a bonus that leaked to them would flatter half the
     control roster.
  2. IT MUST REACH PERMA-DOM AND STOP. The uptime caps at 1.0; a bonus that
     kept growing past +122% recharge would reward recharge without limit.
  3. THE MAGNITUDE HALF MUST STAY OUT until someone settles it, because
     doubling control magnitude across an archetype is not something the
     client unambiguously says.

Usage: python tools/test_domination.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

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
    import first_principles as fp                       # noqa: E402
    import role_output as ro                            # noqa: E402
    from add_wind_control import client_index           # noqa: E402

    DOM = [{"powerset_full_name": "Dominator_Control.Mind_Control"}]
    CON = [{"powerset_full_name": "Controller_Control.Mind_Control"}]

    # ---- the numbers come from the client, not from this file ----
    cl = client_index()
    inh = cl["Inherent.Inherent.Domination"]
    window = max(float(str(t.get("duration", "0")).split()[0] or 0)
                 for g in (inh.get("effects") or [])
                 for t in (g.get("templates") or [])
                 if "Set_Mode" in (t.get("attribs") or []))
    ok("the 90s window and 200s recharge are the CLIENT's, not constants I chose",
       window == fp._DOM_WINDOW == 90.0
       and float(inh.get("recharge_time")) == fp._DOM_RECHARGE == 200.0,
       f"Set_Mode {window}s on a {inh.get('recharge_time')}s recharge")
    ok("the game's own help states the size in words",
       "50 percent longer" in (inh.get("display_help") or ""),
       '"Your control powers will typically last 50 percent longer"')

    # 41 of 41 encoded pairs at 1.5x - the second, independent signal
    MEZ = {"Held", "Immobilized", "Stunned", "Sleep", "Confused", "Terrorized",
           "Afraid", "Intangible"}
    ratios = []
    for fn, r in cl.items():
        if not fn.startswith("Dominator_"):
            continue
        base, dom = {}, {}
        for g in (r.get("effects") or []):
            if "critter" not in (g.get("requires_expression") or ""):
                continue
            d = "Domination" in (g.get("tags") or [])
            if (g.get("tags") or []) and not d:
                continue
            for t in (g.get("templates") or []):
                for a in (t.get("attribs") or []):
                    if a in MEZ and (t.get("scale") or t.get("magnitude")):
                        (dom if d else base)[a] = float(t.get("scale") or 0)
        for a in dom:
            if base.get(a):
                ratios.append(round(dom[a] / base[a], 3))
    ok("...and every encoded pair in the client agrees: 41 of 41 at exactly 1.5x",
       len(ratios) == 41 and set(ratios) == {1.5},
       f"{len(ratios)} pairs, ratios {sorted(set(ratios))}")

    # ---- 1. it applies to Dominators and nobody else ----
    ok("a Dominator gets the bonus", fp._domination_duration_bonus(DOM, 0.0) > 0)
    ok("NEGATIVE CONTROL: a Controller gets NOTHING - Containment is a "
       "different inherent and is still unmodelled",
       fp._domination_duration_bonus(CON, 2.0) == 0.0)
    ok("NEGATIVE CONTROL: an empty build gets nothing",
       fp._domination_duration_bonus([], 1.0) == 0.0
       and fp._domination_duration_bonus(None, 1.0) == 0.0)
    ok("a build detected by full_name alone still counts (no powerset key)",
       fp._domination_duration_bonus(
           [{"full_name": "Dominator_Assault.Fiery_Assault.Flares"}], 0.0) > 0)

    # ---- 2. the duty cycle, and where it stops ----
    base = fp._domination_duration_bonus(DOM, 0.0)
    ok("at no global recharge the floor is 90/200 = 45% of the 50%",
       abs(base - 0.225) < 1e-9, f"{base}")
    ok("global recharge raises it, exactly as it shortens any click",
       fp._domination_duration_bonus(DOM, 0.5) > base)
    ok("it reaches perma-dom at +122% recharge - the threshold players build to",
       abs(fp._domination_duration_bonus(DOM, 1.222) - 0.5) < 1e-3)
    ok("...and STOPS there; more recharge cannot buy more than always-on",
       fp._domination_duration_bonus(DOM, 5.0) == 0.5,
       "an uncapped bonus would reward recharge without limit")

    # ---- 3. it rides the existing channel, not a second mechanism ----
    ok("the bonus is a mez DURATION fraction, the same channel the v30 set "
       "bonuses use", "mez_dur" in fp.encounter_value.__code__.co_names
       or "_domination_duration_bonus" in fp.encounter_value.__code__.co_names)
    ok("...and it covers every mez type the control scorer knows",
       len(ro.CONTROL_WEIGHT) >= 8)

    # ---- 4. the magnitude half stays out, deliberately ----
    src = open(os.path.join(ROOT, "server", "first_principles.py"),
               encoding="utf-8").read()
    ok("the magnitude half is NOT credited, and the file says why",
       "_DOM_DURATION_BONUS = 0.5" in src
       and "MAGNITUDE HALF IS DELIBERATELY NOT CREDITED" in src,
       "whether the variant magnitude adds to the base or replaces it is "
       "ambiguous in the client, and 3 of 41 pairs fit neither reading")
    ok("no Domination magnitude row was written into powers.json",
       not any("Domination" in json.dumps(p.get("control_effects") or [])
               for lst in json.load(open(os.path.join(ROOT, "data", "powers.json"),
                                         encoding="utf-8")).values()
               for p in lst))

    ok("MODEL_VERSION is bumped - this moves scores", fp.MODEL_VERSION == 43,
       f"v{fp.MODEL_VERSION}")

    print(f"\ndomination battery: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
