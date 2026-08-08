"""Back-fill POWER-GRANTED DEFENCE DEBUFF RESISTANCE (DDR), which our data has
never carried on any power.

THE ERROR
---------
Every defence armour set grants resistance to defence debuffs, and the game says
so in its own words. Super Reflexes' Agile prints

    "Auto: Self +DEF(Ranged), Res(DeBuff DEF), Res(DMG, Special)"

and Invulnerability's Tough Hide prints "+RES (Debuff DEF)". Ninety-seven of our
records carry the +DEF half and none of the Res(DeBuff DEF) half.

That matters because the scorer ALREADY applies incoming defence-debuff pressure
and already assumes nobody resists it. first_principles:

    # DDR haircut (v10): a squishy has ZERO defense-debuff resistance
    ddr_in = sc.get("def_debuff_in", 0.0)          # 0.03 general .. 0.10 AV
    def_ml = max(_def_against(...) - ddr_in, 0.0)

So the same flat haircut lands on a Blaster and on Super Reflexes, the set whose
whole identity is that the haircut does not land on it. Unlike the slow-resist
and mez families this needs NO new scenario physics from anyone - the incoming
pressure term has existed since v10; only the resistance to it was missing.

Found by widening reality_check_effect_coverage.py past its five families:
Base_Defense at aspect=Resistance was the largest undispositioned family in the
whole client export, 97 powers.

⚠ THE ASPECT IS THE WHOLE FILTER, exactly as it was for slow resistance.
Self-targeted Base_Defense templates come in two kinds and they are opposites:
    aspect=Resistance  -> DDR                     (Agile 0.2, Tough Hide 0.25)
    aspect=Strength    -> a DEFENCE-strength buff  (the Alpha boost records)
Patching on the attrib alone would have turned boost definitions into armour.

UNITS, RESOLVED NOT ASSUMED. value = scale x table[at_column], the same
resolution the engine uses for every other row, and the same one that produced
Unyielding's real 10.4 mez protection. Scrapper Melee_Res_Boolean = 0.346, so
Agile is 0.2 x 0.346 = 6.9% and Tough Hide is 0.25 x Melee_Ones(1.0) = 25%.
These are fractions, like totals["slow_resist"].

STATED EXCLUSIONS, printed every run:
  * Melee_ArchVillain_Res / Ranged_ArchVillain_Res - NPC records, not player powers.
  * gated groups - conditional, a different claim, deliberately not guessed at.
  * any row naming a modifier table the engine cannot resolve.

⚠ NOT SCORED BY THIS FILE, and that is deliberate - data first, consumer second,
each provable on its own (the v39/v40 order). The rows land inert until
_add_power_effect grows a branch and champion exposure has been counted.

⚠ powers.json is COMPACT single-line. Read binary, write binary, no indent.
Usage:  python tools/patch_power_def_debuff_resist.py [--check]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POWERS = os.path.join(ROOT, "data", "powers.json")
CRAWL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
TABLES = os.path.join(ROOT, "data", "modifier_tables.json")

MARK = "ddr_row"                  # identifies and makes these rows removable
ATTRIB = "Base_Defense"
NPC_TABLES = {"Melee_ArchVillain_Res", "Ranged_ArchVillain_Res"}


def _seconds(dur):
    if dur is None:
        return None
    if isinstance(dur, (int, float)):
        return float(dur)
    try:
        return float(str(dur).strip().split()[0])
    except (ValueError, IndexError):
        return None


def client_index():
    out = {}
    for dirpath, _dirs, files in os.walk(CRAWL):
        for fn in files:
            if not fn.endswith(".json") or fn == "index.json":
                continue
            try:
                with open(os.path.join(dirpath, fn), encoding="utf-8") as fh:
                    rec = json.load(fh)
            except Exception:  # noqa: BLE001
                continue
            if rec.get("full_name"):
                out[rec["full_name"]] = rec
    return out


def ddr_rows(crec):
    """Ungated, self-targeted, aspect=Resistance Base_Defense templates."""
    rows = []
    for grp in (crec.get("effects") or []):
        if (grp.get("requires_expression") or "").strip():
            continue
        for t in (grp.get("templates") or []):
            if t.get("target") != "Self":
                continue
            if t.get("aspect") != "Resistance":          # <- the whole filter
                continue
            if ATTRIB not in (t.get("attribs") or []):
                continue
            if (t.get("table") or "") in NPC_TABLES:
                continue
            scale = t.get("scale")
            if scale is None or scale == 0:
                continue
            rows.append({"scale": float(scale), "dur": _seconds(t.get("duration")),
                         "table": t.get("table"), "stack": t.get("stack")})
    return rows


def gated_only(crec):
    gated = ungated = 0
    for grp in (crec.get("effects") or []):
        for t in (grp.get("templates") or []):
            if (t.get("target") != "Self" or t.get("aspect") != "Resistance"
                    or ATTRIB not in (t.get("attribs") or [])):
                continue
            if (grp.get("requires_expression") or "").strip():
                gated += 1
            else:
                ungated += 1
    return gated > 0 and ungated == 0


def main():
    check_only = "--check" in sys.argv
    raw = open(POWERS, "rb").read()
    data = json.loads(raw.decode("utf-8"))
    orig = json.loads(raw.decode("utf-8"))
    client = client_index()
    known_tables = set(json.load(open(TABLES, encoding="utf-8"))["tables"])

    # IDEMPOTENT: strip our own previous rows, then re-derive from the client.
    stripped = 0
    for _ps, lst in data.items():
        for p in lst:
            fx = p.get("self_effects")
            if not fx:
                continue
            kept = [e for e in fx if not e.get(MARK)]
            stripped += len(fx) - len(kept)
            if len(kept) != len(fx):
                p["self_effects"] = kept
    if stripped:
        print(f"(re-run: stripped {stripped} rows from a previous pass)")

    covered = expected = patched = rows_added = 0
    gated_excluded, no_table = [], {}
    for _ps, lst in data.items():
        for p in lst:
            crec = client.get(p["full_name"])
            if not crec:
                continue
            covered += 1
            rows = ddr_rows(crec)
            if not rows:
                if gated_only(crec):
                    gated_excluded.append(p["full_name"])
                continue
            bad = [r for r in rows if r["table"] not in known_tables]
            if bad:
                no_table.setdefault(bad[0]["table"], set()).add(p["full_name"])
                rows = [r for r in rows if r["table"] in known_tables]
            if not rows:
                continue
            expected += 1
            # ⚠ ask whether we already carry it under ANY name before adding -
            # the lesson from the 121 phantom -ToHit debuffs (one capital B).
            if any(str(e.get("effect", "")).lower() in ("defdebuffresist", "ddr")
                   or (e.get("effect") == "Resistance"
                       and str(e.get("damage_type")) == "Base_Defense")
                   for e in (p.get("self_effects") or [])):
                continue
            if not check_only:
                fx = p.setdefault("self_effects", [])
                for r in rows:
                    fx.append({
                        "effect": "DefDebuffResist",
                        "damage_type": "None",
                        "scale": r["scale"],
                        "nmag": 1.0,
                        "modifier_table": r["table"],
                        # DDR takes no enhancement in game - no IO category
                        # names it, which is why it has no aspect here.
                        "enhance_aspect": "None",
                        "ed_schedule": 0,
                        "pv_mode": 0,
                        "duration": r["dur"],
                        "stack": r["stack"],
                        # ⚠ A CLICK MUST NOT READ AS ALWAYS-ON. Elude, Overload
                        # and Kuji-In Retsu grant the largest DDR in the game
                        # for 180 seconds on a very long recharge; the toggles
                        # and autos beside them are permanent. `mode` +
                        # `host_recharge` are exactly what engine's v39
                        # _mode_duty_cycle needs to tell the two apart, so they
                        # ride here rather than being re-derived later.
                        "mode": True,
                        "host_recharge": p.get("base_recharge"),
                        MARK: True,
                    })
            rows_added += len(rows)
            patched += 1

    print(f"our powers covered by the client export     : {covered}")
    print(f"client grants POWER defence-debuff resist   : {expected}   <- denominator")
    print(f"  {'would patch' if check_only else 'patched'}                               : {patched}")
    print(f"  rows {'would be ' if check_only else ''}added                        : {rows_added}")
    for t, fns in sorted(no_table.items()):
        print(f"STATED EXCLUSION, table the engine lacks ({t}): {len(fns)}")
    print(f"STATED EXCLUSION, gated-only (conditional)  : {len(gated_excluded)}")
    print("STATED EXCLUSION, aspect=Strength Base_Defense rows are not touched "
          "(the Alpha boost definitions - defence STRENGTH, not DDR)")
    print("STATED EXCLUSION, NPC/ArchVillain resistance tables")

    if expected == 0:
        print("\nFAIL: found nothing - the client index is probably empty")
        sys.exit(1)
    if check_only:
        return

    out = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    probe = json.loads(out.decode("utf-8"))
    for src in (probe, orig):
        for _ps, lst in src.items():
            for p in lst:
                fx = p.get("self_effects")
                if fx:
                    p["self_effects"] = [e for e in fx if not e.get(MARK)]
    if (json.dumps(probe, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            != json.dumps(orig, separators=(",", ":"), ensure_ascii=False).encode("utf-8")):
        print("\nINVARIANCE FAILED: stripping the added rows does not reproduce the "
              "baseline - refusing to write")
        sys.exit(2)
    print("invariance: stripping the added rows reproduces the baseline exactly")
    open(POWERS, "wb").write(out)
    print(f"wrote {POWERS} ({len(out):,} bytes, was {len(raw):,})")


if __name__ == "__main__":
    main()
