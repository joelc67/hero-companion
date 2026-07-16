"""TWO-CONTEXT PATH PROBE (verifier flag, ideas.md 2026-07-16 item 3).

Decides whether the E verdict's catastrophic ratios measured a real transfer
failure or a PATH-IDENTITY artifact: e_derived_verdict.py scored bare
autopick picks re-slotted through evaluate_first's canonical chain — NOT the
app's real Build path. This probe produces the build the way the WIZARD does:

  1. POST /build/autopick {archetype, primary, secondary, role, content}
     (the wizard also sends exposure/travel/form from the user's answers;
     omitted here = the no-preference defaults, same as the GT's own seed)
  2. POST /build/solve with the REAL payload — the autopick powers carrying
     their slots + earned_slot_count fields, tier "premium", preserve False
     (build.imported is false after wizard autopick, so the wizard solves
     with preserve off) — the exact payload shape CLAUDE.md pins.
  3. Score the SERVED build directly (calculate_build + encounter_value +
     role_contribution — no re-solve), fresh process, canonical protocol.

Outcome (a): probe lands near GT canonical  -> the E harness measured the
wrong path; re-run only the derived side through this path.
Outcome (b): probe lands ~30%              -> the failure is real and
product-wide; the fleet-fork discussion starts from that.

Run: py tools\\e_path_probe.py  [key ...]   (defaults: worst + median case)
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv  # noqa: E402
import first_principles as fp  # noqa: E402

DEFAULT_KEYS = [
    # worst case, 7.3%
    "Class_Sentinel|Sentinel_Ranged.Archery|Sentinel_Defense.Willpower|itrial",
    # median case, 30.7%
    "Class_Tanker|Tanker_Defense.Bio_Organic_Armor|Tanker_Melee.Super_Strength|itrial",
]


def score_served(at, content, role, powers):
    """Canonical scoring of an ALREADY-SOLVED build (no re-solve)."""
    ctx = srv._stat_ctx(at)
    ctx["power_by_full"] = srv.POWER_BY_FULL
    arch_row = srv.ARCH_BY_NAME.get(at)
    res_cap = (round(arch_row["res_cap"] * 100, 1) if arch_row
               else srv.engine.RESISTANCE_HARD_CAP)
    tot = srv.engine.calculate_build({"archetype": at, "powers": powers},
                                     srv.SET_BONUSES, res_cap=res_cap, ctx=ctx)
    ev = fp.encounter_value(at, powers, ctx, tot, scenario=content,
                            arch_row=arch_row, role_output_mod=srv.role_output)
    tm = (fp.SCENARIOS.get(content) or fp.SCENARIOS["general"]).get(
        "teammates", 0)
    return fp.role_contribution(ev, role, teammates=tm)


def main():
    keys = sys.argv[1:] or DEFAULT_KEYS
    os.environ["HC_SOLVER_BACKEND"] = "cbc"
    verdict = json.load(open(os.path.join(ROOT, "benchmarks",
                                          "e_verdict.json"),
                             encoding="utf-8"))
    vrows = {r["key"]: r for r in verdict["rows"]}
    client = srv.app.test_client()
    print("key | GT_canonical | old_derived(_assess_solve chain) | "
          "probe(real Build path) | probe/GT")
    for key in keys:
        parts = key.split("|")
        at, prim, sec, content = parts[:4]
        role = (srv.ai_build.CONTENT_PRESETS.get(content or "", {})
                .get("default_role")
                or srv._AT_DEFAULT_ROLE.get(at, "damage"))
        ap = client.post("/build/autopick", json={
            "archetype": at, "primary": prim, "secondary": sec,
            "role": role, "content": content}).get_json()
        if not (ap and ap.get("ok")):
            print(f"{key}  AUTOPICK FAILED: {(ap or {}).get('error')}")
            continue
        # the REAL payload: autopick powers keep their slots/earned fields
        sol = client.post("/build/solve", json={
            "archetype": at, "content": content, "role": role,
            "tier": "premium", "powers": ap["powers"], "preserve": False,
        }).get_json()
        if not (sol and sol.get("ok")):
            print(f"{key}  SOLVE FAILED: {(sol or {}).get('error')}")
            continue
        probe = score_served(at, content, role, sol["powers"])
        vr = vrows.get(key, {})
        gt = vr.get("gt_canonical")
        old = vr.get("derived_canonical")
        print(f"{key}\n  GT {gt}  old-derived {old}  "
              f"probe {probe:.1f}  probe/GT "
              f"{(probe / gt):.3f}" if gt else f"  probe {probe:.1f} (no GT row)")


if __name__ == "__main__":
    main()
