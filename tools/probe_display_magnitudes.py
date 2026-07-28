"""Probe every saved build's displayed offense aggregates for absurd magnitudes.

A PROBE, not a gate: it flags rows whose |pct| exceeds a threshold so unit
bugs of the 2026-07-28 heal class ("+94303.2%" = 943 HP formatted as a
percent) surface before a player screenshots them. Found 28 suspects on its
first run; the survivors are the queued Slow/Recovery/Regeneration
scale-normalization data pass (mixed fraction vs percent-as-number storage
in parsed effects), tracked in the slotting-remainder batch paper.

Usage: python tools/probe_display_magnitudes.py [threshold_pct=300]
"""
import glob
import json
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "server")
import server as srv  # noqa: E402

THRESHOLD = float(sys.argv[1]) if len(sys.argv) > 1 else 300.0


def main():
    c = srv.app.test_client()
    checked, suspects = 0, []
    for f in sorted(glob.glob("saves/*.json")):
        try:
            b = json.load(open(f, encoding="utf-8"))
            b = b.get("build", b)
            r = c.post("/build/calculate", json=b).get_json() or {}
        except Exception as e:  # a save that cannot calculate is itself a finding
            suspects.append((f, "CALC FAILED", str(e)[:80]))
            continue
        checked += 1
        off = r.get("offense") or {}
        for kind in ("buffs", "debuffs"):
            for row in off.get(kind) or []:
                v = row.get("pct")
                if v is not None and abs(v) > THRESHOLD:
                    suspects.append((f, kind, row))
    print(f"{checked} builds probed, threshold |{THRESHOLD}%|")
    print(f"{len(suspects)} suspect rows")
    for s in suspects:
        print(" ", s)
    return 0  # probe: informational exit, never a gate


if __name__ == "__main__":
    sys.exit(main())
