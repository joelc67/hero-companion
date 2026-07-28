"""ADDITIVE patcher (the standing powers.json family — NEVER re-parse):
normalize ×100-inflated effect scales against the game client's own records,
and back-fill each matched effect's TARGET (Self vs ally/foe).

Why (Joel's finds, 2026-07-28): the parser stored SOME effect scales as
percent-numbers (Shock's recovery debuff: ours −75.0, client −0.75 — the
offense panel then printed −7500%-class rows), and it kept no target field,
so Absorb Pain's −100% regeneration CASTER penalty (client target: Self)
displays under "Ally buffs". Scales also feed role-output scoring, so any
normalization here is a certification-relevant data fix: this tool prints the
count of normalized records for the movers report, and no champion work
starts before that ruling (harden-before-certify).

Rules — client is the only authority, no heuristics:
- A candidate is one of our buff/debuff effects in the audited families whose
  power has a client record and whose (attrib, table) matches exactly one
  pairing of client templates.
- ours ≈ client            → confirmed, target back-filled.
- ours ≈ client × 100      → scale REWRITTEN to the client value + target.
- anything else            → reported as drift, scale untouched, target still
  back-filled when every candidate template agrees on it.
- Ambiguous matches are skipped and counted, never guessed.

Source: tools/gamedata/bin-crawler/out_full (full client export, 10,708
powers). Verifies powers.json is byte-identical after stripping added keys
and reverting rewritten scales; hard-fails on any other drift.

Run:  py tools\\patch_effect_scales_targets.py
"""
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "powers.json")
EXPORTS = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")

# our effect name -> the client attribs it may have been flattened from
ATTRIB_MAP = {
    "Recovery": {"Recovery"},
    "Regeneration": {"Regeneration"},
    "Endurance": {"Endurance"},
    "HitPoints": {"HitPoints"},
    "Slow": {"SpeedRunning", "SpeedFlying", "SpeedJumping", "RechargeTime"},
}
REL_TOL = 1e-3


def close(a, b):
    return abs(a - b) <= max(abs(a), abs(b), 1e-9) * REL_TOL + 1e-9


def main():
    client = {}
    n_files = 0
    for fp in glob.iglob(os.path.join(EXPORTS, "**", "*.json"), recursive=True):
        if os.path.basename(fp).startswith("_"):
            continue
        n_files += 1
        try:
            rec = json.load(open(fp, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        rows = rec if isinstance(rec, list) else [rec]
        for r in rows:
            fn = r.get("full_name")
            if not fn:
                continue
            tpls = []
            for eff in r.get("effects", []) or []:
                for t in eff.get("templates", []) or []:
                    tpls.append({"attribs": set(t.get("attribs") or []),
                                 "table": t.get("table"),
                                 "scale": t.get("scale"),
                                 "target": t.get("target")})
            if tpls:
                client[fn] = tpls
    if not client:
        raise SystemExit("FAIL: no client templates found — wrong export path")
    print(f"client export: {n_files} files, {len(client)} powers with templates")

    original = open(PATH, encoding="utf-8").read()
    data = json.loads(original)

    # Coverage denominator OUTSIDE the patch loop (standing rule): every
    # audited-family effect on a power that has a client record.
    def candidates():
        for rows in data.values():
            if not isinstance(rows, list):
                continue
            for q in rows:
                tpls = client.get(q.get("full_name"))
                if not tpls:
                    continue
                for key in ("buff_effects", "debuff_effects"):
                    for e in q.get(key, []):
                        if e.get("effect") in ATTRIB_MAP:
                            yield q, e, tpls

    expected = sum(1 for _ in candidates())

    confirmed = normalized = drift = ambiguous = targeted = 0
    drift_samples = []
    rewrites = []          # (effect-dict, old_scale) for the safety revert
    added_targets = []     # effect-dicts that gained "target"
    for q, e, tpls in candidates():
        want = ATTRIB_MAP[e["effect"]]
        table = e.get("modifier_table")
        matches = [t for t in tpls
                   if t["table"] == table and t["attribs"] & want]
        if not matches:
            ambiguous += 1
            continue
        ours = float(e.get("scale") or 0)
        exact = [t for t in matches if close(ours, float(t["scale"] or 0))]
        x100 = [t for t in matches
                if close(ours, float(t["scale"] or 0) * 100.0)]
        if exact:
            confirmed += 1
            chosen = exact
        elif x100:
            rewrites.append((e, e.get("scale")))
            e["scale"] = float(x100[0]["scale"])
            normalized += 1
            chosen = x100
        else:
            drift += 1
            if len(drift_samples) < 8:
                drift_samples.append((q["full_name"].split(".")[-1],
                                      e["effect"], table, ours,
                                      [t["scale"] for t in matches]))
            chosen = matches
        tgts = {t["target"] for t in chosen}
        if len(tgts) == 1 and "target" not in e:
            e["target"] = tgts.pop()
            added_targets.append(e)
            targeted += 1

    handled = confirmed + normalized + drift + ambiguous
    print(f"{handled} of {expected} candidate effects examined "
          f"(confirmed {confirmed} · normalized ×100 {normalized} · "
          f"drift-reported {drift} · no-table-match {ambiguous} · "
          f"targets back-filled {targeted})")
    for s in drift_samples:
        print("  drift:", s)
    if handled != expected:
        raise SystemExit("== COVERAGE FAILURE: candidate count drifted "
                         "mid-patch — nothing written ==")

    # Safety: revert rewrites + strip added keys must reproduce the input.
    for e, old in rewrites:
        e["_undo"] = e["scale"]
        e["scale"] = old
    for e in added_targets:
        e["_t"] = e.pop("target")
    if json.dumps(data, sort_keys=True) != json.dumps(
            json.loads(original), sort_keys=True):
        # tolerate only our bookkeeping keys before failing
        chk = json.loads(json.dumps(data))
        for rows in chk.values():
            if not isinstance(rows, list):
                continue
            for q in rows:
                for key in ("buff_effects", "debuff_effects"):
                    for e in q.get(key, []):
                        e.pop("_undo", None)
                        e.pop("_t", None)
        if json.dumps(chk, sort_keys=True) != json.dumps(
                json.loads(original), sort_keys=True):
            raise SystemExit("== SAFETY FAILURE: patch touched more than "
                             "scales/targets — nothing written ==")
    for e, _old in rewrites:
        e["scale"] = e.pop("_undo")
    for e in added_targets:
        e["target"] = e.pop("_t")

    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print("data/powers.json updated (additive+normalized; run battery, probe, "
          "and the MOVERS REPORT before any champion work)")


if __name__ == "__main__":
    main()
