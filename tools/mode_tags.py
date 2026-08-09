"""What the client's effect-group `tags` field means, one entry at a time.

⚠⚠ THIS IS THE ONLY COPY. `add_wind_control.effects_from` reads it, so does
`reality_check_mode_tags.py`. A second copy of a rule is two things to drift -
the same rule that keeps `prereq_need` and `pool_rules` server-side.

WHY THIS FILE EXISTS
--------------------
`tags` is the field that gates the game's modes and meters, and nothing in this
project had read it until 2026-08-08. It carries FieryEmbrace on 349 groups,
Containment, Domination, Overpower, Defiance, the Scrapper crits, PowerBoostA/B
and ~150 more. Finding it was worth a lot; what came NEXT is the part that
needed care.

⚠⚠ A TAG IS NOT AUTOMATICALLY A GATE, AND THE FIRST FIX ASSUMED IT WAS.
The first version of `effects_from` skipped every tagged group. That is correct
for FieryEmbrace and wrong for `FireBlastBonusDoT`, which is simply the name the
client gives Blaze's own Fire damage-over-time - unconditional, in the power's
own help text, and dropping it would understate 29 Fire attacks. Three
mechanical tests were tried (does the tag name a Set_Mode / a power / does the
group carry a requires residue) and each got some of the 48 wrong in BOTH
directions: PowerBoostA names neither a mode called "PowerBoostA" nor a power,
yet it is a gate; "Damage" and "Taunt" name real powers, yet they are labels.

So this table is hand-adjudicated with the evidence beside each entry, and
`reality_check_mode_tags.py` HARD-FAILS on any tag that reaches a scored group
of a power we carry without an entry here. That is the project's standing
pattern for a vocabulary the data cannot classify for itself.

THE FIVE CLASSES
----------------
LABEL     - not a gate at all. The client is naming a part of the power for its
            own bookkeeping; the effect applies whenever the power does. TAKE IT.
PROB      - a real bonus with a chance the client STATES (a crit, Overpower).
            Weight by that chance; never skip and never take at full value.
MODE      - applies only while a mode is up, and the game states the duration
            and the recharge of the power that sets it, so the duty cycle is
            DERIVABLE. v39's `mode`/`host_recharge` machinery already prices
            exactly this shape.
SCENARIO  - real, and its uptime depends on how the character is played (a
            stack count, a meter, whether the target is already mezzed). The
            client cannot settle it; it needs one scenario constant, which is
            Joel's ruling - the same class as `mez_in` and `kb_in`.
DERIVED   - the engine already models this from another route, so taking the
            client's rows would DOUBLE-COUNT. Defiance is the whole class.
"""

LABEL, PROB, MODE, SCENARIO, DERIVED = "LABEL", "PROB", "MODE", "SCENARIO", "DERIVED"

# tag -> (class, one-line evidence). Every line is what the CLIENT or the game's
# own help says, never a wiki and never an inference from the tag's name.
TAGS = {
    # ---------- LABEL: the client naming a part of the power ----------
    "FireBlastBonusDoT": (LABEL, "Blaze/Fire Ball's own Fire DoT - chance 1.0, no "
                                 "requires, and the power's help states the DoT"),
    "Scorching Heat": (LABEL, "Fire Melee's own DoT on Combustion/Fire Sword, "
                              "0.1 scale over 3.1s, unconditional"),
    "Sonic Vibrations": (LABEL, "the -resistance every Sonic attack applies "
                                "(Howl, Dreadful Wail); in the power's help"),
    "SpinePoison": (LABEL, "Spines' own slow on Barb Swipe/Impale (movement "
                           "attribs, so the v30 exclusion drops it anyway)"),
    "SSDamage": (LABEL, "the Kheldian dwarf/nova form damage rows themselves"),
    "Resistances": (LABEL, "the Resistance power's own resistance"),
    "Crash": (LABEL, "Overload's end-of-buff crash - a Designer_Status penalty"),
    "GranitePenalties": (LABEL, "Granite Armor's own -recharge/-speed penalty, "
                                "which is exactly what the power does"),
    "ReduceIfKD": (LABEL, "knockback magnitude bookkeeping (v30 exclusion)"),
    "HybernateRoot": (LABEL, "Hibernate's self-root (v30 movement exclusion)"),
    "GeodeRoot": (LABEL, "Geode's self-root (v30 movement exclusion)"),
    "Bleed": (LABEL, "Storm Kick's small Lethal DoT"),
    "SoundBoost": (LABEL, "Sound Cannon's own stun magnitude"),
    "Uniqueness": (LABEL, "Vigilance bookkeeping"),
    "Apex Predator": (LABEL, "Call Locusts' own damage"),
    "Offensive": (LABEL, "Serum's own buff"),
    "MainTarget": (LABEL, "Soul Extraction main-target bookkeeping (scale 0.0)"),
    "initAbsorb": (LABEL, "Spirit Ward's initial absorb application"),
    "RestBuffs": (LABEL, "Rest's regeneration, which is what Rest is"),
    "RestPenalties": (LABEL, "Rest's self-immobilise"),
    "StealthOn": (LABEL, "Entropy Shield bookkeeping"),
    "Telekinesis": (LABEL, "the knock RESISTANCE Telekinesis applies to its own "
                           "target so the repel holds them - the power's own "
                           "mechanism, and knock attribs are a v30 exclusion"),
    "Taunt": (LABEL, "names the taunt component of a toggle, not a condition"),
    "InherentTaunt": (LABEL, "the inherent taunt an armour toggle carries"),
    "Damage": (LABEL, "sits on Alpha BOOST definitions (Damage_Common), which "
                      "are enhancement definitions rather than powers"),
    "Defense": (LABEL, "boost definitions (Defense_Buff_Rare)"),
    "Defenses": (LABEL, "Tactical Upgrade bookkeeping"),
    "Mez": (LABEL, "boost definitions (Confuse_Rare)"),
    "Endurance": (LABEL, "boost definitions (Endurance_Reduction_Common)"),
    "Heal": (LABEL, "boost definitions (Heal_Common)"),
    "Accuracy": (LABEL, "boost definitions"),
    "ToHit": (LABEL, "boost definitions"),
    "Range": (LABEL, "boost definitions"),
    "Movement": (LABEL, "boost definitions"),
    "Speed": (LABEL, "Kuji-In Rin's own +speed (v30 exclusion)"),
    "Cost": (LABEL, "Tesla Cage bookkeeping (Revoke_Power plumbing)"),

    # ---------- PROB: the client states the chance ----------
    "ScrapperCrit_ST": (PROB, "the Scrapper critical, chance 0.05 vs minions and "
                              "0.1 vs bosses - the client states both"),
    "ScrapperCrit_AoE": (PROB, "the same critical on AoEs, 0.05/0.1/0.15"),
    "CritSmall": (PROB, "critical chance 0.05, target-rank gated"),
    "CritLarge": (PROB, "critical chance 0.1-0.15, target-rank gated"),
    "CritPlayer": (PROB, "the PvP critical, chance 0.05"),
    "CriticalHit": (PROB, "Shuriken-class critical (chance unset = the inherent's)"),
    "CritActive": (PROB, "Savage Melee's active critical"),
    "StealthCrit": (PROB, "the Stalker's from-hide critical"),
    "ASTeamCrit": (PROB, "Assassin Strike team critical, chance 0.07"),
    "PvPCrit": (PROB, "the PvP critical variant, chance 0.2"),
    "Overpower": (PROB, "the Controller inherent: chance 0.2 (0.5 on some) of a "
                        "higher mez magnitude, stated on every group"),
    "Scrapper": (PROB, "the Scrapper crit on a POOL attack, chance 0.05"),
    "Stalker": (PROB, "the Stalker's pool-attack crit"),
    "Corruptor": (PROB, "Scourge on a pool attack - chance rises as the target's "
                        "health falls (`kHitPoints% target>` in the requires)"),
    "Controller": (PROB, "Containment on a pool attack"),
    "Dominator": (PROB, "the Dominator's pool-attack mez bonus, chance 0.1"),

    # ---------- MODE: the game states duration and recharge ----------
    "FieryEmbrace": (MODE, "Fiery Aura's Fiery Embrace click. 349 groups add Fire "
                           "damage to attacks; 124 clean logged swings show ZERO "
                           "Fire, because it applies only while the click is up"),
    "Domination": (MODE, "the Dominator inherent: a Set_Mode of 90s on a 200s "
                         "recharge, both stated by the client"),
    "PowerBoostA": (MODE, "Power Boost's `BoostPower` Set_Mode, 15s on a 60s "
                          "recharge - the amplified effect list"),
    "PowerBoostB": (MODE, "the second half of the same Power Boost window"),

    # ---------- SCENARIO: real, and blocked on one input ----------
    "Containment": (DERIVED, "⚠ RECLASSIFIED 2026-08-09. v36 already GROUNDS "
                             "Containment (paired equal-scale damage templates) "
                             "and weights it by the scenario's own ctrl_land as "
                             "the mezzed-target fraction. It was listed here as "
                             "blocked on a scenario input it already had. The "
                             "disposition is unchanged - skip - but the reason "
                             "is a double-count, exactly like Defiance"),
    "BuildStatic": (SCENARIO, "Electrical Blast's Static meter - a stack count"),
    "BuildFrenzy": (SCENARIO, "Savage Melee's Frenzy stacks"),
    "Contaminated": (SCENARIO, "Radiation Blast's Contaminated state on the target"),
    "Disintegrate": (SCENARIO, "Beam Rifle's Disintegrate token on the target"),
    "Disintegrate Bonus": (SCENARIO, "the bonus damage that token unlocks"),
    "EnergyRelease": (SCENARIO, "Energy Melee's Energy Focus stacks"),
    "EnergyStore": (SCENARIO, "the same Energy Melee store"),
    "ComboBuild": (SCENARIO, "Street Justice / Dual Blades combo level"),
    "ComboConsume": (SCENARIO, "spending that combo level"),
    "PerfectionofBody": (SCENARIO, "Martial Arts / Staff Perfection stacks"),
    "PerfectionofMind": (SCENARIO, "the same Perfection meter"),
    "PerfectionofSoul": (SCENARIO, "the same Perfection meter"),
    "NormalDebuffGC": (SCENARIO, "Bio Armor's adaptation stance - which stance is "
                                 "active is a play choice, not a build fact"),
    "OffensiveAdaptationGC": (SCENARIO, "the offensive stance of the same"),
    "SynergyFatigue": (SCENARIO, "the Fighting-pool cross-boost; conditional on "
                                 "OWNING Cross Punch, so this one is a build "
                                 "fact and is derivable once cross-power "
                                 "conditions exist"),

    # ---------- DERIVED: already modelled another way ----------
    "Defiance": (DERIVED, "v36 DERIVES Defiance from cast time and area. The "
                          "client's templates carry scale 0.0 and taking them "
                          "would double-count what the engine already adds"),
}


def tag_class(tag):
    """(class, evidence) or (None, None) when the tag has no adjudication."""
    return TAGS.get(tag, (None, None))


def group_disposition(tags):
    """How `effects_from` should treat a group carrying these tags.

    Returns "take" | "skip" | ("weight", chance-is-on-the-group) | "unknown".
    ⚠ The STRICTEST class wins when a group carries several: a group tagged both
    CritLarge and ScrapperCrit_ST is one critical, and a group that is both a
    label and a mode is gated.
    """
    if not tags:
        return "take"
    seen = [TAGS.get(t, (None, None))[0] for t in tags]
    if any(c is None for c in seen):
        return "unknown"
    for strict in (DERIVED, SCENARIO, MODE):
        if strict in seen:
            return "skip"
    if PROB in seen:
        return "weight"
    return "take"
