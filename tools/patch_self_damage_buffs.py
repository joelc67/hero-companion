"""Back-fill the self +DAMAGE buff the game gives 353 powers and our data drops.

THE ERROR
---------
The client ships, on each Build-Up-class power, a self-targeted `Strength`
template across the damage types - beside the ToHit one we already carry. Our
records keep only the ToHit half, because `parse_mids`'s Enhancement-relabel
allowlist is (RechargeTime, Recovery, Regeneration, ToHit, Accuracy): ToHit is
in it, Damage is not. Same family as the v28 accuracy and v29 heal-strength
bugs. Measured consequence before this patch: adding Aim to a build moved
displayed ST DPS by 0.0, and Rage had its -0.2 defence and -0.25 endurance
CRASH modelled with none of its +80% damage.

EVERY FIELD HERE IS THE GAME'S OWN
----------------------------------
Existence, `scale`, `duration`, the damage types, `stack`, `delay`, `flags` and
the modifier TABLE all come straight from the client export.
⚠ The table was very nearly an assumption. The crawler emits it as `table` (see
export_powers.py:240) and an earlier pass of this tool missed the key, inferred
`Melee_Buff_Dmg` from our own convention, and flagged it as unconfirmed. The
client states it outright, on every one of them including the Blaster and the
Corruptor: `Melee_Buff_Dmg`. It is now READ, never chosen. Resolved through the
engine's own `scale x nmag x table[AT column]`, Build Up is +100% Blaster and
Scrapper, +80% Brute/Defender/Stalker, +70% Tanker, +68% Corruptor/Dominator.
⚠ And the lookup corrected a real error on the way: AIM IS SCALE 5.0, NOT 8.0 -
Aim and Build Up are not the same buff, which an assumption would have flattened.

WHY THIS CANNOT MOVE A SCORE (two independent locks, both verified)
-------------------------------------------------------------------
1. Every one of these powers is `power_type` 0 (Click) and engine's totals loop
   only walks `ACTIVE_POWER_TYPES = {1, 2}`, so it never reaches them.
2. `_add_power_effect` has no Damage branch at all - the row would be dropped
   even if it arrived.
A self_effects-only DamageBuff is also caster-only by the v34 pet lever, so pet
damage cannot move either. The rows are therefore INERT AND HONEST: the data now
says what the game says, and nothing prices it until the mode/uptime model lands
with its ruling. `mode`, `mode_duration` and `host_recharge` are written beside
each row precisely so that model cannot later treat a 10-second buff on a
90-second recharge as though it were always on.

⚠ powers.json is COMPACT single-line. Read binary, write binary, no indent.
Usage:  python tools/patch_self_damage_buffs.py [--check]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POWERS = os.path.join(ROOT, "data", "powers.json")
CRAWL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
TABLES = os.path.join(ROOT, "data", "modifier_tables.json")

# client attrib -> our damage_type vocabulary (the names our damage_effects use)
DMG_TYPE = {
    "Smashing_Dmg": "Smashing", "Lethal_Dmg": "Lethal", "Fire_Dmg": "Fire",
    "Cold_Dmg": "Cold", "Energy_Dmg": "Energy",
    "Negative_Energy_Dmg": "Negative", "Psionic_Dmg": "Psionic",
    "Toxic_Dmg": "Toxic",
}
TABLE_FALLBACK = "Melee_Buff_Dmg"  # only if the client omits `table`; it never has so far
MARK = "mode"                     # the key that makes these rows identifiable and removable


def _seconds(dur):
    """The client writes durations as '10 seconds' / '12.50 seconds'."""
    if dur is None:
        return None
    if isinstance(dur, (int, float)):
        return float(dur)
    txt = str(dur).strip().split()
    try:
        return float(txt[0])
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


def gated_only(crec):
    """True when this power's ONLY self-damage templates sit behind a gate, so it
    is excluded above. Counted and printed rather than silently dropped - the
    coverage-denominator rule: a checker that cannot state its exclusions can lie."""
    gated = ungated = 0
    for grp in (crec.get("effects") or []):
        for t in (grp.get("templates") or []):
            if t.get("target") != "Self" or t.get("aspect") != "Strength":
                continue
            if not any(a in DMG_TYPE for a in (t.get("attribs") or [])):
                continue
            if (t.get("scale") or 0) <= 0:
                continue
            if (grp.get("requires_expression") or "").strip():
                gated += 1
            else:
                ungated += 1
    return gated > 0 and ungated == 0


def self_damage_rows(crec):
    """Every self-targeted damage Strength template the client gives this power."""
    rows = []
    for grp in (crec.get("effects") or []):
        # ⚠ A GATED group is conditional (Fiery Embrace's Global_Chance_Mod
        # sibling, the Corruptor Scourge ramps). Only ungated groups are an
        # unconditional self buff; a gated one is a different claim and is
        # deliberately left out rather than guessed at.
        if (grp.get("requires_expression") or "").strip():
            continue
        for t in (grp.get("templates") or []):
            if t.get("target") != "Self" or t.get("aspect") != "Strength":
                continue
            types = [DMG_TYPE[a] for a in (t.get("attribs") or []) if a in DMG_TYPE]
            if not types:
                continue
            scale = t.get("scale")
            dur = _seconds(t.get("duration"))
            if scale is None or scale == 0:
                # ⚠ ZERO-SCALE ROWS CARRY NO MAGNITUDE. Every Blaster blast has
                # one (DEFIANCE's magnitude is not in the template - it is
                # derived from cast time, which first_principles already does).
                # Writing them made 13 contexts look exposed and had me block a
                # re-cert over a double-count that could never fire.
                continue
            for dt in types:
                rows.append({
                    "dt": dt, "scale": float(scale), "dur": dur,
                    # ⚠ THE GAME DISTINGUISHES THESE AND SO MUST WE. Soul Drain
                    # carries TWO damage templates: scale 0.8 `Stack` (it
                    # accumulates per foe hit) and scale 4.0 `Replace` (flat).
                    # Written without `stack`, a later model would simply add
                    # them and lose the per-target behaviour entirely.
                    "stack": t.get("stack"),
                    # Rage's crash is scale -999 with delay 120.0 - the game
                    # fires it exactly as the 120s buff expires. Carried as a
                    # PENALTY row rather than dropped, so the crash is visible
                    # to whatever prices the buff.
                    "delay": t.get("delay"),
                    "flags": t.get("flags") or [],
                    # THE GAME'S OWN table name, read not chosen
                    "table": t.get("table") or TABLE_FALLBACK,
                })
    return rows


def has_damage_self(p):
    return any(("Damage" in str(fx.get("effect")) or fx.get("enhance_aspect") == "Damage")
               for fx in (p.get("self_effects") or []))


def main():
    check_only = "--check" in sys.argv
    # A row naming a table the engine cannot resolve is unusable, so it is
    # SKIPPED AND REPORTED rather than written. Universal rule, not a
    # named-power exclusion: today it catches AT_Uniqueness on Vigilance (the
    # Defender inherent, team-size dependent and already an open ruling), and
    # it will catch the next one without anybody editing this file.
    known_tables = set(json.load(open(TABLES, encoding="utf-8"))["tables"])
    raw = open(POWERS, "rb").read()
    data = json.loads(raw.decode("utf-8"))
    _orig = json.loads(raw.decode("utf-8"))
    client = client_index()

    covered = expected = patched = 0
    rows_added = 0
    skipped_have = 0
    gated_excluded = []
    no_table = {}
    r_tbl = lambda rs: rs[0]["table"]
    # IDEMPOTENT: drop any rows a previous run added, then re-derive from the
    # client. Without this the tool can only ever run once, and a fidelity fix
    # like carrying `stack` could never be applied.
    stripped = 0
    for _ps, lst in data.items():
        for p in lst:
            fx = p.get("self_effects")
            if not fx:
                continue
            kept = [e for e in fx if not e.get(MARK)]
            if len(kept) != len(fx):
                stripped += len(fx) - len(kept)
                p["self_effects"] = kept
    if stripped:
        print(f"(re-run: stripped {stripped} rows from a previous pass)")
    for _ps, lst in data.items():
        for p in lst:
            crec = client.get(p["full_name"])
            if not crec:
                continue
            covered += 1
            rows = self_damage_rows(crec)
            unresolvable = [r for r in rows if r["table"] not in known_tables]
            if unresolvable:
                no_table.setdefault(r_tbl(unresolvable), set()).add(p["full_name"])
                rows = [r for r in rows if r["table"] in known_tables]
            if not rows:
                if gated_only(crec):
                    gated_excluded.append(p["full_name"])
                continue
            expected += 1
            if has_damage_self(p):
                skipped_have += 1
                continue
            if not check_only:
                fx = p.setdefault("self_effects", [])
                for r in rows:
                    fx.append({
                        "effect": "DamageBuff",
                        "damage_type": r["dt"],
                        "scale": r["scale"],
                        "nmag": 1.0,
                        "modifier_table": r["table"],
                        "enhance_aspect": "Damage",
                        "ed_schedule": 0,
                        "pv_mode": 0,
                        "duration": r["dur"],
                        # the mode facts, so no future consumer can read a
                        # 10-second buff on a 90-second recharge as always-on
                        MARK: True,
                        "host_recharge": p.get("base_recharge"),
                        "stack": r["stack"],
                        "penalty": r["scale"] < 0,
                        **({"delay": r["delay"]} if r["delay"] else {}),
                        **({"flags": r["flags"]} if r["flags"] else {}),
                    })
            rows_added += len(rows)
            patched += 1

    print(f"our powers covered by the client export : {covered}")
    print(f"client gives a self +Damage buff        : {expected}   <- denominator")
    print(f"  already had one (must be 0 today)     : {skipped_have}")
    print(f"  {'would patch' if check_only else 'patched'}                          : {patched}")
    print(f"  effect rows {'would be ' if check_only else ''}added            : {rows_added}")
    for tname, fns in sorted(no_table.items()):
        print(f"STATED EXCLUSION, table the engine lacks ({tname}) : {len(fns)} power(s) "
              f"-> {sorted(fns)}")
    print(f"STATED EXCLUSION, self +Damage only behind a GATE : {len(gated_excluded)}")
    for fn in gated_excluded[:6]:
        print(f"    {fn}")
    if len(gated_excluded) > 6:
        print(f"    ... {len(gated_excluded) - 6} more (conditional - deliberately not guessed)")

    if patched + skipped_have != expected:
        print("\nFAIL: coverage short of the denominator")
        sys.exit(1)
    if expected == 0:
        print("\nFAIL: found nothing to patch - the client index is probably empty")
        sys.exit(1)
    if check_only:
        return

    # INVARIANCE: strip every row carrying MARK and the file must be byte-identical.
    out = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    probe = json.loads(out.decode("utf-8"))
    for _ps, lst in probe.items():
        for p in lst:
            fx = p.get("self_effects")
            if not fx:
                continue
            kept = [e for e in fx if not e.get(MARK)]
            if len(kept) != len(fx):
                if kept:
                    p["self_effects"] = kept
                else:
                    p["self_effects"] = []
    for _ps, lst in _orig.items():
        for p in lst:
            fx = p.get("self_effects")
            if fx:
                p["self_effects"] = [e for e in fx if not e.get(MARK)]
    baseline = json.dumps(_orig, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    reverted = json.dumps(probe, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if reverted != baseline:
        print("\nINVARIANCE FAILED: stripping the added rows does not reproduce the "
              "original bytes - refusing to write")
        sys.exit(2)
    print("invariance: stripping the added rows reproduces the original file byte for byte")

    open(POWERS, "wb").write(out)
    print(f"wrote {POWERS} ({len(out):,} bytes, was {len(raw):,})")


if __name__ == "__main__":
    main()
