"""
mids_import.py - Parse a Mids Reborn .mbd file (plain JSON CharacterBuildData)
into our build structure. The reverse of mids_export.build_mbd.

Mids serializes each slotted enhancement either as:
  {"Uid": "<enh uid>", ...}                         (newer / our own exports)
  {"Enhancement": "Set Name: Piece Name", ...}      (name form; resolved by name)
so we resolve by name first ("Set: Piece" or "Invention: <aspect>"), then by uid.
Unresolved enhancements (e.g. Hamidon Os) keep the slot but carry no set/piece,
and are reported back so the critique can mention them.
"""


def _resolve_enh(enh, lk):
    """Resolve one Mids Enhancement object -> our slot dict, or None if unknown."""
    if not isinstance(enh, dict):
        return None
    name = (enh.get("Enhancement") or "").strip()
    uid = (enh.get("Uid") or "").strip()

    # 1) set piece by display name "Set: Piece"
    if name:
        pc = lk["name_to_piece"].get(name.lower())
        if pc:
            return dict(pc)
        low = name.lower()
        # common/generic IO: "Invention: Recharge Reduction"
        if ":" in low:
            asp = low.split(":", 1)[1].strip()
            cu = lk["common_io_map"].get(asp)
            if cu:
                return _common_slot(cu, name, lk)
        cu = lk["common_io_map"].get(low)
        if cu:
            return _common_slot(cu, name, lk)

    # 2) by uid (our exports use the piece uid; also try common-IO uid)
    if uid:
        pc = lk["piece_by_uid"].get(uid)
        if pc:
            return dict(pc)
        if uid in lk["piece_image"]:
            return _common_slot(uid, name or uid, lk)

    return None


def _common_slot(uid, label, lk):
    return {"set_uid": None, "set_name": None, "piece_uid": uid,
            "piece_name": label or uid, "category_id": None,
            "image": lk["piece_image"].get(uid, "")}


def parse_build(data, lk):
    """data: parsed .mbd JSON dict. lk: lookup dicts (see server._import_lookups).
    Returns {ok, build, unresolved_enh, unresolved_powers, name, archetype}."""
    if not isinstance(data, dict) or "PowerEntries" not in data:
        return {"ok": False, "error": "Not a Mids .mbd build (no PowerEntries)."}

    archetype = data.get("Class")
    ps = data.get("PowerSets") or []

    def setname(i):
        v = ps[i] if i < len(ps) else ""
        return v if v and v != "Inherent.Inherent" else None

    primary = setname(0)
    secondary = setname(1)
    pools = [ps[i] for i in (3, 4, 5, 6)
             if i < len(ps) and ps[i] and str(ps[i]).startswith("Pool.")]
    epic = setname(7)

    power_by_full = lk["power_by_full"]
    inc_index = lk["incarnate_index"]

    powers = []
    incarnates = {}
    unresolved_enh = []
    unresolved_powers = []
    for pe in data.get("PowerEntries", []):
        full = pe.get("PowerName")
        if not full:
            continue
        # incarnate selections come through as power entries by full name
        inc = inc_index.get(full)
        if inc:
            incarnates[inc["slot"]] = {"full_name": full,
                                       "display_name": inc["display_name"]}
            continue
        rec = power_by_full.get(full)
        if not rec:
            # skip inherent/temp/uncatalogued power entries silently unless they
            # look like a real pick; record only meaningful misses
            if str(full).split(".")[0] not in ("Inherent", "Temporary_Powers"):
                unresolved_powers.append(full)
            continue
        slots = []
        earned = 0
        for se in pe.get("SlotEntries", []) or []:
            earned += 1
            enh = se.get("Enhancement")
            if not enh:
                continue                 # earned-but-empty slot
            slot = _resolve_enh(enh, lk)
            io_level = enh.get("IoLevel")
            if slot:
                slot["io_level"] = io_level
                slot["attuned"] = "Attuned" in (enh.get("Uid") or "") \
                    or str(enh.get("Uid") or "").startswith("Superior_")
                slots.append(slot)
            else:
                label = (enh.get("Enhancement") or enh.get("Uid") or "?")
                unresolved_enh.append(label)
                slots.append({"set_uid": None, "set_name": None,
                              "piece_uid": None, "piece_name": label,
                              "category_id": None, "image": "",
                              "io_level": io_level, "attuned": False})
        powers.append({
            "full_name": rec["full_name"],
            "display_name": rec["display_name"],
            "powerset_full_name": rec["powerset_full_name"],
            "accepted_set_category_ids": rec.get("accepted_set_category_ids", []),
            "accepted_set_categories": rec.get("accepted_set_categories", []),
            "power_type": rec.get("power_type"),
            "level_available": rec.get("level_available"),
            "pick_level": pe.get("Level"),
            "earned_slot_count": earned,
            "slots": slots,
        })

    build = {
        "archetype": archetype,
        "primary": primary, "secondary": secondary,
        "pools": pools, "epic": epic,
        "incarnates": incarnates,
        "powers": powers,
    }
    return {"ok": True, "build": build, "name": data.get("Name") or "Imported build",
            "archetype": archetype, "unresolved_enh": sorted(set(unresolved_enh)),
            "unresolved_powers": unresolved_powers}
