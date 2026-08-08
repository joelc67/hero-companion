"""Back-fill self ABSORB shields, which our data has never carried on any power.

THE ERROR
---------
Absorb is a shield of hit points that soaks damage before your own HP does, and
38 player powers grant it - Particle Shielding, Master Brawler, Ablative
Carapace, Wild Bastion, Insulating Circuit, Frigid Shield. Our records carry
NONE of it, and the engine has no branch for it either: `Absorb` exists in our
code only as an enhancement aspect name and as a display unit. So Radiation
Armor's signature survival click has been scored on its regeneration half alone.

Found by classifying the empty-record class; it is the one item there that
needed a term rather than only data.

⚠ ONLY THE HEAL-TABLE ROWS ARE TAKEN, AND THE REST ARE PINNED. The client
grants absorb two ways and only one has unambiguous units:

  Melee_HealSelf / Ranged_Heal   -> HIT POINTS, exactly like a heal, and our
                                    engine already treats Heal/Absorb/HitPoints
                                    as point-valued (`_POINT_HP`). 3.0 on a
                                    Scrapper is 401.6 HP - about 30% of base HP,
                                    which is what "a strong absorption shield"
                                    should read.
  Melee_Ones / Ranged_Ones 1.0   -> 19 records (Bio Armor's Ablative Carapace,
                                    Nature's Wild Bastion). A literal 1.0 on the
                                    ones table cannot mean one hit point, so the
                                    scale is a multiplier into something the
                                    export does not carry. NOT GUESSED AT - same
                                    ruling as Gamma Boost's flat 1.0/1.0, which
                                    the game's own help proves is a scaling
                                    curve. Pinned in reality_check_empty_records.

⚠ SELF ONLY. 32 of the client's absorb templates target AnyAffected - Spirit
Ward and Insulating Circuit shield an ALLY. Nothing scores a shield placed on
someone else, so landing that data would be inert; it stays pinned with the
ally mez-protection gap it resembles.

⚠ GATED GROUPS ARE NOT TAKEN. Bio Armor's second absorb group is
`kDefensiveAdaptation Source.Mode?` - a conditional claim, and the mode
machinery does not exist.

⚠ FIRST YIELDING GROUP WINS. Master Brawler carries the same 4.0 twice, once
per PvE/PvP group; taking both would double the shield.

⚠ powers.json is COMPACT single-line. Read binary, write binary, no indent.
Usage:  python tools/patch_power_absorb.py [--check]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POWERS = os.path.join(ROOT, "data", "powers.json")
CRAWL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
TABLES = os.path.join(ROOT, "data", "modifier_tables.json")

MARK = "absorb_row"
NOT_PLAYER = ("Incarnate", "Pets", "Villain_Pets", "Mastermind_Pets",
              "Kheldian_Pets", "Temporary_Powers", "Redirects", "DevouringEarth")


def _seconds(dur):
    if dur is None:
        return None
    if isinstance(dur, (int, float)):
        return float(dur)
    try:
        return float(str(dur).strip().split()[0])
    except (ValueError, IndexError):
        return None


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


def absorb_row(crec):
    """The first ungated, Self, heal-table Absorb grant. (row, twins, ones_only)."""
    row, twins, ones = None, 0, 0
    for grp in (crec.get("effects") or []):
        if (grp.get("requires_expression") or "").strip():
            continue
        for t in (grp.get("templates") or []):
            if ("Absorb" not in (t.get("attribs") or [])
                    or t.get("aspect") != "Maximum"
                    or t.get("target") != "Self"
                    or not (t.get("scale") or 0)):
                continue
            tbl = (t.get("table") or "")
            if "heal" not in tbl.lower():
                ones += 1            # the units-unknown class, counted not taken
                continue
            if row is not None:
                twins += 1
                continue
            row = {"scale": float(t["scale"]), "dur": _seconds(t.get("duration")),
                   "table": tbl}
    return row, twins, ones


def main():
    check_only = "--check" in sys.argv
    raw = open(POWERS, "rb").read()
    data = json.loads(raw.decode("utf-8"))
    orig = json.loads(raw.decode("utf-8"))
    client = client_index()
    known_tables = set(json.load(open(TABLES, encoding="utf-8"))["tables"])

    # IDEMPOTENT: strip our own previous rows, then re-derive from the client.
    stripped = 0
    for _ps, lst in data.items():
        for p in lst:
            fx = p.get("self_effects")
            if not fx:
                continue
            kept = [e for e in fx if not e.get(MARK)]
            stripped += len(fx) - len(kept)
            if len(kept) != len(fx):
                p["self_effects"] = kept       # assign, never delete the key
    if stripped:
        print(f"(re-run: stripped {stripped} rows from a previous pass)")

    covered = expected = patched = 0
    twin_dropped = ones_class = not_player = no_rech = 0
    touched = []
    for _ps, lst in data.items():
        for p in lst:
            crec = client.get(p["full_name"])
            if not crec:
                continue
            covered += 1
            row, twins, ones = absorb_row(crec)
            ones_class += ones
            if not row:
                continue
            if p["full_name"].split(".")[0] in NOT_PLAYER:
                not_player += 1
                continue
            if row["table"] not in known_tables:
                continue
            expected += 1
            twin_dropped += twins
            # ⚠ ask whether we already carry it under ANY name first
            if any(str(e.get("effect", "")).lower() == "absorb"
                   for e in (p.get("self_effects") or [])):
                continue
            # the cadence the shield is re-applied at. A click re-arms on its own
            # recharge; anything with no recharge re-applies on its duration.
            rech = p.get("base_recharge") or 0.0
            if not rech and not row["dur"]:
                no_rech += 1
                continue
            if not check_only:
                fx = p.setdefault("self_effects", [])
                fx.append({
                    "effect": "Absorb",
                    "damage_type": "None",
                    "scale": row["scale"],
                    "nmag": 1.0,
                    "modifier_table": row["table"],
                    # ⚠ THE ASPECT IS "Absorb", NOT "Heal", and our own data
                    # settles it: Crafted_Heal boosts four aspects - Heal,
                    # HitPoints, Regeneration and Absorb - so a Heal IO reaches
                    # the shield through the Absorb aspect. Writing "Heal" here
                    # looks right (the client's boosts_allowed says Heal) and
                    # silently enhances nothing.
                    "enhance_aspect": "Absorb",
                    "ed_schedule": 0,
                    "pv_mode": 0,
                    "duration": row["dur"],
                    "host_recharge": rech,
                    MARK: True,
                })
            patched += 1
            touched.append((p["full_name"], row["scale"], row["dur"], rech))

    print(f"our powers covered by the client export        : {covered}")
    print(f"client grants a SELF heal-table absorb shield  : {expected}   <- denominator")
    print(f"  {'would patch' if check_only else 'patched'} : {patched}")
    for fn, sc, dur, rech in touched:
        print(f"      {fn}  scale {sc}, {dur}s shield, {rech}s recharge")
    print(f"STATED EXCLUSION, units-unknown *_Ones absorb rows : {ones_class} "
          f"(Bio Armor, Nature Affinity - a literal 1.0 cannot be one hit point)")
    print(f"STATED EXCLUSION, PvE/PvP twin groups dropped      : {twin_dropped}")
    print(f"STATED EXCLUSION, not a player power               : {not_player}")
    print(f"STATED EXCLUSION, no cadence stated                : {no_rech}")
    print("STATED EXCLUSION, ally-targeted absorb (Spirit Ward, Insulating "
          "Circuit): nothing scores a shield on someone else")
    print("STATED EXCLUSION, gated groups (Bio's Defensive Adaptation mode)")

    if expected == 0:
        print("\nFAIL: found nothing - the client index is probably empty")
        sys.exit(1)
    if check_only:
        return

    out = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    probe = json.loads(out.decode("utf-8"))
    for src in (probe, orig):
        for _ps, lst in src.items():
            for p in lst:
                fx = p.get("self_effects")
                if fx:
                    p["self_effects"] = [e for e in fx if not e.get(MARK)]
    if (json.dumps(probe, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            != json.dumps(orig, separators=(",", ":"), ensure_ascii=False).encode("utf-8")):
        print("\nINVARIANCE FAILED: stripping the added rows does not reproduce the "
              "baseline - refusing to write")
        sys.exit(2)
    print("invariance: stripping the added rows reproduces the baseline exactly")
    open(POWERS, "wb").write(out)
    print(f"wrote {POWERS} ({len(out):,} bytes, was {len(raw):,})")


if __name__ == "__main__":
    main()
