"""run_benchmark.py — the tool-vs-masters validation loop (the governing principle's proof).

For every hand-made master .mbd in benchmarks/masters/: import it, build the TOOL's version of
the same archetype + primary/secondary (autopick -> solve), compute both builds' endgame stats
(recharge, positional defense, typed resistance, recovery/regen/HP) AND control OUTPUT (the
invisible-role scorecard), then tally where the tool meets-or-beats the master. Run after any
solver/data change to prove role-output gains and catch regressions.

    python benchmarks/run_benchmark.py            # all masters
    python benchmarks/run_benchmark.py plant fire # only masters whose filename matches a term

In-process (imports the Flask app + role_output directly) so it respects the live DB, no server.
"""
import importlib.util as u, os, sys, glob, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _load(name, rel):
    spec = u.spec_from_file_location(name, os.path.join(ROOT, rel))
    mod = u.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m = _load("cohserver", "server/server.py")
ro = _load("roleoutput", "server/role_output.py")
C = m.app.test_client()

# Which content each AT's build targets (endgame): fire farmers farm, support leagues, rest general.
_FIRE_FARM_SECONDARIES = ("Fiery_Aura",)


def _content_for(at, powers):
    if at in ("Class_Brute", "Class_Tanker") and any("Fiery_Aura" in (p.get("full_name") or "") for p in powers):
        return "fire_farm"
    if m._AT_DEFAULT_ROLE.get(at) in ("controller", "buffer", "debuffer", "healer"):
        return "itrial"
    return "general"


def _groups(at):
    a = m.ARCH_BY_NAME.get(at) or {}
    return a.get("primary_group"), a.get("secondary_group")


def _derive_sets(at, powers):
    """Primary/secondary powerset full names from the master's powers via the AT's groups."""
    pg, sg = _groups(at)
    # AT group names carry inconsistent casing in the DB (Corruptor_BUFF, Dominator_CONTROL) vs the
    # powerset prefixes (Corruptor_Buff, Dominator_Control) — match case-insensitively.
    pgl = (pg or "").lower(); sgl = (sg or "").lower()
    pri = sec = None
    for p in powers:
        ps = (p.get("full_name") or "").rsplit(".", 1)[0]
        grp = ps.split(".")[0].lower()
        if pgl and grp == pgl and not pri:
            pri = ps
        elif sgl and grp == sgl and not sec:
            sec = ps
    return pri, sec


def _totals(at, powers):
    # engine.calculate_build directly (not the /calculate endpoint) so we also get the OFFENSE block
    # (st_dps / aoe_dps / pet dps) — the DAMAGE payoff the benchmark was blind to.
    ctx = m._stat_ctx(at); ctx["power_by_full"] = m.POWER_BY_FULL
    r = m.engine.calculate_build({"archetype": at, "powers": powers}, m.SET_BONUSES, ctx=ctx)
    off = r.get("offense") or {}
    def scal(k):
        x = r.get(k); return round((x.get("value", 0) if isinstance(x, dict) else x) or 0, 1)
    def dv(kind, ty):
        return round((r.get(kind) or {}).get(ty, {}).get("value", 0), 1)
    ctrl, _ = ro.build_control_output(powers, ctx)
    pet_dps = round(sum((p.get("dps_each") or p.get("dps") or 0)
                        for p in (off.get("pets") or [])), 1)
    heal = ro.build_heal_output(powers, ctx)
    return {
        "support": ro.build_support_output(off),
        "heal": heal["score"],
        "self_heal": heal["self_hps"],     # armored ATs' self-heal layer (Reconstruction, Healing Flames, Dull Pain)
        "recharge": scal("recharge"), "recovery": scal("recovery"),
        "regen": scal("regeneration"), "max_hp": scal("max_hp"),
        "def_ranged": dv("defense", "Ranged"), "def_aoe": dv("defense", "AoE"),
        "def_melee": dv("defense", "Melee"), "res_sl": dv("resistance", "Smashing"),
        "control": ctrl,
        "st_dps": round(off.get("st_dps", 0) or 0, 1),
        "aoe_dps": round(off.get("aoe_dps", 0) or 0, 1),
        "pet_dps": pet_dps,
    }


# All metrics compared (higher = better). Control/pets only count for the ATs that have them.
METRICS = ["st_dps", "aoe_dps", "pet_dps", "control", "support", "heal", "self_heal", "recharge",
           "def_ranged", "def_aoe", "def_melee", "res_sl", "recovery", "regen", "max_hp"]
_CONTROL_ATS = {"Class_Controller", "Class_Dominator"}
_PET_ATS = {"Class_Mastermind"}
_SUPPORT_ATS = {"Class_Defender", "Class_Corruptor", "Class_Mastermind"}
_HEAL_ATS = {"Class_Defender", "Class_Corruptor", "Class_Mastermind", "Class_Controller"}
# Armored ATs whose SURVIVAL includes their self-heal layer (Reconstruction, Healing Flames, Dull Pain)
_ARMORED_HEAL_ATS = {"Class_Scrapper", "Class_Brute", "Class_Stalker", "Class_Tanker", "Class_Sentinel"}

# Each AT's PRIMARY payoff — what "the best fit" actually means for it. The benchmark's headline is
# whether the tool beats the master on THESE, not on every generic stat equally (a Defender losing a
# damage race isn't a failure; a Blaster losing the damage race IS).
AT_PAYOFF = {
    "Class_Blaster": ["st_dps", "aoe_dps", "recharge"],
    "Class_Scrapper": ["st_dps", "aoe_dps", "self_heal"],
    "Class_Stalker": ["st_dps", "aoe_dps", "self_heal"],
    "Class_Brute": ["st_dps", "aoe_dps", "res_sl", "self_heal"],
    "Class_Tanker": ["res_sl", "def_ranged", "st_dps", "self_heal"],
    "Class_Sentinel": ["st_dps", "aoe_dps", "res_sl", "self_heal"],
    "Class_Controller": ["control", "recharge"],
    "Class_Dominator": ["control", "st_dps", "recharge"],
    "Class_Defender": ["support", "heal", "recharge"],
    "Class_Corruptor": ["st_dps", "aoe_dps", "recharge"],
    "Class_Mastermind": ["pet_dps", "recharge"],
    "Class_Peacebringer": ["st_dps", "aoe_dps", "res_sl"],
    "Class_Warshade": ["st_dps", "aoe_dps"],
    "Class_Arachnos_Soldier": ["st_dps", "aoe_dps", "recharge"],
    "Class_Arachnos_Widow": ["st_dps", "aoe_dps"],
}


def _applies(metric, at):
    if metric == "control":
        return at in _CONTROL_ATS
    if metric == "pet_dps":
        return at in _PET_ATS
    if metric == "support":
        return at in _SUPPORT_ATS
    if metric == "heal":
        return at in _HEAL_ATS
    if metric == "self_heal":
        return at in _ARMORED_HEAL_ATS
    return True


def run(filters):
    files = sorted(glob.glob(os.path.join(HERE, "masters", "*.mbd")))
    if filters:
        files = [f for f in files if any(t.lower() in os.path.basename(f).lower() for t in filters)]
    agg = {k: [0, 0] for k in METRICS}   # metric -> [tool_wins, comparisons] (all ATs)
    payoff_by_at = {}                    # AT -> [payoff_wins, payoff_comps] (the metrics THAT AT is judged on)
    starved_epics = []                   # (AT, epic power, master) — epic picked but left unslotted
    print(f"{'master':38} {'AT':16} payoff (this AT's core metrics): tool vs master")
    for f in files:
        txt = open(f, encoding="utf-8").read()
        imp = C.post("/build/import", json={"mbd": txt}).get_json()
        if not imp.get("ok"):
            print(f"{os.path.basename(f)[:38]:38} import failed"); continue
        b = imp["build"]; at = b["archetype"]; mp = b["powers"]
        pri, sec = _derive_sets(at, mp)
        if not (pri and sec):
            print(f"{os.path.basename(f)[:38]:38} {at.replace('Class_',''):16} no pri/sec"); continue
        content = _content_for(at, mp)
        role = m._AT_DEFAULT_ROLE.get(at, "damage")
        ap = C.post("/build/autopick", json={"archetype": at, "primary": pri, "secondary": sec,
                    "role": role, "content": content, "exposure": "flex", "travel": "teleport"}).get_json()
        if not ap.get("ok"):
            print(f"{os.path.basename(f)[:38]:38} {at.replace('Class_',''):16} autopick failed"); continue
        sol = C.post("/build/solve", json={"archetype": at, "primary": pri, "secondary": sec,
                     "powers": ap["powers"], "content": content, "role": role, "tier": "premium"}).get_json()
        if not sol.get("ok"):
            print(f"{os.path.basename(f)[:38]:38} {at.replace('Class_',''):16} solve failed"); continue
        # INVARIANT — "the solver must think ahead": an EPIC pick is a commitment (patron picks
        # cost a whole unlock arc); picking one and leaving it at its free slot means selection and
        # slotting disagreed. Zero tolerance — flag any epic with <= 1 slot.
        for p in sol["powers"]:
            if p["full_name"].startswith("Epic.") and len(p.get("slots") or []) <= 1:
                starved_epics.append((at.replace("Class_", ""), p["full_name"].split(".")[-1],
                                      os.path.basename(f)[:30]))
        M = _totals(at, mp); T = _totals(at, sol["powers"])
        for k in METRICS:                # all-metric aggregate (for the overall picture)
            if not _applies(k, at):
                continue
            agg[k][1] += 1
            if T[k] >= M[k] - 0.05:
                agg[k][0] += 1
        # PAYOFF-aware: judge this AT only on its core metrics
        payoff = AT_PAYOFF.get(at, ["st_dps", "aoe_dps"])
        pw = sum(1 for k in payoff if T[k] >= M[k] - 0.05)
        payoff_by_at.setdefault(at, [0, 0]); payoff_by_at[at][0] += pw; payoff_by_at[at][1] += len(payoff)
        detail = " ".join(f"{k.replace('_',''):>8}={T[k]:.0f}/{M[k]:.0f}" for k in payoff)
        print(f"{os.path.basename(f)[:38]:38} {at.replace('Class_',''):16} {detail}  {round(100*pw/len(payoff))}%")
    print("\n=== per-AT PAYOFF win rate (tool >= master on that AT's core metrics) ===")
    for at in sorted(payoff_by_at):
        w, n = payoff_by_at[at]
        print(f"  {at.replace('Class_',''):18} {w}/{n}  {round(100*w/max(n,1))}%   (payoff: {', '.join(AT_PAYOFF.get(at, []))})")
    pw = sum(v[0] for v in payoff_by_at.values()); pn = sum(v[1] for v in payoff_by_at.values())
    print(f"\nPAYOFF OVERALL: tool meets-or-beats master on {pw}/{pn} = {round(100*pw/max(pn,1))}% of each AT's core-metric matchups")
    if starved_epics:
        print(f"\n*** INVARIANT VIOLATION — {len(starved_epics)} STARVED EPIC(S) (picked but <=1 slot; "
              f"selection/slotting disagree): ***")
        for at, nm, src in starved_epics:
            print(f"    {at:16} {nm:22} (vs {src})")
    else:
        print("epic-commitment invariant: OK (every epic pick is slotted)")
    print("\n=== per-metric win rate (all ATs, for reference) ===")
    for k in METRICS:
        w, n = agg[k]
        if n:
            print(f"  {k:12} {w}/{n}  {round(100*w/n)}%")


if __name__ == "__main__":
    run(sys.argv[1:])
