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
  Melee_Ones / Ranged_Ones 1.0   -> ANSWERED GAME-FIRST, 2026-08-08. A literal
                                    1.0 could not mean one hit point, and the
                                    reason is that the magnitude is NOT in the
                                    scale at all: the client carries it as an
                                    RPN `magnitude_expression`, and Bio Armor's
                                    Ablative Carapace reads

                                        Max.kHitPoints source> 0.3 * @Strength *

                                    = 30% of the character's max HP. Eleven
                                    self-targeted records are proportional to
                                    max HP and carry no health dependence at
                                    all, so they need NO scenario input and are
                                    taken here. `@StdResult` variants resolve to
                                    their own scale: their table is Melee_Ones,
                                    which is 1.0 for every playable column.

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


def max_hp_fraction(t):
    """The fraction of MAX HP an absorb template grants, or None.

    The client carries these magnitudes as RPN, not as a table scale, which is
    why the scale is a bare 1.0 and looked like "units unknown" until the
    expression was read:

        Max.kHitPoints source> 0.3 * @Strength *   -> 30% of max HP
        Max.kHitPoints source> @StdResult *        -> the template's own scale

    ⚠ ONLY THESE TWO SHAPES ARE DECODED, and anything else returns None rather
    than a guess. `@StdResult` is safe to resolve here because every one of
    these rows sits on Melee_Ones, which is 1.0 for all 15 playable columns -
    checked, not assumed. Health-DEPENDENT expressions (kHitPoints%) are a
    different class and are deliberately not touched: they need an operating
    health, which is a scenario input nobody has ruled on.
    """
    e = (t.get("magnitude_expression") or "").split()
    if len(e) < 2 or e[0] != "Max.kHitPoints" or e[1] != "source>":
        return None
    rest = e[2:]
    if rest == ["@StdResult", "*"]:
        return float(t.get("scale") or 0.0)
    if len(rest) == 3 and rest[1] == "*" and rest[2] == "@Strength":
        try:
            return float(rest[0])
        except ValueError:
            return None
    if len(rest) == 4 and rest[1] == "*" and rest[2] == "@Strength" and rest[3] == "*":
        try:
            return float(rest[0])
        except ValueError:
            return None
    return None


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

    # ---- the MAX-HP-PROPORTIONAL class, decoded from the client's own RPN ----
    hp_patched, hp_touched, hp_refused = 0, [], 0
    for _ps, lst in data.items():
        for p in lst:
            crec = client.get(p["full_name"])
            if not crec or p["full_name"].split(".")[0] in NOT_PLAYER:
                continue
            frac = None
            for grp in (crec.get("effects") or []):
                if (grp.get("requires_expression") or "").strip():
                    continue          # gated: Bio's Defensive Adaptation mode
                for t in (grp.get("templates") or []):
                    if ("Absorb" not in (t.get("attribs") or [])
                            or t.get("target") != "Self"
                            or not (t.get("magnitude_expression") or "")):
                        continue
                    f = max_hp_fraction(t)
                    if f is None:
                        hp_refused += 1
                    elif frac is None:
                        frac = (f, t.get("duration"))
            if not frac or not frac[0]:
                continue
            if any(str(e.get("effect", "")).lower() == "absorb"
                   for e in (p.get("self_effects") or [])):
                continue
            if not check_only:
                p.setdefault("self_effects", []).append({
                    "effect": "Absorb",
                    "damage_type": "None",
                    "scale": 1.0,
                    "nmag": 1.0,
                    "modifier_table": "Melee_Ones",
                    "enhance_aspect": "Absorb",
                    "ed_schedule": 0,
                    "pv_mode": 0,
                    "duration": _seconds(frac[1]),
                    "host_recharge": p.get("base_recharge") or 0.0,
                    # the engine multiplies the archetype's BASE hp by this
                    "max_hp_frac": frac[0],
                    MARK: True,
                })
            hp_patched += 1
            hp_touched.append((p["full_name"], frac[0]))

    print(f"our powers covered by the client export        : {covered}")
    print(f"client grants a SELF heal-table absorb shield  : {expected}   <- denominator")
    print(f"  {'would patch' if check_only else 'patched'} : {patched}")
    for fn, sc, dur, rech in touched:
        print(f"      {fn}  scale {sc}, {dur}s shield, {rech}s recharge")
    print(f"  MAX-HP-PROPORTIONAL shields ({'would patch' if check_only else 'patched'}) "
          f": {hp_patched}")
    for fn, f in hp_touched:
        print(f"      {fn}  {f*100:.1f}% of max HP")
    print(f"  RPN shapes refused rather than guessed        : {hp_refused}")
    print(f"STATED EXCLUSION, *_Ones absorb rows read from the table : {ones_class} "
          f"(their magnitude lives in the RPN expression, decoded above, not the table)")
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
