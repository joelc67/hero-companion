"""MOVERS: how far does the activation-gated-proc fix move the certified roster?

Joel's standing rule is that a re-cert must be JUSTIFIED, never assumed. The fix
(Panacea / Performance Shifter / Power Transfer only pay in a host that actually
runs) changes where the solver puts those pieces, so scores can move. This
measures by how much, per context, before anyone spends a wave on it.

Method: evaluate every champion's picks CANONICALLY - the same evaluate_picks()
the verdict gate uses - once with the gate on and once with it off, and diff.
⚠ The arms MUST be separate processes: solver._PROC_HOST_GATE is read at import,
so flipping the env inside one process would measure nothing.

Usage:
    py tools\\measure_proc_host_movers.py arm  <out.json>   # internal, one arm
    py tools\\measure_proc_host_movers.py                   # runs both, reports
"""
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, "benchmarks", "champions.json")


def run_arm(out_path):
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    sys.path.insert(0, os.path.join(ROOT, "server"))
    import server as srv                       # noqa: E402
    from evaluate_first import evaluate_picks  # noqa: E402
    os.environ["HC_SOLVER_BACKEND"] = "cbc"    # pinned, same as the verdict gate

    champs = json.load(open(MAIN, encoding="utf-8"))
    scores = {}
    for key, ch in sorted(champs.items()):
        parts = key.split("|")
        at, prim, sec, content = parts[:4]
        form = parts[4] if len(parts) > 4 else None
        role = (srv.ai_build.CONTENT_PRESETS.get(content or "", {}).get("default_role")
                or srv._AT_DEFAULT_ROLE.get(at, "damage"))
        try:
            s, _ = evaluate_picks(at, prim, sec, content, ch["picks"], role, form=form)
        except Exception as e:  # noqa: BLE001
            s = None
            print(f"  EVAL FAILED {key}: {e}", file=sys.stderr)
        scores[key] = s
        print(f"  {key} -> {s}", file=sys.stderr)
    json.dump(scores, open(out_path, "w", encoding="utf-8"), indent=1)


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "arm":
        run_arm(sys.argv[2])
        return

    py = sys.executable
    here = os.path.abspath(__file__)
    out = {}
    for arm, flag in (("on", "1"), ("off", "0")):
        path = os.path.join(ROOT, f"_movers_{arm}.json")
        env = dict(os.environ, HC_PROC_HOST_GATE=flag)
        print(f"running arm HC_PROC_HOST_GATE={flag} ...")
        r = subprocess.run([py, here, "arm", path], env=env, cwd=ROOT,
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[-2000:])
            raise SystemExit(f"arm {arm} failed")
        out[arm] = json.load(open(path, encoding="utf-8"))

    on, off = out["on"], out["off"]
    rows = []
    for key in sorted(set(on) | set(off)):
        a, b = off.get(key), on.get(key)          # off = before, on = after
        if a is None or b is None:
            rows.append((key, a, b, None))
            continue
        rows.append((key, a, b, b - a))

    moved = [r for r in rows if r[3] is not None and abs(r[3]) > 0.05]
    flat = [r for r in rows if r[3] is not None and abs(r[3]) <= 0.05]
    failed = [r for r in rows if r[3] is None]

    print(f"\n{'context':58s} {'before':>10s} {'after':>10s} {'delta':>10s}")
    for key, a, b, d in sorted(rows, key=lambda r: (r[3] is None, -(abs(r[3]) if r[3] else 0))):
        nm = key if len(key) <= 56 else key[:55] + "…"
        if d is None:
            print(f"{nm:58s} {'?':>10} {'?':>10} {'EVAL FAIL':>10}")
        else:
            print(f"{nm:58s} {a:10.1f} {b:10.1f} {d:+10.1f}")

    print(f"\n{len(rows)} contexts: {len(moved)} moved, {len(flat)} unchanged, "
          f"{len(failed)} eval-failed")
    if moved:
        ups = [r for r in moved if r[3] > 0]
        downs = [r for r in moved if r[3] < 0]
        worst = min(moved, key=lambda r: r[3])
        best = max(moved, key=lambda r: r[3])
        print(f"  {len(ups)} up, {len(downs)} down")
        print(f"  best  {best[3]:+.1f}  {best[0]}")
        print(f"  worst {worst[3]:+.1f}  {worst[0]}")
        print("\nA MOVED context means the incumbent's picks score differently under the")
        print("fix. That is a reason to consider a re-cert; it is NOT a verdict, because")
        print("re-converging may find better picks entirely. Joel's call.")
    else:
        print("\nNO CONTEXT MOVED — the fix changes slotting nowhere in the certified")
        print("roster, so no re-cert is justified by this change.")


if __name__ == "__main__":
    main()
