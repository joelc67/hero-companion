"""ADDITIVE patcher (the standing powers.json family — NEVER re-parse): back-
fill `interrupt_time` from the game client's own records.

Why: parse_mids never kept interrupt data, so every record reads as
uninterruptible. The v31 AFK sustain assessment (Joel's ruling, 2026-07-16)
must not certify an INTERRUPTIBLE heal as the auto-fire sustain power — in the
asteroid scrum every incoming hit during the interrupt window cancels the cast
(caught on the very first stamp: Aid Self, client interrupt_time 1.0s, priced
as 15.7 HP/s of AFK sustain it cannot deliver).

Source of every value: the full Bin Crawler export from the client piggs
(tools/gamedata/bin-crawler/out_full, exported 2026-07-16 from
C:/Games/HC2/assets/live — 10,708 player powers, 64 categories). Only records
whose full_name matches exactly are touched; the count of client-side
interruptible powers with NO powers.json match is printed for visibility
(alias-map divergence — the standing reconciliation item, not this patcher's
job). Verifies powers.json is byte-identical after stripping the added key;
hard-fails on any drift.

Run:  py tools\\patch_interrupt_times.py
"""
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "powers.json")
EXPORTS = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")


def main():
    interrupt_by_name = {}
    n_files = 0
    for fp in glob.iglob(os.path.join(EXPORTS, "**", "*.json"), recursive=True):
        if os.path.basename(fp) == "manifest.json":
            continue
        n_files += 1
        try:
            rec = json.load(open(fp, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        rows = rec if isinstance(rec, list) else [rec]
        for r in rows:
            it = r.get("interrupt_time") or 0
            fn = r.get("full_name")
            if fn and it > 0:
                interrupt_by_name[fn] = round(float(it), 2)
    if not interrupt_by_name:
        raise SystemExit("FAIL: no interruptible powers found in the export "
                         "tree — wrong path or broken export")
    print(f"client export: {n_files} files scanned, "
          f"{len(interrupt_by_name)} interruptible powers")

    original = open(PATH, encoding="utf-8").read()
    data = json.loads(original)

    # Coverage denominator computed OUTSIDE the patch loop (the standing rule).
    ours = {q.get("full_name")
            for rows in data.values() if isinstance(rows, list)
            for q in rows if isinstance(q, dict)}
    expected = sorted(n for n in interrupt_by_name if n in ours)
    unmatched = len(interrupt_by_name) - len(expected)

    patched = 0
    for rows in data.values():
        if not isinstance(rows, list):
            continue
        for q in rows:
            it = interrupt_by_name.get(q.get("full_name"))
            if it is not None:
                q["interrupt_time"] = it
                patched += 1
    print(f"{patched} of {len(expected)} matchable records patched "
          f"({unmatched} client-side interruptible powers have no powers.json "
          f"match — alias-map divergence, listed nowhere else)")
    if patched != len(expected):
        raise SystemExit("== COVERAGE FAILURE: matchable record count drifted "
                         "mid-patch — investigate before shipping ==")

    # Byte-identity check: stripping the added key must reproduce the input.
    stripped = json.loads(json.dumps(data))
    for rows in stripped.values():
        if not isinstance(rows, list):
            continue
        for q in rows:
            q.pop("interrupt_time", None)
    if json.dumps(stripped, sort_keys=True) != json.dumps(json.loads(original),
                                                          sort_keys=True):
        raise SystemExit("== SAFETY FAILURE: patch touched more than the added "
                         "key — nothing written ==")
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print("data/powers.json updated (additive; run reality checks after)")


if __name__ == "__main__":
    main()
