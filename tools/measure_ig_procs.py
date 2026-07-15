"""Re-derivation of aura/patch proc rates from Joel's raw chatlogs — the
IG-specific evidence the v31 valuation question needs (session 2026-07-15).

Method (recreates the 2026-07-07 pure-window approach with per-target,
per-host attribution): Touch of Lady Grey and Shield Breaker are DEFENSE
DEBUFF set procs — Blazing Aura cannot host them, and the click powers that
could are statistically absent from the logs (Rad Siphon 6 casts, Proton
Sweep 8) — so on Lime Juice (Joel's Rad/Fire farm Brute) their fires
attribute to IRRADIATED GROUND. IG's own damage ticks give per-target
active stretches; a stretch's 10-second windows are the community-standard
denominator, and per-HIT-tick rates are the per-roll denominator.

Competing predictions for a 3.5 PPM proc in IG (period 2.0s, radius 8,
AF 1.9): v31 dev-archive formula = PPM*10/(60*AF) = 30.7% per window;
measured-aura behavior (AF~1) = PPM*10/60 = 58.3% per window.

Run:  py tools\\measure_ig_procs.py [logdir]
"""
import glob
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
LOGDIR = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\joelc\code\game_logs\logs"

TS = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (.*)$")
# Pet-attributed lines carry an "Irradiated Ground:  " channel prefix
# (damage ticks and to-hit rolls); proc fires log UNPREFIXED — which is why
# attribution needs the stretch method at all.
IG_HIT = re.compile(r"^(?:Irradiated Ground:\s+)?You hit (.+?) with your "
                    r"Irradiated Ground for ([\d.]+) points")
IG_MISS = re.compile(r"^(?:Irradiated Ground:\s+)?MISSED (.+?)!! "
                     r"Your Irradiated Ground power")
PROC = re.compile(r"^You hit (.+?) with your (Touch of Lady Grey|Shield Breaker)"
                  r": Chance for")

def main():
    hits = defaultdict(list)          # target -> [epoch...]
    misses = defaultdict(list)
    fires = {"Touch of Lady Grey": defaultdict(list),
             "Shield Breaker": defaultdict(list)}
    dmg_sum = dmg_n = 0.0
    files = sorted(glob.glob(os.path.join(LOGDIR, "chatlog*.txt")))
    for path in files:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = TS.match(line)
                if not m:
                    continue
                t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").timestamp()
                rest = m.group(2)
                h = IG_HIT.match(rest)
                if h:
                    hits[h.group(1)].append(t)
                    dmg_sum += float(h.group(2)); dmg_n += 1
                    continue
                mm = IG_MISS.match(rest)
                if mm:
                    misses[mm.group(1)].append(t)
                    continue
                p = PROC.match(rest)
                if p:
                    fires[p.group(2)][p.group(1)].append(t)
    print(f"{len(files)} log files; IG hit ticks {sum(len(v) for v in hits.values())}, "
          f"misses {sum(len(v) for v in misses.values())}, "
          f"ToLG fires {sum(len(v) for v in fires['Touch of Lady Grey'].values())}, "
          f"SB fires {sum(len(v) for v in fires['Shield Breaker'].values())}")
    print(f"IG mean tick damage: {dmg_sum / max(dmg_n, 1):.2f} "
          f"(the UNPRICED base output, per hit per target)")

    # Per-target contiguous IG stretches (tick gap <= 4s keeps the 2s cadence
    # with 1s timestamp rounding); windows = duration/10.
    GAP = 4.0
    total_windows = 0.0
    total_hit_ticks = 0
    in_stretch = {k: 0 for k in fires}
    cadences = []
    for tgt, ts_list in hits.items():
        ts_list = sorted(set(ts_list))
        start = prev = ts_list[0]
        stretches = []
        for t in ts_list[1:]:
            if t - prev > GAP:
                stretches.append((start, prev))
                start = t
            else:
                cadences.append(t - prev)
            prev = t
        stretches.append((start, prev))
        for a, b in stretches:
            dur = b - a
            if dur < 10.0:
                continue
            total_windows += dur / 10.0
            total_hit_ticks += sum(1 for t in ts_list if a <= t <= b)
            for name, per_tgt in fires.items():
                in_stretch[name] += sum(1 for t in per_tgt.get(tgt, ())
                                        if a - 1 <= t <= b + 1)
    if not total_windows:
        raise SystemExit("no qualifying stretches — method assumption failed")
    mean_cad = sum(cadences) / max(len(cadences), 1)
    print(f"\nqualifying target-stretches: {total_windows:.0f} ten-second windows, "
          f"{total_hit_ticks} hit ticks inside them (tick cadence {mean_cad:.2f}s)")
    for name, n in in_stretch.items():
        w = n / total_windows
        per_tick = n / max(total_hit_ticks, 1)
        # binomial-ish 95% band on the window rate
        import math
        se = math.sqrt(max(w * (1 - w), 1e-9) / total_windows)
        print(f"  {name:22s}: per-10s-window {100*w:5.1f}% ±{196*se:.1f}  "
              f"per-hit-tick {100*per_tick:5.2f}%")
    print("\npredictions for 3.5 PPM in IG: dev-archive AF formula 30.7%/window "
          "(6.1%/tick) · AF=1 58.3%/window (11.7%/tick)")


if __name__ == "__main__":
    main()
