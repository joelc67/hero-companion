"""Crunch the LEGACY half of the Guyver corpus: .mxd forum exports (Mids' ~1.962,
cohplanner era). These predate the modern meta — they document the OLD style
(45% def + resist) Guyver described, so this analysis is the before-picture.

No engine totals (old-DB power names); this harvests CHOICES: AT coverage,
powerset combos, pools, epics, Hasten, LotG+rech density, HO usage, set families.

Run:  python tools/analyze_guyver_mxd.py
Out:  benchmarks/guyver_mxd_analysis.json + printed comparison vs the .mbd corpus
"""
import collections
import glob
import html
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "benchmarks", "masters", "guyver")
OUT = os.path.join(ROOT, "benchmarks", "guyver_mxd_analysis.json")
MBD = os.path.join(ROOT, "benchmarks", "guyver_analysis.json")

# Three export generations share the layout; only the line endings differ
# (HTML <br /> in ~2019 files, plain newlines in Mids Reborn 2.x/3.x). Normalize
# to newlines first, then parse line-wise.
_HDR_AT = re.compile(r"^.*Level \d+ \w+ (.+?)\s*$", re.M)
_PRIM = re.compile(r"^Primary Power Set:\s*(.+?)\s*$", re.M)
_SEC = re.compile(r"^Secondary Power Set:\s*(.+?)\s*$", re.M)
_POOL = re.compile(r"^Power Pool:\s*(.+?)\s*$", re.M)
_EPIC = re.compile(r"^Ancillary Pool:\s*(.+?)\s*$", re.M)
_PLINE = re.compile(r"^Level (\d+):\s*(.+?)(?:\t+|\s{2,})(.+)$", re.M)


def _normalize(raw):
    t = re.sub(r"<br\s*/?>", "\n", raw)
    t = html.unescape(t).replace("\xa0", " ")
    return t.splitlines()

ABBREV = {
    "LucoftheG": "Luck of the Gambler", "Ags": "Aegis", "Mk'Bit": "Mako's Bite",
    "GssSynFr-": "Gaussian's", "NmnCnv": "Numina's", "Prv": "Preventive Medicine",
    "Rct": "Reactive Defenses", "GldArm": "Gladiator's Armor", "StdPrt": "Steadfast Protection",
    "Pnc": "Panacea", "PrfShf": "Performance Shifter", "UnbGrd": "Unbreakable Guard",
    "ShlWal": "Shield Wall", "Obl": "Obliteration", "Arm": "Armageddon", "Hct": "Hecatomb",
    "Rgn": "Ragnarok", "Apc": "Apocalypse", "GrvAnc": "Gravitational Anchor",
    "SprAvl": "Superior Avalanche (winter)", "WntBit": "Winter's Bite (winter)",
    "FrzBls": "Frozen Blast (winter)", "BlsoftheZ": "Blessing of the Zephyr",
    "Mrc": "Miracle", "DctWnd": "Doctored Wounds", "RedFrt": "Red Fortune",
    "CrsImp": "Crushing Impact", "SprBlsCol": "Superior Blistering Cold (winter)",
    "AchHee": "Achilles' Heel", "TchofDth": "Touch of Death", "ThfofEss": "Theft of Essence",
}


def main():
    files = sorted(glob.glob(os.path.join(CORPUS, "**", "*.mxd"), recursive=True))
    print(f"{len(files)} .mxd files")
    recs, failures = [], 0
    for f in files:
        try:
            t = "\n".join(_normalize(open(f, encoding="utf-8", errors="ignore").read()))
            at_m = _HDR_AT.search(t)
            prim, sec = _PRIM.search(t), _SEC.search(t)
            if not (prim and sec):
                failures += 1
                continue
            plines = _PLINE.findall(t)
            powers, slots, lotg, ho, set_fams = [], 0, 0, 0, collections.Counter()
            for _lvl, pname, enh in plines:
                pname = pname.strip()
                powers.append(pname)
                for piece in enh.split(","):
                    piece = piece.strip()
                    if not piece or piece.startswith("Empty") or piece.startswith("--"):
                        continue
                    slots += 1
                    if piece.startswith("HO:"):
                        ho += 1
                        continue
                    fam = piece.split("-")[0].strip()
                    if fam:
                        set_fams[ABBREV.get(fam, fam)] += 1
                    if "LucoftheG" in piece and "Rchg+" in piece:
                        lotg += 1
            recs.append({
                "file": os.path.basename(f),
                "at": (at_m.group(1).strip() if at_m else "?"),
                "primary": prim.group(1).strip(), "secondary": sec.group(1).strip(),
                "pools": sorted(_POOL.findall(t)), "epic": (_EPIC.findall(t) or [""])[0],
                "n_powers": len(powers), "n_slots": slots,
                "hasten": any(p == "Hasten" for p in powers),
                "lotg_rech": lotg, "ho_pieces": ho, "set_fams": dict(set_fams),
            })
        except Exception:  # noqa: BLE001
            failures += 1

    print(f"parsed {len(recs)}, failed {failures}")
    n = max(1, len(recs))
    agg = {
        "n_builds": len(recs), "n_failures": failures,
        "ats": dict(collections.Counter(r["at"] for r in recs).most_common()),
        "top_combos": collections.Counter(
            f'{r["at"]}: {r["primary"]} / {r["secondary"]}' for r in recs).most_common(20),
        "unique_combos": len({(r["at"], r["primary"], r["secondary"]) for r in recs}),
        "hasten_rate": round(100 * sum(r["hasten"] for r in recs) / n, 1),
        "lotg_rech_avg": round(sum(r["lotg_rech"] for r in recs) / n, 2),
        "ho_builds_pct": round(100 * sum(1 for r in recs if r["ho_pieces"]) / n, 1),
        "pool_combos": collections.Counter(
            " + ".join(r["pools"]) for r in recs if r["pools"]).most_common(10),
        "epic_meta": collections.Counter(r["epic"] for r in recs if r["epic"]).most_common(12),
        "set_family_popularity": collections.Counter(
            fam for r in recs for fam in r["set_fams"]).most_common(30),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"records": recs, "aggregate": agg}, f, indent=1)
    print(f"written: {OUT}")

    print("\n════ OLD META (.mxd) vs NEW META (.mbd) ════")
    new = json.load(open(MBD, encoding="utf-8"))["aggregate"] if os.path.exists(MBD) else None
    rows = [("builds", agg["n_builds"], new and new["n_builds"]),
            ("unique combos", agg["unique_combos"], new and new["unique_combos"]),
            ("Hasten %", agg["hasten_rate"], new and new["hasten_rate"]),
            ("LotG+rech avg", agg["lotg_rech_avg"], new and new["lotg_rech_avg"]),
            ("HO builds %", agg["ho_builds_pct"], new and new["ho_builds_pct"])]
    for k, old_v, new_v in rows:
        print(f"  {k:16} old {old_v:>7}   new {new_v}")
    print("  old top pools:", agg["pool_combos"][:3])
    print("  old epic meta:", agg["epic_meta"][:5])
    print("  old top sets:", [s for s, _ in agg["set_family_popularity"][:12]])


if __name__ == "__main__":
    main()
