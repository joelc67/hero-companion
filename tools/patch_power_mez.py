"""Back-fill POWER-GRANTED mez protection and mez resistance.

THE ERROR, and it is the largest of its class found so far
----------------------------------------------------------
Our data carries mez under NO name at all. A search across all 5,660 powers and
every effect bucket for Held / Stunned / Sleep / Immobilized / Terrorized /
Confused / "mez" / "protect" returns nothing. Mez protection is the single
reason armoured archetypes are playable, and the tool has never seen it.

THIS IS THE THIRD INSTANCE OF ONE PATTERN, which makes it a class:
  * knockback protection - noticed, written down as a stated understatement
  * slow resistance      - not noticed, patched 2026-08-08
  * mez protection AND mez duration resistance - not noticed, this file
In each case an axis IS scored, fed only by the IO set-bonus back-fill, while
the POWERS that actually grant it contribute nothing.

⚠⚠ TWO DIFFERENT EFFECTS, AND CONFLATING THEM WOULD BE WORSE THAN THE GAP.
The client puts both on the same template group, distinguished ONLY by aspect:
    aspect=Current     scale -30.0  -> PROTECTION: a magnitude threshold that
                                       stops the mez landing at all
    aspect=Resistance  scale   3.0  -> RESISTANCE: shortens the duration
A magnitude and a duration multiplier are not interchangeable. This is the same
aspect trap that would have turned 78 recharge buffs into slow resistances, so
the two are written as SEPARATE effect names and never merged.

⚠ THE SIGN IS THE GAME'S AND IS STORED VERBATIM. Protection arrives as -30.0.
That is the client's own convention for a magnitude that offsets incoming mez;
it is NOT reinterpreted here, because guessing at sign conventions is exactly
how a protection value becomes a penalty.

STATED EXCLUSIONS, printed every run: gated groups (conditional), NPC/AV tables,
tables the engine cannot resolve.

NOT SCORED YET, deliberately. `_add_power_effect` has no MezProtection or
MezResist branch, so these land inert exactly as the v39 damage rows and the
slow-resist rows did before their consumers existed. Data first, consumer
second, each provable alone - and champion exposure gets counted before any
branch is added. ⚠ Mez DURATION is already scored from set bonuses via
build_control_output, so whoever wires the consumer must check for
double-counting there, the way Defiance had to be checked.

⚠ powers.json is COMPACT single-line. Read binary, write binary, no indent.
Usage:  python tools/patch_power_mez.py [--check]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POWERS = os.path.join(ROOT, "data", "powers.json")
CRAWL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
TABLES = os.path.join(ROOT, "data", "modifier_tables.json")

MARK = "mez_row"
MEZ = {"Held", "Stunned", "Sleep", "Immobilized", "Terrorized", "Confused",
       "Untouchable", "Intangible"}
NPC_TABLES = {"melee_archvillain_res", "ranged_archvillain_res"}
# aspect -> the effect name we store it under. Separate on purpose.
ASPECT_EFFECT = {"Current": "MezProtection", "Resistance": "MezResist"}


def _seconds(d):
    if d is None:
        return None
    if isinstance(d, (int, float)):
        return float(d)
    try:
        return float(str(d).strip().split()[0])
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
                    r = json.load(fh)
            except Exception:  # noqa: BLE001
                continue
            if r.get("full_name"):
                out[r["full_name"]] = r
    return out


def mez_rows(crec):
    rows = []
    for g in (crec.get("effects") or []):
        if (g.get("requires_expression") or "").strip():
            continue
        for t in (g.get("templates") or []):
            if t.get("target") != "Self":
                continue
            if (t.get("table") or "").lower() in NPC_TABLES:
                continue
            eff = ASPECT_EFFECT.get(t.get("aspect"))
            if not eff:
                continue
            types = [a for a in (t.get("attribs") or []) if a in MEZ]
            if not types:
                continue
            scale = t.get("scale")
            if scale is None or scale == 0:
                continue
            for mt in types:
                rows.append({"effect": eff, "mez": mt, "scale": float(scale),
                             "dur": _seconds(t.get("duration")),
                             "table": t.get("table"), "stack": t.get("stack")})
    return rows


def gated_only(crec):
    g_ = u_ = 0
    for g in (crec.get("effects") or []):
        for t in (g.get("templates") or []):
            if (t.get("target") != "Self"
                    or t.get("aspect") not in ASPECT_EFFECT
                    or not (set(t.get("attribs") or []) & MEZ)
                    or not (t.get("scale") or 0)):
                continue
            if (g.get("requires_expression") or "").strip():
                g_ += 1
            else:
                u_ += 1
    return g_ > 0 and u_ == 0


def main():
    check = "--check" in sys.argv
    raw = open(POWERS, "rb").read()
    data = json.loads(raw.decode("utf-8"))
    orig = json.loads(raw.decode("utf-8"))
    client = client_index()
    known = set(json.load(open(TABLES, encoding="utf-8"))["tables"])

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

    covered = expected = patched = added = 0
    gated, no_tbl, prot, res = [], {}, 0, 0
    for _ps, lst in data.items():
        for p in lst:
            c = client.get(p["full_name"])
            if not c:
                continue
            covered += 1
            rows = mez_rows(c)
            if not rows:
                if gated_only(c):
                    gated.append(p["full_name"])
                continue
            bad = [r for r in rows if r["table"] not in known]
            if bad:
                no_tbl.setdefault(bad[0]["table"], set()).add(p["full_name"])
                rows = [r for r in rows if r["table"] in known]
            if not rows:
                continue
            expected += 1
            # RULE 2: do we already carry mez under ANY name on this power?
            if any("mez" in str(e.get("effect", "")).lower()
                   or str(e.get("effect", "")) in ASPECT_EFFECT.values()
                   or str(e.get("damage_type", "")) in MEZ
                   for e in (p.get("self_effects") or [])):
                continue
            if not check:
                fx = p.setdefault("self_effects", [])
                for r in rows:
                    fx.append({
                        "effect": r["effect"],
                        "damage_type": r["mez"],
                        "scale": r["scale"],          # the game's sign, verbatim
                        "nmag": 1.0,
                        "modifier_table": r["table"],
                        "enhance_aspect": "None",
                        "ed_schedule": 0,
                        "pv_mode": 0,
                        "duration": r["dur"],
                        "stack": r["stack"],
                        MARK: True,
                    })
            for r in rows:
                if r["effect"] == "MezProtection":
                    prot += 1
                else:
                    res += 1
            added += len(rows)
            patched += 1

    print(f"our powers covered by the client       : {covered}")
    print(f"client grants power mez prot/resist    : {expected}   <- denominator")
    print(f"  {'would patch' if check else 'patched'}                           : {patched}")
    print(f"  rows {'would be ' if check else ''}added                    : {added}"
          f"   (MezProtection {prot} / MezResist {res})")
    for t, fns in sorted(no_tbl.items()):
        print(f"STATED EXCLUSION, unresolvable table ({t}): {len(fns)}")
    print(f"STATED EXCLUSION, gated-only (conditional): {len(gated)}")
    print("NOT SCORED YET: no MezProtection/MezResist branch in _add_power_effect. "
          "Mez DURATION is already scored from set bonuses - check for "
          "double-counting before wiring a consumer.")

    if expected == 0:
        print("\nFAIL: found nothing - client index probably empty")
        sys.exit(1)
    if check:
        return

    out = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    probe = json.loads(out.decode("utf-8"))
    for src in (probe, orig):
        for _ps, lst in src.items():
            for p in lst:
                fx = p.get("self_effects")
                if fx:
                    p["self_effects"] = [e for e in fx if not e.get(MARK)]
    a = json.dumps(probe, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    b = json.dumps(orig, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if a != b:
        print("\nINVARIANCE FAILED - refusing to write")
        sys.exit(2)
    print("invariance: stripping the added rows reproduces the baseline exactly")
    open(POWERS, "wb").write(out)
    print(f"wrote {POWERS} ({len(out):,} bytes, was {len(raw):,})")


if __name__ == "__main__":
    main()
