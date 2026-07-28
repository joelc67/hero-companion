"""Additive patcher: pet-power inherent ACCURACY from the live client export.

WHY (Piece 2 / model v38, 2026-07-28): the wiki-verified pet hit model
(docs/pet-tohit-sources.md) multiplies each pet attack's chance by the POWER's
inherent accuracy — a client field on every pet attack record
(tools/gamedata/bin-crawler/out_full/<pet dirs>/*.json, field `accuracy`,
observed 0.8–1.35, mostly 1.0). Our Mids-era parse never carried it: 0 of 240
consumed pet damage powers had the field before this patch.

Family rules honored (CLAUDE.md additive-patcher family):
  - additive only: adds `accuracy` to existing records, touches nothing else
  - binary/newline-preserving compact write (powers.json is single-line JSON)
  - idempotent: a second run changes zero records
  - coverage denominator from an independent source: the pet powersets the
    engine actually consumes (data/summons.json entities + summon powers'
    pet_powersets), damage-carrying records only — printed, hard-fail < 90%
  - verify: stripping the added keys reproduces the original bytes

Run:  py tools\\patch_pet_accuracy.py          (report only)
      py tools\\patch_pet_accuracy.py --write  (apply)
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POWERS = os.path.join(ROOT, "data", "powers.json")
SUMMONS = os.path.join(ROOT, "data", "summons.json")
OUT_FULL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
# every export dir that holds PET powers (player-relevant pet categories)
PET_DIRS = ("mastermind_pets", "pets", "villain_pets", "kheldian_pets",
            "npc_pets", "incarnate_pets", "epic")

sys.stdout.reconfigure(encoding="utf-8")


def client_accuracy_index():
    idx = {}
    for d in PET_DIRS:
        for f in glob.glob(os.path.join(OUT_FULL, d, "*", "*.json")):
            if os.path.basename(f) == "index.json":
                continue
            try:
                rec = json.load(open(f, encoding="utf-8"))
            except Exception:  # noqa: BLE001 — a bad export file is reported, not fatal
                print(f"  ! unreadable export: {f}")
                continue
            fn = rec.get("full_name")
            acc = rec.get("accuracy")
            if fn and isinstance(acc, (int, float)):
                idx[fn] = float(acc)
    return idx


def main(write=False):
    raw = open(POWERS, "rb").read()
    data = json.loads(raw)
    summons = json.load(open(SUMMONS, encoding="utf-8"))

    consumed = set()
    for e in summons["entities"].values():
        consumed.update(e.get("powerset_full_names") or [])
    for ps, lst in data.items():
        for p in lst:
            consumed.update(p.get("pet_powersets") or [])

    idx = client_accuracy_index()
    print(f"client export index: {len(idx)} pet powers with accuracy")

    # NAMED EXCLUSIONS (checker states them, never silently narrows):
    #  - Incarnate_Pets.*: the Lore category is ABSENT from the client export
    #    (PLAYER_CATEGORIES never included it) — those pets keep the 1.0
    #    default, stated; a re-export extension unlocks them later.
    #  - Redirects.*: power-redirect shells, not pet-dir records — their
    #    accuracy lives on the redirect target in its own category.
    _EXCLUDED = ("Incarnate_Pets.", "Redirects.")
    expected = []          # consumed, damage-carrying, in-scope — the denominator
    excluded = 0
    patched = changed = 0
    misses = []
    for ps in sorted(consumed):
        for p in data.get(ps) or []:
            if not p.get("damage_effects"):
                continue
            if p["full_name"].startswith(_EXCLUDED):
                excluded += 1
                continue
            expected.append(p["full_name"])
            acc = idx.get(p["full_name"])
            if acc is None:
                misses.append(p["full_name"])
                continue
            patched += 1
            if p.get("accuracy") != acc:
                p["accuracy"] = acc
                changed += 1

    print(f"{patched} of {len(expected)} in-scope consumed pet damage powers "
          f"matched ({changed} records changed this run); "
          f"{excluded} excluded by name (Incarnate_Pets/Redirects — stated above)")
    if misses:
        print(f"  unmatched ({len(misses)}):")
        for m in misses:
            print(f"    {m}")
    ok = len(expected) > 0 and patched >= 0.9 * len(expected)
    if not ok:
        print("HARD FAIL: coverage below 90% — not writing.")
        sys.exit(1)

    if not write:
        print("(report only — rerun with --write to apply)")
        return

    out = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    # verify: stripping the added keys reproduces the original exactly
    check = json.loads(out)
    for ps, lst in check.items():
        for p in lst:
            p.pop("accuracy", None)
    orig = json.loads(raw)
    for ps, lst in orig.items():
        for p in lst:
            p.pop("accuracy", None)   # tolerate re-runs on an already-patched file
    if check != orig:
        print("HARD FAIL: strip-verify mismatch — not writing.")
        sys.exit(1)
    with open(POWERS, "wb") as f:
        f.write(out)
    print(f"written: {POWERS}")


if __name__ == "__main__":
    main(write="--write" in sys.argv)
