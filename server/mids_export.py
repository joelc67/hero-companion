"""
mids_export.py - Produce a Mids Reborn .mbd file (plain JSON) from a build.

The .mbd format is indented JSON of Mids' CharacterBuildData (verified from the
MidsReborn source: BuildManager.SaveToFile + CharacterBuildData). Mids loads it
directly via File -> Open. Schema essentials:
  - Class: archetype class name (e.g. Class_Defender)
  - PowerSets: [primary, secondary, "", pool1..4, epic]  (8 entries, "" if empty)
  - PowerEntries[]: each {PowerName, Level, StatInclude, ProcInclude,
      VariableValue, InherentSlotsUsed, SubPowerEntries[], SlotEntries[]}
  - SlotEntries[]: {Level, IsInherent, Enhancement|null, FlippedEnhancement|null}
  - Enhancement: {Uid, Grade, IoLevel, RelativeLevel, Obtained}
Incarnate selections are included as extra PowerEntries (by full name) so the
exported build carries them too.
"""

# Standard CoH main-power pick levels (24 slots).
PICK_LEVELS = [1, 1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24,
               26, 28, 30, 32, 35, 38, 41, 44, 47, 49]

# Every real Mids build carries the universal inherents + the archetype inherent.
# Mids' loader (CharacterBuildData.SortGridPowers) walks a FIXED inherent grid and
# indexes into it positionally — if these entries are absent it throws
# "Index was outside the bounds of the array" and refuses to open the file. The
# exporter must therefore synthesize any the build doesn't already list.
_AT_INHERENT = {
    "Class_Blaster": "Inherent.Inherent.Defiance",
    "Class_Controller": "Inherent.Inherent.Containment",
    "Class_Defender": "Inherent.Inherent.Vigilance",
    "Class_Scrapper": "Inherent.Inherent.Critical_Hit",
    "Class_Tanker": "Inherent.Inherent.Gauntlet",
    "Class_Brute": "Inherent.Inherent.Bruisers_Fury",
    "Class_Stalker": "Inherent.Inherent.Assassination",
    "Class_Corruptor": "Inherent.Inherent.Scourge",
    "Class_Dominator": "Inherent.Inherent.Domination",
    "Class_Mastermind": "Inherent.Inherent.Supremacy",
    "Class_Sentinel": "Inherent.Inherent.Opportunity",
    "Class_Peacebringer": "Inherent.Inherent.Cosmic_Balance",
    "Class_Warshade": "Inherent.Inherent.Dark_Sustenance",
    "Class_Arachnos_Soldier": "Inherent.Inherent.Spider_Conditioning",
    "Class_Arachnos_Widow": "Inherent.Inherent.Widow_Conditioning",
}
# (full_name, level, StatInclude, give_empty_base_slot) — Mids' canonical order.
_UNIVERSAL_INHERENTS = [
    ("Inherent.Inherent.Brawl", 1, True, True),
    ("Inherent.Inherent.Sprint", 1, True, True),
    ("Inherent.Inherent.Rest", 2, False, True),
    ("Inherent.Fitness.Swift", 1, True, True),
    ("Inherent.Fitness.Hurdle", 1, True, True),
    ("Inherent.Fitness.Health", 1, True, True),
    ("Inherent.Fitness.Stamina", 1, True, True),
]


# booster offset -> Mids RelativeLevel enum name (see mids_import._REL_TO_BOOST)
_BOOST_TO_REL = {-3: "MinusThree", -2: "MinusTwo", -1: "MinusOne",
                 1: "PlusOne", 2: "PlusTwo", 3: "PlusThree",
                 4: "PlusFour", 5: "PlusFive"}


def _enh(uid, io_level=50, boost=0):
    """Mids' IoLevel is 0-based (49 = level 50); ours is the human level. An
    over-level single enhancement (io_level 53 = a +3 HO) travels as the boost
    convention, which is how Mids models it."""
    io = int(io_level or 50)
    if io > 50:
        boost = boost or (io - 50)
        io = 50
    rel = _BOOST_TO_REL.get(max(-3, min(5, int(boost or 0))), "Even")
    return {"Uid": uid, "Grade": "None", "IoLevel": max(0, io - 1),
            "RelativeLevel": rel, "Obtained": False}


def build_mbd(payload, db_name, db_version, level_lookup, app_version="3.7.7.7"):
    powers = payload.get("powers", []) or []

    # PowerSets: [primary, secondary, "", pool1..4, epic]
    # Derive pools/epic from the build itself when the caller doesn't supply them —
    # without these Mids shows the pool/epic dropdowns EMPTY and can't seat the picked
    # powers (the "Ice epic with no power choices" export bug, 2026-07-02).
    pools = list(payload.get("pools", []) or [])
    if not any(pools):
        pools = []
        for p in powers:
            ps = (p.get("full_name") or "").rsplit(".", 1)[0]
            if ps.startswith("Pool.") and ps not in pools:
                pools.append(ps)
    pools = (pools + ["", "", "", ""])[:4]
    epic = payload.get("epic") or next(
        ((p.get("full_name") or "").rsplit(".", 1)[0] for p in powers
         if (p.get("full_name") or "").startswith("Epic.")), "")
    # Index 2 is the inherent powerset slot. Mids' own saves put
    # "Inherent.Inherent" here (not an empty string); the inherent power
    # entries (Brawl, Sprint, Health...) reference it.
    power_sets = [payload.get("primary") or "", payload.get("secondary") or "",
                  "Inherent.Inherent"]
    power_sets += [p or "" for p in pools]
    power_sets += [epic]

    # Assign each power a DISTINCT pick-level slot that is >= its earliest
    # available level, walking the standard progression. This avoids piling
    # several powers onto level 1 (which Mids flags red as invalid placement).
    def minlvl(p):
        return max(1, int(level_lookup(p["full_name"]) or 1))

    # CRITICAL ordering: Mids loads PowerEntries *positionally* — entry[i] maps
    # to build slot[i]. The build slots are: the real power PICKS first
    # (indices 0..N, in level order), THEN the inherent/auto powers
    # (Brawl, Sprint, Health, Stamina...), THEN incarnates. If inherents are
    # interleaved with picks (sorted purely by level), the later picks — the
    # epic powers especially — get shoved past the pick-slot range and Mids
    # silently drops them on load. So split picks from inherents and emit picks
    # first.
    def _is_inherent(p):
        return (p.get("full_name") or "").startswith("Inherent.")

    real = [p for p in powers if p.get("full_name") and not _is_inherent(p)]
    inherents = [p for p in powers if p.get("full_name") and _is_inherent(p)]
    real.sort(key=lambda p: int(p.get("pick_level") or minlvl(p)))
    inherents.sort(key=lambda p: int(p.get("pick_level") or minlvl(p)))

    def _make_entry(p, plevel):
        slot_entries = []
        for s in (p.get("slots") or []):
            io = (s.get("io_level") if s else None)
            # resolved set/common IO -> by uid; an UNRESOLVED kept slot (e.g. a
            # Hamidon O we can't model) carries its original uid in piece_name —
            # write that back so it round-trips instead of being dropped.
            uid = (s.get("piece_uid") or s.get("piece_name")) if s else None
            enh = _enh(uid, io, (s.get("boost") if s else 0) or 0) if uid else None
            slot_entries.append({
                "Level": plevel, "IsInherent": False,
                "Enhancement": enh, "FlippedEnhancement": None,
            })
        return {
            "PowerName": p["full_name"],
            "Level": plevel,
            "StatInclude": True,
            "ProcInclude": False,
            "VariableValue": 0,
            "InherentSlotsUsed": 0,
            "SubPowerEntries": [],
            "SlotEntries": slot_entries,
        }

    power_entries = []
    slot_i = 0
    # Faithful round-trip: if powers carry a real pick_level (imported builds),
    # place by it. Otherwise (generated/solved builds with no levels) walk the
    # standard progression so powers don't pile onto level 1.
    for p in real:
        if p.get("pick_level"):
            plevel = max(1, int(p["pick_level"]))
        else:
            ml = minlvl(p)
            while slot_i < len(PICK_LEVELS) and PICK_LEVELS[slot_i] < ml:
                slot_i += 1
            plevel = PICK_LEVELS[slot_i] if slot_i < len(PICK_LEVELS) else min(49, ml)
            slot_i += 1
        power_entries.append(_make_entry(p, plevel))

    num_picks = len(power_entries)

    # Inherent/auto powers come after all picks (their own slot region). Mids needs
    # the FULL canonical inherent set present and in order, or SortGridPowers indexes
    # out of bounds on open. Emit them in Mids' order: reuse any the build already
    # carries (so Health/Stamina keep their slotted sustain procs) and synthesize the
    # rest (Brawl/Sprint/Rest/Swift/Hurdle + the AT inherent like Containment).
    have_inh = {p.get("full_name"): p for p in inherents}
    at_inh = _AT_INHERENT.get(payload.get("archetype") or "")
    canonical = ([(at_inh, 1, False, False)] if at_inh else []) + _UNIVERSAL_INHERENTS
    for full, level, stat, base in canonical:
        if not full:
            continue
        if full in have_inh:
            p = have_inh.pop(full)
            power_entries.append(_make_entry(p, max(1, int(p.get("pick_level") or level))))
        else:
            slots = ([{"Level": level, "IsInherent": False,
                       "Enhancement": None, "FlippedEnhancement": None}] if base else [])
            power_entries.append({
                "PowerName": full, "Level": level, "StatInclude": stat,
                "ProcInclude": False, "VariableValue": 0, "InherentSlotsUsed": 0,
                "SubPowerEntries": [], "SlotEntries": slots})
    # Any leftover inherents the build listed that aren't in the canonical set.
    for full, p in have_inh.items():
        power_entries.append(_make_entry(p, max(1, int(p.get("pick_level") or minlvl(p)))))

    # An empty placeholder entry separates the inherent block from incarnates in Mids'
    # own saves — mirror it (structure verified against a Mids 3.8.1 native save).
    power_entries.append({
        "PowerName": "", "Level": -1, "StatInclude": False, "ProcInclude": False,
        "VariableValue": 0, "InherentSlotsUsed": 0,
        "SubPowerEntries": [], "SlotEntries": []})

    # Incarnates as extra power entries (no slots). Level is ZERO-INDEXED in .mbd files
    # (a level-50 character is "49") — writing 50 anywhere indexes past Mids' 50-element
    # level arrays and crashes SortGridPowers on load.
    for slot, full in (payload.get("incarnates_full") or {}).items():
        if full:
            power_entries.append({
                "PowerName": full, "Level": 49, "StatInclude": True,
                "ProcInclude": False, "VariableValue": 0, "InherentSlotsUsed": 0,
                "SubPowerEntries": [], "SlotEntries": [],
            })

    # Terminal marker entry present in native Mids saves.
    power_entries.append({
        "PowerName": "Inherent.Inherent.Special_Set_Bonuses", "Level": 1,
        "StatInclude": True, "ProcInclude": False, "VariableValue": 0,
        "InherentSlotsUsed": 0, "SubPowerEntries": [], "SlotEntries": []})

    return {
        "BuiltWith": {
            "App": "Mids Reborn",
            "Version": app_version,
            "Database": db_name,
            "DatabaseVersion": db_version,
        },
        # ZERO-INDEXED: "49" == level 50. "50" crashes Mids (array bounds) on load.
        "Level": "49",
        "Class": payload.get("archetype") or "",
        "Origin": payload.get("origin") or "Magic",
        "Alignment": payload.get("alignment") or "Hero",
        "Name": payload.get("name") or "CoH Planner Build",
        "Comment": "Created with the local CoH Build Planner.",
        "PowerSets": power_sets,
        # Native-save pattern: index of the LAST of the 4 base inherents that follow the
        # picks (…, Vigilance, Brawl, Sprint, Rest ⇒ last_pick_index + 4). Writing the
        # raw pick count under-shoots and breaks Mids' grid split.
        "LastPower": max(num_picks - 1, 0) + 4,
        "PowerEntries": power_entries,
    }
