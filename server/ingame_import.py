"""
ingame_import.py - Parse a Homecoming in-game build export (the text file written
by the /build_save_file slash command) into our build structure, the same shape
mids_import.parse_build produces, PLUS the level information the game encodes:

  * each power's PICK LEVEL  ("Level 16:" -> pick_level=16)
  * each slot's IO LEVEL     ("... (35)" -> io_level=35; attuned/Superior show (1))

The file looks like:

    Buff Juice: Level 50 Mutation Class_Defender

    Character Profile:
    ------------------
    Level 16: Defender_Ranged Dark_Blast Tenebrous_Tentacles
        Superior_Attuned_Frozen_Blast_D (1)
        EMPTY
    ...
    ------------------
    Badges Earned:
    ...

Enhancements are crafted UIDs (Crafted_Hecatomb_C, Superior_Attuned_Winters_Bite_A,
common IOs like Crafted_Recharge) that match our piece uids directly. Unresolved
ids (Hamidon Os) keep the slot with no set/piece and are reported, like the .mbd
importer. Power lines resolve by "Group.Set.Power"; epics whose in-game set token
differs from our internal name (Defender_Fire_Mastery vs Def_Flame_Mastery) fall
back to resolving by power name within the archetype's available epic sets.
"""

import re

# Inherent travel toggles / pseudo-powers that appear in the export but aren't
# real, slottable picks — skip them silently (not "unresolved").
_SKIP_POWERS = {"Pool.Speed.SpeedPhase"}

_HEADER_RE = re.compile(r"^(.*?):\s*Level\s+(\d+)\s+(\w+)\s+(Class_\w+)\s*$")
_POWER_RE = re.compile(r"^Level\s+(\d+):\s+(.+?)\s*$")
_SLOT_RE = re.compile(r"^(.+?)\s+\((\d+)\)\s*$")


def looks_like_ingame(text):
    """Heuristic: a /build_save_file export has a 'Character Profile:' header."""
    return isinstance(text, str) and "Character Profile:" in text


def _parse_blocks(text):
    """Return (name, char_level, archetype, [block,...]). Each block is
    {group, pset, power, pick_level, slots:[(uid, io_level) | None, ...]}."""
    lines = text.splitlines()
    name, char_level, archetype = "Imported build", None, None
    if lines:
        m = _HEADER_RE.match(lines[0].strip())
        if m:
            name = (m.group(1).strip() or name)
            char_level = int(m.group(2))
            archetype = m.group(4)

    blocks, cur, started = [], None, False
    for ln in lines:
        stripped = ln.strip()
        if stripped == "Character Profile:":
            started = True
            continue
        if not started:
            continue
        if stripped.startswith("---"):
            if blocks or cur:        # the closing divider before "Badges Earned:"
                break
            continue                 # the opening divider
        pm = _POWER_RE.match(ln)
        if pm and not (ln.startswith("\t") or ln.startswith("    ")):
            toks = pm.group(2).split(" ")
            if len(toks) < 3:
                continue
            cur = {"group": toks[0], "pset": toks[1], "power": " ".join(toks[2:]),
                   "pick_level": int(pm.group(1)), "slots": []}
            blocks.append(cur)
        elif cur is not None and (ln.startswith("\t") or ln.startswith("    ")):
            if stripped == "EMPTY":
                cur["slots"].append(None)
            else:
                sm = _SLOT_RE.match(stripped)
                if sm:
                    cur["slots"].append((sm.group(1), int(sm.group(2))))
                else:
                    cur["slots"].append((stripped, None))
    return name, char_level, archetype, blocks


def _epic_sets(archetype, lk):
    at_ps = lk["powersets_by_at"].get(archetype, {})
    return [s["full_name"] for s in at_ps.get("epic", [])]


def _lock_epic_set(blocks, archetype, lk):
    """A character has exactly one epic/ancillary set, but the in-game set token
    can differ from our internal name. Pick the AT epic set that contains the most
    of the build's epic-group power names. Returns that set's full_name or None."""
    wanted = [b["power"].replace("_", " ").lower()
              for b in blocks if b["group"] == "Epic"]
    if not wanted:
        return None
    best, best_hits = None, 0
    for sfull in _epic_sets(archetype, lk):
        names = {p["display_name"].lower() for p in lk["powers_by_set"].get(sfull, [])}
        hits = sum(1 for w in wanted if w in names)
        if hits > best_hits:
            best, best_hits = sfull, hits
    return best


def _resolve_power(block, archetype, locked_epic, lk):
    """Resolve one block to a power record. Exact Group.Set.Power first, then a
    name-based fallback within the archetype's candidate sets (handles epics and
    any in-game set token that differs from our internal powerset name)."""
    full = f"{block['group']}.{block['pset']}.{block['power']}"
    if full in _SKIP_POWERS:
        return "skip"
    rec = lk["power_by_full"].get(full)
    if rec:
        return rec
    disp = block["power"].replace("_", " ").lower()
    at_ps = lk["powersets_by_at"].get(archetype, {})
    if block["group"] == "Epic":
        cand = [locked_epic] if locked_epic else _epic_sets(archetype, lk)
    elif block["group"] == "Pool":
        cand = [s["full_name"] for s in lk["pools"]]
    elif block["group"] == "Inherent":
        cand = []                    # inherents only resolve by exact full_name
    else:
        cand = ([s["full_name"] for s in at_ps.get("primary", [])]
                + [s["full_name"] for s in at_ps.get("secondary", [])])
    for sfull in cand:
        if not sfull:
            continue
        for p in lk["powers_by_set"].get(sfull, []):
            if p["display_name"].lower() == disp:
                return p
    return None


def _resolve_slot(uid, io_level, lk):
    """Crafted UID -> our slot dict (carrying io_level), or None if unknown."""
    pc = lk["piece_by_uid"].get(uid)
    if pc:
        slot = dict(pc)
        slot["io_level"] = io_level
        slot["attuned"] = "Attuned" in uid or uid.startswith("Superior_")
        return slot
    if uid in lk["common_io_uids"] or uid in lk["piece_image"]:
        return {"set_uid": None, "set_name": None, "piece_uid": uid,
                "piece_name": uid, "category_id": None,
                "image": lk["piece_image"].get(uid, ""), "io_level": io_level,
                "attuned": False}
    return None


def _classify(powerset_full, archetype, lk):
    """Which build slot a powerset belongs to: primary/secondary/epic/pool/None."""
    at_ps = lk["powersets_by_at"].get(archetype, {})
    for role in ("primary", "secondary", "epic"):
        if any(s["full_name"] == powerset_full for s in at_ps.get(role, [])):
            return role
    if any(s["full_name"] == powerset_full for s in lk["pools"]):
        return "pool"
    return None


def parse_ingame_build(text, lk):
    """text: the raw /build_save_file contents. lk: server._import_lookups()
    (extended with powersets_by_at, pools, powers_by_set, common_io_uids).
    Returns the same shape as mids_import.parse_build (+ pick_level / io_level)."""
    name, char_level, archetype, blocks = _parse_blocks(text)
    if not blocks:
        return {"ok": False, "error": "No powers found — is this a /build_save_file export?"}
    if not archetype:
        return {"ok": False, "error": "Couldn't read the archetype from the header line."}

    locked_epic = _lock_epic_set(blocks, archetype, lk)
    powers, unresolved_enh, unresolved_powers = [], [], []
    roles = {"primary": None, "secondary": None, "epic": None, "pools": []}

    for b in blocks:
        rec = _resolve_power(b, archetype, locked_epic, lk)
        if rec == "skip":
            continue
        if not rec:
            unresolved_powers.append(f"{b['group']}.{b['pset']}.{b['power']}")
            continue
        slots, earned = [], 0
        for entry in b["slots"]:
            earned += 1
            if entry is None:
                slots.append(None)       # EMPTY slot: keep it in the layout, not dropped
                continue
            uid, io_level = entry
            slot = _resolve_slot(uid, io_level, lk)
            if slot:
                slots.append(slot)
            else:
                unresolved_enh.append(uid)
                slots.append({"set_uid": None, "set_name": None, "piece_uid": None,
                              "piece_name": uid, "category_id": None, "image": "",
                              "io_level": io_level, "attuned": False})
        ps_full = rec["powerset_full_name"]
        role = _classify(ps_full, archetype, lk)
        if role == "primary":
            roles["primary"] = ps_full
        elif role == "secondary":
            roles["secondary"] = ps_full
        elif role == "epic":
            roles["epic"] = ps_full
        elif role == "pool" and ps_full not in roles["pools"]:
            roles["pools"].append(ps_full)
        powers.append({
            "full_name": rec["full_name"],
            "display_name": rec["display_name"],
            "powerset_full_name": ps_full,
            "accepted_set_category_ids": rec.get("accepted_set_category_ids", []),
            "accepted_set_categories": rec.get("accepted_set_categories", []),
            "power_type": rec.get("power_type"),
            "level_available": rec.get("level_available"),
            "pick_level": b["pick_level"],
            "earned_slot_count": earned,
            "slots": slots,
        })

    build = {
        "archetype": archetype,
        "primary": roles["primary"], "secondary": roles["secondary"],
        "pools": roles["pools"][:4], "epic": roles["epic"],
        "incarnates": {},            # the in-game export doesn't list incarnates
        "char_level": char_level,
        "powers": powers,
    }
    return {"ok": True, "build": build, "name": name, "archetype": archetype,
            "char_level": char_level, "unresolved_enh": sorted(set(unresolved_enh)),
            "unresolved_powers": unresolved_powers}
