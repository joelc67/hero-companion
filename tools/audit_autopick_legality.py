"""AUDIT: every archetype's autopick proposal must be LEGAL IN THE GAME.

WHY THIS EXISTS (2026-07-30). The Crab Spider Soldier context reported
"score NONE — every evaluation failed" on every leg of every wave, and was
carried as a named defect for days on a wrong hypothesis (a 26-pick seed, or
the prereq counts). The real cause: autopick proposed BOTH members of a VEAT
base-vs-branch twin pair — Frag Grenade AND CS Frag Grenade, Venom Grenade AND
CS Venom Grenade. The game treats each pair as ONE power that upgrades when the
Soldier branches to Crab, so `_picks_legal` refuses a build holding both. The
seed could never be made legal, so no amount of solving could rescue it.

The knowledge already existed in `_VEAT_DUPLICATE_PAIRS`; the legality GATE
consulted it and the PICKER did not. That is the shape of the bug, and it is
why this audit checks the picker's output against the gate for EVERY archetype
rather than just the one that was reported (Joel's universal-rules doctrine: a
game-rule fix is implemented archetype-independently and proven with an all-AT
audit).

Autopick feeds the wizard, so an illegal proposal is user-facing, not merely a
certification problem.

Coverage denominator: every playable archetype x every (primary, secondary)
pairing the game allows, x the contents champions are certified for. Hard-fails
on any illegal proposal.

Run:  py tools\\audit_autopick_legality.py [--contents itrial,team] [--verbose]
"""
import importlib.util as ilu
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = ilu.spec_from_file_location("cohserver", os.path.join(ROOT, "server", "server.py"))
srv = ilu.module_from_spec(spec)
spec.loader.exec_module(srv)

VERBOSE = "--verbose" in sys.argv
CONTENTS = ["itrial"]
if "--contents" in sys.argv:
    CONTENTS = sys.argv[sys.argv.index("--contents") + 1].split(",")

# VEAT sets pair by BRANCH -- cross-branch pairs are impossible in game.
_VEAT_PAIR = {"Arachnos_Soldier": "Training_and_Gadgets",
              "Bane_Spider_Soldier": "Bane_Spider_Training",
              "Crab_Spider_Soldier": "Crab_Spider_Training",
              "Widow_Training": "Teamwork",
              "Night_Widow_Training": "Widow_Teamwork",
              "Fortunata_Training": "Fortunata_Teamwork"}


def combos():
    for a in srv.PLAYABLE:
        at = a["name"]
        ps = srv.POWERSETS["by_archetype"].get(at) or {}
        for pri in ps.get("primary", []):
            pfn = pri["full_name"] if isinstance(pri, dict) else pri
            for sec in ps.get("secondary", []):
                sfn = sec["full_name"] if isinstance(sec, dict) else sec
                pb, sb = pfn.rsplit(".", 1)[-1], sfn.rsplit(".", 1)[-1]
                if pb in _VEAT_PAIR and _VEAT_PAIR[pb] != sb:
                    continue
                yield at, pfn, sfn


def negative_control():
    """Prove this audit can still go RED.

    A green checker that cannot fail is the worst kind (smoke_gold once printed
    FAIL and exited 0 forever). So before trusting 2,691 passes, hand the gate a
    build that deliberately holds BOTH members of a twin pair — exactly the
    shape autopick used to emit — and require it to be refused.
    """
    a, b = srv._VEAT_DUPLICATE_PAIRS[0]
    pri, sec = ("Arachnos_Soldiers.Crab_Spider_Soldier",
                "Training_Gadgets.Crab_Spider_Training")
    client = srv.app.test_client()
    r = client.post("/build/autopick", json={
        "archetype": "Class_Arachnos_Soldier", "primary": pri,
        "secondary": sec, "content": "itrial"}).get_json()
    picks = [p["full_name"] for p in ((r or {}).get("powers") or [])]
    if not picks:
        print("NEGATIVE CONTROL INCONCLUSIVE: autopick returned nothing")
        sys.exit(1)
    # graft the missing twin back in, the way the defect did
    poisoned = [p for p in picks if p != b] + [a, b]
    if srv._picks_legal(poisoned, pri, sec):
        print("NEGATIVE CONTROL FAILED: a build holding BOTH "
              f"{a.rsplit('.', 1)[-1]} and {b.rsplit('.', 1)[-1]} was accepted "
              "as legal — this audit cannot detect the defect it exists for.")
        sys.exit(1)
    print(f"negative control PASSES: holding both {a.rsplit('.', 1)[-1]} and "
          f"{b.rsplit('.', 1)[-1]} is correctly refused")


def main():
    negative_control()
    client = srv.app.test_client()
    checked = 0
    fails = []
    twins = {}
    for a, b in srv._VEAT_DUPLICATE_PAIRS:
        twins[a] = b
        twins[b] = a

    all_combos = list(combos())
    for at, pri, sec in all_combos:
        for content in CONTENTS:
            r = client.post("/build/autopick", json={
                "archetype": at, "primary": pri, "secondary": sec,
                "content": content}).get_json()
            checked += 1
            picks = [p["full_name"] for p in ((r or {}).get("powers") or [])]
            if not picks:
                fails.append((at, pri, sec, content, "autopick returned NOTHING"))
                continue
            why = []
            if not srv._picks_legal(picks, pri, sec):
                why.append("_picks_legal=False")
            held = set(picks)
            for fn in picks:
                if twins.get(fn) in held:
                    why.append(f"twin pair held: {fn.rsplit('.', 1)[-1]}"
                               f" + {twins[fn].rsplit('.', 1)[-1]}")
            if len(picks) > len(srv._PICK_LEVELS) + 2:      # +2 inherent Fitness
                why.append(f"{len(picks)} picks exceeds the ladder")
            if why:
                fails.append((at, pri, sec, content, "; ".join(sorted(set(why)))))
            elif VERBOSE:
                print(f"  ok  {at.replace('Class_', ''):18} {pri.split('.')[-1][:22]:22}"
                      f" {len(picks)} picks")

    print(f"\nAUTOPICK LEGALITY AUDIT — {checked} of "
          f"{len(all_combos) * len(CONTENTS)} expected proposals checked "
          f"(contents: {', '.join(CONTENTS)})")
    if checked < len(all_combos) * len(CONTENTS):
        print("HARD FAIL: coverage denominator not met.")
        sys.exit(1)
    if not fails:
        print(f"ALL {checked} PROPOSALS ARE GAME-LEGAL — no twin pairs, "
              "ladder fits, prereqs satisfied, L1 seats filled.")
        return
    print(f"\n{len(fails)} ILLEGAL PROPOSAL(S):")
    for at, pri, sec, content, why in fails:
        print(f"  {at.replace('Class_', ''):18} {pri.split('.')[-1]:26} "
              f"/ {sec.split('.')[-1]:24} [{content}]  {why}")
    sys.exit(1)


if __name__ == "__main__":
    main()
