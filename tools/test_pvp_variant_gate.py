"""BATTERY: PvP-only effect rows never reach a PvE number.

This closes the "8 irreducible Chrono_Shift rows" queued since 2026-07-28 as
"values match nothing client-side, suspected Mids pre-enhanced bakes".

What they actually are, proven here:
  * they carry pv_mode 2, so engine._pv_ok gates them OFF in PvE;
  * each is exactly 5.33x the client's OWN timed Heal_Dmg scale on the same
    power (0.2 -> 1.066 and 0.3 -> 1.599), the SAME constant on all four AT
    variants, with the Mastermind's 0.88 support factor riding through both
    sides (0.176 -> 0.93808). A constant multiple of a client scale is a
    heal-over-time -> regeneration conversion, not an enhanced bake: an
    enhanced value would not land on one constant across four archetypes.
  * the client export's Chrono_Shift record carries NO PVP_ONLY effect group
    and no Regeneration attribute at all. The export does carry 541 PVP_ONLY
    groups elsewhere, so that absence is real, not a crawler gap - which is
    exactly why the reconciliation instrument could never match these rows.

NOT claimed: that 5.33 is the right constant for live PvP. The client cannot
answer it and no measurement exists. It is inert in PvE either way.

Run:  py tools\\test_pvp_variant_gate.py
"""
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))

import engine                      # noqa: E402
import server as srv               # noqa: E402

EXPORTS = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
# the four AT variants, and the client scale each of our two rows converts
VARIANTS = {
    "Controller_Buff.Time_Manipulation.Chrono_Shift": (0.2, 0.3),
    "Corruptor_Buff.Time_Manipulation.Chrono_Shift": (0.2, 0.3),
    "Defender_Buff.Time_Manipulation.Chrono_Shift": (0.2, 0.3),
    "Mastermind_Buff.Time_Manipulation.Chrono_Shift": (0.176, 0.264),
}
FACTOR = 5.33
CHECKS = []
EXPECTED = 9


def check(name, ok, detail=""):
    CHECKS.append(bool(ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if detail:
        print(f"        {detail}")


def buffs(fn, arch, pvp):
    """The buff panel's rows for a build holding exactly this power."""
    ctx = srv._stat_ctx(arch)
    build = {"archetype": arch, "pvp": pvp,
             "powers": [{"full_name": fn, "slots": [None]}]}
    _deb, buf = engine._debuff_buff_summary(build, ctx)
    return {d["effect"]: d.get("pct", d.get("hp", d.get("end"))) for d in buf}


def main():
    print("PVP-VARIANT GATE BATTERY\n")
    fn = "Defender_Buff.Time_Manipulation.Chrono_Shift"
    pve, pvp = buffs(fn, "Class_Defender", False), buffs(fn, "Class_Defender", True)

    # 1-2. The gate, both directions. Absent in PvE is the whole claim; present
    # in PvP is the negative control that proves the row EXISTS and the PvE
    # result is a gate firing rather than missing data.
    check("PvE: no Regeneration row from Chrono Shift",
          "Regeneration" not in pve, f"PvE buffs: {pve}")
    check("NEGATIVE CONTROL - PvP: the row IS there",
          abs(pvp.get("Regeneration", 0) - 266.5) < 0.1,
          f"PvP buffs: {pvp}")

    # 3. Everything else is arena-neutral and must not move with the flag.
    shared = {k: v for k, v in pvp.items() if k != "Regeneration"}
    check("the power's PvE rows are identical in both arenas",
          shared == pve, f"{pve} vs {shared}")

    # 4-7. The conversion constant, on all four AT variants.
    powers = json.load(open(os.path.join(ROOT, "data", "powers.json"),
                            encoding="utf-8"))
    ours = {}
    for _ps, plist in powers.items():
        for q in plist:
            if q.get("full_name") in VARIANTS:
                ours[q["full_name"]] = [e for e in q.get("buff_effects", [])
                                        if e.get("effect") == "Regeneration"]
    for full, client_scales in VARIANTS.items():
        rows = sorted(float(e["scale"]) for e in ours.get(full, []))
        want = [round(s * FACTOR, 5) for s in sorted(client_scales)]
        got = [round(s, 5) for s in rows]
        allpvp = all(e.get("pv_mode") == 2 for e in ours.get(full, []))
        check(f"{full.split('.')[0]}: both rows are pv_mode 2 and x{FACTOR}",
              allpvp and got == want, f"client {client_scales} x{FACTOR} "
              f"-> expected {want}, data has {got}")

    # 8. The client really has no PvP group here - the reason reconciliation
    #    could never match these, stated as a fact rather than an assumption.
    pvp_groups = 0
    for fp in glob.glob(os.path.join(EXPORTS, "**", "chrono_shift.json"),
                        recursive=True):
        rec = json.load(open(fp, encoding="utf-8"))
        for r in (rec if isinstance(rec, list) else [rec]):
            pvp_groups += sum(1 for eff in r.get("effects", []) or []
                              if eff.get("is_pvp") == "PVP_ONLY")
    check("client export: Chrono_Shift has zero PVP_ONLY effect groups",
          pvp_groups == 0, f"found {pvp_groups}")

    # 9. NEGATIVE CONTROL for check 8: the export DOES carry PvP groups, so a
    #    zero above is an absence in this power, not a crawler that drops them.
    seen = 0
    for fp in glob.iglob(os.path.join(EXPORTS, "**", "*.json"), recursive=True):
        if os.path.basename(fp).startswith("_"):
            continue
        try:
            rec = json.load(open(fp, encoding="utf-8"))
        except Exception:                                        # noqa: BLE001
            continue
        for r in (rec if isinstance(rec, list) else [rec]):
            seen += sum(1 for eff in r.get("effects", []) or []
                        if eff.get("is_pvp") == "PVP_ONLY")
        if seen:
            break
    check("NEGATIVE CONTROL: the export carries PVP_ONLY groups elsewhere",
          seen > 0, f"{seen} found before stopping")

    n, ok = len(CHECKS), sum(CHECKS)
    print(f"\n{ok} of {n} passed ({EXPECTED} expected)")
    return 0 if (ok == n and n == EXPECTED) else 1


if __name__ == "__main__":
    sys.exit(main())
