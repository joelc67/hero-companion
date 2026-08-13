"""Collapse EXACT-duplicate effect rows in data/powers.json.

THE DEFECT (found 2026-08-14 by the population-search experiment, confirmed
against the client export): the client stores an attack's damage once per
CONDITION — base hit, Scrapper crit, Stalker hidden, Corruptor scourge,
Controller containment, PvP — as separate effect groups whose values are
often identical and whose conditions differ (client Boxing: 14 groups).
Our parse dropped the conditions and kept the rows, leaving unconditioned
IDENTICAL copies that the engine then SUMS: slotted Boxing displayed 442
damage (real: ~40 base). 924 powers, ~1,970 surplus rows, in every effect
list; shipped in every release (1,944 of the surplus rows predate the marked
August client-sync passes).

THE FIX: within each effect list of each power, byte-identical rows collapse
to ONE. Rows differing in ANY field (chance, tags, pv_mode, markers) are
untouched — which structurally protects the v44 crit rows (they carry their
own chance) and every genuine multi-component attack (different type/value).

Additive-patcher family rules: byte-preserving round-trip proven before any
write; compact single-line serialisation; idempotent (second run = 0
changes); coverage denominator printed; --check mode fails if any duplicate
remains.
"""
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "powers.json")
LISTS = ("damage_effects", "buff_effects", "debuff_effects",
         "control_effects", "heal_effects")


def dedup(data):
    powers_touched = rows_removed = total_powers = 0
    by_list = collections.Counter()
    for ps, v in data.items():
        recs = v if isinstance(v, list) else list(v.values())
        for rec in recs:
            if not isinstance(rec, dict):
                continue
            total_powers += 1
            touched = False
            for lname in LISTS:
                rows = rec.get(lname)
                if not rows:
                    continue
                seen, out = set(), []
                for r in rows:
                    k = json.dumps(r, sort_keys=True)
                    if k in seen:
                        rows_removed += 1
                        by_list[lname] += 1
                        touched = True
                        continue
                    seen.add(k)
                    out.append(r)
                if touched:
                    rec[lname] = out
            if touched:
                powers_touched += 1
    return total_powers, powers_touched, rows_removed, by_list


def main():
    check = "--check" in sys.argv
    raw = open(PATH, "rb").read()
    text = raw.decode("utf-8")
    data = json.loads(text)

    # Prove the serializer reproduces the file byte-for-byte BEFORE transforming.
    rt = json.dumps(data, ensure_ascii=False, separators=(",", ": "))
    if rt.encode("utf-8") != raw:
        for seps in ((",", ":"), (", ", ": ")):
            rt = json.dumps(data, ensure_ascii=False, separators=seps)
            if rt.encode("utf-8") == raw:
                break
        else:
            raise SystemExit("REFUSING: cannot reproduce powers.json byte-identical "
                             "before transform — serializer convention unknown")
        seps_used = seps
    else:
        seps_used = (",", ": ")

    total, touched, removed, by_list = dedup(data)
    print(f"{total} power records scanned; {touched} powers held exact-duplicate "
          f"rows; {removed} surplus rows removed  {dict(by_list)}")
    if check:
        if removed:
            raise SystemExit(f"CHECK FAILED: {removed} duplicate rows present")
        print("CHECK OK: zero exact-duplicate effect rows")
        return
    if not removed:
        print("nothing to do (idempotent re-run)")
        return
    out = json.dumps(data, ensure_ascii=False, separators=seps_used)
    open(PATH, "wb").write(out.encode("utf-8"))
    print(f"written: {PATH}")


if __name__ == "__main__":
    main()
