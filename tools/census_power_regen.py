"""CENSUS: power-granted +Regeneration in the CLIENT vs our data.

Found 2026-08-17 measuring Maelwys's example farm builds: Rooted and
Temperature Protection carry client Regeneration templates our records lack
(Rooted's at top level; TP's inside effect-group child_effects — the descend
trap). This census walks EVERY client record for the powersets we actually
serve, collects Self-targeted Regeneration templates at ANY depth, and
reports which of our records are missing them.

Read-only. The additive patcher comes after Joel sees the table.
Run:  python tools/census_power_regen.py
"""
import importlib.util as ilu
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRAWL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
spec = ilu.spec_from_file_location("cohserver", os.path.join(ROOT, "server", "server.py"))
srv = ilu.module_from_spec(spec)
spec.loader.exec_module(srv)


def regen_templates(rec):
    """Every Self-targeted Regeneration template in a client record, ANY depth
    (groups' child_effects nest arbitrarily). Returns (template, group) pairs —
    the group carries the gating context (requires/tags)."""
    out = []

    def walk_group(g):
        for t in (g.get("templates") or []):
            if ("Regeneration" in (t.get("attribs") or [])
                    and t.get("target") == "Self"
                    and t.get("aspect") == "Current"):
                out.append((t, g))
        for c in (g.get("child_effects") or []):
            walk_group(c)

    for g in (rec.get("effects") or []):
        walk_group(g)
    return out


def our_regen_presence(fn):
    """Does OUR record carry any self +Regeneration effect row?"""
    rec = srv.POWER_BY_FULL.get(fn)
    if not rec:
        return None
    for field in ("buff_effects", "self_effects", "heal_effects"):
        for e in (rec.get(field) or []):
            blob = " ".join(str(e.get(k) or "") for k in
                            ("effect", "attribute", "display", "effect_type",
                             "enhance_aspect"))
            if "egen" in blob:
                return True
    return False


served_sets = set()
for at, groups in srv.POWERSETS["by_archetype"].items():
    for grp in ("primary", "secondary", "epic"):
        for e in (groups.get(grp) or []):
            served_sets.add((e["full_name"] if isinstance(e, dict) else e))
for ps in srv.POWERS:
    if ps.startswith("Pool."):
        served_sets.add(ps)

rows, ours_have, client_total = [], 0, 0
for dirpath, _d, files in os.walk(CRAWL):
    for f in files:
        if not f.endswith(".json") or f == "index.json":
            continue
        try:
            rec = json.load(open(os.path.join(dirpath, f), encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        full = rec.get("full_name") or ""
        ps = full.rsplit(".", 1)[0]
        if ps not in served_sets:
            continue
        tmpls = regen_templates(rec)
        if not tmpls:
            continue
        client_total += 1
        have = our_regen_presence(full)
        if have:
            ours_have += 1
            continue
        gated = any((g.get("requires_expression") or g.get("tags")) for _t, g in tmpls)
        scale = sum(t.get("scale") or 0 for t, _g in tmpls)
        rows.append((full, rec.get("display_name"), len(tmpls),
                     round(scale, 2), "gated" if gated else "clean",
                     "MISSING-FROM-OURS" if have is False else "RECORD-ABSENT"))

print(f"client records with Self +Regeneration templates in SERVED sets: {client_total}")
print(f"  our data already carries regen on: {ours_have}")
print(f"  GAPS: {len(rows)}\n")
for full, disp, n, scale, gate, kind in sorted(rows):
    print(f"  {full:<62} {disp or '':<24} tmpl={n} scale={scale:<5} {gate:<6} {kind}")
