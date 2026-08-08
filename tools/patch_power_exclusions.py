"""Back-fill MUTUALLY EXCLUSIVE power pairs - the game refuses both, we allowed both.

THE ERROR
---------
Several powers forbid each other, and the game says so in its own words. Broad
Sword's Boomerang Slice prints

    "This power is mutually exclusive from Slice."

and the client encodes it as a `requires` of exactly `<other power> !` on BOTH
records. Our data carried none of it, `engine.validate_build` raised nothing,
and `_picks_legal` - the certification legality gate - knew about exactly TWO of
the pairs because someone had hardcoded the VEAT grenades by hand:

    _VEAT_DUPLICATE_PAIRS = [ ...Frag_Grenade..., ...Venom_Grenade... ]

So the tool would happily build, and a wave would happily certify, a Dark Armor
character holding BOTH Dark Regeneration and Obscure Sustenance. That is the
same defect class as the eight illegal champions 0.12.30 shipped, and Joel's
ruling on it is settled: LEGALITY OUTRANKS SCORE.

⚠ Champion exposure was counted BEFORE any change: ZERO of 24 certified
contexts hold both sides of any pair. Nothing certified is illegal today; the
hole is that nothing was stopping it.

NINE PAIRS, both sides already in our data:
    Dark Regeneration <-> Obscure Sustenance      (5 archetypes)
    Master Brawler <-> Practiced Brawler          (Sentinel SR)
    Frag Grenade <-> CS Frag Grenade              (the hardcoded VEAT pair)
    Venom Grenade <-> CS Venom Grenade            (the other hardcoded one)
    Build Up <-> Follow Up                        (Widow)

⚠ ONLY THE PURE `X !` FORM IS TAKEN. The client's `requires` field also carries
archetype gates and prerequisite expressions; a regex for the whole language
would be a second, drifting parser of a field that already cost this project a
12-hour wave when it was read too eagerly. Anything else is counted and left.

⚠ MIRRORED OR NOT AT ALL. A pair is written only when BOTH records name each
other, because a one-sided exclusion is either a different mechanic or a parse
artefact, and guessing which would put a false rule into the legality gate.

⚠ powers.json is COMPACT single-line. Read binary, write binary, no indent.
Usage:  python tools/patch_power_exclusions.py [--check]
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POWERS = os.path.join(ROOT, "data", "powers.json")
CRAWL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")

KEY = "excludes"
_PURE = re.compile(r"^([\w.]+)\s+!$")

# the hand-maintained list this replaces; the patcher proves it is a superset
VEAT_HARDCODED = {
    ("Arachnos_Soldiers.Arachnos_Soldier.Frag_Grenade",
     "Arachnos_Soldiers.Crab_Spider_Soldier.CS_Frag_Grenade"),
    ("Arachnos_Soldiers.Arachnos_Soldier.Venom_Grenade",
     "Arachnos_Soldiers.Crab_Spider_Soldier.CS_Venom_Grenade"),
}


def client_index():
    out = {}
    for dirpath, _dirs, files in os.walk(CRAWL):
        for fn in files:
            if not fn.endswith(".json") or fn == "index.json":
                continue
            try:
                with open(os.path.join(dirpath, fn), encoding="utf-8") as fh:
                    rec = json.load(fh)
            except Exception:  # noqa: BLE001
                continue
            if rec.get("full_name"):
                out[rec["full_name"]] = rec
    return out


def main():
    check_only = "--check" in sys.argv
    raw = open(POWERS, "rb").read()
    data = json.loads(raw.decode("utf-8"))
    orig = json.loads(raw.decode("utf-8"))
    client = client_index()
    ours = {p["full_name"] for _ps, l in data.items() for p in l}

    # IDEMPOTENT
    stripped = 0
    for _ps, lst in data.items():
        for p in lst:
            if KEY in p:
                del p[KEY]
                stripped += 1
    if stripped:
        print(f"(re-run: stripped {stripped} keys from a previous pass)")

    pure, other_forms = {}, 0
    for fn, c in client.items():
        req = (c.get("requires") or "").strip()
        if not req:
            continue
        m = _PURE.match(req)
        if m:
            pure[fn] = m.group(1)
        elif req.endswith("!"):
            other_forms += 1

    # ⚠ mirrored, and both sides ours
    pairs = set()
    for a, b in pure.items():
        if a in ours and b in ours and pure.get(b) == a:
            pairs.add(tuple(sorted((a, b))))
    one_sided = sum(1 for a, b in pure.items()
                    if a in ours and b in ours and pure.get(b) != a)

    if not check_only:
        for _ps, lst in data.items():
            for p in lst:
                mine = sorted({b if p["full_name"] == a else a
                               for a, b in pairs if p["full_name"] in (a, b)})
                if mine:
                    p[KEY] = mine

    print(f"client powers with a pure `X !` requires        : {len(pure)}")
    print(f"  MIRRORED pairs with both sides in our data    : {len(pairs)}")
    for a, b in sorted(pairs):
        print(f"      {a.split('.')[-1]:<22} <-> {b.split('.')[-1]:<22} "
              f"({a.rsplit('.', 1)[0]})")
    print(f"  powers marked                                 : "
          f"{len({x for pr in pairs for x in pr})}")
    print(f"STATED EXCLUSION, one-sided (not mirrored)      : {one_sided}")
    print(f"STATED EXCLUSION, other `requires` forms untouched : {other_forms}")
    print(f"STATED EXCLUSION, pairs with a side we do not carry: "
          f"{sum(1 for a, b in pure.items() if (a in ours) != (b in ours)) // 1}")

    # the hand-maintained VEAT list must be a strict SUBSET of what the client says
    missing = VEAT_HARDCODED - pairs - {tuple(sorted(p)) for p in VEAT_HARDCODED
                                        if tuple(sorted(p)) in pairs}
    if missing:
        print(f"\nFAIL: the client does not confirm a hardcoded VEAT pair: {missing}")
        sys.exit(1)
    print("the hardcoded _VEAT_DUPLICATE_PAIRS are a SUBSET of these - the "
          "client confirms both, so the generalisation loses nothing")

    if not pairs:
        print("\nFAIL: found nothing - the client index is probably empty")
        sys.exit(1)
    if check_only:
        return

    out = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    probe = json.loads(out.decode("utf-8"))
    for src in (probe, orig):
        for _ps, lst in src.items():
            for p in lst:
                p.pop(KEY, None)
    if (json.dumps(probe, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            != json.dumps(orig, separators=(",", ":"), ensure_ascii=False).encode("utf-8")):
        print("\nINVARIANCE FAILED: stripping the key does not reproduce the "
              "baseline - refusing to write")
        sys.exit(2)
    print("invariance: stripping the added keys reproduces the baseline exactly")
    open(POWERS, "wb").write(out)
    print(f"wrote {POWERS} ({len(out):,} bytes, was {len(raw):,})")


if __name__ == "__main__":
    main()
