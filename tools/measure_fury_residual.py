"""MEASURE the sustained Fury damage multiplier — the v36 farm anchor.

No-wiki absolute (Joel's ruling-4 clarification, 2026-07-22): the 2%/pt Fury
read-side is third-party lore, and modifier_tables.json carries no meter
curves — so the ONLY permitted basis is a measurement from the game itself.

Method (the proc-measurement lineage):
  1. Parse Lime Juice's real /build_save export (OneDrive temp limejuice.txt)
     through the app's own in-game import parser -> the exact build.
  2. Engine computes each attack's EXPECTED enhanced damage (enhancement +
     credited buffs, NO fury term — v35 model has none).
  3. Farm chatlog damage lines (9,400+ hits) give the OBSERVED per-attack
     medians at steady state.
  4. residual = observed / expected, per attack; the cross-attack median is
     the MEASURED sustained fury damage multiplier in farm content.
The ruled scenario ladder (75/60/50/65) applies as RATIOS of this anchor,
stated on every label. If attacks disagree wildly (spread > ~15%), the
isolation is NOT clean -> print UNCLEAN and v36 ships Fury damage at the
dormant/display tier ("meter shown; damage credit awaits measurement").

Run: python tools/measure_fury_residual.py
"""
import json
import re
import statistics as st
import sys
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
import server as srv  # noqa: E402

EXPORT = r"C:\Users\joelc\OneDrive\Desktop\temp\limejuice.txt"
LOGS = [rf"C:\Users\joelc\code\game_logs\logs\chatlog 2026-07-0{d}.txt" for d in (5, 6, 7)]
LINE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) You hit .+ with your "
                  r"([A-Za-z' ]+) for ([0-9.]+) points")


def main():
    # 1) the real build through the app's own parser
    import ingame_import
    txt = open(EXPORT, encoding="utf-8", errors="replace").read()
    parsed = ingame_import.parse_ingame_build(txt, srv._import_lookups())
    build = parsed.get("build") or parsed
    powers = build.get("powers") or []
    at = build.get("archetype") or "Class_Brute"
    print(f"build parsed: {at}, {len(powers)} powers")

    # 2) expected enhanced per-attack damage, NO fury (v35 engine)
    ctx = srv._stat_ctx(at)
    tot = srv.engine.calculate_build({"archetype": at, "powers": powers},
                                     srv.SET_BONUSES, ctx=ctx)
    expected = {}
    for a in (tot.get("offense") or {}).get("attacks", []) or []:
        nm, dmg = a.get("name"), a.get("damage") or a.get("enhanced_damage")
        if nm and dmg:
            expected[nm.lower()] = float(dmg)
    if not expected:
        print("UNCLEAN: engine offense block exposes no per-attack damage list")
        return 1

    # 3) observed medians from the farm logs (longest session per attack)
    obs = defaultdict(list)
    for f in LOGS:
        try:
            for line in open(f, encoding="utf-8", errors="replace"):
                m = LINE.match(line)
                if m:
                    obs[m.group(2).strip().lower()].append(float(m.group(3)))
        except FileNotFoundError:
            pass

    # 4) residuals on attacks present in BOTH (>=100 observations)
    rows = []
    for nm, vals in obs.items():
        if len(vals) < 100 or nm not in expected:
            continue
        med = st.median(vals)
        rows.append((nm, len(vals), expected[nm], med, med / expected[nm]))
    if not rows:
        print("UNCLEAN: no attack matched between build export and log lines")
        print("  log attacks:", sorted(k for k, v in obs.items() if len(v) >= 100)[:8])
        print("  build attacks:", sorted(expected)[:8])
        return 1
    print(f"\n{'attack':22} {'n':>6} {'expected':>9} {'observed':>9} {'residual':>9}")
    for nm, n, e, o, res in sorted(rows, key=lambda r: -r[1]):
        print(f"{nm:22} {n:>6} {e:>9.1f} {o:>9.1f} {res:>9.3f}")
    residuals = [r[4] for r in rows]
    anchor = st.median(residuals)
    spread = (max(residuals) - min(residuals)) / anchor
    print(f"\nFARM FURY ANCHOR (median residual): {anchor:.3f} "
          f"(spread {spread:.0%} across {len(rows)} attacks)")
    if spread > 0.15:
        print("VERDICT: UNCLEAN (spread > 15%) — Fury damage ships DORMANT-LABELED in v36.")
        return 1
    print("VERDICT: CLEAN — v36 uses this measured anchor; ladder applies as ratios "
          "(farm=anchor; team/itrial=anchor×60/75; solo=×50/75; AV=×65/75), stated on labels.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
