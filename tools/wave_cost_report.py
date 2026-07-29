"""WAVE COST REPORT — where certification time actually goes.

Joel's standing ask (2026-07-29): "efficiencies should be something we try and
achieve every time we run these." This mines the worker logs a wave already
writes — no instrumentation, no extra compute — and reports per-context cost
so the expensive contexts are named rather than guessed at.

Per context: wall minutes, sweeps, total solves, solves/minute, and minutes
per sweep. Sorted by cost. Then the aggregate levers:
  - which contexts eat the wave's tail (the wall-clock critical path)
  - solves/min spread (a context that is slow AND low-throughput is blocked
    on something other than raw solve count — the plateau/marathon signature)
  - capped-solve counts (node-cap pressure = degenerate plateau proving)

Run:  py tools\\wave_cost_report.py [log-glob ...]
      py tools\\wave_cost_report.py champions_shard_v38ho*_p*.log
Default: every champions_shard_*_p*.log in the repo root.
"""
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_RE_START = re.compile(r"^\[\s*([0-9.]+)m\]\s+(\S+)")
_RE_DONE = re.compile(r"->\s+score\s+([0-9.]+|NONE)(?:.*?solves\s+(\d+))?"
                      r".*?'sweeps':\s*(\d+)", re.S)
_RE_CAP = re.compile(r"'capped_solves_floor':\s*(\d+)")
_RE_TOTAL = re.compile(r"^total:\s+([0-9.]+)\s+min", re.M)


def parse_log(path):
    """[(key, start_min, end_min, sweeps, solves, capped)] for one worker log."""
    text = open(path, encoding="utf-8", errors="replace").read()
    lines = text.splitlines()
    rows, pending = [], None
    for ln in lines:
        m = _RE_START.match(ln)
        if m:
            if pending:                      # previous context ended here
                pending["end"] = float(m.group(1))
                rows.append(pending)
            pending = {"key": m.group(2), "start": float(m.group(1)),
                       "end": None, "sweeps": None, "solves": None, "capped": 0}
            continue
        if pending and "-> score" in ln:
            d = _RE_DONE.search(ln)
            if d:
                pending["solves"] = int(d.group(2)) if d.group(2) else None
                pending["sweeps"] = int(d.group(3))
            c = _RE_CAP.search(ln)
            if c:
                pending["capped"] = int(c.group(1))
    if pending:
        t = _RE_TOTAL.search(text)
        pending["end"] = float(t.group(1)) if t else pending["start"]
        rows.append(pending)
    return rows


def main():
    pats = sys.argv[1:] or ["champions_shard_*_p*.log"]
    logs = sorted({f for p in pats for f in glob.glob(os.path.join(ROOT, p))})
    if not logs:
        print("no worker logs matched")
        return
    rows = []
    for lg in logs:
        for r in parse_log(lg):
            r["log"] = os.path.basename(lg)
            r["min"] = max(0.0, (r["end"] or r["start"]) - r["start"])
            rows.append(r)
    rows = [r for r in rows if r["min"] > 0]
    if not rows:
        print(f"{len(logs)} logs read, no completed contexts yet")
        return
    rows.sort(key=lambda r: -r["min"])
    print(f"\nWAVE COST REPORT — {len(rows)} contexts across {len(logs)} worker logs\n")
    print(f"  {'minutes':>8} {'sweeps':>7} {'solves':>8} {'slv/min':>8} "
          f"{'min/swp':>8} {'capped':>7}  context")
    for r in rows:
        spm = (r["solves"] / r["min"]) if r["solves"] else 0
        mps = (r["min"] / r["sweeps"]) if r["sweeps"] else 0
        p = r["key"].split("|")
        name = (f"{p[0].replace('Class_','')}/{p[1].split('.')[-1]}"
                f"{'/' + p[4] if len(p) > 4 else ''}")
        print(f"  {r['min']:8.1f} {r['sweeps'] or 0:7d} {r['solves'] or 0:8d} "
              f"{spm:8.0f} {mps:8.2f} {r['capped']:7d}  {name}")

    tot = sum(r["min"] for r in rows)
    med = sorted(r["min"] for r in rows)[len(rows) // 2]
    slowest = rows[0]
    print(f"\n  total context-minutes {tot:.0f} · median {med:.1f} · "
          f"slowest {slowest['min']:.1f} ({slowest['key'].split('|')[0].replace('Class_','')})")
    # the levers
    thru = [(r["solves"] / r["min"], r) for r in rows if r["solves"]]
    if thru:
        thru.sort()
        lo, hi = thru[0], thru[-1]
        print(f"  throughput spread: {lo[0]:.0f} solves/min "
              f"({lo[1]['key'].split('|')[1].split('.')[-1]}) → {hi[0]:.0f} "
              f"({hi[1]['key'].split('|')[1].split('.')[-1]}) — a SLOW context "
              f"with LOW throughput is blocked on solve difficulty (plateau), "
              f"not on doing more work")
    capped = [r for r in rows if r["capped"]]
    if capped:
        print(f"  node-cap pressure on {len(capped)} contexts "
              f"(max {max(r['capped'] for r in capped)} capped solves) — "
              f"degenerate-plateau proving, the known marathon signature")
    tail = [r for r in rows if r["min"] > 2 * med]
    if tail:
        print(f"  ⚠ WALL-CLOCK TAIL: {len(tail)} context(s) over 2× median — "
              f"the wave cannot finish faster than these, so they are the "
              f"scheduling lever (send them FIRST, or to the fastest worker):")
        for r in tail:
            print(f"      {r['min']:.0f} min  {r['key']}")


if __name__ == "__main__":
    main()
