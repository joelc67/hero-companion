"""EVERY effect family, not five. The widened completeness check.

WHY THIS EXISTS
---------------
`reality_check_effect_structure.py` says in its own docstring that its scope is
"deliberately the sustain/armor family ... NOT every damage/control template -
that would drown the signal". That narrowing is why every gap of this class has
been found REACTIVELY from a field report instead of by an instrument: accuracy
(v28), heal-strength (v29), +MaxEnd (v35), the self +Damage buff across 275
powers, Granite Armor's -30%, Bio Armor's -25%, power-granted slow resistance
across 126 powers, and now DEFENCE DEBUFF RESISTANCE across 178. Nobody failed
to look. The instrument was aimed narrowly and the aim was never revisited.

This one looks at EVERY self-targeted client template and refuses to drown by
CLASSIFYING families rather than by narrowing scope. Every family lands in
exactly one of four places, and the residue can only shrink:

  SOURCE_EXCLUSIONS  the record is not a player power at all (counted, printed)
  DISPOSITIONS       we correctly carry no data for it, with the reason
  OPEN_GAPS          a REAL defect, named, with its power count PINNED
  residue            undispositioned -> HARD FAIL

⚠ OPEN_GAPS IS THE POINT OF THIS FILE. A real gap must not be dispositioned into
silence, and it must not hard-fail forever either or the check gets switched off.
Each entry pins the number of powers affected, so the check fails if a gap GROWS
(a new defect wearing an old name) and equally if it SHRINKS (someone fixed it
and left the entry behind). Same contract as the prereq baseline.

SIX RULES, EVERY ONE PAID FOR
-----------------------------
1. Compare modifier tables CASE-INSENSITIVELY. Ours is `Ranged_DeBuff_ToHit`,
   the client's is `Ranged_Debuff_ToHit`. One capital B invented 121 phantom
   missing -ToHit debuffs across the whole of Dark Blast.
2. Ask whether we carry the ATTRIB under ANY table before calling it absent. A
   table mismatch is a naming artefact; a missing attrib is a defect.
3. The ASPECT is part of the identity. Self RechargeTime templates are slow
   RESISTANCE at aspect=Resistance and a recharge BUFF at aspect=Strength -
   opposites. Keying on the attrib alone would have corrupted 78 records, and
   the same trap sits under Base_Defense (DDR vs the Alpha boost definitions).
4. A zero-scale template carries no magnitude. Every Blaster blast has one
   (Defiance is derived from cast time, not stored), and counting them made 13
   champion contexts look exposed and stalled a re-cert over nothing.
5. TRANSLATE THE VOCABULARY, not just the case. Ours says `AoE` and `Negative`
   where the client says `Area` and `Negative_Energy` - Arsenal Control's
   Cloaking Device carries all eleven defence vectors and still reported two
   missing. Rule 1's lesson in a second coat.
6. NOT EVERY RECORD IS A PLAYER POWER. The Alpha/Genesis boost tables are
   ENHANCEMENT definitions whose attribs are aspects (Accuracy, Held, Smashing),
   not effects a power applies; pet records carry the pet's own model. Both are
   excluded BY SOURCE with a printed count, never silently.

Report-only. NEVER writes powers.json - the additive patchers do that.
Usage:  python tools/reality_check_effect_coverage.py [--all]
"""
import json
import os
import sys
import glob
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUCKETS = ("self_effects", "buff_effects", "debuff_effects",
           "control_effects", "heal_effects", "damage_effects")

# Rule 5. Client vocabulary -> ours, lower-cased.
SYNONYMS = {"area": "aoe", "negative_energy": "negative"}

# Rule 6. A record that is not a player power, with the reason. Counted and
# printed every run so this can never become a quiet way to shrink the scope.
SOURCE_EXCLUSIONS = (
    (lambda fn: fn.startswith("Incarnate.") and "_Silent." in fn,
     "Alpha/Genesis/Hybrid BOOST DEFINITIONS - enhancement records, not powers. "
     "Their attribs are enhancement ASPECTS (Accuracy, Held, Smashing at "
     "aspect=Strength); our incarnate model reads data/incarnates.json"),
    (lambda fn: fn.split(".")[0] in ("Pets", "Villain_Pets", "Mastermind_Pets",
                                     "Kheldian_Pets"),
     "PET records - a pet's own self rows belong to the pet model (v26/v29/v38), "
     "not the player's totals. Henchman innate defences are a STATED "
     "understatement (v29), not a finding of this check"),
)

# Families we correctly carry no data for, each traceable to a ruling already
# made. This file is where those rulings become machine-readable instead of
# living only in prose. Keyed by family, or by (family, aspect) where the aspect
# is what decides (rule 3).
DISPOSITIONS = {
    "Grant_Power":       "plumbing - grants another power, not a stat (reconciliation residue)",
    "Revoke_Power":      "plumbing - revokes a power (reconciliation residue)",
    "Execute_Power":     "plumbing - fires another power",
    "Recharge_Power":    "plumbing - resets ANOTHER power's recharge (summon timers, "
                         "Cinders-class). Not a stat on this build",
    "Silent_Kill":       "mission/NPC plumbing",
    "Null":              "no-op template",
    "Create_Entity":     "plumbing - spawns the pseudo-pet whose output our data already "
                         "FOLDS INTO the summoner (the reconciliation lane's 761 "
                         "pseudo-pet folds); counting it here would double the pet",
    "RunningSpeed":      "v30 stated display-only exclusion (movement)",
    "FlyingSpeed":       "v30 stated display-only exclusion (movement)",
    "JumpingSpeed":      "v30 stated display-only exclusion (movement)",
    "JumpHeight":        "v30 stated display-only exclusion (movement)",
    "Fly":               "v30 stated display-only exclusion (movement)",
    "SpeedRunning":      "v30 stated display-only exclusion (movement)",
    "MovementControl":   "v30 stated display-only exclusion (movement physics - air "
                         "control on Dwarf Step and the travel powers)",
    "MovementFriction":  "v30 stated display-only exclusion (movement physics)",
    "Evade":             "v30 stated display-only exclusion (movement - leap evasion)",
    "Range":             "v30 stated display-only exclusion (range)",
    "PerceptionRadius":  "no scoring path; perception is not modelled",
    "Translucency":      "stealth: how visible you are. Not modelled, same class as "
                         "PerceptionRadius. The DEFENCE a stealth power grants IS "
                         "modelled - it arrives as ordinary Defense rows",
    "StealthRadius_PVE": "stealth radius - see Translucency",
    "StealthRadius_PVP": "stealth radius, PvP column - see Translucency",
    "Global_Chance_Mod": "v36 DORMANT - Opportunity semantics ungrounded in the export",
    "Knockback":         "v30 stated exclusion - KB STRENGTH display-only (protection IS scored)",
    "Knockup":           "v30 stated exclusion - KB strength display-only",
    "Repel":             "v30 stated exclusion - KB strength display-only",
    "Set_Mode":          "OPEN - the mode/meter capability (Power Boost class), queued",
    "Meter":             "OPEN - the mode/meter capability, same queue as Set_Mode "
                         "(Hide's meter, Placate). Fury/Rage/Domination/Defiance are "
                         "one piece of work",
    "Rage":              "OPEN - the meter class (Rage_Dampen, Domination_Dampen, "
                         "Battle_Euphoria_Dampen are the meter's own decay), same queue",
    "Designer_Status":   "internal state flag (combo levels, Titan Weapons momentum) - "
                         "carries no magnitude",
    "Cancel_Mods":       "plumbing - clears the Dual Blades combo mods",
    "Clear_Damagers":    "plumbing - clears damage-over-time on the caster",
    "Token_Set":         "plumbing - sets an internal token",
    "ThreatLevel":       "threat/aggro is not modelled (taunt MAGNITUDE has never been "
                         "in the score; the Taunt powers are picked, not priced)",
    "OnlyAffectsSelf":   "plumbing - Personal Force Field's untouchability flag",
    "Special":           "the client's CATCH-ALL self-cost attribute: Oppressive Gloom's "
                         "HP tick and Absorb Pain's caster penalty. The penalty IS "
                         "carried - as the Self Regeneration -1.0 row v37 taught the "
                         "scorer to stop reading as an ally buff",
    "Elusivity":         "PvP-only mechanic - inert in PvE exactly like a pv_mode 2 row",
    "ElusivityBase":     "PvP-only mechanic - see Elusivity",
    "Unknown":           "the client names no attribute for this id; nothing to carry",
}
# (family, aspect) entries - the aspect is what decides.
DISPOSITIONS_BY_ASPECT = {
    ("Teleport", "Current"):    "self-teleport (Shield Charge, Lightning Rod, Jaunt) - "
                                "movement, the v30 exclusion",
    ("Teleport", "Resistance"): "plumbing - Personal Force Field cannot be teleported",
    ("Endurance", "Strength"):  "buffs the endurance DRAIN your attacks do (Electrical "
                                "Blast's Aim). Enemy endurance is not modelled anywhere - "
                                "sapping has never been a scored axis",
    ("Heal", "Resistance"):     "heal-debuff resistance on an inherent + the pet "
                                "un-healable flag; no incoming heal-debuff exists in any "
                                "scenario, so there is nothing to resist",
}
# Damage-type families that are only ever the INHERENT's own derived rows.
_VIGILANCE_NOTE = ("v36 derives Vigilance from the inherent's own scales; anything "
                   "the inherent term DERIVES must stay out of the data or it is "
                   "counted twice (the same rule that removed Defiance's rows)")

# ⚠ REAL DEFECTS. Named, counted, and pinned - not dispositioned into silence.
# The count is the number of POWERS affected today. The check fails if a number
# moves in EITHER direction: up means a new defect, down means someone fixed it
# and left the entry behind.
OPEN_GAPS = {
    ("EnduranceDiscount", "Strength"): (20,
        "Conserve Power and the Bio/Energy Aura discounts. Our records for these "
        "powers are EMPTY - Epic.Body_Mastery.Conserve_Power carries no effects at "
        "all. DATA is owed; SCORING is not, because end-discount is a v30 stated "
        "display-only exclusion"),
    ("ToHit", "Resistance"): (13,
        "ToHit-DEBUFF resistance (Obscure Sustenance, Fallout Shelter, Combat "
        "Training: Offensive). Real, and the same shape as the DDR gap v41 just "
        "closed - EXCEPT that no scenario carries incoming ToHit-debuff pressure, "
        "so there is nothing yet for it to resist. Blocked on a scenario input, "
        "the same blocker as mez_in"),
    ("Endurance", "Resistance"): (8,
        "endurance-DRAIN resistance (Inexhaustible, Murky Cloud, Gamma Boost). "
        "Blocked on a scenario input - no incoming end drain exists"),
    ("Regeneration", "Resistance"): (7,
        "regeneration-debuff resistance. Blocked on a scenario input"),
    ("Recovery", "Resistance"): (3,
        "recovery-debuff resistance. Blocked on a scenario input"),
    ("Regeneration", "Current"): (6,
        "WHOLE RECORDS ARE EMPTY. Radiation Armor's Gamma Boost prints 'Auto: "
        "Self +Regen, +Recovery, Special' and our record carries NOTHING. This is "
        "the empty-record class (877 of our powers hold zero effect rows while the "
        "client populates them) surfacing through this check"),
    ("Recovery", "Current"): (5, "Gamma Boost - see Regeneration/Current"),
    # ✅ CLOSED by tools/patch_power_absorb.py + the v42 term: Absorb was
    # "not modelled ANYWHERE" when this entry was written. Particle
    # Shielding and Master Brawler now carry the shield and the scorer
    # consumes it. The pin is what said so.
    ("Accuracy", "Strength"): (3,
        "Terra Firma and Combat Training: Offensive grant +Accuracy beside their "
        "+ToHit and we carry only the ToHit half. Both axes ARE modelled, so this "
        "is data-only - the v28 accuracy family again, on powers this time"),
    ("Heal", "Strength"): (1,
        "Field Medic's +Heal strength. The heal_strength axis has existed since "
        "v29, so this is data-only"),
    # ✅ CLOSED by tools/patch_empty_player_records.py: the ten damage-type
    # entries that lived here were Shield Defense's Active Defense and
    # Ninjitsu's Bo Ryaku, both of which held NO effect rows at all. The
    # two-way pin is what surfaced it - they went to zero and this check
    # failed on the stale entries rather than quietly passing.
}
NPC_TABLES = {"melee_archvillain_res", "ranged_archvillain_res"}
_DMG_TYPES = {"Smashing", "Lethal", "Fire", "Cold", "Energy", "Negative_Energy",
              "Psionic", "Toxic", "Melee", "Ranged", "Area"}


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


def disposition_for(fam, aspect, full_name):
    if (fam, aspect) in DISPOSITIONS_BY_ASPECT:
        return DISPOSITIONS_BY_ASPECT[(fam, aspect)]
    if fam in DISPOSITIONS:
        return DISPOSITIONS[fam]
    if fam.endswith("_Elusivity"):
        return DISPOSITIONS["Elusivity"]
    if fam.startswith("Unknown("):
        return DISPOSITIONS["Unknown"]
    # the inherent terms DERIVE their own numbers; the data must not repeat them
    if fam in _DMG_TYPES and full_name.startswith("Inherent.Inherent."):
        return _VIGILANCE_NOTE
    return None


def main():
    show_all = "--all" in sys.argv
    ours, client = load()
    residue = collections.defaultdict(set)     # (attrib, aspect) -> powers
    gaps = collections.defaultdict(set)
    disposed = collections.Counter()
    src_excluded = collections.Counter()
    covered = 0

    for _ps, lst in ours.items():
        for p in lst:
            c = client.get(p["full_name"])
            if not c:
                continue
            covered += 1
            # rule 1 + 2 + 5: our vocabulary, case-folded and translated
            mine = set()
            for b in BUCKETS:
                for e in (p.get(b) or []):
                    mine |= {str(e.get("modifier_table", "")).lower(),
                             str(e.get("effect", "")).lower(),
                             str(e.get("damage_type", "")).lower()}
            for g in (c.get("effects") or []):
                if (g.get("requires_expression") or "").strip():
                    continue          # gated = a different, conditional claim
                for t in (g.get("templates") or []):
                    if t.get("target") != "Self":
                        continue
                    if (t.get("table") or "").lower() in NPC_TABLES:
                        continue
                    if not (t.get("scale") or 0):
                        continue      # rule 4: zero scale carries no magnitude
                    tbl = (t.get("table") or "").lower()
                    for a in (t.get("attribs") or []):
                        fam = a.replace("_Dmg", "")
                        low = fam.lower()
                        if (a.lower() in mine or low in mine or tbl in mine
                                or SYNONYMS.get(low, low) in mine):
                            continue
                        why = disposition_for(fam, t.get("aspect"), p["full_name"])
                        if why:
                            disposed[why] += 1
                            continue
                        # rule 6, applied AFTER dispositions so the printed
                        # exclusion count only covers what would otherwise show
                        skipped = None
                        for pred, reason in SOURCE_EXCLUSIONS:
                            if pred(p["full_name"]):
                                skipped = reason
                                break
                        if skipped:
                            src_excluded[skipped] += 1
                            continue
                        key = (fam, t.get("aspect"))
                        (gaps if key in OPEN_GAPS else residue)[key].add(p["full_name"])

    print(f"powers compared against the client : {covered}")
    print(f"dispositioned families             : "
          f"{len(DISPOSITIONS) + len(DISPOSITIONS_BY_ASPECT)} "
          f"({sum(disposed.values())} template instances)")
    for why, n in sorted(src_excluded.items(), key=lambda x: -x[1]):
        print(f"SOURCE EXCLUSION ({n:>4} templates) : {why.splitlines()[0][:74]}")
    print(f"UNDISPOSITIONED families           : {len(residue)}\n")

    print("KNOWN OPEN GAPS - real defects, pinned so they cannot go quiet:")
    bad_pins = []
    for key in sorted(OPEN_GAPS):
        want, note = OPEN_GAPS[key]
        got = len(gaps.get(key) or ())
        flag = "  " if got == want else " !"
        print(f"{flag} {key[0]:<20} aspect={str(key[1]):<11} {got:>3} powers "
              f"(pinned {want})")
        print(f"       {note.splitlines()[0][:96]}")
        if got != want:
            bad_pins.append((key, want, got))

    if residue:
        rows = sorted(residue.items(), key=lambda x: -len(x[1]))
        print(f"\nUNCLASSIFIED - {len(rows)} families:")
        for (fam, aspect), fns in (rows if show_all else rows[:25]):
            print(f"  {fam:<24} aspect={str(aspect):<11} {len(fns):>5} powers")
            print(f"       e.g. {sorted(fns)[0][:70]}")
        if not show_all and len(rows) > 25:
            print(f"  ... {len(rows) - 25} more (--all to list)")
        print(f"\nHARD FAIL: {len(rows)} families carry no classification. Each must be "
              f"fixed by an additive patcher, dispositioned with its reason, or "
              f"pinned in OPEN_GAPS.")
        sys.exit(1)

    if bad_pins:
        print("\nHARD FAIL: an OPEN_GAPS pin no longer matches reality:")
        for key, want, got in bad_pins:
            what = ("GREW - a new defect wearing an old name" if got > want else
                    "SHRANK - fixed? then remove or correct the entry" if got else
                    "is EMPTY - stale entry, remove it")
            print(f"  {key[0]}/{key[1]}: pinned {want}, found {got} - {what}")
        sys.exit(1)

    print("\nEVERY FAMILY CLASSIFIED. "
          f"{len(OPEN_GAPS)} open gaps pinned, none moved.")


if __name__ == "__main__":
    main()
