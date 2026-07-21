"""Measure Performance Shifter +Endurance proc rate from Joel's raw chatlogs.

Q1 ruling (2026-07-21, endurance-fix-paper §8): end-procs are credited in the
recovery ledger at their MEASURED average, stated on the label — same class as
the aura-proc measured pricing (tools/measure_ig_procs.py, v32).

Method:
  - Event lines: "You hit <char> with your Performance Shifter: Chance for
    +Endurance granting them <N> points of endurance."  (self-perspective only —
    the mirrored "<char> hits you with their ..." line is the SAME event logged
    twice; counting both would double the rate.)
  - Each distinct grant AMOUNT is a separate slotted proc copy (different host /
    level scaling), so each amount-group is its own stream.
  - Active time per stream: span of its own timestamps, split on gaps > 180s
    (logout/zone-idle). Stamina is an auto power — the proc rolls every
    activate_period (10s, client) unconditionally while logged in, so
    within-session per-second averaging is unbiased by AFK.
  - Outputs per stream: procs per 10s roll window (the portable rate) and
    measured end/sec. The engine consumes the RATE and scales by the piece's
    own grant at char level (50: 10.64, log-verified).

Usage: python tools/measure_end_procs.py [logdir]
"""
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"C:\Users\joelc\code\game_logs\logs")
LINE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) You hit .+ with your "
    r"(Performance Shifter: Chance for \+Endurance|"
    r"Panacea: Chance for \+Hit Points/Endurance) granting them "
    r"([0-9.]+) points of endurance\.")
ROLL_PERIOD = 10.0   # Stamina activate_period, client powers.bin
GAP_SPLIT = 180.0    # seconds; larger gap = separate session


def main():
    streams = defaultdict(list)          # (proc, grant amount) -> [timestamps]
    for f in sorted(LOG_DIR.glob("chatlog*.txt")):
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            m = LINE.match(line)
            if m:
                ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                proc = m.group(2).split(":")[0]
                streams[(proc, m.group(3))].append(ts)

    if not streams:
        print("No Performance Shifter +Endurance lines found.")
        return

    print(f"{'proc':<22} {'grant':>7} {'procs':>6} {'active_s':>9} {'windows':>8} "
          f"{'rate/window':>12} {'end/s':>7}")
    per_proc = defaultdict(lambda: [0.0, 0.0])   # proc -> [rate*windows, windows]
    for (proc, amount), times in sorted(streams.items(), key=lambda kv: -float(kv[0][1])):
        times.sort()
        active = 0.0
        procs = len(times)
        start = prev = times[0]
        for t in times[1:]:
            if (t - prev).total_seconds() > GAP_SPLIT:
                active += (prev - start).total_seconds() + ROLL_PERIOD
                start = t
            prev = t
        active += (prev - start).total_seconds() + ROLL_PERIOD
        windows = active / ROLL_PERIOD
        rate = procs / windows
        eps = procs * float(amount) / active
        print(f"{proc:<22} {amount:>7} {procs:>6} {active:>9.0f} {windows:>8.0f} "
              f"{rate:>12.3f} {eps:>7.3f}")
        per_proc[proc][0] += rate * windows
        per_proc[proc][1] += windows

    print()
    for proc, (rw, w) in per_proc.items():
        pooled = rw / w
        print(f"{proc}: measured rate {pooled:.3f} per {ROLL_PERIOD:.0f}s roll "
              f"window (implied PPM {pooled * 60 / ROLL_PERIOD:.2f}); "
              f"end/s per copy = rate x grant / {ROLL_PERIOD:.0f}")


if __name__ == "__main__":
    main()
