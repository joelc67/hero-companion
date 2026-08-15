"""Champion validation (source-side): every champions.json entry is served by autopick
(passes the L1 gate). Run after any champion refresh.
"""
import os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"C:\Users\joelc\code\coh-builder"
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv, learn
c = srv.app.test_client()
champs = json.load(open(os.path.join(ROOT,"benchmarks","champions.json"), encoding="utf-8"))
ok = rej = 0
for key, entry in champs.items():
    parts = key.split("|")
    at, prim, sec, content = parts[:4]
    form = parts[4] if len(parts) > 4 else None
    # does autopick now SERVE the champion (not reject it at the L1 gate)?
    # Form champions serve through the same path with the wizard's Form answer.
    ap = c.post("/build/autopick", json={"archetype":at,"primary":prim,"secondary":sec,
                                         "content":content,"form":form}).get_json()
    got = {p["full_name"] for p in ap["powers"] if not p["full_name"].startswith("Inherent")}
    champ = {p for p in entry["picks"] if not p.split(".")[0].startswith("Inherent")}
    served = len(got & champ) / max(1, len(champ))
    status = "SERVED" if served > 0.9 else f"partial {served:.0%}"
    if served > 0.9: ok += 1
    else: rej += 1
    # certified-slotting layer (game-truth ruling 2026-08-14): when banked, the
    # REAL /build/solve on the autopicked kit must hand back exactly that build
    slot_col = ""
    if entry.get("slotting") and served > 0.9:
        sv = c.post("/build/solve", json={"archetype": at, "content": content,
                                          "powers": ap["powers"]}).get_json()
        def _sig(pw):
            return {p["full_name"]: sorted((s.get("set_uid") or "", s.get("piece_uid") or "")
                                           for s in (p.get("slots") or []) if s)
                    for p in pw if p.get("slots")}
        if (sv or {}).get("certified_slotting") and _sig(sv["powers"]) == _sig(entry["slotting"]):
            slot_col = " +SLOTTING"
        else:
            slot_col = " !!SLOT-DRIFT"; rej += 1; ok -= 1
    tag = f" [{form}]" if form else ""
    print(f"  {status:12s}{slot_col} {prim.split('.')[-1]:18s}/{sec.split('.')[-1]:18s}{tag} score={entry['score']:.0f}")
print(f"\nchampions served by autopick: {ok}/{len(champs)}")
