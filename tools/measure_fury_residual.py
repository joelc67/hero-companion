"""MEASURE the sustained Fury damage multiplier — the v36 farm anchor.

No-wiki absolute (Joel's ruling-4 clarification, 2026-07-22): the 2%/pt Fury
read-side is third-party lore, and modifier_tables.json carries no meter curves
— so the ONLY permitted basis is a measurement from the game itself.

── v2, 2026-08-06: THE MEMO'S NAMED NEXT INSTRUMENT ────────────────────────────
v1 read every damage line as if it were a whole hit and reported UNCLEAN at a
228% spread. The memo named the fix: "component-summed swing reconstruction
(group log lines by timestamp+target+attack, sum components, match engine
per-component model)". That is what this does now, plus one correction the memo
could not have known:

  ⚠ AoE ATTACKS CANNOT BE RECONSTRUCTED FROM THIS LOG FORMAT. Farm mobs share a
  display name ("Malifiend Fragment"), so grouping on (timestamp, target,
  attack) merges an AoE's hits on SEVERAL DIFFERENT enemies into one pseudo
  swing. It shows up as impossible component counts — Atom Smasher logs 2x, 4x,
  6x, 8x ... 18x for a two-component attack. Single-target attacks show ONE
  consistent count and are the only clean isolation available. This tool reports
  the purity of every attack and only anchors on the pure ones, rather than
  quietly averaging the contaminated ones in.

RESULT WHEN LAST RUN (Lime Juice, Brute Radiation_Melee/Fiery_Aura, 3 farm days):
  spread 228% -> 25.2%, two attacks isolated at 100% shape purity. Still above
  the 15% bar, and the reason is NOT Fury noise: both attacks' swing
  distributions are tight and unimodal with near-identical shape (p95/p05 of
  1.38 and 1.45). The disagreement is in the EXPECTED side —

      Radioactive Smash / Devastating Blow
          engine   0.325
          game     0.420   (observed medians, this tool)
          client   0.481   (PvE damage scales, bin-crawler export)

  Three numbers that should agree do not, and the engine is the outlier. A
  global multiplier like Fury CANCELS in that ratio, so this is a per-attack
  baseline question, not a meter question. **Fury cannot be measured until the
  Radiation Melee per-attack damage is reconciled with the client.** That is the
  next concrete step, and it is a data question rather than a measurement one.

Run: python tools/measure_fury_residual.py
"""
import re
import statistics as st
import sys
from collections import defaultdict, Counter

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
import server as srv  # noqa: E402

EXPORT = r"C:\Users\joelc\OneDrive\Desktop\temp\limejuice.txt"
LOGS = [rf"C:\Users\joelc\code\game_logs\logs\chatlog 2026-07-0{d}.txt" for d in (5, 6, 7)]

# ONE component of ONE outgoing swing. Deliberately strict:
#   "You hit"          — outgoing and mine
#   no "Prefix:" ahead — drops pseudo-pet/patch lines ("Burn Flames: You hit …")
#   [^:]+ power name   — drops set procs ("Obliteration: Chance for Smashing …"),
#                        which are their own damage, not the attack's swing
SWING = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) You hit (.+?) with your ([^:]+?) "
    r"for ([0-9.]+) points of ([A-Za-z]+) damage(?: over time)?\.")
MIN_SWINGS = 40          # below this a median is noise
PURE = 0.95              # share of swings that must share one component count
CLEAN_SPREAD = 0.15      # the memo's bar


def main():
    import ingame_import
    try:
        txt = open(EXPORT, encoding="utf-8", errors="replace").read()
    except FileNotFoundError:
        print(f"MISSING the build export: {EXPORT}")
        print("  It must be the SAME character that produced the logs, exported")
        print("  in game with /build_save_file — the expected side is computed")
        print("  from that character's real slotting.")
        return 1
    parsed = ingame_import.parse_ingame_build(txt, srv._import_lookups())
    build = parsed.get("build") or parsed
    powers, at = build.get("powers") or [], build.get("archetype")
    print(f"build: {at} {build.get('primary')} / {build.get('secondary')}"
          f"  ({len(powers)} powers)")
    if at != "Class_Brute":
        print(f"  ⚠ {at} has no Fury — this measurement only means anything on a Brute.")

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

    # ── reconstruct swings ──────────────────────────────────────────────────
    groups = defaultdict(list)
    for f in LOGS:
        try:
            fh = open(f, encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        with fh:
            for line in fh:
                if " damage" not in line:
                    continue
                m = SWING.match(line.strip())
                if m:
                    ts, tgt, atk, val, _ty = m.groups()
                    groups[(ts, tgt, atk.strip())].append(
                        (float(val), "over time" in line))

    swings, counts = defaultdict(list), defaultdict(Counter)
    for (_ts, _tgt, atk), comps in groups.items():
        direct = [v for v, dot in comps if not dot]      # DoT ticks are their own stream
        if direct:
            swings[atk].append(sum(direct))
            counts[atk][len(direct)] += 1

    print(f"\n{'attack':24} {'swings':>7} {'expected':>9} {'observed':>9} "
          f"{'residual':>9}  isolation")
    rows = []
    for atk, vals in sorted(swings.items(), key=lambda kv: -len(kv[1])):
        key = atk.lower()
        if len(vals) < MIN_SWINGS or key not in expected or expected[key] <= 0:
            continue
        mix = counts[atk]
        purity = mix.most_common(1)[0][1] / sum(mix.values())
        med = st.median(vals)
        res = med / expected[key]
        tag = ("single-target, clean" if purity >= PURE
               else f"AoE name-collision ({purity:.0%} pure) — EXCLUDED")
        print(f"{atk[:24]:24} {len(vals):>7} {expected[key]:>9.1f} {med:>9.1f} "
              f"{res:>9.3f}  {tag}")
        if purity >= PURE:
            rows.append((atk, res))

    if not rows:
        print("\nUNCLEAN: no attack isolated cleanly (all AoE name-collisions).")
        return 1
    resid = [r[1] for r in rows]
    anchor = st.median(resid)
    spread = (max(resid) - min(resid)) / anchor if len(resid) > 1 else 0.0
    print(f"\nclean single-target attacks: {len(rows)}")
    print(f"FARM FURY ANCHOR (median residual): {anchor:.3f}  spread {spread:.1%}")
    if spread > CLEAN_SPREAD or len(rows) < 2:
        print(f"VERDICT: UNCLEAN (spread > {CLEAN_SPREAD:.0%}, or too few attacks) — "
              "Fury damage stays DORMANT-LABELED.")
        print("  ⚠ Check the EXPECTED side before blaming the meter: a global "
              "multiplier cancels in an attack-to-attack ratio, so a spread this "
              "shape is a per-attack baseline disagreement, not Fury noise.")
        return 1
    print("VERDICT: CLEAN — the ruled ladder applies as ratios of this anchor "
          "(farm=anchor; team/itrial=×60/75; solo=×50/75; AV=×65/75), stated on "
          "every label.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
