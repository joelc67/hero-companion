#!/usr/bin/env python3
"""
extract_boost_level_tables.py - pin the game's OWN enhancement level-difference
tables out of the client, so nothing about exemplaring is quoted from memory.

Joel, 2026-08-02: "pin the enhancement rule from the client bins."

WHAT THE CLIENT HOLDS (bin.pigg):
  boost_effect_above.bin     enhancement ABOVE your combat level
  boost_effect_below.bin     enhancement BELOW your combat level
  boost_effect_boosters.bin  the +1..+5 boost catalysts
  exemplar_handicaps.bin     per-level exemplar handicap table (50 records)

FORMAT (Parse7, same family the Bin Crawler reads):
  8b "CrypticS" | 4b CRC | u16 len + "Parse7" | u4 string-table size + table
  | pad to 4 | u4 data-block size | u4 RECORD COUNT | float32[] little-endian

The record count is what makes this trustworthy rather than a guess at where an
array starts: above/below both declare 4, and 4 floats is exactly what follows.

⚠ THE BOUND IS THE FINDING. Both tables define FOUR entries - differences of
0, 1, 2 and 3 levels. The client has no scaling entry beyond that, which is why
a level-50 enhancement does nothing for you exemplared to 25: you are 25 levels
outside a table that stops at 3. Attuned and Superior pieces carry no fixed
level, so they follow your combat level instead and keep working.

⚠ CROSS-VALIDATION, worth keeping: boost_effect_boosters is
[1.0, 1.05, 1.1, 1.15, 1.2, 1.25] - exactly the x(1 + 0.05 * boost) the engine
has been applying for +1..+5 since the Mids import. A shipped constant confirmed
against the game rather than assumed.

Run:  python tools/extract_boost_level_tables.py [--json]
"""
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WRANGLER = os.path.join(HERE, "gamedata", "pigg-wrangler")
sys.path.insert(0, WRANGLER)
from pigg_wrangler.pigg import PiggArchive  # noqa: E402

PIGG = r"C:\Games\HC2\assets\live\bin.pigg"
TABLES = {
    "boost_effect_above": "bin/boost_effect_above.bin",
    "boost_effect_below": "bin/boost_effect_below.bin",
    "boost_effect_boosters": "bin/boost_effect_boosters.bin",
    "exemplar_handicaps": "bin/exemplar_handicaps.bin",
}
# What the client MUST still say. If a patch changes these, this fails loudly
# rather than letting the app keep quoting a stale rule.
EXPECT = {
    "boost_effect_above": [1.0, 1.05, 1.1, 1.15],
    "boost_effect_below": [1.0, 0.9, 0.8, 0.7],
    "boost_effect_boosters": [1.0, 1.05, 1.1, 1.15, 1.2, 1.25],
}


def read_floats(raw):
    """(record_count, [float, ...]) from a Parse7 float table."""
    strtab = struct.unpack_from("<I", raw, 20)[0]
    off = (24 + strtab + 3) & ~3
    _dsize, count = struct.unpack_from("<II", raw, off)
    start = off + 8
    n = (len(raw) - start) // 4
    return count, [round(struct.unpack_from("<f", raw, start + 4 * i)[0], 6)
                   for i in range(n)]


def main():
    if not os.path.exists(PIGG):
        print(f"client not found: {PIGG}")
        return 1
    a = PiggArchive(PIGG)
    out, fails = {}, []
    for key, path in TABLES.items():
        count, vals = read_floats(a.extract(path))
        out[key] = {"record_count": count, "values": vals}
        exp = EXPECT.get(key)
        if exp is not None:
            got = vals[:len(exp)]
            ok = count == len(exp) and got == exp
            print(f"  {'OK  ' if ok else 'FAIL'} {key:24s} count={count:3d}  {got}")
            if not ok:
                fails.append(f"{key}: expected count {len(exp)} {exp}, got {count} {got}")
        else:
            print(f"  ---- {key:24s} count={count:3d}  {len(vals)} floats"
                  f"  distinct={sorted(set(vals))[:6]}")

    print("\nTHE RULE, from the client's own tables:")
    print("  enhancement ABOVE your combat level : +5% per level, defined only to +3")
    print("  enhancement BELOW your combat level : -10% per level, defined only to -3")
    print("  boost catalysts (+1..+5)            : +5% each, to +25%")
    print("  Both level tables stop at a difference of 3. A level-50 enhancement is")
    print("  far outside that when exemplared to 25; attuned/Superior pieces carry no")
    print("  fixed level and follow your combat level instead.")

    if "--json" in sys.argv:
        dest = os.path.join(ROOT, "data", "boost_level_tables.json")
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1)
        print(f"\nwritten: {dest}")
    if fails:
        print("\nCLIENT DISAGREES WITH THE PINNED RULE:")
        for f in fails:
            print("  " + f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
