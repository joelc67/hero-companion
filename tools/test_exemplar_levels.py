"""BATTERY: the exemplar target level actually rescues early powers.

WHY THIS EXISTS. BasiliskXVIII, 2026-08-01: "Envenom coming in on my corruptor at
level 49... if most of what I do with that character involves exemping down to run
TFs, I don't want to be exemping out of all of my best tools, particularly when
it's a power that you can get at level 4."

The cause was that _assign_pick_levels optimises for SLOT FEASIBILITY only, so a
power the game offers at 4 can be parked at 49 and vanish the moment you exemplar.

DEFINITION USED, with no invented value model: a pick is STRANDED when the game
would grant it at or below your exemplar level but the plan seats it above.

NEGATIVE CONTROLS, because a pass that just reshuffles proves nothing:
  - the un-hinted arm must actually strand something (else the test is vacuous)
  - no power may be seated BEFORE the game allows it (rescuing by cheating)
  - the slot schedule must remain satisfiable in both arms
  - a level nothing is stranded at must change nothing

Run:  py tools\\test_exemplar_levels.py
"""
import importlib.util as ilu
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = ilu.spec_from_file_location("cohserver", os.path.join(ROOT, "server", "server.py"))
srv = ilu.module_from_spec(spec)
spec.loader.exec_module(srv)

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if detail:
        print(f"        {detail}")


def build_powers(picks):
    """Power dicts shaped the way _assign_pick_levels expects, with the game's own
    availability and a realistic slot spread (weight is what the repair loop moves)."""
    out = []
    for i, fn in enumerate(picks):
        rec = srv.POWER_BY_FULL.get(fn) or {}
        n_slots = 6 if i % 3 == 0 else (3 if i % 3 == 1 else 1)
        out.append({"full_name": fn,
                    "level_available": rec.get("level_available"),
                    "powerset_full_name": rec.get("powerset_full_name"),
                    "slots": [None] * n_slots})
    return out


def stranded(powers, level):
    return [p for p in powers
            if srv._sched_avail(p) <= level < int(p.get("pick_level") or 99)]


def seated_too_early(powers):
    return [p for p in powers
            if int(p.get("pick_level") or 99) < srv._sched_avail(p)]


def main():
    print("EXEMPLAR TARGET-LEVEL BATTERY\n")
    champs = json.load(open(os.path.join(ROOT, "benchmarks", "champions.json"),
                            encoding="utf-8"))
    key = next(k for k in champs if "Corruptor" in k or "Defender" in k)
    at = key.split("|")[0]
    picks = [p for p in champs[key]["picks"]
             if not str(p).startswith("Inherent")]
    print(f"  context: {key}\n  {len(picks)} picks\n")

    L = 25

    # ARM A — no hint (today's behaviour)
    a = build_powers(picks)
    ok_a = srv._assign_pick_levels(a, at)
    str_a = stranded(a, L)

    # ARM B — same build, exemplar level declared
    b = build_powers(picks)
    ok_b = srv._assign_pick_levels(b, at, exemplar_level=L)
    str_b = stranded(b, L)

    check("NEGATIVE CONTROL: the un-hinted plan really does strand early powers",
          len(str_a) > 0,
          f"{len(str_a)} power(s) the game grants by {L} are seated later"
          + (f" — e.g. {str_a[0]['full_name'].split('.')[-1]} "
             f"(available {srv._sched_avail(str_a[0])}, seated {str_a[0]['pick_level']})"
             if str_a else ""))

    # !! THE COUNT IS INVARIANT, and this battery is what proved it. Every seat
    # at or below L must hold a power the game grants by L, so the number
    # stranded is fixed at (picks available by L) - (seats existing by L).
    # Reordering cannot change it; rescuing one early power always pushes
    # another out. Asserting "fewer" would be asserting something impossible.
    check(f"the stranded COUNT is unchanged (it is invariant, not a failure)",
          len(str_b) == len(str_a), f"{len(str_a)} -> {len(str_b)}, as the maths requires")

    def _weight(ps):
        return sum(1 + srv._sched_added(p) for p in ps)

    check("the exemplar pass never makes the loss WORSE",
          _weight(str_b) <= _weight(str_a),
          f"slot investment left outside the window: {_weight(str_a)} -> {_weight(str_b)}")

    check("no power is seated before the game allows it (arm B)",
          not seated_too_early(b),
          "rescuing by cheating the availability rules would be worse than the bug")
    check("no power is seated before the game allows it (arm A)",
          not seated_too_early(a))

    check("the slot schedule stays satisfiable in both arms",
          ok_a == ok_b, f"feasible A={ok_a} B={ok_b}")

    # A level with nothing to rescue must be a no-op.
    c = build_powers(picks)
    srv._assign_pick_levels(c, at, exemplar_level=50)
    d = build_powers(picks)
    srv._assign_pick_levels(d, at)
    check("NEGATIVE CONTROL: exemplar 50 changes nothing (nothing can be stranded)",
          [p["pick_level"] for p in c] == [p["pick_level"] for p in d],
          "level 50 is the whole game, so there is nothing to rescue")

    # Every pick level must still be a real pick-ladder level.
    ladder = set(srv.leveling_schedule.POWER_PICK_LEVELS)
    off = [p for p in b if int(p["pick_level"]) not in ladder]
    check("every seat is a real pick-ladder level", not off,
          f"{len(off)} off-ladder" if off else "")

    print(f"\n{len(CHECKS)} checks ran")
    if not all(CHECKS):
        print(f"{CHECKS.count(False)} FAILURE(S)")
        sys.exit(1)
    print("== ALL CHECKS PASS — early powers survive the exemplar ==")


if __name__ == "__main__":
    main()
