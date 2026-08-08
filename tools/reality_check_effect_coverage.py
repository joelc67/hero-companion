"""EVERY effect family, not five. The widened completeness check.

WHY THIS EXISTS
---------------
`reality_check_effect_structure.py` says in its own docstring that its scope is
"deliberately the sustain/armor family ... NOT every damage/control template -
that would drown the signal". That narrowing is why every gap of this class has
been found REACTIVELY from a field report instead of by an instrument: accuracy
(v28), heal-strength (v29), +MaxEnd (v35), the self +Damage buff across 275
powers, Granite Armor's -30%, Bio Armor's -25%, and power-granted slow
resistance across 126 powers. Nobody failed to look. The instrument was aimed
narrowly and the aim was never revisited.

This one looks at EVERY self-targeted client template and refuses to drown by
DISPOSITIONING families rather than by narrowing scope. Anything not
dispositioned is printed and HARD-FAILS, so the residue can only shrink.

FOUR RULES, EACH ONE PAID FOR TODAY
-----------------------------------
1. Compare modifier tables CASE-INSENSITIVELY. Ours is `Ranged_DeBuff_ToHit`,
   the client's is `Ranged_Debuff_ToHit`. One capital B invented 121 phantom
   missing -ToHit debuffs across the whole of Dark Blast.
2. Ask whether we carry the ATTRIB under ANY table before calling it absent. A
   table mismatch is a naming artefact; a missing attrib is a defect.
3. The ASPECT is part of the identity. Self RechargeTime templates are slow
   RESISTANCE at aspect=Resistance and a recharge BUFF at aspect=Strength -
   opposites. Keying on the attrib alone would have corrupted 78 records.
4. A zero-scale template carries no magnitude. Every Blaster blast has one
   (Defiance is derived from cast time, not stored), and counting them made 13
   champion contexts look exposed and stalled a re-cert over nothing.

Report-only. NEVER writes powers.json - the additive patchers do that.
Usage:  python tools/reality_check_effect_coverage.py [--all]
"""
import json
import os
import sys
import glob
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUCKETS = ("self_effects", "buff_effects", "debuff_effects",
           "control_effects", "heal_effects", "damage_effects")

# Each entry: why this family needs no data of ours. Every one traceable to a
# ruling already made - this file is where those rulings become machine-readable
# instead of living only in prose.
DISPOSITIONS = {
    "Grant_Power":       "plumbing - grants another power, not a stat (reconciliation residue)",
    "Revoke_Power":      "plumbing - revokes a power (reconciliation residue)",
    "Execute_Power":     "plumbing - fires another power",
    "Silent_Kill":       "mission/NPC plumbing",
    "Null":              "no-op template",
    "RunningSpeed":      "v30 stated display-only exclusion (movement)",
    "FlyingSpeed":       "v30 stated display-only exclusion (movement)",
    "JumpingSpeed":      "v30 stated display-only exclusion (movement)",
    "JumpHeight":        "v30 stated display-only exclusion (movement)",
    "Fly":               "v30 stated display-only exclusion (movement)",
    "SpeedRunning":      "v30 stated display-only exclusion (movement)",
    "Range":             "v30 stated display-only exclusion (range)",
    "PerceptionRadius":  "no scoring path; perception is not modelled",
    "Global_Chance_Mod": "v36 DORMANT - Opportunity semantics ungrounded in the export",
    "Knockback":         "v30 stated exclusion - KB STRENGTH display-only (protection IS scored)",
    "Knockup":           "v30 stated exclusion - KB strength display-only",
    "Repel":             "v30 stated exclusion - KB strength display-only",
    "Set_Mode":          "OPEN - the mode/meter capability (Power Boost class), queued",
}
NPC_TABLES = {"melee_archvillain_res", "ranged_archvillain_res"}


def load():
    ours = json.load(open(os.path.join(ROOT, "data", "powers.json"), encoding="utf-8"))
    client = {}
    for f in glob.glob(os.path.join(ROOT, "tools", "gamedata", "bin-crawler",
                                    "out_full", "**", "*.json"), recursive=True):
        if os.path.basename(f) == "index.json":
            continue
        try:
            c = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if c.get("full_name"):
            client[c["full_name"]] = c
    return ours, client


def main():
    show_all = "--all" in sys.argv
    ours, client = load()
    residue = collections.defaultdict(set)     # (attrib, aspect) -> powers
    disposed = collections.Counter()
    covered = 0

    for _ps, lst in ours.items():
        for p in lst:
            c = client.get(p["full_name"])
            if not c:
                continue
            covered += 1
            # rule 1 + 2: our vocabulary, case-folded, tables AND effect names
            mine = {str(e.get("modifier_table", "")).lower() for b in BUCKETS
                    for e in (p.get(b) or [])}
            mine |= {str(e.get("effect", "")).lower() for b in BUCKETS
                     for e in (p.get(b) or [])}
            mine |= {str(e.get("damage_type", "")).lower() for b in BUCKETS
                     for e in (p.get(b) or [])}
            for g in (c.get("effects") or []):
                if (g.get("requires_expression") or "").strip():
                    continue          # gated = a different, conditional claim
                for t in (g.get("templates") or []):
                    if t.get("target") != "Self":
                        continue
                    if (t.get("table") or "").lower() in NPC_TABLES:
                        continue
                    if not (t.get("scale") or 0):
                        continue      # rule 4: zero scale carries no magnitude
                    tbl = (t.get("table") or "").lower()
                    for a in (t.get("attribs") or []):
                        fam = a.replace("_Dmg", "")
                        if fam in DISPOSITIONS:
                            disposed[fam] += 1
                            continue
                        # rule 2: do we carry it under ANY name?
                        if (a.lower() in mine or fam.lower() in mine or tbl in mine):
                            continue
                        residue[(fam, t.get("aspect"))].add(p["full_name"])   # rule 3

    print(f"powers compared against the client : {covered}")
    print(f"families dispositioned             : {len(DISPOSITIONS)} "
          f"({sum(disposed.values())} template instances)")
    print(f"UNDISPOSITIONED families           : {len(residue)}\n")
    rows = sorted(residue.items(), key=lambda x: -len(x[1]))
    for (fam, aspect), fns in (rows if show_all else rows[:25]):
        print(f"  {fam:<24} aspect={str(aspect):<11} {len(fns):>5} powers")
        print(f"       e.g. {sorted(fns)[0][:70]}")
    if not show_all and len(rows) > 25:
        print(f"  ... {len(rows) - 25} more (--all to list)")

    if residue:
        print(f"\nHARD FAIL: {len(residue)} families carry no disposition. Each must be "
              f"either fixed by an additive patcher or added to DISPOSITIONS with "
              f"its reason.")
        sys.exit(1)
    print("\nALL FAMILIES DISPOSITIONED.")


if __name__ == "__main__":
    main()
