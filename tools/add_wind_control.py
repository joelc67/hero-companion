"""Add WIND CONTROL - a whole shipping powerset the tool could not plan.

Ten powers on Controller and Dominator, absent from our Mids-derived data.
Every field comes from the game client; every MAPPING between the client's
vocabulary and ours was derived by measuring the powers we already hold, never
by reading a wiki or guessing. `docs/wind-control-spec.md` is the write-up; the
rules and their evidence are repeated here so this file stands alone:

  level_available   client `available_level` + 1     5,478 of 5,589 agree
  power_type        Click->0, Toggle->2, Auto->1     3,719 / 628 / 1,024 agree
  effect_area       SingleTarget->1 Sphere->2        3,025 / 1,404 / 401 / 444
                    Cone->3 Location->4 Chain->1
  is_attack         exactly "has damage rows"        2,331 True/True, 3,332 F/F
  control rows      client scale->scale,             539 powers agree
                    magnitude->nmag, critter->pv 1
  control kind      hard/soft by mez NAME            unanimous, no mez has both
  categories        by name + 2 aliases              1,128x and 452x
  enhancements      by co-occurrence table below     >99% on every name used
  summons           entity_def, underscores removed  570 exact + 7 normalised

⚠ JOEL'S RULING (2026-08-08): the Controller and Dominator SHARE the Vortex
entity. The client carries two defs (`Pets_WindControl_Vortex_Controller` and
`Pets_WindControl_Vortex`) and our pet model carries one; sharing is the
documented v26 pattern for Controller/Dominator pet pairs, and he ruled it so.
Both archetypes point at `Pets_Wind_Control_Vortex`.

⚠ DAMAGE LIVES IN `child_effects` AS WELL AS `templates`. Boomerang Slice's
damage groups looked empty for exactly this reason. Both are read here.

⚠ REFUSES RATHER THAN GUESSES. Any client vocabulary this script cannot map to
ours with high confidence aborts the run and names the term. A powerset that is
80% right is worse than no powerset: the solver optimises into it and the player
trusts the numbers.

⚠ powers.json is COMPACT single-line. Read binary, write binary, no indent.
Usage:  python tools/add_wind_control.py [--check]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mode_tags import group_disposition   # noqa: E402  - ONE copy of the rule

# ⚠⚠ TARGETING IS NOT A CONDITION. A `requires_expression` mixes two unrelated
# jobs: WHO the effect may land on (always true for the enemy in front of you)
# and WHEN it applies (a mode, a state, a die roll). Only the second makes a
# group conditional. Censused over the whole client: 5,123 of the 7,323
# expression-carrying groups reduce to nothing but the clauses below, and every
# residue is a genuine condition (random rolls, kMeter, Source.Mode?, archetype
# variants, token ownership). Strip these, and anything LEFT means conditional.
_TARGETING = re.compile("|".join((
    r"enttype\s+target>\s+(?:critter|player)\s+eq",   # which side
    r"entref\s+target\.owner>\s+entref\s+source>\s+eq",   # not my own pet
    r"entref\s+target>\s+entref\s+source>\s+eq",          # is / is not me
    r"target\.isFriend\?", r"source\.isFriend\?", r"target\.isPlayer\?",
    r"&&", r"\|\|", r"!",
)))
_ENT_ONLY = re.compile(r"enttype\s+target>\s+(?:critter|player)\s+eq")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POWERS = os.path.join(ROOT, "data", "powers.json")
PSETS = os.path.join(ROOT, "data", "powersets.json")
CATS = os.path.join(ROOT, "data", "set_categories.json")
SUMM = os.path.join(ROOT, "data", "summons.json")
CRAWL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")

MARK = "added_from_client"
SETS = {"Controller_Control.Wind_Control": ("Class_Controller", "primary"),
        "Dominator_Control.Wind_Control": ("Class_Dominator", "primary")}
DISPLAY = "Wind Control"

AREA = {"SingleTarget": 1, "Sphere": 2, "Cone": 3, "Location": 4, "Chain": 1, "Map": 6}
PTYPE = {"Click": 0, "Toggle": 2, "Auto": 1}
# empirically derived from the powers we already hold (counts in the docstring)
CAT_ALIAS = {"Universal Damage Sets": "Universal Damage",
             "Ranged AoE Damage": "Targeted AoE Damage",
             # travel, proven against the powers we hold: Super Speed's client
             # "Running & Sprints" is our "Run (No Sprint)", Combat Jumping's
             # "Leaping & Sprints" is our "Jump (No Sprint)", and Fly's
             # "Universal Travel" is our "Travel".
             "Universal Travel": "Travel",
             "Running & Sprints": "Run (No Sprint)",
             "Leaping & Sprints": "Jump (No Sprint)"}
# ⚠ ONE CLIENT CATEGORY, TWO OF OURS: every record we hold that accepts client
# "Flight" also accepts our "Flight (No Sprint)" (Fly itself is the witness).
CAT_ALSO = {"Flight": "Flight (No Sprint)"}
BOOST_ALIAS = {
    "Accuracy": "Accuracy", "Buff_Defense": "Defense Buff",
    "Buff_ToHit": "To Hit Buff", "Confuse": "Confuse Duration",
    "Damage": "Damage Increase", "Debuff_Defense": "Defense Debuff",
    "Debuff_ToHit": "To Hit Debuff", "EnduranceDiscount": "Endurance Reduction",
    "Fear": "Fear Duration", "Heal": "Healing", "Hold": "Hold Duration",
    "Immobilize": "Immobilisation Duration", "Interrupt": "Activation Decrease",
    "Jump": "Jumping", "Knockback": "Knockback Distance", "Range": "Range",
    "Recharge": "Recharge Reduction", "Recovery": "Endurance Modification",
    "Res_Damage": "Resist Damage", "Sleep": "Sleep Duration", "Slow": "Slow",
    "SpeedFlying": "Flight Speed", "SpeedRunning": "Run Speed",
    "Stun": "Disorient Duration", "Taunt": "Taunt Duration",
}
MEZ_KIND = {"Held": "hard", "Stunned": "hard", "Immobilized": "hard",
            "Confused": "hard", "Terrorized": "hard", "Intangible": "hard",
            "Knockback": "soft", "Knockup": "soft", "Sleep": "soft",
            "Repel": "soft", "Afraid": "soft"}
DMG = {"Smashing": "Smashing", "Lethal": "Lethal", "Fire": "Fire", "Cold": "Cold",
       "Energy": "Energy", "Negative_Energy": "Negative", "Psionic": "Psionic",
       "Toxic": "Toxic"}
# ⚠ JOEL'S RULING: one Vortex entity, shared.
ENTITY_OVERRIDE = {"Pets_WindControl_Vortex_Controller": "Pets_Wind_Control_Vortex"}


def _sec(v):
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip().split()[0])
    except (ValueError, IndexError):
        return 0.0


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


# Families this project has already classified as carrying no data of ours -
# the same vocabulary as reality_check_effect_coverage's DISPOSITIONS. Skipped
# with a printed count, never silently, and never confused with "unmapped".
SKIP_FAMILIES = {
    "Create_Entity": "plumbing - the summon itself, handled by `summons`",
    "Grant_Power": "plumbing", "Revoke_Power": "plumbing", "Null": "no-op",
    "Set_Mode": "the mode/meter capability, queued",
    "Fly": "v30 movement exclusion", "FlyingSpeed": "v30 movement exclusion",
    "RunningSpeed": "v30 movement exclusion", "JumpingSpeed": "v30 movement",
    "JumpHeight": "v30 movement exclusion", "SpeedRunning": "v30 movement",
    "MovementControl": "v30 movement", "MovementFriction": "v30 movement",
    "Knockback": "v30 - KB strength/resistance is display-only",
    "Knockup": "v30 - KB strength is display-only", "Repel": "v30",
    "Range": "v30 range exclusion", "Translucency": "stealth, not modelled",
    "StealthRadius_PVE": "stealth", "StealthRadius_PVP": "stealth",
    "PerceptionRadius": "perception, not modelled",
    "ThreatLevel": "threat is not modelled",
    "Global_Chance_Mod": "v36 DORMANT - Opportunity semantics ungrounded",
    "Ninja_Run": "a movement MODE, the v30 movement exclusion",
}


def skip_reason(key):
    """Why a group or family was left out. ⚠ EVERY key gets a TRUE sentence:
    the first version defaulted to "sapping is not a scored axis" and printed
    it against tag: and conditional: keys it had nothing to do with. A stated
    exclusion whose stated reason is wrong is worse than an unstated one."""
    if key.startswith("tag:"):
        return (f"the game gates this group on {key[4:]} - a mode/meter, "
                "which the engine does not model (Fury class)")
    if key.startswith("conditional:"):
        return ("group(s) the game gates on state the engine cannot read "
                "(a stack count, a die roll, an archetype)")
    return SKIP_FAMILIES.get(key, "sapping is not a scored axis")


def _ticks(t):
    """How many times a periodic template applies. int(duration/period), the
    same reading our damage rows already agree with on 12 client DoTs (a 4.1s
    1s-period DoT is 4 ticks - the .1 is the client's epsilon)."""
    per = float(t.get("application_period") or 0.0)
    dur = _sec(t.get("duration"))
    return max(1, int(dur / per)) if per > 0 and dur > 0 else 1


def _at_full_health(t):
    """The magnitude multiplier of a health-scaling template AT FULL HEALTH.

    Life Support System's heal is `100 kHitPoints% source> - X / Y + @StdResult *`
    = ((100 - HP%) / X + Y) x StdResult, so at full health the multiplier is the
    constant Y and it rises as you lose health - which is exactly what the
    game's own help says ("This power's potency increases as your health
    decreases"). We take the FULL-HEALTH FLOOR: it is the value that is always
    true, and crediting the wounded bonus would need a scenario nobody has
    ruled on. Returns 1.0 when there is no expression, None when there is one
    this cannot read - the caller then refuses rather than guesses.
    """
    e = (t.get("magnitude_expression") or "").split()
    if not e:
        return 1.0
    # "100 kHitPoints% source> - X / Y + @StdResult *" - Y is token 6
    if (len(e) >= 8 and e[0] == "100" and e[1] == "kHitPoints%"
            and e[2] == "source>" and e[3] == "-" and e[5] == "/"
            and e[7] == "+"):
        try:
            return float(e[6])                   # the constant term Y
        except ValueError:
            return None
    return None


def effects_from(crec, refuse, skipped):
    _who = (crec.get("full_name") or "?").split(".")[-1]
    """(damage, control, debuff, self_fx, buff) - templates AND child_effects.

    ⚠ THE SIDE COMES FROM THE POWER'S `target_type`, NEVER THE TEMPLATE'S
    `target`. Clear Skies is a SELF auto whose templates all say "AnyAffected";
    reading the template would have thrown its entire buff away as un-mappable.
    Same trap the ally sweep hit earlier today, in a new place.
    """
    dmg, ctrl, deb, selff, buff, heal = [], [], [], [], [], []
    # ⚠⚠ `targets_affected` IS THE DISCRIMINATOR, not target_type. Thundergust
    # and Wind Shear are BOTH target_type "Self" - meaning centred on you - and
    # both land entirely on FOES; only `targets_affected` tells them apart from
    # Clear Skies, which is target_type Self AND targets_affected Self. Reading
    # target_type would have written a cone attack's damage as a self buff.
    _aff = set(crec.get("targets_affected") or [])
    friendly = bool(_aff & {"Self", "Friend"}) and not (_aff & {"Foe"})

    def take(t, pv, chance, gated):
        asp, tbl = t.get("aspect"), t.get("table")
        dur = _sec(t.get("duration"))
        me = friendly or t.get("target") == "Self"
        for a in (t.get("attribs") or []):
            fam = a.replace("_Dmg", "")
            if fam in SKIP_FAMILIES:
                skipped[fam] = skipped.get(fam, 0) + 1
            elif me and fam in DMG and asp == "Strength":
                # a SELF +damage buff - the v39 class. An AUTO is always on, so
                # it takes full magnitude and needs no duty cycle.
                selff.append({"effect": "DamageBuff", "damage_type": DMG[fam],
                              "scale": float(t.get("scale") or 0.0), "nmag": 1.0,
                              "modifier_table": tbl, "enhance_aspect": "None",
                              "ed_schedule": 0, "pv_mode": pv, "duration": dur})
            # ⚠ HEAL AND ABSORB COME FIRST. They have their own buckets, and the
            # generic self-buff branch below would swallow them into
            # self_effects where nothing reads them. Order matters in this chain.
            elif me and fam == "Absorb" and asp == "Maximum":
                _e = (t.get("magnitude_expression") or "").split()
                _row = {"effect": "Absorb", "damage_type": "None",
                        "scale": float(t.get("scale") or 0.0), "nmag": 1.0,
                        "modifier_table": tbl, "enhance_aspect": "Absorb",
                        "ed_schedule": 0, "pv_mode": pv, "duration": dur,
                        "host_recharge": float(crec.get("recharge_time") or 0.0)}
                if len(_e) >= 4 and _e[0] == "Max.kHitPoints" and _e[1] == "source>":
                    try:
                        _row["max_hp_frac"] = (float(t.get("scale") or 0.0)
                                               if _e[2] == "@StdResult"
                                               else float(_e[2]))
                    except ValueError:
                        refuse.add(f"{_who}: absorb RPN {' '.join(_e)!r}")
                selff.append(_row)
            elif me and fam == "Heal" and asp in ("Absolute", "Current"):
                # ⚠ A HEAL ROW CARRIES NO DURATION - `role_output.power_heal_output`
                # multiplies scale x table and divides by recharge, so a
                # heal-over-time must arrive as its TOTAL. Our damage rows keep
                # the per-tick scale plus a duration (verified against 12 client
                # DoTs, ratio 1.00); heals have no such field, so the ticks are
                # folded in here instead of inventing one nothing reads.
                sc, mult = float(t.get("scale") or 0.0), _at_full_health(t)
                if mult is None:
                    refuse.add(f"{_who}: heal magnitude_expression "
                               f"{t.get('magnitude_expression')!r}")
                    continue
                heal.append({"to_who": 2, "scale": sc * mult * _ticks(t),
                             "nmag": 1.0, "modifier_table": tbl,
                             "probability": float(chance), "pv_mode": pv})
            elif me and asp in ("Current", "Strength", "Absolute"):
                eff = {"ToHit": "ToHit", "RechargeTime": "RechargeTime",
                       "Recovery": "Recovery", "Regeneration": "Regeneration",
                       "EnduranceDiscount": "EnduranceDiscount",
                       "Endurance": "Endurance"}.get(fam)
                if eff:
                    selff.append({"effect": eff, "damage_type": "None",
                                  "scale": float(t.get("scale") or 0.0), "nmag": 1.0,
                                  "modifier_table": tbl, "enhance_aspect": "None",
                                  "ed_schedule": 0, "pv_mode": pv, "duration": dur})
                else:
                    refuse.add(f"{_who}: self {fam}/{asp}")
            elif not me and fam in ("Regeneration", "Recovery") and asp == "Current":
                # "Foe -Regen" on Nano Net / Wrist Blaster / Blaster Barrage
                deb.append({"effect": fam, "damage_type": "None",
                            "scale": float(t.get("scale") or 0.0), "nmag": 1.0,
                            "modifier_table": tbl, "probability": float(chance),
                            "duration": dur, "pv_mode": pv})
            elif not me and asp == "Strength":
                # a STRENGTH aspect on a FOE is a debuff of that family -
                # Breathless's -damage/-recharge/+endcost, Downdraft's -recharge.
                eff = {"RechargeTime": "RechargeTime",
                       "EnduranceDiscount": "EnduranceDiscount",
                       "Recovery": "Recovery", "Regeneration": "Regeneration",
                       "ToHit": "ToHit", "Defense": "Defense"}.get(fam)
                if eff is None and fam in DMG:
                    eff = "Damage"
                if eff:
                    deb.append({"effect": eff, "damage_type":
                                DMG.get(fam, "None") if eff == "Damage" else "None",
                                "scale": float(t.get("scale") or 0.0), "nmag": 1.0,
                                "modifier_table": tbl, "probability": float(chance),
                                "duration": dur, "pv_mode": pv})
                else:
                    refuse.add(f"{_who}: foe {fam}/Strength")
            elif not me and fam == "Endurance":
                # endurance DRAIN on a foe: sapping has never been scored
                skipped["Endurance (foe drain)"] = skipped.get("Endurance (foe drain)", 0) + 1
            elif fam in MEZ_KIND and asp in ("Magnitude", "Current", None):
                ctrl.append({"mez": fam, "kind": MEZ_KIND[fam],
                             "scale": float(t.get("scale") or 0.0),
                             "nmag": float(t.get("magnitude") or 1.0),
                             "modifier_table": tbl, "duration": dur,
                             "probability": float(chance), "pv_mode": pv})
            elif fam in DMG and asp in ("Absolute", "Current") and "damage" in (tbl or "").lower():
                dmg.append({"effect": "Damage", "damage_type": DMG[fam],
                            "scale": float(t.get("scale") or 0.0), "nmag": 1.0,
                            "modifier_table": tbl, "probability": float(chance),
                            "duration": dur, "pv_mode": pv,
                            "enhance_aspect": "Damage", "ed_schedule": 0})
            elif fam == "Base_Defense" and asp == "Current" and not gated:
                deb.append({"effect": "Defense", "damage_type": "None",
                            "scale": float(t.get("scale") or 0.0), "nmag": 1.0,
                            "modifier_table": tbl, "probability": float(chance),
                            "duration": dur, "pv_mode": pv})
            elif fam == "ToHit" and asp == "Current" and t.get("target") != "Self" and not gated:
                deb.append({"effect": "ToHit", "damage_type": "None",
                            "scale": float(t.get("scale") or 0.0), "nmag": 1.0,
                            "modifier_table": tbl, "probability": float(chance),
                            "duration": dur, "pv_mode": pv})
            else:
                refuse.add(f"{_who}: {fam}/{asp}/{t.get('target')} tt={crec.get('target_type')}")

    for grp in (crec.get("effects") or []):
        req = (grp.get("requires_expression") or "").strip()
        pv = 1 if "critter" in req else 2 if "player" in req else 0
        # ⚠⚠ A GROUP CAN BE PvE-TAGGED **AND** CONDITIONAL. Wrist Blaster's
        # damage is written once per archetype and again per game state
        # ("arch source> Class_Scrapper eq enttype target> critter eq" is a
        # Scrapper crit at 5%), so testing for "critter" alone let 22 extra
        # damage rows through as if they were all unconditional - a 20x attack.
        # A group counts as plain only when NOTHING remains after the entity
        # test is struck out. Wind Control never showed this: an archetype
        # powerset needs no per-archetype variants.
        gated = bool(_TARGETING.sub(" ", req).strip())
        # ⚠⚠ A TAG IS NOT AUTOMATICALLY A GATE. `tags` is where the client
        # gates its modes - FieryEmbrace, Domination, Containment, the Scrapper
        # crits, PowerBoostA/B - and the first version of this skipped EVERY
        # tagged group. That is wrong for `FireBlastBonusDoT`, which is just the
        # client's name for Blaze's own Fire DoT: unconditional, in the power's
        # help, and dropping it understates 29 Fire attacks. Three mechanical
        # tests were tried and each misclassified some of the 48 in both
        # directions, so the adjudication is a table with its evidence
        # (tools/mode_tags.py) and a check that hard-fails on anything new.
        _disp = group_disposition(grp.get("tags"))
        if _disp == "unknown":
            refuse.add(f"{_who}: unadjudicated tag(s) {grp.get('tags')} - add "
                       f"them to tools/mode_tags.py")
            continue
        if _disp == "skip":
            for _t in grp["tags"]:
                skipped[f"tag:{_t}"] = skipped.get(f"tag:{_t}", 0) + 1
            continue
        # ⚠ chance 0.0 MEANS UNSET, not "never". The crawler writes 0.0 for an
        # absent field: Poisoned Dagger's -DMG group reads 0.0 while the game's
        # own short help says "-DMG". Corpus-wide only 64 untagged chance-0
        # groups exist and every one carries a real, help-stated effect.
        chance = grp.get("chance") or 1.0
        if gated:
            # A CONDITIONAL GROUP IS A DIFFERENT CLAIM, and it is REPORTED.
            # Vacuum's whole Lethal DoT sits behind "hold 6 stacks of Wind
            # Control Pressure"; crediting it unconditionally would make a
            # meter-gated attack look permanent, and dropping it silently would
            # leave an attack reading zero damage with nothing to explain it.
            skipped[f"conditional:{_who}"] = skipped.get(f"conditional:{_who}", 0) + 1
            continue
        for t in (grp.get("templates") or []):
            if t.get("scale") or t.get("magnitude"):
                take(t, pv, chance, gated)
        for ch in (grp.get("child_effects") or []):     # ⚠ where damage hides
            if (ch.get("requires_expression") or "").strip():
                continue
            cch = ch.get("chance") or 1.0        # 0.0 means unset, see above
            for t in (ch.get("templates") or []):
                if t.get("scale") or t.get("magnitude"):
                    take(t, pv, cch, False)
    return dmg, ctrl, deb, selff, buff, heal


def main():
    check_only = "--check" in sys.argv
    raw = open(POWERS, "rb").read()
    data = json.loads(raw.decode("utf-8"))
    orig = json.loads(raw.decode("utf-8"))
    sraw = open(SUMM, "rb").read()
    summ = json.loads(sraw.decode("utf-8"))
    sorig = json.loads(sraw.decode("utf-8"))
    praw = open(PSETS, "rb").read()
    psets = json.loads(praw.decode("utf-8"))
    porig = json.loads(praw.decode("utf-8"))
    client = client_index()
    sc = json.load(open(CATS, encoding="utf-8"))
    cat_id = {(c["name"]).lower(): c for c in sc["categories"]}
    enh_id = {(c["name"]).lower(): c for c in sc["enhancement_classes"]}
    ent_meta = json.load(open(SUMM, encoding="utf-8"))["entities"]
    entities = set(ent_meta)
    norm = lambda s: s.replace("_", "").lower()          # noqa: E731
    ent_by_norm = {}
    for e in entities:
        ent_by_norm.setdefault(norm(e), e)

    # IDEMPOTENT
    dropped = 0
    for ps in list(data):
        if ps in SETS:
            dropped += len(data[ps])
            del data[ps]
    for at, entry in list(psets.get("by_archetype", {}).items()):
        for kind in ("primary", "secondary"):
            keep = [s for s in (entry.get(kind) or []) if s["full_name"] not in SETS]
            if len(keep) != len(entry.get(kind) or []):
                entry[kind] = keep
    for k in [x for x in summ["powers"] if x.rsplit(".", 1)[0] in SETS]:
        del summ["powers"][k]
    # ⚠ THE BASELINE MUST BE STRIPPED TOO. `orig`/`porig`/`sorig` are read from
    # disk, which on a re-run already contains the set - so the invariance check
    # compared "without" against "with" and refused a perfectly good re-run.
    for _b in (orig,):
        for ps in [x for x in _b if x in SETS]:
            del _b[ps]
    for _b in (porig,):
        for _at, _e in (_b.get("by_archetype") or {}).items():
            for _k in ("primary", "secondary"):
                if _e.get(_k):
                    _e[_k] = [s for s in _e[_k] if s["full_name"] not in SETS]
    for k in [x for x in sorig["powers"] if x.rsplit(".", 1)[0] in SETS]:
        del sorig["powers"][k]
    if dropped:
        print(f"(re-run: dropped {dropped} record(s) from a previous pass)")

    refuse, skipped = set(), {}
    made = []
    for ps_name, (at, slot) in SETS.items():
        leaves = sorted(f for f in client if f.startswith(ps_name + "."))
        if not leaves:
            print(f"FAIL: the client has no {ps_name}")
            sys.exit(1)
        recs = []
        for fn in leaves:
            c = client[fn]
            # categories
            cats = []
            for name in (c.get("allowed_set_categories") or []):
                for ours_name in ([CAT_ALIAS.get(name, name)]
                                  + ([CAT_ALSO[name]] if name in CAT_ALSO else [])):
                    hit = cat_id.get(ours_name.lower())
                    if not hit:
                        refuse.add(f"set category {name!r}")
                    elif hit not in cats:
                        cats.append(hit)
            boosts = []
            for name in (c.get("boosts_allowed") or []):
                ours_name = BOOST_ALIAS.get(name)
                hit = enh_id.get((ours_name or "").lower())
                if not hit:
                    refuse.add(f"boost {name!r}")
                    continue
                boosts.append(hit)
            dmg, ctrl, deb, selff, buff, heal = effects_from(c, refuse, skipped)
            summons, spec_pets, spec_dur = [], [], 0.0
            for g in (c.get("effects") or []):
                for t in (g.get("templates") or []):
                    ed = (t.get("params") or {}).get("entity_def")
                    if not ed:
                        continue
                    ed = ENTITY_OVERRIDE.get(ed, ed)
                    got = ed if ed in entities else ent_by_norm.get(norm(ed))
                    if not got:
                        refuse.add(f"summon entity {ed!r}")
                        continue
                    spec_dur = max(spec_dur, _sec(t.get("duration")))
                    hit = next((x for x in spec_pets if x["uid"] == got), None)
                    if hit:
                        hit["count"] += 1
                    else:
                        spec_pets.append({"uid": got, "count": 1,
                                          "class": ent_meta[got]["class_name"]})
                    if got not in summons:
                        summons.append(got)
            if spec_pets:
                # ⚠ every field measured: permanent <=> duration >= 99999 (483/53
                # split, perfectly correlated); copy_boosts is True on all 475
                # existing specs; level_shift 0 because none of the Wind pets
                # carries a Levelminus table (the v38 signal).
                summ["powers"][fn] = {
                    "pets": spec_pets, "duration": spec_dur,
                    "permanent": spec_dur >= 99999, "copy_boosts": True,
                    "level_shift": 0}
            recs.append({
                "full_name": fn,
                "display_name": c.get("display_name") or fn.split(".")[-1],
                "power_name": fn.split(".")[-1],
                "powerset_full_name": ps_name,
                "group_name": ps_name.split(".")[0],
                "level_available": int(c.get("available_level") or 0) + 1,
                "power_type": PTYPE.get(c.get("type"), 0),
                "slottable": True,
                "default_slot_count": 1,
                "max_slot_count": 6,
                "accepted_enhancement_type_ids": [b["id"] for b in boosts],
                "accepted_enhancement_types": [b["name"] for b in boosts],
                "accepted_set_category_ids": [x["id"] for x in cats],
                "accepted_set_categories": [x["name"] for x in cats],
                "accepted_set_category_shorts": [x["short"] for x in cats],
                "is_attack": bool(dmg),
                "is_resurrect": False,
                "base_recharge": float(c.get("recharge_time") or 0.0),
                "end_cost": float(c.get("endurance_cost") or 0.0),
                "cast_time": float(c.get("activation_time") or 0.0),
                "activate_period": float(c.get("activate_period") or 0.0),
                "effect_area": AREA.get(c.get("effect_area"), 1),
                "max_targets": int(c.get("max_targets_hit") or 1),
                "radius": float(c.get("radius") or 0.0),
                "range": float(c.get("range") or 0.0),
                "arc": float(c.get("arc") or 0.0),
                "damage_effects": dmg,
                "control_effects": ctrl,
                "debuff_effects": deb,
                "self_effects": selff,
                "buff_effects": buff,
                "heal_effects": heal,
                "summons": summons,
                "pet_powersets": [],
                MARK: True,
            })
        recs.sort(key=lambda p: (p["level_available"], p["full_name"]))
        data[ps_name] = recs
        made.append((ps_name, recs))
        # offer it in the app
        entry = psets.setdefault("by_archetype", {}).setdefault(at, {})
        lst = entry.setdefault(slot, [])
        idx = lst[0].get("archetype_index") if lst else 0
        lst.append({"full_name": ps_name, "display_name": DISPLAY,
                    "set_type": slot.capitalize(), "archetype_index": idx})
        lst.sort(key=lambda s: s["display_name"])

    if refuse:
        print("FAIL - refusing to write a partly-understood powerset. Unmapped:")
        for r in sorted(refuse):
            print(f"    {r}")
        sys.exit(1)

    for fam, n in sorted(skipped.items(), key=lambda x: -x[1]):
        print(f"STATED EXCLUSION x{n:<4} {fam}: {skip_reason(fam)}")
    for ps_name, recs in made:
        print(f"{ps_name}: {len(recs)} powers")
        for r in recs:
            print(f"    L{r['level_available']:<3}{r['display_name']:<16}"
                  f"{'atk' if r['is_attack'] else '   '} "
                  f"dmg={len(r['damage_effects'])} ctrl={len(r['control_effects'])} "
                  f"deb={len(r['debuff_effects'])} self={len(r['self_effects'])} "
                  f"pets={r['summons'] or ''}")
    for k in sorted(summ["powers"]):
        if k.rsplit(".", 1)[0] in SETS:
            print(f"    summon spec {k.split('.')[-1]:<10} {json.dumps(summ['powers'][k])}")
    if check_only:
        return

    # ⚠ THREE files change together, and each must invert exactly.
    out = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    probe = json.loads(out.decode("utf-8"))
    for ps in list(probe):
        if ps in SETS:
            del probe[ps]
    if (json.dumps(probe, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            != json.dumps(orig, separators=(",", ":"), ensure_ascii=False).encode("utf-8")):
        print("INVARIANCE FAILED on powers.json - refusing to write")
        sys.exit(2)
    # ⚠⚠ MATCH THE FILE'S OWN SERIALISATION. powers.json and summons.json are
    # COMPACT single-line; powersets.json is indent=1 with CRLF. Writing it
    # compact collapsed a 3,088-line file into one and turned a two-entry
    # addition into a 3,102-line diff - content identical, review impossible.
    _CRLF, _LF = b"\r\n", b"\n"
    pout = json.dumps(psets, indent=1, ensure_ascii=False).encode("utf-8")
    pout = pout.replace(_CRLF, _LF).replace(_LF, _CRLF)
    pprobe = json.loads(pout.decode("utf-8"))
    for _at, entry in pprobe.get("by_archetype", {}).items():
        for kind in ("primary", "secondary"):
            if entry.get(kind):
                entry[kind] = [s for s in entry[kind] if s["full_name"] not in SETS]
    if (json.dumps(pprobe, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            != json.dumps(porig, separators=(",", ":"), ensure_ascii=False).encode("utf-8")):
        print("INVARIANCE FAILED on powersets.json (ordering?) - refusing to write")
        sys.exit(2)
    sout = json.dumps(summ, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sprobe = json.loads(sout.decode("utf-8"))
    for k in [x for x in sprobe["powers"] if x.rsplit(".", 1)[0] in SETS]:
        del sprobe["powers"][k]
    if (json.dumps(sprobe, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            != json.dumps(sorig, separators=(",", ":"), ensure_ascii=False).encode("utf-8")):
        print("INVARIANCE FAILED on summons.json - refusing to write")
        sys.exit(2)
    print("invariance: removing the set reproduces all three baselines exactly")
    # ⚠⚠ `open(path, "wb").write(expr)` TRUNCATES BEFORE IT EVALUATES `expr`.
    # A NameError in that expression emptied powers.json to 0 bytes while
    # building this script - 17 MB of data gone in one statement, recovered only
    # because it is in git and the rest is tool-generated. Every byte is built
    # and checked ABOVE; these three writes touch nothing that can raise.
    for _path, _bytes in ((POWERS, out), (PSETS, pout), (SUMM, sout)):
        with open(_path, "wb") as _fh:
            _fh.write(_bytes)
    print(f"wrote powers.json ({len(out):,}), powersets.json ({len(pout):,}) "
          f"and summons.json ({len(sout):,})")


if __name__ == "__main__":
    main()
