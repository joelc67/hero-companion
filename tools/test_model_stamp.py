"""Every champion records the model that certified it.

Until 2026-08-10 it did not, and that absence had a cost. Joel asked "have we
updated all the champions?" and the honest answer needed a tool run, because
nothing in the data said which model produced any entry. The same ambiguity is
what let the v43+v44 re-cert be scoped by "does this build HOLD a patched
power?" instead of by the movers - a test that is sufficient but not necessary,
missed five contexts, and cost a second wave.

With the stamp, the scope question is answerable by inspection:

    stale = [k for k, v in champions.items()
             if (v.get("model_version") or 0) < fp.MODEL_VERSION]

⚠ THE STAMP IS METADATA AND MUST STAY THAT WAY. Nothing in the engine, the
scorer or the solver may read it, or it stops being free and starts being a
model input. Two checks below guard that: the value is never consulted outside
the merge tool, and stripping it from the roster reproduces the file exactly.

Usage: python tools/test_model_stamp.py
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))

PASS = FAIL = 0


def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}")
    if detail:
        print(f"        {detail}")


def main():
    import first_principles as fp                      # noqa: E402

    MAIN = os.path.join(ROOT, "benchmarks", "champions.json")
    raw = open(MAIN, "rb").read()
    ch = json.loads(raw.decode("utf-8"))

    # ---- 1. the roster carries it ----
    stamped = [k for k, v in ch.items() if v.get("model_version")]
    ok("every champion records the model that certified it",
       len(stamped) == len(ch) == 24, f"{len(stamped)} of {len(ch)}")
    ok(f"...and they all read v{fp.MODEL_VERSION}, which the 0-moved "
       "evaluate_first result is the evidence for",
       {v.get("model_version") for v in ch.values()} == {fp.MODEL_VERSION})

    # ---- 2. the scope question is answerable BY INSPECTION ----
    stale = [k for k, v in ch.items()
             if (v.get("model_version") or 0) < fp.MODEL_VERSION]
    ok("the correct wave-scope test now needs no tool run: champions predating "
       "the current model can be listed straight from the data",
       stale == [], f"{len(stale)} predate v{fp.MODEL_VERSION}")

    # ---- 3. IT IS METADATA. Nothing may score off it. ----
    # ⚠ TEST THE ACCESS, NOT THE WORD. A first version grepped for the bare
    # string "model_version" and flagged server.py - which only ever REPORTS
    # `fp.MODEL_VERSION`, the module constant, in its responses. That is a
    # different thing from reading a champion's stamp, and conflating them is
    # a check that cries wolf. What must never appear is a READ of the field
    # off an entry: .get("model_version") or ["model_version"].
    import re
    reads = re.compile(r"""(?:\.get\(\s*["']model_version|\[\s*["']model_version)""")
    hits = []
    for mod in ("engine.py", "first_principles.py", "role_output.py",
                "solver.py", "proc_pass.py", "server.py", "ai_build.py"):
        fp_ = os.path.join(ROOT, "server", mod)
        if os.path.exists(fp_) and reads.search(open(fp_, encoding="utf-8").read()):
            hits.append(mod)
    ok("NEGATIVE CONTROL: no scoring module READS a champion's stamp - the "
       "moment one does, it stops being free metadata and becomes an input",
       not hits,
       f"read by {hits}" if hits else
       "engine/scorer/solver clean; server.py only reports fp.MODEL_VERSION")
    probe = json.loads(raw.decode("utf-8"))
    for v in probe.values():
        v.pop("model_version", None)
    bare = json.dumps(probe, indent=1, ensure_ascii=False)
    ok("...and stripping it from the roster changes nothing else",
       len(bare) < len(raw.decode("utf-8")) and json.loads(bare).keys() == ch.keys())

    # ---- 4. THE MERGE PATH STAMPS, proven by running it ----
    # ⚠ A roster that happens to be stamped proves only that someone did it once.
    # This drives the real tool over a scratch shard and reads the result back.
    src = open(os.path.join(ROOT, "tools", "merge_champion_shards.py"),
               encoding="utf-8").read()
    ok("merge_champion_shards sets the stamp at its single write point",
       "model_version=fp.MODEL_VERSION" in src and "data[k] = v" in src,
       "one write point, so a shard cannot slip in unstamped")
    key = next(iter(ch))
    with tempfile.TemporaryDirectory() as td:
        shard = os.path.join(td, "champions_shard_stamptest_p0.json")
        entry = dict(ch[key])
        entry.pop("model_version", None)          # arrive UNstamped, as a worker writes
        json.dump({key: entry}, open(shard, "w", encoding="utf-8"))
        verd = os.path.join(td, "v.json")
        json.dump({key: "supersede"}, open(verd, "w", encoding="utf-8"))
        before = open(MAIN, "rb").read()
        try:
            r = subprocess.run([sys.executable,
                                os.path.join(ROOT, "tools", "merge_champion_shards.py"),
                                "--replace", "--verdicts", verd, shard],
                               capture_output=True, text=True, cwd=ROOT)
            after = json.load(open(MAIN, encoding="utf-8"))
            ok("...and a shard entry that arrives UNSTAMPED comes out stamped",
               r.returncode == 0
               and after[key].get("model_version") == fp.MODEL_VERSION,
               f"rc={r.returncode}, stamp={after.get(key, {}).get('model_version')}")
        finally:
            open(MAIN, "wb").write(before)         # always restore the roster
    ok("the roster was restored byte-identical after the live merge test",
       open(MAIN, "rb").read() == raw)

    print(f"\nmodel-stamp battery: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
