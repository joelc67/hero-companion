"""Sync CONTROL rows that disagree with the game client. The game is right.

Found while adding Wind Control: our control encoding matches the client on 539
powers and disagrees on 29. The standing rule settles the direction - "when the
tool and the game disagree, the game is right" - so the client's values win.

WHAT WAS WRONG, and it is not noise:
    Epic holds across ten sets read a 12.0 duration scale where the game says
    10.0 (Block of Ice, Fossilize, Char, Dominate, Shocking Bolt, Melt Armor);
    the four Electric Shackles read 8.0 where the game says 10.0; Hymn of
    Dissonance claimed magnitude 1 where the game says 3 - a mag-1 hold does not
    hold anything a mag-3 one does; and Telekinesis was recorded as a HOLD when
    the game's own short help reads "Foe Immobilize, Repel".

⚠ ONLY ONE-TO-ONE CASES ARE SYNCED. Where our record has one PvE mez row and the
client states exactly one, the client's (mez, scale, magnitude) is written.
FOUR powers have multi-row encodings on one side or both - Synaptic Overload
carries eight rows to the client's two, Cryo Freeze Ray and EM Pulse carry an
extra magnitude-1 row the client does not have, Seismic Smash carries its row
twice - and those are left alone and REPORTED. Collapsing a multi-application
encoding is a different question from correcting a value, and guessing at it
would risk the control scores of powers people actually use.

✓ CHAMPION EXPOSURE COUNTED BEFORE THE CHANGE: zero of 24 certified contexts
hold any drifting power, so no score moves and no re-cert is owed.

⚠ powers.json is COMPACT single-line. Read binary, write binary, no indent.
Usage:  python tools/patch_control_drift.py [--check]
"""
import json
import os
import sys
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POWERS = os.path.join(ROOT, "data", "powers.json")
CRAWL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")

MARK = "control_synced"
MEZ = {"Held", "Immobilized", "Stunned", "Sleep", "Confused", "Terrorized"}
KIND = {"Held": "hard", "Stunned": "hard", "Immobilized": "hard",
        "Confused": "hard", "Terrorized": "hard", "Sleep": "soft"}


def client_index():
    out = {}
    for f in glob.glob(os.path.join(CRAWL, "**", "*.json"), recursive=True):
        if os.path.basename(f) == "index.json":
            continue
        try:
            c = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if c.get("full_name"):
            out[c["full_name"]] = c
    return out


def client_pve_mez(crec):
    rows = set()
    for g in (crec.get("effects") or []):
        if "critter" not in (g.get("requires_expression") or ""):
            continue
        for t in (g.get("templates") or []):
            for a in (t.get("attribs") or []):
                if a in MEZ:
                    rows.add((a, round(float(t.get("scale") or 0), 4),
                              round(float(t.get("magnitude") or 0), 4)))
    return rows


def main():
    check_only = "--check" in sys.argv
    raw = open(POWERS, "rb").read()
    data = json.loads(raw.decode("utf-8"))
    orig = json.loads(raw.decode("utf-8"))
    client = client_index()

    # IDEMPOTENT: restore anything a previous pass changed, then re-derive.
    restored = 0
    for _ps, lst in data.items():
        for p in lst:
            for e in (p.get("control_effects") or []):
                if MARK in e:
                    was = e.pop(MARK)
                    e["mez"], e["scale"], e["nmag"] = was["mez"], was["scale"], was["nmag"]
                    e["kind"] = was["kind"]
                    restored += 1
    if restored:
        print(f"(re-run: restored {restored} row(s) from a previous pass)")

    synced, multi, agreed = [], [], 0
    for _ps, lst in data.items():
        for p in lst:
            if p.get("added_from_client"):
                continue
            c = client.get(p["full_name"])
            if not c:
                continue
            ours = [e for e in (p.get("control_effects") or [])
                    if e.get("pv_mode") == 1 and e.get("mez") in MEZ]
            theirs = client_pve_mez(c)
            if not ours or not theirs:
                continue
            om = {(e["mez"], round(e["scale"], 4), round(e.get("nmag") or 0, 4))
                  for e in ours}
            if om & theirs:
                agreed += 1
                continue
            if len(ours) != 1 or len(theirs) != 1:
                multi.append((p["full_name"], sorted(om), sorted(theirs)))
                continue
            mez, sc, mag = next(iter(theirs))
            e = ours[0]
            if not check_only:
                e[MARK] = {"mez": e["mez"], "scale": e["scale"],
                           "nmag": e.get("nmag"), "kind": e.get("kind")}
                e["mez"], e["scale"], e["nmag"] = mez, sc, mag
                e["kind"] = KIND.get(mez, e.get("kind"))
            synced.append((p["full_name"], sorted(om)[0], (mez, sc, mag)))

    print(f"control powers whose PvE rows already AGREE with the client : {agreed}")
    print(f"{'would sync' if check_only else 'SYNCED'} (one-to-one, the game wins) : {len(synced)}")
    for fn, a, b in sorted(synced):
        print(f"    {fn:<54} {a} -> {b}")
    print(f"LEFT ALONE, multi-row encodings that need their own ruling : {len(multi)}")
    for fn, a, b in sorted(multi):
        print(f"    {fn:<54} ours {a} / client {b}")

    if not synced:
        print("\nnothing to sync")
        return
    if check_only:
        return

    out = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    probe = json.loads(out.decode("utf-8"))
    for _ps, lst in probe.items():
        for p in lst:
            for e in (p.get("control_effects") or []):
                if MARK in e:
                    was = e.pop(MARK)
                    e["mez"], e["scale"], e["nmag"] = was["mez"], was["scale"], was["nmag"]
                    e["kind"] = was["kind"]
    if (json.dumps(probe, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            != json.dumps(orig, separators=(",", ":"), ensure_ascii=False).encode("utf-8")):
        print("\nINVARIANCE FAILED: undoing the sync does not reproduce the "
              "baseline - refusing to write")
        sys.exit(2)
    print("invariance: undoing the sync reproduces the baseline exactly")
    with open(POWERS, "wb") as fh:
        fh.write(out)
    print(f"wrote {POWERS} ({len(out):,} bytes, was {len(raw):,})")


if __name__ == "__main__":
    main()
