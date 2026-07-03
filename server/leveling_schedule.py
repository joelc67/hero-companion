"""
leveling_schedule.py — the EXACT per-level events a STANDARD archetype gets while leveling, so the
companion never suggests a choice that doesn't exist at a given level. Sourced from the Homecoming
wiki Leveling Chart + Enhancements page.

✓ CONFIRMED against the official Homecoming Leveling Chart (exact match, every level): through
level 30 a POWER on every even level and +2 SLOTS on every odd level (level 1 is special — your two
tier-1 powersets); from level 31 the slot grants shift to +3 at a time. The grants SUM TO 67 — the
game's slot budget.

Also from the chart (power-TYPE gates + build-relevant milestones):
  • POOL powers open at level 4 (first two), higher pool tiers at 14 — no pool power before 4.
  • EPIC / Ancillary powers open at 35 (then 38, 41, 44); Patrons unlock at 35 too.
  • IOs may be USED from level 7 (a level-10 IO is within the +3 window); common IOs come at levels
    divisible by 5 (10, 15, 20…); IO sets at any level once usable.
  • Free RESPEC trials become available at 24, 34, 44 — the companion can point a drifted player here.
  • Tier-9 primary at 26, tier-9 secondary at 30; Incarnate system at 50.
Per-power availability is already encoded in each power's `level_available` (Mids data); these gates
are the aggregate cross-check.

The FOUR Epic ATs — Peacebringer, Warshade, Arachnos Soldier, Arachnos Widow — do NOT follow this
ladder cleanly (Kheldian form powers, VEAT branching into Crab/Bane & Night Widow/Fortunata, and a
mid-career restructure/respec around level 20). They are handled as a separate track, not here.
"""
from collections import Counter

# A new power is granted at each of these levels (level 1 grants two — primary + secondary tier-1).
POWER_PICK_LEVELS = [1, 1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28,
                     30, 32, 35, 38, 41, 44, 47, 49]

# Enhancement slots granted AT each level. +2 on odd levels 3–29, +3 at a time from 31. Sums to 67.
SLOT_GRANTS = {
    3: 2, 5: 2, 7: 2, 9: 2, 11: 2, 13: 2, 15: 2, 17: 2, 19: 2, 21: 2, 23: 2, 25: 2, 27: 2, 29: 2,
    31: 3, 33: 3, 34: 3, 36: 3, 37: 3, 39: 3, 40: 3, 42: 3, 43: 3, 45: 3, 46: 3, 48: 3, 50: 3,
}
TOTAL_ADDED_SLOTS = sum(SLOT_GRANTS.values())     # == 67

_PICKS_AT = Counter(POWER_PICK_LEVELS)

# Build-relevant milestones from the chart's "Other" / availability columns — surfaced verbatim
# once, as the character reaches each level, so advice is anchored to what's actually unlocked.
MILESTONES = {
    4:  "Power Pools open — you can take your first pool power (travel, Fighting, Leadership…).",
    7:  "You can start slotting Invention Origin (IO) enhancements now.",
    14: "The higher pool tiers (3rd–5th pool powers) open up.",
    24: "First RESPEC trial (Terra Volta / Tree of Thorns) — and you already get a free respec every 10 "
        "levels. A respec re-picks powers in THIS level order (powersets stay locked); slots you then place freely.",
    26: "Your primary's tier-9 power is available.",
    30: "Your secondary's tier-9 power is available.",
    34: "Second respec trial available (up to 3 from trials total).",
    35: "Epic / Ancillary pools open (and Patron pools unlock via a Patron arc).",
    44: "Third respec trial available.",
    47: "Hamidon Origin (HO) enhancements can be slotted.",
    50: "Max level — the Incarnate system opens. Unlock order: Alpha (universal boost + level shift) → "
        "Judgement (AoE nuke) & Interface (proc debuff) → Lore (pets) & Destiny (team buff) → Hybrid. "
        "Incarnates keep working down to level 45 when you exemplar.",
}


# COST-SMART enhancement progression. The solver's end-game build is a pile of expensive IO SETS,
# only affordable near 50. Advising that mid-leveling is useless — so the companion recommends an
# AFFORDABLE path that converges on it. Core economics (Enhancement Prices + Enhancements wiki):
# SOs scale with level AND expire (±3 rule → re-buy every ~5 levels = a money-pit treadmill); COMMON
# IOs are PERMANENT (slot once); SETS are the end-game investment. So: cheap early → IOs as soon as
# usable (7) → sets at end-game. Never suggest set/expensive slotting the character can't afford yet.
ENH_PHASES = [
    (1,  6,  "Cheap TO/DO from stores, or leave slots bare — you out-level enhancements fast here, so don't overspend."),
    (7,  21, "Switch to COMMON IOs — they're permanent (no re-buy). This is the cost-smart move; SOs would expire every ~5 levels."),
    (22, 34, "Stay on common IOs and start banking cheap SET pieces from drops/merits. SOs still expire; IOs never do."),
    (35, 49, "Fold in IO SETS for their set bonuses — this is where your end-game build actually takes shape."),
    (50, 50, "Full IO-set build — the optimized end-game the solver targets."),
]


def enh_phase(level):
    for lo, hi, note in ENH_PHASES:
        if lo <= level <= hi:
            return note
    return ""


def so_cost(level):
    """Rough inf cost of a typical combat Single-Origin enhancement (Accuracy/Damage tier) at this level.
    SOs scale ~2304*(level+1)/2 and must be RE-BOUGHT as you out-level them (±3) — the treadmill IOs avoid."""
    return round(2304 * (level + 1) / 2)


# ── Epic Archetypes ─────────────────────────────────────────────────────────
# Kheldians (Peacebringer/Warshade) do NOT force-respec: they level from two big sets that hold
# their Nova/Dwarf FORMS, have inherent flight (L1) + combat flight (L10), and take NO epic pool.
# VEATs (Arachnos Soldier/Widow) DO force a RESPEC at level 24 — the branch point (Crab/Bane, Night
# Widow/Fortunata) — after which all six sets open and you rebuild from level 1. (Homecoming wiki.)
_KHELDIANS = {"Class_Peacebringer", "Class_Warshade"}
_VEATS = {"Class_Arachnos_Soldier", "Class_Arachnos_Widow"}


def eat_type(archetype):
    if archetype in _KHELDIANS:
        return "kheldian"
    if archetype in _VEATS:
        return "veat"
    return None


def milestone_for(archetype, level):
    """The milestone at this level, with Epic-AT corrections merged over the standard ladder."""
    if archetype in _VEATS:
        if level == 24:
            return ("🕸️ BRANCH POINT — you're required to RESPEC now and choose your career track "
                    "(Crab or Bane / Night Widow or Fortunata). All six power sets unlock and you "
                    "rebuild from level 1; a later respec can switch tracks.")
        return MILESTONES.get(level)             # VEATs keep the standard ladder incl. Patron pools @35
    if archetype in _KHELDIANS:
        if level == 1:
            return "You start with inherent flight — no travel pool needed. Nova & Dwarf forms come from your own power sets."
        if level == 10:
            return "Combat flight unlocks (flying in combat)."
        if level == 35:
            return None                          # Kheldians have NO epic/patron pool — suppress that
        return MILESTONES.get(level)
    return MILESTONES.get(level)


def level_events(level):
    """Exactly what a standard character gets AT this level: power picks, slots, gates, milestone, econ."""
    return {
        "level": level,
        "power_picks": _PICKS_AT.get(level, 0),      # how many power CHOICES here (2 at level 1)
        "slots": SLOT_GRANTS.get(level, 0),          # enhancement SLOTS to place here
        "io_ok": level >= 7,                         # can slot IOs from 7 (a level-10 IO is within +3)
        "common_io_level": level >= 10 and level % 5 == 0,   # common IOs come at 10,15,20,25…
        "milestone": MILESTONES.get(level),
        "enh_advice": enh_phase(level),              # cost-smart what-to-slot for this level band
    }


def walk_levels(max_level=50):
    """The full 1..max_level event list — the spine of the level-by-level walk."""
    return [level_events(l) for l in range(1, max_level + 1)]
