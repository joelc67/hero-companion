"""
solver.py - Constraint-driven slot solver.

Instead of letting the LLM guess a build and grading it after, this solves the
slotting *backward* from target stats: given the chosen powers and a target
profile (e.g. 45% S/L/F/C/E defense, 75% fire resistance, +recharge), it assigns
enhancement SETS and unique globals to slots to best close the gap to those
targets — because set bonuses are flat, additive and capped by the rule of five,
this is a tractable optimization rather than a guess.

`solve_ilp` models it as an integer linear program (PuLP/CBC): binary set-
placement choices, maximize balanced *capped* gap-coverage of the targets,
subject to rule-of-5, unique, category, and 67-slot constraints — solved to
optimum in well under a second. Deterministic: same powers + targets -> same
slotting, every time. A tier dial (budget/balanced/premium) controls premium
(purple/ATO/Winter/PvP) set use via a cost penalty.

Functionality guard: attack powers are only ever given attack-category SETS
(which inherently carry accuracy/damage/endurance/recharge across their pieces),
so the build stays playable, not just bonus-stacked.
"""

from collections import defaultdict, Counter

try:
    import pulp
except ImportError:  # ILP unavailable -> solve_ilp raises; install pulp
    pulp = None

# Stats the solver optimizes toward, keyed uniformly. damage_type "None" on a
# Defense/Resistance effect spreads to all types.
DEF_TYPES = ["Smashing", "Lethal", "Fire", "Cold", "Energy", "Negative",
             "Toxic", "Psionic", "Melee", "Ranged", "AoE"]
RES_TYPES = ["Smashing", "Lethal", "Fire", "Cold", "Energy", "Negative",
             "Toxic", "Psionic"]
GLOBAL_STATS = {"RechargeTime", "Recovery", "Regeneration", "HitPoints", "ToHit"}

# Categories that hold "attack" sets (need functionality) vs defensive/utility.
ATTACK_CATS = {"Melee Damage", "Ranged Damage", "PBAoE Damage",
               "Targeted AoE Damage", "Sniper Attacks", "Holds", "Stuns",
               "Immobilize", "Sleep", "Confuse", "Fear", "Universal Damage"}

RULE_OF_FIVE = 5

# Fighting-pool PREREQ attacks (Boxing/Kick) exist only as a gateway to Tough/Weave. On a
# character that never fights in melee (ranged/support ATs), NO ONE slots them — the master
# corpus confirms it: every hand-made ranged/support master leaves Boxing/Kick at its single
# free slot, while only true-melee ATs ever add slots to it. So for non-melee ATs we cap the
# prereq at 1 slot: the solver must harvest its set bonuses in powers the player actually uses,
# never in a dead melee attack. (Melee ATs — Scrapper/Brute/Stalker/Tanker/Kheldians — keep it
# open; Boxing can be a real part of their attack chain.)
_FIGHTING_PREREQS = {"Pool.Fighting.Boxing", "Pool.Fighting.Kick"}
# ATs whose core payoff is DAMAGE as well as control/support — must slot their attacks for damage.
_DAMAGE_HYBRID_ATS = {"Class_Dominator", "Class_Corruptor"}
# Set categories that hold a debuff power's WORKING enhancement (−def/−tohit are enhanceable).
_DEBUFF_SET_CATS = {"Defense Debuff", "Accurate Defense Debuff",
                    "To Hit Debuff", "Accurate To-Hit Debuff"}
# ATs with a NATIVE armor set (primary/secondary) — their armor slotting is already driven by the
# survival objective. The armor-must-enhance floor is for SQUISHIES, whose only armor is a bought
# epic shield (Scorpion/Frozen/Charged Armor) that otherwise sits at 1 slot, unenhanced.
_ARMOR_NATIVE_ATS = {"Class_Scrapper", "Class_Brute", "Class_Stalker", "Class_Tanker",
                     "Class_Sentinel", "Class_Peacebringer", "Class_Warshade",
                     "Class_Arachnos_Soldier", "Class_Arachnos_Widow"}
_MELEE_FIGHTING_ATS = {"Class_Scrapper", "Class_Brute", "Class_Stalker", "Class_Tanker",
                       "Class_Peacebringer", "Class_Warshade"}
# Frankenslotting: a power may hold pieces from up to this many different sets
# (e.g. 3 of set A for one bonus + 3 of set B for another). 2 covers the
# real-world case; more bloats the ILP for negligible gain. Globals placed in
# Phase 0 sit outside this count (they're single unique IOs, not sets).
MAX_SETS_PER_POWER = 2
# Approx ED-capped res/def ENHANCEMENT a res/def SET gives its host armor toggle, by
# piece count (a set is multi-aspect so it's below n pure res IOs). Used to credit the
# toggle enhancement in the ILP so it sizes res/def sets up enough to cap survival.
_ED_RESDEF = {1: 0.13, 2: 0.26, 3: 0.38, 4: 0.46, 5: 0.52, 6: 0.56}


def _stat_key(eff):
    """Map a bonus effect to a target/total key, or None if untracked."""
    et = eff.get("effect")
    dt = eff.get("damage_type", "None")
    if et == "Defense":
        return ("Defense", dt)
    if et == "Resistance":
        return ("Resistance", dt)
    if et in GLOBAL_STATS:
        return (et, None)
    return None


def _mutex_key(set_name, piece_name):
    """Identity for unique-IO mutual exclusion. A set's REGULAR and 'Superior'
    (catalyzed) forms are the SAME enhancement in-game — they share a mutex group,
    so a character can't slot both (e.g. Winter's Bite AND Superior Winter's Bite).
    Normalize by dropping a leading 'Superior ' from the set name + the piece name."""
    sn = (set_name or "").strip().lower()
    if sn.startswith("superior "):
        sn = sn[len("superior "):]
    return (sn, (piece_name or "").strip().lower())


def _expand(key, value):
    """Expand a ('Defense','None') all-types effect into the concrete types."""
    kind, dt = key
    if kind in ("Defense", "Resistance") and dt in ("None", "Special"):
        types = DEF_TYPES if kind == "Defense" else RES_TYPES
        return [((kind, t), value) for t in types]
    return [(key, value)]


def _pv_ok(pv_mode, pvp):
    """Whether a set bonus applies in the current arena (mirrors engine._pv_ok):
    Any(0) always; PvE(1) only out of PvP; PvP(2) only in PvP."""
    pm = pv_mode or 0
    if pm == 0:
        return True
    return pm == 2 if pvp else pm == 1


def _set_bonus_contrib(set_rec, n_pieces, used_sig, pvp=False):
    """Cumulative bonus stat-vector for slotting `n_pieces` of a set, honoring
    the rule of five via `used_sig` (signature -> count, mutated on commit=False
    only for scoring). Returns (contrib dict, list of signatures used)."""
    contrib = defaultdict(float)
    sigs = []
    for b in set_rec.get("bonuses", []):
        if b.get("pieces_required", 99) > n_pieces:
            continue
        if not _pv_ok(b.get("pv_mode", 0), pvp):
            continue
        sig = "|".join(b.get("bonuses", []))
        if used_sig.get(sig, 0) + sum(1 for s in sigs if s == sig) >= RULE_OF_FIVE:
            continue                        # rule of five reached
        sigs.append(sig)
        for eff in b.get("effects", []):
            k = _stat_key(eff)
            if not k:
                continue
            for ek, ev in _expand(k, eff.get("value", 0.0)):
                contrib[ek] += ev
    return contrib, sigs


def normalize_targets(targets_pct):
    """Convert a friendly target dict (percent) into internal fraction keys.
    Accepts {'defense': {'Fire': 45, ...} or {'all': 45}, 'resistance': {...},
    'recharge': 100, 'recovery': 50, ...}."""
    t = {}
    for kind, key in (("defense", "Defense"), ("resistance", "Resistance")):
        d = targets_pct.get(kind) or {}
        types = DEF_TYPES if kind == "defense" else RES_TYPES
        if "all" in d:
            for ty in types:
                t[(key, ty)] = d["all"] / 100.0
        for ty, val in d.items():
            if ty != "all":
                t[(key, ty)] = val / 100.0
    for fld, key in (("recharge", "RechargeTime"), ("recovery", "Recovery"),
                     ("regen", "Regeneration"), ("regeneration", "Regeneration"),
                     ("max_hp", "HitPoints"), ("tohit", "ToHit")):
        if fld in targets_pct:
            t[(key, None)] = targets_pct[fld] / 100.0
    return t


# Premium ("very rare") sets — the common->purple upgrade IS the budget/premium
# cost axis. level (49,49) = purples + Superior ATOs + Superior Winter; the
# non-Superior Winter and PvP sets are level 9-49 so need a name check.
_PREMIUM_NAMES = ("winter's bite", "frozen blast", "avalanche", "blistering cold",
                  "gladiator", "shield wall", "panacea", "javelin volley",
                  "fury of the gladiator", "sting of the manticore")


def set_cost_rank(srec):
    """0 = standard/cheap, 2 = premium (very-rare purple / ATO / Winter / PvP)."""
    if srec.get("level_min") == 49 and srec.get("level_max") == 49:
        return 2
    n = srec.get("name", "").lower()
    return 2 if any(k in n for k in _PREMIUM_NAMES) else 0


# Set categories that DON'T enhance damage. The engine can't total damage/accuracy,
# so the ILP would otherwise happily drop a taunt/defense set into an attack purely for
# its set BONUSES (recharge, etc.) — stripping the attack of damage AND accuracy, so it
# whiffs on +3/+4 and Fury never builds. An attack must DEAL DAMAGE: keep only
# damage-enhancing sets for it (damage cats + archetype/universal sets carry Acc/Dam;
# control sets like Holds/Immobilize stay, for control-attacks like Char/Ring of Fire).
_NON_DMG_ATTACK_CATS = {
    "Threat Duration", "Defense Sets", "Resist Damage", "Healing",
    "Accurate Healing", "To Hit Buff", "Endurance Modification",
    "Universal Travel", "Flight", "Jump", "Running", "Teleport", "Knockback",
    # Mez / debuff "mule" sets: the ILP loves them for their recharge/def set bonuses,
    # then leaves a real attack (Follow Through, Dark Blast, Shatter Armor) with ~0 damage
    # enhancement. A damage dealer's attacks must DEAL DAMAGE — block these as primary
    # slotting. Defense-Debuff sets (Shield Breaker, Touch of Lady Grey, Achilles) carry NO
    # damage enhancement, so they're pure mules in an attack; the valuable -Res procs they
    # source are added back later by proc_pass on the AURA + biggest AoE nuke, spawn-wide,
    # NOT as full sets in single-target attacks. (Holds/Immobilize stay ALLOWED below, for
    # control-attacks like Char / Ring of Fire where the "attack" IS the control.)
    "Stuns", "Sleep", "Confuse", "Fear",
    "To Hit Debuff", "Accurate To-Hit Debuff", "Slow Movement",
    "Defense Debuff", "Accurate Defense Debuff",
}

# Categories whose pieces actually ENHANCE damage — used to reward slot allocation toward
# the hardest-hitting attacks on a damage build (so a premium attack gets a full damage set,
# not 2 mule slots). Archetype sets in an attack are damage ATOs (Brute's Fury, etc.).
_DMG_SET_CATS = {
    "Melee Damage", "Ranged Damage", "PBAoE Damage", "Targeted AoE Damage",
    "Sniper Attacks", "Pet Damage", "Universal Damage",
}
# Weight on the per-attack damage reward. Tuned to sit ABOVE the 0.003/slot penalty (so the
# solver pours leftover slots into attacks instead of perk mules) but BELOW the survival
# coverage weights (so hard defense/resist targets are still hit first). Scaled per attack by
# its base damage / the build's hardest hit, so premium attacks win the slots.
_DMG_REWARD_W = 0.05


def _is_dmg_cat(cat):
    return cat in _DMG_SET_CATS or (isinstance(cat, str) and cat.endswith("Archetype Sets"))


# Bonus KINDS a non-damage role is happy to HARVEST from a damage set. The masters slot Winter sets
# (Frozen Blast / Winter's Bite) and ATOs on the control powers BECAUSE those "damage" sets carry
# defense + recharge + recovery bonuses — the controller's whole survival/uptime engine from one
# slot budget. The damage ENHANCEMENT is wasted, but the bonuses are gold, so such a set is NOT a
# wasted mule and must be EXEMPT from the non-damage-role damage penalty.
_HARVEST_KINDS = {"Defense", "Resistance", "RechargeTime", "Recovery", "Regeneration", "HitPoints"}


def _candidate_sets(sets_by_category, cat_ids, is_attack, allow_premium=True):
    out = []
    seen = set()
    for cid in cat_ids:
        for s in sets_by_category.get(cid, []):
            if s["uid"] in seen:
                continue
            seen.add(s["uid"])
            if not allow_premium and set_cost_rank(s) >= 2:
                continue
            out.append(s)
    if is_attack:
        dmg = [s for s in out if s.get("category") not in _NON_DMG_ATTACK_CATS]
        if dmg:                    # fall back to full list for pure-utility "attacks"
            return dmg             # (Taunt/Provoke) that genuinely have no damage set
    return out


def _find_set(sets_by_category, cat_ids, set_name):
    nl = set_name.lower()
    for cid in cat_ids:
        for s in sets_by_category.get(cid, []):
            if nl in s["name"].lower():
                return s
    return None


def _global_piece(srec, g):
    for pc in srec.get("pieces", []):
        if g["piece"] in pc["name"].lower():
            return pc["name"]
    return srec["pieces"][0]["name"] if srec.get("pieces") else g["piece"]


def _global_piece_uid(srec, g):
    for pc in srec.get("pieces", []):
        if g["piece"] in pc["name"].lower():
            return pc.get("uid")
    return srec["pieces"][0].get("uid") if srec.get("pieces") else None


def _commit_set(p, srec, n, sigs, contrib, used_sig, totals):
    pieces = srec.get("pieces", [])[:n]
    for pc in pieces:
        p["_slots"].append({"set_uid": srec["uid"], "set_name": srec["name"],
                            "piece_name": pc["name"], "piece_uid": pc.get("uid"),
                            "category_id": srec["category_id"]})
    for s in sigs:
        used_sig[s] += 1
    for k, v in contrib.items():
        totals[k] += v


def _options_for_power(p, sets_by_category, targets, perks, piece_choices,
                       allow_premium=False, pvp=False):
    """Candidate (set, n-pieces) slotting options for a power. An option is
    functional by construction (a category-fitting set covers the power's
    aspects). Phase 1 solves CHEAP-only (allow_premium=False); the upgrade pass
    introduces premium sets. Prunes to sets that contribute to a target/perk;
    attacks always keep a few options so they get a real set. `pvp` selects the
    PvP set-bonus set."""
    cand = _candidate_sets(sets_by_category, p["_cats"], p["_is_attack"],
                           allow_premium=allow_premium)
    must_set = p.get("_must_set")
    armor = p.get("_armor_res") or p.get("_armor_def")
    base_rd = p.get("_base_rd") or {}
    armor_kind = "Resistance" if p.get("_armor_res") else "Defense"
    opts = []
    for srec in cand:
        contrib6, _ = _set_bonus_contrib(srec, 6, {}, pvp)
        touches = any(k in targets or k in perks for k in contrib6)
        # armor toggles keep their res/def-set options even if the BONUSES don't touch
        # a target — the ENHANCEMENT (credited below) does.
        if not touches and not p["_is_attack"] and not must_set and not armor:
            continue
        for n in piece_choices:
            if n > 6 or (must_set and not armor and n > 4):  # buff must-sets stay small; armor sizes up
                continue
            contrib, sigs = _set_bonus_contrib(srec, n, {}, pvp)
            # Credit the res/def this set ENHANCES in the host armor toggle (base ×
            # ED-aware factor for n pieces) toward the matching target — so the ILP
            # values a 5-6 piece res set in the toggle, not the 3 it'd pick for bonuses.
            if armor and base_rd:
                f = _ED_RESDEF.get(min(n, 6), 0.0)
                for (kk, t), base in base_rd.items():
                    if kk == armor_kind:
                        contrib[(kk, t)] += base * f
            opts.append({"set": srec, "n": n, "contrib": contrib, "sigs": sigs})
    if p["_is_attack"] and not any(o["n"] >= 5 for o in opts):
        # ensure attacks have at least one full functional set option
        for srec in cand[:3]:
            contrib, sigs = _set_bonus_contrib(srec, 6, {}, pvp)
            opts.append({"set": srec, "n": 6, "contrib": contrib, "sigs": sigs})
    elif must_set and not opts:
        # ensure a forced buff has at least one (small) set option
        for srec in cand[:3]:
            contrib, sigs = _set_bonus_contrib(srec, 3, {}, pvp)
            opts.append({"set": srec, "n": 3, "contrib": contrib, "sigs": sigs})
    return opts


# Plain-language perk focuses -> the stat keys the solver can actually push.
# (Damage/buffs aren't in the engine's totals, so they're not offered here.)
PERK_FOCUS = {
    "hp": [("HitPoints", None)],
    "recovery": [("Recovery", None)],
    "regen": [("Regeneration", None)],
    "recharge": [("RechargeTime", None)],
    "defense": [("Defense", t) for t in DEF_TYPES],
    "resistance": [("Resistance", t) for t in RES_TYPES],
}


# Player-facing "what should we base this build on?" roles. Each role tilts the
# solve two ways: `mult` scales the objective weight on a stat KIND (so spare
# slots chase the role's payoff), and `cats` nudges set selection toward the
# role's enhancement-set categories (so the build leans damage / heal / buff /
# debuff in the IO sets it actually picks). Blendable — pass several.
ROLE_DEFS = {
    "damage": {
        "label": "Deal more damage",
        "mult": {"RechargeTime": 2.0},     # faster attack cycle = more DPS
        "cats": {"Melee Damage", "Ranged Damage", "PBAoE Damage",
                 "Targeted AoE Damage", "Sniper Attacks", "Pet Damage",
                 "Universal Damage"},
    },
    "healing": {
        "label": "Heal better",
        "mult": {"Regeneration": 2.0, "Recovery": 1.6, "HitPoints": 1.4},
        "cats": {"Healing", "Accurate Healing"},
    },
    "buffing": {
        "label": "Buff allies better",
        "mult": {"ToHit": 1.6, "Recovery": 1.4},
        "cats": {"To Hit Buff", "Defense Sets", "Endurance Modification",
                 "Healing", "Accurate Healing"},
    },
    "debuffing": {
        "label": "Debuff enemies better",
        "mult": {"ToHit": 1.4},
        "cats": {"To Hit Debuff", "Accurate To-Hit Debuff", "Defense Debuff",
                 "Accurate Defense Debuff", "Slow Movement"},
    },
    "controlling": {
        "label": "Control / lock down better",
        # recharge IS the controller's payoff — perma-control means everything is locked,
        # which is also the controller's survival. Lean into control IO sets.
        "mult": {"RechargeTime": 2.2},
        "cats": {"Holds", "Confuse", "Immobilize", "Sleep", "Stuns", "Fear",
                 "Controller Archetype Sets", "Dominator Archetype Sets"},
    },
    "survival": {
        "label": "Survive better",
        "mult": {"Defense": 1.8, "Resistance": 1.8, "HitPoints": 1.5,
                 "Regeneration": 1.3},
        "cats": {"Defense Sets", "Resist Damage", "Healing"},
    },
    "recharge": {
        "label": "Recharge powers faster",
        "mult": {"RechargeTime": 2.2},
        "cats": {"Recharge Intensive Pets"},
    },
}


# Common IO uids/names (stable Mids ids) for slotting set-less buff powers.
_CIO = {
    "recharge": ("Crafted_Recharge", "Recharge Reduction IO"),
    "accuracy": ("Crafted_Accuracy", "Accuracy IO"),
    "heal": ("Crafted_Heal", "Healing IO"),
    "endmod": ("Crafted_Recovery", "Endurance Modification IO"),
    "tohit": ("Crafted_ToHit_Buff", "To Hit Buff IO"),
}
_BUFF_SLOT_BUDGET = 10     # cap common-IO slots for set-less buffs (Fulcrum/Siphon Power)

# accepted-enhancement-type (lowercased) -> a generic common IO that enhances it.
# Used to fill any leftover ALLOCATED slot so it's never left empty (a blank slot is
# wasted investment the user can't reclaim without a respec).
_TYPE_TO_CIO = {
    "damage": ("Crafted_Damage", "Damage IO"),
    "accuracy": ("Crafted_Accuracy", "Accuracy IO"),
    "recharge reduction": ("Crafted_Recharge", "Recharge Reduction IO"),
    "endurance reduction": ("Crafted_Endurance_Discount", "Endurance Reduction IO"),
    "endurance modification": ("Crafted_Recovery", "Endurance Modification IO"),
    "healing": ("Crafted_Heal", "Healing IO"),
    "defense buff": ("Crafted_Defense_Buff", "Defense IO"),
    "resist damage": ("Crafted_Res_Damage", "Resist Damage IO"),
    "resistance": ("Crafted_Res_Damage", "Resist Damage IO"),
    "to hit buff": ("Crafted_ToHit_Buff", "To Hit Buff IO"),
    "to hit debuff": ("Crafted_ToHit_DeBuff", "To Hit Debuff IO"),
    "defense debuff": ("Crafted_Defense_DeBuff", "Defense Debuff IO"),
    "slow": ("Crafted_Snare", "Slow IO"),
    "hold": ("Crafted_Hold", "Hold IO"),
    "immobilize": ("Crafted_Immobilize", "Immobilize IO"),
    "stun": ("Crafted_Stun", "Stun IO"),
    "confuse": ("Crafted_Confuse", "Confuse IO"),
    "fear": ("Crafted_Fear", "Fear IO"),
    "sleep": ("Crafted_Sleep", "Sleep IO"),
    "taunt": ("Crafted_Taunt", "Taunt IO"),
    "range": ("Crafted_Range", "Range IO"),
    "knockback": ("Crafted_Knockback", "Knockback IO"),
    "fly": ("Crafted_Fly", "Fly IO"),
    "running": ("Crafted_Run", "Run IO"),
    "jumping": ("Crafted_Jump", "Jump IO"),
}
# round-robin priority so a power gets a useful SPREAD (e.g. dmg/acc/rech/endrdx on an
# attack) instead of stacking one type into ED diminishing returns.
_CIO_FILL_PRIORITY = [
    "damage", "accuracy", "recharge reduction", "defense buff", "resist damage",
    "resistance", "healing", "endurance modification", "to hit buff", "hold",
    "immobilize", "stun", "confuse", "fear", "sleep", "taunt", "defense debuff",
    "endurance reduction", "range", "fly", "jumping", "running", "knockback",
]
# EFFECTS-FIRST order for single-slot fills on non-attack utility powers (armor/debuff
# toggles): the power's defining aspect leads, with recharge/end as last resort. Unlike
# _CIO_FILL_PRIORITY (attack-tuned: dmg/acc/rech first), this never wastes the lone slot
# on recharge when the power actually does resist / defense / a debuff.
_FILL_PRIMARY = [
    "resist damage", "resistance", "defense buff", "defense debuff", "to hit debuff",
    "slow", "healing", "hold", "immobilize", "stun", "confuse", "fear", "sleep", "taunt",
    "endurance modification", "to hit buff", "damage", "accuracy", "knockback", "range",
    # toggles (e.g. Assault) prefer EndRdx over Recharge — recharge does nothing on an
    # always-on power; a recharge-gated CLICK gets recharge via the want=3 branch instead.
    "endurance reduction", "recharge reduction", "fly", "jumping", "running",
]


def _cio_slot(kind):
    uid, name = _CIO[kind]
    return {"set_uid": None, "set_name": "Common IO", "piece_uid": uid,
            "piece_name": name, "category_id": None}


def _slot_buff_powers(powers, slots_left):
    """Reserve common-IO slots on the build's recharge-gated buff/heal/debuff CLICK
    powers (they accept no IO sets). Heavy Recharge for uptime + Accuracy to land +
    Heal/EndMod where fitting. Returns slots consumed. Needs each power to carry
    `base_recharge` and `accepted_enhancement_types` (enriched server-side)."""
    cand = []
    for p in powers:
        if p.get("_is_attack"):
            continue
        # ONLY powers that accept NO IO sets (e.g. Fulcrum Shift, Siphon Power, Hasten)
        # need common IOs — every other buff/heal takes a real SET (whose bonuses serve
        # survival/recharge), so the ILP handles those. Common IOs give no bonuses, so a
        # slot here is "dead" beyond the power's own enhancement — keep it minimal and
        # never steal slots from the set-bonus engine.
        if p.get("accepted_set_category_ids"):
            continue
        rch = p.get("base_recharge") or 0
        types = {t.lower() for t in (p.get("accepted_enhancement_types") or [])}
        if rch < 8 or "recharge reduction" not in types:
            continue              # toggles/passives/fire-and-forget buffs
        already = len(p["_slots"])
        cand.append((rch, p, types, already))
    # the support set's OWN buffs first (they are the point), heals ahead of the rest
    # (survival-critical); generic recharge clicks (Hasten) get the leftover, capped.
    cand.sort(key=lambda c: (0 if c[1].get("_buff_priority") else 1,
                             0 if "healing" in c[2] else 1, -c[0]))

    spent = 0
    for rch, p, types, already in cand:
        if spent >= _BUFF_SLOT_BUDGET or slots_left - spent <= 0:
            break
        # these slots give no set bonuses, so keep them lean — just enough recharge
        # (ED-limited) + accuracy; global recharge from the attack sets does the rest.
        priority = p.get("_buff_priority")
        target = 4 if (priority and rch >= 30) else 3
        # respect the player's allocated slot count on imported builds (_slot_budget),
        # so a set-less buff never grows past the layout the user actually made.
        target = min(target, int(p.get("_slot_budget") or p.get("max_slot_count") or 6))
        need = target - already
        if need <= 0:
            continue
        need = min(need, _BUFF_SLOT_BUDGET - spent, slots_left - spent)
        if need <= 0:
            continue
        # priority order of enhancement kinds by the power's job; take the first
        # `need` the power actually accepts.
        is_heal = "healing" in types
        restores_end = ("endurance modification" in types) and not is_heal and rch >= 20
        if is_heal:                         # Transfusion: heal + uptime, must land
            order = ["heal", "recharge", "accuracy", "heal", "recharge", "heal"]
        elif restores_end:                  # Transference: team endurance + uptime
            order = ["endmod", "recharge", "accuracy", "endmod", "recharge"]
        elif "to hit buff" in types:        # Fulcrum Shift: heavy recharge for perma
            order = ["recharge", "accuracy", "recharge", "recharge", "recharge"]
        else:                               # Siphon Speed/Power etc.: land + recharge
            order = ["accuracy", "recharge", "recharge", "recharge", "recharge"]
        ok = {"recharge": "recharge reduction", "accuracy": "accuracy",
              "heal": "healing", "endmod": "endurance modification",
              "tohit": "to hit buff"}
        mix = [k for k in order if ok[k] in types][:need]
        if not mix:
            continue
        if "recharge" not in mix and "recharge reduction" in types:
            mix[-1] = "recharge"            # always at least 1 recharge for uptime
        for kind in mix:
            p["_slots"].append(_cio_slot(kind))
        spent += len(mix)
    return spent


def solve_ilp(powers, targets_pct, sets_by_category, piece_globals, base_totals,
              slot_cap=67, tier="premium", perk_focus=None, roles=None, pvp=False,
              preserve=False, keep_layout=False, archetype=None):
    """Optimal slot solve via integer linear programming.

    Phase 1 solves the targets with CHEAP sets only (the least-expensive build
    that meets the need). Phase 2 is a tier-gated UPGRADE pass: it swaps those
    same placements for premium (purple/ATO/Winter/PvP) sets that still satisfy
    the targets but add extra value — the common->very-rare upgrade IS the whole
    budget->premium cost difference, on the same skeleton. budget = no upgrade,
    balanced = upgrade only where it still advances a target, premium = upgrade
    wherever it adds value. Requires PuLP."""
    if pulp is None:
        raise RuntimeError("PuLP not installed")
    targets = normalize_targets(targets_pct)
    totals = defaultdict(float, dict(base_totals or {}))
    slots_left = slot_cap
    buffing = "buffing" in (roles or [])
    for p in powers:
        p["_slots"] = []
        p["_cats"] = set(p.get("accepted_set_category_ids", []))
        cats = p.get("accepted_set_categories", [])
        # Imported preserve/keep-layout builds: cap each power at the slots the player
        # ACTUALLY allocated (filled+empty = _earned), so the solve upgrades IOs only
        # WITHIN the player's own layout — it never adds or silently drops slots. Only
        # a full re-slot (neither preserve nor keep-layout) lets a power grow to 6.
        cap_layout = (keep_layout or preserve) and p.get("_earned")
        p["_slot_budget"] = min(6, int(p["_earned"])) if cap_layout else 6
        # Slot-schedule cap (set by the caller after an infeasible pick-level pass):
        # a power stuck in the pick ladder's tail can only receive the few slots the
        # game still grants there — e.g. a level-49 pick holds at most 4.
        if p.get("_sched_budget") is not None:
            p["_slot_budget"] = min(p["_slot_budget"], max(1, int(p["_sched_budget"])))
        # Inherent utility powers (Brawl/Sprint/Rest/prestige sprints/Swift/Hurdle) gain
        # nothing from slotting. Brawl even accepts "Damage Increase", so a full re-slot
        # would dump a damage SET into it to farm bonuses. Cap their budget to the real
        # SET pieces the player already put there (0 for the usual generics-only case),
        # so the ILP/globals/perk/common-fill can never ADD to them, yet a genuine
        # investment like a Celerity +Stealth proc in Sprint survives. (Health/Stamina
        # are excluded — they take real procs/uniques and stay fully slottable.)
        if _is_no_enhance_inherent(p):
            p["_slot_budget"] = sum(
                1 for s in (p.get("_existing_slots") or []) if s and s.get("set_uid"))
        # Fighting-pool prereq (Boxing/Kick) on a non-melee AT: cap at its 1 free slot so the
        # solver can't sink a set into a dead attack — it must harvest bonuses in real powers
        # (matches 100% of ranged/support masters). Skip on imported preserve/keep-layout builds,
        # where we respect the player's own layout.
        if (not cap_layout and archetype not in _MELEE_FIGHTING_ATS
                and p.get("full_name") in _FIGHTING_PREREQS):
            p["_slot_budget"] = 1
        p["_is_attack"] = bool(p.get("is_attack")) or any(c in ATTACK_CATS for c in cats)
        # support: a signature buff CLICK that accepts sets must end up functionally
        # slotted with one (its bonuses serve recharge/recovery + the power works) even
        # when the survival objective wouldn't pick it — same "must take a set" rule as
        # attacks. Trades a little attack survival for working buffs (what a passive
        # support bot wants). Capped at 4 pieces so the trade stays small.
        p["_must_set"] = (buffing and not p["_is_attack"] and p.get("_buff_priority")
                          and bool(p.get("accepted_set_category_ids"))
                          and (p.get("base_recharge") or 0) >= 8)
        # A signature DEBUFF power (Envenom, Weaken…) must be functionally slotted when the role
        # is debuffing: its −def/−tohit IS enhanceable (unlike −res), but debuff magnitude isn't a
        # solver target, so the ILP left Envenom at ONE slot (measured). Same principle as buff
        # clicks and armor toggles: the role's working powers get their working sets — which also
        # opens the Achilles' Heel −res proc home the in-game standard slotting uses.
        if ("debuffing" in (roles or []) and not p["_is_attack"]
                and set(cats) & _DEBUFF_SET_CATS):
            p["_must_set"] = True
        # Armor res/def TOGGLE: the ILP otherwise sizes its set for BONUSES only and
        # leaves the toggle under-enhanced (S/L res stalls short of cap). Flag it so
        # _options_for_power credits the res/def each set ENHANCES in it — making the
        # ILP size that set up to actually cap the survival floor.
        _types = {t.lower() for t in (p.get("accepted_enhancement_types") or [])}
        # Recharge gate: native armor toggles store ~0-4s (< 8 as always), but SQUISHIES' epic
        # shields (Scorpion/Frozen/Charged Armor) store exactly 8.0 — `< 8` silently excluded them,
        # so the patron shield never got the armor-enhancement credit and sat at 1 slot, unenhanced.
        # Widened to <= 10 for squishies ONLY — armored ATs keep their tuned behavior untouched.
        _arm_rt = 10.5 if archetype not in _ARMOR_NATIVE_ATS else 8
        p["_armor_res"] = (p.get("power_type") == 2 and not p["_is_attack"]
                           and (p.get("base_recharge") or 0) < _arm_rt and "resist damage" in _types)
        p["_armor_def"] = (p.get("power_type") == 2 and not p["_is_attack"]
                           and (p.get("base_recharge") or 0) < _arm_rt and "defense buff" in _types
                           and not p["_armor_res"])
        # Squishy AT + armor toggle (the epic shield case): floor it at 2 enhanced pieces — no
        # master buys a patron shield and leaves it raw. Native-armor ATs are exempt: forcing 2pc
        # into every one of a Tanker's five toggles steals slots from its payoff (measured).
        p["_armor_min2"] = ((p["_armor_res"] or p["_armor_def"])
                            and archetype not in _ARMOR_NATIVE_ATS)

    # Imported preserve/keep-layout: the global budget is the player's own allocated
    # slots, not 67 — the solve stays within the build the user actually made.
    if (keep_layout or preserve) and any(p.get("_earned") for p in powers):
        slot_cap = sum(p["_slot_budget"] for p in powers)
        slots_left = slot_cap

    # uid -> set record (same shape the ILP uses) for crediting locked sets.
    set_by_uid = {}
    for _cat in sets_by_category.values():
        for _s in _cat:
            set_by_uid.setdefault(_s["uid"], _s)
    # piece uid -> (is_unique, mutex_key). The mutex_key collapses a set's regular
    # and Superior forms so the ILP never slots both anywhere (un-buildable).
    piece_meta = {}
    for _s in set_by_uid.values():
        for _pc in _s.get("pieces", []):
            if _pc.get("uid"):
                piece_meta[_pc["uid"]] = (_pc.get("unique", False),
                                          _mutex_key(_s.get("name"), _pc.get("name")))

    # PRESERVE mode (the default "complete my fit"): keep the build's existing set
    # IOs + unique globals, re-solving ONLY the freed generic/empty slots. Pre-place
    # the locked sets and credit their bonuses so the ILP fills around them, never
    # removing what the user already invested in.
    kept_sets, present_globals = [], set()
    if preserve:
        locked, kept_sets, present_globals = _preserve_locked(
            powers, set_by_uid, piece_globals, totals, pvp)
        slots_left -= locked

    # Phase 0: place the cheap high-value unique globals (1 slot) into base —
    # but in preserve mode don't re-place a unique global the build already has.
    _place_globals(powers, piece_globals, sets_by_category, totals,
                   seed_unique=present_globals)
    used_global_slots = sum(len(p["_slots"]) for p in powers) - sum(
        1 for p in powers for s in p["_slots"] if s.get("_locked"))
    slots_left -= used_global_slots

    # Phase 0b (support): the signature buff/heal/debuff CLICK powers (Fulcrum
    # Shift, Transfusion, Transference, Siphon Speed/Power, Hasten...) accept NO IO
    # sets — only common enh types — so the set-based ILP never slots them. For a
    # buffing build, reserve common-IO slots on them (heavy Recharge for uptime +
    # Accuracy to land + Heal/EndMod as fitting) BEFORE the ILP, so they're actually
    # good and the rest of the budget still solves survival.
    if "buffing" in (roles or []):
        slots_left -= _slot_buff_powers(powers, slots_left)

    perks = {}
    for k, cap in ((("Regeneration", None), 3.0), (("Recovery", None), 1.5),
                   (("HitPoints", None), 0.6), (("RechargeTime", None), 3.0)):
        perks[k] = cap
    for t in DEF_TYPES:
        perks[("Defense", t)] = 0.60

    # Tier controls premium-set use, via the ILP itself (robust + optimal):
    #  budget   = cheap sets only (cheapest build that meets the need)
    #  balanced = premium allowed but heavily penalized (only where clearly better)
    #  premium  = premium allowed, tiny penalty (use purples wherever they add value)
    allow_premium = tier in ("balanced", "premium")
    cost_w = {"budget": 0.0, "balanced": 0.06, "premium": 0.004}.get(tier, 0.004)

    # Player roles ("what should we base this build on?") → kind multipliers +
    # set-category preferences. Blend several; each contributes its tilt.
    roles = [r for r in (roles or []) if r in ROLE_DEFS]
    # DAMAGE-HYBRID archetypes — their payoff is control/support AND DAMAGE (a Dominator's Assault
    # secondary, a Corruptor's Scourge blasts). Solved as pure control/support they get the
    # non-damage penalty on their attacks and under-slot damage (benchmark: Dom st_dps 116 vs master
    # 155). Add the damage role so their attacks slot for damage while the control/support powers keep
    # their sets — recharge still leads (perma-dom/perma-buffs) via the control/support recharge block.
    if archetype in _DAMAGE_HYBRID_ATS and "damage" not in roles:
        roles = roles + ["damage"]
    kind_mult = defaultdict(lambda: 1.0)
    pref_cats = set()
    for r in roles:
        rd = ROLE_DEFS[r]
        for kind, m in rd["mult"].items():
            kind_mult[kind] = max(kind_mult[kind], m)
        pref_cats |= rd["cats"]
    kind_mult = dict(kind_mult)

    # Per-target PRIORITY: the objective weights a target by 1/target, so a HARD, high
    # target (Fire res 75 on a fire farm) is worth LESS per point than an easy one
    # (recharge 50, S/L res 60) — so the solver caps the easy ones and spends the rare
    # res/def sets (Winter's Bite = Fire/Cold res) nowhere. Lift the high survival
    # targets so they outweigh the incidental ones and pull those sets onto the attacks.
    priority = {}
    for k, tgt in targets.items():
        if k[0] in ("Resistance", "Defense"):
            priority[k] = 3.0 if tgt >= 0.7 else 2.0 if tgt >= 0.6 else 1.0
            # POSITIONAL defense (Ranged/AoE/Melee) is a squishy's real survival route, but a TYPED
            # def toggle (Scorpion Shield = S/L/E) satisfies the per-KIND "Defense" weight without
            # touching it — so the solver settles for typed def and leaves positional short. Lift the
            # positional targets specifically so it HARVESTS them (Winter's Bite/Frozen Blast + the
            # 6th-piece control-set bonuses: Coercive 6pc=Rng+5, Frozen 6pc=AoE+7.5).
            if k[0] == "Defense" and k[1] in ("Ranged", "AoE", "Melee"):
                priority[k] = max(priority[k], 4.0)
            # v24 meta: the TYPED quad (S/L/F/C ~35) is now the default survival route —
            # give an explicitly-targeted typed def the same lift, or the ILP funds cheap
            # abundant S/L riders and leaves scarce Fire/Cold (winter 6-pieces) unfunded.
            if (k[0] == "Defense" and k[1] in ("Smashing", "Lethal", "Fire", "Cold")
                    and tgt >= 0.30):
                priority[k] = max(priority[k], 4.0)
    # RECHARGE is targeted high (90-100%), so its per-target weight (÷1.0) is tiny next to a
    # 0.45 def target (÷0.45) — phase 1 caps def and spends NOTHING on recharge, leaving the
    # recharge perk-pass no slots. But EATs (perma-pets/Hasten), controllers (perma-control)
    # and damage (AoE cycling) all LIVE on recharge, and masters stack 100%+ from 5× LotG
    # globals + purple/recharge sets. Lift recharge so it competes in phase 1 and the solver
    # actually buys those globals + recharge-dense sets.
    if ("RechargeTime", None) in targets:
        priority[("RechargeTime", None)] = max(priority.get(("RechargeTime", None), 0.0), 4.0)

    # TYPED-DEF ROUTE (squishies only): when a squishy's build carries a def ARMOR TOGGLE (an epic
    # shield — Scorpion Shield = S/L/E), ITS types are the build's reachable soft-cap route —
    # masters enhance the shield and cap those. Without a lift, a typed target sits at priority 1.0
    # (vs positional 4.0 / recharge 12), so the ILP left the shield at ONE slot: a patron unlock
    # bought and never enhanced. Lift the toggle's own def types to positional parity so enhancing
    # the shield + typed bonuses actually competes. Armored ATs keep their tuned positional routes.
    if archetype not in _ARMOR_NATIVE_ATS:
        for p in powers:
            for (kind, ty), v in (p.get("_base_rd") or {}).items():
                if kind == "Defense" and v >= 0.05 and ("Defense", ty) in targets:
                    priority[("Defense", ty)] = max(priority.get(("Defense", ty), 0.0), 4.0)

    # SUPPORT / CONTROL ROLES — role OUTPUT is the payoff AND the survival (invisible-role
    # doctrine), and that output lives on UPTIME: perma-control, perma-debuff (Rad's AM, Cold's
    # Heat Loss), perma-buff (Kin's Fulcrum), fast-recast heals — all recharge-driven. But the
    # ÷target normalization makes a 0.45 def target out-weigh a 1.0 recharge target ~2x, so the
    # solver caps defense and leaves uptime short (measured: controllers matched masters on control
    # SELECTION but slotted for defense, stalling recharge ~90%). So for these roles recharge LEADS
    # positional defense — recharge-dense role sets (Basilisk's/Lockdown/purples for control; the
    # debuff/buff sets) land in the ACTUAL role powers, buying uptime AND enhancing the effect.
    # Defense stays a harvested bonus (LotG mules still give def+recharge), just no longer primary.
    # Benchmark evidence: the best masters get BOTH high defense AND perma-control by slotting
    # DUAL-PURPOSE sets (LotG = def+global recharge, Winter/purples = def bonus + recharge). So we
    # make recharge LEAD (perma-uptime is the payoff) but do NOT suppress defense — the solver
    # should still value def so it harvests those def+recharge sets, not pure-recharge ones. With
    # recharge target 1.5 (frac): recharge weight 12*2.2/1.5=17.6 just edges positional def
    # 4*1.8/0.45=16 → recharge tips the tie, defense stays strongly pursued.
    _SUPPORT_CONTROL = {"controlling", "debuffing", "buffing"}
    if _SUPPORT_CONTROL & set(roles):
        targets[("RechargeTime", None)] = max(targets.get(("RechargeTime", None), 0.0), 1.5)
        priority[("RechargeTime", None)] = 12.0
    elif "healing" in roles:
        # Healers live on recharge too (recast heals/buffs), but keep heal/regen for the team.
        priority[("RechargeTime", None)] = max(priority.get(("RechargeTime", None), 0.0), 10.0)

    # PHASE 1: solve the targets. PHASE 2: fill remaining slots with perks. Both
    # honor the tier's premium policy (premium upgrades fall out of the solve).
    _ilp_pass(powers, targets, totals, sets_by_category, slot_cap,
              piece_choices=(6, 5, 4, 3, 2), objective_targets=targets,
              allow_premium=allow_premium, cost_w=cost_w, pref_cats=pref_cats, pvp=pvp,
              priority=priority, piece_meta=piece_meta)
    focus_keys = set(PERK_FOCUS.get(perk_focus, []))
    perk_kind_mult = dict(kind_mult)
    if focus_keys:                  # the 🧮 perk dial gets an outsized weight
        for k in focus_keys:
            perks[k] = max(perks.get(k, 0.0), 2.0)
            perk_kind_mult[k[0]] = max(perk_kind_mult.get(k[0], 1.0), 8.0)
    # Roles also open headroom on their stat kinds so spare slots have something
    # worth chasing (otherwise a saturated target leaves the multiplier inert).
    for r in roles:
        for kind in ROLE_DEFS[r]["mult"]:
            if kind == "HitPoints":
                continue
            for pk in list(perks):
                if pk[0] == kind:
                    perks[pk] = max(perks[pk], 2.0)
    _ilp_pass(powers, targets, totals, sets_by_category, slot_cap,
              piece_choices=(6, 5, 4, 3, 2), objective_targets=perks, perk_pass=True,
              allow_premium=allow_premium, cost_w=cost_w,
              kind_mult=perk_kind_mult, pref_cats=pref_cats, pvp=pvp, piece_meta=piece_meta)

    # DEFAULT: never drop a cheap IO for an empty slot — restore any the solve
    # didn't replace with a set (keeps Hasten/Fulcrum/etc. functional). Runs in
    # preserve & keep-layout (no-op otherwise, since _cheap_ios is only set then).
    _restore_cheap_ios(powers)

    # NO empty allocated slots: top every imported power up to its _earned count with
    # the best remaining value (extend its sets, else common IOs). A blank slot the
    # solve left behind would otherwise be wasted investment.
    slots_left = _fill_remaining_slots(powers, set_by_uid, slots_left)
    # GENERATED builds (auto-pick): no _earned layout, so the ILP leaves set-LESS or
    # low-priority powers (Hasten, toggles, skipped debuffs) with an empty base slot.
    # Give each a sensible common-IO slotting so nothing ships empty.
    slots_left = _fill_generated_empties(powers, slots_left)

    # In-game legality: slots BEYOND the first in each power must total <= 67
    # (each power's first slot is free). The restore above can push a few powers
    # over, so trim the least-valuable extras (fattest set powers first) to budget.
    added = _enforce_added_cap(powers, ADDED_SLOT_BUDGET)

    out_powers = _finalize_powers(powers)
    used = sum(len(p["_slots"]) for p in powers)
    return {"powers": out_powers, "totals": dict(totals),
            "report": _report(totals, targets, used, slot_cap), "slots_used": used,
            "added_slots": added, "added_budget": ADDED_SLOT_BUDGET,
            "kept_sets": kept_sets, "preserved": bool(preserve)}


ADDED_SLOT_BUDGET = 67     # slots beyond each power's free base slot (MidsReborn MaxSlots)


def _added_slots(powers):
    return sum(max(0, len(p["_slots"]) - 1) for p in powers if p["_slots"])


def _restore_cheap_ios(powers):
    """DEFAULT RULE (always on): a cheap/generic IO is swapped out only when a
    goal-advancing SET actually takes its place — it's never dropped for an empty
    slot. After the ILP fills what it can, back-fill each power with its ORIGINAL
    cheap IOs that no new set replaced, so a power never ends up with fewer
    enhancements than it started (critical for set-LESS powers like Hasten,
    Fulcrum Shift, Siphon Speed that accept no IO sets). Bounded by the power's
    own cheap count + slot budget, so it never invents slots or exceeds the layout."""
    for p in powers:
        cheap = p.get("_cheap_ios") or []
        if not cheap:
            continue
        locked = sum(1 for s in p["_slots"] if s.get("_locked"))
        added_by_solve = len(p["_slots"]) - locked      # sets/globals the solve placed
        room = p.get("_slot_budget", 6) - len(p["_slots"])
        n = min(len(cheap) - added_by_solve, room)       # only the cheap IOs nothing replaced
        for s in cheap[:max(0, n)]:
            p["_slots"].append({
                "set_uid": None, "set_name": s.get("set_name") or "Invention",
                "piece_name": s.get("piece_name"), "piece_uid": s.get("piece_uid"),
                "category_id": None, "io_level": s.get("io_level")})


def _fill_commons(p, n):
    """n common-IO slot dicts spread across the power's accepted enhancement types."""
    types = {t.lower() for t in (p.get("accepted_enhancement_types") or [])}
    ordered = [t for t in _CIO_FILL_PRIORITY if t in types and t in _TYPE_TO_CIO]
    if not ordered:
        ordered = ["recharge reduction"]      # universal fallback (every power recharges)
    out = []
    i = 0
    while len(out) < n:
        uid, name = _TYPE_TO_CIO[ordered[i % len(ordered)]]
        out.append({"set_uid": None, "set_name": "Common IO", "piece_uid": uid,
                    "piece_name": name, "category_id": None, "io_level": 50, "_fill": True})
        i += 1
    return out


# Inherent "utility" powers gain nothing from enhancement — Brawl, Sprint, Rest, Walk,
# the prestige sprints, and the run/jump Fitness pair (Swift/Hurdle). NEVER junk-fill
# these with common IOs: it wastes the slot AND overwrites what the player had (e.g.
# Sprint's run IO → a useless generic). Health & Stamina are the ONE exception — they
# take real uniques/procs (Numina/Miracle/Panacea, Performance Shifter/Power Transfer).
_SLOTTABLE_INHERENTS = {"Inherent.Fitness.Health", "Inherent.Fitness.Stamina"}


def _is_no_enhance_inherent(p):
    fn = p.get("full_name") or ""
    if fn in _SLOTTABLE_INHERENTS:
        return False
    return fn.startswith("Inherent.")


def _fill_remaining_slots(powers, set_by_uid, slots_left):
    """NO allocated slot is left empty (a blank slot is wasted investment that needs a
    respec to reclaim). Fill each imported power's remaining slots (up to _earned) with
    the best available value: first EXTEND any set already in the power toward its full
    piece count — its higher set bonuses (5th/6th piece) are real value the perk pass
    skipped because they weren't a target stat — then back-fill with common IOs that
    enhance the power. The engine re-derives all bonuses from the final slots, so this
    pass only places pieces; it never has to touch the running totals."""
    for p in powers:
        earned = p.get("_earned")
        if not earned:
            continue                            # generated builds allocate as they fill
        if _is_no_enhance_inherent(p):
            continue                            # never junk-fill Brawl/Sprint/Rest/etc.
        free = int(earned) - len(p["_slots"])
        if free <= 0 or slots_left <= 0:
            continue
        free = min(free, slots_left)
        used_pieces = {s.get("piece_uid") for s in p["_slots"] if s.get("piece_uid")}
        # 1) extend sets already in the power toward their full piece count
        have = Counter(s["set_uid"] for s in p["_slots"] if s.get("set_uid"))
        for suid, _cnt in have.most_common():
            if free <= 0:
                break
            srec = set_by_uid.get(suid)
            if not srec:
                continue
            # match the level/attunement of the set pieces already in this power
            sib = next((s for s in p["_slots"] if s.get("set_uid") == suid), {})
            for pc in srec.get("pieces", []):
                if free <= 0:
                    break
                if not pc.get("uid") or pc["uid"] in used_pieces:
                    continue
                p["_slots"].append({
                    "set_uid": srec["uid"], "set_name": srec.get("name"),
                    "piece_uid": pc["uid"], "piece_name": pc.get("name"),
                    "category_id": srec.get("category_id"),
                    "io_level": sib.get("io_level"), "attuned": sib.get("attuned"),
                    "_fill": True})
                used_pieces.add(pc["uid"])
                free -= 1
                slots_left -= 1
        # 2) common-IO back-fill for whatever still remains
        if free > 0:
            for cio in _fill_commons(p, free):
                p["_slots"].append(cio)
                slots_left -= 1
    return slots_left


def _fill_generated_empties(powers, slots_left):
    """Generated (auto-picked) builds carry no _earned layout, so the ILP leaves set-LESS
    powers (Hasten, Leadership/armor toggles, debuffs it didn't prioritize) sitting on an
    empty base slot. Fill each unslotted power with common IOs matching its best enhance
    types: a long-recharge click like Hasten gets up to 3 Recharge IOs (toward perma);
    everything else gets its single base slot filled. Never touches inherents, powers the
    ILP already set, or truly unslottable powers (no accepted enhancement types)."""
    for p in powers:
        if p.get("_earned") or _is_no_enhance_inherent(p):
            continue                              # imported / inherent: handled elsewhere
        if slots_left <= 0:
            break
        if any(s.get("piece_uid") or s.get("set_uid") for s in p["_slots"]):
            continue                              # ILP already slotted it
        types = {t.lower() for t in (p.get("accepted_enhancement_types") or [])}
        if not types:
            continue                              # e.g. Rest/Walk — nothing to enhance
        # A long-recharge click (Hasten) gets TWO Recharge IOs, never three — the third
        # is ED-crushed to ~13% of face value, a wasted slot (master rule: "never go past
        # two slots on Hasten"). Otherwise fill ONE slot with the power's DEFINING aspect —
        # an armor → Resist, a debuff toggle → its debuff — NOT a recharge filler.
        if "recharge reduction" in types and (p.get("base_recharge") or 0) >= 60:
            order, want = ["recharge reduction"], 2
        else:
            order = [t for t in _FILL_PRIMARY if t in types] or ["recharge reduction"]
            want = 1
        want = min(want, slots_left)
        p["_slots"] = [s for s in p["_slots"] if s.get("piece_uid") or s.get("set_uid")]
        for i in range(want):
            uid, name = _TYPE_TO_CIO.get(order[i % len(order)],
                                         _TYPE_TO_CIO["recharge reduction"])
            p["_slots"].append({"set_uid": None, "set_name": "Common IO", "piece_uid": uid,
                                "piece_name": name, "category_id": None, "io_level": 50,
                                "_fill": True})
            slots_left -= 1
    return slots_left


def _enforce_added_cap(powers, budget):
    """Trim extra slots until additional-slot count (slots beyond the first per
    power) <= budget. Removes from the most-slotted powers first, dropping only
    non-locked, non-global slots (keeps preserved sets + unique globals intact).
    Recomputes nothing — the engine re-derives totals from the trimmed slots."""
    while _added_slots(powers) > budget:
        removed = False
        for p in sorted((q for q in powers if len(q["_slots"]) > 1),
                        key=lambda q: len(q["_slots"]), reverse=True):
            for i in range(len(p["_slots"]) - 1, 0, -1):
                s = p["_slots"][i]
                if not s.get("_locked") and not s.get("_global"):
                    p["_slots"].pop(i)
                    removed = True
                    break
            if removed:
                break
        if not removed:        # nothing left to trim (all locked/global)
            break
    return _added_slots(powers)


def _ilp_pass(powers, targets, totals, sets_by_category, slot_cap, piece_choices,
              objective_targets, perk_pass=False, allow_premium=False, cost_w=0.0,
              kind_mult=None, pref_cats=None, pvp=False, priority=None, piece_meta=None):
    """Run one ILP over powers that still have free slots / no set yet.
    `kind_mult` weights a stat KIND (e.g. {'Defense':2}) so the player's role
    leans coverage that way; `pref_cats` nudges set selection toward role-fitting
    categories (e.g. damage/heal/debuff sets). `pvp` selects PvP set bonuses."""
    kind_mult = kind_mult or {}
    pref_cats = pref_cats or set()
    piece_meta = piece_meta or {}
    # Damage-build mode: when the role prefers damage categories, reward filling the real
    # attacks with damage sets (weighted by each attack's base hit) so the slots land on the
    # hardest hitters — not minimised to 1 set and spent on perk mules instead.
    dmg_mode = bool(pref_cats & _DMG_SET_CATS)
    # Role-based slotting: a CONTROL/DEBUFF/BUFF/HEAL build (a role is set, but not damage) gets
    # NOTHING from a power's damage enhancement, so a damage set there is just a wasted mule. Prefer
    # the role's sets (whose enhancement LANDS controls / lengthens holds / debuffs) and penalise
    # damage sets, so slotting serves the role — not damage the role never uses. (Survival set
    # bonuses still win where genuinely needed; proc_pass still adds Containment procs to controls.)
    non_damage_role = bool(pref_cats) and not dmg_mode

    def _uniq_key(pc):
        """(unique?, mutex_key) for a set piece — uses the mutex_key so a set's
        regular and Superior forms count as one identity."""
        return piece_meta.get(pc.get("uid"), (pc.get("unique", False),
                                              _mutex_key(None, pc.get("name"))))
    # Any power with a free slot is fair game — including ones Phase 1 already
    # gave a partial set to, so the perk pass can FRANKEN-fill their leftover
    # slots with a second set rather than waste them.
    free_powers = [p for p in powers if (p.get("_slot_budget", 6) - len(p["_slots"])) > 0]
    if not free_powers:
        return
    # hardest hit among the attacks still being slotted — normalises the damage reward so
    # a premium attack outbids a weak one for the same slot (0 ⇒ uniform fallback).
    max_base = max((p.get("_base_dmg", 0.0) for p in free_powers if p.get("_is_attack")),
                   default=0.0)
    used_now = sum(len(p["_slots"]) for p in powers)
    budget = slot_cap - used_now
    if budget <= 0:
        return

    prob = pulp.LpProblem("slots", pulp.LpMaximize)
    x = {}            # (pi, oi) -> binary
    opts_by_power = {}
    sig_terms = defaultdict(list)
    cov_upper = defaultdict(list)   # stat -> list of (coef, var)
    premium_terms = []              # (premium_pieces, var) for the cost penalty
    cat_terms = []                  # (pieces, var) for role-category preference
    dmg_terms = []                  # (base_weighted_pieces, var) for the attack-damage reward
    dmg_pen_terms = []              # (pieces, var) — damage sets to penalise on a non-damage role
    uniq_piece = defaultdict(list)  # unique mutex_key -> vars (≤1 PER CHARACTER)
    # unique pieces ALREADY placed (phase 0/1) — no later pass may place a piece
    # that mutex-conflicts with one (same identity, incl. regular vs Superior).
    placed_uniq = set()
    for p in powers:
        for s in (p["_slots"] or []):
            if not s or not s.get("piece_uid"):
                continue
            uq, mk = piece_meta.get(s["piece_uid"],
                                    (False, _mutex_key(s.get("set_name"), s.get("piece_name"))))
            if uq and mk:
                placed_uniq.add(mk)
    for pi, p in enumerate(free_powers):
        free = p.get("_slot_budget", 6) - len(p["_slots"])
        # Sets already in this power (from Phase 1 or a Phase-0 global): don't
        # re-pick them, and count them against the per-power franken cap.
        already = {s.get("set_uid") for s in p["_slots"] if s and s.get("set_uid")}
        remaining_sets = MAX_SETS_PER_POWER - len(already)
        choices = [n for n in piece_choices if n <= free]
        # Non-damage role: on a power where a damage set is pure waste — a Fighting-pool PREREQ
        # (Boxing/Kick) or a multi-minute utility CLICK (Dark Consumption 360s) — that power
        # should take its FUNCTIONAL set (a Stun set on the prereq, an Endurance-Modification set
        # on the endurance click), not a damage mule. But `_candidate_sets` strips non-damage
        # categories from ATTACKS, so those sets are never even offered. Re-evaluate the power as a
        # NON-attack (shallow copy) so its real categories surface, then keep only non-damage opts.
        force_func = False
        if non_damage_role and p.get("_is_attack"):
            is_pool_atk = (p.get("full_name") or "").startswith("Pool.")
            is_long_util = p.get("power_type") == 0 and (p.get("base_recharge") or 0) > 90
            # …OR any attack that accepts a stripped ROLE set (a -ToHit/-Def debuff or a mez set):
            # slotting it for the role beats a wasted damage set. `_cats` holds category IDs, so
            # resolve NAMES via the sets they group before testing the blocklist.
            cat_names = {s.get("category") for cid in (p.get("_cats") or [])
                         for s in sets_by_category.get(cid, [])}
            _AOE_DMG_NAMES = {"Targeted AoE Damage", "PBAoE Damage", "Melee AoE",
                              "Targeted AoE", "Player Melee AoE"}
            is_aoe_atk = bool(cat_names & _AOE_DMG_NAMES)
            has_role_alt = bool(cat_names & _NON_DMG_ATTACK_CATS)
            force_func = bool(is_pool_atk or is_long_util or has_role_alt)
        opt_src = dict(p, _is_attack=False) if force_func else p
        opts = _options_for_power(opt_src, sets_by_category, targets, objective_targets,
                                  choices, allow_premium=allow_premium, pvp=pvp)
        opts = [o for o in opts if o["n"] <= free and o["set"]["uid"] not in already
                and not any((lambda uq, mk: uq and mk in placed_uniq)(*_uniq_key(pc))
                            for pc in o["set"].get("pieces", [])[:o["n"]])]
        if remaining_sets <= 0:
            opts = []
        if force_func:
            non_dmg = [o for o in opts if not _is_dmg_cat(o["set"].get("category"))]
            # An AoE ATTACK gets only a SMALL secondary role set (≤2 pieces): a full 6-piece debuff
            # set on an occasional AoE nuke (Dark Obliteration) would steal 4 slots from the spammed
            # dedicated debuff (Weaken), which must stay fully slotted. A single-target prereq or a
            # utility click (Boxing, Dark Consumption) takes the full functional set — it competes
            # with nothing. (The freed slots return to the budget for a more beneficial home.)
            if is_aoe_atk:
                capped = [o for o in non_dmg if o["n"] <= 2]
                non_dmg = capped or non_dmg
            if non_dmg:
                opts = non_dmg
        opts_by_power[pi] = opts
        povars = []
        by_set = defaultdict(list)   # set_uid -> [vars] (one piece-count per set)
        for oi, o in enumerate(opts):
            v = pulp.LpVariable(f"x_{pi}_{oi}", cat="Binary")
            x[(pi, oi)] = v
            povars.append(v)
            by_set[o["set"]["uid"]].append(v)
            # UNIQUE pieces (attuned/Superior/purple set pieces, +special procs) may
            # exist only ONCE on a character — so the same unique set can't be slotted
            # in two powers. Track each unique piece this option would place.
            for pc in o["set"].get("pieces", [])[:o["n"]]:
                uq, mk = _uniq_key(pc)
                if uq and mk:
                    uniq_piece[mk].append(v)
            for s in o["sigs"]:
                sig_terms[s].append(v)
            for k, val in o["contrib"].items():
                if k in objective_targets:
                    cov_upper[k].append((val, v))
            if set_cost_rank(o["set"]) >= 2:
                premium_terms.append((o["n"], v))
            if pref_cats and o["set"].get("category") in pref_cats:
                cat_terms.append((o["n"], v))
            # Attack-damage reward: a damage set in a real attack, weighted by the attack's
            # base hit (premium attacks first) and the pieces it lands — capped at 5 since
            # past ~5 the extra DAMAGE is ED-flat (the 6th piece's SET BONUS is already
            # valued by the coverage obj, so it isn't double-counted here).
            if dmg_mode and p["_is_attack"] and _is_dmg_cat(o["set"].get("category")):
                base_w = (p.get("_base_dmg", 0.0) / max_base) if max_base > 0 else 1.0
                dmg_terms.append((base_w * min(o["n"], 5), v))
            # Non-damage role: penalise damage-set pieces (wasted enhancement) so the solver
            # leans to role/utility sets. The penalty is HEAVY on powers where a damage set is
            # pure waste — a Fighting-pool PREREQ (Boxing/Kick) and a multi-minute utility CLICK
            # (Dark Consumption 360s) barely scratch a controller and cost slots a 6-piece role
            # set would use better. Normal attacks (the AoE nuke) keep the light penalty.
            if non_damage_role and _is_dmg_cat(o["set"].get("category")):
                # EXEMPT a damage set that HARVESTS survival/recharge/recovery bonuses (Winter sets,
                # Entomb, ATOs) — that's the masters' softcap+perma engine, not a wasted mule.
                harvests = any(k in objective_targets and k[0] in _HARVEST_KINDS
                               for k in (o.get("contrib") or {}))
                if not harvests:
                    is_pool_atk = (p.get("full_name") or "").startswith("Pool.") and p.get("_is_attack")
                    is_long_util = p.get("power_type") == 0 and (p.get("base_recharge") or 0) > 90
                    pen_w = 0.15 if (is_pool_atk or is_long_util) else 0.03
                    dmg_pen_terms.append((pen_w * o["n"], v))
        if povars:
            # Frankenslotting: a power may stack pieces from up to MAX_SETS_PER_POWER
            # different sets, but only one piece-count per set, and the pieces it
            # holds can't exceed its free slots. Attacks must end up functionally
            # slotted (>= 1 set in the target pass).
            for vs in by_set.values():
                prob += pulp.lpSum(vs) <= 1
            prob += pulp.lpSum(povars) <= remaining_sets
            prob += pulp.lpSum(o["n"] * x[(pi, oi)]
                               for oi, o in enumerate(opts)) <= free
            if (p["_is_attack"] or p.get("_must_set")) and not perk_pass:
                prob += pulp.lpSum(povars) >= 1
            # A SQUISHY's armor toggle (epic shield) must be functionally ENHANCED, not a 1-slot
            # global mule — no master buys Scorpion Shield with a patron arc and leaves its defense
            # raw. Same principle as "attacks must get a set": require >= 2 pieces so the toggle's
            # own def/res is enhanced (the _armor_def/_armor_res credit sizes the set up on merit).
            if p.get("_armor_min2") and p.get("_base_rd") and not perk_pass and free >= 2:
                prob += pulp.lpSum(o["n"] * x[(pi, oi)]
                                   for oi, o in enumerate(opts)) >= 2

    # slot budget
    prob += pulp.lpSum(o["n"] * x[(pi, oi)]
                       for pi, opts in opts_by_power.items()
                       for oi, o in enumerate(opts)) <= budget
    # rule of five per bonus signature
    for s, vs in sig_terms.items():
        if len(vs) > RULE_OF_FIVE:
            prob += pulp.lpSum(vs) <= RULE_OF_FIVE
    # each UNIQUE piece at most once on the character (no two Superior/purple/attuned
    # sets of the same kind — their pieces are unique)
    for puid, vs in uniq_piece.items():
        if len(vs) > 1:
            prob += pulp.lpSum(vs) <= 1
    # capped coverage vars + balanced objective (fractional coverage per target)
    obj = []
    for k, tgt in objective_targets.items():
        if tgt <= 0:
            continue
        cur = totals.get(k, 0.0)
        room = max(0.0, tgt - cur)
        if room <= 0 and not perk_pass:
            continue
        cov = pulp.LpVariable(f"cov_{k}", lowBound=0, upBound=room)
        prob += cov <= pulp.lpSum(coef * v for coef, v in cov_upper.get(k, []))
        weight = (priority or {}).get(k, 1.0) * kind_mult.get(k[0], 1.0) / tgt
        obj.append(weight * cov)
    # Role set-category preference: lean toward the role's set categories. STRONGER for a
    # non-damage role (control/debuff/buff/heal) — there the role's sets are the WHOLE point
    # (they land controls, lengthen holds, debuff), so the lean should actually decide ties,
    # not just whisper. Still small vs the survival coverage obj, so it never derails a target.
    _cat_w = 0.012 if non_damage_role else 0.0008
    cat_bonus = _cat_w * pulp.lpSum(n * v for n, v in cat_terms) if cat_terms else 0
    # Damage-set penalty on a non-damage role (per-power weight folded into the term above): a
    # damage set's enhancement is wasted, so avoid it unless its survival bonus is genuinely best.
    dmg_penalty = pulp.lpSum(c * v for c, v in dmg_pen_terms) if dmg_pen_terms else 0
    # Per-slot cost (target pass only) → hit targets with the FEWEST slots, no
    # wasteful overshoot. Premium cost → use purple/ATO/Winter sets only when
    # their extra value beats the tier's cost weight (the budget↔premium dial).
    premium_pen = cost_w * pulp.lpSum(n * v for n, v in premium_terms) if premium_terms else 0
    # Attack-damage reward — pulls leftover slots onto the hardest hitters on a damage build.
    dmg_bonus = _DMG_REWARD_W * pulp.lpSum(c * v for c, v in dmg_terms) if dmg_terms else 0
    if not perk_pass:
        slot_terms = [o["n"] * x[(pi, oi)]
                      for pi, opts in opts_by_power.items()
                      for oi, o in enumerate(opts)]
        prob += (pulp.lpSum(obj) - 0.003 * pulp.lpSum(slot_terms) - premium_pen
                 + cat_bonus + dmg_bonus - dmg_penalty)
    else:
        prob += pulp.lpSum(obj) - premium_pen + cat_bonus + dmg_bonus - dmg_penalty
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if pulp.LpStatus[prob.status] != "Optimal":
        return
    for pi, opts in opts_by_power.items():
        p = free_powers[pi]
        for oi, o in enumerate(opts):
            if x[(pi, oi)].value() and x[(pi, oi)].value() > 0.5:
                _commit_set(p, o["set"], o["n"], o["sigs"], o["contrib"],
                            defaultdict(int), totals)


def _preserve_locked(powers, set_by_uid, piece_globals, totals, pvp):
    """PRESERVE mode. Keep each power's existing SET IOs (any slot with a set_uid —
    purples/Winters/ATOs/regular sets AND unique globals like LotG/Steadfast) by
    pre-placing them as LOCKED slots and crediting their set bonuses, so the ILP
    only fills the FREED slots. Generic/common IOs (set_uid is None) are dropped —
    those cheap slots are exactly what we re-solve. Returns
    (locked_count, kept_sets, already_present_global_substrs)."""
    locked_count = 0
    kept = []
    present_globals = set()
    uniq_globals = [g for g in piece_globals if g.get("unique", True)]
    for p in powers:
        by_set = {}
        # stash the power's CHEAP/generic IOs (set_uid None) so keep-layout mode can
        # restore any that the solve didn't upgrade — a cheap IO is only swapped out
        # when a goal-advancing set takes its place, never dropped for an empty slot.
        p["_cheap_ios"] = [s for s in (p.get("_existing_slots") or [])
                           if s and s.get("piece_uid") and not s.get("set_uid")]
        # Keep UNRESOLVED slots (e.g. Hamidon Os we can't model) exactly as-is —
        # they're real, often-expensive IOs the player invested in; never drop them.
        for s in (p.get("_existing_slots") or []):
            if (s and s.get("piece_name") and not s.get("set_uid")
                    and not s.get("piece_uid")
                    and len(p["_slots"]) < p.get("_slot_budget", 6)):
                p["_slots"].append({"set_uid": None, "set_name": None, "piece_uid": None,
                                    "piece_name": s.get("piece_name"), "category_id": None,
                                    "io_level": s.get("io_level"), "_locked": True})
                locked_count += 1
        for s in (p.get("_existing_slots") or []):
            if s and s.get("set_uid") and s.get("piece_uid"):
                by_set.setdefault(s["set_uid"], []).append(s)
        for suid, slots in by_set.items():
            n = min(len(slots), p.get("_slot_budget", 6) - len(p["_slots"]))
            if n <= 0:
                continue
            for s in slots[:n]:
                p["_slots"].append({
                    "set_uid": s.get("set_uid"), "set_name": s.get("set_name"),
                    "piece_name": s.get("piece_name"), "piece_uid": s.get("piece_uid"),
                    "category_id": s.get("category_id"), "io_level": s.get("io_level"),
                    "_locked": True})
                locked_count += 1
                sn = (s.get("set_name") or "").lower()
                for g in uniq_globals:
                    if g["set"] in sn:
                        present_globals.add(g["set"])
            srec = set_by_uid.get(suid)
            if srec:
                contrib, _ = _set_bonus_contrib(srec, n, {}, pvp)
                for k, v in contrib.items():
                    totals[k] += v
            kept.append({"power": p.get("display_name"),
                         "set": (srec or {}).get("name") or slots[0].get("set_name") or suid,
                         "pieces": n})
    return locked_count, kept, present_globals


def _place_globals(powers, piece_globals, sets_by_category, totals, seed_unique=None):
    used_unique = set(seed_unique or ())

    def try_place(p, g):
        if len(p["_slots"]) >= p.get("_slot_budget", 6):
            return False
        srec = _find_set(sets_by_category, p["_cats"], g["set"])
        if not srec:
            return False
        p["_slots"].append({"set_uid": srec["uid"], "set_name": srec["name"],
                            "piece_name": _global_piece(srec, g),
                            "piece_uid": _global_piece_uid(srec, g),
                            "category_id": srec["category_id"], "_global": True})
        for eff in g.get("effects", []):
            for ek, ev in _expand((eff.get("effect"),
                                   eff.get("damage_type", "None")),
                                  eff.get("value", 0.0)):
                totals[ek] += ev
        return True

    for g in piece_globals:
        nonunique = not g.get("unique", True)
        placed = 0
        for p in powers:
            if len(p["_slots"]) >= p.get("_slot_budget", 6):
                continue
            if not _find_set(sets_by_category, p["_cats"], g["set"]):
                continue
            if g["set"] in used_unique and not nonunique:
                break
            if try_place(p, g):
                placed += 1
                if not nonunique:
                    used_unique.add(g["set"])
                    break
                if placed >= 5:
                    break


def _finalize_powers(powers):
    out = []
    for p in powers:
        slots = [{k: v for k, v in s.items() if not k.startswith("_")}
                 for s in p["_slots"]]
        # Preserve the player's allocated slot COUNT: pad any slots the solve didn't
        # fill back as EMPTY (None) so an imported power never loses slots. The budget
        # cap above guarantees len(slots) <= _earned, so this only ever pads.
        earned = p.get("_earned")
        if earned:
            while len(slots) < int(earned):
                slots.append(None)
        out.append({
            "full_name": p["full_name"], "display_name": p.get("display_name"),
            "powerset_full_name": p.get("powerset_full_name"),
            "accepted_set_category_ids": p.get("accepted_set_category_ids", []),
            "accepted_set_categories": p.get("accepted_set_categories", []),
            "power_type": p.get("power_type"),
            "include_in_totals": p.get("power_type") in (1, 2),
            "slotCount": max(1, len(slots)), "slots": slots or [None]})
    return out


def _report(totals, targets, used, cap):
    lines = []
    for k, tv in sorted(targets.items(), key=lambda x: str(x[0])):
        cur = totals.get(k, 0.0)
        name = k[0] + (f" {k[1]}" if k[1] else "")
        status = "OK" if cur >= tv - 1e-6 else f"short {(tv-cur)*100:.0f}%"
        lines.append(f"{name}: {cur*100:.0f}% / target {tv*100:.0f}%  [{status}]")
    return {"slots_used": used, "slot_cap": cap, "lines": lines}
