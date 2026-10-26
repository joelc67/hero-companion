"""IO set names and set-bonus labels, from the live client (review of 2026-10-26).

STAGED FOR THE NEXT UPDATE (Joel 2026-10-26: "include in a future update"). Run
--apply at the START of that update's model change, then evaluate_first: the
tier labels feed the engine's rule-of-five signature (engine.py: sig =
"|".join(bonus names)), so fixing a label can move a score.

GAME-FIRST, field by field, keyed by internal ids (never changed):
  A. set display names (5): the game's boostsets.json display_name per set uid.
     Ours carried Mids spellings: Numina's Convalesence, Cacophany, Ascendency of
     the Dominator (+ Superior), "Coercive Persuasion " (trailing space). Fields:
     enhancement_sets.json name, set_bonuses.json name, proc_catalog.json set,
     champions.json slot set_name. Piece names are NOT touched: the game's own
     piece records keep "Ascendency of the Dominator: ..." (the client is
     inconsistent; set_details.json's 1,231 titles already match it).
  B. set-bonus tier labels (19): each tier's names = the display names of the
     Set_Bonus records the game's tier grants (auto_powers), PvE/PvP paired by
     the record's PVP_Set_Bonus group. Values were already right (reality_check_
     setbonuses 0 drift); only labels were stale: 11 Increased Range sizes
     (+7.5% is "Huge", ours said "Large"; +5% is "Moderate", ours "Tiny") and
     Experienced Marksman's "(PVP)" suffix on the wrong 8 tiers.
  C. powers.json Set_Bonus(.PVP_Set_Bonus).Increased_Range_2/_3 display names
     (ours Large/Ultimate, the game's records are Small/Moderate).

Coverage (hard-fail): every game set pairs to ours by uid, every changed tier
pairs exactly once, and the change counts equal EXPECT. Idempotent.

Run:  python tools/patch_set_names_from_client.py            # report only
      python tools/patch_set_names_from_client.py --apply    # write
"""
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXP = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
D = lambda *p: os.path.join(ROOT, *p)  # noqa: E731
EXPECT = {"set_names": 5, "tier_labels": 19, "power_labels": 4}


def game_record(fn):
    g, s, p = fn.lower().split(".")
    f = os.path.join(EXP, g, s, p + ".json")
    return json.load(open(f, encoding="utf-8")) if os.path.exists(f) else None


def main():
    apply = "--apply" in sys.argv
    game_sets = {s["name"]: s for s in json.load(open(os.path.join(EXP, "boostsets.json"), encoding="utf-8"))}
    sb_raw = open(D("data", "set_bonuses.json"), "rb").read()
    sb = json.loads(sb_raw)

    # our uid -> the game set it is (an Attuned_ copy of ours shares its base set's record)
    def game_uid(uid):
        if uid in game_sets:
            return uid
        base = uid[len("Attuned_"):] if uid.startswith("Attuned_") else None
        if base in game_sets:
            return base
        sys.exit(f"FAIL: our set {uid} has no game set")

    # A. set display names by uid
    rename = {}                                   # old display -> new display
    for uid, ours in sb.items():
        g = game_sets[game_uid(uid)]
        if ours.get("name") != g["display_name"]:
            rename[ours.get("name")] = g["display_name"]
    missing = set(game_sets) - {game_uid(u) for u in sb}
    print(f"sets paired by uid: {len(sb)} of {len(game_sets)} game sets"
          + (f" (game-only: {sorted(missing)})" if missing else ""))

    # B. tier labels
    tier_changes = []
    for uid, ours in sb.items():
        for b in game_sets[game_uid(uid)].get("bonuses") or []:
            aps = [a for a in (b.get("auto_powers") or []) if not a.startswith("Set_Bonus.Global_Bonus.")]
            if not aps:
                continue
            pv = any(".PVP_Set_Bonus." in a for a in aps)
            want = [(game_record(a) or {}).get("display_name") for a in aps]
            if None in want:
                sys.exit(f"FAIL: {uid} tier {b['min_boosts']}: unresolved game record {aps}")
            cand = [t for t in ours["bonuses"] if t.get("pieces_required") == b["min_boosts"]
                    and t.get("pv_mode", 0) in ((1, 2) if pv else (0,))]
            if len(cand) != 1:
                sys.exit(f"FAIL: {uid} tier {b['min_boosts']} pv={pv}: {len(cand)} of ours pair")
            if sorted(cand[0].get("bonuses") or []) != sorted(want):
                tier_changes.append((uid, b["min_boosts"], pv, list(cand[0]["bonuses"]), want))
                cand[0]["bonuses"] = want
    # A applied to set_bonuses names
    for ours in sb.values():
        if ours.get("name") in rename:
            ours["name"] = rename[ours["name"]]

    # A in the other files: exact display-string fields only
    def rewrite(path, field):
        raw = open(path, "rb").read()
        data = json.loads(raw)
        n = [0]

        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k == field and isinstance(v, str) and v in rename:
                        o[k] = rename[v]
                        n[0] += 1
                    else:
                        walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(data)
        return raw, data, n[0]

    others = [(D("data", "enhancement_sets.json"), "name"), (D("data", "proc_catalog.json"), "set"),
              (D("benchmarks", "champions.json"), "set_name")]
    rewritten = [(p, f, *rewrite(p, f)) for p, f in others]

    # C. the Set_Bonus power records' labels
    p_raw = open(D("data", "powers.json"), "rb").read()
    powers = json.loads(p_raw)
    power_changes = []
    for lst in powers.values():
        for rec in lst:
            fn = rec["full_name"]
            if fn.startswith(("Set_Bonus.Set_Bonus.Increased_Range_", "Set_Bonus.PVP_Set_Bonus.Increased_Range_")):
                g = game_record(fn)
                if g and rec.get("display_name") != g["display_name"]:
                    power_changes.append((fn, rec["display_name"], g["display_name"]))
                    rec["display_name"] = g["display_name"]

    print(f"\nA. set names: {len(rename)}")
    for o, n in rename.items():
        print(f"   {o!r} -> {n!r}")
    for p, f, _raw, _d, n in rewritten:
        print(f"   {os.path.relpath(p, ROOT)} '{f}' fields: {n}")
    print(f"B. tier labels: {len(tier_changes)}")
    for uid, n, pv, o, w in tier_changes:
        print(f"   {uid} {n}pc{' PvP' if pv else ''}: {o} -> {w}")
    print(f"C. Set_Bonus record labels: {len(power_changes)}")
    for fn, o, n in power_changes:
        print(f"   {fn}: {o!r} -> {n!r}")

    got = {"set_names": len(rename), "tier_labels": len(tier_changes), "power_labels": len(power_changes)}
    if got == {k: 0 for k in got}:
        print("\nalready applied: nothing to change")
        return
    if got != EXPECT:
        sys.exit(f"\nFAIL: counts {got} differ from the reviewed {EXPECT}")
    if not apply:
        print("\nreport only (staged for the next update); --apply writes")
        return

    # Write each file in ITS OWN serialization: the format that reproduces the
    # original bytes exactly from the original parse. None found = refuse.
    FORMATS = [dict(indent=i, ensure_ascii=a) for i in (None, 1, 2) for a in (True, False)]

    def dump(obj, fmt, crlf):
        out = json.dumps(obj, **fmt).encode("utf-8")
        return out.replace(b"\n", b"\r\n") if crlf else out

    def fmt_of(raw):
        orig = json.loads(raw)
        for crlf in (False, True):
            for fmt in FORMATS:
                if dump(orig, fmt, crlf) in (raw, raw.rstrip(b"\r\n")):
                    return fmt, crlf
        return None

    jobs = [(D("data", "set_bonuses.json"), sb, sb_raw), (D("data", "powers.json"), powers, p_raw)]
    jobs += [(p, data, raw) for p, _f, raw, data, _n in rewritten]
    plans = []
    for path, data, raw in jobs:
        f = fmt_of(raw)
        if not f:
            sys.exit(f"FAIL: can't reproduce {os.path.relpath(path, ROOT)}'s own format; nothing written")
        plans.append((path, data, raw, f))
    for path, data, raw, (fmt, crlf) in plans:
        out = dump(data, fmt, crlf)
        if raw.endswith(b"\n") and not out.endswith(b"\n"):
            out += b"\r\n" if crlf else b"\n"
        open(path, "wb").write(out)
    print("\nwritten (each file in its own format)")


if __name__ == "__main__":
    main()
