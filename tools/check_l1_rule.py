"""Reality-check the level-1 pick rule against the master corpus.

Field report (Joel, making a Poison/Sonic Defender in game): at creation the
power CHOICE offered was only Shriek vs Scream (secondary first two) — the tool
told him to "take Alkaloid at 1" as if it were a choice. Hypotheses:
  A) primary T1 is FORCED (every build contains it) + secondary = choice of first two
  B) both primary and secondary offer their first two as choices
Checks 2,255 master .mbd builds: presence of primary/secondary T1, and what the
builds actually place at their two level-1 picks. Bonus: verify the corpus obeys
the late-slot rule (a 49-pick holds at most 4 slots).

Run:  python tools/check_l1_rule.py
"""
import collections
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"C:\Users\joelc\code\coh-builder"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv
import mids_import

CORPUS = os.path.join(ROOT, "benchmarks", "masters", "guyver")
files = sorted(glob.glob(os.path.join(CORPUS, "**", "*.mbd"), recursive=True))
print(f"{len(files)} .mbd files")
lookups = srv._import_lookups()

n = 0
p1_missing, s1_missing = [], []
l1_combo = collections.Counter()      # (which sets the two L1 picks come from)
l1_notfirst2 = []                     # an L1 pick that is NOT its set's first-two
late_over = []                        # 49-picks with more than 4 slots
for i, f in enumerate(files):
    if i % 400 == 0:
        print(f"  {i}/{len(files)} …", flush=True)
    try:
        parsed = mids_import.parse_build(
            json.loads(open(f, encoding="utf-8", errors="ignore").read()), lookups)
        if not parsed.get("ok"):
            continue
        b = parsed["build"]
    except Exception:
        continue
    powers = [p for p in b.get("powers", [])
              if not (p.get("full_name") or "").startswith(("Inherent", "Incarnate", "Temp"))]
    main_sets = [ps for ps in {p.get("powerset_full_name") for p in powers}
                 if ps and not ps.startswith(("Pool", "Epic"))]
    if len(main_sets) < 2:
        continue
    # primary vs secondary: use each set's data order in POWERSETS by_archetype
    at = b.get("archetype")
    groups = srv.POWERSETS["by_archetype"].get(at) or {}
    prims = {e["full_name"] for e in (groups.get("primary") or [])}
    prim = next((s for s in main_sets if s in prims), None)
    sec = next((s for s in main_sets if s != prim), None)
    if not (prim and sec and prim in srv.POWERS and sec in srv.POWERS):
        continue
    n += 1
    have = {p["full_name"] for p in powers}
    p_first2 = [x["full_name"] for x in srv.POWERS[prim][:2]]
    s_first2 = [x["full_name"] for x in srv.POWERS[sec][:2]]
    if p_first2 and p_first2[0] not in have:
        p1_missing.append(os.path.basename(f)[:60])
    if s_first2 and s_first2[0] not in have:
        s1_missing.append(os.path.basename(f)[:60])
    # what sits at the two level-1 picks (mbd carries real pick levels)
    l1 = [p for p in powers if int(p.get("pick_level") or 0) == 1]
    if len(l1) == 2:
        kinds = []
        for p in l1:
            ps = p.get("powerset_full_name")
            kind = "primary" if ps == prim else ("secondary" if ps == sec else "other")
            kinds.append(kind)
            first2 = p_first2 if ps == prim else (s_first2 if ps == sec else [])
            if kind != "other" and p["full_name"] not in first2:
                l1_notfirst2.append((os.path.basename(f)[:50], p["full_name"].split(".")[-1]))
        l1_combo[tuple(sorted(kinds))] += 1
    # late-slot rule in the wild
    for p in powers:
        if int(p.get("pick_level") or 0) == 49 and len(p.get("slots") or []) > 4:
            late_over.append((os.path.basename(f)[:50], p["full_name"].split(".")[-1],
                              len(p["slots"])))

print(f"\nanalyzed: {n} builds")
print(f"primary T1 missing:   {len(p1_missing):4d}  ({100 * len(p1_missing) / max(1, n):.1f}%)")
for r in p1_missing[:8]:
    print("    ", r)
print(f"secondary T1 missing: {len(s1_missing):4d}  ({100 * len(s1_missing) / max(1, n):.1f}%)")
for r in s1_missing[:8]:
    print("    ", r)
print(f"\nlevel-1 pick composition: {dict(l1_combo)}")
print(f"L1 pick outside its set's first two: {len(l1_notfirst2)}")
for r in l1_notfirst2[:8]:
    print("    ", r)
print(f"\n49-picks with >4 slots (should be ~0 if the rule is real): {len(late_over)}")
for r in late_over[:8]:
    print("    ", r)
