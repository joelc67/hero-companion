"""BATTERY: activation-gated procs must only pay out in a host that actually runs.

WHY THIS EXISTS. Field report from BasiliskXVIII (2026-08-01), confirmed in code:
Panacea sat in PIECE_GLOBALS, whose contract is "these work whether or not the
host power is active". So the engine credited the same measured end/s whether
the proc sat in Health (an Auto power that ticks forever) or in a single-target
heal cast twice an hour, and the solver was therefore free to mule it anywhere.
The credited numbers were MEASURED with the pieces in Health/Stamina, so the
host is baked into them.

Coverage denominator: every flagged proc in PIECE_GLOBALS, in an Auto host, a
Toggle host and a Click host.

NEGATIVE CONTROLS, because a gate that blocks everything proves nothing:
  - the same proc in an Auto host must STILL pay (else the fix just deleted value)
  - Theft of Essence, deliberately unflagged, must STILL pay in a click host
    (it is a healing-set proc priced for click hosts at half usage)

Run:  py tools\\test_proc_host_gate.py
"""
import importlib.util as ilu
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
spec = ilu.spec_from_file_location("cohengine", os.path.join(ROOT, "server", "engine.py"))
eng = ilu.module_from_spec(spec)
spec.loader.exec_module(eng)

AUTO, TOGGLE, CLICK = 1, 2, 0
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if detail:
        print(f"        {detail}")


def credit(set_name, piece_name, power_type):
    """Run the real _piece_globals over a one-power build and return
    (totals, skipped-list)."""
    build = {"powers": [{"full_name": "Test.Set.Host", "display_name": "Host",
                         "power_type": power_type,
                         "slots": [{"set_name": set_name, "piece_name": piece_name}]}]}
    totals = eng._empty_totals()
    eng._piece_globals(build, totals)
    return totals, build["powers"][0]


def magnitude(totals):
    """Total credited magnitude across the effect keys these procs touch."""
    return sum(abs(totals.get(k) or 0) for k in ("recovery", "regeneration"))


def main():
    print("ACTIVATION-GATED PROC HOST BATTERY\n")
    flagged = [g for g in eng.PIECE_GLOBALS if g.get("needs_running_host")]
    check("the flagged family is non-empty (else this battery is vacuous)",
          len(flagged) >= 3, f"{len(flagged)} flagged: "
          + ", ".join(g["set"] for g in flagged))

    for g in flagged:
        sn, pn = g["set"], g["piece"]
        auto, _sk_auto = credit(sn, pn, AUTO)
        tog, _ = credit(sn, pn, TOGGLE)
        clk, _sk_clk = credit(sn, pn, CLICK)

        check(f"{sn}: PAYS in an Auto host", magnitude(auto) > 0,
              f"credited {magnitude(auto):.3f}")
        check(f"{sn}: PAYS in a Toggle host", magnitude(tog) > 0,
              f"credited {magnitude(tog):.3f}")
        check(f"{sn}: pays NOTHING in a Click host", magnitude(clk) == 0,
              f"credited {magnitude(clk):.3f} (must be 0)")
        # The predicate itself is the behavioural check now. The earlier version
        # recorded skips into `totals`, which holds floats and dicts only - the
        # list broke Force Feedback seating and the standing gate caught it.
        check(f"{sn}: the host predicate agrees (click is not continuous)",
              not eng._host_runs_continuously({"power_type": CLICK})
              and eng._host_runs_continuously({"power_type": AUTO}),
              "click False, auto True")

    # NEGATIVE CONTROL: an unflagged proc must be untouched by the gate.
    toe = next((g for g in eng.PIECE_GLOBALS if "theft" in g["set"]), None)
    if toe:
        clk, _ = credit(toe["set"], toe["piece"], CLICK)
        check("NEGATIVE CONTROL: Theft of Essence still pays in a Click host",
              magnitude(clk) > 0,
              f"credited {magnitude(clk):.3f} (priced for click hosts on purpose)")

    # NEGATIVE CONTROL: a non-proc global must be unaffected by host type.
    lotg, _ = credit("luck of the gambler", "global recharge", CLICK)
    check("NEGATIVE CONTROL: a true always-on global (LotG) is unaffected",
          abs(lotg.get("recharge") or 0) > 0,
          f"recharge {lotg.get('recharge')}")

    print(f"\n{len(CHECKS)} checks ran")
    if not all(CHECKS):
        print(f"{CHECKS.count(False)} FAILURE(S)")
        sys.exit(1)
    print("== ALL CHECKS PASS — procs pay only where they actually fire ==")


if __name__ == "__main__":
    main()
