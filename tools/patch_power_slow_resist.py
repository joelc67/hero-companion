"""Back-fill POWER-GRANTED slow resistance, which our data has never carried.

THE ERROR
---------
Wet Ice, Permafrost, Unyielding, Obsidian Shield, Plasma Shield, Energy
Protection, Resist Elements, Quickness, Time Lord and the rest grant resistance
to -recharge/slow in game. Our records carry none of it: those powers hold only
their defence and resistance rows.

That matters because slow resistance IS a scored term (v30: recharge-bound
output share x the scenario's slow_in physics) - fed ONLY by the 103-record
set-bonus back-fill. So a build is credited for slow resist that came from IO
set bonuses and gets ZERO from the armour powers that actually provide it. It is
the same shape as the knockback-protection gap, which was at least noticed and
written down as a stated understatement; this one never was.

Found by classifying the `Melee_Ones` modifier table (1,277 powers) against the
client - the first table of 45, and the only real defect in 4,306 instances.

⚠ THE ASPECT IS THE WHOLE FILTER, AND SKIPPING IT WOULD HAVE CORRUPTED DATA.
Self-targeted RechargeTime templates come in two kinds and they are opposites:
    aspect=Resistance  x223  -> slow RESISTANCE   (Quickness 0.4, Time Lord 0.6)
    aspect=Strength    x78   -> a recharge BUFF   (Beta Decay, Metabolic Accel.)
Patching on the attrib alone would have turned 78 recharge buffs into
resistances. Only aspect == "Resistance" is taken.

STATED EXCLUSIONS, printed every run:
  * `Melee_ArchVillain_Res` (79) - NPC/AV records, not player powers.
  * gated groups - conditional, a different claim, deliberately not guessed at.
  * any row naming a modifier table the engine cannot resolve.

⚠ NOT YET SCORED, AND THAT IS DELIBERATE. `_add_power_effect` has no slow-resist
branch (its branches are Defense, Resistance, RechargeTime, Recovery,
Regeneration, HitPoints, ToHit, DamageBuff), so these rows land inert exactly as
the v39 damage rows did before their branch existed. Data first, consumer
second, each provable on its own. Champion exposure must be counted before the
branch is added, not before the data lands.

⚠ powers.json is COMPACT single-line. Read binary, write binary, no indent.
Usage:  python tools/patch_power_slow_resist.py [--check]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POWERS = os.path.join(ROOT, "data", "powers.json")
CRAWL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
TABLES = os.path.join(ROOT, "data", "modifier_tables.json")

MARK = "slow_resist_row"          # identifies and makes these rows removable
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


def slow_resist_rows(crec):
    """Ungated, self-targeted, aspect=Resistance RechargeTime templates."""
    rows = []
    for grp in (crec.get("effects") or []):
        if (grp.get("requires_expression") or "").strip():
            continue
        for t in (grp.get("templates") or []):
            if t.get("target") != "Self":
                continue
            if t.get("aspect") != "Resistance":          # <- the whole filter
                continue
            if "RechargeTime" not in (t.get("attribs") or []):
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
                    or "RechargeTime" not in (t.get("attribs") or [])):
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
            rows = slow_resist_rows(crec)
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
            if any("slow" in str(e.get("effect", "")).lower()
                   or (e.get("effect") == "Resistance"
                       and str(e.get("damage_type")) == "RechargeTime")
                   for e in (p.get("self_effects") or [])):
                continue
            if not check_only:
                fx = p.setdefault("self_effects", [])
                for r in rows:
                    fx.append({
                        "effect": "SlowResist",
                        "damage_type": "None",
                        "scale": r["scale"],
                        "nmag": 1.0,
                        "modifier_table": r["table"],
                        "enhance_aspect": "None",
                        "ed_schedule": 0,
                        "pv_mode": 0,
                        "duration": r["dur"],
                        "stack": r["stack"],
                        MARK: True,
                    })
            rows_added += len(rows)
            patched += 1

    print(f"our powers covered by the client export     : {covered}")
    print(f"client grants POWER slow resistance         : {expected}   <- denominator")
    print(f"  {'would patch' if check_only else 'patched'}                               : {patched}")
    print(f"  rows {'would be ' if check_only else ''}added                        : {rows_added}")
    for t, fns in sorted(no_table.items()):
        print(f"STATED EXCLUSION, table the engine lacks ({t}): {len(fns)}")
    print(f"STATED EXCLUSION, gated-only (conditional)  : {len(gated_excluded)}")
    print("STATED EXCLUSION, aspect=Strength recharge BUFFS are not touched (78 "
          "templates: Beta Decay, Metabolic Acceleration, ...)")
    print("STATED EXCLUSION, NPC/ArchVillain resistance tables")
    print("NOT SCORED YET: _add_power_effect has no slow-resist branch, so these "
          "rows are inert until one is added and champion exposure counted.")

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
