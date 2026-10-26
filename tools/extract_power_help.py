"""
extract_power_help.py - Generate data/power_help.json: each power's AUTHENTIC
in-game description for the power info panel. GAME-FIRST for copy: every string
is the client's own text, never written by us.

Why (user bug report, 0.12.58): "When I click on the ? next to a power, I expect
to see an explanation of the power, not just what IO set can go into the power.
This is essential as an offline builder." The panel showed numbers and allowed
enhancements but never said what the power DOES.

Source: a Bin Crawler export_powers run against the live client (see
tools/gamedata/README.md). Each power record carries `display_short_help` (the
one-line tag, e.g. "Ranged, DMG(Lethal), DoT(Toxic), Immobilize") and
`display_help` (the full description), already resolved from the client's
message table. Our names reach client names directly, or via the local
tools/gamedata/power_aliases.json (tools/build_power_aliases.py) where the two
disagree (Temporal_Manipulation = client Time_Manipulation).

Text handling: verbatim, except the client's display markup. <color ...> /
</color> wrappers are dropped (the app has its own theme) and <br> becomes a
newline; <b>/<i> are kept for the app to render.

Coverage denominator (standing rule, hard-fail): every power in every set the
builder can offer — each playable archetype's primary/secondary/epic sets, the
pools, and the Inherent sets minus the internal inherents the client snapshot
omits (power_aliases.json "inherents_not_in_snapshot") — must resolve a
non-empty description. M comes from data/powersets.json + data/archetypes.json,
independent of the export.

Run:  python tools/extract_power_help.py [--export tools/gamedata/bin-crawler/out_full]
"""
import argparse
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "power_help.json")
ALIASES = os.path.join(ROOT, "tools", "gamedata", "power_aliases.json")

# Ours -> client records the alias map doesn't reach. Evidence per entry; extend
# ONLY with evidence (the coverage gate below names anything still unresolved).
RENAMES = {
    # The game grants Pack Mentality as a temporary power, not inside the Beast
    # Mastery set; it is the client's only "Pack Mentality" record and its own
    # text names the mechanic ("As your Beast Mastery pets attack you will gain
    # stacks of Pack Mentality...").
    "Mastermind_Summon.Beast_Mastery.Pack_Mentality": "Temporary_Powers.Temporary_Powers.Pack_Mentality",
}

# Our displayed name -> the game's CURRENT name for the same power, where the
# game renamed it and our display name is older. Evidence: the joined client
# record (same set, same internal name) carries the new name, and no client
# record in that set still carries the old one. The text is the right text for
# the power; only our label lags.
GAME_RENAMED = {
    "Adrenalin Boost": "Adrenaline Boost",            # spelling (Empathy, every AT)
    "Web Grenade": "Debilitating Web Grenade",        # Traps, every AT
    "Caltrops": "Shrapnel Grenade",                   # Traps: "toss a grenade ... spread a handful of Caltrops"
}


def clean(text):
    text = re.sub(r"</?color[^>]*>", "", text or "", flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    return re.sub(r"[ \t]+\n", "\n", text).strip()


def load_export(export_dir):
    """Lower-cased client full_name -> (short help, help, client display name)."""
    out = {}
    for f in glob.glob(os.path.join(export_dir, "**", "*.json"), recursive=True):
        base = os.path.basename(f)
        if base == "index.json" or base.startswith("_"):
            continue
        try:
            rec = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(rec, dict) and rec.get("full_name") and "display_help" in rec:
            out[rec["full_name"].lower()] = (clean(rec.get("display_short_help")), clean(rec.get("display_help")),
                                             rec.get("display_name") or "")
    return out


def offered_sets():
    """Every powerset the builder can put on a power card (the denominator)."""
    sets = json.load(open(os.path.join(DATA, "powersets.json"), encoding="utf-8"))
    ats = json.load(open(os.path.join(DATA, "archetypes.json"), encoding="utf-8"))["archetypes"]
    names = {ps["full_name"] for ps in sets["pools"]}
    for at in ats:
        if not at.get("playable"):
            continue
        by = sets["by_archetype"].get(at["name"], {})
        for kind in ("primary", "secondary", "epic"):
            names |= {ps["full_name"] for ps in by.get(kind, [])}
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", default=os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full"))
    args = ap.parse_args()

    client = load_export(args.export)
    if not client:
        sys.exit(f"FAIL: no power records with display_help under {args.export}")
    alias_doc = json.load(open(ALIASES, encoding="utf-8"))
    aliases = {k.lower(): v.lower() for k, v in {**alias_doc["aliases"], **RENAMES}.items()}
    internal_inherents = set(alias_doc.get("inherents_not_in_snapshot", []))

    powers = json.load(open(os.path.join(DATA, "powers.json"), encoding="utf-8"))
    # (client set, displayed name) -> records, for the display-identity rung.
    by_display = {}
    for cfn, rec in client.items():
        by_display.setdefault((cfn.rsplit(".", 1)[0], rec[2].lower()), []).append(rec)

    out, shown_as, client_name = {}, {}, {}
    for recs in powers.values():
        for p in recs:
            fn = p["full_name"]
            key = fn.lower() if fn.lower() in client else aliases.get(fn.lower(), "")
            hit = client.get(key)
            # Client internal names are historical and REUSED (Tactical Arrow's
            # record named Gymnastics is displayed "Oil Slick Arrow"). When the
            # joined record shows a different name, take the UNIQUE record in the
            # same client set that shows ours.
            if hit and hit[2] != p.get("display_name"):
                alt = by_display.get((key.rsplit(".", 1)[0], (p.get("display_name") or "").lower()), [])
                if len(alt) == 1:
                    hit = alt[0]
            if hit and hit[1]:
                out[fn] = [hit[0], hit[1]]
                shown_as[fn], client_name[fn] = p.get("display_name", ""), hit[2]

    offered = offered_sets() | {ps for ps in powers if ps.startswith("Inherent.")}
    expected = [p["full_name"] for ps in sorted(offered) for p in powers.get(ps, [])
                if p["full_name"] not in internal_inherents]
    missing = [fn for fn in expected if fn not in out]
    print(f"client records: {len(client)}; descriptions written: {len(out)}")
    print(f"builder-offered powers with a description: {len(expected) - len(missing)} of {len(expected)} expected checked")
    if missing:
        print("FAIL: offered powers with no client description:")
        for fn in missing[:50]:
            print("  ", fn)
        sys.exit(1)
    # Identity check: the client internal names are historical and REUSED (our
    # Sonic_Aura.Noise_Cancellation is the game's "Somatic Aura"), so a wrong
    # name join would put one power's text under another. The name the panel
    # shows must be the name on the client record the text came from.
    wrong = [fn for fn in expected if shown_as[fn] != client_name[fn]
             and GAME_RENAMED.get(shown_as[fn]) != client_name[fn]]
    renamed = sum(1 for fn in expected if GAME_RENAMED.get(shown_as[fn]) == client_name[fn])
    print(f"of those, game-renamed (pinned in GAME_RENAMED): {renamed}")
    print(f"description matches the power's displayed name: {len(expected) - len(wrong)} of {len(expected)} expected checked")
    if wrong:
        print("FAIL: text joined to a differently-named client power:")
        for fn in wrong[:50]:
            print(f"   {fn}: shows '{shown_as[fn]}', client record is '{client_name[fn]}'")
        sys.exit(1)

    # Ship only what a power card can show (pets/temp/set-bonus records never reach the panel).
    shipped = {fn: out[fn] for fn in expected}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(shipped, fh, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    print(f"shipped {len(shipped)} descriptions")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
