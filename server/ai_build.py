"""
ai_build.py - "Build this for me": ask Claude for a structured build, then
resolve every name to real Mids data and validate enhancements against each
power's accepted set categories (slot enforcement still applies).
"""

import difflib
import json
import re


# ---------------------------------------------------------------------------
# Goal lexicon — map common CoH build phrasing to concrete priorities so the
# build matches intent. Used both to (1) interpret + confirm the goal with the
# user before generating, and (2) inject confirmed priorities into the prompt.
# Each entry: label (shown to user), terms (synonyms matched in the goal text),
# focus (the concrete instruction handed to the build generator).
# ---------------------------------------------------------------------------
GOAL_TERMS = [
    {"label": "Fire-farm survival", "focus": (
        "A fire farm build is a DAMAGE-DEALING farmer (it must kill spawns) whose "
        "SURVIVAL COMES FROM ITS ATTACK SLOTS. This is the proven expert recipe:\n"
        "  * TAKE the full attack chain (most of the secondary blasts + an "
        "epic attack). Even if the user said 'no/low damage', a fire farmer "
        "still needs its attacks slotted — the attack sets ARE the defensive "
        "engine; do not skip them.\n"
        "  * Slot ALL THREE 6-piece WINTER sets — they are the backbone of "
        "fire-farm survival (each gives Fire/Cold RESISTANCE + Ranged/AoE "
        "DEFENSE). They need three DIFFERENT attack types, so TAKE a power of "
        "each as a mule: Superior Winter's Bite (a single-target RANGED blast, "
        "e.g. Gloom/Dark Blast), Superior Frozen Blast (a TARGETED-AoE, e.g. "
        "Tenebrous Tentacles/Night Fall), and Superior Avalanche (a PBAoE — TAKE "
        "THE TIER-9 NUKE, e.g. Blackstar, purely as the Avalanche mule even if "
        "you never fire it). Missing the third Winter set is the #1 reason a "
        "fire-farm build falls short on Fire resistance. Use purples (Apocalypse, "
        "Hecatomb, Ragnarok, Unbreakable Constraint) in the rest for recharge.\n"
        "  * Slot Fire Shield with a FULL Aegis resistance set to drive Fire "
        "RESISTANCE toward the 75% cap; add the Steadfast/Gladiator's +3% Def "
        "uniques. Keep Tough LIGHTLY slotted — do NOT chase Smashing/Lethal "
        "resistance; FIRE is the threat.\n"
        "  * Use Weave / Maneuvers / Combat Jumping (Luck of the Gambler) for "
        "defense + global recharge.\n"
        "TARGET both layers: ~45% Fire/Cold/AoE DEFENSE (hits miss) AND ~75% Fire "
        "RESISTANCE (cap). Ignore Energy/Negative/Psionic. (Totals exclude "
        "incarnates; Barrier/accolades are a bonus on top, not the plan.)"),
     "terms": ["fire farm", "fire farmer", "fire farming", "farm", "farming", "farmer"]},
    {"label": "Maximum survivability", "focus": "layer typed defense toward the "
     "45% soft cap and resistance toward the cap; raise Max HP and regen",
     "terms": ["tanky", "tank", "survivable", "survivability", "survive", "durable",
               "sturdy", "unkillable", "hard to kill", "tough as nails", "beefy"]},
    {"label": "Soft-capped defense (45%)", "focus": "reach 45% defense to the "
     "relevant types/positions",
     "terms": ["soft cap", "softcap", "soft-cap", "softcapped", "soft-capped",
               "capped defense", "45%"]},
    {"label": "Capped resistance", "focus": "drive resistance to the archetype cap "
     "(75%, or 90% Tanker/Brute) on the key types",
     "terms": ["res cap", "resist cap", "capped resist", "capped resistance",
               "resistance capped", "max resist"]},
    {"label": "Ranged defense", "focus": "soft-cap Ranged (and AoE) positional defense",
     "terms": ["ranged defense", "ranged def", "range defense", "ranged softcap"]},
    {"label": "Melee defense", "focus": "soft-cap Melee positional defense and S/L resist",
     "terms": ["melee defense", "melee def", "melee softcap"]},
    {"label": "High global recharge", "focus": "stack global recharge as high as "
     "possible (LotG: Def/+Global Recharge in every defense toggle, recharge set "
     "bonuses, Spiritual/Agility Alpha)",
     "terms": ["recharge", "global recharge", "cooldown", "cooldowns", "fast recharge"]},
    {"label": "Perma-Hasten", "focus": "reach ~+275% total recharge (Hasten "
     "3-slotted + global recharge from sets/LotG/Ageless) so Hasten is PERMANENT "
     "and never expires (so it never crashes); take and 3-slot Hasten",
     "terms": ["perma", "perma hasten", "perma-hasten", "permahasten", "perma haste"]},
    {"label": "Don't rely on Hasten", "focus": "The user does NOT want to use "
     "Hasten. CoH only allows ONE auto-fire power (Ctrl+click), and they reserve "
     "it for a key buff/heal (e.g. Fulcrum Shift or Transfusion), not Hasten — so "
     "Hasten would have to be a manual click with downtime/an end dip. Therefore: "
     "OMIT Hasten. Source global recharge entirely from ALWAYS-ON things — Luck "
     "of the Gambler: +Global Recharge in EVERY defense toggle, recharge set "
     "bonuses, and Ageless Destiny. Make sure the main buff/heal they'll auto-"
     "fire (Fulcrum Shift / Transfusion) is well slotted for recharge so it "
     "cycles fast. Do NOT count on Hasten to reach the goal.",
     "terms": ["no hasten", "without hasten", "hasten free", "hasten-free",
               "don't want hasten", "dont want hasten", "avoid hasten",
               "hate hasten", "don't rely on hasten", "dont rely on hasten",
               "without relying on hasten", "no perma hasten", "auto fire",
               "auto-fire", "auto cast", "autocast"]},
    {"label": "High damage output", "focus": "maximize damage: full damage sets, "
     "damage procs in attacks, and a damage Alpha (Musculature)",
     # NOTE: no bare "damage" / "damage output" — they false-match "damage
     # resist" and "no damage output". Use unambiguous damage phrasings only.
     "terms": ["dps", "high dps", "hard hitting", "hard-hitting", "hits hard",
               "burst", "nuke", "high damage", "big damage", "max damage",
               "maximum damage", "more damage", "lots of damage", "strong damage",
               "damage dealer", "deal damage"]},
    {"label": "Proc-heavy", "focus": "load attacks with damage procs (force-feedback, "
     "ATO procs, purple procs) over pure set bonuses",
     "terms": ["proc", "procs", "proc bomb", "proc-heavy", "proc heavy", "procced"]},
    {"label": "Endurance sustain", "focus": "secure positive net endurance: recovery "
     "set bonuses, Performance Shifter/Panacea, endurance reduction, Cardiac Alpha",
     "terms": ["endurance", "end heavy", "endurance hungry", "end hungry", "sustain",
               "blue bar", "recovery", "no end problems", "endurance management"]},
    {"label": "Regeneration / self-healing", "focus": "boost regeneration, Max HP and "
     "healing; recover lost HP quickly",
     "terms": ["regen", "regeneration", "self heal", "self-heal", "healing",
               "self healing", "recover", "recover fast", "bounce back"]},
    {"label": "Team support / buffs", "focus": (
        "TEAM SUPPORT: this character's job is to make the ally it supports hit "
        "HARDER, recharge FASTER and never run out of endurance — value that ABOVE "
        "the character's own offense/defense. So TAKE every signature team-buff / "
        "team-heal / debuff power in the support set (do NOT skip them — e.g. for "
        "Kinetics that means Transfusion, Siphon Speed, Speed Boost, Increase "
        "Density, Transference, Fulcrum Shift, and Siphon Power; other support sets "
        "have their own equivalents). SLOT them for their job: the recharge-gated "
        "CLICK buffs/heals/debuffs (Fulcrum Shift, Transfusion, Transference, Siphon "
        "Speed, etc.) get Accuracy (they MUST land) + heavy Recharge (so they are up "
        "as often as possible / as close to perma as you can — that is what drives "
        "the ally's damage and the team's uptime); fire-and-forget ally buffs (Speed "
        "Boost, Increase Density) need only ~1 slot. Frankenslot or use sets that "
        "add Recharge/Accuracy/EndMod/Heal as fits each power. Slotting that only "
        "helps THIS character's survival is secondary to buff uptime."),
     "terms": ["support", "buffer", "buff", "buffs", "team", "teammate", "team support",
               "team buffs", "debuff", "debuffs", "supportive"]},
    {"label": "Dual-box support (passive)", "focus": (
        "DUAL-BOX / SUPPORT BOT: this character supports an ally (e.g. a Brute) "
        "who deals the damage; it will not activate its own attacks. So ALL of "
        "its combat value comes from ALWAYS-ON effects — set bonuses, toggle/auto "
        "powers, and unique global IOs — which apply 100% whether or not a power "
        "is ever fired. OPTIMIZE FOR THAT: build the FULL normal character "
        "(including the attack powers) and, in every power, choose the "
        "enhancements that MAXIMIZE the always-on set bonuses serving the goal — "
        "an attack power's slots are just bonus real estate, treated exactly like "
        "any other slot (e.g. for a fire farm, Gloom/Tenebrous Tentacles/"
        "Blackstar carry Superior Winter's Bite/Frozen Blast/Avalanche for their "
        "Fire/Cold resistance + Ranged/AoE defense bonuses). The fact that you "
        "won't press the attacks changes NOTHING about how you slot them. The "
        "ONLY differences from a normal build: (1) NEVER pick 'Chance for…' / "
        "proc / pure-damage-proc pieces — they only do something when you fire "
        "the power, so they are wasted here; always choose the set piece that "
        "advances a useful set bonus instead; (2) the single auto-fire slot goes "
        "to a buff/heal (Fulcrum Shift / Transfusion), and skip Hasten. Also take "
        "the ally buff/heal powers and the always-on mitigation toggles (Tough, "
        "Weave, Maneuvers, Combat Jumping)."),
     "terms": ["dual box", "dual-box", "dualbox", "duo box", "two box", "second account",
               "two accounts", "buff bot", "buffbot", "support bot", "bot account",
               "mule", "follows a brute", "follows the brute", "follow the brute",
               "follows my brute", "supports a brute", "supports my brute"]},
    {"label": "Strong AoE", "focus": "favor AoE attacks and AoE-friendly procs/recharge",
     "terms": ["aoe", "area damage", "aoe damage", "spawns", "clear spawns"]},
    {"label": "Control / lockdown", "focus": "maximize control magnitude/duration and "
     "recharge for lockdown",
     "terms": ["control", "lockdown", "mez", "hold", "holds", "stuns", "immobilize"]},
    {"label": "Mez protection", "focus": "include status/mez protection (Clarion "
     "Destiny, mez-protection IOs/powers)",
     "terms": ["mez protection", "status protection", "mez prot", "hold protection",
               "status protect", "anti-mez"]},
    {"label": "Exemplar-friendly", "focus": "use sets that grant their bonuses at low "
     "levels so they hold while exemplared",
     "terms": ["exemp", "exemplar", "exemping", "exemplaring", "lowbie", "low level content"]},
    {"label": "Solo capable", "focus": "balance enough survivability and damage to solo",
     "terms": ["solo", "soloing", "solo-friendly", "solo friendly", "solo capable"]},
    {"label": "PvP-oriented", "focus": "account for PvP diminishing returns; favor PvP "
     "IO globals and typed defense/HP/recharge",
     "terms": ["pvp", "pvp build", "arena", "zone pvp", "player vs player"]},
    {"label": "Psionic protection", "focus": "add Psionic defense and resistance",
     "terms": ["psi", "psionic", "psy", "psionics"]},
    {"label": "Accuracy / to-hit", "focus": "ensure high accuracy/to-hit (Kismet +ToHit, "
     "Tactics, accuracy in attacks)",
     "terms": ["accuracy", "to hit", "tohit", "to-hit", "never miss", "hit things"]},
]


# Which set-bonus stats each goal priority actually needs. The server uses this
# to tell the AI WHICH real sets grant those bonuses — otherwise it picks sets
# blind to their bonuses (e.g. stacking S/L-res sets on a fire farm and leaving
# Fire resistance stranded).
LABEL_BONUS_NEEDS = {
    "Fire-farm survival": [("Resistance", "Fire"), ("Resistance", "Cold"),
                           ("Resistance", "Smashing"), ("Resistance", "Lethal"),
                           ("Defense", "Fire"), ("Defense", "AoE"),
                           ("Defense", "Ranged")],
    "Capped resistance": [("Resistance", "Smashing"), ("Resistance", "Lethal"),
                          ("Resistance", "Fire"), ("Resistance", "Energy")],
    "Maximum survivability": [("Defense", "Smashing"), ("Defense", "Lethal"),
                              ("Resistance", "Smashing"), ("Resistance", "Lethal")],
    "Soft-capped defense (45%)": [("Defense", "Smashing"), ("Defense", "Lethal"),
                                  ("Defense", "Energy")],
    "Ranged defense": [("Defense", "Ranged"), ("Defense", "AoE")],
    "Melee defense": [("Defense", "Melee")],
    "Psionic protection": [("Resistance", "Psionic"), ("Defense", "Psionic")],
}


# Concrete stat targets each goal priority implies, for the constraint solver.
# Merged (max per stat) across all matched labels. Percentages.
LABEL_TARGETS = {
    "Fire-farm survival": {"defense": {"Fire": 45, "Cold": 45, "AoE": 45},
                           "resistance": {"Fire": 75, "Smashing": 60, "Lethal": 60,
                                          "Cold": 45}, "recharge": 50},
    "Maximum survivability": {"defense": {"Smashing": 45, "Lethal": 45, "Fire": 45,
                                          "Cold": 45, "Energy": 45, "Negative": 45},
                              "resistance": {"Smashing": 50, "Lethal": 50}},
    "Soft-capped defense (45%)": {"defense": {"Smashing": 45, "Lethal": 45,
                                              "Energy": 45, "Negative": 45}},
    "Capped resistance": {"resistance": {"Smashing": 75, "Lethal": 75, "Fire": 75,
                                         "Cold": 75}},
    "Ranged defense": {"defense": {"Ranged": 45, "AoE": 45}},
    "Melee defense": {"defense": {"Melee": 45}},
    "High global recharge": {"recharge": 80},
    "Perma-Hasten": {"recharge": 100},
    "Endurance sustain": {"recovery": 50},
    "Regeneration / self-healing": {"regen": 150},
    "Psionic protection": {"resistance": {"Psionic": 40}, "defense": {"Psionic": 30}},
}


# Damage/position types the user can name in a goal ("soft/hard cap on fire, lethal").
_TYPE_WORDS = {
    "smashing/lethal": ["Smashing", "Lethal"], "smashing": ["Smashing"],
    "lethal": ["Lethal"], "s/l": ["Smashing", "Lethal"], "fire": ["Fire"],
    "cold": ["Cold"], "energy": ["Energy"], "negative energy": ["Negative"],
    "negative": ["Negative"], "toxic": ["Toxic"], "psionic": ["Psionic"],
    "psi": ["Psionic"], "melee": ["Melee"], "ranged": ["Ranged"], "aoe": ["AoE"],
}
_RES_TYPES = {"Smashing", "Lethal", "Fire", "Cold", "Energy", "Negative", "Toxic", "Psionic"}


def _explicit_cap_targets(goal, out, res_cap=75):
    """Honor explicitly-named cap requests like 'soft/hard cap on fire, lethal':
    soft cap -> 45% DEFENSE on those types; hard cap -> res_cap% RESISTANCE on them
    (so the user's own stated targets are met, not just the generic goal preset)."""
    g = " " + (goal or "").lower() + " "
    if "cap" not in g and "max " not in g:
        return
    soft = "soft" in g          # catches "soft cap", "soft/hard cap", "softcap"
    hard = "hard" in g          # catches "hard cap", "soft/hard cap", "hardcap"
    if not (soft or hard):      # a bare "cap"/"max" request -> aim for both
        soft = hard = True
    types = []
    for word, ts in _TYPE_WORDS.items():
        # plain word boundaries — a "/" between types ("fire/lethal", "s/l") is a
        # SEPARATOR, so both sides must still match.
        if re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", g):
            types += ts
    types = list(dict.fromkeys(types))
    if not types:
        return
    want_def = soft or not hard         # "soft cap"=def; bare/"max" cap = both
    want_res = hard or not soft
    for t in types:
        if want_def:
            out.setdefault("defense", {})[t] = max(out.get("defense", {}).get(t, 0), 45)
        if want_res and t in _RES_TYPES:
            out.setdefault("resistance", {})[t] = max(out.get("resistance", {}).get(t, 0), res_cap)


def goal_targets(goal, res_cap=75):
    """Merge the matched goal priorities into a concrete target profile for the
    solver (max per stat across labels), then honor any explicitly-named cap
    requests (e.g. 'soft/hard cap on fire, lethal'). Returns {} if nothing specific."""
    labels = [m["label"] for m in interpret_goal(goal)["matched"]]
    out = {"defense": {}, "resistance": {}}
    for lb in labels:
        spec = LABEL_TARGETS.get(lb, {})
        for kind in ("defense", "resistance"):
            for t, v in spec.get(kind, {}).items():
                out[kind][t] = max(out[kind].get(t, 0), v)
        for fld in ("recharge", "recovery", "regen", "max_hp", "tohit"):
            if fld in spec:
                out[fld] = max(out.get(fld, 0), spec[fld])
    _explicit_cap_targets(goal, out, res_cap)
    if not out["defense"]:
        del out["defense"]
    if not out["resistance"]:
        del out["resistance"]
    return out


# Dedicated buff/debuff "support" powersets (Defender/Corruptor primaries,
# Controller/Mastermind secondaries). A character with one of these is a SUPPORT —
# in a "fire farm" context they BUFF the farmer, they are not the farmer themselves.
SUPPORT_SETS = {
    "kinetics", "cold domination", "thermal radiation", "empathy", "force field",
    "sonic resonance", "radiation emission", "storm summoning", "trick arrow",
    "dark miasma", "nature affinity", "time manipulation", "traps", "poison",
    "pain domination", "electrical affinity", "marine affinity",
}

# ── Build presets: pick CONTENT + ROLE instead of typing a goal ──────────────
# Each CONTENT preset is the survival/utility floor for that kind of play; the ROLE
# tilts it and selects the solver's role multipliers + perk dial. Archetype caps are
# applied via res_cap, so a Brute fire-farm caps fire res at 90, a Defender at 75.
# "CAP" in a resistance spec means "this AT's resistance cap". A free-text goal stays
# OPTIONAL — it just layers extra named caps on top via goal_targets().

# CURRENT-META targets (model v24, calibrated against the 2,255-build Sovereign
# corpus + the master builder's stated doctrine): ~35% defense to Smashing/Lethal/
# Fire/Cold (TYPED) for most characters — positional-armor characters take 35%
# Melee/Ranged/AoE instead (preset_targets swaps this in) — with the freed slots
# spent on PROCS, which the engine now prices. The OLD 45%-softcap style remains
# reachable via the "classic softcap" goal text. Fire farm keeps its hard fire
# floor — farm spawns are a special case where the cap still rules.
CONTENT_PRESETS = {
    "fire_farm": {
        "label": "Fire Farm",   # farmer (damage/tank) OR support mule (buffer/healer on a team / dual-box) — role decides
        # survival FLOOR: Fire + S/L to BOTH the 45% defense soft cap AND the AT's
        # resistance hard cap (fire-farm enemies hit fire + smashing/lethal). This is
        # non-negotiable even for the damage-dealer role — you tank the spawn first.
        "defense": {"Fire": 45, "Smashing": 45, "Lethal": 45, "Cold": 45, "AoE": 45},
        "resistance": {"Fire": "CAP", "Smashing": "CAP", "Lethal": "CAP", "Cold": 45},
        "recharge": 50, "recovery": 50,
    },
    "itrial": {                     # league / incarnate content: +3/+4 enemies
        "label": "League / iTrials",
        "defense": {"Smashing": 35, "Lethal": 35, "Fire": 35, "Cold": 35},
        "resistance": {"Smashing": 50, "Lethal": 50, "Energy": 40, "Negative": 40},
        "recharge": 90, "recovery": 50,
    },
    "team": {                       # team covers your survival; you bring uptime
        "label": "Team play",
        "defense": {"Smashing": 35, "Lethal": 35, "Fire": 35, "Cold": 35},
        "recharge": 80, "recovery": 30,
    },
    "general": {                    # everyday solo / AV soloing: balanced
        "label": "General / solo",
        "defense": {"Smashing": 35, "Lethal": 35, "Fire": 35, "Cold": 35},
        "resistance": {"Smashing": 50, "Lethal": 50},
        "recharge": 70, "recovery": 40,
    },
    "av": {                         # hard single targets (EB/AV): tank it + sustain ST DPS
        "label": "EB / AV (hard targets)",
        # typed 35 + a bit of E/N (AV mixed damage) + high recharge for the chain.
        "defense": {"Smashing": 35, "Lethal": 35, "Fire": 35, "Cold": 35,
                    "Energy": 30, "Negative": 30},
        "resistance": {"Smashing": 50, "Lethal": 50},
        "recharge": 95, "recovery": 40,
    },
}

# Armor sets whose native defense is POSITIONAL — characters built on these chase
# 35% Melee/Ranged/AoE instead of typed S/L/F/C (the typed targets would fight the
# armor's own geometry). Matched on the set's short name, lowercased.
POSITIONAL_ARMOR_SETS = {
    "super_reflexes", "shield_defense", "ninjitsu", "ninja_training",
    "widow_training", "night_widow_training", "fortunata_training",
    "energy_aura", "scrapper_ninjitsu", "stalker_ninjitsu",
}

_POSITIONAL_35 = {"Melee": 35, "Ranged": 35, "AoE": 35}
_CLASSIC_RE = None


def wants_classic_softcap(goal):
    """The old 45%-softcap style, on request: 'classic softcap', '45 def', 'old meta'…"""
    import re as _re
    global _CLASSIC_RE
    if _CLASSIC_RE is None:
        _CLASSIC_RE = _re.compile(r"classic\s+soft\s*cap|old\s+meta|45%?\s*(def|defense)|soft\s*cap\s*everything", _re.I)
    return bool(goal and _CLASSIC_RE.search(goal))


_CLASSIC_DEF = {"Smashing": 45, "Lethal": 45, "Fire": 45, "Cold": 45, "Ranged": 45, "AoE": 45}


def positional_build(primary=None, secondary=None):
    """True when either main set is a positional-defense armor."""
    for ps in (primary, secondary):
        short = ((ps or "").split(".")[-1]).lower()
        if short in POSITIONAL_ARMOR_SETS:
            return True
    return False

# Role -> solver role list (ROLE_DEFS keys), perk dial, and perk floors it raises.
# tank also pushes resistances toward the AT cap + adds HP.
ROLE_PRESETS = {
    "buffer": {"label": "Buffer / Support", "roles": ["buffing", "debuffing", "survival"],
               "perk_focus": "recharge", "floors": {"recharge": 90, "recovery": 50}},
    "support": {"label": "Buffer / Support", "roles": ["buffing", "debuffing", "survival"],
                "perk_focus": "recharge", "floors": {"recharge": 90, "recovery": 50}},  # alias of buffer

    "healer": {"label": "Healer", "roles": ["healing", "survival"],
               "perk_focus": "regen", "floors": {"regen": 150, "recovery": 50, "recharge": 70}},
    "damage": {"label": "Damage dealer", "roles": ["damage", "survival"],
               # AoE throughput is recharge-bound (cycle your AoEs faster), so the
               # damage dealer pushes recharge hard — that's the dominant AoE lever.
               "perk_focus": "recharge", "floors": {"recharge": 100}},
    "tank":   {"label": "Tank / Survivor", "roles": ["survival"],
               # floors are PERCENT like every sibling (recharge 100 = +100%):
               # +30% max HP was written as 0.30 and normalized to +0.3% — a
               # latent units bug surfaced by the HitPoints bonus-unit fix.
               "perk_focus": "resistance", "floors": {"max_hp": 30},
               "res_to_cap": True},
    # A Controller's lifeblood is RECHARGE (perma-control + debuff uptime), NOT regen/heal —
    # locked-down enemies are the survival. Control + debuff IO sets, high recharge.
    "controller": {"label": "Controller / Lockdown", "roles": ["controlling", "debuffing", "survival"],
                   "perk_focus": "recharge", "floors": {"recharge": 100, "recovery": 40}},
    "control":    {"label": "Controller / Lockdown", "roles": ["controlling", "debuffing", "survival"],
                   "perk_focus": "recharge", "floors": {"recharge": 100, "recovery": 40}},  # alias (discovery uses "control")
    "debuffer":   {"label": "Debuffer", "roles": ["debuffing", "controlling", "survival"],
                   "perk_focus": "recharge", "floors": {"recharge": 90, "recovery": 40}},
    # MIXED ROLE (Joel's design ruling, 2026-07-08): the honest choice for players
    # who don't specialize — the players the old silent "damage dealer" default
    # used to absorb. Content-baseline ("balanced") targets with moderate uptime
    # floors and no role tilt beyond survival; the scorer's role lens falls
    # through to raw physics (first_principles.role_contribution's no-weight
    # fallback = the whole-team-in-one-character generalist objective). Rides the
    # existing v23 focus-split machinery — no champion or model dependency.
    "mixed": {"label": "Mixed role / Generalist", "roles": ["survival"],
              "perk_focus": None, "floors": {"recharge": 70, "recovery": 40}},
}


def preset_targets(content, role, res_cap=75, exposure=None,
                   primary=None, secondary=None, goal=None):
    """Compose a CONTENT preset + ROLE (+ EXPOSURE) into a concrete solver request:
    {"targets": {...}, "roles": [...], "perk_focus": ...}. No free text needed.

    v24 meta targets: the typed S/L/F/C-35 baseline swaps to POSITIONAL 35 when the
    build's armor is positional-natured (pass primary/secondary), and the whole
    defense vector lifts to the classic 45 profile when the goal asks for it.
    The lowered 35 baseline is safe now because the engine PRICES PROCS — the slots
    the old 45-proxy would have spent on marginal defense sets buy real damage.

    NOTE on role-first: the survival def/res targets remain HARVEST proxies, not
    literal goals — the role KIND-MULTIPLIERS (ROLE_DEFS) still tilt which bonuses
    get harvested."""
    base = CONTENT_PRESETS.get(content) or {}
    rolespec = ROLE_PRESETS.get(role) or {}
    out = {"defense": {}, "resistance": {}}
    for t, v in base.get("defense", {}).items():
        out["defense"][t] = v
    # meta-baseline reshaping (never touches fire_farm's hard 45 floor)
    _meta_quad = all(out["defense"].get(t) == 35 for t in ("Smashing", "Lethal", "Fire", "Cold"))
    if goal and wants_classic_softcap(goal):
        for t, v in _CLASSIC_DEF.items():
            out["defense"][t] = max(out["defense"].get(t, 0), v)
    elif _meta_quad and positional_build(primary, secondary):
        for t in ("Smashing", "Lethal", "Fire", "Cold"):
            del out["defense"][t]
        out["defense"].update(_POSITIONAL_35)
    # EXPOSURE shapes the DEFENSE vector via the achievable POSITIONAL route: a front-
    # liner is hit in melee (aim Melee def), a backliner by ranged/AoE (aim Ranged+AoE).
    if exposure == "front":
        out["defense"]["Melee"] = max(out["defense"].get("Melee", 0), 45)
    elif exposure == "back":
        out["defense"]["Ranged"] = max(out["defense"].get("Ranged", 0), 45)
        out["defense"]["AoE"] = max(out["defense"].get("AoE", 0), 45)
    for t, v in base.get("resistance", {}).items():
        out["resistance"][t] = res_cap if v == "CAP" else min(v, res_cap)
    for fld in ("recharge", "recovery", "regen", "max_hp", "tohit"):
        if fld in base:
            out[fld] = base[fld]
    # role raises the relevant perk floors (max), never lowers the content baseline
    for fld, v in rolespec.get("floors", {}).items():
        out[fld] = max(out.get(fld, 0), v)
    # tank pushes every named resistance toward the AT cap
    if rolespec.get("res_to_cap"):
        for t in list(out["resistance"]):
            out["resistance"][t] = res_cap
    if not out["defense"]:
        del out["defense"]
    if not out["resistance"]:
        del out["resistance"]
    # The solver's accuracy-valuation term needs to know WHAT it fights (the
    # +N base-hit table lives in first_principles.SCENARIOS, keyed like the
    # content presets). Ride along in the targets dict so every solve path —
    # /build/solve, autopick, champions refresh — gets it without new plumbing;
    # normalize_targets ignores unknown fields.
    if content in CONTENT_PRESETS:
        out["scenario"] = content
    return {"targets": out, "roles": rolespec.get("roles", ["survival"]),
            "perk_focus": rolespec.get("perk_focus")}


# ── Incarnate recommender ────────────────────────────────────────────────────
# Gap-aware + content/role/target-framed. Always-on slots (Alpha/Interface/Hybrid/
# Lore) are weighed first because they push past slotting limits (Alpha ignores ED).
# The model, per the user's experience:
#   - short of a survival cap  -> close it with the always-on path (Resilient/Cardiac
#     res, Agility/Nerve def) — slotting tops out at ED, the Alpha goes past it.
#   - cap already MET          -> redirect to offense/utility (Musculature damage).
#   - support role             -> weight TEAM value (Barrier group shield, -regen).
#   - EB/AV target             -> -Regen (Diamagnetic) + debuff-resist Destiny + control.
# We have the choice NAMES/descriptions but not magnitudes, so each pick carries a
# REASON (direction/priority), not fake precision.

def _alpha(fam, branch="Core"):    return f"Incarnate.Alpha.{fam}_{branch}_Paragon"
def _judg(fam, branch="Radial"):   return f"Incarnate.Judgement.{fam}_{branch}_Final_Judgement"
def _iface(fam):                   return f"Incarnate.Interface.{fam}_Total_Radial_Conversion"
def _dest(fam, branch="Core"):     return f"Incarnate.Destiny.{fam}_{branch}_Epiphany"
def _hybrid(fam, branch="Radial"):
    return (f"Incarnate.Hybrid.{fam}_{branch}_Embodiment" if fam in ("Assault", "Control")
            else f"Incarnate.Hybrid.{fam}_Genome_8")
def _lore(fam="Cimeroran"):        return f"Incarnate.Lore.{fam}_Total_Radial_Improved_Ally"


_INC_MAG = None


def _inc_magnitudes():
    """full_name -> {stat: peak value} from the parsed incarnate effects (loaded once)."""
    global _INC_MAG
    if _INC_MAG is None:
        _INC_MAG = {}
        try:
            import json
            import os
            import sys
            if getattr(sys, "frozen", False):
                base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
            else:
                base = os.path.join(os.path.dirname(__file__), "..")
            path = os.path.join(base, "data", "incarnates.json")
            for s in json.load(open(path, encoding="utf-8"))["slots"]:
                for c in s["choices"]:
                    best = {}
                    for e in (c.get("effects") or []):
                        best[e["effect"]] = max(best.get(e["effect"], 0), e["value"])
                    if best:
                        _INC_MAG[c["full_name"]] = best
        except Exception:  # noqa: BLE001
            _INC_MAG = {}
    return _INC_MAG


def _mag_str(full_name):
    """Short headline magnitude, e.g. '+45% damage' / '+33% resistance · +20% to-hit'."""
    label = {"DamageBuff": "damage", "Resistance": "resistance", "Defense": "defense",
             "RechargeTime": "recharge", "Recovery": "recovery", "Regeneration": "regen",
             "Healing": "heal", "ToHit": "to-hit", "Accuracy": "accuracy",
             "Endurance": "endurance", "HitPoints": "max HP", "Absorb": "absorb"}
    best = _inc_magnitudes().get(full_name) or {}
    parts = [f"+{round(v * 100)}% {label[k]}"
             for k, v in sorted(best.items(), key=lambda x: -x[1]) if k in label and v > 0][:2]
    return " · ".join(parts)


def _worst_gap(targets, totals, kind, min_target=0):
    """Largest UNMET gap (target - achieved) for a def/res kind, and the type.
    `min_target` restricts to types aimed at/above a floor — so a 'survival hole'
    is measured against the SOFT/HARD-cap threats (e.g. Fire/S-L res at the cap),
    not a secondary target (e.g. Cold res 45) that shouldn't force resilience-first."""
    worst, ty = 0.0, None
    for t, tv in (targets.get(kind) or {}).items():
        if not isinstance(tv, (int, float)) or tv < min_target:
            continue
        cur = (totals.get(kind) or {}).get(t, {}).get("value", 0)
        if tv - cur > worst:
            worst, ty = tv - cur, t
    return worst, ty


def recommend_incarnates(archetype, content, role, totals, targets=None, res_cap=75):
    """Return [{slot, full_name, display, why, always_on}] — the optimal full set
    assuming all slots are unlocked. `content` in fire_farm|itrial|team|general|av;
    `role` in damage|buffer|healer|tank (None = infer-light)."""
    targets = targets or {}
    totals = totals or {}
    role = role or "damage"
    controller = role in ("controller", "control", "debuffer")
    support = role in ("buffer", "healer") or controller   # league force-multipliers → Barrier/Support Hybrid
    av = content == "av"
    # Verified mechanic (homecoming.wiki/Limits + forum): NO incarnate raises the
    # resistance CAP — overcap resistance only helps as a -res-DEBUFF cushion (the cap
    # is applied AFTER summing buffs+debuffs). So whether stacking resilience past cap is
    # worth it depends on whether the CONTENT debuffs:
    debuff_content = content in ("itrial", "team", "av")   # league/iTrial/AV: -res/-def common -> overcap cushion is real
    farm_content = content == "fire_farm"                  # raw damage, ~no debuffs -> overcap res is dead weight; sustain instead
    is_mm = archetype == "Class_Mastermind"   # a MM's damage is its henchmen — Musculature/Lore/Assault buff the PETS
    rech_cur = (totals.get("recharge") or {}).get("value", 0)
    rech_tgt = targets.get("recharge", 0)
    # a survival "hole" = far below a SOFT/HARD cap threat (res aimed near the hard cap,
    # def aimed near the 45 soft cap) — not a secondary target like Cold res 45.
    res_gap, res_ty = _worst_gap(targets, totals, "resistance", min_target=res_cap - 10)
    def_gap, def_ty = _worst_gap(targets, totals, "defense", min_target=40)
    rech_gap = max(0.0, rech_tgt - rech_cur)
    RES_HOLE = 10.0    # res this far below cap is a real survival hole (close it first)
    DEF_HOLE = 10.0
    # Survival is "met" if EITHER layer is at its cap — a build pinned at the res HARD
    # cap survives on resistance even with sub-soft-cap defense, so a defense gap then
    # isn't a hole that should override the content-aware pick.
    res_capped = res_gap <= RES_HOLE
    def_capped = def_gap <= DEF_HOLE
    survival_met = res_capped or def_capped
    recs = []

    # ALPHA — decision tree:
    #   far below caps -> close the gap (raw mitigation needed, ANY content)
    #   at caps + DEBUFF content (iTrial/league/AV) -> Resilient for the overcap cushion
    #   at caps + FIRE FARM (no debuffs) -> sustain (buff frequency + heal), NOT more res
    #   recharge starved -> Spiritual; else support->Vigor, damage->Musculature
    #   CONTROLLER/DEBUFFER -> Spiritual first: recharge (perma-control) IS the survival.
    if controller:
        recs.append({"slot": "Alpha", "full_name": _alpha("Nerve"),
                     "display": "Nerve Core Paragon",
                     "why": "controls must LAND and hold longer — Nerve adds accuracy + hold duration + defense past ED. "
                            "Your perma-control recharge comes from Ageless Destiny, so the Alpha firms up accuracy/"
                            "defense instead. (Prefer to stack recharge? Spiritual works too — both are valid.)",
                     "always_on": True})
    elif not survival_met and res_gap >= def_gap:
        recs.append({"slot": "Alpha", "full_name": _alpha("Resilient"),
                     "display": "Resilient Core Paragon",
                     "why": f"{res_ty} resistance is ~{round(res_gap)}% short of your {res_cap:.0f}% cap and defense "
                            "isn't soft-capped either — you're still eating that damage, so Resilient's always-on res "
                            "(past ED) closes a real survival hole.",
                     "always_on": True})
    elif not survival_met:
        recs.append({"slot": "Alpha", "full_name": _alpha("Agility"),
                     "display": "Agility Core Paragon",
                     "why": f"{def_ty} defense is ~{round(def_gap)}% short and resistance isn't capped either — Agility "
                            "adds defense (and recharge) past the slotting limit to firm up the survival floor.",
                     "always_on": True})
    elif support and debuff_content:
        recs.append({"slot": "Alpha", "full_name": _alpha("Resilient"),
                     "display": "Resilient Core Paragon",
                     "why": "you're at cap, but league/iTrial enemies stack -resistance — Resilient banks raw resistance "
                            "ABOVE your cap, a cushion that keeps you pinned at the cap when debuffs land.",
                     "always_on": True})
    elif support and farm_content:
        recs.append({"slot": "Alpha", "full_name": _alpha("Spiritual"),
                     "display": "Spiritual Core Paragon",
                     "why": "a fire farm throws raw damage, not -resistance, so overcap resistance is dead weight — "
                            "survivability here is buff frequency + healing, and Spiritual speeds both (recharge + heal).",
                     "always_on": True})
    elif farm_content:
        recs.append({"slot": "Alpha", "full_name": _alpha("Musculature"),
                     "display": "Musculature Core Paragon",
                     "why": "survival's already capped, so the Alpha goes to offense. Musculature's +damage and +to-hit "
                            "(past ED) raise your attacks' and Burn's BASE damage and help land hits on +4s. "
                            "⚖️ BUT if you proc-bomb (stack %Damage procs in your auras/AoEs), pick Spiritual instead: "
                            "proc damage is FIXED — it doesn't scale with +damage — so recharge wins by cycling attacks "
                            "and procs faster. Both are top-tier farmer Alphas; the choice tracks how proc-heavy you build.",
                     "always_on": True})
    elif rech_cur < 60 or (support and rech_cur < 70):
        recs.append({"slot": "Alpha", "full_name": _alpha("Spiritual"),
                     "display": "Spiritual Core Paragon",
                     "why": f"recharge is the limiter at +{round(rech_cur)}% (buff/attack uptime, and AoE throughput "
                            "is recharge-bound) — Spiritual adds recharge past ED.",
                     "always_on": True})
    elif support:
        recs.append({"slot": "Alpha", "full_name": _alpha("Vigor"),
                     "display": "Vigor Core Paragon",
                     "why": "support role with survival + recharge handled — Vigor boosts heal + accuracy + endurance.",
                     "always_on": True})
    elif is_mm:
        recs.append({"slot": "Alpha", "full_name": _alpha("Musculature"),
                     "display": "Musculature Core Paragon",
                     "why": "your damage is your henchmen — Musculature's +damage flows to the PETS "
                            "(they inherit your Alpha) and ignores ED, so it's the biggest pet-DPS lever.",
                     "always_on": True})
    else:
        recs.append({"slot": "Alpha", "full_name": _alpha("Musculature"),
                     "display": "Musculature Core Paragon",
                     "why": "survival floor already met — redirect the Alpha to pure damage; "
                            "Musculature ignores ED for a real DPS ramp.",
                     "always_on": True})

    # INTERFACE — content-dependent (validated across 13 master builds): Reactive (-res +
    # Fire DoT) for FARM/trash AoE clear; Degenerative (-max-hp / -regen) is the general &
    # hard-target default (what the masters actually ran outside farming); Diamagnetic vs AV.
    if av:
        recs.append({"slot": "Interface", "full_name": _iface("Diamagnetic"),
                     "display": "Diamagnetic Total Radial",
                     "why": "vs an AV, -Regeneration is the single biggest lever — it counters the AV's regen wall.",
                     "always_on": True})
    elif farm_content:
        recs.append({"slot": "Interface", "full_name": _iface("Reactive"),
                     "display": "Reactive Total Radial",
                     "why": "-Resistance + Fire DoT procs on every hit — boosts ALL your AoE; the farm/trash-clear pick.",
                     "always_on": True})
    else:
        recs.append({"slot": "Interface", "full_name": _iface("Degenerative"),
                     "display": "Degenerative Total Radial",
                     "why": "-Max HP + a toxic DoT on every hit — shrinks each enemy's effective health and chips regen, "
                            "so it out-performs Reactive against tougher targets and is the all-round default (every master "
                            "build outside a pure farm ran Degenerative).",
                     "always_on": True})

    # DESTINY — Barrier (group/self shield) vs Ageless (recharge + recovery + debuff resist).
    # Fire farm: no -res for Barrier's cushion to matter, so Ageless's no-downtime
    # recovery/recharge (sustain across spawns) is the better pick.
    if controller:
        recs.append({"slot": "Destiny", "full_name": _dest("Ageless", "Radial"),
                     "display": "Ageless Radial Epiphany",
                     "why": "recharge + endurance + DEBUFF RESISTANCE — Ageless is what makes your control PERMA and "
                            "keeps it from being -recharge'd out from under you in a league. Recharge here frees the "
                            "Alpha for accuracy/defense.",
                     "always_on": False})
    elif support and content in ("itrial", "team"):
        recs.append({"slot": "Destiny", "full_name": _dest("Barrier"),
                     "display": "Barrier Core Epiphany",
                     "why": "as league support, Barrier is short-term def+res for the WHOLE group through spike damage.",
                     "always_on": False})
    elif farm_content or av or rech_gap > 15:
        recs.append({"slot": "Destiny", "full_name": _dest("Ageless", "Radial"),
                     "display": "Ageless Radial Epiphany",
                     "why": ("recharge + DEBUFF RESISTANCE — beats an AV's -recharge/-tohit spam" if av else
                             "no-downtime recovery + recharge — sustains you spawn-to-spawn; a fire farm has no -res "
                             "for Barrier's cushion to matter." if farm_content else
                             "recharge + endurance with no downtime — sustains the build."),
                     "always_on": False})
    else:
        recs.append({"slot": "Destiny", "full_name": _dest("Barrier"),
                     "display": "Barrier Core Epiphany",
                     "why": "cycled def+res that stacks beyond your caps for its duration — a survival cushion.",
                     "always_on": False})

    # JUDGEMENT — AoE nuke (skip-ish vs AV).
    if av:
        recs.append({"slot": "Judgement", "full_name": _judg("Void"),
                     "display": "Void Radial Final Judgement",
                     "why": "single-target fight — Void adds -Damage so the AV hits softer; the nuke itself is secondary.",
                     "always_on": False})
    else:
        fam = "Pyronic" if content == "fire_farm" else "Ion"
        recs.append({"slot": "Judgement", "full_name": _judg(fam),
                     "display": f"{fam} Radial Final Judgement",
                     "why": ("big fire AoE to wipe packed farm spawns." if content == "fire_farm"
                             else "chaining AoE nuke for spawn/add clear."),
                     "always_on": False})

    # HYBRID — Control (controllers) / Support (team) / Assault (dmg) / Melee (survive).
    if controller:
        recs.append({"slot": "Hybrid", "full_name": "Incarnate.Hybrid.Control_Core_Embodiment",
                     "display": "Control Core Embodiment",
                     "why": "toggled boost to control DURATION + magnitude — the controller's force-multiplier, so your "
                            "holds/confuses last longer and stick on the tougher +3/+4 league targets.", "always_on": True})
    elif support:
        recs.append({"slot": "Hybrid", "full_name": _hybrid("Support"),
                     "display": "Support Radial Genome",
                     "why": "a toggling team buff aura — your role's force-multiplier.", "always_on": True})
    elif role == "tank":
        recs.append({"slot": "Hybrid", "full_name": _hybrid("Melee"),
                     "display": "Melee Radial Genome",
                     "why": "toggled def+res while in melee — extra survival for the front line.", "always_on": True})
    else:
        recs.append({"slot": "Hybrid", "full_name": _hybrid("Assault"),
                     "display": "Assault Radial Embodiment",
                     "why": ("toggled damage buff with a double-hit chance — and it buffs your henchmen too."
                             if is_mm else
                             "toggled damage buff with a double-hit chance — straight DPS, and it can be near-perma."),
                     "always_on": True})

    # LORE — damage+survival pets (always strong; Cimeroran = damage + a heal).
    recs.append({"slot": "Lore", "full_name": _lore("Cimeroran"),
                 "display": "Cimeroran Total Radial",
                 "why": ("two more damage pets layered on top of your henchmen — a Mastermind turns Lore "
                         "into even more pet DPS." if is_mm else
                         "two pets that add sustained damage; the Radial ally also heals — value in any content."),
                 "always_on": True})
    # attach the real parsed magnitude (e.g. "+33% resistance") to each pick
    for r in recs:
        m = _mag_str(r["full_name"])
        if m:
            r["magnitude"] = m
    return recs


def incarnate_loadouts(archetype, role, totals, res_cap=75,
                       contents=("fire_farm", "itrial", "av")):
    """Per-CONTENT incarnate loadouts for the SAME build — incarnates are swappable
    per encounter, so a farmed-out character carries different T4s for different nights.
    Each content re-runs the recommender against THAT content's preset targets, so the
    'is overcap resistance worth it?' call comes out right per encounter (fire farm ->
    sustain; iTrial/league -> resilience cushion)."""
    out = []
    for c in contents:
        tg = preset_targets(c, role, res_cap=res_cap).get("targets") or {}
        out.append({"content": c,
                    "label": CONTENT_PRESETS.get(c, {}).get("label", c),
                    "recs": recommend_incarnates(archetype, c, role, totals, tg, res_cap)})
    return out


_TERMS_BY_LABEL = {e["label"]: e for e in GOAL_TERMS}


def interpret_goal(goal, primary=None, secondary=None):
    """Deterministic, instant interpretation of a free-text goal against the
    lexicon. Returns {matched:[{label}], confirmation, focus} for the confirm
    step + the priority text injected into generation.

    `primary`/`secondary` (powerset display names) make it CONTEXT-AWARE: a support
    set (e.g. Kinetics) + a "farm" goal means the character SUPPORTS a farmer, so we
    steer to team-buffing instead of (impossible) solo fire-farm survival."""
    g = " " + (goal or "").lower() + " "
    matched, seen = [], set()
    for entry in GOAL_TERMS:
        for term in entry["terms"]:
            # tolerate an optional trailing plural 's' (farm/farms, proc/procs)
            if re.search(r"(?<![a-z])" + re.escape(term) + r"s?(?![a-z])", g):
                if entry["label"] not in seen:
                    matched.append(entry)
                    seen.add(entry["label"])
                break

    # Context correction: a SUPPORT character can't be the fire farmer — if a farm
    # goal matched, reinterpret as supporting/buffing the farm.
    is_support = (primary or "").lower() in SUPPORT_SETS or \
                 (secondary or "").lower() in SUPPORT_SETS
    if is_support and "Fire-farm survival" in seen:
        matched = [m for m in matched if m["label"] != "Fire-farm survival"]
        seen.discard("Fire-farm survival")
        for lbl in ("Team support / buffs", "Dual-box support (passive)"):
            if lbl not in seen and lbl in _TERMS_BY_LABEL:
                matched.insert(0, _TERMS_BY_LABEL[lbl])
                seen.add(lbl)
    if matched:
        labels = [m["label"] for m in matched]
        if len(labels) == 1:
            phrase = labels[0]
        elif len(labels) == 2:
            phrase = labels[0] + " and " + labels[1]
        else:
            phrase = ", ".join(labels[:-1]) + ", and " + labels[-1]
        confirmation = f"Based on your request, you want: {phrase}. Is that correct?"
        focus = ("CONFIRMED PRIORITIES (the user verified these — honor them, in "
                 "roughly this order):\n"
                 + "\n".join(f"- {m['label']}: {m['focus']}" for m in matched))
    else:
        confirmation = ("I didn't detect specific priorities, so I'll aim for a "
                        "well-rounded, generally strong build. Add terms like "
                        "'soft-capped ranged defense', 'perma-Hasten', 'high AoE "
                        "damage', or 'fire-farm survival' to steer it. Proceed?")
        focus = ("No specific priorities detected; build a well-rounded, generally "
                 "strong character for this archetype and powersets.")
    return {"matched": [{"label": m["label"], "focus": m["focus"]} for m in matched],
            "confirmation": confirmation, "focus": focus}


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------
def _options_text(powers_grouped, incarnate_slots):
    """The 'available powers + sets + incarnates' block shared by both prompts."""
    L = ["\nYou may ONLY use powers from this list (exact display names):"]
    for label, names in powers_grouped.items():
        if names:
            L.append(f"  [{label}] " + " | ".join(names))
    L.append("\nUse real Homecoming Invention set names you know (e.g. Luck of "
             "the Gambler, Reactive Armor, Theft of Essence, Thunderstrike). The "
             "app validates every set against the power's allowed categories and "
             "silently drops mismatches, so just pick sensible real sets.")
    L.append("\nIncarnate choices (pick the strongest tier, e.g. Core/Radial "
             "Paragon for Alpha):")
    for slot, choices in incarnate_slots.items():
        L.append(f"  [{slot}] {', '.join(choices[:8])} ...")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Build tiers — same goal, three different budgets / levels of optimization.
# ---------------------------------------------------------------------------
TIER_META = {
    "budget":   {"label": "Budget", "cost": "Cheapest & efficient",
                 "blurb": "SOs / common IOs and cheap sets. Meets the goal at "
                          "minimal influence cost."},
    "balanced": {"label": "Balanced", "cost": "Middle of the road",
                 "blurb": "Strong common IO sets + LotG global recharge. No "
                          "purples / ATOs / Winter / PvP IOs."},
    "premium":  {"label": "Premium", "cost": "Top-end, where it counts",
                 "blurb": "Purples, Superior ATOs, Winter & PvP IOs — but only "
                          "where they noticeably beat the cheaper option. Goal is "
                          "a floor; maximizes impact per slot, not spend."},
}
TIER_ORDER = ["budget", "balanced", "premium"]

_TIER_GUIDANCE = {
    "budget": (
        "BUILD TIER: BUDGET / EFFICIENT — minimize influence cost.\n"
        "- Slot SOs or common Invention IOs and only CHEAP, common IO sets. Do "
        "NOT use purple/very-rare sets, Archetype Origin (ATO) sets, Winter "
        "sets, or PvP IOs.\n"
        "- MEET the goal at the lowest reasonable cost. Still build a COMPLETE "
        "build (all ~24 powers, all slots used) — completeness is free; cost is "
        "in the IOs. Just fill it with cheap/common sets and SOs rather than "
        "expensive ones. One Luck of the Gambler: Def/+Global Recharge is fine."),
    "balanced": (
        "BUILD TIER: BALANCED / MID-RANGE — strong but reasonably priced.\n"
        "- Use good, widely-available IO sets and frankenslotting. Use Luck of "
        "the Gambler: Def/+Global Recharge freely. Do NOT use purple/very-rare "
        "sets, ATO sets, Winter sets, or PvP IOs.\n"
        "- Soft-cap (45%) the defense type(s) the goal needs, push key "
        "resistances up, and secure solid global recharge and endurance "
        "sustain.\n"
        "- Build is COMPLETE (all ~24 powers, all slots used); 6-slot the "
        "build-defining powers for full sets, mule the rest for unique globals "
        "and cheaper bonuses."),
    "premium": (
        "BUILD TIER: PREMIUM / HIGH-IMPACT — money is available, but spending it "
        "is NOT the goal; IMPACT is. Every expensive IO (purple/very-rare, "
        "Superior ATO, Winter, PvP) must EARN its slot by giving a NOTICEABLE "
        "improvement over the cheaper option. If a common IO or a cheap set "
        "bonus gets you essentially the same result, USE THE CHEAPER ONE — do "
        "not slot purples for their own sake.\n"
        "- Treat the GOAL AS A FLOOR, then spend premium budget where it moves "
        "the needle most: big set-bonus jumps (global recharge, layered defense/"
        "resistance, HP/regen), uniques that ONLY a premium IO provides "
        "(Gladiator's Armor +3% Def, Shield Wall +5% Res, Kismet +Acc, LotG +"
        "Global Recharge), and high-value damage procs (Apocalypse/Hecatomb/"
        "Ragnarok/Armageddon/Unbreakable Constraint/Fury of the Gladiator, Force "
        "Feedback +Recharge). Available premium sets: those purples, the "
        "archetype's SUPERIOR ATO sets, and Winter sets (Superior Winter's Bite, "
        "Frozen Blast, Avalanche, Blistering Cold).\n"
        "- Build is COMPLETE (all ~24 powers, all ~67 slots used): 6-slot the "
        "powers that host your best sets, mule every other pick for a unique "
        "global or bonus. Use the strongest incarnate tier in each useful slot.\n"
        "- In the \"summary\", call out the 2-3 premium picks that deliver the "
        "biggest payoff vs. a cheaper alternative, and roughly what each buys "
        "(e.g. 'Apocalypse over a cheap damage set here = +10% global recharge "
        "and a strong proc'). Don't list expensive IOs that aren't pulling "
        "their weight."),
}

_SCHEMA = """
General rules:
- BUILD A COMPLETE LEVEL-50 BUILD — this overrides any narrower reading of the
  goal. Take the FULL number of power picks a level 50 gets (~24 powers) and USE
  ALL of your ~67 enhancement slots. Never leave a power pick on the table or a
  power under-slotted when set bonuses are available: because set bonuses and
  toggles are ALWAYS-ON (you do not have to activate a power to get its set
  bonus), EVERY power — even one you will never click — is a passive set-bonus
  "mule". Fill utility/filler picks with mules carrying valuable UNIQUE globals
  (Luck of the Gambler: Defense/+Recharge; Steadfast Protection / Gladiator's
  Armor: +3% Def; Kismet: +Accuracy; Shield Wall / Reactive Defenses uniques) or
  with sets whose bonuses advance the goal. Prefer picks that accept useful set
  categories.
- ALWAYS slot the FREE inherent Fitness powers (they cost no power pick): HEALTH
  with Healing-set globals (Numina's Convalescence, Miracle, Panacea, Preventive
  Medicine — for passive +Regen/+Recovery/+HP/+Absorb) and STAMINA with Endurance
  Modification globals (Performance Shifter: Chance for +Endurance; Power
  Transfer: Chance for Heal). These are pure passive bonuses — never leave Health
  and Stamina empty.
- SLOT EFFICIENCY — every slot must EARN its place (marginal value): give a power
  only as many slots as it PRODUCTIVELY uses; stop adding slots once they no
  longer buy a worthwhile set bonus or hit Enhancement Diversification (ED). ED
  knee is ~3 enhancements of the SAME aspect (~95%) — a 4th+ of the same aspect
  is largely wasted, so do NOT 6-slot a power that only needs 3-4 to cover its
  aspects / reach its useful bonus. REDIRECT the spare slots to powers that can
  start a NEW set bonus or hold a unique global — including Health/Stamina and
  other mules. Use the Rule of 5 deliberately: a given set bonus counts up to 5
  times, so to keep stacking a bonus, SPREAD the same set (or different sets that
  share that bonus) across several powers rather than over-investing one. You
  have EXACTLY 67 enhancement slots — a HARD CAP. Spend close to all 67 where
  marginal value is highest (6-slot only where a full set is worth it; 1-3 slot
  the many mules), but NEVER exceed 67 total across the whole build.
- Defense soft cap 45%, resistance hard cap 75%. Set bonuses count up to 5
  identical instances. Luck of the Gambler: Defense/Increased Global Recharge
  Speed can be slotted multiple times.
- IMPORTANT: a power's slot count EQUALS the number of enhancements you list for
  it. Never leave a slot empty — provide exactly one enhancement per slot. The
  "slots" number must equal the length of "enhancements".
- Each enhancement is {"set":<set name>,"piece":<piece name>}; common single IOs
  use {"set":"Invention","piece":"<aspect> IO"} (e.g. "Accuracy IO", "Recharge
  IO", "Endurance Reduction IO").
- Choose incarnates for the slots that help the goal.
- Keep the JSON compact. Do not add fields beyond the schema.

Output JSON with EXACTLY this shape:
{
  "powers": [
    {"name": "<power display name>", "slots": <int 1-6>,
     "enhancements": [{"set":"<set name>","piece":"<piece name>"}]}
  ],
  "incarnates": {"Alpha":"<choice or empty>","Judgement":"","Interface":"",
                 "Lore":"","Destiny":"","Hybrid":"","Genesis":""},
  "summary": "<2-3 sentence rationale>"
}
Output ONLY the JSON object."""


def generate_prompt(archetype_display, primary, secondary, goal,
                    powers_grouped, sets_by_cat, incarnate_slots, tier="balanced",
                    focus=None, set_hints=None):
    """First-pass build generation at a given budget tier. `focus` is the
    confirmed-priority text from interpret_goal (the user verified it).
    `set_hints` lists real sets that grant the goal-critical bonuses."""
    guidance = _TIER_GUIDANCE.get(tier, _TIER_GUIDANCE["balanced"])
    focus_block = (focus + "\n\n") if focus else ""
    hints_block = (set_hints + "\n\n") if set_hints else ""
    return (
        "You are building a City of Heroes (Homecoming) character. Output a "
        "complete, optimized build as STRICT JSON ONLY — no prose, no markdown "
        "fences, no commentary outside the JSON.\n"
        f"\nArchetype: {archetype_display}\nPrimary: {primary}\n"
        f"Secondary: {secondary}\n\nGoal: {goal}\n\n"
        + focus_block
        + _GOAL_TARGETING + "\n\n"
        + hints_block
        + _UNIQUE_GLOBALS + "\n\n"
        + guidance + "\n"
        + _options_text(powers_grouped, incarnate_slots)
        + "\n" + _SCHEMA)


_POWERS_SCHEMA = """
Rules:
- Choose a COMPLETE level-50 power selection: the key primary/secondary powers,
  survivability (usually Fighting: Boxing + Tough + Weave), Leadership
  (Maneuvers, often Tactics), a travel/utility pool, and an epic/ancillary pool.
  Aim for ~24 powers (a level-50 has 24 picks).
- ALWAYS include the attack powers, even on a support/non-attacking build — they
  are the build's set-bonus carriers (slotted as bonus-holders). Skipping them
  throws away most of the build's defense/resistance.
- Pick the strongest incarnate tier for each useful slot.
- Do NOT choose enhancements or slots — a separate optimizer assigns those.

Output JSON with EXACTLY this shape:
{
  "powers": ["<power display name>", ...],
  "incarnates": {"Alpha":"<choice or empty>","Judgement":"","Interface":"",
                 "Lore":"","Destiny":"","Hybrid":"","Genesis":""},
  "summary": "<2-3 sentence rationale for the power picks>"
}
Output ONLY the JSON object."""


def powers_prompt(archetype_display, primary, secondary, goal, powers_grouped,
                  incarnate_slots, focus=None):
    """Ask the LLM for the POWER PICKS only (not enhancements) — the part it's
    actually good at. The deterministic solver slots them afterward."""
    focus_block = (focus + "\n\n") if focus else ""
    return (
        "You are choosing the POWERS for a City of Heroes (Homecoming) level-50 "
        "build. Pick the powers ONLY — a separate optimizer will assign the "
        "enhancements/slots. Output STRICT JSON ONLY.\n"
        f"\nArchetype: {archetype_display}\nPrimary: {primary}\n"
        f"Secondary: {secondary}\n\nGoal: {goal}\n\n"
        + focus_block
        + _GOAL_TARGETING + "\n"
        + _options_text(powers_grouped, incarnate_slots)
        + "\n" + _POWERS_SCHEMA)


def resolve_powers(cjson, power_index, incarnate_index):
    """Resolve an LLM power-pick list into real power records (dedup, validated)
    + incarnates. No slotting — that's the solver's job."""
    out, seen, used, warnings = [], set(), set(), []
    for nm in cjson.get("powers", []) or []:
        rec = _best(nm, power_index)
        if not rec:
            warnings.append(f"Power not found, skipped: '{nm}'")
            continue
        if rec["full_name"] in seen:
            continue
        seen.add(rec["full_name"])
        used.add(rec["powerset_full_name"])
        out.append({
            "full_name": rec["full_name"], "display_name": rec["display_name"],
            "powerset_full_name": rec["powerset_full_name"],
            "accepted_set_category_ids": rec.get("accepted_set_category_ids", []),
            "accepted_set_categories": rec.get("accepted_set_categories", []),
            "power_type": rec.get("power_type")})
    out_inc = {}
    for slot, choice in (cjson.get("incarnates") or {}).items():
        if not choice:
            continue
        idx = incarnate_index.get(slot)
        if idx:
            full = _best(choice, idx)
            if full:
                out_inc[slot] = full
    return {"powers": out, "incarnates": out_inc,
            "powersets_used": sorted(used), "warnings": warnings,
            "summary": cjson.get("summary", "")}


_GOAL_TARGETING = (
    "FIRST, infer the SPECIFIC threats this goal implies and prioritize "
    "mitigation against THOSE — do not chase set bonuses for irrelevant "
    "damage/position types. Mapping examples:\n"
    "- Fire farm / fire farming: the threat is overwhelmingly FIRE plus "
    "Smashing/Lethal. FIRE mitigation is priority #1. On an AT without strong "
    "innate fire resistance (e.g. Defender — Fire Shield is mostly S/L), layer "
    "it: FIRST soft-cap typed/positional DEFENSE toward 45% so hits miss, THEN "
    "push Fire resistance (slot the fire-armor toggle for resistance + Fire/Cold-"
    "res set bonuses), then S/L resistance. Do NOT over-stack S/L resistance "
    "while Fire stays low. Ignore Energy/Negative/Psionic.\n"
    "- Ranged/positional builds: prioritize Ranged (and AoE) defense.\n"
    "- Melee/scrapper survivability: prioritize Melee defense and S/L resist.\n"
    "- 'Survive anything' with no type named: build TYPED defense to the 45% "
    "soft cap across S/L/F/C/E/N if achievable, else positional (Melee/Ranged/"
    "AoE) defense.\n"
    "Pick enhancement sets whose BONUSES advance the goal-relevant stats, not "
    "whatever is highest by accident.")


_UNIQUE_GLOBALS = (
    "HIGH-VALUE UNIQUE / PROC IOs — a single one of these in a slot is often "
    "worth more than completing a set. Place each in a power that accepts its "
    "category. Each UNIQUE may be slotted only ONCE per character (never twice). "
    "Always include the universally strong ones unless the goal makes them "
    "pointless. Use exact {set, piece} names:\n"
    "DEFENSE/RESISTANCE — slot in armor/defense toggles (Tough, Weave, Maneuvers, "
    "Combat Jumping, Fire Shield, etc.):\n"
    "  - {Luck of the Gambler, Defense/Increased Global Recharge Speed} — +7.5% "
    "global recharge; NOT unique — put ONE in EVERY defense-category toggle.\n"
    "  - {Steadfast Protection, Resistance/+Def 3%} — unique, +3% Defense (all).\n"
    "  - {Gladiator's Armor, TP Protection +3% Def (All)} — unique, +3% Defense "
    "(stacks with Steadfast for +6%).\n"
    "  - {Shield Wall, +Res (Teleportation), +5% Res (All)} — unique, +5% "
    "Resistance (all).\n"
    "  - {Reactive Defenses, Scaling Resist Damage} — unique, resistance that "
    "scales up as HP drops (great for farms).\n"
    "  - {Kismet, Accuracy +6%} — unique, +6% ToHit; slot in a defense toggle.\n"
    "SURVIVAL — slot in HEALTH:\n"
    "  - {Numina's Convalescence, +Regeneration/+Recovery} — unique.\n"
    "  - {Miracle, +Recovery} — unique.\n"
    "  - {Panacea, +Hit Points/Endurance} — unique proc.\n"
    "  - {Preventive Medicine, Chance for +Absorb} — unique proc.\n"
    "ENDURANCE — slot in STAMINA:\n"
    "  - {Performance Shifter, Chance for +End} — proc.\n"
    "  - {Power Transfer, Chance to Heal Self} — proc.\n"
    "RECHARGE/UTILITY:\n"
    "  - {Force Feedback, Chance for +Recharge} — strong recharge proc; slot in "
    "an attack or knockback power.\n"
    "  - {Winter's Gift, Slow Resistance (20%)} — unique; slot in a travel power.\n"
    "  - {Celerity, +Stealth} — slot in Sprint/travel.\n"
    "DAMAGE/DEBUFF PROCS (ONLY if this character actually attacks): {Achilles' "
    "Heel, Chance for Res Debuff} and purple/ATO damage procs. A proc only fires "
    "when YOU use the power, so SKIP damage/debuff procs for a non-attacking "
    "support/dual-box bot — they would do nothing.")


def totals_summary(totals):
    """Compact readable summary of computed totals for the refine prompt."""
    def hi(d, cap):
        items = sorted(((k, v["value"]) for k, v in d.items()), key=lambda x: -x[1])
        return ", ".join(f"{k} {v:.1f}%" for k, v in items if v > 0.1) or "none"
    return (
        f"Defense (soft cap 45%): {hi(totals['defense'], 45)}\n"
        f"Resistance (cap {totals['caps']['resistance_hard_cap']}%): "
        f"{hi(totals['resistance'], 75)}\n"
        f"Recharge +{totals['recharge']['value']:.0f}%, "
        f"Recovery +{totals['recovery']['value']:.0f}%, "
        f"Regen +{totals['regeneration']['value']:.0f}%, "
        f"MaxHP +{totals['max_hp']['value']:.0f}%")


def refine_prompt(archetype_display, primary, secondary, goal, resolved, totals,
                  powers_grouped, incarnate_slots, tier="balanced", focus=None,
                  fill_note=None):
    """Second pass: given the current build + its computed totals, improve it.
    `focus` is the confirmed-priority text from interpret_goal. `fill_note`, when
    set, makes this a COMPLETENESS pass (fill empty slots, complete partial sets)
    rather than a goal re-optimization."""
    cur = []
    for p in resolved.get("powers", []):
        sets = sorted({s["set_name"] for s in p.get("slots", [])
                       if s and s.get("set_name")})
        cur.append(f"  {p['display_name']} [{p['slotCount']} slots]: "
                   + (", ".join(sets) if sets else "(unslotted)"))
    inc = resolved.get("incarnates", {})
    inc_line = ("  Incarnates: " + ", ".join(
        f"{k}={v.get('display_name')}" for k, v in inc.items())) if inc else ""

    if fill_note:
        improve = (fill_note + " Keep the powers and good slotting you already "
                   "have — just FILL the gaps: add enhancements until close to 67 "
                   "slots are used (67 is a HARD CAP — NEVER exceed it), COMPLETE "
                   "partial sets (a set left at 1-2 pieces wastes it — take it to "
                   "the piece count that gives the bonus you want), and full-slot "
                   "the build-defining powers. Do not remove powers. Stay within "
                   "this build tier:")
    else:
        improve = ("Now improve the build toward the goal and the confirmed "
                   "priorities above: keep what works, but change power/slot/"
                   "enhancement choices to raise the stats that matter (e.g. push "
                   "a key resistance toward its cap, reach the 45% defense soft "
                   "cap, add global recharge). Re-slot or swap sets as needed. "
                   "Stay within this build tier:")

    return (
        "You previously generated this City of Heroes build. REFINE it, using the "
        "COMPUTED TOTALS below (what the build currently achieves — from toggle/"
        "auto powers, enhancements with ED, and set bonuses). Output STRICT JSON "
        "ONLY, same schema.\n"
        f"\nArchetype: {archetype_display}\nPrimary: {primary}\n"
        f"Secondary: {secondary}\n\nGoal: {goal}\n\n"
        + ((focus + "\n\n") if focus else "")
        + "CURRENT BUILD:\n" + "\n".join(cur) + ("\n" + inc_line if inc_line else "")
        + "\n\nCOMPUTED TOTALS:\n" + totals_summary(totals)
        + "\n\n" + improve + "\n\n"
        + _TIER_GUIDANCE.get(tier, _TIER_GUIDANCE["balanced"]) + "\n"
        + _options_text(powers_grouped, incarnate_slots)
        + "\n" + _SCHEMA)


# ---------------------------------------------------------------------------
# Parse Claude's JSON (tolerant of stray fences / prose)
# ---------------------------------------------------------------------------
def extract_json(text):
    text = text.strip()
    # strip ```json fences if present
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    # otherwise grab the outermost {...}
    if not text.startswith("{"):
        a, b = text.find("{"), text.rfind("}")
        if a != -1 and b != -1:
            text = text[a:b + 1]
    return json.loads(text)


# ---------------------------------------------------------------------------
# Fuzzy matching helpers
# ---------------------------------------------------------------------------
def _best(name, choices_lower_map):
    """choices_lower_map: {lowername: value}. Return value or None."""
    if not name:
        return None
    key = name.strip().lower()
    if key in choices_lower_map:
        return choices_lower_map[key]
    # substring
    for k, v in choices_lower_map.items():
        if key == k or key in k or k in key:
            return v
    m = difflib.get_close_matches(key, list(choices_lower_map.keys()), n=1, cutoff=0.82)
    return choices_lower_map[m[0]] if m else None


# ---------------------------------------------------------------------------
# Resolve a Claude build into real, validated build data
# ---------------------------------------------------------------------------
def resolve_common_io(piece_name, common_io_map):
    """Map a generic IO name (e.g. 'Accuracy IO', 'Recharge') to a real
    common-IO uid via keyword match. common_io_map: {keyword_lower: uid}."""
    if not piece_name:
        return None
    p = piece_name.lower().replace(" io", "").replace("invention", "").strip()
    if p in common_io_map:
        return common_io_map[p]
    for kw, uid in common_io_map.items():
        if kw in p or p in kw:
            return uid
    m = difflib.get_close_matches(p, list(common_io_map.keys()), n=1, cutoff=0.8)
    return common_io_map[m[0]] if m else None


def _piece_available(pc, used_in_power, used_unique):
    """A set piece may go in a slot only if it isn't already used in THIS power
    AND — if it's a UNIQUE IO (purple/Superior/attuned piece or special proc) —
    isn't already placed ANYWHERE in the build. Unique IOs are one per character,
    so the same unique can't appear in two powers (an un-buildable fit)."""
    uid = pc.get("uid")
    if uid in used_in_power:
        return False
    if pc.get("unique") and uid in used_unique:
        return False
    return True


def resolve_build(cjson, power_index, set_by_name, cat_by_id, incarnate_index,
                  common_io_map=None):
    """
    power_index: {display_lower: power_record}  (record has full_name,
                 powerset_full_name, display_name, accepted_set_category_ids,
                 accepted_set_categories)
    set_by_name: {set_name_lower: set_record}
    incarnate_index: {slot: {choice_lower: full_name/display}}
    Returns {powers, incarnates, summary, warnings, powersets_used}
    """
    warnings = []
    out_powers = []
    powersets_used = set()
    taken = set()             # full_names already in the build (no duplicate picks)
    used_unique = set()       # unique-IO piece uids placed ANYWHERE (one per character)

    for pw in cjson.get("powers", []):
        rec = _best(pw.get("name", ""), power_index)
        if not rec:
            warnings.append(f"Power not found, skipped: '{pw.get('name')}'")
            continue
        # A power can only be taken ONCE. If the AI repeats one (e.g. Maneuvers
        # twice), drop the duplicate — it's an invalid, wasted pick.
        if rec["full_name"] in taken:
            warnings.append(f"Duplicate power dropped: '{rec['display_name']}' "
                            f"(already taken).")
            continue
        taken.add(rec["full_name"])
        accepted = set(rec.get("accepted_set_category_ids", []))
        slots = []
        used_set_pieces = set()   # set-piece uids already used in THIS power
        for enh in pw.get("enhancements", []) or []:
            set_name = (enh.get("set") or "").strip()
            piece_name = (enh.get("piece") or "").strip()
            if set_name.lower() in ("invention", "io", "common", "generic", "common io"):
                # generic single IO -> resolve to a real common-IO uid
                uid = resolve_common_io(piece_name or set_name, common_io_map or {})
                if uid:
                    slots.append({"set_uid": None, "set_name": "Invention",
                                  "piece_uid": uid, "piece_name": piece_name or "IO",
                                  "category_id": None, "enhances": [],
                                  "unique": False, "generic": True})
                else:
                    warnings.append(f"{rec['display_name']}: couldn't resolve common IO "
                                    f"'{piece_name}', skipped.")
                continue
            srec = _best(set_name, set_by_name)
            if not srec:
                warnings.append(f"{rec['display_name']}: set '{set_name}' not found, skipped.")
                continue
            # SLOT ENFORCEMENT: set category must fit the power
            if accepted and srec["category_id"] not in accepted:
                warnings.append(
                    f"{rec['display_name']}: '{srec['name']}' "
                    f"({srec['category']}) doesn't fit this power's categories "
                    f"({', '.join(rec.get('accepted_set_categories', []))}); skipped.")
                continue
            piece_map = {p["name"].lower(): p for p in srec["pieces"]}
            piece = _best(piece_name, piece_map) or (srec["pieces"][0] if srec["pieces"] else None)
            if not piece:
                warnings.append(f"{rec['display_name']}: no piece for set '{srec['name']}'.")
                continue
            # A piece can't repeat in THIS power, and a UNIQUE piece can't repeat
            # anywhere in the build. If the chosen piece is unavailable, substitute
            # the next available piece of the same set; if none, drop the slot.
            if not _piece_available(piece, used_set_pieces, used_unique):
                alt = next((p for p in srec["pieces"]
                            if _piece_available(p, used_set_pieces, used_unique)), None)
                if alt is None:
                    if piece.get("unique"):
                        warnings.append(
                            f"{rec['display_name']}: '{srec['name']}: {piece['name']}' "
                            f"is a unique IO already used elsewhere; dropped (one per "
                            f"character).")
                    continue   # set exhausted here / all remaining uniques taken
                piece = alt
            used_set_pieces.add(piece.get("uid"))
            if piece.get("unique"):
                used_unique.add(piece.get("uid"))
            slots.append({
                "set_uid": srec["uid"], "set_name": srec["name"],
                "piece_uid": piece.get("uid"), "piece_name": piece["name"],
                "category_id": srec["category_id"], "enhances": piece.get("enhances", []),
                "unique": piece.get("unique", False),
                "image": piece.get("image") or srec.get("image") or "",
            })

        # Slot count follows the actual enhancements so there are no empty
        # slots. A power with no enhancements keeps a single base slot.
        slots = slots[:6]
        if slots:
            slot_count = len(slots)
        else:
            slot_count = 1
            slots = [None]

        powersets_used.add(rec["powerset_full_name"])
        ptype = rec.get("power_type")
        out_powers.append({
            "full_name": rec["full_name"],
            "display_name": rec["display_name"],
            "powerset_full_name": rec["powerset_full_name"],
            "accepted_set_category_ids": rec.get("accepted_set_category_ids", []),
            "accepted_set_categories": rec.get("accepted_set_categories", []),
            "power_type": ptype,
            "include_in_totals": ptype in (1, 2),
            "slotCount": slot_count,
            "slots": slots,
        })

    # incarnates
    out_inc = {}
    for slot, choice in (cjson.get("incarnates") or {}).items():
        if not choice:
            continue
        idx = incarnate_index.get(slot)
        if not idx:
            continue
        full = _best(choice, idx)
        if full:
            out_inc[slot] = full   # {full_name, display_name}

    return {
        "powers": out_powers,
        "incarnates": out_inc,
        "summary": cjson.get("summary", ""),
        "warnings": warnings,
        "powersets_used": sorted(powersets_used),
    }
