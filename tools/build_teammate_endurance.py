"""data/teammate_endurance.json: the endurance profile of every certified champion
in each content that has teammates - the teammates first_principles' v53 team-
endurance term prices ally +Recovery against (Joel 2026-10-10: "the app's own
builds"). Each profile is encounter_value's own end_profile on the canonical
evaluate chain: [chain drain/s, toggle drain/s, recovery/s, max endurance].

Rebuild after every champion promotion (the release procedure runs it):
  python tools/build_teammate_endurance.py            # report
  python tools/build_teammate_endurance.py --write
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ROOT, os.path.join(ROOT, "server"), os.path.join(ROOT, "tools")):
    sys.path.insert(0, p)
OUT = os.path.join(ROOT, "data", "teammate_endurance.json")
CHAMPS = os.path.join(ROOT, "benchmarks", "champions.json")


def _profile(job):
    key, picks = job
    import evaluate_first as ef
    import server as srv
    at, pri, sec, content = key.split("|")[:4]
    role = (srv.ai_build.CONTENT_PRESETS.get(content, {}).get("default_role")
            or srv._AT_DEFAULT_ROLE.get(at, "damage"))
    evs = []
    ef.evaluate_picks(at, pri, sec, content, picks, role, ev_out=evs)
    return key, content, (evs[0].get("end_profile") if evs else None)


def main():
    import first_principles as fp
    teamed = {c for c, sc in fp.SCENARIOS.items() if sc.get("teammates")}
    champs = json.load(open(CHAMPS, encoding="utf-8"))
    jobs = [(k, c["picks"]) for k, c in champs.items()
            if k.split("|")[3] in teamed and c.get("picks")]
    prof, missing = {}, []
    with ProcessPoolExecutor(max_workers=int(os.environ.get("TE_PAR", "8"))) as ex:
        for key, content, p in ex.map(_profile, jobs, chunksize=4):
            if p:
                prof.setdefault(content, []).append(p)
            else:
                missing.append(key)
    for c, ps in sorted(prof.items()):
        dry = sum(1 for dc, dt, r, em in ps
                  if fp._end_factor(dc, dt, r, em, fp.SCENARIOS[c]["length"]) < 1.0)
        print(f"  {c}: {len(ps)} champions, {dry} run dry within the {fp.SCENARIOS[c]['length']}s fight")
    if missing:
        sys.exit(f"REFUSE: {len(missing)} champions did not evaluate, e.g. {missing[:3]}")
    if "--write" in sys.argv:
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"model_version": fp.MODEL_VERSION, "source": "benchmarks/champions.json",
                       "profiles": {c: sorted(ps) for c, ps in sorted(prof.items())}},
                      f, separators=(",", ":"))
        print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
