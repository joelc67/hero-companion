"""BATTERY: no two PICKABLE powers in one powerset share a display name.

Found 2026-08-07 by the alias map's new collision rung. Blaster Tactical Arrow
shows "Oil Slick Arrow" TWICE and never shows "Gymnastics":

  ours .Gymnastics        holds the client Quickness record's effects - +25%
                          defence on all 11 vectors (Melee_Buff_Def) plus
                          RechargeTime 0.2 (Melee_Ones), which is the Gymnastics
                          passive - but wears client Gymnastics' display name
                          AND header (90s recharge, 15.6 end, 70 range).
                          The real one is 10s / 0.13 end.
  ours .Oil_Slick_Arrow   is the genuine Oil Slick click (the slow debuffs), and
                          pairs with the client's Gymnastics record.

Neither a name check nor a display check can see it - both sides say "Oil Slick
Arrow" and the header matches its name-pair exactly. Only "two of ours want one
of theirs" catches it. It reaches the player: the picker offers the same name
twice, and whoever takes the passive is charged Oil Slick's endurance.

⚠ It is ALLOWED here, not fixed. Correcting it edits a shipped power's endurance
cost and recharge, which is a data ruling and Joel's call. Champion exposure is
ZERO (no certified build holds it), so nothing is owed until he rules.

This battery exists so a SECOND one cannot appear unnoticed. New collision =
hard fail with both records named.

Run:  py tools\\test_display_name_collisions.py
"""
import os
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))

import server as srv                # noqa: E402

# Known and adjudicated. key -> why it is here.
ALLOWED = {
    ("Blaster_Support.Tactical_Arrow", "Oil Slick Arrow"):
        "our Gymnastics record wears Oil Slick's name and header while holding "
        "the Gymnastics passive's effects - open data ruling, zero champion "
        "exposure",
}


def player_sets():
    """The powersets a player actually picks from: primary/secondary/epic + pools.
    Incarnate/pet/temp machinery legitimately reuses display names and is not a
    surface anyone browses, so it is out of scope by construction."""
    sets = set()
    for groups in srv.POWERSETS["by_archetype"].values():
        for kind in ("primary", "secondary", "epic"):
            for e in (groups.get(kind) or []):
                if e.get("full_name"):
                    sets.add(e["full_name"])
    sets.update(ps for ps in srv.POWERS if ps.startswith("Pool."))
    return sets


def main():
    print("DISPLAY-NAME COLLISION BATTERY\n")
    sets = player_sets()
    found = {}
    powers = 0
    for ps in sorted(sets):
        by_disp = defaultdict(list)
        for p in (srv.POWERS.get(ps) or []):
            if not p.get("slottable"):
                continue          # hidden machinery is never offered to anyone
            disp = (p.get("display_name") or "").strip()
            if disp:
                powers += 1
                by_disp[disp].append(p["full_name"].rsplit(".", 1)[1])
        for disp, names in by_disp.items():
            if len(names) > 1:
                found[(ps, disp)] = sorted(names)

    print(f"  {len(sets)} player powersets, {powers} pickable powers checked")
    ok = True
    for key, names in sorted(found.items()):
        ps, disp = key
        if key in ALLOWED:
            print(f"  KNOWN  {ps}: {disp!r} <- {names}\n         {ALLOWED[key]}")
        else:
            ok = False
            print(f"  FAIL   NEW COLLISION {ps}: {disp!r} <- {names}")
            print("         Two pickable powers show one name. Find which record "
                  "holds which power's effects before touching either.")
    stale = [k for k in ALLOWED if k not in found]
    for ps, disp in stale:
        ok = False
        print(f"  FAIL   allowlisted collision {ps}/{disp!r} is GONE - if it was "
              "fixed, delete its ALLOWED entry in the same change")

    print(f"\n  {len(found)} collision(s), {len(ALLOWED)} allowed, "
          f"{len(found) - len([k for k in found if k in ALLOWED])} unexpected")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
