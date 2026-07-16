"""CORRECTED LABELS (Joel's gate, 2026-07-16): restamp every champion's AFK
sustain ledger under the CURRENT model, so the label says what today's maths
says — "whatever that turns out to be", as promised publicly.

Why this exists: a certificate's afk_sustain block is computed at CONVERGENCE
time and then frozen. The shipped 0.12.20 farm_afk champion carries
  "AFK-certified at +3x8 ... the +4x8 asteroid worst case is unreachable for
   this combo"
— computed on pre-6/23 data (Temperature Protection missing its +MaxHP) and
without the community-standard accolades. Under v33 those SAME PICKS sustain
42.5 HP/s and clear +4x8. The picks never needed changing; the DATA did. If we
shipped without restamping, the public correction would be contradicted by our
own certificate.

This recomputes the ledger from the stored picks through the same chain
deep_optimize stamps with (autopick-free: bare picks -> _assess_solve ->
proc_pass -> endurance relief -> calculate_build -> afk_sustain_assessment),
for every context whose preset declares an afk_regen_floor. It changes NO
picks and NO scores — only the sustain block and its label.

Prints before/after for each and hard-fails if a context's preset asks for the
floor but no ledger can be produced.

Run:  py tools\\refresh_afk_labels.py  [--dry-run]
"""
import argparse
import copy
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv          # noqa: E402
import proc_pass              # noqa: E402
import first_principles as fp  # noqa: E402

MAIN = os.path.join(ROOT, "benchmarks", "champions.json")


def ledger_for(at, content, role, picks):
    pre = srv.ai_build.preset_targets(
        content, role,
        res_cap=round(((srv.ARCH_BY_NAME.get(at) or {}).get("res_cap") or .75) * 100, 1),
        archetype=at)
    ctx = srv._stat_ctx(at); ctx["power_by_full"] = srv.POWER_BY_FULL
    arch_row = srv.ARCH_BY_NAME.get(at)
    res_cap = (round(arch_row["res_cap"] * 100, 1) if arch_row
               else srv.engine.RESISTANCE_HARD_CAP)
    r = srv._assess_solve(at, [{"full_name": f} for f in picks],
                          copy.deepcopy(pre["targets"]), "premium",
                          pre["perk_focus"], pre["roles"], False, False, False,
                          with_powers=True)
    if not r:
        return None
    _t, solved = r
    solved = proc_pass.apply_proc_pass(solved, srv.POWER_BY_FULL, role=role,
                                       content=content)
    solved = srv._endurance_relief_pass(solved, at, ctx, res_cap)
    tot = srv.engine.calculate_build({"archetype": at, "powers": solved},
                                     srv.SET_BONUSES, res_cap=res_cap, ctx=ctx)
    return fp.afk_sustain_assessment(
        solved, tot, arch_row, ctx, role_output_mod=srv.role_output,
        assume_accolades=bool((srv.ai_build.CONTENT_PRESETS.get(content, {}) or {})
                              .get("assumes_accolades")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    data = json.load(open(MAIN, encoding="utf-8"))

    expected = [k for k in data
                if (srv.ai_build.CONTENT_PRESETS.get(k.split("|")[3], {}) or {})
                .get("afk_regen_floor")]
    print(f"contexts whose preset declares an AFK regen floor: {len(expected)}")
    done = 0
    for key in expected:
        at, prim, sec, content = key.split("|")[:4]
        role = ((srv.ai_build.CONTENT_PRESETS.get(content, {}) or {})
                .get("default_role") or srv._AT_DEFAULT_ROLE.get(at, "damage"))
        led = ledger_for(at, content, role, data[key]["picks"])
        if not led:
            print(f"HARD FAIL: {key} declares the floor but produced no ledger")
            sys.exit(1)
        cert = data[key].setdefault("certificate", {})
        before = (cert.get("afk_sustain") or {}).get("label", "(none)")
        print(f"\n  {key.split('|')[1]}|{content}")
        print(f"    BEFORE: {before}")
        print(f"    AFTER : {led['label']}")
        cert["afk_sustain"] = led
        done += 1

    print(f"\n{done} of {len(expected)} expected labels refreshed")
    if done != len(expected):
        print("HARD FAIL: coverage shortfall")
        sys.exit(1)
    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return
    with open(MAIN, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    print(f"\nwrote {MAIN}")


if __name__ == "__main__":
    main()
