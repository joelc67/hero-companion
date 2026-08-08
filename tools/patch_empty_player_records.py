"""Back-fill PLAYER records that hold NO effect rows at all while the client
populates them - the armour half, where the engine already has a branch.

THE CLASS THIS COMES FROM
-------------------------
876 of our power records hold zero effect rows in every bucket while the client
gives them ungated, non-zero templates. `reality_check_empty_records.py` is the
standing instrument that classifies all 876; this patcher fixes the part that is
a plain data gap and nothing more.

⚠⚠ MOST OF THAT 876 IS NOT A DATA GAP, AND THAT IS WHY THIS PATCHER IS SMALL.
The classification found: 524 records that are not player powers (Alpha/Genesis
boost DEFINITIONS, pet records, temp tokens), 210 player records whose client
templates are pure plumbing (Grant_Power, Set_Mode, Create_Entity, movement),
and a handful of real gaps of which most need a CONSUMER that does not exist
(Absorb has no engine branch) or a scenario input (the debuff-resistance
families, blocked exactly as mez_in is). Two records are a plain data gap.

⚠ REGENERATION AND RECOVERY ARE DELIBERATELY NOT IN THE ALLOWLIST, and this is
the "check the game, not your parse" rule earning its keep. The only empty
records wanting them are the five Gamma Boosts, and the game's own help says:

    "The lower your current health is, the greater the regeneration bonus...
     The higher your current health is, the greater the recovery bonus"

The client's flat Regeneration 1.0 and Recovery 1.0 are the two ENDS of one
scaling curve and can never both apply. Writing them as flat rows would credit
+100% regeneration and +100% recovery at once. It stays pinned as the scaling
class, beside Agile's scaling damage resistance (whose templates the export
carries at scale 0.0 for the same reason).

WHAT IT DOES TAKE, and why each is safe:
  * the record is EMPTY, so there is nothing to conflict with and none of the
    wholesale-sync hazard that makes target-cap drift untouchable.
  * Defense and Resistance ONLY - both have an engine branch AND an existing
    convention in our own data to copy rather than invent.
  * THE FIRST YIELDING GROUP WINS WHOLE. The client's second group is the PvP
    variant (its tell is an Elusivity template) and it is not merely a copy:
    Shield Defense's adds a Psionic defence vector our populated Brute,
    Scrapper and Tanker records all carry at pv_mode 2. Taking rows per
    (effect, damage type) instead of per group let that vector through into
    PvE - caught before it shipped, and it is exactly the sort of quiet wrong
    number this audit exists to stop. When a twin group exists the rows are
    written pv_mode 1 (PvE only), matching the siblings, so PvP reads nothing
    rather than a wrong number: a stated understatement.
  * Redirects/* is excluded: those records are empty BY DESIGN, their effects
    live on the twin (the reconciliation lane's 230 proven redirect folds).

Verified against a populated SIBLING wherever one exists - Shield Defense's
Active Defense is empty on Stalker and populated on Brute, Scrapper and Tanker,
so the shape is copied, not guessed, and only the AT column differs.

⚠ powers.json is COMPACT single-line. Read binary, write binary, no indent.
Usage:  python tools/patch_empty_player_records.py [--check]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POWERS = os.path.join(ROOT, "data", "powers.json")
CRAWL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
TABLES = os.path.join(ROOT, "data", "modifier_tables.json")

MARK = "empty_record_row"
BUCKETS = ("self_effects", "buff_effects", "debuff_effects",
           "control_effects", "heal_effects", "damage_effects")
NOT_PLAYER = ("Incarnate", "Pets", "Villain_Pets", "Mastermind_Pets",
              "Kheldian_Pets", "Temporary_Powers", "Inherent", "Redirects")
# client vocabulary -> ours
DMG = {"Smashing": "Smashing", "Lethal": "Lethal", "Fire": "Fire", "Cold": "Cold",
       "Energy": "Energy", "Negative_Energy": "Negative", "Psionic": "Psionic",
       "Toxic": "Toxic", "Melee": "Melee", "Ranged": "Ranged", "Area": "AoE"}


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


def classify(t):
    """(effect, enhance_aspect, ed_schedule) for an allowlisted template, else None."""
    tbl = (t.get("table") or "").lower()
    asp = t.get("aspect")
    if asp == "Current" and "buff_def" in tbl:
        return "Defense", "Defense", 1
    if asp == "Resistance" and "res_dmg" in tbl:
        return "Resistance", "Resistance", 1
    return None


def power_type_from_game(crec, sibling_types):
    """(power_type, evidence) or (None, why-not) - TWO signals, or nothing.

    ⚠ THE EFFECTS ALONE WOULD HAVE LANDED INERT, and that is worth stating
    plainly: the engine only counts a power's self effects when
    `power_type in ACTIVE_POWER_TYPES` (auto or toggle). Both stubs carry
    power_type 0 (click), so a perfect effect back-fill measured ZERO through
    the real route. The stub was wrong in two fields, not one.

    Signal A is the game's own word - display_short_help opens "Toggle:" or
    "Auto:". Signal B is a populated SIBLING record of the same power on
    another archetype. Where both exist they must AGREE or nothing is written.
    """
    short = (crec.get("display_short_help") or "").strip().lower()
    said = 2 if short.startswith("toggle") else 1 if short.startswith("auto") else None
    if said is None:
        return None, "the game states no Auto/Toggle prefix"
    if sibling_types and sibling_types != {said}:
        return None, (f"REFUSED - the game says {said} and populated siblings "
                      f"say {sorted(sibling_types)}")
    how = "the game's own Auto/Toggle prefix"
    if sibling_types:
        how += " + agreeing populated siblings"
    return said, how


def wanted_rows(crec):
    """Allowlisted Self rows, first group wins, PvP twin counted not taken."""
    rows, seen, twins = [], set(), 0
    for grp in (crec.get("effects") or []):
        if (grp.get("requires_expression") or "").strip():
            continue
        # ⚠ THE FIRST YIELDING GROUP WINS WHOLE, not row by row. Taking rows
        # per (effect, damage type) let a vector that exists ONLY in the PvP
        # group through at PvE: Shield Defense's second group adds Psionic
        # defence, and our populated Brute/Scrapper/Tanker siblings all carry
        # that at pv_mode 2. One extra vector in PvE is exactly the kind of
        # quiet wrong number this whole audit is about.
        if rows:
            twins += sum(1 for t in (grp.get("templates") or [])
                         if t.get("target") == "Self" and (t.get("scale") or 0)
                         and classify(t))
            continue
        for t in (grp.get("templates") or []):
            if t.get("target") != "Self" or not (t.get("scale") or 0):
                continue
            hit = classify(t)
            if not hit:
                continue
            eff, asp, ed = hit
            for a in (t.get("attribs") or []):
                dt = DMG.get(a.replace("_Dmg", ""))
                if not dt:
                    continue
                key = (eff, dt)
                if key in seen:
                    twins += 1
                    continue
                seen.add(key)
                rows.append({"effect": eff, "damage_type": dt,
                             "scale": float(t["scale"]), "aspect": asp,
                             "ed": ed, "dur": _seconds(t.get("duration")),
                             "table": t.get("table")})
    return rows, twins


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
                # ⚠ ASSIGN, NEVER DELETE. These records carry
                # "self_effects": [] rather than no key at all, so removing the
                # key breaks byte-identity - the invariance guard caught exactly
                # that and refused to write.
                p["self_effects"] = kept
            if "power_type_was" in p:
                p["power_type"] = p.pop("power_type_was")
    if stripped:
        print(f"(re-run: stripped {stripped} rows from a previous pass)")

    # populated siblings: same power leaf + same powerset leaf, other archetype
    sib = {}
    for _ps, lst in data.items():
        for p in lst:
            if not (p.get("self_effects") or []) or p.get("power_type") is None:
                continue
            a = p["full_name"].split(".")
            if len(a) == 3:
                sib.setdefault((a[1], a[2]), set()).add(p["power_type"])

    empty = expected = patched = added = 0
    not_player = no_table = 0
    twin_dropped = 0
    touched = []
    type_refused = []
    for _ps, lst in data.items():
        for p in lst:
            if any(p.get(b) for b in BUCKETS):
                continue
            crec = client.get(p["full_name"])
            if not crec:
                continue
            empty += 1
            rows, twins = wanted_rows(crec)
            if not rows:
                continue
            if p["full_name"].split(".")[0] in NOT_PLAYER:
                not_player += 1
                continue
            expected += 1
            bad = [r for r in rows if r["table"] not in known_tables]
            if bad:
                no_table += 1
                rows = [r for r in rows if r["table"] in known_tables]
            if not rows:
                continue
            twin_dropped += twins
            # a twin group existed => the client keeps a separate PvP variant,
            # so mark ours PvE-only exactly as the populated siblings do
            pv = 1 if twins else 0
            a = p["full_name"].split(".")
            ptype, how = power_type_from_game(
                crec, sib.get((a[1], a[2]), set()) if len(a) == 3 else set())
            if ptype is None or ptype == p.get("power_type"):
                if ptype is None:
                    type_refused.append((p["full_name"], how))
                ptype = None
            if not check_only:
                fx = p.setdefault("self_effects", [])
                for r in rows:
                    fx.append({
                        "effect": r["effect"],
                        "damage_type": r["damage_type"],
                        "scale": r["scale"],
                        "nmag": 1.0,
                        "modifier_table": r["table"],
                        "enhance_aspect": r["aspect"],
                        "ed_schedule": r["ed"],
                        "pv_mode": pv,
                        "duration": r["dur"],
                        MARK: True,
                    })
                if ptype is not None:
                    p["power_type_was"] = p.get("power_type")
                    p["power_type"] = ptype
            patched += 1
            added += len(rows)
            touched.append((p["full_name"], len(rows), pv, ptype, how))

    print(f"our records holding ZERO effect rows that the client also has : {empty}")
    print(f"  of those, carrying an allowlisted Defense/Resistance row : "
          f"{expected + not_player}")
    print(f"  STATED EXCLUSION, not a player power (pets/incarnate/temp/"
          f"Redirects) : {not_player}")
    print(f"  {'would patch' if check_only else 'patched'} : {patched}   "
          f"rows added: {added}")
    print(f"  STATED EXCLUSION, PvP twin templates dropped : {twin_dropped}")
    print(f"  STATED EXCLUSION, table the engine lacks     : {no_table}")
    print("  STATED EXCLUSION, Regeneration/Recovery: the game's help says Gamma "
          "Boost SCALES with health, so its flat 1.0/1.0 are two ends of one "
          "curve - pinned, never written")
    for fn, n, pv, ptype, how in touched:
        extra = (f", power_type -> {ptype} ({how})" if ptype is not None
                 else ", power_type unchanged")
        print(f"      {fn}  ({n} rows, pv_mode {pv}{extra})")
    for fn, why in type_refused:
        print(f"  STATED EXCLUSION, power_type left alone: {fn} - {why}")

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
                if "power_type_was" in p:
                    p["power_type"] = p.pop("power_type_was")
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
