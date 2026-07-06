"""Proc-bombing pass — the #1 damage lever every master build uses, encoded from the
validated build doctrine (docs/build-doctrine.md §3).

A power can hold ONE proc per DISTINCT accepted set-category (each is a different set's
unique global -> no rule-of-5 clash). Damage AURAS (constant pulse) and AoE attacks are the
best homes. -Resistance procs (Achilles' Heel / Fury of the Gladiator / Annihilation) are
spawn-wide force-multipliers and go FIRST.

Runs AFTER the ILP solve, only for offense builds (damage/tank role or fire-farm content).
Budget-safe: it REPLACES a vehicle's slotting in place (same slot count), so the 67-slot
budget is preserved. Premium-set homes (purple/ATO) are left alone — they're already optimal.
Fails safe: any error returns the build untouched.
"""
import json
import os
import sys

_CATALOG = None


def _data_dir():
    """The data folder — bundle root when packaged (PyInstaller), repo root from source."""
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), "data")
    return os.path.join(os.path.dirname(__file__), "..", "data")


def _catalog():
    global _CATALOG
    if _CATALOG is None:
        try:
            with open(os.path.join(_data_dir(), "proc_catalog.json"), encoding="utf-8") as f:
                _CATALOG = json.load(f)
        except Exception:  # noqa: BLE001
            _CATALOG = {"damage_procs": {}, "res_procs": {}}
    return _CATALOG


_AOE_DMG_CATS = {"PBAoE Damage", "Targeted AoE Damage", "Melee AoE", "Targeted AoE",
                 "Player Melee AoE"}
# A vehicle's slotting is only replaced if its current set is "filler" — keep premium homes
# (purples, Winter sets, ATOs) intact, since those give the recharge/damage bonuses masters
# build around. Damage AURAS are the exception (always proc-bombed — pulse damage > bonuses).
_PREMIUM_HINTS = ("Superior", "Armageddon", "Hecatomb", "Ragnarok", "Apocalypse",
                  "Gravitational Anchor", "Unbreakable Constraint", "Absolute Amazement",
                  "Coercive Persuasion", "Avalanche", "Blistering Cold", "Frozen Blast",
                  "Winter", "Overwhelming Presence", "Mako", "Gladiator's Javelin")
_OFFENSE_ROLES = {"damage", "tank"}
_CONTROL_ROLES = {"controller", "control", "dominator", "debuffer"}
# Premium sets that are DAMAGE sets: their enhancement is WASTED on a non-damage role, so on a
# controller's AoE attack we proc-bomb right over them (Containment procs > a dead damage set).
# Premium CONTROL/role homes (Gravitational Anchor, ATOs, etc.) are NOT here — those stay intact.
_PREMIUM_DMG_HINTS = ("Armageddon", "Hecatomb", "Ragnarok", "Apocalypse", "Avalanche",
                      "Blistering Cold", "Frozen Blast", "Mako", "Gladiator's Javelin")


def _is_proc_uid(uid):
    cat = _catalog()
    for table in (cat["damage_procs"], cat["res_procs"]):
        for procs in table.values():
            if any(p["uid"] == uid for p in procs):
                return True
    return False


def _proc_slot(setname, uid, cat_id):
    return {"set_uid": setname, "set_name": setname, "piece_name": "proc",
            "piece_uid": uid, "category_id": cat_id, "_proc": True}


def _pick_procs(cats, nslots, used, prefer_res=True):
    """Choose up to nslots procs for a power accepting `cats`: -Res procs first (force
    multipliers), then %Damage procs, one per set, skipping globals already on the build."""
    cat = _catalog()
    out, seen_sets = [], set()
    order = []
    if prefer_res:
        for c in cats:
            order += [("res", c, p) for p in cat["res_procs"].get(c, [])]
    # RANK damage procs by expected contribution (ppm × dmg-at-50), strongest first, so when a
    # power accepts more proc categories than it has slots the best procs win — not whichever
    # category the data happens to list first. Without this the pass could seat a weak single
    # proc (e.g. Cupid's Crush / Explosive Strike) over a stronger one and read as "random"
    # scatter to an expert. -Res procs stay ahead of all of them (spawn-wide force multipliers).
    dmg = []
    for c in cats:
        dmg += [("dmg", c, p) for p in cat["damage_procs"].get(c, []) if not p.get("premium")]
    dmg.sort(key=lambda t: -((t[2].get("ppm") or 0) * (t[2].get("dmg50") or 0)))
    order += dmg
    for _kind, c, p in order:
        if len(out) >= nslots:
            break
        if p["uid"] in used or p["set"] in seen_sets:
            continue
        out.append((p["set"], p["uid"], c))
        seen_sets.add(p["set"]); used.add(p["uid"])
    return out


def _vehicle_rank(rec):
    """Higher = better proc home. Damage auras (constant pulse) first; then any AoE-damage
    power — AoE attacks AND AoE controls (Flashfire/Fire Cages accept Targeted-AoE-Damage, so
    they're proc vehicles whose damage DOUBLES via Containment on a controller). Non-vehicles 0."""
    # An ultra-long-recharge CLICK (Dark Consumption 360s, Soul Drain 240s — endurance/steroid
    # dumps) fires once every few minutes; procs there almost never land, so it's not a proc home.
    if rec.get("power_type") == 0 and (rec.get("base_recharge") or 0) > 90:
        return 0
    # Deliberately keyed on ACCEPTED AoE-damage proc SETS, not raw geometry: a proc home must
    # ACCEPT the damage/-res procs we slot. A Confuse cone (Seeds) hits an area but takes no
    # damage proc, so geometry alone would mis-rank it. (Geometry/`engine.is_aoe` is used for
    # DPS + recommendations elsewhere; here proc-set acceptance is the correct signal.)
    cats = set(rec.get("accepted_set_categories") or [])
    has_aoe = bool(cats & _AOE_DMG_CATS)
    if rec.get("power_type") == 2 and has_aoe:
        return 3                          # damage aura — the premier proc home
    if has_aoe:
        return 2                          # AoE attack OR AoE control — both proc vehicles
    if cats & {"Defense Debuff", "Accurate Defense Debuff", "Holds", "Immobilize", "Stuns"}:
        return 1                          # single-target control / debuff (left as a set home)
    return 0


def apply_proc_pass(powers, power_by_full, role="damage", content="general"):
    role = role or "damage"
    if not (role in _OFFENSE_ROLES or role in _CONTROL_ROLES or content == "fire_farm"):
        return powers
    try:
        cat = _catalog()
        if not cat["damage_procs"]:
            return powers
        # globals already on the build are unique-once — never duplicate them
        used = set()
        for p in powers:
            for s in p.get("slots", []) or []:
                if s and s.get("piece_uid") and _is_proc_uid(s["piece_uid"]):
                    used.add(s["piece_uid"])
        # rank vehicles; proc-bomb auras always, AoEs/controls only if filler-slotted
        ranked = []
        for p in powers:
            rec = power_by_full.get(p.get("full_name"))
            if not rec:
                continue
            r = _vehicle_rank(rec)
            if r:
                ranked.append((r, p, rec))
        # Master pattern: proc-bomb ALL damage auras (constant pulse) + the SINGLE biggest
        # AoE "nuke" (most accepted proc categories). Other attacks keep their set homes.
        def _ncats(rec):
            c = set(rec.get("accepted_set_categories") or [])
            return sum(1 for cat in c if cat in _catalog()["damage_procs"]
                       or cat in _catalog()["res_procs"])
        auras = [(p, rec) for r, p, rec in ranked if r == 3]
        aoes = sorted([(p, rec) for r, p, rec in ranked if r == 2],
                      key=lambda pr: -_ncats(pr[1]))

        def _is_premium(p):
            cs = " ".join(s.get("set_name", "") for s in (p.get("slots") or []) if s)
            return any(h in cs for h in _PREMIUM_HINTS)

        def _is_premium_dmg(p):
            cs = " ".join(s.get("set_name", "") for s in (p.get("slots") or []) if s)
            return any(h in cs for h in _PREMIUM_DMG_HINTS)
        if role == "debuffer":
            # A DEBUFFER's own damage is ~1/9th of the league's output — damage procs enhance
            # the wrong person. His slots serve debuff UPTIME (set bonuses) and team
            # amplification; only the −res/debuff-anchor procs below are his to carry.
            targets = []
        elif role in _CONTROL_ROLES:
            # Controls ARE the damage (proc × Containment) → proc-bomb all filler AoE
            # controls/attacks; keep purple/ATO CONTROL homes (their recharge = perma-control),
            # but a premium DAMAGE set on an AoE attack is wasted enhancement → proc-bomb it too.
            targets = list(auras) + [(p, rec) for p, rec in aoes
                                     if _is_premium_dmg(p) or not _is_premium(p)]
        else:
            # Offense → auras + the single biggest AoE nuke; other attacks keep their set homes.
            targets = list(auras) + (aoes[:1] if aoes else [])
        for p, rec in targets:
            slots = p.get("slots") or []
            nslots = len(slots)
            if nslots < 2:
                continue                  # not enough room to proc-bomb meaningfully
            cats = rec.get("accepted_set_categories") or []
            procs = _pick_procs(cats, nslots, used)
            if len(procs) >= 2:           # only convert if we can land a real proc bomb
                cid = (slots[0] or {}).get("category_id")
                p["slots"] = [_proc_slot(sn, uid, cid) for sn, uid, _c in procs]
        # DEBUFF ANCHOR: a def-debuff power carries the Achilles' Heel "Chance for Res Debuff"
        # — ~−20% res at high uptime beats any top set-bonus tier for a debuff role. Home
        # ranking follows proc mechanics, not slot count: a debuff TOGGLE aura rolls PPM
        # against every enemy inside it each 10s pulse (spawn-wide, the Venomous Gas
        # standard) > a spammed click (the Envenom standard). Pet summons are excluded —
        # the swap would break their pet set, and the pet, not the player, owns the rolls.
        if role in _CONTROL_ROLES:
            _PET_CATS = {"Pet Damage", "Recharge Intensive Pets"}
            # EVERY −res proc is a team amplifier (Achilles/Annihilation/Fury of the
            # Gladiator): each goes into the best host accepting its category — debuff
            # toggle auras first (PPM rolls vs the whole aura every 10s), then the
            # biggest non-premium home; swap only the LAST piece (keeps set bonuses);
            # never raid pet sets or purple/ATO homes.
            for pcat, procs in (cat["res_procs"] or {}).items():
                proc = next((x for x in procs if x.get("uid")
                             and x["uid"] not in used), None)
                if not proc:
                    continue
                cand = []
                for p in powers:
                    rec = power_by_full.get(p.get("full_name"))
                    if not rec:
                        continue
                    cats = set(rec.get("accepted_set_categories") or [])
                    if pcat not in cats or cats & _PET_CATS or _is_premium(p):
                        continue
                    slots = p.get("slots") or []
                    if len(slots) >= 2 and not any(
                            s and s.get("piece_uid") == proc["uid"] for s in slots):
                        is_toggle = 1 if rec.get("power_type") == 2 else 0
                        cand.append(((is_toggle, len(slots)), p, slots))
                if cand:
                    cand.sort(key=lambda x: (-x[0][0], -x[0][1]))
                    _k, p, slots = cand[0]
                    cid = (slots[0] or {}).get("category_id")
                    slots[-1] = _proc_slot(proc["set"], proc["uid"], cid)
                    used.add(proc["uid"])
        return powers
    except Exception:  # noqa: BLE001 — fail safe, never break a solve
        return powers
