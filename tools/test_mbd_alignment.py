"""PIN: exported .mbd files must open in Mids Reborn — enum casing.

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

    print(f"\n{4 - len(FAILS)} of 4 checks pass")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
