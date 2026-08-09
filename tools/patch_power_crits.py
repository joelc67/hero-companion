"""v44 CRITICAL HITS - the chance the client states, at the floor it states it.

The Scrapper's and Stalker's defining mechanic, and the tool has never scored a
point of it. v36 deferred the whole class for want of grounding: "the export
carries 12/194 explicit, gates only - third-party chance tables are forbidden
basis". The 2026-08-08 `tags` finding removed that obstacle. The chances are in
the export, per power, and they are not a table anyone had to look up.

WHAT THE CLIENT SAYS, on Scrapper Broad Sword's Hack:

    base                          chance 1.0   scale 1.64
    CritSmall  + ScrapperCrit_ST  chance 0.05  scale 1.64   (target is a minion)
    CritLarge  + ScrapperCrit_ST  chance 0.10  scale 1.64   (target is not)

So a critical adds ONE HUNDRED PERCENT of the attack's own damage - the crit
row is the base row again - and the chance depends on the target's rank.

⚠⚠ THE FLOOR IS TAKEN, AND THAT IS A DELIBERATE UNDERSTATEMENT. Crediting the
0.10 needs the share of attacks that land on something above a minion, and the
scenario model does not carry a rank mix: `rank_acc` and `ctrl_land` were each
derived from one, but neither writes it down, and inverting `rank_acc` back into
a mix needs an assumption about the tail's composition - an assumption on top of
an assumption. The minimum stated chance needs NOTHING, is exact on a
minion-heavy spawn, and errs the same way every other honest gap here does.
The premium above it is stated and left for whoever supplies a rank mix.

⚠ ONLY PvE ROWS. `CritPlayer` groups carry `enttype target> player eq` and are
written at pv_mode 2, which `engine._pv_ok` gates off outside PvP.

⚠ DAMAGE HIDES IN `child_effects`. Hack's crit rows are one level down - the
Boomerang Slice lesson, and a first probe here reported "no damage rows" for an
attack that plainly has some.

⚠ powers.json is COMPACT single-line. Read binary, write binary, no indent.
Usage:  python tools/patch_power_crits.py [--check]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from add_wind_control import client_index, DMG, _TARGETING     # noqa: E402
from mode_tags import TAGS, PROB                               # noqa: E402

POWERS = os.path.join(ROOT, "data", "powers.json")
MARK = "crit_row"
# the PROB tags that ARE a critical. Overpower and the archetype-named ones are
# probabilistic too but they are mez or pool-attack bonuses, not crits.
CRIT_TAGS = {t for t, (c, _) in TAGS.items()
             if c == PROB and ("crit" in t.lower())}


def crit_rows(crec):
    """[(damage_type, scale, chance, table, pvp)] for this power's PvE crits.

    Groups are walked with their children because that is where damage lives.
    """
    out = []

    def walk(g):
        tags = set(g.get("tags") or [])
        if tags & CRIT_TAGS:
            req = g.get("requires_expression") or ""
            if "player" not in req:                    # PvP variants excluded
                ch = float(g.get("chance") or 0.0)
                for t in (g.get("templates") or []):
                    sc = float(t.get("scale") or 0.0)
                    if not sc:
                        continue
                    for a in (t.get("attribs") or []):
                        fam = a.replace("_Dmg", "")
                        # ⚠⚠ A CHANCE OF 1.0 IS NOT A DIE ROLL. StealthCrit
                        # on Kyokan and Mask Presence reads 1.0 because it is
                        # the GUARANTEED critical you get while hidden - gated
                        # on a play state, not on a roll. Taking it would have
                        # doubled those attacks unconditionally. Only a stated
                        # sub-1 chance is a probability this pass can price;
                        # the hidden case belongs with the SCENARIO class.
                        if fam in DMG and 0 < ch < 1.0:
                            out.append((DMG[fam], sc, ch, t.get("table")))
        for c in (g.get("child_effects") or []):
            walk(c)

    for g in (crec.get("effects") or []):
        walk(g)
    return out


def main():
    check = "--check" in sys.argv
    raw = open(POWERS, "rb").read()
    data = json.loads(raw.decode("utf-8"))
    orig = json.loads(raw.decode("utf-8"))
    client = client_index()

    # IDEMPOTENT: drop anything a previous pass added, then re-derive.
    # ⚠ THE BASELINE MUST BE STRIPPED TOO. `orig` is read from a file that may
    # already hold a previous pass's rows, so comparing against it un-stripped
    # makes a correct re-run look like it changed the world. The guard caught
    # exactly that here and refused to write - which is what it is for, and it
    # left the OVER-BROAD earlier version on disk until this was fixed.
    for lst in orig.values():
        for p in lst:
            if p.get("damage_effects") is not None:
                p["damage_effects"] = [e for e in p["damage_effects"]
                                       if not e.get(MARK)]
    dropped = 0
    for lst in data.values():
        for p in lst:
            keep = [e for e in (p.get("damage_effects") or []) if not e.get(MARK)]
            dropped += len(p.get("damage_effects") or []) + 0 - len(keep)
            if p.get("damage_effects") is not None:
                p["damage_effects"] = keep
    if dropped:
        print(f"(re-run: removed {dropped} row(s) from a previous pass)")

    # ⚠ PLAYER-PICKABLE RECORDS ONLY. The client puts the crit tags on pet and
    # redirect records too (Pets.Titan_Weapons among them), and a pet does not
    # crit as its owner's archetype. Crediting them would inflate pet damage on
    # the strength of a tag that describes the player's mechanic. Excluded, and
    # if some pet genuinely does crit that is an understatement, like the rest.
    NOT_A_PICK = ("Pets.", "Redirects.", "Villain_Pets.", "Mastermind_Pets.",
                  "Incarnate.", "Boosts.", "Temporary_Powers.")
    added, powers_hit, by_set, skipped_pets, skipped_shared = 0, 0, {}, 0, 0
    for _ps, lst in data.items():
        for p in lst:
            c = client.get(p["full_name"])
            if not c:
                continue
            if p["full_name"].startswith(NOT_A_PICK):
                if crit_rows(c):
                    skipped_pets += 1
                continue
            # ⚠⚠ ONLY THE TWO ARCHETYPES THE GAME GIVES A CRIT INHERENT.
            # Our Epic.* records are SHARED across archetypes (that is why the
            # epic set bridge exists), and the client's crit tags on them
            # describe the Scrapper/Stalker variant - so a first pass credited
            # criticals to Defenders, Tankers, Peacebringers and Warshades
            # through their epic picks, taking exposure from 6 champions to 14.
            # Sentinels have Opportunity and Blasters have Defiance; neither
            # crits. Scrapper (Critical Hit) and Stalker (Assassination) do.
            if not p["full_name"].startswith(("Scrapper_", "Stalker_")):
                if crit_rows(c):
                    skipped_shared += 1
                continue
            rows = crit_rows(c)
            if not rows:
                continue
            # ⚠ THE FLOOR PER DAMAGE TYPE. A power states its crit twice (once
            # per target-rank branch) and we take the smaller, which is the one
            # that needs no rank mix to be true.
            best = {}
            for dt, sc, ch, tbl in rows:
                cur = best.get(dt)
                if cur is None or ch < cur[1]:
                    best[dt] = (sc, ch, tbl)
            new = []
            for dt, (sc, ch, tbl) in sorted(best.items()):
                new.append({"effect": "Damage", "damage_type": dt, "scale": sc,
                            "nmag": 1.0, "modifier_table": tbl,
                            "probability": round(ch, 4), "duration": 0.0,
                            "pv_mode": 1, "enhance_aspect": "Damage",
                            "ed_schedule": 0, MARK: True})
            if not check:
                p.setdefault("damage_effects", []).extend(new)
            added += len(new)
            powers_hit += 1
            by_set[_ps] = by_set.get(_ps, 0) + 1

    print(f"{'would add' if check else 'ADDED'} {added} crit row(s) across "
          f"{powers_hit} powers in {len(by_set)} powersets")
    print(f"    excluded, not player-pickable: {skipped_pets} record(s)")
    print(f"    excluded, shared/non-critting archetype: {skipped_shared}")
    for ps, n in sorted(by_set.items(), key=lambda x: -x[1])[:8]:
        print(f"    {ps:<44}{n}")
    chances = sorted({r["probability"] for lst in data.values() for p in lst
                      for r in (p.get("damage_effects") or []) if r.get(MARK)})
    print(f"    distinct chances taken (the floors): {chances}")
    if check:
        return

    out = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    probe = json.loads(out.decode("utf-8"))
    for lst in probe.values():
        for p in lst:
            if p.get("damage_effects") is not None:
                p["damage_effects"] = [e for e in p["damage_effects"]
                                       if not e.get(MARK)]
    if (json.dumps(probe, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            != json.dumps(orig, separators=(",", ":"), ensure_ascii=False).encode("utf-8")):
        print("INVARIANCE FAILED - refusing to write")
        sys.exit(2)
    print("invariance: stripping the crit rows reproduces the baseline exactly")
    with open(POWERS, "wb") as fh:
        fh.write(out)
    print(f"wrote powers.json ({len(out):,} bytes, was {len(raw):,})")


if __name__ == "__main__":
    main()
