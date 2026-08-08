"""Patch three client-verified target-cap / radius drifts on the Soul Drain family.

WHY THIS IS AN ADJUDICATED LIST AND NOT A BLANKET SYNC
------------------------------------------------------
Sweeping every power we hold against the client export finds 205 max_targets and
265 radius disagreements across 5,660 covered records. MOST OF THOSE ARE NOT
DRIFT, and copying the client over them would damage the data:

  * PSEUDO-PET POWERS. Fiery Aura's Burn reads 5 targets / 8 radius for us and
    0 / 0 in the client, because the client's parent record carries nothing - the
    damage lives on the patch entity, and our data deliberately folds the pet in
    (the documented pseudo-pet fold). Blizzard, Meteor, Time Bomb and Rise of the
    Phoenix are the same shape. Ours is right and the client parent is 0 by
    design.
  * SINGLE-TARGET SEMANTICS. Tesla Cage is 0 for us and 1 in the client: we use 0
    to mean "not an area power", the client counts the one target it hits. A
    different convention, not a wrong number.

So the honest scope here is the records whose disagreement has been adjudicated
one at a time. Each entry below carries a SECOND signal - a sibling record of the
same power where our value and the client's already agree - because a lone
disagreement cannot tell you which side moved. Classifying the remaining sweep is
its own piece of work and is deliberately NOT attempted here.

EVIDENCE PER ENTRY
------------------
  Brute Dark Melee Soul Drain      ours 7, client 10.  Scrapper and Tanker Dark
                                   Melee Soul Drain read 10 on BOTH sides.
  Corr Soul Mastery Soul Drain     ours 7, client 10.  Dominator Soul Mastery
                                   Soul Drain reads 10 on BOTH sides.
  Dom Soul Mastery Soul Drain      radius ours 15, client 10.  Every other Soul
                                   Drain is radius 10 on both sides; only Spirit
                                   Drain is 15, and there we already agree.

Champion exposure: ZERO of 24 certified contexts hold any of these three
(counted over 624 picks, not assumed), so no score moves and no re-cert is owed.

⚠ powers.json is COMPACT single-line. Read binary, write binary, no indent.
Usage:  python tools/patch_drain_target_caps.py [--check]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POWERS = os.path.join(ROOT, "data", "powers.json")
CRAWL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")

# (full_name, field, our current value, the client value, sibling that corroborates)
PATCHES = [
    ("Brute_Melee.Dark_Melee.Soul_Drain", "max_targets", 7, 10,
     "Scrapper_Melee.Dark_Melee.Soul_Drain"),
    ("Epic.Corruptor_Soul_Mastery.Soul_Drain", "max_targets", 7, 10,
     "Epic.Dominator_Soul_Mastery.Soul_Drain"),
    ("Epic.Dominator_Soul_Mastery.Soul_Drain", "radius", 15.0, 10.0,
     "Brute_Melee.Dark_Melee.Soul_Drain"),
]
_CLIENT_FIELD = {"max_targets": "max_targets_hit", "radius": "radius"}


def _client_index():
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


def main():
    check_only = "--check" in sys.argv
    raw = open(POWERS, "rb").read()
    data = json.loads(raw.decode("utf-8"))
    client = _client_index()

    by_name = {}
    for ps, lst in data.items():
        for p in lst:
            by_name[p["full_name"]] = p

    failures, applied = [], 0
    for full_name, field, ours_exp, client_exp, sibling in PATCHES:
        rec = by_name.get(full_name)
        crec = client.get(full_name)
        if rec is None:
            failures.append(f"{full_name}: not in our data")
            continue
        if crec is None:
            failures.append(f"{full_name}: not in the client export")
            continue
        cval = crec.get(_CLIENT_FIELD[field])
        # The game must still say what this patch was adjudicated against.
        if cval != client_exp:
            failures.append(f"{full_name}.{field}: client now says {cval}, "
                            f"expected {client_exp} - re-adjudicate, do not patch")
            continue
        # STALE-ENTRY CHECK: an entry left behind after the drift is gone is a
        # failure too, exactly like the display-name collision allowlist.
        if rec.get(field) == client_exp:
            failures.append(f"{full_name}.{field}: already correct - remove this "
                            f"entry from PATCHES")
            continue
        if rec.get(field) != ours_exp:
            failures.append(f"{full_name}.{field}: our value is {rec.get(field)}, "
                            f"expected {ours_exp} - the file moved under this patch")
            continue
        # The corroborating sibling must genuinely agree with the client.
        sib, csib = by_name.get(sibling), client.get(sibling)
        if not sib or not csib or sib.get(field) != csib.get(_CLIENT_FIELD[field]):
            failures.append(f"{full_name}.{field}: corroborating sibling {sibling} "
                            f"does not agree with the client - evidence is gone")
            continue
        if not check_only:
            rec[field] = client_exp
        applied += 1
        print(f"  {'would patch' if check_only else 'patched'} "
              f"{full_name}.{field}: {ours_exp} -> {client_exp}   (sibling {sibling})")

    print(f"\n{applied} of {len(PATCHES)} expected records patched")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  " + f)
        sys.exit(1)
    if applied != len(PATCHES):
        print("coverage short of the denominator")
        sys.exit(1)
    if check_only:
        return

    # INVARIANCE PROOF: revert the patched fields in a copy and require the
    # re-serialised bytes to equal the original file exactly. That is what shows
    # nothing else in a 16 MB single-line file moved.
    out = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    probe = json.loads(out.decode("utf-8"))
    pby = {}
    for ps, lst in probe.items():
        for p in lst:
            pby[p["full_name"]] = p
    for full_name, field, ours_exp, _c, _s in PATCHES:
        pby[full_name][field] = ours_exp
    reverted = json.dumps(probe, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if reverted != raw:
        print("INVARIANCE FAILED: reverting the patched fields does not reproduce "
              "the original bytes - refusing to write")
        sys.exit(2)
    print("invariance: reverting the 3 fields reproduces the original file byte for byte")

    open(POWERS, "wb").write(out)
    print(f"wrote {POWERS} ({len(out):,} bytes, was {len(raw):,})")


if __name__ == "__main__":
    main()
