"""Back-fill the 103 empty-effect PvE set-bonus tiers from the game client snapshot.

Root cause (found 2026-07-08 for Accuracy, 2026-07-09 for Heal, completed here):
parse_mids keeps only STAT_EFFECT_TYPES / an Enhancement-relabel allowlist, so ten
whole bonus families parsed to EMPTY effects lists and were invisible to the
engine, the scorer and the solver since launch: knockback protection, slow
resist, the six mez-DURATION families (confuse/hold/stun/sleep/immobilize/fear),
improved movement, improved slow, improved knockback, increased range and
endurance discount. Maelwys round 4 made two of them load-bearing (his Fire
Shield slotting earns +KB protection the model literally could not see).

This script back-fills BOTH shipped data files (data/set_bonuses.json +
data/enhancement_sets.json) from the authoritative game-client extraction
(tools/gamedata/setbonuses.json, Bin Crawler) — GAME-FIRST, not Mids. The
parser itself stays untouched: we NEVER re-parse powers-era data (additive
patchers only, standing rule), and reality_check_setbonuses gains these values
so any future parse regression hard-fails.

UNIVERSAL ENCODING RULE (no per-family cases): every game effect is expanded
per attribute via ATTRIB_EFFECT (game attrib -> our effect name, Mids
EFFECT_TYPE vocabulary) with the game's own aspect (Current->Cur,
Strength->Str, Resistance->Res). The aspect disambiguates the families that
share attributes: (Knockback, Cur) = protection, (Knockback, Str) = improved
knockback; (RunningSpeed, Cur) = improved movement, (RunningSpeed, Str) =
improved slow, (RunningSpeed, Res) = slow resist. The original game "attribs"
list rides along on each effect for fidelity.

GUARDS (all hard-fail):
- label-family signature check: the matched game tier's (attribs, aspect) must
  agree with what OUR tier's display text promises — a piece-count collision
  with the wrong bonus can never silently patch wrong values;
- unmapped attrib -> abort (no silent drops);
- coverage denominator: exactly 103 of 103 empty PvE tiers patched per file, or
  the run fails;
- byte-identical output after stripping the added effects (additive-only proof).

Idempotent: already-filled tiers are left alone.

Run:  python tools/patch_empty_bonus_tiers.py
"""
import copy
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.join(os.path.dirname(__file__), "..")
SNAP = os.path.join(os.path.dirname(__file__), "gamedata", "setbonuses.json")
EXPECTED = 103   # independent denominator: the empty PvE tier count, pinned

# game attribute -> our effect name (Mids EFFECT_TYPE / eMez vocabulary)
ATTRIB_EFFECT = {
    "RunningSpeed": "SpeedRunning", "FlyingSpeed": "SpeedFlying",
    "JumpingSpeed": "SpeedJumping", "JumpHeight": "JumpHeight",
    "RechargeTime": "RechargeTime",
    "Confused": "Confused", "Held": "Held", "Stunned": "Stunned",
    "Immobilized": "Immobilized", "Sleep": "Sleep", "Terrorized": "Terrorized",
    "Knockback": "Knockback", "Knockup": "Knockup",
    "Range": "Range", "EnduranceDiscount": "EnduranceDiscount",
}
ASPECT = {"Current": "Cur", "Strength": "Str", "Resistance": "Res"}

_MOVE = {"RunningSpeed", "FlyingSpeed", "JumpingSpeed", "JumpHeight"}
_KB = {"Knockback", "Knockup"}
# label family -> (allowed attribs, required aspect). The label is what the
# in-game tooltip promises; the signature check makes the game tier prove it.
_FAMILY_SIG = [
    ("knockback protection", _KB, "Current"),
    ("improved knockback", _KB, "Strength"),
    ("slow resist", _MOVE | {"RechargeTime"}, "Resistance"),
    ("improved slow", _MOVE, "Strength"),
    ("improved movement", _MOVE, "Current"),
    ("confuse duration", {"Confused"}, "Strength"),
    ("hold duration", {"Held"}, "Strength"),
    ("stun duration", {"Stunned"}, "Strength"),
    ("sleep duration", {"Sleep"}, "Strength"),
    ("immobilize duration", {"Immobilized"}, "Strength"),
    ("fear duration", {"Terrorized"}, "Strength"),
    ("increased range", {"Range"}, "Strength"),
    ("endurance discount", {"EnduranceDiscount"}, "Strength"),
]


# The game's OWN internal key for this one set is misspelled (verified in the
# snapshot: 'debiliative_action', no first 't') — a data alias, not a rename.
_GAME_KEY_ALIAS = {"debilitative_action": "debiliative_action"}


def norm(s):
    """Set-name normalizer: lowercase, apostrophes dropped, every other
    non-alphanumeric run -> '_'. Applied to BOTH sides (the game snapshot's own
    keys keep literal hyphens — gaussians_synchronized_fire-control — which is
    why the accuracy patcher's one-sided norm missed it)."""
    s = (s or "").strip().lower().replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return _GAME_KEY_ALIAS.get(s, s)


def families_for_label(label):
    """ALL families the label promises (a tier can grant several — Will of the
    Controller 3pc names all six mez durations in one bonus). Returns the
    permitted (attrib, aspect) pairs plus the matched family keys."""
    low = (label or "").lower()
    perms, keys = set(), []
    for key, attribs, aspect in _FAMILY_SIG:
        if key in low:
            keys.append(key)
            perms.update((a, aspect) for a in attribs)
    return perms, keys


def effects_from_game(gtier, perms, where):
    """Expand one matched game tier into our per-attrib effect records. A game
    effect is consumed only when EVERY (attrib, aspect) it carries is permitted
    by the label's families; a permitted-aspect effect with a foreign attrib
    hard-fails (piece-count collision guard)."""
    out = []
    aspects_permitted = {a for _, a in perms}
    for ge in gtier.get("effects", []):
        if ge.get("aspect") not in aspects_permitted:
            continue
        for attrib in ge.get("attribs", []):
            if (attrib, ge["aspect"]) not in perms:
                raise SystemExit(f"FAIL {where}: game attrib {attrib!r}/"
                                 f"{ge['aspect']} outside the label families")
            eff = ATTRIB_EFFECT.get(attrib)
            if not eff:
                raise SystemExit(f"FAIL {where}: unmapped game attrib {attrib!r}")
            asp = ASPECT[ge["aspect"]]
            out.append({
                "effect": eff, "damage_type": "None", "aspect": asp,
                "modifies": eff if asp == "Str" else "None",
                "value": round(ge["scale"], 5), "to_who": 2,
                "attribs": list(ge.get("attribs", [])),
            })
    return out


def patch_records(records, game_by_key, report):
    """records: iterable of (set_display_name, bonus_tier_list). Returns patched count."""
    patched = 0
    for sname, bonuses in records:
        gset = game_by_key.get(norm(sname))
        for tier in bonuses:
            if tier.get("effects") or tier.get("pv_mode") not in (0, 1):
                continue
            label = "; ".join(tier.get("bonuses") or [])
            perms, keys = families_for_label(label)
            where = f"{sname} {tier.get('pieces_required')}pc ({label})"
            if not perms:
                raise SystemExit(f"FAIL {where}: empty tier with unrecognized label")
            if not gset:
                raise SystemExit(f"FAIL {where}: set missing from game snapshot")
            gts = [t for t in gset.get("tiers", [])
                   if t.get("pieces") == tier.get("pieces_required") and t.get("effects")]
            fx = []
            for gt in gts:
                fx = effects_from_game(gt, perms, where)
                if fx:
                    break
            if not fx:
                raise SystemExit(f"FAIL {where}: no game tier at this piece count "
                                 f"carries the promised {'/'.join(keys)} effect")
            tier["effects"] = fx
            patched += 1
            report.append(f"  {where}: {len(fx)} effect(s), "
                          f"value {fx[0]['value']} [{'/'.join(keys)}]")
    return patched


def strip_added(obj):
    """Deep-copy with the patched effects removed again (additive-only proof)."""
    o = copy.deepcopy(obj)
    stack = [o]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            fx = cur.get("effects")
            if isinstance(fx, list) and fx and all(isinstance(e, dict) and "attribs" in e for e in fx):
                cur["effects"] = []
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return o


def main():
    game = json.load(open(SNAP, encoding="utf-8"))
    game_by_key = {norm(k): v for k, v in game.items()}

    results = {}
    for fname in ("set_bonuses.json", "enhancement_sets.json"):
        path = os.path.join(ROOT, "data", fname)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        before = copy.deepcopy(data)
        if fname == "set_bonuses.json":
            records = [(rec.get("name") or k, rec.get("bonuses") or [])
                       for k, rec in data.items()]
        else:
            records = [(rec.get("name"), rec.get("bonuses") or []) for rec in data]
        report = []
        patched = patch_records(records, game_by_key, report)
        if patched not in (0, EXPECTED):
            raise SystemExit(f"FAIL {fname}: patched {patched} of {EXPECTED} expected "
                             f"— partial patch aborted, file NOT written")
        if patched == EXPECTED and json.dumps(strip_added(data), sort_keys=True) \
                != json.dumps(strip_added(before), sort_keys=True):
            raise SystemExit(f"FAIL {fname}: patch was not purely additive")
        if patched:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=1)
            print(f"{fname}: {patched} of {EXPECTED} expected empty PvE tiers patched")
            for line in report[:6]:
                print(line)
            print(f"  … ({len(report)} total)")
        else:
            print(f"{fname}: 0 empty PvE tiers found — already patched (idempotent)")
        results[fname] = patched
    if len(set(results.values())) != 1:
        raise SystemExit(f"FAIL: files disagree: {results}")
    print("OK — both files consistent")


if __name__ == "__main__":
    main()
