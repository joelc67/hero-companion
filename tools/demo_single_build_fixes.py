"""SINGLE-BUILD demonstration tests for the 2026-07-08 field reports (Joel + Maelwys).

One build — Maelwys's exact case, a Bots/Marine Mastermind, "damage dealer + team play"
— generated through the SAME path the app uses (autopick -> solve with the app payload),
then each reported issue is checked individually with a visible PASS/FAIL:

  1. EMPTY-LOOKING SLOTS   every filled slot carries an icon (0.12.13 dropped every
                           common IO's icon — they rendered as empty slots next to
                           expensive globals like LotG)
  2. TRULY EMPTY SLOTS     no solved power mixes real pieces with empty (None) slots
  3. HO DUPLICATE WARNINGS Hamidon Origins stack legally — validate must NOT warn
                           "duplicate piece ... once per power" on HO x2/x3 cores
  4. ORPHANED FRAGMENTS    no power carries a 1-piece non-global set (the "dead
                           fragment" the -res/FF last-piece swap could create)
  5. PROC-BOMB INTEGRITY   Force Feedback seating must not overwrite a damage proc
                           in a proc-bombed power (it cost Whitecap its Obliteration)
  6. HO PRICING            Hamidon Origins have NO ref level (an imported Enzyme at
                           IoLevel 1 must not scale to zero) while common IOs DO

Run:  python tools/demo_single_build_fixes.py
"""
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
import server as srv  # noqa: E402
import engine  # noqa: E402

AT, PRIM, SEC = ("Class_Mastermind", "Mastermind_Summon.Robots",
                 "Mastermind_Buff.Marine_Affinity")
ROLE, CONTENT = "damage", "team"

# sets whose single piece is a working global (mule), never a fragment
_GLOBAL_HINTS = ("luck of the gambler", "steadfast", "gladiator's armor", "shield wall",
                 "kismet", "numina", "miracle", "regenerative tissue", "panacea",
                 "performance shifter", "power transfer", "reactive defenses",
                 "unbreakable guard", "preventive medicine", "overwhelming force")

results = []


def check(name, ok, detail):
    results.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}\n        {detail}")


print(f"Generating Maelwys's build: Bots/Marine MM, role={ROLE}, content={CONTENT} …")
c = srv.app.test_client()
ap = c.post("/build/autopick", json={"archetype": AT, "primary": PRIM, "secondary": SEC,
                                     "role": ROLE, "content": CONTENT,
                                     "exposure": "flex", "travel": "speed"}).get_json()
presolve = [{"full_name": p["full_name"], "slots": p.get("slots"),
             "earned_slot_count": p.get("earned_slot_count")} for p in ap["powers"]]
sol = c.post("/build/solve", json={"archetype": AT, "goal": "", "tier": "premium",
                                   "content": CONTENT, "role": ROLE, "exposure": "flex",
                                   "preserve": False, "keep_layout": False,
                                   "powers": presolve}).get_json()
powers = sol["powers"]

print("\nThe build:")
for p in powers:
    slots = p.get("slots") or []
    filled = [s for s in slots if s]
    hist = Counter((s.get("set_name") or "?") for s in filled)
    desc = ", ".join(f"{k}x{v}" if v > 1 else k for k, v in hist.items())
    pad = f"  (+{len(slots)-len(filled)} EMPTY)" if len(filled) < len(slots) else ""
    print(f"  {p.get('display_name') or p['full_name']:26s} [{len(slots)}] {desc}{pad}")

print("\nIndividual checks:")

# 1 — every filled slot has an icon (the 0.12.13 'empty slot' regression)
missing = [f"{p.get('display_name')}: {s.get('set_name')}:{s.get('piece_name')}"
           for p in powers for s in (p.get("slots") or [])
           if s and s.get("piece_uid") and not srv.PIECE_IMAGE.get(s["piece_uid"])]
check("every slotted piece has an icon (no empty-LOOKING slots)",
      not missing, missing[:3] or "all pieces carry icons, incl. every common IO")

# 2 — no filled-power carries truly empty slots
mixed = [p.get("display_name") for p in powers
         if (p.get("slots") or []) and any(s for s in p["slots"]) and
         any(s is None for s in p["slots"])]
check("no power mixes real pieces with EMPTY slots", not mixed,
      mixed[:5] or "every allocated slot is filled")

# 3 — HO x2/x3 cores draw ZERO duplicate-piece warnings
ho_powers = [p.get("display_name") for p in powers
             if sum(1 for s in (p.get("slots") or [])
                    if s and str(s.get("piece_uid", "")).startswith("Hamidon_")) >= 2]
val = engine.validate_build({"powers": powers})
dup_warns = [w for w in (val.get("warnings") or []) if "duplicate piece" in w]
check("HO x2/x3 cores trigger no 'duplicate piece' warnings",
      bool(ho_powers) and not dup_warns,
      f"HO-stacked powers: {ho_powers or 'NONE (expected some!)'} — "
      f"duplicate warnings: {dup_warns or 0}")

# 4 — no orphaned 1-piece fragments (non-global sets)
frags = []
for p in powers:
    hist = Counter()
    for s in (p.get("slots") or []):
        if s and not s.get("_proc") and s.get("set_name") \
           and srv.SET_BY_NAME.get(s["set_name"].lower()):
            hist[s["set_name"]] += 1
    for sname, n in hist.items():
        if n == 1 and not any(g in sname.lower() for g in _GLOBAL_HINTS):
            frags.append(f"{p.get('display_name')}: {sname} x1")
check("no orphaned 1-piece set fragments", not frags,
      frags[:5] or "every non-global set earns a bonus (>=2 pieces)")

# 5 — FF must not have eaten a damage proc in a proc-bombed power
bombs = {}
ff_host = None
for p in powers:
    slots = [s for s in (p.get("slots") or []) if s]
    n_proc = sum(1 for s in slots if s.get("_proc"))
    if any("force feedback" in (s.get("set_name") or "").lower() for s in slots):
        ff_host = p.get("display_name")
    if n_proc >= 4:
        bombs[p.get("display_name")] = n_proc
check("Force Feedback seats WITHOUT cannibalizing a proc bomb",
      ff_host is not None and (ff_host not in bombs or bombs[ff_host] >= 5),
      f"FF host: {ff_host} — full proc bombs intact: {dict(bombs)}")

# 6 — HO pricing: no ref level for HOs (grade-flat), ref level 50 for common IOs
ho_ref = [u for u in srv.PIECE_REF_LEVEL if str(u).startswith(("Hamidon_", "Titan_",
                                                               "Hydra_", "DSync_",
                                                               "Dsync_"))]
common_ok = all(srv.PIECE_REF_LEVEL.get(c["uid"]) == 50
                for c in srv.COMMON_IOS["common_ios"] if c.get("uid"))
check("HOs grade-flat (no ref level), common IOs ref level 50",
      not ho_ref and common_ok,
      f"HO uids wrongly ref-leveled: {ho_ref[:3] or 'none'}; "
      f"common IOs ref-leveled correctly: {common_ok}")

fails = [n for n, ok, _ in results if not ok]
print(f"\n══ {'ALL ' + str(len(results)) + ' CHECKS PASS' if not fails else 'FAILURES: ' + ', '.join(fails)} ══")
sys.exit(1 if fails else 0)
