"""BATTERY: an epic-pool swap can refill itself (server half).

Joel, 2026-08-07: "I had a character I wanted to change the Epic from Electricity
to attain access to Mace Mastery. It took more effort than I thought to implement
the change and have the tool redo my build with that choice."

It was an asymmetry the code stated outright — primary/secondary swaps offered
"switch and rebuild", and "epic keeps the lighter prune-only confirm". MEASURED
before the fix on a real save (Scrapper, Dark -> Energy Mastery): picks 24 -> 22,
added slots 67 -> 65, powers taken from the pool you had just chosen: ZERO.

The client half is the dialog's new "Switch and refill" action. THIS file covers
the server half, which is the part that made the refill useless: /build/autopick
chose its OWN favourite epic pool, and the client then discarded those powers as
belonging to a set the build does not hold. `_pick_epic(force=)` lets the user's
choice decide the pool while the server still decides which powers inside it are
worth taking.

The check that matters most is the FIRST one: force=None must be byte-identical,
because _auto_pick_powers also feeds the wizard and the champion paths, and a
certified score must not move for a UI convenience.

Run:  py tools\\test_epic_swap_refill.py
"""
import itertools
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))

import server as srv                # noqa: E402

CHECKS = []
EXPECTED = 6


def check(name, ok, detail=""):
    CHECKS.append(bool(ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if detail:
        print(f"        {detail}")


def names(res):
    return [fn for (fn, _lvl) in res]


def main():
    print("EPIC SWAP REFILL BATTERY\n")
    ats = [a for a in srv.POWERSETS["by_archetype"]]
    contents = ["general", "itrial", "av", "farm_afk"]
    roles = ["damage", "tank", "buffer", "control"]

    # 1. ABSENT IS BYTE-IDENTICAL — the whole safety case for the change.
    same = total = 0
    for at, c, r in itertools.product(ats, contents, roles):
        total += 1
        if names(srv._pick_epic(at, c, r, "flex")) == \
           names(srv._pick_epic(at, c, r, "flex", force=None)):
            same += 1
    check("force=None reproduces the scored pick exactly", same == total,
          f"{same} of {total} archetype x content x role combinations")

    # 2. FAIL-SAFE: a pool this archetype cannot take is IGNORED, not obeyed —
    #    a bad value degrades to the old behaviour, never an unbuildable build.
    base = names(srv._pick_epic("Class_Defender", "general", "buffer", "flex"))
    bogus = names(srv._pick_epic("Class_Defender", "general", "buffer", "flex",
                                 force="Epic.Not_A_Real_Pool"))
    check("an epic the archetype cannot take falls back to the scored pick",
          base == bogus and bool(base))

    # 3-4. A LEGAL choice is obeyed, and EVERY pick comes from it.
    offered = [e["full_name"] for e in
               (srv.POWERSETS["by_archetype"]["Class_Defender"].get("epic") or [])]
    scored = base[0].rsplit(".", 1)[0]
    alt = next(p for p in offered if p != scored)
    got = names(srv._pick_epic("Class_Defender", "general", "buffer", "flex", force=alt))
    check("the user's pool is honoured over the scored one",
          bool(got) and got != base, f"scored {scored.split('.')[-1]} -> forced {alt.split('.')[-1]}")
    check("...and every pick comes from that pool",
          {f.rsplit(".", 1)[0] for f in got} == {alt},
          ", ".join(f.rsplit(".", 1)[1] for f in got))

    # 5. The route accepts it, so the client can actually reach this.
    c = srv.app.test_client()
    r = c.post("/build/autopick", json={
        "archetype": "Class_Defender", "primary": "Defender_Buff.Poison",
        "secondary": "Defender_Ranged.Sonic_Attack", "content": "general",
        "role": "buffer", "epic": alt}).get_json()
    picked = [p["full_name"] for p in (r or {}).get("powers", [])
              if p["full_name"].startswith("Epic.")]
    check("/build/autopick honours an `epic` in the payload",
          bool(picked) and all(p.startswith(alt + ".") for p in picked),
          f"{len(picked)} epic pick(s): {[p.rsplit('.', 1)[1] for p in picked]}")

    # 6. NEGATIVE CONTROL: with no `epic` in the payload the route is unchanged.
    r2 = c.post("/build/autopick", json={
        "archetype": "Class_Defender", "primary": "Defender_Buff.Poison",
        "secondary": "Defender_Ranged.Sonic_Attack", "content": "general",
        "role": "buffer"}).get_json()
    picked2 = [p["full_name"] for p in (r2 or {}).get("powers", [])
               if p["full_name"].startswith("Epic.")]
    check("NEGATIVE CONTROL: no `epic` in the payload leaves the route's own choice",
          bool(picked2) and not all(p.startswith(alt + ".") for p in picked2),
          f"chose {picked2[0].rsplit('.', 1)[0].split('.')[-1] if picked2 else '(none)'}")

    n, ok = len(CHECKS), sum(CHECKS)
    print(f"\n{ok} of {n} passed ({EXPECTED} expected)")
    return 0 if (ok == n and n == EXPECTED) else 1


if __name__ == "__main__":
    sys.exit(main())
