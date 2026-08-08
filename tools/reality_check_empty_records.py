"""The EMPTY-RECORD class: our powers that hold no effect rows at all.

WHY THIS EXISTS
---------------
`reality_check_effect_coverage.py` compares FAMILIES and only sees Self
templates, so a record that carries nothing whatsoever shows up as a few
scattered family entries and reads as small. It is not small: **1,072 of our
records hold zero effect rows in every bucket while the client has a record for
them**, and 874 of those have ungated, non-zero templates (1,074 and 876 before
this pass fixed two). Gamma Boost prints
"Auto: Self +Regen, +Recovery, Special" and our record is blank.

⚠⚠ AND YET MOST OF IT IS NOT A DATA GAP. That is the finding, and it is why
this file classifies rather than alarms. The same four-outcome contract as the
coverage check, and the same two-way pin.

⚠ THE STUB IS WRONG IN TWO FIELDS, NOT ONE. Both records fixed by
`patch_empty_player_records.py` also carried `power_type: 0` (a click) where
the game says "Toggle:" and "Auto:" - and the engine only counts a power's self
effects when power_type is auto or toggle. A perfect effect back-fill measured
ZERO through the real route until the type was corrected too. Any future work
on this class must check both.

Report-only. Usage:  python tools/reality_check_empty_records.py [--all]
"""
import json
import os
import sys
import glob
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUCKETS = ("self_effects", "buff_effects", "debuff_effects",
           "control_effects", "heal_effects", "damage_effects")

NOT_PLAYER = {
    "Incarnate": "Alpha/Genesis/Hybrid boost DEFINITIONS and the incarnate "
                 "powers we model from data/incarnates.json",
    "Pets": "pet records - the pet model owns these (v26/v29/v38)",
    "Villain_Pets": "pet records - the pet model owns these",
    "Mastermind_Pets": "pet records - the pet model owns these",
    "Kheldian_Pets": "pet records - the pet model owns these",
    "Temporary_Powers": "temp powers and combo tokens, not build content",
    "Inherent": "inherent machinery; the scored inherents are DERIVED by v36 "
                "and must not also exist as data (Vigilance, Defiance)",
    "Redirects": "redirect stubs - empty BY DESIGN, the effects live on the "
                 "twin (the reconciliation lane's 230 proven redirect folds)",
}

# A record whose client templates are ALL of these is correctly empty: there is
# no stat to carry. Same vocabulary as the coverage check's dispositions.
PLUMBING = {
    "Grant_Power", "Revoke_Power", "Execute_Power", "Silent_Kill", "Null",
    "Create_Entity", "Set_Mode", "Meter", "Global_Chance_Mod", "Combat_Mod_Shift",
    "Recharge_Power", "Designer_Status", "Token_Set", "ThreatLevel", "Cancel_Mods",
    "OnlyAffectsSelf", "Clear_Damagers", "Rage", "RunningSpeed", "FlyingSpeed",
    "JumpingSpeed", "JumpHeight", "Fly", "SpeedRunning", "MovementControl",
    "MovementFriction", "Evade", "Range", "Teleport", "PerceptionRadius",
    "Translucency", "StealthRadius_PVE", "StealthRadius_PVP", "ElusivityBase",
    "Knockback", "Knockup", "Repel", "Special", "Untouchable", "Intangible",
}

# ⚠ REAL, and pinned by COUNT so they can neither go quiet nor block forever.
OPEN_GAPS = {
    "gamma-boost-scaling": (5,
        "Gamma Boost x5. The game's help: 'The LOWER your current health, the "
        "greater the regeneration bonus... the HIGHER your current health, the "
        "greater the recovery bonus'. The client's flat Regeneration 1.0 and "
        "Recovery 1.0 are two ends of ONE curve and can never both apply, so a "
        "flat back-fill would credit +100% of each at once. The export flattens "
        "the scaling - same class as Agile's scaling damage resistance, whose "
        "templates the export carries at scale 0.0. Needs the scaling model"),
    "ally-mez-protection": (8,
        "Clear Mind / Clarity x8 - the classic ally mez-protection buff, and "
        "our records are blank, so an Empathy Defender's signature support "
        "power does nothing in the model. DATA is straightforward; the CONSUMER "
        "is not - nothing scores mez protection granted to an ALLY, and landing "
        "the data alone would be inert"),
    "absorb-no-branch": (3,
        "Master Brawler, Insulating Circuit, Spirit Ward. Absorb is not "
        "modelled ANYWHERE - the engine has no branch, only an enhancement "
        "aspect of that name. A term is owed before the data means anything"),
    "endurance-discount": (6,
        "Conserve Power x5 + Conserve Energy. EnduranceDiscount has no "
        "_add_power_effect branch and no convention in our data to copy, and "
        "the axis is a v30 stated display-only exclusion. Needs a branch and a "
        "convention, which is its own small piece"),
    "self-accuracy": (2,
        "Combat Training: Offensive x2 grant +Accuracy. totals['accuracy'] IS "
        "scored but is fed only by set bonuses - no power path exists. One "
        "branch plus an ED convention, deliberately not invented here"),
    "field-medic-heal-strength": (1,
        "Field Medic's +Heal strength. The heal_strength axis exists (v29) but "
        "is fed only by set bonuses"),
    "mm-summon-root": (7,
        "The seven tier-1 Mastermind summons carry a SelfAndPets Immobilized "
        "at duration 0 - the summon rooting you while it places the pets. "
        "Plumbing in substance; pinned rather than dispositioned because "
        "'Immobilized' is a real family everywhere else and a blanket "
        "disposition would hide a genuine one"),
}


def load():
    ours = json.load(open(os.path.join(ROOT, "data", "powers.json"), encoding="utf-8"))
    client = {}
    for f in glob.glob(os.path.join(ROOT, "tools", "gamedata", "bin-crawler",
                                    "out_full", "**", "*.json"), recursive=True):
        if os.path.basename(f) == "index.json":
            continue
        try:
            c = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if c.get("full_name"):
            client[c["full_name"]] = c
    return ours, client


def gap_key(full_name, fams):
    leaf = full_name.split(".")[-1]
    if leaf == "Gamma_Boost":
        return "gamma-boost-scaling"
    if leaf in ("Clear_Mind", "Clarity"):
        return "ally-mez-protection"
    if "Absorb" in fams:
        return "absorb-no-branch"
    if "EnduranceDiscount" in fams:
        return "endurance-discount"
    if "Accuracy" in fams:
        return "self-accuracy"
    if leaf == "Field_Medic":
        return "field-medic-heal-strength"
    if full_name.split(".")[0] == "Mastermind_Summon":
        return "mm-summon-root"
    return None


def main():
    show_all = "--all" in sys.argv
    ours, client = load()
    total = populated = 0
    not_player = collections.Counter()
    plumbing_only = []
    gaps = collections.Counter()
    unclassified = []

    for _ps, lst in ours.items():
        for p in lst:
            if any(p.get(b) for b in BUCKETS):
                continue
            c = client.get(p["full_name"])
            if not c:
                continue
            total += 1
            ung = [t for g in (c.get("effects") or [])
                   if not (g.get("requires_expression") or "").strip()
                   for t in (g.get("templates") or []) if (t.get("scale") or 0)]
            if not ung:
                continue          # client says nothing either - correctly empty
            populated += 1
            root = p["full_name"].split(".")[0]
            if root in NOT_PLAYER:
                not_player[root] += 1
                continue
            fams = {a.replace("_Dmg", "") for t in ung for a in (t.get("attribs") or [])}
            if all(f in PLUMBING or f.endswith("_Elusivity") or f.startswith("Unknown(")
                   for f in fams):
                plumbing_only.append(p["full_name"])
                continue
            key = gap_key(p["full_name"], fams)
            if key:
                gaps[key] += 1
            else:
                unclassified.append((p["full_name"], sorted(fams)))

    print(f"our records with ZERO effect rows the client also has : {total}")
    print(f"  of those, the client gives ungated non-zero templates: {populated}")
    print(f"  NOT A PLAYER POWER ({sum(not_player.values())}):")
    for root, n in not_player.most_common():
        print(f"      {n:>4}  {root:<17} {NOT_PLAYER[root][:66]}")
    print(f"  PLUMBING-ONLY player records (correctly empty)       : "
          f"{len(plumbing_only)}")
    if show_all:
        for fn in sorted(plumbing_only):
            print(f"      {fn}")

    print("\nKNOWN OPEN GAPS - real, pinned so they cannot go quiet:")
    bad = []
    for key in sorted(OPEN_GAPS):
        want, note = OPEN_GAPS[key]
        got = gaps.get(key, 0)
        print(f"{'  ' if got == want else ' !'} {key:<28} {got:>3} records "
              f"(pinned {want})")
        print(f"       {note.splitlines()[0][:96]}")
        if got != want:
            bad.append((key, want, got))

    if unclassified:
        print(f"\nUNCLASSIFIED - {len(unclassified)} records:")
        for fn, fams in sorted(unclassified)[:40]:
            print(f"  {fn:<62} {','.join(fams)[:44]}")
        print(f"\nHARD FAIL: {len(unclassified)} empty records carry a stat family "
              f"with no classification. Fix, disposition, or pin each one.")
        sys.exit(1)
    if bad:
        print("\nHARD FAIL: an OPEN_GAPS pin no longer matches reality:")
        for key, want, got in bad:
            print(f"  {key}: pinned {want}, found {got} - "
                  f"{'GREW' if got > want else 'SHRANK or was fixed'}")
        sys.exit(1)

    print(f"\nEVERY EMPTY RECORD CLASSIFIED. {len(OPEN_GAPS)} open gaps pinned, "
          f"none moved.")


if __name__ == "__main__":
    main()
