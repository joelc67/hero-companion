"""Disposition census for effect-family reconciliation (the 2026-07-28 lane).

Classifies every audited-family effect (Slow/Recovery/Regeneration/Endurance/
HitPoints) that patch_effect_scales_targets.py could not confirm, against the
client export — zero guessing, value proofs only:

  PvP-only variant  our row carries pv_mode 2, so engine._pv_ok gates it OFF
                    in every PvE calculation. Mids ships PvE and PvP variants
                    side by side; the client export's own record for these
                    powers has no PVP_ONLY effect group (the export DOES carry
                    541 of those elsewhere, so this is a real absence, not a
                    crawler gap). Nothing to reconcile: the row cannot move a
                    number outside the arena. Tested first, because it is a
                    property of OUR row and outranks any client match.
                    ⚠ These were the "8 irreducible Chrono_Shift rows" queued
                    since 2026-07-28 as "values match nothing client-side,
                    suspected Mids pre-enhanced bakes". They are neither:
                    each is exactly 5.33x the client's OWN timed Heal_Dmg
                    scale (0.2 -> 1.066, 0.3 -> 1.599), the same constant on
                    all four AT variants, with the Mastermind's 0.88 support
                    factor riding through both sides (0.176 -> 0.93808). That
                    is a deliberate heal-over-time -> regeneration conversion,
                    not an enhanced bake. Nature Affinity's Regrowth is the
                    same shape at x5.0. Whether the constant matches live PvP
                    is UNVERIFIABLE from the client and deliberately not
                    claimed. Proof of the gate: tools/test_pvp_variant_gate.py.
  pseudo-pet fold   client power carries Create_Entity: our effects are the
                    DELIBERATE fold of the pet's effects onto the summoner.
  grant/revoke      Grant_Power/Revoke_Power chains (Unrelenting Fury lane).
  redirect PROVEN   a twin record (zapp_normal/_quick class) value-matches
                    our (table, scale) exactly — the fold is client-proven.
  client stub       the client record has ZERO templates and no proving twin
                    was found under the known suffixes — structurally the
                    redirect class, twin naming unknown.
  partial unproven  the client record has templates but not this family and
                    no twin matches: the TRUE residue for per-power study.

2026-07-28 disposition of the original 1,900 unmatched: 1,787 confirmed +
2 ×100-normalized + 3 one-to-one synced; folds by design 761 pseudo-pet +
230 redirect-proven; 26 grant/revoke; 167 stubs; residue 240 partial +
53 multi-template drifts.

2026-08-07, after the PvP class was added (same 1,424 rows, re-sorted — no
data changed): 712 pseudo-pet · 200 redirect-proven · 189 PvP-only ·
120 stub · 19 grant/revoke · TRUE RESIDUE 184 (was 240). The 56 that left
the residue are PvP variants that were never reconcilable against a PvE
export.

Run:  py tools\\classify_unmatched_effects.py
"""
import glob
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
FAMS = {"Recovery", "Regeneration", "Endurance", "HitPoints", "Slow"}
SLOW = {"RunningSpeed", "FlyingSpeed", "JumpingSpeed", "JumpHeight",
        "RechargeTime"}
TWIN_SUFFIXES = ("_normal", "_quick", "_fast", "_slow")


def close(a, b):
    return abs(a - b) <= max(abs(a), abs(b), 1e-9) * 2e-3 + 1e-9


def main():
    powers = json.load(open(os.path.join(ROOT, "data", "powers.json"),
                            encoding="utf-8"))
    client, by_base = {}, {}
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
            tpls = [{"attribs": set(t.get("attribs") or []),
                     "table": t.get("table"), "scale": t.get("scale")}
                    for eff in r.get("effects", []) or []
                    for t in eff.get("templates", []) or []]
            client[fn] = tpls
            base = fn.split(".")[-1].lower()
            for sfx in TWIN_SUFFIXES:
                if base.endswith(sfx):
                    base = base[: -len(sfx)]
            by_base.setdefault(base, []).append((fn, tpls))

    cls = Counter()
    total = 0
    for _ps, plist in powers.items():
        for q in plist:
            fn = q.get("full_name")
            tpls = client.get(fn)
            if tpls is None:
                continue
            allattribs = (set().union(*[t["attribs"] for t in tpls])
                          if tpls else set())
            for key in ("buff_effects", "debuff_effects"):
                for e in q.get(key, []):
                    if e.get("effect") not in FAMS or "target" in e:
                        continue
                    want = SLOW if e["effect"] == "Slow" else {e["effect"]}
                    if allattribs & want:
                        continue      # matched family — handled by the patcher
                    total += 1
                    if e.get("pv_mode") == 2:
                        cls["PvP-only variant (gated off in PvE)"] += 1
                        continue
                    if "Create_Entity" in allattribs:
                        cls["pseudo-pet fold (by design)"] += 1
                        continue
                    if {"Grant_Power", "Revoke_Power"} & allattribs:
                        cls["grant/revoke chain"] += 1
                        continue
                    ours = float(e.get("scale") or 0)
                    base = fn.split(".")[-1].lower()
                    twin = False
                    for tfn, ttpls in by_base.get(base, []):
                        if tfn == fn:
                            continue
                        if any(t["attribs"] & want
                               and t["table"] == e.get("modifier_table")
                               and close(ours, float(t["scale"] or 0))
                               for t in ttpls):
                            twin = True
                            break
                    if twin:
                        cls["redirect twin PROVEN"] += 1
                    elif not tpls:
                        cls["client stub (redirect class, twin unproven)"] += 1
                    else:
                        cls["partial record, unproven (TRUE residue)"] += 1
    print(f"{total} unmatched family effects dispositioned:")
    for k, n in cls.most_common():
        print(f"  {n:5d}  {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
