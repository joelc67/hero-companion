"""Additive patcher: summon LEVEL SHIFT from the client's own Create_Entity tables.

WHY (Piece 2 / model v38, 2026-07-28): a summon template's modifier table IS the
client's level-setting shell (bin_crawler parser: `Level`/`Levelminus`/
`Levelminus2` fronts). `*_Levelminus` ⇒ the pet spawns 1 level below the caster
(Fire Imps), `*_Levelminus2` ⇒ 2 below, `*_Level`/`*_Ones` ⇒ caster level.
MM henchman templates are uniformly `Ranged_Ones` — their tier shift is the
count-gated COMBAT-LEVEL rule (wiki-sourced, docs/pet-tohit-sources.md) and is
applied by CLASS in the engine, never from this field.

Adds `level_shift` (0/1/2) to every data/summons.json powers entry with a
matching client export record. Coverage denominator = every powers entry;
misses listed. Idempotent; report-only without --write.

Run:  py tools\\patch_summon_level_shift.py [--write]
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUMMONS = os.path.join(ROOT, "data", "summons.json")
OUT_FULL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")

sys.stdout.reconfigure(encoding="utf-8")


def client_shift_index():
    """full_name -> level shift (max over its Create_Entity templates; mixed
    shifts within one power are reported — none observed in the live export)."""
    idx, mixed = {}, []
    for f in glob.glob(os.path.join(OUT_FULL, "*", "*", "*.json")):
        if os.path.basename(f) == "index.json":
            continue
        try:
            rec = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        fn = rec.get("full_name")
        if not fn:
            continue
        shifts = set()
        for eff in rec.get("effects") or []:
            for t in eff.get("templates") or []:
                if "Create_Entity" not in (t.get("attribs") or []):
                    continue
                table = t.get("table") or ""
                if re.search(r"Levelminus2$", table):
                    shifts.add(2)
                elif re.search(r"Levelminus$", table):
                    shifts.add(1)
                else:
                    shifts.add(0)
        if shifts:
            if len(shifts) > 1:
                mixed.append(fn)
            idx[fn] = max(shifts)
    return idx, mixed


def main(write=False):
    raw = open(SUMMONS, "rb").read()
    data = json.loads(raw)
    idx, mixed = client_shift_index()
    print(f"client export: {len(idx)} summon powers with Create_Entity templates")
    if mixed:
        print(f"  MIXED shifts within one power ({len(mixed)}): {mixed}")

    # NAMED EXCLUSIONS (stated, never silently narrowed): Boosts.* (ATO
    # grant shells) and Temporary_Powers.* are categories the client export
    # does not include (v33 finding), and neither feeds the scored pet-DPS
    # model. They keep no level_shift; absent = engine default 0.
    _EXCLUDED = ("Boosts.", "Temporary_Powers.")
    powers = data.get("powers") or {}
    matched = changed = excluded = 0
    misses = []
    nonzero = []
    for fn, spec in powers.items():
        if fn.startswith(_EXCLUDED):
            excluded += 1
            continue
        sh = idx.get(fn)
        if sh is None:
            misses.append(fn)
            continue
        matched += 1
        if spec.get("level_shift") != sh:
            spec["level_shift"] = sh
            changed += 1
        if sh:
            nonzero.append((fn, sh))
    in_scope = len(powers) - excluded
    print(f"{matched} of {in_scope} in-scope summons.json powers matched "
          f"({changed} changed this run; {excluded} excluded by name — stated "
          f"above); {len(nonzero)} carry a nonzero shift")
    for fn, sh in nonzero:
        print(f"   -{sh}: {fn}")
    if misses:
        print(f"  unmatched ({len(misses)}):")
        for m in misses:
            print(f"    {m}")
    if matched < 0.9 * max(in_scope, 1):
        print("HARD FAIL: coverage below 90% — not writing.")
        sys.exit(1)
    if not write:
        print("(report only — rerun with --write to apply)")
        return
    # summons.json is pretty-printed? Match the existing serialization exactly:
    # detect indent from the original bytes.
    indent = 1 if raw.startswith(b"{\n ") else None
    out = json.dumps(data, indent=indent,
                     separators=(",", ": ") if indent else (",", ":"),
                     ensure_ascii=False).encode("utf-8")
    check = json.loads(out)
    for spec in (check.get("powers") or {}).values():
        spec.pop("level_shift", None)
    orig = json.loads(raw)
    for spec in (orig.get("powers") or {}).values():
        spec.pop("level_shift", None)
    if check != orig:
        print("HARD FAIL: strip-verify mismatch — not writing.")
        sys.exit(1)
    with open(SUMMONS, "wb") as f:
        f.write(out)
    print(f"written: {SUMMONS}")


if __name__ == "__main__":
    main(write="--write" in sys.argv)
