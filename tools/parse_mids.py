"""
parse_mids.py  -  Convert Mids Reborn .mhd binary databases into structured JSON.

The .mhd files are .NET BinaryWriter output:
  - strings  : 7-bit-encoded length prefix (LEB128) + UTF-8 bytes
  - int32    : little-endian signed 4 bytes
  - int64    : little-endian signed 8 bytes
  - single   : little-endian IEEE-754 float, 4 bytes
  - bool     : 1 byte (0/1)

Array idiom throughout the C# source:   x = new T[reader.ReadInt32() + 1]
so every length read is N and the loop reads (N + 1) elements.

Field orders below are transcribed 1:1 from the MidsReborn C# reader
constructors (DatabaseAPI.cs, Power.cs, Effect.cs, Archetype.cs, Powerset.cs,
Enhancement.cs, EnhancementSet.cs, Requirement.cs). Do not reorder.
"""

import collections
import json
import os
import struct
import sys

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)                       # coh-builder/
DEFAULT_DB = os.path.join(
    os.path.dirname(PROJECT), "MidsReborn", "MidsReborn", "Databases", "Homecoming"
)
DB_DIR = os.environ.get("MIDS_DB_DIR", DEFAULT_DB)
OUT_DIR = os.path.join(PROJECT, "data")

# ----------------------------------------------------------------------------
# Enum tables (transcribed from Enums.cs) - index == enum value
# ----------------------------------------------------------------------------
EENHANCE = ["None", "Accuracy", "Damage", "Defense", "EnduranceDiscount",
            "Endurance", "SpeedFlying", "Heal", "HitPoints", "Interrupt",
            "JumpHeight", "SpeedJumping", "Mez", "Range", "RechargeTime",
            "X_RechargeTime", "Recovery", "Regeneration", "Resistance",
            "SpeedRunning", "ToHit", "Slow", "Absorb"]

EFFECT_TYPE = [
    "None", "Accuracy", "ViewAttrib", "Damage", "DamageBuff", "Defense",
    "DropToggles", "Endurance", "EnduranceDiscount", "Enhancement", "Fly",
    "SpeedFlying", "GrantPower", "Heal", "HitPoints", "InterruptTime",
    "JumpHeight", "SpeedJumping", "Meter", "Mez", "MezResist",
    "MovementControl", "MovementFriction", "PerceptionRadius", "Range",
    "RechargeTime", "Recovery", "Regeneration", "ResEffect", "Resistance",
    "RevokePower", "Reward", "SpeedRunning", "SetCostume", "SetMode", "Slow",
    "StealthRadius", "StealthRadiusPlayer", "EntCreate", "ThreatLevel",
    "ToHit", "Translucency", "XPDebtProtection", "SilentKill", "Elusivity",
    "GlobalChanceMod", "LevelShift", "UnsetMode", "Rage", "MaxRunSpeed",
    "MaxJumpSpeed", "MaxFlySpeed", "DesignerStatus", "PowerRedirect",
    "TokenAdd", "ExperienceGain", "InfluenceGain", "PrestigeGain",
    "AddBehavior", "RechargePower", "RewardSourceTeam", "VisionPhase",
    "CombatPhase", "ClearFog", "SetSZEValue", "ExclusiveVisionPhase",
    "Absorb", "XAfraid", "XAvoid", "BeastRun", "ClearDamagers",
    # Enums.cs continues to 85 — the list was truncated here for years, silently dropping
    # every effect of these types (incl. ExecutePower=85, the Redirects.* delivery for
    # Sonic Attack / Storm Blast / Marine Affinity hidden debuffs — found 2026-07-02).
    "EntCreate_x", "Glide", "Hoverboard", "Jumppack", "MagicCarpet", "NinjaRun",
    "Null", "NullBool", "Stealth", "SteamJump", "Walk", "XPDebt", "ForceMove",
    "ModifyAttrib", "ExecutePower"]

EDAMAGE = ["None", "Smashing", "Lethal", "Fire", "Cold", "Energy", "Negative",
           "Toxic", "Psionic", "Special", "Melee", "Ranged", "AoE",
           "Unique1", "Unique2", "Unique3"]

EASPECT = ["Res", "Max", "Abs", "Str", "Cur"]

# eSchedule: None=-1, A=0, B=1, C=2, D=3, Multiple=4
MATH_LEVEL_BASE = 49

# Maps a stat EffectType -> the eEnhance aspect that boosts it (for enhancement
# math) and lets us pick the ED schedule. None means "not enhanceable here".
EFFECT_TO_ENHANCE = {
    "Defense": "Defense", "Resistance": "Resistance", "RechargeTime": "RechargeTime",
    "Recovery": "Recovery", "Regeneration": "Regeneration", "Heal": "Heal",
    "HitPoints": "HitPoints", "Endurance": "Endurance", "ToHit": "ToHit",
    "Range": "Range",
}


def ed_schedule_for_aspect(aspect):
    """Mirror Enhancement.GetSchedule (eSchedule index)."""
    return {"Defense": 1, "Resistance": 1, "ToHit": 1, "Range": 1,
            "Interrupt": 2, "Mez": 0}.get(aspect, 0)   # default A=0


def load_maths(path):
    """Parse Maths.mhd -> MultIO[level]=[A,B,C,D], MultED[sched]=[t1,t2,t3], and
    MultGRADE['TO'|'DO'|'SO'|'HO']=[A,B,C,D] (Enhancement Grade Effectiveness — the
    HO row 0.333/0.20/0.40/0.60 prices Hamidon/Titan/Hydra Origin enhancements)."""
    mult_io, mult_ed, mult_grade = {}, {}, {}
    section = None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            cols = raw.rstrip("\r\n").split("\t")
            head = cols[0].strip()
            if head in ("EDRT", "EGE", "LBIOE"):
                section = head
                continue
            if section == "EDRT" and head.startswith("EDThresh_"):
                idx = int(head.split("_")[1]) - 1
                for s in range(4):
                    mult_ed.setdefault(s, [0, 0, 0])[idx] = float(cols[s + 1])
            elif section == "EGE" and head.rstrip(":") in ("TO", "DO", "SO", "HO"):
                mult_grade[head.rstrip(":")] = [float(cols[i + 1]) for i in range(4)]
            elif section == "LBIOE":
                try:
                    lvl = int(head)
                except ValueError:
                    continue
                mult_io[lvl] = [float(cols[i + 1]) for i in range(4)]
    return mult_io, mult_ed, mult_grade


def load_attribmod(path):
    """Return {table_id: row} where row is Table[49] (values per class column)."""
    data = json.load(open(path, "r", encoding="utf-8"))
    out = {}
    for m in data["Modifier"]:
        tbl = m.get("Table") or []
        if len(tbl) > MATH_LEVEL_BASE:
            out[m["ID"]] = tbl[MATH_LEVEL_BASE]
    return out

# Effect types that contribute to the build stat totals the app displays.
STAT_EFFECT_TYPES = {"Defense", "Resistance", "RechargeTime", "Recovery",
                     "Regeneration", "Heal", "HitPoints", "Endurance",
                     "ToHit", "Accuracy", "Enhancement", "MezResist",
                     "Absorb", "Damage", "DamageBuff", "Range", "Slow"}

# eEntity flag for foe-affecting powers (attacks / debuffs).
ENTITY_FOE = 2048
# eEntity friendly bits (Player=2, Teammate=8, Friend=512): a PBAoE ally buff (Accelerate
# Metabolism, Sonic Dispersion, Radiant Aura) is encoded to_who=SELF with these area flags —
# the old to_who==1 gate dropped EVERY such buff (wiki-audit find, 2026-07-02).
ENTITY_FRIENDLY = 2 | 8 | 512
# Effect types we summarize as enemy DEBUFFS / ally-or-self BUFFS so the
# damage/buff/debuff roles have a measured number. (Resistance/Defense to a foe
# = a debuff; to an ally = a buff — direction is by target, not sign.)
DEBUFF_EFFECT_TYPES = {"Resistance", "Defense", "ToHit", "DamageBuff",
                       "Regeneration", "Recovery", "RechargeTime", "Slow",
                       "Endurance"}
# Movement-slow flavors → summarized under "Slow" (the wiki's "-SPD"; Lingering Radiation,
# Snow Storm etc. carry these instead of the literal Slow effect type).
SLOW_EFFECT_TYPES = {"SpeedRunning", "SpeedJumping", "SpeedFlying", "MaxRunSpeed",
                     "MaxJumpSpeed", "MaxFlySpeed"}
BUFF_EFFECT_TYPES = {"DamageBuff", "ToHit", "Defense", "Resistance", "Recovery",
                     "Regeneration", "Heal", "HitPoints", "RechargeTime"}

# eMez enum (Mids Enums.cs) — the CONTROL a power lands on a foe. Index == mez value.
# Surfacing these (magnitude × duration × chance × area) is how the optimizer finally
# SEES a controller's/dominator's actual output instead of being blind to it.
EMEZ = ["None", "Confused", "Held", "Immobilized", "Knockback", "Knockup",
        "OnlyAffectsSelf", "Placate", "Repel", "Sleep", "Stunned", "Taunt",
        "Terrorized", "Untouchable", "Teleport", "ToggleDrop", "Afraid", "Avoid",
        "CombatPhase", "Intangible"]
# The "hard" mez a control build is judged on (magnitude must beat protection, holds the
# foe). WIKI "Control" page (verified 2026-07-01): Holds/Disorients = hard; "less reliable
# effects such as Knockback or Sleep are called 'soft'" — Sleep breaks on any damage, so it
# is SOFT despite its magnitude. Knockback/Knockup/Repel are positional soft control;
# Taunt/Placate are aggro, not control.
HARD_CONTROL = {"Held", "Immobilized", "Stunned", "Confused", "Terrorized", "Intangible"}
SOFT_CONTROL = {"Sleep", "Knockback", "Knockup", "Repel", "Afraid", "Avoid"}
# Ally-REVIVE powers (a clutch team utility, no heal magnitude). Name-based (rez has no distinct
# effect type in the data): Empathy/Medicine/Poison/Dark/Storm/Sonic + incarnate Destiny Rebirth.
_RESURRECT_POWERS = {"Resurrect", "Resuscitate", "Elixir_of_Life", "Soul_Transfer",
                     "Howling_Twilight", "Mutation"}


# ----------------------------------------------------------------------------
# .NET BinaryReader
# ----------------------------------------------------------------------------
class Reader:
    def __init__(self, data: bytes):
        self.d = data
        self.p = 0

    def eof(self):
        return self.p >= len(self.d)

    def _7bit_len(self):
        # .NET 7-bit encoded int (LEB128, max 5 bytes)
        count = 0
        shift = 0
        while True:
            b = self.d[self.p]
            self.p += 1
            count |= (b & 0x7F) << shift
            if (b & 0x80) == 0:
                break
            shift += 7
        return count

    def string(self):
        n = self._7bit_len()
        s = self.d[self.p:self.p + n].decode("utf-8", errors="replace")
        self.p += n
        return s

    def int32(self):
        v = struct.unpack_from("<i", self.d, self.p)[0]
        self.p += 4
        return v

    def int64(self):
        v = struct.unpack_from("<q", self.d, self.p)[0]
        self.p += 8
        return v

    def single(self):
        v = struct.unpack_from("<f", self.d, self.p)[0]
        self.p += 4
        return v

    def boolean(self):
        v = self.d[self.p]
        self.p += 1
        return v != 0


# ----------------------------------------------------------------------------
# Class readers (mirror the C# BinaryReader constructors exactly)
# ----------------------------------------------------------------------------
def read_requirement(r: Reader):
    n = r.int32() + 1
    class_name = [r.string() for _ in range(n)]
    n = r.int32() + 1
    class_name_not = [r.string() for _ in range(n)]
    n = r.int32() + 1
    power_id = [(r.string(), r.string()) for _ in range(n)]
    n = r.int32() + 1
    power_id_not = [(r.string(), r.string()) for _ in range(n)]
    return {
        "class_name": [c for c in class_name if c],
        "class_name_not": [c for c in class_name_not if c],
        "power_id": power_id,
        "power_id_not": power_id_not,
    }


def read_effect(r: Reader):
    """Consume one Effect. We keep only the fields useful downstream
    (set-bonus / power display); the rest are read purely to advance."""
    e = {}
    e["power_full_name"] = r.string()
    r.int32()                                   # UniqueID
    e["effect_class"] = r.int32()
    e["effect_type"] = r.int32()
    e["damage_type"] = r.int32()
    e["mez_type"] = r.int32()
    e["et_modifies"] = r.int32()
    e["summon"] = r.string()                    # Summon (entity/power UID, for pets)
    r.single()                                  # DelayedTime
    r.int32()                                   # Ticks
    r.int32()                                   # Stacking
    e["base_probability"] = r.single()
    e["suppression"] = r.int32()                # eSuppress bitmask (combat suppression)
    r.boolean()                                 # Buffable
    r.boolean()                                 # Resistible
    r.int32()                                   # SpecialCase
    r.boolean()                                 # VariableModifiedOverride
    r.boolean()                                 # IgnoreScaling
    e["pv_mode"] = r.int32()                     # ePvX
    e["to_who"] = r.int32()
    r.int32()                                   # DisplayPercentageOverride
    e["scale"] = r.single()
    e["magnitude"] = r.single()                  # nMagnitude
    e["duration"] = r.single()                   # nDuration
    e["attrib_type"] = r.int32()
    e["aspect"] = r.int32()
    e["modifier_table"] = r.string()            # ModifierTable (UID into AttribMod)
    r.boolean()                                 # NearGround
    r.boolean()                                 # CancelOnMiss
    r.boolean()                                 # RequiresToHitCheck
    r.string()                                  # UIDClassName
    r.int32()                                   # nIDClassName
    r.string()                                  # Expressions.Duration
    r.string()                                  # Expressions.Magnitude
    r.string()                                  # Expressions.Probability
    r.string()                                  # Reward
    r.string()                                  # EffectId
    r.boolean()                                 # IgnoreED
    r.string()                                  # Override
    r.single()                                  # ProcsPerMinute
    e["power_attribs"] = r.int32()
    # 12 AtrOrig fields
    r.single(); r.single(); r.int32(); r.single(); r.int32(); r.single()
    r.single(); r.int32(); r.single(); r.single(); r.single(); r.single()
    # 12 AtrMod fields
    r.single(); r.single(); r.int32(); r.single(); r.int32(); r.single()
    r.single(); r.int32(); r.single(); r.single(); r.single(); r.single()
    cond_count = r.int32()
    for _ in range(cond_count):
        r.string(); r.string()
    return e


def read_power(r: Reader):
    p = {}
    p["static_index"] = r.int32()
    p["full_name"] = r.string()
    p["group_name"] = r.string()
    p["set_name"] = r.string()
    p["power_name"] = r.string()
    p["display_name"] = r.string()
    p["available"] = r.int32()
    p["requires"] = read_requirement(r)
    r.int32()                                   # ModesRequired
    r.int32()                                   # ModesDisallowed
    p["power_type"] = r.int32()
    r.single()                                  # Accuracy
    r.int32()                                   # AttackTypes
    n = r.int32() + 1                            # GroupMembership
    for _ in range(n):
        r.string()
    p["entities_affected"] = r.int32()          # EntitiesAffected (eEntity flags)
    r.int32()                                   # EntitiesAutoHit
    r.int32()                                   # Target
    r.boolean()                                 # TargetLoS
    p["range"] = r.single()                     # Range (ft): 0/melee = self/PBAoE, >0 = ranged/targeted
    r.int32()                                   # TargetSecondary
    r.single()                                  # RangeSecondary
    p["end_cost"] = r.single()                  # EndCost
    r.single()                                  # InterruptTime
    p["cast_time"] = r.single()                 # CastTime (animation time)
    r.single()                                  # RechargeTime (current/buffed)
    p["base_recharge"] = r.single()             # BaseRechargeTime
    p["activate_period"] = r.single()           # ActivatePeriod (toggle tick interval, s) — for end/sec
    p["effect_area"] = r.int32()                # EffectArea: 0 None,1 Character(single),2 Cone,3 Sphere(PB/targeted AoE),4 Location,5 Volume
    p["radius"] = r.single()                    # Radius (ft); >0 = AoE
    p["arc"] = r.int32()                        # Arc (cone angle, degrees)
    p["max_targets"] = r.int32()                # MaxTargets (cap of foes hit)
    r.string()                                  # MaxBoosts
    r.int32()                                   # CastFlags
    r.int32()                                   # AIReport
    r.int32()                                   # NumCharges
    r.int32()                                   # UsageTime
    r.int32()                                   # LifeTime
    r.int32()                                   # LifeTimeInGame
    r.int32()                                   # NumAllowed
    r.boolean()                                 # DoNotSave
    n = r.int32() + 1                            # BoostsAllowed
    p["boosts_allowed"] = [r.string() for _ in range(n)]
    r.boolean()                                 # CastThroughHold
    r.boolean()                                 # IgnoreStrength
    p["desc_short"] = r.string()                # DescShort
    r.string()                                  # DescLong
    n = r.int32() + 1                            # Enhancements (accepted enh type ids)
    p["enhancements"] = [r.int32() for _ in range(n)]
    set_type_count = r.int32()                   # NOTE: loop is 0..count INCLUSIVE
    p["set_types"] = [r.int32() for _ in range(set_type_count + 1)]
    r.boolean()                                 # ClickBuff
    r.boolean()                                 # AlwaysToggle
    p["level"] = r.int32()
    r.boolean()                                 # AllowFrontLoading
    r.boolean()                                 # VariableEnabled
    r.boolean()                                 # VariableOverride
    r.string()                                  # VariableName
    r.int32()                                   # VariableMin
    r.int32()                                   # VariableMax
    n = r.int32() + 1                            # UIDSubPower
    for _ in range(n):
        r.string()
    n = r.int32() + 1                            # IgnoreEnh
    for _ in range(n):
        r.int32()
    n = r.int32() + 1                            # Ignore_Buff
    for _ in range(n):
        r.int32()
    r.boolean()                                 # SkipMax
    r.int32()                                   # InherentType
    r.int32()                                   # DisplayLocation
    r.boolean()                                 # MutexAuto
    r.boolean()                                 # MutexIgnore
    r.boolean()                                 # AbsorbSummonEffects
    r.boolean()                                 # AbsorbSummonAttributes
    r.boolean()                                 # ShowSummonAnyway
    r.boolean()                                 # NeverAutoUpdate
    r.boolean()                                 # NeverAutoUpdateRequirements
    r.boolean()                                 # IncludeFlag
    r.string()                                  # ForcedClass
    r.boolean()                                 # SortOverride
    r.boolean()                                 # BoostBoostable
    r.boolean()                                 # BoostUsePlayerLevel
    n = r.int32() + 1                            # Effects
    effects = [read_effect(r) for _ in range(n)]
    p["effects"] = effects
    r.boolean()                                 # HiddenPower
    r.boolean()                                 # Active
    r.boolean()                                 # Taken
    r.int32()                                   # Stacks
    r.int32()                                   # VariableStart
    return p


def read_archetype(r: Reader):
    a = {}
    a["display_name"] = r.string()
    a["hitpoints"] = r.int32()
    a["hp_cap"] = r.single()
    r.string()                                  # DescLong
    a["res_cap"] = r.single()
    n = r.int32() + 1                            # Origin
    a["origins"] = [r.string() for _ in range(n)]
    a["class_name"] = r.string()
    a["class_type"] = r.int32()
    a["column"] = r.int32()                     # Column (index into AttribMod tables)
    r.string()                                  # DescShort
    a["primary_group"] = r.string()
    a["secondary_group"] = r.string()
    a["playable"] = r.boolean()
    a["recharge_cap"] = r.single()
    a["damage_cap"] = r.single()
    a["recovery_cap"] = r.single()
    a["regen_cap"] = r.single()
    a["base_recovery"] = r.single()
    a["base_regen"] = r.single()
    a["base_threat"] = r.single()
    a["perception_cap"] = r.single()
    return a


def read_powerset(r: Reader):
    ps = {}
    ps["display_name"] = r.string()
    ps["n_archetype"] = r.int32()
    ps["set_type"] = r.int32()
    r.string()                                  # ImageName
    ps["full_name"] = r.string()
    ps["set_name"] = r.string()
    r.string()                                  # Description
    ps["sub_name"] = r.string()
    ps["at_class"] = r.string()
    r.string()                                  # UIDTrunkSet
    r.string()                                  # UIDLinkSecondary
    num = r.int32()
    for _ in range(num + 1):
        r.string()                              # UIDMutexSets
        r.int32()                               # nIDMutexSets
    return ps


def read_enhancement(r: Reader):
    e = {}
    e["static_index"] = r.int32()
    e["name"] = r.string()
    e["short_name"] = r.string()
    r.string()                                  # Desc
    e["type_id"] = r.int32()                     # eType
    e["sub_type_id"] = r.int32()
    n = r.int32() + 1                            # ClassID (allowed enh classes)
    e["class_id"] = [r.int32() for _ in range(n)]
    e["image"] = r.string()                     # Image (icon filename)
    e["nid_set"] = r.int32()
    e["uid_set"] = r.string()
    r.single()                                  # EffectChance
    e["level_min"] = r.int32()
    e["level_max"] = r.int32()
    e["unique"] = r.boolean()
    e["mutex_id"] = r.int32()
    r.int32()                                   # BuffMode
    n = r.int32() + 1                            # Effect[] (sEffect)
    boosts = []
    for _ in range(n):
        r.int32()                               # Mode
        r.int32()                               # BuffMode
        enh_id = r.int32()                       # Enhance.ID (eEnhance aspect)
        sub_id = r.int32()                       # Enhance.SubID
        sched = r.int32()                        # Schedule (eSchedule)
        mult = r.single()                        # Multiplier
        boosts.append({"aspect_id": enh_id, "sub_id": sub_id,
                       "schedule": sched, "multiplier": mult})
        if r.boolean():                         # has FX Effect? (placeholder in
            read_effect(r)                      # the data — global value not here)
    e["enhances_ids"] = [b["aspect_id"] for b in boosts]
    e["boosts"] = boosts
    e["uid"] = r.string()
    r.string()                                  # RecipeName
    e["superior"] = r.boolean()
    e["is_proc"] = r.boolean()
    e["is_scalable"] = r.boolean()
    return e


def read_enhancement_set(r: Reader):
    s = {}
    s["display_name"] = r.string()
    s["short_name"] = r.string()
    s["uid"] = r.string()
    r.string()                                  # Desc
    s["set_type"] = r.int32()                    # -> TypeGrades SetTypes index
    s["image"] = r.string()                     # Image (set icon filename)
    s["level_min"] = r.int32()
    s["level_max"] = r.int32()
    n = r.int32() + 1                            # Enhancements (member enh indices)
    s["enhancement_ids"] = [r.int32() for _ in range(n)]
    # Bonus[]
    n = r.int32() + 1
    bonuses = []
    for _ in range(n):
        r.int32()                               # Special
        r.string()                              # AltString
        pv_mode = r.int32()                      # PvMode
        slotted = r.int32()                      # Slotted (# pieces required)
        m = r.int32() + 1
        names = []
        for _ in range(m):
            names.append(r.string())            # bonus power full name
            r.int32()                           # Index
        bonuses.append({"pieces": slotted, "pv_mode": pv_mode,
                        "power_names": [x for x in names if x]})
    s["bonus"] = bonuses
    # SpecialBonus[] (no PvMode / Slotted)
    n = r.int32() + 1
    special = []
    for _ in range(n):
        r.int32()                               # Special
        r.string()                              # AltString
        m = r.int32() + 1
        names = []
        for _ in range(m):
            names.append(r.string())
            r.int32()
        special.append({"power_names": [x for x in names if x]})
    s["special_bonus"] = special
    return s


# ----------------------------------------------------------------------------
# Top-level loaders
# ----------------------------------------------------------------------------
def load_main_db(path):
    r = Reader(open(path, "rb").read())
    header = r.string()
    assert header == "Mids Reborn Powers Database", header
    version = r.string()
    year = r.int32()
    if year > 0:
        r.int32(); r.int32()                    # month, day
    else:
        r.int64()                               # date binary
    issue = r.int32()
    r.int32()                                   # PageVol
    r.string()                                  # PageVolText

    assert r.string() == "BEGIN:ARCHETYPES"
    n = r.int32() + 1
    archetypes = [read_archetype(r) for _ in range(n)]

    assert r.string() == "BEGIN:POWERSETS"
    n = r.int32() + 1
    powersets = [read_powerset(r) for _ in range(n)]

    assert r.string() == "BEGIN:POWERS"
    n = r.int32() + 1
    powers = [read_power(r) for _ in range(n)]

    # Summons section: maps each summoned-entity UID -> its pet powersets, so a
    # summon power (EntCreate effect's `summon` UID) can be resolved to the pet's
    # actual attack powers for pet-damage display.
    assert r.string() == "BEGIN:SUMMONS"
    n = r.int32() + 1
    entities = [read_summoned_entity(r) for _ in range(n)]

    return {"version": version, "issue": issue,
            "archetypes": archetypes, "powersets": powersets, "powers": powers,
            "entities": entities}


def read_summoned_entity(r: Reader):
    """One SummonedEntity (mirrors SummonedEntity(BinaryReader))."""
    e = {}
    e["uid"] = r.string()
    e["display_name"] = r.string()
    r.int32()                                   # EntityType (eSummonEntity)
    e["class_name"] = r.string()
    n = r.int32()                               # PowersetFullName (exact count)
    e["powerset_full_names"] = [r.string() for _ in range(n)]
    n = r.int32()                               # UpgradePowerFullName (exact count)
    e["upgrade_powers"] = [r.string() for _ in range(n)]
    return e


def load_enh_db(path):
    r = Reader(open(path, "rb").read())
    header = r.string()
    assert header == "Mids Reborn Enhancement Database", header
    r.single()                                  # version float
    n = r.int32() + 1
    enhancements = [read_enhancement(r) for _ in range(n)]
    n = r.int32() + 1
    sets = [read_enhancement_set(r) for _ in range(n)]
    return {"enhancements": enhancements, "sets": sets}


def load_eclasses(path):
    """EClasses.mhd is tab-delimited text:  Index<TAB>Name<TAB>Short<TAB>Class<TAB>Desc"""
    classes = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        seen_index_header = False
        for raw in f:
            line = raw.rstrip("\r\n")
            cols = line.split("\t")
            if not seen_index_header:
                if cols and cols[0] == "Index":
                    seen_index_header = True
                continue
            if not cols or cols[0] == "End" or cols[0] == "":
                if cols and cols[0] == "End":
                    break
                continue
            try:
                idx = int(cols[0])
            except ValueError:
                continue
            classes[idx] = {
                "name": cols[1] if len(cols) > 1 else "",
                "short": cols[2] if len(cols) > 2 else "",
                "class": cols[3] if len(cols) > 3 else "",
            }
    return classes


def load_set_types(path):
    data = json.load(open(path, "r", encoding="utf-8"))
    return [t["Name"] for t in data["SetTypes"]], \
           [t["ShortName"] for t in data["SetTypes"]]


# ----------------------------------------------------------------------------
# Build the structured output JSON
# ----------------------------------------------------------------------------
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"DB dir: {DB_DIR}")

    main_db = load_main_db(os.path.join(DB_DIR, "I12.mhd"))
    enh_db = load_enh_db(os.path.join(DB_DIR, "EnhDB.mhd"))
    eclasses = load_eclasses(os.path.join(DB_DIR, "EClasses.mhd"))
    set_type_names, set_type_shorts = load_set_types(
        os.path.join(DB_DIR, "TypeGrades.json"))
    mult_io, mult_ed, mult_grade = load_maths(os.path.join(DB_DIR, "Maths.mhd"))
    mod_tables = load_attribmod(os.path.join(DB_DIR, "AttribMod.json"))
    # MidsReborn matches modifier-table names case-INSENSITIVELY; the DB authors
    # them inconsistently (e.g. armor shields reference 'Melee_Res_DMG' while the
    # table is stored 'Melee_Res_Dmg'). A case-sensitive lookup silently drops those
    # effects — which nuked the resistance on ~37 armor shields (Fire Shield, Plasma
    # Shield, Charged Armor…). Resolve to the canonical key so every effect lands.
    _mt_ci = {k.lower(): k for k in mod_tables}

    def canon_table(name):
        return _mt_ci.get((name or "").lower())

    archetypes = main_db["archetypes"]
    powersets = main_db["powersets"]
    powers = main_db["powers"]
    enhancements = enh_db["enhancements"]
    sets = enh_db["sets"]

    # ---- Pseudo-pet / "location AoE" debuff resolution -----------------------
    # Powers like Freezing Rain, Sleet, Ice Slick don't carry their debuff on the
    # power you pick — they SUMMON a pseudo-pet POWER (a rain/patch entity) that holds
    # the real -Resistance/-Defense/Slow effects. In the DB the picked power has a single
    # summon-redirect effect whose `summon` field is the pseudo-pet power's full_name
    # (e.g. 'Pets.FreezingRain_Controller.FreezingRain'), and that pseudo-pet power lives
    # in the powers table with the actual effects. Without folding those back, the picked
    # power reads as effectless — so the solver/autopicker can't see a controller's or
    # defender's signature debuff. We fold ONLY foe-facing debuffs/ally-buffs from the
    # pseudo-pet (never its self-buffs, never re-flagging the parent as an attack), and
    # ONLY when the summon target is itself a pet/pseudo-pet power (Pets.* / Villain_Pets.*)
    # — which excludes attack-variant redirects (Ranged_Shot->..._Normal, same set) and
    # enhancement procs (Boosts.*).
    POWERS_BY_FULL = {p["full_name"]: p for p in powers if p.get("full_name")}
    _PBF_CI = {p["full_name"].lower(): p for p in powers if p.get("full_name")}
    # ENTITY summons (EntCreate, et=38): the `summon` uid names a SummonedEntity whose powersets
    # hold the delivering powers. This covers the OTHER pseudo-pet flavor — Tar Patch / Caltrops /
    # Poison Trap patches and Transfusion's heal — whose effects live on entity powers, not on a
    # redirect power. The critical gate: real COMBAT pets (Jack Frost, Fire Imps, Animate Stone)
    # use the same mechanism but must NOT be folded (their attacks are the PET's damage, shown via
    # the pet-DPS display) — and their summon powers accept the PET set categories ("Pet Damage",
    # "Recharge Intensive Pets") while pseudo-pet delivery powers never do. So: fold entity effects
    # only when the summoning power has NO pet set category. (class_name can't discriminate — both
    # are 'Class_Minion_Pets'.)
    ENTITY_BY_UID = {e["uid"]: e for e in main_db.get("entities", [])}
    # Summon uids are cased inconsistently in the DB (power says 'Pets_Volcanicgas', entities
    # table says 'Pets_VolcanicGas') — Mids matches loosely; an exact lookup silently dropped
    # 248 summon uids (cost Volcanic Gasses its pulsing Hold). Same disease as the
    # modifier-table casing fix above: resolve case-insensitively.
    _ENT_CI = {e["uid"].lower(): e for e in main_db.get("entities", [])}
    POWERS_BY_PS = {}
    for _p in powers:
        _ps = (_p["group_name"] + "." + _p["set_name"]) if (_p["group_name"] and _p["set_name"]) \
            else (_p["full_name"].rsplit(".", 1)[0] if _p.get("full_name") else "")
        POWERS_BY_PS.setdefault(_ps, []).append(_p)
    PET_CAT_IDS = {i for i, n in enumerate(set_type_names)
                   if n in ("Pet Damage", "Recharge Intensive Pets")}

    def _accepts_pet_sets(p):
        return any(i in PET_CAT_IDS for i in p.get("set_types", []) if i >= 0)

    def _is_pseudopet_full(full_name):
        ps = full_name.rsplit(".", 1)[0] if "." in full_name else full_name
        # Redirects.* is the game's hidden-effect delivery namespace (ExecutePower, et=85):
        # Sonic Attack's per-blast −res lives in Redirects.Sonic.Sonic_Vibrations_*, Storm
        # Blast/Marine Affinity/Pyrotechnic Control use it too. Same fold as pseudo-pets —
        # without it those sets read as debuff-less (user-caught 2026-07-02).
        return ps.startswith("Pets.") or ps.startswith("Villain_Pets.") \
            or ps.startswith("Redirects.")

    def pseudopet_effects(p, _depth=0, _seen=None, _entity_ok=None):
        """Yield (effect, owner_power) for effects reached THROUGH a pseudo-pet summon —
        either a POWER redirect (Freezing Rain -> Pets.FreezingRain…) or an ENTITY summon
        (Tar Patch -> Pets_TarPatch entity -> its patch power). Bounded recursion.
        `_entity_ok` (decided at the TOP power) gates the entity flavor to non-combat-pet powers."""
        if _seen is None:
            _seen = set()
        if _entity_ok is None:
            _entity_ok = not _accepts_pet_sets(p)
        for ef in p["effects"]:
            uid = ef.get("summon")
            if not uid or uid in _seen or _depth >= 3:
                continue
            tgt = POWERS_BY_FULL.get(uid) or _PBF_CI.get(uid.lower())
            if tgt is not None and _is_pseudopet_full(tgt["full_name"]):
                _seen.add(uid)
                for tef in tgt["effects"]:
                    yield tef, tgt
                yield from pseudopet_effects(tgt, _depth + 1, _seen, _entity_ok)
                continue
            ent = ENTITY_BY_UID.get(uid) or _ENT_CI.get(uid.lower())
            if ent is not None and _entity_ok:
                _seen.add(uid)
                for eps in ent.get("powerset_full_names", []):
                    for pp in POWERS_BY_PS.get(eps, []):
                        for tef in pp["effects"]:
                            yield tef, pp
                        yield from pseudopet_effects(pp, _depth + 1, _seen, _entity_ok)

    print(f"Parsed: {len(archetypes)} archetypes, {len(powersets)} powersets, "
          f"{len(powers)} powers, {len(enhancements)} enhancements, {len(sets)} sets")

    SET_TYPE_MAP = {"None": -1, "Primary": 1, "Secondary": 2, "Ancillary": 3,
                    "Inherent": 4, "Pool": 5, "Accolade": 6, "Temp": 7,
                    "Pet": 8, "SetBonus": 9, "Boost": 10, "Incarnate": 11,
                    "Redirect": 12}
    SET_TYPE_LABEL = {v: k for k, v in SET_TYPE_MAP.items()}

    def cat_name(i):
        return set_type_names[i] if 0 <= i < len(set_type_names) else f"Unknown({i})"

    def cat_short(i):
        return set_type_shorts[i] if 0 <= i < len(set_type_shorts) else f"Unknown({i})"

    def enh_type_name(i):
        return eclasses.get(i, {}).get("name", f"Unknown({i})")

    # ---- powername -> display name (for resolving set bonuses) ----
    power_by_fullname = {p["full_name"].lower(): p for p in powers if p["full_name"]}

    def resolve_bonus_text(power_full):
        p = power_by_fullname.get((power_full or "").lower())
        if p:
            return p["display_name"] or p["power_name"] or power_full
        return power_full

    def enh_class_name(i):
        """Map an eEnhance enum value to a readable name."""
        return EENHANCE[i] if 0 <= i < len(EENHANCE) else f"Enh({i})"

    def resolve_bonus_effects(power_full):
        """Resolve a set-bonus power into structured numeric stat effects.
        Set bonuses are flat (magnitude 1.0), so the value lives in `scale`."""
        p = power_by_fullname.get((power_full or "").lower())
        if not p:
            return []
        out = []
        for ef in p["effects"]:
            et = EFFECT_TYPE[ef["effect_type"]] if 0 <= ef["effect_type"] < len(EFFECT_TYPE) else None
            if et not in STAT_EFFECT_TYPES:
                continue
            val = ef["scale"] if abs(ef["scale"]) > 1e-9 else ef["magnitude"]
            if abs(val) < 1e-9:
                continue
            # ETModifies is an eEffectType index (NOT eEnhance) — same enum the
            # power/incarnate code uses.
            modifies = (EFFECT_TYPE[ef["et_modifies"]]
                        if 0 <= ef["et_modifies"] < len(EFFECT_TYPE) else "None")
            # A set bonus's +recharge/+recovery/etc. is encoded as an
            # Enhancement effect that *modifies* that stat. Relabel it to the
            # modified stat so the engine counts it as a flat global (e.g.
            # Apocalypse 5-pc -> effect "RechargeTime" +10%). This was the cause
            # of builds showing +0% recharge despite heavy recharge slotting.
            eff = et
            if et == "Enhancement":
                if modifies in ("RechargeTime", "Recovery", "Regeneration",
                                "ToHit", "HitPoints", "Accuracy", "Heal"):
                    # "Accuracy" was missing until 2026-07-08 (65 invisible
                    # bonuses); "Heal" until v29 (the 11 heal-strength bonuses,
                    # Numina 4pc +6% etc.) — same gap, same fix.
                    eff = modifies
                else:
                    continue   # enhancement of an untracked aspect (Range, EndDisc…)
            out.append({
                "effect": eff,
                "damage_type": EDAMAGE[ef["damage_type"]] if 0 <= ef["damage_type"] < len(EDAMAGE) else "None",
                "aspect": EASPECT[ef["aspect"]] if 0 <= ef["aspect"] < len(EASPECT) else "Str",
                "modifies": modifies,
                "value": round(val, 5),
                "to_who": ef["to_who"],   # 0 Unspecified, 1 Target, 2 Self
            })
        return out

    # ---- archetypes.json ----
    arch_out = []
    for a in archetypes:
        if not a["class_name"]:
            continue
        arch_out.append({
            "name": a["class_name"],
            "display_name": a["display_name"],
            "playable": a["playable"],
            "column": a["column"],
            "hitpoints": a["hitpoints"],
            "hp_cap": round(a["hp_cap"], 2),
            "res_cap": round(a["res_cap"], 4),
            "recharge_cap": round(a["recharge_cap"], 4),
            "damage_cap": round(a["damage_cap"], 4),
            "regen_cap": round(a["regen_cap"], 4),
            "recovery_cap": round(a["recovery_cap"], 4),
            "base_recovery": round(a["base_recovery"], 4),
            "base_regen": round(a["base_regen"], 4),
            "primary_group": a["primary_group"],
            "secondary_group": a["secondary_group"],
        })

    # ---- powersets.json ----
    # index archetypes by their position (n_archetype refers to Classes index)
    at_by_idx = {i: a for i, a in enumerate(archetypes)}
    valid_classes = {a["class_name"] for a in archetypes if a["class_name"]}

    # Epic/ancillary pools are often shared (n_archetype == -1) with eligibility
    # encoded in each power's Requires.ClassName. Build full_name -> {classes}.
    epic_eligibility = {}
    for p in powers:
        if not (p["group_name"] and p["set_name"]):
            continue
        psf = p["group_name"] + "." + p["set_name"]
        reqs = [c for c in p["requires"]["class_name"] if c in valid_classes]
        if reqs:
            epic_eligibility.setdefault(psf, set()).update(reqs)
    # CLIENT-VERIFIED eligibility subtractions (2026-07-08, powers.bin requires
    # expressions): the frozen Mids DB's Requires.ClassName lists extra classes
    # on three epic pools, which put duplicate same-display pools in the wrong
    # dropdowns (Joel's field report: Stalker showed two "Fire Mastery"). The
    # game's own requires say: Sentinel_Fire_Mastery = Sentinel only;
    # Dark_Mastery_TankBrute (client Tank_Dark_Mastery) = Tanker/Brute only;
    # Sentinel_Psi_Mastery (client Sentinel_Psionic_Mastery) = Sentinel only.
    # All-AT audit vs the client: these 3 are the only wrong grants, and no
    # rightful grant is missing (116 client (set, AT) pairs checked).
    _EPIC_NOT = {"Epic.Sentinel_Fire_Mastery": {"Class_Stalker"},
                 "Epic.Dark_Mastery_TankBrute": {"Class_Dominator"},
                 "Epic.Sentinel_Psi_Mastery": {"Class_Dominator"}}
    for psf, drop in _EPIC_NOT.items():
        if psf in epic_eligibility:
            epic_eligibility[psf] -= drop

    powerset_out = {}      # archetype class_name -> {primary, secondary, epic}
    universal_pools = []   # set_type == Pool
    seen_epic = {}         # cls -> set(full_name) to dedupe
    for ps in powersets:
        if not ps["full_name"]:
            continue
        st_label = SET_TYPE_LABEL.get(ps["set_type"], str(ps["set_type"]))
        entry = {
            "full_name": ps["full_name"],
            "display_name": ps["display_name"],
            "set_type": st_label,
            "archetype_index": ps["n_archetype"],
        }
        at = at_by_idx.get(ps["n_archetype"])

        if st_label == "Pool":
            universal_pools.append(entry)
            continue

        if st_label == "Ancillary":
            # union of direct n_archetype link and Requires.ClassName eligibility
            eligible = set()
            if at and at["class_name"]:
                eligible.add(at["class_name"])
            eligible |= epic_eligibility.get(ps["full_name"], set())
            for cls in eligible:
                bucket = powerset_out.setdefault(
                    cls, {"primary": [], "secondary": [], "epic": []})
                if entry["full_name"] in seen_epic.setdefault(cls, set()):
                    continue
                seen_epic[cls].add(entry["full_name"])
                bucket["epic"].append(entry)
            continue

        if at is None or not at["class_name"]:
            continue
        cls = at["class_name"]
        bucket = powerset_out.setdefault(cls, {"primary": [], "secondary": [],
                                               "epic": []})
        if st_label == "Primary":
            bucket["primary"].append(entry)
        elif st_label == "Secondary":
            bucket["secondary"].append(entry)
    # attach shared pools to every archetype view via a top-level key
    powerset_payload = {
        "by_archetype": powerset_out,
        "pools": sorted(universal_pools, key=lambda e: e["display_name"]),
    }

    # ---- powers.json ----
    def power_self_effects(p):
        """Stat-relevant self-buff effects, with the raw params the engine
        needs to compute base magnitude per archetype: base = scale * nmag *
        modifier_table[49][AT.column]. pv_mode tagged (0=Any,1=PvE,2=PvP) so the
        engine can pick PvE vs PvP effect variants."""
        out = []
        for ef in p["effects"]:
            et = (EFFECT_TYPE[ef["effect_type"]]
                  if 0 <= ef["effect_type"] < len(EFFECT_TYPE) else None)
            # Direct stat effect, or a global Enhancement(X) buff (e.g. Hasten
            # = Enhancement modifying RechargeTime).
            if et in EFFECT_TO_ENHANCE:
                eff_stat = et
            elif et == "Enhancement":
                mod_et = (EFFECT_TYPE[ef["et_modifies"]]
                          if 0 <= ef["et_modifies"] < len(EFFECT_TYPE) else None)
                if mod_et in ("RechargeTime", "Recovery", "Regeneration", "ToHit"):
                    eff_stat = mod_et
                else:
                    continue
            else:
                continue
            if ef["attrib_type"] != 0:        # only Magnitude effects
                continue
            if ef["to_who"] != 2:             # only self buffs
                continue
            if ef["base_probability"] < 0.99:   # skip chance/proc effects
                continue
            mt = canon_table(ef["modifier_table"])
            if mt is None:
                continue
            aspect = EFFECT_TO_ENHANCE.get(eff_stat, eff_stat)
            entry = {
                "effect": eff_stat,
                "damage_type": (EDAMAGE[ef["damage_type"]]
                                if 0 <= ef["damage_type"] < len(EDAMAGE) else "None"),
                "scale": round(ef["scale"], 6),
                "nmag": round(ef["magnitude"], 6) if abs(ef["magnitude"]) > 1e-9 else 1.0,
                "modifier_table": mt,
                "enhance_aspect": aspect,
                "ed_schedule": ed_schedule_for_aspect(aspect),
                "pv_mode": ef["pv_mode"],
            }
            # Combat suppression (eSuppress bitmask): kept only when set, so the
            # display layer can subtract suppressed contributions (Mids' Options >
            # Effects and Maths > Suppression). Zero = never suppresses = omitted.
            if ef.get("suppression"):
                entry["suppression"] = ef["suppression"]
            # Buff window (nDuration, seconds): kept only when set — a click
            # self-buff's active window (Hasten 120s, Build Up 10s), which the
            # totals-chip uptime note divides by the power's cycle. Zero (toggle
            # ticks, autos) = omitted, same convention as suppression.
            if ef.get("duration"):
                entry["duration"] = round(ef["duration"], 3)
            out.append(entry)
        return out

    def power_combat_effects(p):
        """Offensive effects, with the raw params the engine resolves per
        archetype (base = scale*nmag*modifier_table[49][AT.column]):
          - damage   : Damage effects to a target -> enhanced damage / DPS
          - debuffs  : stat effects on a FOE (e.g. -Resistance from a -res attack)
          - buffs    : stat effects on an ally/teammate (team support output)
        Non-Magnitude effects excluded; pv_mode tagged (0=Any,1=PvE,2=PvP) so the
        engine can pick PvE vs PvP variants. nMag defaults to 1."""
        dmg, debuffs, buffs = [], [], []

        def bucket(ef, owner, allow_damage):
            et = (EFFECT_TYPE[ef["effect_type"]]
                  if 0 <= ef["effect_type"] < len(EFFECT_TYPE) else None)
            if et is None or ef["attrib_type"] != 0:
                return
            # An Enhancement effect modifies the TARGET'S strength in another attribute
            # (et_modifies indexes eEffectType): Lingering Radiation's −Recharge, Accelerate
            # Metabolism's +Recharge live here — previously invisible (wiki-audit 2026-07-02).
            if et == "Enhancement":
                em = ef.get("et_modifies")
                et = (EFFECT_TYPE[em] if isinstance(em, int)
                      and 0 <= em < len(EFFECT_TYPE) else None)
                # Enhancement rows debuff/buff the target's STRENGTH in an attribute, not the
                # stat itself. Only the recharge/movement-slow family is canonically delivered
                # this way (Lingering Radiation's −Rech, AM's +Rech) — those units coincide.
                # Everything else (Benumb-class "−Special": ToHit/Heal/Damage strength) is a
                # DIFFERENT unit; folding it as stat points once gave a Mastermind −185% ToHit.
                # Future term, flagged — dropped for now.
                if et != "RechargeTime" and et not in SLOW_EFFECT_TYPES:
                    return
            if et in SLOW_EFFECT_TYPES:
                et = "Slow"                     # the wiki's "-SPD" family, one summary key
            mt = canon_table(ef["modifier_table"])
            if mt is None:
                return
            scale = round(ef["scale"], 6)
            nmag = round(ef["magnitude"], 6) if abs(ef["magnitude"]) > 1e-9 else 1.0
            prob = round(ef["base_probability"], 4)
            dtype = (EDAMAGE[ef["damage_type"]]
                     if 0 <= ef["damage_type"] < len(EDAMAGE) else "None")
            rec = {"effect": et, "damage_type": dtype, "scale": scale,
                   "nmag": nmag, "modifier_table": mt, "probability": prob,
                   "duration": round(ef["duration"], 3), "pv_mode": ef["pv_mode"]}
            # Foe-check is per the effect's OWNER: a location power (Freezing Rain) may not
            # itself flag foe-affecting, but the pseudo-pet it summons does.
            hits_foe = bool((owner.get("entities_affected", 0) or 0) & ENTITY_FOE)
            # PBAoE ally buffs (AM, Sonic Dispersion, Maneuvers-likes) are encoded
            # to_who=SELF + friendly area flags — count them as team buffs, not self-only.
            team_area = bool((owner.get("entities_affected", 0) or 0) & ENTITY_FRIENDLY)
            if allow_damage and et == "Damage" and ef["to_who"] == 1:
                rec["enhance_aspect"] = "Damage"
                rec["ed_schedule"] = ed_schedule_for_aspect("Damage")
                dmg.append(rec)
            elif ef["to_who"] == 1 and hits_foe and et in DEBUFF_EFFECT_TYPES:
                debuffs.append(rec)
            elif (not hits_foe and et in BUFF_EFFECT_TYPES
                  and (ef["to_who"] == 1
                       or (ef["to_who"] == 2 and team_area and et != "Heal"))):
                buffs.append(rec)      # PBAoE heals live in heal_effects, not here

        # CONTROL: foe Mez (hold/immob/stun/sleep/confuse/fear/KB). Kept as raw params so the
        # engine resolves magnitude per AT (mag = scale*nmag*table[49][AT]); duration + chance let
        # the optimizer score control OUTPUT (mag-seconds x uptime x area) — the thing it was blind
        # to. Aggro/utility mez (Taunt/Placate/ToggleDrop/Untouchable/Teleport) is NOT control.
        control = []
        _NOT_CONTROL = {"None", "OnlyAffectsSelf", "Taunt", "Placate", "ToggleDrop",
                        "Untouchable", "Teleport", "CombatPhase", "Avoid"}

        def ctrl(ef, owner):
            et = (EFFECT_TYPE[ef["effect_type"]]
                  if 0 <= ef["effect_type"] < len(EFFECT_TYPE) else None)
            if et != "Mez" or ef["to_who"] != 1:
                return
            if not bool((owner.get("entities_affected", 0) or 0) & ENTITY_FOE):
                return
            mez = EMEZ[ef["mez_type"]] if 0 <= ef["mez_type"] < len(EMEZ) else "Unknown"
            if mez in _NOT_CONTROL:
                return
            control.append({
                "mez": mez,
                "kind": "hard" if mez in HARD_CONTROL else ("soft" if mez in SOFT_CONTROL else "other"),
                "scale": round(ef["scale"], 6),
                "nmag": round(ef["magnitude"], 6) if abs(ef["magnitude"]) > 1e-9 else 1.0,
                "modifier_table": canon_table(ef["modifier_table"]),   # None -> magnitude is nmag alone
                "duration": round(ef["duration"], 3),
                "probability": round(ef["base_probability"], 4),
                "pv_mode": ef["pv_mode"],
            })

        # HEAL: direct HP restoration — SELF (to_who=2 = a survival self-heal like Reconstruction,
        # which the buff bucket drops) AND ALLY (to_who=1 = team support like Heal Other). Kept with
        # to_who + raw params so the optimizer can score heal OUTPUT: magnitude × area (group vs
        # single) ÷ recharge (throughput) ÷ split self-survival vs team-support. (+Regen buffs like
        # Regeneration Aura are sustained healing but live in buff_effects as Regeneration.)
        heal = []

        def heal_fn(ef, owner):
            et = (EFFECT_TYPE[ef["effect_type"]]
                  if 0 <= ef["effect_type"] < len(EFFECT_TYPE) else None)
            if et != "Heal" or ef["to_who"] not in (1, 2):
                return
            # PBAoE group heals (Radiant Aura, Healing Aura) are encoded to_who=SELF with
            # friendly area flags — they heal the TEAM, not just the caster (wiki-audit
            # 2026-07-02). Reclassify so heal output scores them as group heals.
            to_who = ef["to_who"]
            if to_who == 2 and ((owner.get("entities_affected", 0) or 0) & ENTITY_FRIENDLY):
                to_who = 1
            heal.append({
                "to_who": to_who,                               # 1 = ally/group, 2 = self
                "scale": round(ef["scale"], 6),
                "nmag": round(ef["magnitude"], 6) if abs(ef["magnitude"]) > 1e-9 else 1.0,
                "modifier_table": canon_table(ef["modifier_table"]),
                "probability": round(ef["base_probability"], 4),
                "pv_mode": ef["pv_mode"],
            })

        for ef in p["effects"]:
            bucket(ef, p, allow_damage=True)
            ctrl(ef, p)
            heal_fn(ef, p)
        # Fold foe-debuffs / ally-buffs / CONTROL / HEAL from any summoned pseudo-pet (Freezing Rain's
        # rain, Transfusion's heal pseudo-pet…). allow_damage=False so a pseudo-pet DoT doesn't
        # mislabel the location power as an attack (its own damage effects, if any, still count).
        for ef, owner in pseudopet_effects(p):
            bucket(ef, owner, allow_damage=False)
            ctrl(ef, owner)
            heal_fn(ef, owner)
        return dmg, debuffs, buffs, control, heal

    powers_out = {}        # powerset full_name -> [powers]
    for p in powers:
        if not p["full_name"]:
            continue
        # slottable if it accepts any boosts/enhancements
        accepted_enh_ids = [i for i in p["enhancements"] if i in eclasses]
        accepted_cat_ids = [i for i in p["set_types"] if i >= 0]
        slottable = len(p["boosts_allowed"]) > 0 or len(accepted_enh_ids) > 0
        self_fx = power_self_effects(p)
        dmg_fx, debuff_fx, buff_fx, control_fx, heal_fx = power_combat_effects(p)
        # Pet summons: entity UIDs this power creates (EntCreate effects), so the
        # engine can resolve them to the pet's powersets -> pet attacks.
        summon_uids = []
        pet_powersets = []
        for ef in p["effects"]:
            et = (EFFECT_TYPE[ef["effect_type"]]
                  if 0 <= ef["effect_type"] < len(EFFECT_TYPE) else None)
            if et == "EntCreate" and ef.get("summon"):
                if ef["summon"] not in summon_uids:
                    summon_uids.append(ef["summon"])
            elif ef.get("summon"):
                # POWER-redirect summons (et=85): Carrion Creepers' vines live in
                # Villain_Pets.Creeper_Patch/Creeper_Vine as POWERS, not entities — record their
                # POWERSETS so the engine can price the pet DAMAGE (the fold above takes only
                # their debuffs/control/heals; the vines' damage was invisible to the optimizer).
                tgt = POWERS_BY_FULL.get(ef["summon"]) or _PBF_CI.get(ef["summon"].lower())
                if tgt is not None and _is_pseudopet_full(tgt["full_name"]):
                    tps = tgt["full_name"].rsplit(".", 1)[0]
                    if tps not in pet_powersets:
                        pet_powersets.append(tps)
        # Powerset full name uniquely identifies archetype+powerset
        # (e.g. "Tanker_Defense.Invulnerability"). The bare set_name
        # ("Invulnerability") is shared across archetypes, so never key on it.
        if p["group_name"] and p["set_name"]:
            powerset_full = p["group_name"] + "." + p["set_name"]
        else:
            powerset_full = p["full_name"].rsplit(".", 1)[0]
        rec = {
            "full_name": p["full_name"],
            "display_name": p["display_name"],
            "power_name": p["power_name"],
            "powerset_full_name": powerset_full,
            "group_name": p["group_name"],
            "level_available": p["level"],
            "power_type": p["power_type"],
            "slottable": slottable,
            "default_slot_count": 1 if slottable else 0,
            "max_slot_count": 6 if slottable else 0,
            "accepted_enhancement_type_ids": accepted_enh_ids,
            "accepted_enhancement_types": [enh_type_name(i) for i in accepted_enh_ids],
            "accepted_set_category_ids": accepted_cat_ids,
            "accepted_set_categories": [cat_name(i) for i in accepted_cat_ids],
            "accepted_set_category_shorts": [cat_short(i) for i in accepted_cat_ids],
            "self_effects": self_fx,
            "is_attack": bool(dmg_fx),
            "cast_time": round(p.get("cast_time", 0.0), 4),
            "base_recharge": round(p.get("base_recharge", 0.0), 4),
            "end_cost": round(p.get("end_cost", 0.0), 4),
            # Geometry (real Mids fields) — replaces category-guessing for AoE/PBAoE/cone/single
            # target + melee/ranged. effect_area: 1=single,2=cone,3=sphere,4=location patch.
            "range": round(p.get("range", 0.0), 2),
            "activate_period": round(p.get("activate_period", 0.0), 3),
            "effect_area": p.get("effect_area", 0),
            "radius": round(p.get("radius", 0.0), 2),
            "arc": p.get("arc", 0),
            "max_targets": p.get("max_targets", 0),
            "damage_effects": dmg_fx,
            "debuff_effects": debuff_fx,
            "buff_effects": buff_fx,
            "control_effects": control_fx,
            "heal_effects": heal_fx,
            "is_resurrect": (p.get("power_name") or "") in _RESURRECT_POWERS,
            "summons": summon_uids,
            "pet_powersets": pet_powersets,
        }
        powers_out.setdefault(powerset_full, []).append(rec)

    # ---- enhancement_sets.json ----
    enh_by_idx = {i: e for i, e in enumerate(enhancements)}

    def piece_boosts(e, set_level_max):
        """Per-aspect enhancement value for one piece, at its IO level.
        value = MultIO[level][schedule] * multiplier * (1.25 if superior)."""
        io_level = max(10, min(50, set_level_max or 50))
        if io_level not in mult_io:
            io_level = 50
        out = []
        for b in e.get("boosts", []):
            sched = b["schedule"]
            if sched < 0 or sched > 3:        # None / Multiple -> no enh value
                continue
            aspect = (EENHANCE[b["aspect_id"]]
                      if 0 <= b["aspect_id"] < len(EENHANCE) else None)
            if not aspect or aspect == "None":
                continue
            base = mult_io.get(io_level, [0, 0, 0, 0])[sched]
            mult = b["multiplier"] if abs(b["multiplier"]) > 0.01 else 1.0
            val = base * mult * (1.25 if e.get("superior") else 1.0)
            if abs(val) < 1e-9:
                continue
            out.append({"aspect": aspect, "value": round(val, 6), "schedule": sched})
        return out

    sets_out = []
    set_bonuses_out = {}
    sets_by_category = {}
    for s in sets:
        cat_id = s["set_type"]
        pieces = []
        for eid in s["enhancement_ids"]:
            e = enh_by_idx.get(eid)
            if not e:
                continue
            enh_classes = sorted({enh_class_name(i) for i in e["enhances_ids"]
                                  if i > 0})
            pieces.append({
                "name": e["name"],
                "short_name": e["short_name"],
                "enhances": enh_classes,
                "boosts": piece_boosts(e, s["level_max"]),
                "unique": e["unique"],
                "is_proc": e["is_proc"],
                "uid": e["uid"],
                # Icon: the piece's own image, falling back to the set's icon.
                "image": e.get("image") or s.get("image") or "",
            })
        # set bonuses: group by piece count
        bonus_list = []
        for b in s["bonus"]:
            texts = [resolve_bonus_text(pn) for pn in b["power_names"]]
            texts = [t for t in texts if t]
            if not texts:
                continue
            effects = []
            for pn in b["power_names"]:
                effects.extend(resolve_bonus_effects(pn))
            bonus_list.append({
                "pieces_required": b["pieces"],
                "pv_mode": b["pv_mode"],   # 0 Any, 1 PvE, 2 PvP
                "bonuses": texts,
                "effects": effects,
            })
        bonus_list.sort(key=lambda x: (x["pieces_required"], x["pv_mode"]))

        set_rec = {
            "name": s["display_name"],
            "short_name": s["short_name"],
            "uid": s["uid"],
            "category_id": cat_id,
            "category": cat_name(cat_id),
            "category_short": cat_short(cat_id),
            "level_min": s["level_min"],
            "level_max": s["level_max"],
            "piece_count": len(pieces),
            "image": s.get("image") or "",
            "pieces": pieces,
            "bonuses": bonus_list,
        }
        sets_out.append(set_rec)
        set_bonuses_out[s["uid"]] = {
            "name": s["display_name"],
            "category": cat_name(cat_id),
            "bonuses": bonus_list,
        }
        sets_by_category.setdefault(cat_name(cat_id), []).append(s["display_name"])

    # ---- incarnates.json ----
    # The 7 player-facing incarnate slots; each is a powerset under "Incarnate".
    INCARNATE_SLOTS = ["Alpha", "Judgement", "Interface", "Lore",
                       "Destiny", "Hybrid", "Genesis"]
    inc_by_slot = {}
    for p in powers:
        if p["group_name"] == "Incarnate" and p["set_name"] in INCARNATE_SLOTS:
            inc_by_slot.setdefault(p["set_name"], []).append(p)

    # Lookup over ALL powers — Alpha boosts live in a hidden GRANTED power
    # (GrantPower.summon -> e.g. 'Incarnate.Alpha_Silent.Damage_Plus_Very_Rare'),
    # so we follow that chain to find the real magnitude.
    inc_byname = {p["full_name"]: p for p in powers}
    # direct stat effects we keep, + Enhancement(X) mods we map to a stat
    INC_STATS = {"Defense", "Resistance", "ToHit", "Recovery", "Regeneration",
                 "Healing", "DamageBuff", "Endurance", "Absorb", "MaxHP", "HitPoints"}
    INC_ENH = {"RechargeTime", "Recovery", "Regeneration", "ToHit", "Healing", "Damage"}

    # Alpha boosts are GRANTED powers whose effect_type is uniformly "DamageBuff"
    # (a Strength buff, aspect=3) regardless of what they actually boost — the DB
    # distinguishes them ONLY by the granted power's NAME (Damage_Plus vs
    # Res_Damage_Plus vs ToHit_Buff…). So when we follow a grant, the summon name
    # OVERRIDES the effect's stat. (Direct effects on the visible power keep their et.)
    _SILENT_STAT = [("res_damage", "Resistance"), ("resist", "Resistance"),
                    ("defense", "Defense"), ("tohit", "ToHit"),
                    ("recharge", "RechargeTime"), ("heal", "Healing"),
                    ("endmod", "Recovery"), ("recovery", "Recovery"),
                    ("regen", "Regeneration"), ("accuracy", "Accuracy"),
                    ("damage", "DamageBuff")]

    def _silent_stat(name):
        n = (name or "").lower()
        if "debuff" in n or "de_buff" in n:
            return None   # boosts your offensive DEBUFFS (e.g. Musculature's -Def), not your own def/res
        for sub, st in _SILENT_STAT:
            if sub in n:
                return st
        return None    # run/jump/immobilize/fly/etc. — not a tracked combat stat

    def _inc_agg(p, _depth=0, override=None):
        """Group incarnate effects by (stat, damage_type) and SUM the PvE variants.
        Grouping by damage_type keeps a +Def(All) like Barrier at 57.5% PER TYPE
        (not a bogus 172% across types). `override` (from a granted power's name)
        forces the stat for Alpha boosts whose effect_type is the generic DamageBuff."""
        agg = collections.defaultdict(float)
        for ef in p["effects"]:
            et = (EFFECT_TYPE[ef["effect_type"]]
                  if 0 <= ef["effect_type"] < len(EFFECT_TYPE) else None)
            if et == "GrantPower" and ef.get("summon") and _depth < 2:
                gp = inc_byname.get(ef["summon"])
                if gp:
                    ov = _silent_stat(ef["summon"])
                    if ov is None:        # not a combat stat (Run/Jump/Immob) — skip
                        continue
                    for k, v in _inc_agg(gp, _depth + 1, override=ov).items():
                        agg[k] += v
                continue
            if ef.get("to_who") == 1:       # FOE debuff (Judgement nuke / Interface proc), not a self/ally buff
                continue
            if ef.get("pv_mode") == 2:      # skip the PvP variant for a PvE build
                continue
            if override:                    # granted Alpha boost — its NAME says what it boosts
                stat = override
            elif et in INC_STATS:
                stat = et
            elif et == "Enhancement":
                mod = (EFFECT_TYPE[ef["et_modifies"]]
                       if 0 <= ef.get("et_modifies", -1) < len(EFFECT_TYPE) else None)
                if mod not in INC_ENH:
                    continue
                stat = "DamageBuff" if mod == "Damage" else mod
            else:
                continue
            val = ef["scale"] if abs(ef["scale"]) > 1e-9 else ef["magnitude"]
            if abs(val) < 1e-9:
                continue
            dt = (EDAMAGE[ef["damage_type"]]
                  if 0 <= ef["damage_type"] < len(EDAMAGE) else "None")
            agg[(stat, dt)] += val
        return agg

    def incarnate_stat_effects(p):
        return [{"effect": stat, "damage_type": dt, "value": round(v, 5)}
                for (stat, dt), v in sorted(_inc_agg(p).items())]

    incarnate_out = []
    for slot in INCARNATE_SLOTS:
        choices = []
        for p in sorted(inc_by_slot.get(slot, []), key=lambda x: x["display_name"]):
            choices.append({
                "full_name": p["full_name"],
                "display_name": p["display_name"],
                "desc": p.get("desc_short", ""),
                "effects": incarnate_stat_effects(p),
            })
        incarnate_out.append({"slot": slot, "powerset": "Incarnate." + slot,
                              "choice_count": len(choices), "choices": choices})

    # ---- write files ----
    def dump(name, obj):
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        print(f"  wrote {name}  ({os.path.getsize(path):,} bytes)")

    dump("archetypes.json", {"version": main_db["version"],
                             "issue": main_db["issue"],
                             "archetypes": arch_out})
    dump("powersets.json", powerset_payload)
    dump("powers.json", powers_out)
    dump("enhancement_sets.json", sets_out)
    dump("set_bonuses.json", set_bonuses_out)
    # ---- common_ios.json (single-aspect Invention IOs, not part of a set) ----
    common_ios = []
    for e in enhancements:
        if e["type_id"] == 2 and e["nid_set"] < 0:   # eType.InventO, no set
            aspects = sorted({enh_class_name(i) for i in e["enhances_ids"] if i > 0})
            common_ios.append({"uid": e["uid"], "name": e["name"],
                               "enhances": aspects, "boosts": piece_boosts(e, 50),
                               "image": e.get("image") or ""})
    # ---- special origin enhancements (Hamidon / Titan / Hydra "Origin" enhancements) ----
    # type_id 3 = SpecialO, no set. Multi-aspect at GRADE effectiveness (Maths.mhd EGE HO
    # row: 33.3%/20%/40%/60% per schedule), never IO-level-scaled — the classic debuffer
    # slotting (Enzyme = Acc+ToHitDeb+DefDeb) master builds run in Envenom/Weaken/VG.
    # Was entirely unmodeled until a user-shared master exposed it (2026-07-02).
    ho_row = (mult_grade or {}).get("HO") or [0.333, 0.20, 0.40, 0.60]
    special_ios = []
    for e in enhancements:
        if e["type_id"] != 3 or e["nid_set"] >= 0:
            continue
        boosts = []
        for b in e.get("boosts", []):
            sched = b["schedule"]
            if sched < 0 or sched > 3:
                continue
            aspect = (EENHANCE[b["aspect_id"]]
                      if 0 <= b["aspect_id"] < len(EENHANCE) else None)
            if not aspect or aspect == "None":
                continue
            mult = b["multiplier"] if abs(b["multiplier"]) > 0.01 else 1.0
            val = ho_row[sched] * mult
            if abs(val) > 1e-9:
                boosts.append({"aspect": aspect, "value": round(val, 6),
                               "schedule": sched})
        if boosts:
            aspects = sorted({enh_class_name(i) for i in e["enhances_ids"] if i > 0})
            special_ios.append({"uid": e["uid"], "name": e["name"],
                                "enhances": aspects, "boosts": boosts,
                                "image": e.get("image") or ""})
    dump("common_ios.json", {"common_ios": common_ios, "special_ios": special_ios})

    dump("summons.json", {"entities": {
        e["uid"]: {"display_name": e["display_name"],
                   "class_name": e["class_name"],
                   "powerset_full_names": e["powerset_full_names"],
                   "upgrade_powers": e["upgrade_powers"]}
        for e in main_db.get("entities", []) if e.get("uid")}})
    dump("incarnates.json", {"slots": incarnate_out})
    dump("modifier_tables.json", {"math_level_base": MATH_LEVEL_BASE,
                                  "tables": mod_tables})
    dump("maths.json", {"mult_io": mult_io, "mult_ed": mult_ed})
    dump("set_categories.json", {
        "categories": [{"id": i, "name": n, "short": set_type_shorts[i]}
                       for i, n in enumerate(set_type_names)],
        "enhancement_classes": [{"id": k, "name": v["name"], "short": v["short"]}
                                for k, v in sorted(eclasses.items())],
    })

    print("Done.")


if __name__ == "__main__":
    main()
