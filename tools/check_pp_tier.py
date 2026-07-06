"""Ground-truth the Physical Perfection prereq (Maelwys: tool says 2, real = 1).

(a) Our data: for every AT with Energy Mastery, show the tier order + level ladder and
    what _tier_need / _epic_prereq_errors compute for Physical Perfection.
(b) Corpus: scan Guyver's .mbd for builds containing Physical Perfection and report the
    MINIMUM number of OTHER Energy Mastery powers they carry — the real prereq can't
    exceed that.

Run:  python tools/check_pp_tier.py
"""
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"C:\Users\joelc\code\coh-builder"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv

print("── our data: Energy Mastery tiers ──")
for at, groups in srv.POWERSETS["by_archetype"].items():
    for e in (groups.get("epic") or []):
        ps = e["full_name"]
        if "Energy_Mastery" not in ps:
            continue
        allp = srv.POWERS.get(ps) or []
        tiers = srv._pool_tiers(ps)
        seq = sorted(allp, key=lambda p: tiers.get(p["full_name"], 0))
        line = ", ".join(f"{p['full_name'].split('.')[-1]}(t{tiers.get(p['full_name'],0)}"
                         f"/L{p.get('level_available')})" for p in seq)
        pp = next((p for p in allp if p["full_name"].endswith("Physical_Perfection")), None)
        if pp:
            need = srv._tier_need(pp["full_name"])
            print(f"  {at} {ps.split('.')[-1]}: {line}")
            print(f"    -> Physical Perfection tier_need = {need} prereq(s)")

print("\n── corpus: real builds with Physical Perfection ──")
try:
    import mids_import
    lookups = srv._import_lookups()
    files = glob.glob(os.path.join(ROOT, "benchmarks", "masters", "guyver", "**", "*.mbd"),
                      recursive=True)
    print(f"  scanning {len(files)} builds…")
    min_others = 99
    hits = 0
    for f in files:
        try:
            parsed = mids_import.parse_build(json.loads(open(f, encoding="utf-8", errors="ignore").read()), lookups)
            if not parsed.get("ok"):
                continue
            powers = parsed["build"].get("powers", [])
        except Exception:
            continue
        em = [p for p in powers if "Energy_Mastery" in (p.get("powerset_full_name") or "")]
        has_pp = any((p.get("full_name") or "").endswith("Physical_Perfection") for p in em)
        if has_pp:
            hits += 1
            others = len(em) - 1
            min_others = min(min_others, others)
    if hits:
        print(f"  {hits} builds have Physical Perfection; MIN other Energy Mastery powers = {min_others}")
        print(f"  => real prereq is AT MOST {min_others}")
    else:
        print("  no corpus builds with Physical Perfection found (corpus may be unavailable)")
except Exception as e:  # noqa: BLE001
    print(f"  corpus scan unavailable: {e}")
