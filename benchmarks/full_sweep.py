"""full_sweep.py — the DELUSION AUDIT: build every possible (archetype x primary x
secondary) combo through the real pipeline (autopick -> solve, the AT's natural role,
iTrial content) and run mechanical sanity invariants against each. Every check encodes a
defect the user actually caught by hand (2026-07-02 session); the sweep exists so the
NEXT one is caught by machine, all at once, instead of one painful build at a time.

Usage:  python benchmarks/full_sweep.py [at-filter ...] [--limit N]
Output: benchmarks/sweep_results.jsonl (one row per combo) + aggregated summary.
"""
import importlib.util as ilu
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = ilu.spec_from_file_location("cohserver", os.path.join(ROOT, "server", "server.py"))
m = ilu.module_from_spec(spec)
spec.loader.exec_module(m)
sys.path.insert(0, os.path.join(ROOT, "server"))
import first_principles as fp        # noqa: E402
import role_output as ro             # noqa: E402

client = m.app.test_client()

# The role the sweep builds each AT for = its first natural role (the game's own table).
ROLE_FOR_AT = {at: (roles[0] if roles else "damage")
               for at, roles in m._AT_NATURAL_ROLES.items()}

# Pool melee attacks a RANGED AT would never press (Boxing allowed once as Tough's toll).
_POOL_MELEE = {"Kick", "Cross_Punch", "Jump_Kick", "Flurry", "Air_Superiority"}
_MELEE_ATS = {"Class_Scrapper", "Class_Brute", "Class_Stalker", "Class_Tanker",
              "Class_Peacebringer", "Class_Warshade"}
# Sets whose presence PROMISES debuff output (from the role-extension table).
_DEBUFF_SETS = {k for k, v in m._SET_ROLE_EXTENSIONS.items() if "debuffer" in v}
_HEAL_SETS = {k for k, v in m._SET_ROLE_EXTENSIONS.items() if "healer" in v}


def audit_combo(at, pri, sec):
    """Build one combo through the real pipeline; return (flags, meta)."""
    flags, meta = [], {}
    role = ROLE_FOR_AT.get(at, "damage")
    ap = client.post("/build/autopick", json={
        "archetype": at, "primary": pri, "secondary": sec, "role": role,
        "content": "itrial", "exposure": "flex", "travel": "fly"}).get_json()
    if not (ap and ap.get("powers")):
        return ["autopick_failed"], meta
    sol = client.post("/build/solve", json={
        "archetype": at, "primary": pri, "secondary": sec, "powers": ap["powers"],
        "content": "itrial", "role": role, "tier": "premium",
        "preserve": False}).get_json()
    if not (sol and sol.get("powers")):
        return ["solve_failed"], meta
    powers = sol["powers"]

    # ── invariants (each encodes a user-caught defect) ──────────────────────────
    picks = [p for p in powers if not (p.get("full_name") or "").startswith("Inherent")]
    meta["picks"] = len(picks)
    if len(picks) < 24:
        flags.append("under_cap_%d" % len(picks))          # "two missing power pools"
    pools = {(p["full_name"].rsplit(".", 1)[0]) for p in picks
             if p["full_name"].startswith("Pool.")}
    if len(pools) > 4:
        flags.append("illegal_5_pools")
    epic_starved = [p["full_name"].split(".")[-1] for p in picks
                    if p["full_name"].startswith("Epic.")
                    and len([s for s in (p.get("slots") or []) if s]) <= 1]
    if len(epic_starved) > 1:                              # 1-slot epic ok once (mule LotG)
        flags.append("epic_starved")                       # "Ice epic, no power choices"
    if at not in _MELEE_ATS:
        mules = [p["full_name"].split(".")[-1] for p in picks
                 if p["full_name"].startswith("Pool.")
                 and p["full_name"].split(".")[-1] in _POOL_MELEE]
        if len(mules) >= 2:
            flags.append("mule_attacks_%d" % len(mules))   # "Boxing, Kick, Cross Punch?"

    ctx = m._stat_ctx(at); ctx["power_by_full"] = m.POWER_BY_FULL
    arch = m.ARCH_BY_NAME.get(at)
    res_cap = round(arch["res_cap"] * 100, 1) if arch else 75.0
    tot = m.engine.calculate_build({"archetype": at, "powers": powers},
                                   m.SET_BONUSES, res_cap=res_cap, ctx=ctx)
    endb = tot.get("endurance") or {}
    drain, rec = endb.get("drain_per_sec") or 0, endb.get("recovery_per_sec") or 0.01
    meta["end"] = round(drain / max(rec, 0.01), 2)
    # Calibrated against real master practice: the user's shared iTrial master runs 2.9×
    # (Ageless assumed at 50+). Flag only builds WORSE than what masters accept.
    if drain > 3.0 * rec:
        flags.append("end_starved")                        # the blue-bar problem
    rechg = ((tot.get("recharge") or {}).get("value") or 0)
    meta["recharge"] = rechg
    ev = fp.encounter_value(at, powers, ctx, tot, scenario="itrial",
                            arch_row=arch, role_output_mod=ro)
    score = fp.role_contribution(ev, role, teammates=7)
    meta["score"] = round(score, 1)
    if not (score > 0 and score == score and score < 1e7):
        flags.append("score_insane")

    # role-output promises: a debuff set must SHOW debuffs, a heal set must SHOW healing
    base_names = {ps.rsplit(".", 1)[-1] for ps in (pri, sec)}
    deb = ro.enhanced_debuff_totals(powers, ctx, global_recharge=rechg / 100.0)
    if base_names & _DEBUFF_SETS:
        # Kinetics-family sets debuff −dmg/−regen/−recharge rather than −res/−def/−tohit —
        # count ALL enemy-debuff families before calling a set blind (sweep triage fix).
        core = (deb.get("Resistance", 0) + deb.get("Defense", 0) + deb.get("ToHit", 0)
                + deb.get("DamageBuff", 0) + deb.get("Regeneration", 0)
                + deb.get("RechargeTime", 0) + 0.25 * min(deb.get("Slow", 0), 100))
        if core < 30:
            flags.append("debuff_blind")                   # "Sonic doesn't debuff anything"
    if base_names & _HEAL_SETS:
        h = ro.build_heal_output(powers, ctx)
        if (h["team_hps"] or 0) + (h["self_hps"] or 0) <= 0:
            flags.append("heal_blind")

    # export round-trip (the Mids-crash class of bug)
    exp = client.post("/build/export", json={
        "name": "sweep", "archetype": at, "primary": pri, "secondary": sec,
        "powers": powers}).get_json()
    if not (exp and exp.get("ok")):
        flags.append("export_failed")
    else:
        mbd = exp["mbd"]
        doc = mbd if isinstance(mbd, dict) else json.loads(mbd)
        if str(doc.get("Level")) != "49":
            flags.append("export_bad_level")               # zero-indexed level crash
        if any(not ps for ps in doc.get("PowerSets", [])[3:3 + len(pools)]):
            flags.append("export_missing_pools")
        imp = client.post("/build/import", json={"mbd": exp["mbd"]}).get_json()
        if not (imp and imp.get("ok")):
            flags.append("reimport_failed")
    val = client.post("/build/validate", json={
        "archetype": at, "powers": powers}).get_json() or {}
    issues = val.get("issues") or []
    if issues:
        flags.append("validate_%d_issues" % len(issues))
    return flags, meta


def main():
    args = [a for a in sys.argv[1:]]
    limit = None
    if "--limit" in args:
        i = args.index("--limit"); limit = int(args[i + 1]); args = args[:i] + args[i + 2:]
    filters = [a.lower() for a in args]
    combos = []
    for a in m.PLAYABLE:
        at = a["name"]
        if filters and not any(f in at.lower() for f in filters):
            continue
        ps = m.POWERSETS["by_archetype"].get(at) or {}
        # VEAT sets pair by BRANCH (Bane↔Bane Training…) — cross-branch combos are
        # impossible in game; auditing them wasted flags (the Night Widow under_cap pair).
        _VEAT_PAIR = {"Arachnos_Soldier": "Training_and_Gadgets",
                      "Bane_Spider_Soldier": "Bane_Spider_Training",
                      "Crab_Spider_Soldier": "Crab_Spider_Training",
                      "Widow_Training": "Teamwork",
                      "Night_Widow_Training": "Widow_Teamwork",
                      "Fortunata_Training": "Fortunata_Teamwork"}
        for pri in ps.get("primary", []):
            pfn = pri["full_name"] if isinstance(pri, dict) else pri
            for sec in ps.get("secondary", []):
                sfn = sec["full_name"] if isinstance(sec, dict) else sec
                pbase, sbase = pfn.rsplit(".", 1)[-1], sfn.rsplit(".", 1)[-1]
                if pbase in _VEAT_PAIR and _VEAT_PAIR[pbase] != sbase:
                    continue
                combos.append((at, pfn, sfn))
    if limit:
        combos = combos[:limit]
    outp = os.path.join(ROOT, "benchmarks", "sweep_results.jsonl")
    done = set()
    if os.path.exists(outp):                     # resumable across runs
        with open(outp, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line); done.add((r["at"], r["pri"], r["sec"]))
                except Exception:  # noqa: BLE001
                    pass
    print("sweep: %d combos (%d already done)" % (len(combos), len(done)))
    t0 = time.time()
    flagged = 0
    with open(outp, "a", encoding="utf-8") as f:
        for i, (at, pri, sec) in enumerate(combos):
            if (at, pri, sec) in done:
                continue
            try:
                flags, meta = audit_combo(at, pri, sec)
            except Exception as e:  # noqa: BLE001
                flags, meta = ["exception:%s" % type(e).__name__], {}
            row = {"at": at, "pri": pri, "sec": sec, "flags": flags, **meta}
            f.write(json.dumps(row) + "\n"); f.flush()
            if flags:
                flagged += 1
                print("FLAG %-18s %-28s / %-28s %s" % (
                    at.replace("Class_", ""), pri.split(".")[-1], sec.split(".")[-1],
                    ",".join(flags)))
            if i % 25 == 0:
                el = time.time() - t0
                print("... %d/%d (%.0fs elapsed, %d flagged)" % (i, len(combos), el, flagged))
    # summary
    from collections import Counter
    cnt, total = Counter(), 0
    with open(outp, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line); total += 1
            for fl in r["flags"]:
                cnt[fl.split("_%")[0].split(":")[0]] += 1
    print("\n=== SWEEP SUMMARY: %d combos ===" % total)
    for k, v in cnt.most_common():
        print("  %-24s %d" % (k, v))


if __name__ == "__main__":
    main()
