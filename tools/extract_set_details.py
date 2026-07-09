"""
extract_set_details.py - Generate data/set_details.json: the AUTHENTIC in-game
IO text for the detail card + slotted-set progress features. GAME-FIRST for
copy as well as numbers: every string comes from the client's own bins.

Sources (via Bin Crawler + Pigg Wrangler, clone-run-discard per
tools/gamedata/README.md):
  - boostsets.bin          all 227 IO sets: rosters (crafted+attuned twins),
                           level ranges, rarity, tier -> Set_Bonus power refs
  - powers.bin             the Boosts.* piece records (title / short / help
                           TEMPLATE) and Set_Bonus.* bonus records (tier text)
  - clientmessages-en.bin  the P-hash -> text table (96k strings)

The help texts are the game's own TEMPLATES ("...by {Boost.Attrib.RechargeTime
.Scale}%...") — the app substitutes level-scaled values at display time with
the same MultIO math the engine prices with, so the card stays honest at every
level and boost state. This tool emits templates verbatim.

Coverage denominators (standing rule, all hard-fail):
  - every client set joins one of OUR sets by uid (227 == 227, both directions)
  - every roster piece resolves a crafted Boosts record with resolved
    (non-P-hash) title and help template
  - every tier's Set_Bonus power resolves title + short text
  - every template attrib is coverable by the joined piece's boost aspects
    through the pinned alias map (else the render helper would emit raw
    placeholders at runtime)

Run:  python tools/extract_set_details.py --crawler <CoH-Planner clone> \
          [--assets "C:/Games/HC2/assets/live"]
"""
import argparse
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data", "set_details.json")

# template attrib name -> acceptable piece boost aspects (in priority order).
# The game's placeholder vocabulary differs slightly from the boost aspect
# enum; DefenseDebuff/Defense and Endurance/EnduranceDiscount are the known
# pairs. Extend ONLY with evidence — the coverage gate below fails loudly on
# any attrib this map plus exact-match can't cover.
ATTRIB_ALIASES = {
    "DefenseDebuff": ("Defense",),
    "Endurance": ("EnduranceDiscount", "Endurance"),
    "Recovery": ("Endurance", "Recovery"),
    "ToHitDebuff": ("ToHit",),
    "Mez": ("Mez",),
    "Heal": ("Heal",),
    # Resist pieces: the game's template attrib for the resistance scale is
    # "Damage" (the Damage-attrib-at-aspect-Resistance convention, same as the
    # set-bonus records) — exact-match runs first, so damage-set pieces whose
    # aspects include a literal "Damage" are unaffected.
    "Damage": ("Resistance",),
    # Travel/slow pieces use one "Movement" placeholder for the whole speed
    # family (Pacing of the Turtle, Soaring — evidenced in their templates).
    # Both vocabularies appear: boost aspects say Speed*; effect attribs say
    # *Speed (Synapse's Shock's run-speed global).
    "Movement": ("SpeedRunning", "SpeedFlying", "SpeedJumping", "Slow",
                 "RunningSpeed", "FlyingSpeed", "JumpingSpeed"),
    # Knockback pieces (Sudden Acceleration): "Knock" — a Mez-family aspect.
    "Knock": ("Mez",),
    "InterruptTime": ("Interrupt",),
}

# BAKE-ONLY aliases (client effect-scale lookup, never boost aspects). Two
# evidenced crawler enum gaps: Experienced Marksman's interrupt effect parses
# as attrib Unknown(91) (sits exactly where InterruptTime belongs, scale
# matches its triple's pattern); Synapse's Shock F's +run-speed global parses
# as attrib Null (0.15 = the +15% global). Damage placeholders also resolve
# through the typed *_Dmg attribs (the set-bonus vocabulary).
BAKE_ALIASES = {
    "InterruptTime": ("unknown(91)",),
    "Movement": ("null",),
    "Damage": ("smashing_dmg", "lethal_dmg"),
    # Numina's unique writes "endurance recovery" with an Endurance placeholder
    # over a Recovery effect; Deflated Ego's proc likewise (−recovery, abs'd).
    "Endurance": ("recovery",),
    # Rectified Reticle's +Perception global parses as attrib Null (enum gap,
    # same class as the Null run-speed global). Steadfast's +3% Def global is
    # the same Null pattern. Regen uniques write Heal/Regen placeholders over
    # Regeneration effects (Regenerative Tissue E, Numina F).
    "Perception": ("null",),
    "Defense": ("null",),
    "Heal": ("regeneration",),
    "Regen": ("regeneration",),
    # LotG F: the +7.5% global recharge is the same Null-global pattern.
    "RechargeTime": ("null",),
}
# The client templates are not case-consistent (Nightmare F writes
# {Boost.Attrib.accuracy.Scale}); matching is case-insensitive as a fallback.

# Client set uid -> our set uid, where they legitimately differ. Cupid's Crush
# (the event set) exists in the Mids-derived data ONLY as its attuned form —
# our record IS the set, under the attuned uid.
UID_EXCEPTIONS = {"Cupids_Crush": "Attuned_Cupids_Crush"}
_PLACEHOLDER = re.compile(r"\{Boost\.Attrib\.([A-Za-z_]+)\.Scale\}")
_PHASH = re.compile(r"^P\d+$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crawler", required=True,
                    help="path to a CoH-Planner clone (tools/bin-crawler inside)")
    ap.add_argument("--assets", default=r"C:/Games/HC2/assets/live")
    ap.add_argument("--powers-bin", default=None,
                    help="optional pre-extracted powers.bin (skips the pigg read)")
    args = ap.parse_args()

    sys.path.insert(0, os.path.join(args.crawler, "tools", "bin-crawler"))
    from bin_crawler.parser._pigg import BinResolver          # noqa: E402
    from bin_crawler.parser._messages import load_messages    # noqa: E402
    from bin_crawler.parser._boostsets import parse_boostsets  # noqa: E402
    from bin_crawler.parser._powers import parse_powers        # noqa: E402

    res = BinResolver(args.assets)
    msgs = load_messages(res.read("clientmessages-en.bin"))
    csets = parse_boostsets(res.read("boostsets.bin"))
    precs = parse_powers(args.powers_bin or res.read("powers.bin"))
    by_full = {r.full_name: r for r in precs}

    ours = json.load(open(os.path.join(ROOT, "data", "enhancement_sets.json"),
                          encoding="utf-8"))
    our_by_uid = {s["uid"]: s for s in ours}

    def rtext(key):
        v = msgs.resolve(key)
        return None if (not v or _PHASH.match(v)) else v

    problems = []
    out = {"_meta": {
        "source": "client bins (boostsets/powers/clientmessages-en), "
                  "extracted with Bin Crawler",
        "attuned_note": rtext("EnhancementIgnoreEffectiveness"),
        "render": "substitute {Boost.Attrib.X.Scale} with the piece's "
                  "level-scaled boost value (MultIO math, engine-identical)",
        # single source for the render helper's placeholder->aspect matching
        "attrib_aliases": {k: list(v) for k, v in ATTRIB_ALIASES.items()},
    }}
    if not out["_meta"]["attuned_note"]:
        problems.append("attuned note key EnhancementIgnoreEffectiveness unresolved")

    joined = set()
    for cs in csets:
        uid = UID_EXCEPTIONS.get(cs.name, cs.name)
        rec = our_by_uid.get(uid)
        if rec is None:
            problems.append(f"client set {uid} not in our data")
            continue
        joined.add(uid)
        pieces = []
        for bi, bl in enumerate(cs.boostlists):
            crafted = next((b for b in bl.boosts if ".Crafted_" in b
                            or ".Superior_" in b), bl.boosts[0] if bl.boosts else None)
            attuned = next((b for b in bl.boosts if ".Attuned_" in b), None)
            if not crafted:
                problems.append(f"{uid}: empty boostlist")
                continue
            piece_uid = crafted.split(".")[1]
            pr = by_full.get(crafted)
            if not pr:
                problems.append(f"{uid}: no Boosts record for {crafted}")
                continue
            title = rtext(pr.display_name)
            help_t = rtext(pr.display_help)
            short = rtext(pr.short_help) or ""
            if not (title and help_t):
                problems.append(f"{uid}: unresolved title/help for {piece_uid}")
                continue
            our_piece = next((pc for pc in rec.get("pieces", [])
                              if pc.get("uid") == piece_uid), None)
            if our_piece is None and bi < len(rec.get("pieces", [])):
                # renamed set (client Artillery vs our Crafted_Shrapnel_*):
                # rosters are ordered A–F on both sides — join by position and
                # emit OUR uid, which is what the app's lookups key on.
                our_piece = rec["pieces"][bi]
            if our_piece is not None:
                piece_uid = our_piece.get("uid") or piece_uid
            p_aspects = {b["aspect"] for b in (our_piece or {}).get("boosts") or []}
            asp_lower = {a.lower() for a in p_aspects}
            # Fixed magnitudes from the client record's own effects — the source
            # for placeholders our static boosts can't level-scale: proc pieces
            # ("Chance for…", empty boosts) and the GLOBAL half of uniques
            # (LotG +7.5% recharge, Steadfast +3% def…). Keyed by both attrib
            # and aspect (Impervium's psi-res: attrib Psionic_Dmg, aspect
            # Resistance — the placeholder resolves through the aspect).
            fx_scales = {}
            for g in pr.effects:
                for t in g.templates:
                    for a in t.attribs:
                        fx_scales.setdefault(a.lower(), abs(t.scale))
                    if t.aspect:
                        fx_scales.setdefault(str(t.aspect).lower(), abs(t.scale))

            def _resolve(m):
                attrib = m.group(1)
                cands = (attrib,) + ATTRIB_ALIASES.get(attrib, ())
                # 1) level-scalable from the piece's own boosts → keep the
                #    placeholder; the app renders it with the MultIO math.
                if any(a in p_aspects for a in cands) or attrib.lower() in asp_lower:
                    return m.group(0)
                # 2) fixed magnitude from the client effects → bake now.
                bake_cands = ((attrib,) + ATTRIB_ALIASES.get(attrib, ())
                              + BAKE_ALIASES.get(attrib, ()))
                for cand in bake_cands:
                    v = fx_scales.get(cand.lower())
                    if v is not None:
                        return f"{round(v * 100.0, 1):g}"
                problems.append(f"{uid}/{piece_uid}: placeholder {attrib} "
                                f"covered by neither boosts nor effect scales")
                return m.group(0)

            help_t = _PLACEHOLDER.sub(_resolve, help_t)
            pieces.append({"piece_uid": piece_uid, "title": title,
                           "short": short, "help_template": help_t,
                           "static": not _PLACEHOLDER.search(help_t),
                           "crafted_fn": crafted, "attuned_fn": attuned})
        tiers = []
        for b in cs.bonuses:
            for ap_ in b.auto_powers:
                sbr = by_full.get(ap_)
                t_title = sbr and rtext(sbr.display_name)
                t_short = (sbr and rtext(sbr.short_help)) or ""
                if not t_title:
                    problems.append(f"{uid}: unresolved tier power {ap_}")
                    continue
                tiers.append({"pieces_required": b.min_boosts,
                              "bonus_power": ap_, "bonus_title": t_title,
                              "bonus_short": t_short})
        out[uid] = {"display": rtext(cs.display_name) or rec["name"],
                    "category_label": rtext(cs.description) or rec.get("category"),
                    "min_level": cs.min_level, "max_level": cs.max_level,
                    "rarity": cs.rarity, "pieces": pieces, "tiers": tiers}

    unjoined_ours = set(our_by_uid) - joined
    n_sets = len(out) - 1
    n_pieces = sum(len(v["pieces"]) for k, v in out.items() if k != "_meta")
    n_tiers = sum(len(v["tiers"]) for k, v in out.items() if k != "_meta")
    print(f"sets: {n_sets} of {len(csets)} client / {len(our_by_uid)} ours "
          f"(unjoined ours: {len(unjoined_ours)}) | pieces: {n_pieces} | "
          f"tiers: {n_tiers}")
    for p in problems[:30]:
        print("  PROBLEM:", p)
    if unjoined_ours:
        print("  UNJOINED OURS:", sorted(unjoined_ours)[:10])
    if problems or unjoined_ours or n_sets != len(csets):
        print("HARD FAIL: nothing written.")
        return 1
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("written:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
