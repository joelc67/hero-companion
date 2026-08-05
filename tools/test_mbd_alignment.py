"""PIN: the Mids Reborn round trip — exports open in Mids, and come back whole.

Field report (2026-07-30, Web3Forms, SS/Shield Brute): our exports crashed
Mids with "Unhandled exception: Requested value 'hero' was not found". Mids
parses Alignment as a case-sensitive .NET enum ("Hero"); the app's toggle
stores lowercase "hero" and the exporter passed it through verbatim. Imports
worked (Mids-authored files carry proper casing) — only OUR exports crashed.

Checks, through the REAL /build/export route:
  1 lowercase app alignment exports as the Mids enum casing ("Hero")
  2 villain side too ("Villain")
  3 every OTHER enum-shaped field in the export keeps Mids casing
    (Grade "None", RelativeLevel "Even", Origin capitalized)
  4 round-trip: our export re-imports through the real /build/import route
    (the reporter's imports worked; this keeps it that way)

Round-trip FIDELITY (added 2026-08-05, Joel: "test mids reborn export and import
work flawlessly"). Check 4 only ever asserted "it parsed" — these assert that
what comes back is what went out:
  5 every power survives
  6 every slot keeps its exact piece (uid by uid, in order)
  7 the engine totals do not move — the number the user actually sees
  8 STABILITY: export -> import -> export converges (hop2 == hop3). Hop 1 may
    legitimately normalise (an HO's "+3" becomes "a level-53 HO"); what must
    never happen is a build that drifts every time it makes the trip.
  9 special origins keep their DISPLAY name (found by this battery: HOs live in
    common_ios.json, missed PIECE_BY_UID, and came back labelled
    "Hamidon_Damage_Accuracy" instead of "Nucleolus Exposure")

Run:  py tools\\test_mbd_alignment.py
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
import server as srv  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def main():
    c = srv.app.test_client()
    ap = c.post("/build/autopick", json={
        "archetype": "Class_Brute", "primary": "Brute_Melee.Super_Strength",
        "secondary": "Brute_Defense.Shield_Defense", "content": "team"}).get_json()
    pre = [{"full_name": p["full_name"], "slots": p.get("slots"),
            "earned_slot_count": p.get("earned_slot_count")} for p in ap["powers"]]
    # the reporter exported a SOLVED build — slots carry real set pieces
    sol = c.post("/build/solve", json={"archetype": "Class_Brute", "goal": "",
        "tier": "premium", "content": "team", "role": "damage",
        "preserve": False, "keep_layout": False, "powers": pre}).get_json()
    powers = sol["powers"]

    for align_in, want in (("hero", "Hero"), ("villain", "Villain")):
        r = c.post("/build/export", json={
            "archetype": "Class_Brute", "alignment": align_in,
            "powers": powers}).get_json()
        mbd = json.loads(r["mbd"]) if isinstance(r.get("mbd"), str) else r.get("mbd") or r
        check(f"alignment '{align_in}' exports as '{want}' (Mids enum casing)",
              mbd.get("Alignment") == want,
              f"exported Alignment={mbd.get('Alignment')!r}")

    # enum-shaped neighbors stay Mids-cased
    origin_ok = (mbd.get("Origin") or "")[:1].isupper()
    slot_enums = [(s["Enhancement"].get("Grade"), s["Enhancement"].get("RelativeLevel"))
                  for pe in mbd.get("PowerEntries", [])
                  for s in pe.get("SlotEntries", []) if s.get("Enhancement")]
    enums_ok = all(g == "None" and rl == "Even" for g, rl in slot_enums)
    check("Origin/Grade/RelativeLevel keep Mids enum casing",
          origin_ok and bool(slot_enums) and enums_ok,
          f"Origin={mbd.get('Origin')!r}, {len(slot_enums)} slot enums checked")

    # round-trip: our export must re-import through the real route
    imp = c.post("/build/import", json={"mbd": json.dumps(mbd)}).get_json()
    n_imp = len(((imp or {}).get("build") or {}).get("powers") or [])
    check("our export re-imports through /build/import",
          bool(imp and imp.get("ok")) and n_imp > 0,
          f"ok={bool(imp and imp.get('ok'))}, imported {n_imp} powers")

    # ── FIDELITY: what comes back is what went out ──────────────────────────
    # Boost every filled slot across a 0..5 spread first — an off-by-one in the
    # 0-based IoLevel conversion cannot hide behind a build that is all +0.
    for i, p in enumerate(powers):
        for j, s in enumerate(p.get("slots") or []):
            if s:
                s["boost"] = (i + j) % 6

    def _export(pw):
        r = c.post("/build/export", json={"archetype": "Class_Brute",
                                          "alignment": "hero", "powers": pw}).get_json()
        return r["mbd"] if isinstance(r.get("mbd"), str) else json.dumps(r.get("mbd") or r)

    def _import(m):
        r = c.post("/build/import", json={"mbd": m}).get_json()
        return (r.get("build") or {}).get("powers") or []

    def _uids(pw):
        return {p["full_name"]: [(s or {}).get("piece_uid") for s in (p.get("slots") or [])]
                for p in pw}

    m1 = _export(powers)
    b1 = _import(m1)
    m2 = _export(b1)
    b2 = _import(m2)
    m3 = _export(b2)

    a, b = _uids(powers), _uids(b1)
    lost = [n for n in a if n not in b]
    check("every power survives the round trip", not lost,
          f"{len(a)} out, {len(b)} back (extra = the game's inherents, which Mids carries)")
    moved = {n: (a[n], b[n]) for n in a if n in b and a[n] != b[n]}
    check("every slot keeps its exact piece, in order", not moved,
          f"{sum(len(v) for v in a.values())} slots compared"
          + (f" — {len(moved)} POWERS DIFFER: {list(moved)[:3]}" if moved else ""))

    def _totals(pw):
        t = c.post("/build/calculate", json={"archetype": "Class_Brute",
                                             "powers": pw}).get_json() or {}

        def num(d, k):
            v = (d or {}).get(k)
            return round(float((v.get("total", v.get("value", 0)) if isinstance(v, dict)
                                else v) or 0), 4)
        return (num(t.get("defense"), "Melee"), num(t.get("resistance"), "Smashing"),
                t.get("applied_bonus_count"))

    t0, t1, t2 = _totals(powers), _totals(b1), _totals(b2)
    check("the engine totals do not move", t0 == t1 == t2,
          f"melee def / S-L res / set bonuses — out {t0}, back {t1}, twice {t2}")
    check("export -> import -> export converges (no drift on every trip)", m2 == m3,
          f"hop2 {len(m2)}b vs hop3 {len(m3)}b"
          + ("" if m2 == m3 else " — the build changes every time it round-trips"))

    ho = [s for p in b1 for s in (p.get("slots") or [])
          if s and str(s.get("piece_uid") or "").startswith(("Hamidon_", "Titan_",
                                                             "Hydra_", "DSync_", "Dsync_"))]
    named = [s for s in ho if s.get("piece_name") and s["piece_name"] != s["piece_uid"]
             and s.get("set_name")]
    check("special origins come back with their display name, not their uid",
          bool(ho) and len(named) == len(ho),
          f"{len(ho)} HO/special slots, {len(named)} correctly named"
          + (f" — e.g. {ho[0]['piece_name']!r} of {ho[0].get('set_name')!r}" if ho else
             " — NO HO IN FIXTURE, this check proved nothing"))

    print(f"\n{9 - len(FAILS)} of 9 checks pass")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
