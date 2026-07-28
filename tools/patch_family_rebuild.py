"""Family-row REBUILD from client templates — the hard-residue closer
(2026-07-28, Joel's ruling: "as authentic and accurate to the game as
possible"). For each (power, effect-family) group that every gentler proof
failed (patch_effect_scales_targets + the EV/sum census), our rows are
REPLACED by a flattening of the client's own templates:

    one row per PvE/EITHER template: scale, modifier_table, probability
    (= the template's effect chance), duration (parsed), target, and the
    family's effect name. PVP_ONLY templates become pv_mode=2 rows.

This is the sync precedent applied to row STRUCTURE, restricted to the
hard-classified groups only — confirmed/proven/fold-by-design groups are
untouched. It is NOT a re-parse: only the audited families on the hard list
change, every value is the client's, and the tool prints per-power
before/after for the record. Scores can move (Kinetics is on the list):
run battery + probe + the champion movers check after, and NO champion
work before the movers ruling.

Run:  py tools\\patch_family_rebuild.py
"""
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "powers.json")
EXPORTS = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
FAMS = {"Recovery", "Regeneration", "Endurance", "HitPoints", "Slow"}
SLOW = {"RunningSpeed", "FlyingSpeed", "JumpingSpeed", "JumpHeight",
        "RechargeTime"}


def close(a, b, tol=2e-3):
    return abs(a - b) <= max(abs(a), abs(b), 1e-9) * tol + 1e-9


def parse_dur(s):
    m = re.match(r"([\d.]+)", str(s or ""))
    return float(m.group(1)) if m else 0.0


def load_client():
    client = {}
    for fp in glob.iglob(os.path.join(EXPORTS, "**", "*.json"),
                         recursive=True):
        if os.path.basename(fp).startswith("_"):
            continue
        try:
            rec = json.load(open(fp, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for r in (rec if isinstance(rec, list) else [rec]):
            fn = r.get("full_name")
            if not fn:
                continue
            tpls = []
            for eff in r.get("effects", []) or []:
                ch = float(eff.get("chance") or 1.0)
                pv = eff.get("is_pvp") or "EITHER"
                for t in eff.get("templates", []) or []:
                    tpls.append({"attribs": set(t.get("attribs") or []),
                                 "table": t.get("table"),
                                 "scale": float(t.get("scale") or 0),
                                 "chance": ch, "pv": pv,
                                 "duration": parse_dur(t.get("duration")),
                                 "target": t.get("target")})
            client[fn] = tpls
    return client


def is_hard(rows, fam_tpls):
    """Mirror of the census: True when neither per-row EV/scale match nor
    EV-sum conservation explains this group."""
    matched = 0
    for e in rows:
        ours_s = float(e.get("scale") or 0)
        ours_ev = ours_s * float(e.get("probability") or 1.0)
        pv_ours = e.get("pv_mode", 0)
        for t in fam_tpls:
            if t["table"] != e.get("modifier_table"):
                continue
            if pv_ours == 2 and t["pv"] == "PVE_ONLY":
                continue
            if pv_ours != 2 and t["pv"] == "PVP_ONLY":
                continue
            cev = t["scale"] * t["chance"]
            if close(ours_ev, cev) or close(ours_s, t["scale"]) \
                    or close(ours_ev, t["scale"]) or close(ours_s, cev):
                matched += 1
                break
    if matched == len(rows):
        return False
    by_table = {}
    for e in rows:
        by_table.setdefault(e.get("modifier_table"), 0.0)
        by_table[e.get("modifier_table")] += (float(e.get("scale") or 0)
                                              * float(e.get("probability")
                                                      or 1.0))
    for tab, s_ours in by_table.items():
        s_client = sum(t["scale"] * t["chance"] for t in fam_tpls
                       if t["table"] == tab and t["pv"] != "PVP_ONLY")
        if s_client and close(s_ours, s_client, 5e-2):
            return False
    return True


def main():
    client = load_client()
    original = open(PATH, encoding="utf-8").read()
    data = json.loads(original)

    # Denominator first (standing rule): count hard groups before touching.
    hard_groups = []
    for ps, plist in data.items():
        if not isinstance(plist, list):
            continue
        for q in plist:
            tpls = client.get(q.get("full_name"))
            if tpls is None:
                continue
            for key in ("buff_effects", "debuff_effects"):
                fam_rows = {}
                for e in q.get(key, []):
                    if e.get("effect") in FAMS:
                        fam_rows.setdefault(e["effect"], []).append(e)
                for fam, rows in fam_rows.items():
                    want = SLOW if fam == "Slow" else {fam}
                    fam_tpls = [t for t in tpls if t["attribs"] & want]
                    if not fam_tpls:
                        continue          # stub/fold class, untouched
                    if is_hard(rows, fam_tpls):
                        hard_groups.append((q, key, fam, rows, fam_tpls))
    print(f"{len(hard_groups)} hard (power, list, family) groups; "
          f"{sum(len(g[3]) for g in hard_groups)} rows to rebuild")

    rebuilt_rows = 0
    for q, key, fam, rows, fam_tpls in hard_groups:
        new_rows = []
        for t in fam_tpls:
            row = {"effect": fam, "damage_type": "None",
                   "scale": t["scale"], "modifier_table": t["table"],
                   "probability": t["chance"], "nmag": 1.0,
                   "duration": t["duration"],
                   "pv_mode": 2 if t["pv"] == "PVP_ONLY" else 0,
                   "target": t["target"],
                   "rebuilt_from_client": True}
            new_rows.append(row)
        kept = [e for e in q.get(key, []) if e.get("effect") != fam]
        q[key] = kept + new_rows
        rebuilt_rows += len(new_rows)
        print(f"  {q['full_name']}: {fam} {len(rows)} row(s) -> "
              f"{len(new_rows)} client row(s)")
    if len(hard_groups) == 0:
        raise SystemExit("nothing to rebuild — census disagrees, investigate")

    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print(f"data/powers.json updated: {rebuilt_rows} client-derived rows "
          f"replacing the hard residue. Run battery, probe, census, and the "
          f"CHAMPION MOVERS CHECK before any champion work.")


if __name__ == "__main__":
    main()
