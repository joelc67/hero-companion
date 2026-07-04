"""Crunch the Guyver/Sovereign master-build corpus for tidbits of knowledge.

Reads benchmarks/masters/guyver/**/*.mbd (private corpus, never committed),
parses + computes totals through the app's own pipeline, and aggregates the
master builder's revealed preferences: coverage, softcap habits, set economy,
pool meta, Hasten adoption, incarnate meta, iteration depth.

Run:  python tools/analyze_guyver.py
Out:  benchmarks/guyver_analysis.json  + printed summary
"""
import collections
import glob
import json
import os
import re
import statistics
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))

import server as srv                      # noqa: E402  (loads the game data)
import engine                             # noqa: E402
import mids_import                        # noqa: E402

CORPUS = os.path.join(ROOT, "benchmarks", "masters", "guyver")
OUT = os.path.join(ROOT, "benchmarks", "guyver_analysis.json")

_FNAME_RE = re.compile(r"^(?P<name>.+?) - (?P<at>[A-Za-z ]+) \((?P<sets>[^)]+)\)\.mbd$", re.I)
_VARIANT_RE = re.compile(r"\s+v(?:\d+|[A-Z][\w ]*)$", re.I)


def short(ps):
    if isinstance(ps, dict):
        ps = ps.get("full_name") or ps.get("name") or ps.get("display_name") or ""
    return (ps or "").split(".")[-1].replace("_", " ")


def main():
    files = sorted(glob.glob(os.path.join(CORPUS, "**", "*.mbd"), recursive=True))
    print(f"{len(files)} .mbd files")
    lookups = srv._import_lookups()

    records, failures = [], []
    for i, f in enumerate(files):
        if i % 100 == 0:
            print(f"  {i}/{len(files)} …", flush=True)
        try:
            data = json.loads(open(f, encoding="utf-8", errors="ignore").read())
            parsed = mids_import.parse_build(data, lookups)
            if not parsed.get("ok"):
                failures.append((os.path.basename(f), parsed.get("error", "?")[:80]))
                continue
            b = parsed["build"]
            at = b.get("archetype")
            at_rec = srv.ARCH_BY_NAME.get(at)
            if not at_rec:
                failures.append((os.path.basename(f), f"unknown AT {at}"))
                continue
            res_cap = round(at_rec["res_cap"] * 100, 1)
            totals = engine.calculate_build(b, srv.SET_BONUSES, res_cap=res_cap,
                                            ctx=srv._stat_ctx(at))
            lk = srv._level_key_stats(totals)
            powers = b.get("powers", [])
            pnames = {(p.get("full_name") or "").split(".")[-1] for p in powers}
            sets_used = collections.Counter()
            lotg_rech = 0
            ho_pieces = 0
            n_slots = 0
            for p in powers:
                per_power_sets = set()
                for s in (p.get("slots") or []):
                    if not isinstance(s, dict):
                        continue
                    n_slots += 1
                    sn = s.get("set_name")
                    pn = s.get("piece_name") or ""
                    if sn:
                        per_power_sets.add(sn)
                    elif pn and ("Exposure" in pn or "Enzyme" in pn or "Cytoskeleton" in pn
                                 or "Membrane" in pn or "Ribosome" in pn or "Golgi" in pn
                                 or "Endoplasm" in pn or "Centriole" in pn or "Peroxisome" in pn
                                 or "Lysosome" in pn or "Nucleolus" in pn):
                        ho_pieces += 1
                    if "Luck of the Gambler" in (sn or "") and "Recharge" in pn:
                        lotg_rech += 1
                for sn in per_power_sets:
                    sets_used[sn] += 1
            base = os.path.basename(f)[:-4]
            nm = base.split(" - ")[0]
            family = _VARIANT_RE.sub("", nm)
            records.append({
                "file": os.path.basename(f), "name": nm, "family": family,
                "at": at.replace("Class_", ""),
                "primary": short(b.get("primary")), "secondary": short(b.get("secondary")),
                "pools": sorted(short(p) for p in (b.get("pools") or [])),
                "epic": short(b.get("epic")), "n_powers": len(powers), "n_slots": n_slots,
                "hasten": "Hasten" in pnames, "lotg_rech": lotg_rech, "ho_pieces": ho_pieces,
                "sets": dict(sets_used),
                "incarnates": {k: short(v) for k, v in (b.get("incarnates") or {}).items() if v},
                **lk,
            })
        except Exception as e:  # noqa: BLE001
            failures.append((os.path.basename(f), str(e)[:80]))

    print(f"parsed {len(records)}, failed {len(failures)}")

    # ── aggregate ────────────────────────────────────────────────────────────
    def med(vals):
        vals = [v for v in vals if isinstance(v, (int, float))]
        return round(statistics.median(vals), 1) if vals else None

    by_at = collections.defaultdict(list)
    for r in records:
        by_at[r["at"]].append(r)

    agg = {
        "n_builds": len(records), "n_failures": len(failures),
        "ats": {at: len(rs) for at, rs in sorted(by_at.items(), key=lambda kv: -len(kv[1]))},
        "top_combos": collections.Counter(
            f'{r["at"]}: {r["primary"]} / {r["secondary"]}' for r in records).most_common(25),
        "unique_combos": len({(r["at"], r["primary"], r["secondary"]) for r in records}),
        "hasten_rate": round(100 * sum(r["hasten"] for r in records) / max(1, len(records)), 1),
        "hasten_by_at": {at: round(100 * sum(r["hasten"] for r in rs) / len(rs), 1)
                         for at, rs in by_at.items()},
        "median_stats_by_at": {at: {k: med([r[k] for r in rs])
                                    for k in ("melee_def", "ranged_def", "aoe_def", "sl_res",
                                              "recharge", "max_hp", "recovery")}
                               for at, rs in by_at.items()},
        "softcap_rates": {at: {pos: round(100 * sum(1 for r in rs if (r[pos] or 0) >= 45) / len(rs), 1)
                               for pos in ("melee_def", "ranged_def", "aoe_def")}
                          for at, rs in by_at.items()},
        "set_popularity": collections.Counter(
            sn for r in records for sn in r["sets"]).most_common(40),
        "lotg_rech_avg": round(sum(r["lotg_rech"] for r in records) / max(1, len(records)), 2),
        "ho_builds_pct": round(100 * sum(1 for r in records if r["ho_pieces"]) / max(1, len(records)), 1),
        "pool_combos": collections.Counter(
            " + ".join(r["pools"]) for r in records if r["pools"]).most_common(15),
        "epic_by_at": {at: collections.Counter(r["epic"] for r in rs if r["epic"]).most_common(3)
                       for at, rs in by_at.items()},
        "incarnate_meta": {slot: collections.Counter(
            r["incarnates"].get(slot) for r in records if r["incarnates"].get(slot)).most_common(5)
            for slot in ("Alpha", "Judgement", "Interface", "Destiny", "Hybrid", "Lore")},
        "biggest_families": collections.Counter(
            r["family"] for r in records).most_common(20),
        "failures_sample": failures[:20],
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"records": records, "aggregate": agg}, f, indent=1)
    print(f"\nwritten: {OUT}")

    a = agg
    print("\n════ TIDBITS ════")
    print(f"builds parsed: {a['n_builds']}  (failures {a['n_failures']})")
    print(f"unique AT+powerset combos: {a['unique_combos']}")
    print(f"HASTEN adoption: {a['hasten_rate']}% of all builds")
    print(f"avg LotG +rech per build: {a['lotg_rech_avg']}")
    print(f"builds using Hamidon Origins: {a['ho_builds_pct']}%")
    print("top ATs:", dict(list(a["ats"].items())[:8]))
    print("top pool combos:", a["pool_combos"][:5])
    print("top sets:", [s for s, _ in a["set_popularity"][:12]])


if __name__ == "__main__":
    main()
