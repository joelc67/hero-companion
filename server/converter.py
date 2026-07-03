"""converter.py — Enhancement Converter PLANNER. For each set in a build, work out the CHEAPEST
concrete way to obtain the pieces via converters, per the Homecoming rules (Enhancement Converter
Salvage wiki), instead of buying the finished IO for 10-20M.

The rules that shape every plan:
  • By-Set   (3 converters): -> another piece of the SAME set (small pool = the set's other pieces).
  • By-Rarity(1 converter) : -> a piece of ANOTHER set of the SAME rarity (purple->purple, PvP->PvP,
                              ATO->ATO, uncommon->uncommon, rare->rare). Never crosses rarity.
  • By-Category(2 converters): -> another set in the SAME slotting category at the SAME level,
                              regardless of rarity — BUT can NEVER produce Very Rare (purple), PvP,
                              or Winter. So this is the "cheap uncommon -> expensive rare" lever, and
                              the reason you CANNOT converter your way UP into a purple.
Converters: 3 for 1 Reward Merit (any merit vendor, L10+), or random drops. Common IOs/SO/DO/TO
can't be converted.
"""

# The 11 Very Rare (purple) sets — one per attack/control category. Verified vs the data (level_min
# 49, non-Archetype, non-Winter). Purples can't be made from cheap IOs; you shuffle purples you own.
_PURPLE = {"armageddon", "apocalypse", "ragnarok", "hecatomb", "absolute amazement",
           "unbreakable constraint", "gravitational anchor", "coercive persuasion",
           "fortunata hypnosis", "soulbound allegiance", "cupid's crush"}
# Winter event sets (regular + Superior share these names).
_WINTER = {"avalanche", "blistering cold", "frozen blast", "winter's bite", "entomb"}
# PvP sets (not level-49 in the data, so listed by name).
_PVP = {"gladiator's", "panacea", "shield wall", "fury of the gladiator", "javelin volley",
        "exposed interface", "gladiator's net"}

_PURPLE_POOL = 11          # By-Rarity pool among purples
_PVP_POOL = 10
_WINTER_POOL = 5


def rarity_of(s):
    """Rarity CLASS of a set dict: purple | pvp | winter | superior_ato | ato | standard."""
    name = (s.get("name") or "").lower()
    cat = s.get("category") or ""
    if "Archetype" in cat:
        return "superior_ato" if name.startswith("superior ") else "ato"
    if any(w in name for w in _WINTER):
        return "winter"
    if any(p in name for p in _PVP):
        return "pvp"
    if name in _PURPLE or (s.get("level_min") == 49 and "Archetype" not in cat and name not in _WINTER):
        return "purple"
    return "standard"


def _merits(conv):
    return round(conv / 3)


def plan_for_set(s, pieces_used, cat_pool):
    """Concrete plan to obtain `pieces_used` (piece names) of set `s`. cat_pool = # sets sharing its
    category (the By-Category landing pool). Returns {set, rarity, category, level, pieces, steps[],
    est_converters, est_merits, headline}."""
    rar = rarity_of(s)
    name = s.get("name")
    cat = s.get("category") or "?"
    lvl = s.get("level_max") or 50
    npieces = s.get("piece_count") or len(s.get("pieces") or []) or 6
    inset_pool = max(1, npieces - 1)
    nwant = max(1, len(pieces_used))
    steps = []

    if rar == "standard":
        # The killer lever: land in the SET cheaply, then By-Set to the exact piece(s).
        steps.append(f"Buy the CHEAPEST piece of {name} on the auction (most set pieces are <1M) — "
                     f"or a cheap Uncommon in the '{cat}' category and By-Category (2 conv, ~{cat_pool} "
                     f"sets in category) until it lands in {name}.")
        # Most standard pieces are cheap to just BUY (<1M); converters only earn their keep on the
        # pricey piece(s) (a global unique / proc). So estimate ~one By-Set sweep, not every piece.
        est = inset_pool * 3
        steps.append(f"Buy the cheap pieces outright (<1M each); By-Set (3 conv/roll, pool {inset_pool}) "
                     f"only for the pricey piece(s) you need ({', '.join(pieces_used) or 'the set'}).")
        head = f"Cheap Uncommon → By-Category into {name} → By-Set to your piece(s)."
    elif rar in ("purple", "pvp", "winter"):
        pool = {"purple": _PURPLE_POOL, "pvp": _PVP_POOL, "winter": _WINTER_POOL}[rar]
        src = {"purple": "any Very Rare (purple) recipe — buy the CHEAPEST purple (some are only 2-4M)",
               "pvp": "any cheap PvP IO", "winter": "any Winter set IO (Winter Grab-Bag / P2W in-event, or auction)"}[rar]
        why = {"purple": "Purples CANNOT be made from cheap IOs — you can only shuffle purples you own.",
               "pvp": "PvP sets only convert among PvP.",
               "winter": "Winter sets can't be reached by Category conversion."}[rar]
        steps.append(f"{why} Get {src}.")
        steps.append(f"By-Rarity (1 conv/roll, pool ~{pool}) until it lands in {name} — ~{pool} rolls.")
        est = pool + inset_pool * 3 * min(nwant, 2)   # By-Rarity seed + a couple of By-Set fills
        steps.append(f"By-Set (3 conv/roll, pool {inset_pool}) to the {nwant} piece(s) you need. "
                     f"For a full {name} set, By-Rarity several cheap {rar}s into it first, then By-Set to fill.")
        label = {"purple": "Very Rare", "pvp": "PvP", "winter": "Winter"}[rar]
        head = f"Start from ONE {label} you own → By-Rarity into {name} → By-Set to your piece(s). No Category shortcut into {label}."
    else:  # ato / superior_ato
        est = inset_pool * 3
        catalyst = " (a Catalyst upgrades a normal ATO to Superior.)" if rar == "superior_ato" else ""
        steps.append(f"{name} is an Archetype set — buy the recipe directly with Reward Merits, or use a drop.{catalyst}")
        steps.append(f"By-Set (3 conv/roll, pool {inset_pool}) to the piece(s) you need. Do NOT By-Rarity/"
                     f"Category — those land on OTHER archetypes' ATOs, which you can't slot.")
        head = f"Buy the recipe with merits, then By-Set to your piece(s)."

    return {"set": name, "rarity": rar, "category": cat, "level": lvl,
            "pieces": pieces_used, "steps": steps,
            "est_converters": est, "est_merits": _merits(est), "headline": head}


# Order plans hardest/priciest first so the player tackles the big-ticket pieces first.
_RARITY_ORDER = {"purple": 0, "pvp": 1, "superior_ato": 2, "winter": 3, "ato": 4, "standard": 5}


def summary(s):
    """Compact set descriptor for the interactive pickers."""
    return {"uid": s.get("uid"), "name": s.get("name"), "rarity": rarity_of(s),
            "category": s.get("category"), "category_id": s.get("category_id"),
            "level_min": s.get("level_min"), "level_max": s.get("level_max"),
            "pieces": [p.get("name") for p in (s.get("pieces") or [])]}


def catalog(enh_sets):
    """Every set (any archetype/category) for the target/source pickers, grouped-friendly order."""
    out = [summary(s) for s in enh_sets]
    out.sort(key=lambda x: (x["category"] or "", _RARITY_ORDER.get(x["rarity"], 9), x["name"]))
    return out


def forward_options(s, enh_sets, sets_by_category):
    """What the set `s` can be CONVERTED INTO — the three in-game choices (the 'Y dropdown'):
      By-Set (3): another piece of s.  By-Rarity (1): any set of s's rarity.
      By-Category (2): any set in s's category at the same level — NEVER purple/PvP/Winter, and only
      if s itself is a standard (rare/uncommon) IO (purples/PvP/Winter/ATO can't By-Category)."""
    rar = rarity_of(s)
    by_set = [p.get("name") for p in (s.get("pieces") or [])]
    same_rar = [summary(x) for x in enh_sets
                if x.get("uid") != s.get("uid") and rarity_of(x) == rar]
    by_cat, cat_note = [], None
    if rar == "standard":
        lvl = s.get("level_max") or s.get("level_min") or 50
        for x in sets_by_category.get(s.get("category_id"), []):
            if x.get("uid") == s.get("uid") or rarity_of(x) in ("purple", "pvp", "winter"):
                continue
            if (x.get("level_min") or 0) <= lvl <= (x.get("level_max") or 50):
                by_cat.append(summary(x))
    else:
        cat_note = f"By-Category can't convert a {rar.replace('_', ' ')} — it never crosses into or out of purple/PvP/Winter/ATO."
    return {"source": summary(s), "rarity": rar,
            "by_set": {"cost": 3, "pieces": by_set},
            "by_rarity": {"cost": 1, "sets": same_rar},
            "by_category": {"cost": 2, "sets": by_cat, "note": cat_note}}


def plan_build(powers, set_by_uid, sets_by_category):
    """Group a build's slotted set pieces by set and return a conversion plan per set."""
    used = {}   # uid -> {"set": s, "pieces": set()}
    for p in powers or []:
        for slot in (p.get("slots") or []):
            if not slot or not slot.get("set_uid"):
                continue
            s = set_by_uid.get(slot["set_uid"])
            if not s:
                continue
            e = used.setdefault(slot["set_uid"], {"set": s, "pieces": []})
            pn = slot.get("piece_name")
            if pn and pn not in e["pieces"]:
                e["pieces"].append(pn)
    plans = []
    for uid, e in used.items():
        s = e["set"]
        cat_pool = len(sets_by_category.get(s.get("category_id"), []))
        plans.append(plan_for_set(s, e["pieces"], cat_pool))
    plans.sort(key=lambda p: (_RARITY_ORDER.get(p["rarity"], 9), -p["est_converters"]))
    return plans


def assign_haul(haul, powers, set_by_uid, sets_by_category):
    """FARM-EXIT MATCHMAKER: "I walked out of a farm with these drops — what should each
    become?" Each needed set in the build wants ONE seed converted into it (then buy/By-Set
    the rest, per the plan). Assign drops to needs greedily by conversion cost, respecting
    the real rules: By-Set within a set; By-Category only standard→standard in the same
    category/level window (never INTO purple/PvP/Winter); By-Rarity within purple/PvP/Winter
    pools; ATOs never By-Rarity (lands other archetypes' sets). Drops that can't reach any
    need viably → SELL (fund the seeds the plan says to buy)."""
    needs = plan_build(powers, set_by_uid, sets_by_category)
    need_sets = {}
    for n in needs:
        s = next((x for x in set_by_uid.values() if x.get("name") == n["set"]), None)
        if s:
            need_sets[s["uid"]] = {"set": s, "plan": n, "seeded": False}

    def route_cost(sd, sn):
        """(est_converters, route_text) for converting a piece of sd into set sn — None if not viable."""
        rd, rn = rarity_of(sd), rarity_of(sn)
        inset = max(1, (sn.get("piece_count") or len(sn.get("pieces") or []) or 6) - 1)
        if sd.get("uid") == sn.get("uid"):
            return (3 * max(1, inset // 2), "already the right set — By-Set (3 conv/roll) to the piece you need")
        if rd == "standard" and rn == "standard" \
                and sd.get("category_id") == sn.get("category_id"):
            lvl = sd.get("level_max") or 50
            if (sn.get("level_min") or 0) <= lvl <= (sn.get("level_max") or 50):
                pool = max(1, len([x for x in sets_by_category.get(sn.get("category_id"), [])
                                   if rarity_of(x) == "standard"]))
                return (2 * max(1, pool // 2) + 3 * max(1, inset // 2),
                        f"By-Category (2 conv/roll, ~{pool} sets) into {sn.get('name')}, then By-Set")
        if rd == rn and rd in ("purple", "pvp", "winter"):
            pool = {"purple": _PURPLE_POOL, "pvp": _PVP_POOL, "winter": _WINTER_POOL}[rd]
            return (1 * max(1, pool // 2) + 3 * max(1, inset // 2),
                    f"By-Rarity (1 conv/roll, ~{pool} {rd} sets) into {sn.get('name')}, then By-Set")
        return None

    # expand haul to individual drops
    drops = []
    for h in haul or []:
        s = set_by_uid.get(h.get("set_uid"))
        if s:
            drops += [s] * max(1, int(h.get("count") or 1))
    # all viable (cost, drop_idx, need_uid) pairs, cheapest first
    pairs = []
    for di, sd in enumerate(drops):
        for uid, e in need_sets.items():
            rc = route_cost(sd, e["set"])
            if rc:
                pairs.append((rc[0], di, uid, rc[1]))
    pairs.sort(key=lambda x: x[0])
    assigned_drop, assignments = set(), []
    for cost, di, uid, route in pairs:
        e = need_sets[uid]
        if di in assigned_drop or e["seeded"]:
            continue
        assigned_drop.add(di)
        e["seeded"] = True
        assignments.append({
            "drop_set": drops[di].get("name"), "drop_uid": drops[di].get("uid"),
            "target_set": e["set"].get("name"), "target_rarity": e["plan"]["rarity"],
            "target_pieces": e["plan"]["pieces"],
            # Converters only work on CRAFTED enhancements — a recipe drop must be built
            # first (salvage + crafting fee at an invention table / base worktable).
            "craft_first": True,
            "route": "craft the recipe first (salvage + crafting fee), then " + route,
            "est_converters": cost, "est_merits": _merits(cost)})
    sell, keep = [], []
    for di, sd in enumerate(drops):
        if di not in assigned_drop:
            rar = rarity_of(sd)
            if rar in ("purple", "pvp", "winter"):
                # Intrinsically valuable classes — never vendor fodder, even when this
                # build doesn't need them. (No price feed — class-level guidance only.)
                keep.append({"drop_set": sd.get("name"), "rarity": rar,
                             "reason": "high-value class — craft & sell high, or bank it "
                                       "as a future By-Rarity seed for another build"})
            else:
                sell.append({"drop_set": sd.get("name"),
                             "reason": "no needed set reachable at sane cost — sell it on "
                                       "the auction and fund the seeds below"})
    unseeded = [{"set": e["plan"]["set"], "rarity": e["plan"]["rarity"],
                 "headline": e["plan"]["headline"],
                 "est_converters": e["plan"]["est_converters"]}
                for e in need_sets.values() if not e["seeded"]]
    tot = sum(a["est_converters"] for a in assignments)
    return {"assignments": assignments, "sell": sell, "keep": keep, "unseeded": unseeded,
            "totals": {"drops": len(drops), "seeded": len(assignments),
                       "est_converters": tot, "est_merits": _merits(tot)}}


def summarize(plans):
    """Whole-build acquisition summary: grand totals + a concise shopping list, so the converter
    panel is a complete 'gear this recommended fit cheaply' checklist covering EVERY IO."""
    tot_c = sum(p.get("est_converters", 0) for p in plans)
    by_rar = {}
    for p in plans:
        by_rar[p["rarity"]] = by_rar.get(p["rarity"], 0) + 1
    # Shopping list: what cheap seeds to acquire (you re-roll these into the pieces you need).
    shop = []
    npurple = by_rar.get("purple", 0)
    if npurple:
        shop.append(f"~{npurple} cheap Very Rare (purple) recipe(s) to seed the purple sets")
    npvp = by_rar.get("pvp", 0)
    if npvp:
        shop.append(f"~{npvp} cheap PvP IO(s)")
    nstd = by_rar.get("standard", 0)
    if nstd:
        shop.append(f"~{nstd} cheap Uncommon/Rare piece(s) in the right categories (the By-Category seed)")
    nato = by_rar.get("ato", 0) + by_rar.get("superior_ato", 0)
    if nato:
        shop.append(f"{nato} Archetype set(s) bought straight from Reward Merits")
    return {"set_count": len(plans), "total_converters": tot_c, "total_merits": round(tot_c / 3),
            "by_rarity": by_rar, "shopping": shop}
