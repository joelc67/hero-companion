"""
server.py - Flask backend for the CoH Build Planner.

Serves the SPA and exposes the data + validation + calculation + AI endpoints.
All game data is loaded once at startup from the JSON produced by
tools/parse_mids.py (sourced from Mids Reborn).
"""

import copy
import json
import os
import time
import re
import sys
from collections import defaultdict, Counter

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# --- make sibling packages importable (ai/, server/) ---
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "ai"))

import engine                      # noqa: E402
import claude_bridge               # noqa: E402
import ai_build                    # noqa: E402
import mids_export                 # noqa: E402
import mids_import                 # noqa: E402
import ingame_import               # noqa: E402
import proc_pass                   # noqa: E402
import mids_powercust              # noqa: E402
import solver                      # noqa: E402
import leveling_schedule          # noqa: E402
import converter                   # noqa: E402
import role_output                 # noqa: E402

# Packaged (PyInstaller) build: bundled read-only assets (data/, static/, VERSION,
# client_config.json) live under the bundle root, not the source tree.
if getattr(sys, "frozen", False):
    ROOT = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))

DATA_DIR = os.path.join(ROOT, "data")
STATIC_DIR = os.path.join(ROOT, "static")

app = Flask(__name__, static_folder=None)
CORS(app)

# After a self-update relaunch, run_app waits briefly for the OLD browser tab to
# reconnect (its update poll) before deciding whether to open a new tab at all.
SEEN_REQUEST = False


@app.before_request
def _mark_request_seen():
    global SEEN_REQUEST
    SEEN_REQUEST = True


# ---------------------------------------------------------------------------
# Load data once
# ---------------------------------------------------------------------------
def _load(name):
    with open(os.path.join(DATA_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


print("Loading game data...")
ARCHETYPES = _load("archetypes.json")
POWERSETS = _load("powersets.json")
POWERS = _load("powers.json")
ENH_SETS = _load("enhancement_sets.json")
SET_BONUSES = _load("set_bonuses.json")
SET_CATEGORIES = _load("set_categories.json")
INCARNATES = _load("incarnates.json")
COMMON_IOS = _load("common_ios.json")
SUMMONS = _load("summons.json")["entities"]   # entity UID -> pet powersets
# summon power full_name -> {pets:[{uid,count,class}],duration,permanent,copy_boosts}
# (reconciled from the game client's EntCreate templates — squads, uptime, live classes)
SUMMON_POWERS = _load("summons.json").get("powers") or {}

# keyword -> common IO uid (for resolving generic "Accuracy IO" etc.)
COMMON_IO_MAP = {}
for _c in COMMON_IOS["common_ios"]:
    COMMON_IO_MAP[_c["name"].lower()] = _c["uid"]
    for _asp in _c["enhances"]:
        COMMON_IO_MAP.setdefault(_asp.lower(), _c["uid"])
# friendly aliases the AI tends to use
COMMON_IO_MAP.update({
    "accuracy": "Crafted_Accuracy", "damage": "Crafted_Damage",
    "recharge": "Crafted_Recharge", "recharge reduction": "Crafted_Recharge",
    "defense": "Crafted_Defense_Buff", "resist": "Crafted_Res_Damage",
    "resistance": "Crafted_Res_Damage", "heal": "Crafted_Heal",
    "healing": "Crafted_Heal", "endurance reduction": "Crafted_Endurance_Discount",
    "endredux": "Crafted_Endurance_Discount", "endrdx": "Crafted_Endurance_Discount",
    "endmod": "Crafted_Recovery", "endurance modification": "Crafted_Recovery",
    "tohit": "Crafted_ToHit_Buff", "to hit": "Crafted_ToHit_Buff",
    "range": "Crafted_Range", "taunt": "Crafted_Taunt", "threat": "Crafted_Taunt",
})

# Indexes
PLAYABLE = [a for a in ARCHETYPES["archetypes"] if a.get("playable")]
ARCH_BY_NAME = {a["name"]: a for a in ARCHETYPES["archetypes"]}
# v31: preset_targets derives the AFK-farm regen floor from the AT's base HP
# (the stated simplification) — register the lookup so every call site can
# just pass archetype=.
ai_build.BASE_HP_BY_AT = {a["name"]: a.get("hitpoints") or 0
                          for a in ARCHETYPES["archetypes"]}


def _at_solve_phys(archetype):
    """The AT physics solve_ilp's post-target decay derives from (v30): the
    hard res cap bounds the resistance segment, base HP feeds the availability
    curve ρ is measured on. Empty for an unknown AT — the solver then skips
    the decay rather than derive from wrong physics."""
    at = ARCH_BY_NAME.get(archetype or "")
    if not at:
        return {}
    return {"at_res_cap": at.get("res_cap") or 0.75,
            "at_base_hp": at.get("hitpoints") or 0}
CAT_BY_ID = {c["id"]: c for c in SET_CATEGORIES["categories"]}
CAT_BY_SHORT = {c["short"].lower(): c for c in SET_CATEGORIES["categories"]}
CAT_BY_NAME = {c["name"].lower(): c for c in SET_CATEGORIES["categories"]}

SETS_BY_CATEGORY = {}
SET_BY_UID = {}
SET_BY_NAME = {}
for s in ENH_SETS:
    SETS_BY_CATEGORY.setdefault(s["category_id"], []).append(s)
    SET_BY_UID[s["uid"]] = s
    SET_BY_NAME[s["name"].lower()] = s

# full_name -> power record (for level lookup + self-effects)
POWER_BY_FULL = {p["full_name"]: p for plist in POWERS.values() for p in plist}
DB_NAME = "Homecoming"
DB_VERSION = ARCHETYPES.get("version") or "0.0.0.0"

# App version (VERSION file at the repo/bundle root) + the client's pointers to the
# project's online home (GitHub). client_config.json ships with the install; the
# REPLACE-ME placeholder keeps every phone-home feature politely disabled until the
# repository actually exists.
try:
    with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as _vf:
        APP_VERSION = _vf.read().strip()
except OSError:
    APP_VERSION = "0.0.0"
try:
    with open(os.path.join(ROOT, "client_config.json"), encoding="utf-8") as _cf:
        CLIENT_CONFIG = json.load(_cf)
except Exception:  # noqa: BLE001 — missing/broken config just disables the links
    CLIENT_CONFIG = {}

# AI seam — AI is OPT-IN everywhere (user decision 2026-07-04: "no mention of an
# AI assistant"): the planner is fully deterministic and the product has ONE face.
# HC_AI=1 enables the assistant (hub work / bring-your-own-key); default is off,
# packaged or from source alike.
AI_ENABLED = os.environ.get("HC_AI") == "1"


def _ai_gate():
    """None when AI may run; otherwise the friendly refusal every /ai endpoint returns."""
    if AI_ENABLED:
        return None
    return jsonify({"ok": False, "response":
                    "The AI assistant isn't included in this standalone build — everything "
                    "the planner does (the wizard, Solve, the optimizer) is deterministic "
                    "and needs no AI. Advanced: set HC_AI=1 with your own Claude key to "
                    "enable the assistant."}), 403

# ---- stat-engine data ----
MODIFIER_TABLES = _load("modifier_tables.json")["tables"]
MATHS = _load("maths.json")
MULT_ED = MATHS["mult_ed"]
MULT_IO = MATHS["mult_io"]      # level -> [schedA,B,C,D] IO enhancement values
# FIRST occurrence wins: the class table carries DUPLICATE names (Class_Minion_Henchman at
# columns 17 AND 42 — 42's modifier values are garbage; last-wins made demonlings hit for 361
# per claw, 3× a Scrapper). The real class sits in its family cluster (Boss/Lt/Minion 15/16/17).
AT_COLUMN = {}
for _a in ARCHETYPES["archetypes"]:
    AT_COLUMN.setdefault(_a["name"], _a.get("column"))

# piece uid -> enhancement boosts (per-aspect value) for set pieces + common IOs
PIECE_BOOSTS = {}
# piece uid -> icon filename (set pieces fall back to the set's icon)
PIECE_IMAGE = {}
# piece uid -> the level its stored boost value was computed at (parser used
# clamp(set.level_max,10,50); common IOs are stored at level 50). Used to scale
# a slot's magnitude to its actual IO level.
PIECE_REF_LEVEL = {}
for s in ENH_SETS:
    ref = max(10, min(50, s.get("level_max") or 50))
    for pc in s["pieces"]:
        if pc.get("uid") and pc.get("boosts"):
            PIECE_BOOSTS[pc["uid"]] = pc["boosts"]
        if pc.get("uid"):
            PIECE_IMAGE[pc["uid"]] = pc.get("image") or s.get("image") or ""
            PIECE_REF_LEVEL[pc["uid"]] = ref
for c in COMMON_IOS["common_ios"]:
    if c.get("uid") and c.get("boosts"):
        PIECE_BOOSTS[c["uid"]] = c["boosts"]
    if c.get("uid"):
        PIECE_IMAGE[c["uid"]] = c.get("image") or ""
        PIECE_REF_LEVEL[c["uid"]] = 50
# Hamidon/Titan/Hydra Origin enhancements (multi-aspect, grade-priced). Deliberately NO
# PIECE_REF_LEVEL entry: HO values are grade-flat, never IO-level-scaled — _scaled_boosts
# uses the stored value as-is (a master's Enzyme at "IoLevel 1" must not scale to zero).
# (0.12.13 shipped a duplicate of this loop spliced INTO the common-IO loop above: common
# IOs lost their icons — slots looked EMPTY in the UI — and HOs gained a ref level that
# scaled low-level imports toward zero. One loop each, and the coherence audit now pins it.)
for c in COMMON_IOS.get("special_ios", []):
    if c.get("uid") and c.get("boosts"):
        PIECE_BOOSTS[c["uid"]] = c["boosts"]
    if c.get("uid"):
        PIECE_IMAGE[c["uid"]] = c.get("image") or ""

# Import lookups: resolve a Mids enhancement (by "Set: Piece" name or uid) -> slot.
PIECE_BY_UID = {}        # piece uid -> slot dict
ENH_NAME_TO_PIECE = {}   # "set name: piece name" (lower) -> slot dict
for s in ENH_SETS:
    for pc in s["pieces"]:
        if not pc.get("uid"):
            continue
        slot = {"set_uid": s["uid"], "set_name": s["name"],
                "piece_uid": pc["uid"], "piece_name": pc["name"],
                "category_id": s.get("category_id"),
                "image": pc.get("image") or s.get("image") or ""}
        PIECE_BY_UID[pc["uid"]] = slot
        ENH_NAME_TO_PIECE[f"{s['name']}: {pc['name']}".lower()] = slot

# full_name -> {slot, display_name} for incarnate choices (import resolution)
INCARNATE_INDEX = {}
for _slot in INCARNATES.get("slots", []):
    for _ch in _slot.get("choices", []):
        if _ch.get("full_name"):
            INCARNATE_INDEX[_ch["full_name"]] = {
                "slot": _slot.get("slot") or _slot.get("name") or "",
                "display_name": _ch.get("display_name") or _ch["full_name"]}


def _import_lookups():
    return {"power_by_full": POWER_BY_FULL, "piece_by_uid": PIECE_BY_UID,
            "name_to_piece": ENH_NAME_TO_PIECE, "common_io_map": COMMON_IO_MAP,
            "piece_image": PIECE_IMAGE, "incarnate_index": INCARNATE_INDEX,
            # extras used by the in-game (/build_save_file) text importer
            "powersets_by_at": POWERSETS.get("by_archetype", {}),
            "pools": POWERSETS.get("pools", []),
            "powers_by_set": POWERS,
            "common_io_uids": set(COMMON_IO_MAP.values())}


def _is_support_powerset(ps_full):
    """True if a powerset full_name (e.g. 'Defender_Buff.Kinetics') is a dedicated
    buff/debuff support set — its signature buffs are the slot-reservation priority."""
    name = (ps_full or "").split(".")[-1].replace("_", " ").lower()
    return name in ai_build.SUPPORT_SETS


def _enrich_solver_powers(powers):
    """Add the fields the solver's buff-slotting pass needs (recharge, accepted
    common-enh types, max slots) from the master power records."""
    for p in powers:
        rec = POWER_BY_FULL.get(p.get("full_name"))
        if rec:
            if p.get("is_attack") is None:
                p["is_attack"] = rec.get("is_attack")
            p["base_recharge"] = rec.get("base_recharge")
            p["max_slot_count"] = rec.get("max_slot_count")
            p["accepted_enhancement_types"] = rec.get("accepted_enhancement_types", [])
    return powers


def _fill_slot_images(resolved):
    """Ensure every resolved slot carries an icon filename (by piece uid) AND the IO's
    buy level — the set's max (Mids stores levels 0-based, so +1). Field report: set
    pieces showed no level under their icons while common IOs showed 50."""
    for pw in resolved.get("powers", []):
        for slot in pw.get("slots", []) or []:
            if not slot:
                continue
            if not slot.get("image"):
                slot["image"] = PIECE_IMAGE.get(slot.get("piece_uid"), "")
            rec = (SET_BY_UID.get(slot.get("set_uid"))                       # solver slots
                   or SET_BY_NAME.get((slot.get("set_name") or "").lower()))  # proc-pass slots
            if not rec:
                continue
            if not slot.get("io_level") and rec.get("level_max") is not None:
                slot["io_level"] = min(50, int(rec["level_max"]) + 1)
            # The proc pass labels its pieces just "proc" (field report: "Annihilation:
            # proc — what is that?") — resolve the REAL piece name from the catalog.
            if slot.get("piece_name") in (None, "", "proc") and slot.get("piece_uid"):
                pc = next((q for q in (rec.get("pieces") or [])
                           if q.get("uid") == slot["piece_uid"]), None)
                if pc and pc.get("name"):
                    slot["piece_name"] = pc["name"]
    return resolved


# full_name -> [effects]; only Destiny/Hybrid/Judgement carry flat effect data.
INCARNATE_FX = {}
INCARNATE_NAMES = {}       # full_name -> display_name (per-source attribution)
for _slot in INCARNATES.get("slots", []):
    for _choice in _slot.get("choices", []):
        INCARNATE_NAMES[_choice["full_name"]] = (
            _choice.get("display_name") or _choice["full_name"].split(".")[-1])
        if _choice.get("effects"):
            INCARNATE_FX[_choice["full_name"]] = _choice["effects"]


# Categories that go in always-on survival/utility powers (toggles, Health,
# defenses) — i.e. sets a build can slot WITHOUT taking attacks. A Fire-res
# bonus that only exists on an attack-set purple is useless to a no-damage
# buffer, so for Resistance/Defense stat hints we prefer these.
_UTILITY_CATS = {"Resist Damage", "Defense Sets", "Healing",
                 "Endurance Modification", "To Hit Buff"}

# Short tag telling the AI which power TYPE a set goes in (it otherwise slots
# e.g. a Melee purple into a Ranged blast and the piece gets dropped).
_CAT_ABBR = {
    "Ranged Damage": "Ranged", "Melee Damage": "Melee", "PBAoE Damage": "PBAoE",
    "Targeted AoE Damage": "Targeted-AoE", "Sniper Attacks": "Sniper",
    "Slow Movement": "Slow", "Holds": "Hold", "Stuns": "Stun",
    "Immobilize": "Immob", "Sleep": "Sleep", "Confuse": "Confuse", "Fear": "Fear",
    "Resist Damage": "resist toggle", "Defense Sets": "defense toggle",
    "Healing": "heal/Health", "Endurance Modification": "endmod",
    "To Hit Buff": "ToHit power", "Knockback": "knockback",
}


def _cat_tag(cat):
    return _CAT_ABBR.get(cat, cat)

# (effect, damage_type) -> {set_name: (value, category)}.
BONUS_BY_STAT = {}
for _rec in SET_BONUSES.values():
    _cat = _rec.get("category", "")
    for _b in _rec.get("bonuses", []):
        if _b.get("pv_mode") == 2:        # skip PvP-only bonuses
            continue
        for _e in _b.get("effects", []):
            if _e.get("effect") in ("Resistance", "Defense") and _e.get("value", 0) > 0:
                _key = (_e["effect"], _e.get("damage_type"))
                _d = BONUS_BY_STAT.setdefault(_key, {})
                if _e["value"] > _d.get(_rec["name"], (0.0, ""))[0]:
                    _d[_rec["name"]] = (_e["value"], _cat)


def _set_hints(goal):
    """Tell the AI which real sets grant the bonuses the goal needs (it picks
    sets blind to their bonuses otherwise). Splits sets the build can slot in
    survival/utility powers from attack-set bonuses, so a no-attack buffer is
    pointed at sets it can actually use."""
    labels = [m["label"] for m in ai_build.interpret_goal(goal)["matched"]]
    needs = []
    for lb in labels:
        for need in ai_build.LABEL_BONUS_NEEDS.get(lb, []):
            if need not in needs:
                needs.append(need)
    if not needs:
        return None
    lines = ["Real Invention sets whose set BONUSES grant the goal-critical "
             "stats. To STACK a stat you must reach a set's piece threshold "
             "(usually 3-6 pieces of ONE set in ONE power). Do not guess which "
             "set gives what — use these:"]
    for eff, dt in needs:
        ranked = sorted(BONUS_BY_STAT.get((eff, dt), {}).items(), key=lambda kv: -kv[1][0])
        # annotate each set with the power TYPE it must be slotted in
        util = [f"{n} ({_cat_tag(c)})" for n, (_, c) in ranked if c in _UTILITY_CATS][:10]
        atk = [f"{n} ({_cat_tag(c)})" for n, (_, c) in ranked if c not in _UTILITY_CATS][:10]
        if util:
            lines.append(f"- +{dt} {eff} — in toggles/Health/defenses: "
                         + ", ".join(util))
        if atk:
            lines.append(f"- +{dt} {eff} — in attack/control powers (slot 6 "
                         f"pieces in a power of the matching type; the main "
                         f"source, take the attacks to get these): " + ", ".join(atk))
    return "\n".join(lines) if len(lines) > 1 else None


def _stat_ctx(archetype):
    at = ARCH_BY_NAME.get(archetype) or {}
    return {
        "power_by_full": POWER_BY_FULL,
        "piece_boosts": PIECE_BOOSTS,
        "modifier_tables": MODIFIER_TABLES,
        "mult_ed": MULT_ED,
        "mult_io": MULT_IO,
        "piece_ref_level": PIECE_REF_LEVEL,
        "at_column": AT_COLUMN.get(archetype),
        "at_damage_cap": at.get("damage_cap"),
        "at_recharge_cap": at.get("recharge_cap"),
        "at_hp_cap": at.get("hp_cap"),          # ABSOLUTE max HP (e.g. 1606); base below
        "at_base_hp": at.get("hitpoints"),      # base HP -> converts hp_cap to a +%MaxHP cap
        "at_regen_cap": at.get("regen_cap"),    # bonus-fraction caps (20.0 => +2000%)
        "at_recovery_cap": at.get("recovery_cap"),
        "incarnate_fx": INCARNATE_FX,
        "incarnate_names": INCARNATE_NAMES,  # full_name -> display (attribution)
        "entities": SUMMONS,           # summon UID -> pet powersets (for pet dmg)
        "summon_powers": SUMMON_POWERS,  # power -> squad spec (counts/uptime/class)
        "class_columns": AT_COLUMN,    # any class name -> AttribMod column (incl pets)
        "powers_by_set": POWERS,       # powerset full_name -> [power recs] (pet attacks)
    }

print(f"  {len(PLAYABLE)} playable archetypes, {len(POWERS)} powersets of powers, "
      f"{len(ENH_SETS)} enhancement sets.")

# Prefer the fast Messages API path; load the subscription token if the launcher
# didn't put it in our env.
_has_token = claude_bridge.ensure_oauth_token()
_claude_info = claude_bridge.detect_info()
if _has_token:
    _kind = claude_bridge._api_creds()[0]
    print(f"  AI: Messages API fast-path ({_kind}), model={claude_bridge.GEN_MODEL}")
elif _claude_info["found"]:
    print(f"  AI: no API token — using slow `claude -p` CLI at {_claude_info['found']}")
else:
    print("  AI: NOT available (no token, no CLI). CLAUDE_BIN="
          f"{_claude_info['CLAUDE_BIN_env'] or '(unset)'}")


# ---------------------------------------------------------------------------
# Static SPA
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    # CACHE-BUSTING (Joel's 0.12.20 standing requirement: "users must never
    # need Ctrl+F5"): every static asset URL in the page carries a version
    # token derived from the app version AND the asset file's mtime, so a
    # release OR a dev-server restart after an edit reaches every browser on
    # a plain reload. index.html itself is served no-store so the tokens are
    # always current; the tokenized assets get long-lived caching below —
    # faster than before AND always fresh.
    with open(os.path.join(STATIC_DIR, "index.html"), encoding="utf-8") as f:
        html = f.read()

    def _tok(fname):
        try:
            mt = int(os.path.getmtime(os.path.join(STATIC_DIR, fname)))
        except OSError:
            mt = 0
        return f"{APP_VERSION}-{mt}"

    html = re.sub(
        r'((?:src|href)="/static/([^"?]+))"',
        lambda m: f'{m.group(1)}?v={_tok(m.group(2))}"',
        html)
    resp = app.response_class(html, mimetype="text/html")
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/static/<path:fname>")
def static_files(fname):
    resp = send_from_directory(STATIC_DIR, fname)
    # versioned URLs may cache hard; unversioned requests must revalidate
    if request.args.get("v"):
        resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    else:
        resp.headers["Cache-Control"] = "no-cache"
    return resp


# Legal / attribution pages — the markdown files at the repo root, rendered just enough
# to be readable in a browser (headers, bold, links, bullets). No markdown dependency.
_DOC_PAGES = {"terms": "TERMS.md", "license": "LICENSE", "credits": "CREDITS.md"}


def _md_to_html(text):
    import re as _re
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = _re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
                   r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    text = _re.sub(r"(?<![\"=])(https?://[^\s<)]+)", r'<a href="\1" target="_blank" rel="noopener">\1</a>', text)
    text = _re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = _re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", text)
    out = []
    for ln in text.split("\n"):
        if ln.startswith("### "):   out.append(f"<h3>{ln[4:]}</h3>")
        elif ln.startswith("## "):  out.append(f"<h2>{ln[3:]}</h2>")
        elif ln.startswith("# "):   out.append(f"<h1>{ln[2:]}</h1>")
        elif ln.startswith("- "):   out.append(f"<li>{ln[2:]}</li>")
        elif ln.strip() == "---":   out.append("<hr>")
        elif not ln.strip():        out.append("<br>")
        else:                       out.append(f"{ln} ")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Distribution plumbing: versions, update check, feedback, champion candidates.
# The client NEVER phones home on its own — every outbound touch is a user click,
# and all of it goes through the GitHub home configured in client_config.json.
# ---------------------------------------------------------------------------
@app.route("/accolades")
def accolades_roster():
    """v34 accolade panel — DISPLAY-ONLY scaffold (v33 rides nothing from this).

    Serves data/accolades.json: the roster GAME-FIRST from the client bins
    (tools/extract_accolades.py), tiered exactly as Joel's scope ruling asks —
    build-affecting passives first, click-power accolades next, badge-only rows
    last, each honestly marked. Ordering inside the passive tier is by impact
    magnitude (computed from the game's own scales, never hand-ranked).

    NOT wired to totals or labels: checking a row changes nothing today. The
    model half (apply-all preview, per-accolade totals, label statements) is
    v34 per the one-batch-one-refresh ruling; the farm-preset accolade
    ASSUMPTION that DOES ship in v33 lives in first_principles, not here.
    ATTAINMENT text is absent by design: Phase-0 established the client carries
    what an accolade grants, not how it is earned (no player badges.bin, no
    requirement chains — that logic is server-side in CoH), so those pop-ups
    await the wiki as an explicitly labeled guidance-tier last resort.
    """
    try:
        base = getattr(sys, "_MEIPASS", None) or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..")
        with open(os.path.join(base, "data", "accolades.json"),
                  encoding="utf-8") as f:
            roster = json.load(f)
    except Exception:  # noqa: BLE001
        return jsonify({"ok": False, "rows": []})
    # v34 item 4: attain-it text, GAME-SOURCED ONLY (Joel's no-wiki amendment).
    # Where the client carries no binding and Joel has not yet supplied the
    # badge-window text, the row says so honestly rather than borrowing prose.
    try:
        with open(os.path.join(base, "data", "accolade_attainment.json"),
                  encoding="utf-8") as f:
            attain = json.load(f)
    except Exception:  # noqa: BLE001
        attain = {}
    order = {"passive": 0, "click": 1, "badge_only": 2}

    def impact(v):
        e = v.get("effects") or {}
        return (e.get("HitPoints") or 0) * 10 + (e.get("Endurance") or 0) * 0.5

    def effect_short(v):
        """The one-line row text. The panel is WIDE AND SHORT (Joel's corrected
        placement), so a row gets one line — the game's full sentence rides the
        hover title instead. HitPoints scale 1.0 = +10% MaxHP, corroborated by
        the client's own wording ('Freedom Phalanx Reserve … +10% Max Hit
        Points')."""
        e = v.get("effects") or {}
        bits = []
        if e.get("HitPoints"):
            bits.append(f"+{e['HitPoints'] * 10:.0f}% HP")
        if e.get("Endurance"):
            bits.append(f"+{e['Endurance']:.0f} End")
        if e.get("Recovery"):
            bits.append(f"+{e['Recovery']:.0f} Rec")
        if e.get("Regeneration"):
            bits.append(f"+{e['Regeneration']:.0f} Regen")
        return " ".join(bits)
    # v34 item 5: which accolades a generated level-50 build assumes. ONE source
    # of truth — first_principles.FARM_ASSUMED_ACCOLADES, the same four the
    # scoring side already assumes for farm presets and the same four every
    # community reference build carries. Never a second list.
    import first_principles as _fp
    import engine as _engine
    # The canonical standard set = the four hero accolades every endgame build
    # assumes (FARM_ASSUMED, explicit names) + their DIRECT villain equivalents
    # (the villain-aligned accolade sharing each standard's effect signature —
    # exactly one per signature, so unambiguous). The no-gate extras (Labyrinth
    # Conqueror, Mazebreaker) and the odd Super Patriot are NOT standard; they
    # remain optional stacking choices. The client preselects the four matching
    # the character's alignment.
    hero_std = set(_fp.FARM_ASSUMED_ACCOLADES)
    std_sigs = {_engine.accolade_signature(roster[k]) for k in hero_std
                if k in roster}

    def is_standard(k, v):
        if k in hero_std:
            return True
        return (v.get("alignment") == "villain"
                and _engine.accolade_signature(v) in std_sigs)

    rows = [dict(key=k, effect_short=effect_short(v),
                 standard_assumed=is_standard(k, v),
                 attain=(attain.get(k) or {}).get("text", ""),
                 attain_source=(attain.get(k) or {}).get("source", ""),
                 attain_summary=(attain.get(k) or {}).get("summary", ""),
                 badge_chain=(attain.get(k) or {}).get("badge_chain", []),
                 attain_note=(attain.get(k) or {}).get("note", ""),
                 attain_unobtainable=bool((attain.get(k) or {}).get("unobtainable")), **v)
            for k, v in roster.items()]
    rows.sort(key=lambda v: (order.get(v["tier"], 9), -impact(v),
                             v["display"]))
    return jsonify({"ok": True, "rows": rows,
                    "tiers": {t: sum(1 for r in rows if r["tier"] == t)
                              for t in order}})


@app.route("/meta")
def meta():
    import first_principles as fp
    # form_champions gates the wizard's Kheldian Form question: it only shows
    # when form-tagged champions actually ship in this build — a route is never
    # offered to a champion that isn't there (Joel's roster-split release,
    # 2026-07-13: non-Kheldian roster first, Kheldians + forms later that week).
    try:
        import learn as _learn
        _ch = json.load(open(_learn.CHAMPIONS_PATH, encoding="utf-8"))
        has_forms = any(len(k.split("|")) > 4 for k in _ch)
        champion_count = len(_ch)
    except Exception:  # noqa: BLE001
        has_forms = False
        champion_count = 0
    return jsonify({"ok": True, "app_version": APP_VERSION, "model_version": fp.MODEL_VERSION,
                    "db_name": DB_NAME, "db_version": DB_VERSION,
                    "packaged": bool(getattr(sys, "frozen", False)),
                    "form_champions": has_forms,
                    "champion_count": champion_count,
                    "urls": CLIENT_CONFIG.get("urls", {})})


@app.route("/meta/update-check")
def update_check():
    """User-initiated check against the project's GitHub Releases — compares tags only,
    sends nothing about the user or their builds."""
    import re as _re
    api_url = (CLIENT_CONFIG.get("urls") or {}).get("releases_api") or ""
    if not api_url or "REPLACE-ME" in api_url:
        return jsonify({"ok": False, "reason": "not_configured"})
    try:
        import requests
        r = requests.get(api_url, timeout=6, headers={"Accept": "application/vnd.github+json"})
        r.raise_for_status()
        rel = r.json()
        latest = (rel.get("tag_name") or "").lstrip("vV")

        def _t(v):
            return tuple(int(x) for x in (_re.findall(r"\d+", v)[:3] or ["0"]))

        return jsonify({"ok": True, "current": APP_VERSION, "latest": latest,
                        "update_available": _t(latest) > _t(APP_VERSION),
                        "url": rel.get("html_url") or (CLIENT_CONFIG.get("urls") or {}).get("releases")})
    except Exception as e:  # noqa: BLE001 — offline is a normal state, not an error page
        return jsonify({"ok": False, "reason": "offline", "error": str(e)[:200]})


# Set by the packaged launcher (run_app) to a callable that stops the tray icon and exits.
# A clean stop is what removes the Windows tray icon — a force-kill orphans it as a "ghost"
# that lingers until you hover the notification area. None in dev/source mode.
SHUTDOWN_HOOK = None


@app.route("/app/shutdown", methods=["POST"])
def app_shutdown():
    """Ask THIS instance to exit cleanly. A self-update calls this on the old copy so it
    removes its own tray icon before making way for the new one — instead of being force-
    killed (which leaves the ghost icon the user reported). No-op in dev (no tray to close)."""
    hook = SHUTDOWN_HOOK
    if not hook:
        return jsonify({"ok": False, "reason": "not_packaged"})

    def _later():
        import time
        time.sleep(0.3)          # let the HTTP response flush first
        try:
            hook()
        except Exception:  # noqa: BLE001
            os._exit(0)
    import threading
    threading.Thread(target=_later, daemon=True).start()
    return jsonify({"ok": True, "stopping": True})


def _graceful_self_exit_for_update():
    """After a self-update hands off to the installer, retire THIS process by removing its
    own tray icon cleanly (SHUTDOWN_HOOK -> icon.stop) instead of waiting to be force-killed
    — a force-kill orphans the icon as a lingering tray "ghost" (field-reported). Delayed so
    the /update/install response reaches the browser first; the installer then replaces the
    now-unlocked files and relaunches us with --after-update. No-op when there's no tray
    (running from source / headless: no icon to orphan, installer's kill is fine)."""
    hook = SHUTDOWN_HOOK
    if not hook:
        return
    import threading

    def _later():
        import time
        time.sleep(2.5)          # response flushed + installer has a head start
        try:
            hook()
        except Exception:  # noqa: BLE001
            os._exit(0)
    threading.Thread(target=_later, daemon=True).start()


@app.route("/update/install", methods=["POST"])
def update_install():
    """One-click self-update, packaged builds only: download the latest release's
    Setup exe from the project's GitHub (the only source this will touch), verify
    its size against the API's answer, and launch it silently with /RELAUNCH=1 —
    the installer ends this process itself, installs, and restarts the app."""
    import re as _re
    if not getattr(sys, "frozen", False):
        return jsonify({"ok": False, "response": "Self-update only applies to the installed app — "
                        "you're running from source (use git pull)."}), 400
    api_url = (CLIENT_CONFIG.get("urls") or {}).get("releases_api") or ""
    if not api_url or "REPLACE-ME" in api_url:
        return jsonify({"ok": False, "response": "No update source configured."}), 400
    try:
        import subprocess
        import tempfile
        import requests
        rel = requests.get(api_url, timeout=10,
                           headers={"Accept": "application/vnd.github+json"}).json()
        latest = (rel.get("tag_name") or "").lstrip("vV")

        def _t(v):
            return tuple(int(x) for x in (_re.findall(r"\d+", v)[:3] or ["0"]))

        if _t(latest) <= _t(APP_VERSION):
            return jsonify({"ok": False, "response": f"Already up to date (v{APP_VERSION})."})
        asset = next((a for a in rel.get("assets", [])
                      if a.get("name", "").lower().endswith(".exe")
                      and "setup" in a.get("name", "").lower()), None)
        if not asset:
            return jsonify({"ok": False, "response": "The latest release has no installer — "
                            "grab it from the download page instead."})
        dest = os.path.join(tempfile.gettempdir(), asset["name"])
        with requests.get(asset["browser_download_url"], stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(256 * 1024):
                    f.write(chunk)
        if os.path.getsize(dest) != asset.get("size"):
            return jsonify({"ok": False, "response": "Download came out the wrong size — "
                            "try again, or use the download page."})
        subprocess.Popen([dest, "/SILENT", "/RELAUNCH=1"], close_fds=True)
        # Drop our own tray icon cleanly before the installer force-kills us (no ghost icon).
        _graceful_self_exit_for_update()
        return jsonify({"ok": True, "version": latest})
    except Exception as e:  # noqa: BLE001 — fall back to the manual download page
        return jsonify({"ok": False, "response": f"Auto-update failed ({str(e)[:160]}) — "
                        "use the download page instead."})


@app.route("/champion/bundle", methods=["POST"])
def champion_bundle():
    """Wrap the user's current build as a CHAMPION CANDIDATE — the portable submission
    format. The hub never trusts a client's numbers: it re-scores the build with its own
    deterministic physics (same solver, its MODEL_VERSION), sweeps it, and only a build
    that survives gets promoted into the next data pack. Tampering with a bundle is
    therefore harmless — the hub recomputes everything that matters."""
    import datetime
    import first_principles as fp
    body = request.get_json(force=True) or {}
    return jsonify({"ok": True, "bundle": {
        "kind": "champion-candidate",
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
        "app_version": APP_VERSION, "model_version": fp.MODEL_VERSION,
        "db_name": DB_NAME, "db_version": DB_VERSION,
        "archetype": body.get("archetype"), "primary": body.get("primary"),
        "secondary": body.get("secondary"), "epic": body.get("epic"),
        "role": body.get("role"), "content": body.get("content"),
        "build": body.get("build"),
        "notes": (body.get("notes") or "")[:2000],
    }})


@app.route("/docs/<page>")
def doc_page(page):
    fname = _DOC_PAGES.get(page)
    if not fname:
        return "Not found", 404
    path = os.path.join(ROOT, fname)
    if not os.path.exists(path):
        return "Not found", 404
    with open(path, encoding="utf-8") as f:
        body = _md_to_html(f.read())
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>Hero Companion — {page.title()}</title>"
            "<style>body{max-width:820px;margin:2rem auto;padding:0 1rem;font:15px/1.6 'Segoe UI',sans-serif;"
            "background:#12161d;color:#dbe4f0}a{color:#6db3ff}h1,h2,h3{color:#fff}li{margin:.2rem 0 .2rem 1.2rem}"
            "hr{border:0;border-top:1px solid #333}</style></head><body>"
            f"{body}<hr><p><a href='/'>← back to Hero Companion</a></p></body></html>")


# ---------------------------------------------------------------------------
# Data endpoints
# ---------------------------------------------------------------------------
# ── NATURAL ROLES per archetype (user doctrine: "this game is first and foremost a role
# based game… If I play a Defender, I either buff, debuff, or heal"). Picking a role
# OUTSIDE this set (Damage-dealer Defender = "Offender", tankermind…) is a legitimate but
# DELIBERATE off-role choice — the UI warns and the user owns it. Never optimizer drift.
# WIKI-VERIFIED (Homecoming "Role Diversity", pasted 2026-07-02): the game's own five-role
# table — Tank / Melee Damage / Ranged Damage / Control / Support — mapped to the UI's role
# keys (Support ⇒ buffer/debuffer/healer; both Damage columns ⇒ damage). Epic ATs count for
# multiple roles, per the page. Sharp edges faithfully kept: officially Brute fills TANK
# (not damage), Corruptor fills RANGED DAMAGE (not support), Controller fills CONTROL.
    # NOTE: the official Role-Diversity table is about TEAM SLOTS (who fills the "tank" a
    # team needs), not whether an AT can deal damage. For a BUILD optimizer, damage is a
    # legit goal for any AT with full attack sets or damage pets — so Brute/Tanker/
    # Mastermind carry "damage" too (a damage Brute is the norm, not an off-role oddity;
    # field feedback 2026-07-06). Genuinely off-role stays flagged (a support Defender
    # built for "damage" = the Offender warning; a Controller as "tank"; etc.).
_AT_NATURAL_ROLES = {
    "Class_Defender":         ["buffer", "debuffer", "healer"],           # Support
    "Class_Mastermind":       ["buffer", "debuffer", "healer", "damage"],  # Support + pet damage
    "Class_Corruptor":        ["damage"],                                 # Ranged Damage
    "Class_Blaster":          ["damage"],                                 # Ranged Damage
    "Class_Sentinel":         ["damage"],                                 # Ranged Damage
    "Class_Scrapper":         ["damage"],                                 # Melee Damage
    "Class_Stalker":          ["damage"],                                 # Melee Damage
    "Class_Controller":       ["controller"],                             # Control
    "Class_Dominator":        ["controller", "damage"],                  # Control + real damage
    "Class_Brute":            ["tank", "damage"],                         # Tank + Fury damage
    "Class_Tanker":           ["tank", "damage"],                         # Tank + real damage
    "Class_Peacebringer":     ["tank", "damage"],                         # Tank + both Damage
    "Class_Warshade":         ["tank", "damage", "controller"],           # Tank + Ranged + Control
    "Class_Arachnos_Soldier": ["damage", "buffer", "debuffer", "healer"],  # Melee+Ranged + Support
    "Class_Arachnos_Widow":   ["damage", "controller"],                   # Melee+Ranged + Control
}


# ── ROLE EXTENSIONS by chosen powerset (user doctrine: "an MM with Empathy — not an ideal
# group healer, but can support their own summoned fighters… to play more than one role.
# But it is ALL role based choices"). A SUPPORT/CONTROL set carries role identity wherever
# it appears: Controller+Poison legitimately plays Debuffer, MM+Empathy legitimately plays
# Healer (a self-contained team). Extensions get an informative note, not a warning; the
# full off-role warning stays for roles supported by NEITHER the archetype NOR its sets
# (a blast set does NOT extend "damage" onto a support AT — the Offender warning survives).
_SET_ROLE_EXTENSIONS = {
    "Empathy":              ["healer", "buffer"],
    "Pain_Domination":      ["healer", "buffer"],
    "Nature_Affinity":      ["healer", "buffer"],
    "Electrical_Affinity":  ["healer", "buffer"],
    "Shock_Therapy":        ["healer", "buffer"],
    "Force_Field":          ["buffer"],
    "Sonic_Debuff":         ["buffer", "debuffer"],
    "Sonic_Resonance":      ["buffer", "debuffer"],
    "Cold_Domination":      ["buffer", "debuffer"],
    "Thermal_Radiation":    ["buffer", "healer", "debuffer"],
    "Kinetics":             ["buffer", "debuffer", "healer"],
    "Time_Manipulation":    ["buffer", "debuffer", "healer"],
    "Marine_Affinity":      ["buffer", "debuffer", "healer"],
    "Radiation_Emission":   ["debuffer", "healer"],
    "Dark_Miasma":          ["debuffer", "healer"],
    "Darkness_Affinity":    ["debuffer", "healer"],
    "Poison":               ["debuffer"],
    "Trick_Arrow":          ["debuffer"],
    "Traps":                ["debuffer"],
    "Storm_Summoning":      ["debuffer"],
}


def _set_role_extensions(*powerset_fulls):
    """Roles legitimized by the chosen powersets. Control primaries extend 'controller';
    support sets extend per the table (keyed by the set's base name, shared across ATs)."""
    out = []
    for ps in powerset_fulls:
        if not ps:
            continue
        base = ps.rsplit(".", 1)[-1]
        for r in _SET_ROLE_EXTENSIONS.get(base, []):
            if r not in out:
                out.append(r)
        # control sets ('Controller_Control.Plant_Control', 'Dominator_Control.…')
        if ps.split(".")[0].endswith("_Control") and "controller" not in out:
            out.append("controller")
    return out


def _off_role_notice(archetype, role, primary=None, secondary=None):
    """Role legitimacy in three tiers: AT-natural (silent) → set-EXTENDED (informative
    note — deliberate multi-role diversity) → true off-role (full warning). None when
    on-role or unknown. 'control'/'support' alias 'controller'/'buffer'."""
    nat = _AT_NATURAL_ROLES.get(archetype)
    r = {"control": "controller", "support": "buffer"}.get(role, role)
    # A declared generalist is never off-role on ANY archetype — "mixed" is the
    # absence of specialization, not a job the AT could be unsuited for.
    if r == "mixed":
        return None
    if not (nat and r) or r in nat:
        return None
    at = (ARCH_BY_NAME.get(archetype) or {}).get("display_name") or archetype
    labels = {"controller": "Controller / Lockdown", "debuffer": "Debuffer",
              "buffer": "Buffer / Support", "healer": "Healer",
              "damage": "Damage dealer", "tank": "Tank / Survivor"}
    ext = _set_role_extensions(primary, secondary)
    if r in ext:
        which = [ (ps or "").rsplit(".", 1)[-1].replace("_", " ")
                  for ps in (primary, secondary)
                  if ps and r in _set_role_extensions(ps) ]
        return (f"◆ ROLE EXTENSION: {labels.get(r, r)} isn't a {at}'s official role, but "
                f"your {' / '.join(which) or 'powerset'} choice makes it a legitimate "
                f"multi-role play — deliberate diversity, still a role-based choice.")
    return (f"⚠ OFF-ROLE: {labels.get(r, r)} is outside a {at}'s natural role "
            f"({' / '.join(labels.get(n, n) for n in nat)}) and none of your powersets "
            f"extend it. The build will be optimized for the role you picked — a "
            f"deliberate off-role character, not the archetype's standard job.")


# ── "HOW DO YOU PLAY" EXPLAINER (ideas.md 2026-07-08) ─────────────────────────────
# Every wizard choice gets a DETAILED, TAILORED explanation (specific to the chosen
# archetype + primary + secondary), plus a combined summary of what the choices make
# the solver actually chase. Deterministic by design: the text is derived from the
# SAME preset machinery the solve uses (ai_build.preset_targets / ROLE_PRESETS /
# CONTENT_PRESETS), so it can never drift from what the build really does.

def _ps_label(ps_full):
    return (ps_full or "").rsplit(".", 1)[-1].replace("_", " ")


def _explain_role(archetype, role, primary, secondary, at_name):
    if not role:                 # unanswered explains nothing (no-defaults ruling)
        return None
    spec = ai_build.ROLE_PRESETS.get(role) or {}
    label = spec.get("label") or role
    is_mm = archetype == "Class_Mastermind"
    support_sets = [_ps_label(ps) for ps in (primary, secondary)
                    if ps and _is_support_powerset(ps)]
    parts = []
    if role == "damage":
        if is_mm:
            parts.append(f"On a {at_name}, damage means your HENCHMEN: the planner "
                         "prices pet sets, squad size and uptime, and the pet aura "
                         "IOs — your personal attacks serve as proc carriers, not "
                         "the main event.")
        else:
            parts.append("Your attacks get full damage sets; the biggest AoE becomes "
                         "a deliberate proc bomb (procs + a Nucleolus for accuracy).")
        parts.append("−Resistance procs (Achilles' Heel class) are hunted into their "
                     "best hosts — they multiply the whole team's damage. Recharge is "
                     "pushed hard (at least +100%): cycling AoEs faster is the "
                     "biggest damage lever.")
    elif role in ("buffer", "support"):
        which = " / ".join(support_sets) or "your support set"
        parts.append(f"Your signature buffs from {which} always get working sets — "
                     "the build's job is keeping them strong and available. Recharge "
                     "(at least +90%) and recovery floors keep them cycling.")
    elif role == "healer":
        which = " / ".join(support_sets) or "your set"
        parts.append(f"Heals from {which} get heal sets and the regen/recovery floors "
                     "(+150% regen) that keep you casting through long fights.")
    elif role == "tank":
        parts.append(f"Every resistance is pushed toward your archetype's hard cap, "
                     f"with a +30% max-HP floor — a {at_name} built to hold the line. "
                     "Spare slots chase more resistance, not damage.")
    elif role in ("controller", "control"):
        parts.append("Control powers get control sets, and recharge (at least +100%) "
                     "is the lifeblood: perma-control IS the survival plan — a locked "
                     "spawn deals no damage.")
    elif role == "debuffer":
        which = " / ".join(support_sets) or "your debuff set"
        parts.append(f"Debuff powers from {which} are fully slotted for magnitude and "
                     "uptime — the goal is being FELT on the team. The Achilles' Heel "
                     "−res proc gets its anchor home, and recharge (+90%) keeps the "
                     "debuffs stacked.")
    elif role == "mixed":
        parts.append("A deliberate generalist — no single job is favored. The planner "
                     "chases the content's balanced baseline (solid defense and "
                     "resistance, moderate recharge and recovery) and judges every "
                     "slot by raw contribution instead of one role's lens. Pick this "
                     "when you genuinely play a bit of everything; a specialized role "
                     "will always beat it at that one specialty.")
    notice = _off_role_notice(archetype, role, primary, secondary)
    if notice:
        parts.append(notice)
    return {"label": label, "title": f"Role: {label}", "text": " ".join(parts)}


_FORM_EXPLAIN = {
    "human": ("Human form (no shapeshifting)",
              "You stay in your normal shape and use your full power list. The "
              "planner serves the human-form champion build: everything is "
              "enhanced around the powers you cast as yourself."),
    "dwarf": ("Dwarf form (the tanky shape)",
              "You plan to spend your fights shifted into the Dwarf — the "
              "durable, melee shape. The planner serves a champion built AROUND "
              "living in Dwarf: the form power is a permanent part of the build "
              "and the rest supports that way of playing."),
    "nova": ("Nova form (the blasting shape)",
             "You plan to spend your fights shifted into the Nova — the flying, "
             "pure-blasting shape. The planner serves a champion built AROUND "
             "living in Nova: the form power is a permanent part of the build "
             "and the rest supports that way of playing."),
    "triform": ("All three — tri-form (swap between shapes)",
                "The classic way to play: you swap shapes mid-fight — Nova to "
                "blast, Dwarf when things get rough, human for everything else. "
                "The planner serves a champion that carries BOTH form powers "
                "plus the human kit, with the slotting spread to make every "
                "shape worth being in. One honest note: the planner prices what "
                "each shape gives you, not the swapping itself — your rotation "
                "skill is yours."),
}


def _explain_form(form, archetype):
    """The Form question, in plain language (Joel: the user must see WHY a
    choice is even offered). Kheldians only; unanswered returns the WHY of the
    question itself — that explains the question, it invents no answer."""
    if archetype not in ("Class_Peacebringer", "Class_Warshade"):
        return None
    why = ("This question only exists for Peacebringers and Warshades: they can "
           "shapeshift into a tanky Dwarf or a blasting Nova, and a build that "
           "lives in one form wants different powers and slotting than one that "
           "stays human. Your answer picks which certified champion build the "
           "planner starts you from. Whichever you pick, you can still use every "
           "form in game — this only chooses what the BUILD is optimized around.")
    if not form or form not in _FORM_EXPLAIN:
        return {"label": None, "title": "Why the Form question?", "text": why}
    label, text = _FORM_EXPLAIN[form]
    return {"label": label, "title": f"Form: {label}",
            "text": text + " You can still use every form in game — this only "
                           "chooses what the build is optimized around."}


def _afk_champion_label(archetype, primary, secondary):
    """The certified AFK champion's sustain label for this exact context, if one
    exists (Joel's ruling, 2026-07-16: the tier a build DOES sustain prints on
    the certification label — a floor shortfall is never silent, a combo that
    covers the worst case through auto-fire sustain says exactly that)."""
    try:
        import learn as _learn
        champs = json.load(open(_learn.CHAMPIONS_PATH, encoding="utf-8"))
        entry = champs.get(f"{archetype}|{primary}|{secondary}|farm_afk") or {}
        return ((entry.get("certificate") or {}).get("afk_sustain") or {}).get("label")
    except Exception:  # noqa: BLE001 — explainer must never block the wizard
        return None


def _explain_content(archetype, content, primary, secondary, res_cap):
    if not content:              # unanswered explains nothing (no-defaults ruling)
        return None
    base = ai_build.CONTENT_PRESETS.get(content) or {}
    label = base.get("label") or content
    positional = ai_build.positional_build(primary, secondary)
    pos_set = next((_ps_label(ps) for ps in (primary, secondary)
                    if ps and (ps.split(".")[-1]).lower()
                    in ai_build.POSITIONAL_ARMOR_SETS), None)
    parts = []
    if content == "fire_farm":
        parts.append("Fire-farm enemies deal fire plus smashing/lethal damage only, "
                     "so the survival floor is non-negotiable even for a pure damage "
                     f"dealer: 45% Fire/S/L defense AND Fire/S/L resistance at your "
                     f"archetype's cap ({res_cap:.0f}%). You tank the spawn first, "
                     "then clear it.")
    elif content == "farm_afk":
        parts.append("AFK farming means the build fights alone while you are away "
                     "from the keyboard: 45% Fire defense, Fire resistance at your "
                     f"archetype's cap ({res_cap:.0f}%), and enough PASSIVE sustain "
                     "(regeneration, plus one self-heal on auto-fire) to out-heal "
                     "the whole spawn's incoming damage indefinitely.")
        champ_label = _afk_champion_label(archetype, primary, secondary)
        if champ_label:
            parts.append(champ_label)
    elif content == "farm_active":
        # v33 scenario ruling (Joel, 2026-07-16), stated to the user in plain
        # language: survival is a CONSTRAINT here, not a goal to maximise.
        parts.append("Active farming keeps you at the wheel — moving, clicking "
                     "heals, eating inspirations — so survival is treated as a "
                     "REQUIREMENT to satisfy, not a score to keep raising: 45% "
                     f"Fire defense and Fire resistance at the cap ({res_cap:.0f}%) "
                     "are hard requirements this build must meet, and once they are "
                     "met, extra survivability earns nothing more. From there, "
                     "damage throughput decides every remaining pick and slot — "
                     "because staying alive past what the requirements already "
                     "guarantee is your job at the keyboard, not the build's.")
    elif content == "itrial":
        parts.append("League and iTrial enemies run +3/+4 with heavy energy/negative "
                     "damage and defense-stripping spikes: the baseline is 35% typed "
                     "defense, 50% S/L + 40% E/N resistance, and +90% recharge so "
                     "your part of the league's output never idles.")
    elif content == "team":
        parts.append("On a steady team the group covers part of your survival — what "
                     "you bring is UPTIME. The baseline keeps 35% typed defense as a "
                     "cushion and pushes +80% recharge so your contribution cycles.")
    elif content == "av":
        parts.append("Hard single targets (EBs/AVs) mean long fights against mixed "
                     "damage: 35% typed defense plus an energy/negative cushion, and "
                     "+95% recharge to sustain your best single-target chain.")
    else:
        parts.append("Everyday content, solo or casual teams: a balanced 35% typed "
                     "defense, 50% S/L resistance, and +70% recharge — sturdy "
                     "everywhere without over-committing to one enemy type.")
    if positional and pos_set and content != "fire_farm":
        parts.append(f"Because {pos_set} is POSITIONAL armor, the planner chases "
                     "Melee/Ranged/AoE defense instead of typed — building typed "
                     "defense would fight your own armor's geometry.")
    return {"label": label, "title": f"Content: {label}", "text": " ".join(parts)}


def _explain_exposure(exposure, primary, secondary):
    # No invented answers (no-defaults ruling): unanswered = no explanation. The
    # old fallthrough narrated "flexible range" for a question nobody answered.
    if not exposure:
        return None
    positional = ai_build.positional_build(primary, secondary)
    if exposure == "front":
        text = ("Front line: you are hit in MELEE, so the defense vector adds a 45% "
                "Melee defense target — the soft cap against the hits you actually "
                "take up close.")
    elif exposure == "back":
        text = ("Backline: what reaches you is RANGED fire and stray AoE, so the "
                "defense vector adds 45% Ranged and AoE defense targets instead of "
                "melee — cap what actually hits you.")
    else:
        text = ("Flexible range: no positional lean — the content baseline stays "
                "balanced so you're covered wherever the fight drifts.")
    if positional and exposure != "flex":
        text += (" This stacks naturally with your positional armor — the same "
                 "Melee/Ranged/AoE bonuses serve both.")
    labels = {"front": "the front line (melee)", "back": "long range (backline)",
              "flex": "flexible range"}
    return {"label": labels.get(exposure, exposure or "flexible range"),
            "title": "You fight from: " + labels.get(exposure, "flexible range"),
            "text": text}


def _explain_travel(travel, content, archetype):
    # No invented answers (no-defaults ruling): an unanswered travel question has
    # no explanation — and never the old "P2W jet pack covers it" assertion.
    if not travel:
        return None
    innate = archetype in ("Class_Peacebringer", "Class_Warshade")
    texts = {
        "none": "No travel pool spent — a P2W jet pack covers the gaps, and the "
                "freed pool pick goes to the build.",
        "super_speed": "Super Speed shares the Speed pool with Hasten, which the "
                       "build wants anyway — so travel costs you no extra pool.",
        "fly": "Fly takes its own pool, but it's the most forgiving travel and "
               "iTrial-friendly: BAF and Lambda can only be ENTERED by Flight or "
               "Teleport.",
        "teleport": "Teleport takes its own pool; fastest point-to-point, and "
                    "iTrial-friendly: BAF and Lambda can only be ENTERED by Flight "
                    "or Teleport.",
        "super_jump": "Super Jump comes from the Leaping pool — which the build "
                      "often visits anyway for Combat Jumping (immobilize "
                      "protection + a cheap defense mule).",
    }
    text = texts.get(travel, texts["none"])
    if innate:
        text = ("Kheldians fly (and Warshades teleport) natively — no travel pool "
                "needed. " + text if travel != "none" else
                "Kheldians fly (and Warshades teleport) natively — no travel pool "
                "needed.")
    if content == "itrial" and travel in ("super_speed", "super_jump"):
        text += (" ⚠ For iTrials note BAF/Lambda entry requires Flight or Teleport — "
                 "keep a P2W jet pack on hand.")
    labels = {"none": "No extra travel power", "super_speed": "Super Speed",
              "fly": "Fly", "teleport": "Teleport", "super_jump": "Super Jump"}
    return {"label": labels.get(travel, travel), "title": f"Travel: {labels.get(travel, travel)}",
            "text": text}


def _summarize_intent(archetype, primary, secondary, role, content, exposure,
                      travel, res_cap, at_name):
    """The combined picture: what these choices make the solver actually chase.
    Asserts nothing until Role AND Content exist (empty text hides the panel) —
    the per-choice pop-ups fire independently for whatever WAS answered."""
    if not (role and content):
        return {"text": "", "targets": []}
    tgt = ai_build.preset_targets(content, role, res_cap=res_cap, exposure=exposure,
                                  primary=primary, secondary=secondary) or {}
    targets = tgt.get("targets") or {}
    items = []
    dfs = targets.get("defense") or {}
    if dfs:
        items.append("Defense targets: " + ", ".join(
            f"{t} {v:.0f}%" for t, v in sorted(dfs.items(), key=lambda kv: -kv[1])))
    rss = targets.get("resistance") or {}
    if rss:
        items.append("Resistance targets: " + ", ".join(
            f"{t} {v:.0f}%" for t, v in sorted(rss.items(), key=lambda kv: -kv[1])))
    for fld, name in (("recharge", "Recharge"), ("recovery", "Recovery"),
                      ("regen", "Regeneration"), ("max_hp", "Max HP"),
                      ("tohit", "ToHit")):
        v = targets.get(fld)
        if v:
            items.append(f"{name} +{v * 100:.0f}%" if fld == "max_hp"
                         else f"{name} +{v:.0f}%")
    spec = ai_build.ROLE_PRESETS.get(role) or {}
    pf = tgt.get("perk_focus") or spec.get("perk_focus")
    if pf:
        items.append(f"Spare slots chase: {pf}")
    # Unanswered questions are SAID to be unanswered — never asserted (the
    # travel-carryover field report caught the summary claiming "no extra travel
    # power" for a question nobody had answered yet).
    exp_part = (f"fighting from {_explain_exposure(exposure, primary, secondary)['label']}"
                if exposure else "fighting range not chosen yet")
    trav_d = _explain_travel(travel, content, archetype)
    trav_part = (f"traveling by {trav_d['label'].lower()}" if trav_d
                 else "travel not chosen yet")
    lead = (f"A {at_name} — {_ps_label(primary)} / {_ps_label(secondary)} — built as "
            f"{spec.get('label') or role} for "
            f"{(ai_build.CONTENT_PRESETS.get(content) or {}).get('label') or content}, "
            f"{exp_part}, {trav_part}.")
    return {"text": lead, "targets": items}


@app.route("/build/explain_intent", methods=["POST"])
def explain_intent():
    """Tailored plain-language explanations for the wizard's 'How do you play?'
    choices + a combined summary of what they make the solver chase. Deterministic:
    derived from the same presets the solve itself uses."""
    body = request.get_json(force=True, silent=True) or {}
    archetype = body.get("archetype")
    primary, secondary = body.get("primary"), body.get("secondary")
    # No server-side inventions either (no-defaults ruling): EVERY unanswered
    # question explains nothing — including role/content, whose old "damage"/
    # "general" fallbacks leaned on the client's whole-gate (the release-gate
    # bug: Role and Fight-from sit before Mostly-in in the wizard flow, so
    # gating all explainers on content silenced their pop-ups at pick time).
    role = body.get("role") or None
    content = body.get("content") or None
    exposure = body.get("exposure") or None
    travel = body.get("travel") or None
    form = body.get("form") or None
    at = ARCH_BY_NAME.get(archetype) or {}
    at_name = at.get("display_name") or (archetype or "?").replace("Class_", "")
    res_cap = round((at.get("res_cap") or 0.75) * 100, 1)
    try:
        return jsonify({
            "ok": True,
            "role": _explain_role(archetype, role, primary, secondary, at_name),
            "content": _explain_content(archetype, content, primary, secondary,
                                        res_cap),
            "exposure": _explain_exposure(exposure, primary, secondary),
            "travel": _explain_travel(travel, content, archetype),
            "form": _explain_form(form, archetype),
            "summary": _summarize_intent(archetype, primary, secondary, role,
                                         content, exposure, travel, res_cap,
                                         at_name),
        })
    except Exception as e:  # noqa: BLE001 — explainer must never block the wizard
        return jsonify({"ok": False, "error": str(e)})


@app.route("/archetypes")
def get_archetypes():
    return jsonify({
        "version": ARCHETYPES.get("version"),
        "issue": ARCHETYPES.get("issue"),
        "archetypes": [
            {"name": a["name"], "display_name": a["display_name"],
             "hitpoints": a["hitpoints"], "res_cap": a["res_cap"],
             "recharge_cap": a["recharge_cap"], "damage_cap": a["damage_cap"],
             "primary_group": a["primary_group"],
             "secondary_group": a["secondary_group"],
             "natural_roles": _AT_NATURAL_ROLES.get(a["name"], [])}
            for a in PLAYABLE
        ],
        "set_role_extensions": _SET_ROLE_EXTENSIONS,
    })


@app.route("/powersets/<archetype>")
def get_powersets(archetype):
    by_at = POWERSETS["by_archetype"].get(archetype)
    if by_at is None:
        # tolerate display name
        match = next((a["name"] for a in PLAYABLE
                      if a["display_name"].lower() == archetype.lower()), None)
        by_at = POWERSETS["by_archetype"].get(match, {}) if match else {}
    return jsonify({
        "archetype": archetype,
        "primary": by_at.get("primary", []),
        "secondary": by_at.get("secondary", []),
        "epic": by_at.get("epic", []),
        "pools": POWERSETS.get("pools", []),
    })


def _powers_for(powerset_full_name):
    powers = POWERS.get(powerset_full_name, [])
    # Attach the resolved category objects for convenience
    out = []
    for p in powers:
        rec = dict(p)
        rec["accepted_set_categories_detail"] = [
            {"id": cid, "name": CAT_BY_ID.get(cid, {}).get("name", str(cid)),
             "short": CAT_BY_ID.get(cid, {}).get("short", str(cid))}
            for cid in p.get("accepted_set_category_ids", [])
        ]
        rec["icon"] = _power_icon_url(p.get("full_name"))   # in-game power icon (card art)
        out.append(rec)
    return out


@app.route("/powers/<path:powerset_full_name>")
def get_powers(powerset_full_name):
    # Supports both "/powers/<full_name>" and "/powers/<archetype>/<powerset>"
    powers = _powers_for(powerset_full_name)
    if not powers and "/" in powerset_full_name:
        # archetype/powerset form -> join with "."
        joined = powerset_full_name.replace("/", ".")
        powers = _powers_for(joined)
    return jsonify({"powerset": powerset_full_name, "powers": powers})


# In-game incarnate art ships as one FAMILY icon per rarity ring:
# Incarnate_{Slot}_{FamilyFirstWord}_{Common|Uncommon|Rare|VeryRare}.png. The ability's
# NAME encodes its tier (Boost < Core/Radial < Partial/Total < Paragon/Final/Epiphany/
# Embodiment/Flawless/Superior), so the icon resolves from name alone.
try:
    _INC_ICON_FILES = {f[:-4].lower(): f[:-4]
                       for f in os.listdir(os.path.join(STATIC_DIR, "icons", "powers"))
                       if f.startswith("Incarnate_")}
except Exception:  # noqa: BLE001
    _INC_ICON_FILES = {}


def _incarnate_icon(full_name, display_name):
    parts = (full_name or "").split(".")
    if len(parts) < 2 or not display_name:
        return None
    slot = parts[1]
    words = display_name.split(" ")
    d = display_name.lower()
    if any(m in d for m in ("paragon", "final", "epiphany", "embodiment", "flawless", "superior")):
        rar = "VeryRare"
    elif "partial" in d or "total" in d:
        rar = "Rare"
    elif "core" in d or "radial" in d:
        rar = "Uncommon"
    else:
        rar = "Common"
    # Family token variants cover the art's naming quirks: two-word families keep the
    # SECOND word (Storm Elementals, Polar Lights, Robotic Drones), some pluralize
    # (Phantom→Phantoms), some differ only in case (Warworks→WarWorks).
    fams = [words[0], words[0] + "s"] + (words[1:2])
    for fam in fams:
        for r in (rar, "VeryRare", "Common"):
            hit = _INC_ICON_FILES.get(f"incarnate_{slot}_{fam}_{r}".lower())
            if hit:
                return "/static/icons/powers/" + hit + ".png"
    return _power_icon_url(full_name)    # a few (Mighty Judgement…) only exist in the old map


@app.route("/incarnates")
def get_incarnates():
    """The SIX live incarnate slots. Genesis (and later Omega-tier slots) were DESIGNED
    but never released — the Mids DB carries them as dormant data (37 choices, zero
    effects), and showing them confused players (user report 2026-07-02). Filtered here."""
    # v34 item 6 — THE HONESTY CLAUSE (Joel's gate: "no silent dead picks in any
    # picker surface the release touches"). `modeled` says whether OUR MATH
    # prices this choice, computed from the engine's own source of truth
    # (INCARNATE_FX — exactly what _incarnate_totals reads), never a hand-list.
    # Measured 2026-07-16: 357 of the 468 live-picker choices carry ZERO effect
    # records, so picking them moves no number — Lore (pets) and Interface
    # (attack procs) are 100% unmodeled, Judgement 52/54 (nukes), and Destiny's
    # Clarion (mez protection). They are not broken, they are UNPRICED: their
    # effect KINDS aren't in the incarnate model's vocabulary yet. The picker
    # now says so instead of pretending. Extraction of the real records is the
    # standing data-completeness work order; pricing follows per surface.
    live = dict(INCARNATES)
    live["slots"] = [dict(s, choices=[dict(ch, icon=_incarnate_icon(ch.get("full_name"),
                                                                    ch.get("display_name")),
                                           modeled=bool(INCARNATE_FX.get(ch.get("full_name"))))
                                      for ch in (s.get("choices") or [])])
                     for s in INCARNATES.get("slots", [])
                     if (s.get("slot") or s.get("name") or "") != "Genesis"]
    return jsonify(live)


@app.route("/sets/<category>")
def get_sets(category):
    """Return all enhancement sets in a category (by id, short name, or name)."""
    cat = None
    if category.isdigit():
        cat = int(category)
    elif category.lower() in CAT_BY_SHORT:
        cat = CAT_BY_SHORT[category.lower()]["id"]
    elif category.lower() in CAT_BY_NAME:
        cat = CAT_BY_NAME[category.lower()]["id"]
    if cat is None:
        return jsonify({"category": category, "sets": [], "error": "unknown category"}), 404
    sets = SETS_BY_CATEGORY.get(cat, [])
    return jsonify({
        "category": category,
        "category_id": cat,
        "category_name": CAT_BY_ID.get(cat, {}).get("name", str(cat)),
        "sets": sets,
    })


# ── Manual slotting (#7): single enhancements — common crafted IOs, Hamidon/
# Titan/Hydra Origins, D-Syncs — a power can host by hand. The game's rule: a
# piece may be slotted when the power accepts at least one enhancement type the
# piece boosts (aspects the power can't use simply do nothing), and identical
# copies stack freely. The tables translate the pieces' aspect vocabulary into
# the powers' accepted-enhancement-type vocabulary.
_ASPECT_ACCEPTS = {
    "accuracy": ("accuracy",), "damage": ("damage increase",),
    "rechargetime": ("recharge reduction",),
    "endurancediscount": ("endurance reduction",),
    "endurance": ("endurance modification",),
    "recovery": ("endurance modification",),
    "heal": ("healing",), "absorb": ("healing",), "hitpoints": ("healing",),
    "regeneration": ("healing",),
    "range": ("range",), "slow": ("slow",), "interrupt": ("activation decrease",),
    "speedflying": ("flight speed",), "speedrunning": ("run speed",),
    "speedjumping": ("jumping",), "jumpheight": ("jumping",),
}
_MEZ_ACCEPTS = ("hold duration", "immobilisation duration", "disorient duration",
                "confuse duration", "fear duration", "sleep duration",
                "taunt duration", "knockback distance", "intangibility duration")
# Common IOs are single-purpose: the display name IS the accepted type, bar two.
_COMMON_ACCEPTS = {"threat duration": "taunt duration",
                   "interrupt reduction": "activation decrease"}
_SPECIAL_FAMILY = (("hamidon_", "Hamidon Origin"), ("titan_", "Titan Origin"),
                   ("hydra_", "Hydra Origin"), ("dsync_", "D-Sync"))


def _special_accepts(uid, enhances):
    """Accepted-enhancement-types that admit a multi-aspect special IO. The
    Defense/ToHit aspects mean buff OR debuff depending on the piece (the uid
    carries the marker: Cytoskeleton is Buff_, Enzyme is DeBuff_); a Threat
    piece's Mez aspect is taunt only, any other Mez piece covers the whole
    mez family (the game lets Endoplasm enhance whatever mez the power does)."""
    u = (uid or "").lower()
    debuff = "debuff" in u
    out = set()
    for a in enhances or []:
        al = a.lower()
        if al == "defense":
            out.add("defense debuff" if debuff else "defense buff")
        elif al == "tohit":
            out.add("to hit debuff" if debuff else "to hit buff")
        elif al == "mez":
            out.update(("taunt duration",) if "threat" in u else _MEZ_ACCEPTS)
        else:
            out.update(_ASPECT_ACCEPTS.get(al, ()))
    return out


@app.route("/sets/for-power", methods=["POST"])
def sets_for_power():
    """Given a power's accepted category ids, return ONLY the matching sets —
    plus the single enhancements (common IOs, HOs/D-Syncs) the power accepts.
    This is the slot-enforcement endpoint used by the UI."""
    body = request.get_json(force=True) or {}
    cat_ids = body.get("accepted_set_category_ids", [])
    result = []
    seen = set()
    for cid in cat_ids:
        for s in SETS_BY_CATEGORY.get(cid, []):
            if s["uid"] in seen:
                continue
            seen.add(s["uid"])
            result.append(s)
    result.sort(key=lambda s: (s["category"], s["name"]))
    rec = POWER_BY_FULL.get(body.get("full_name") or "") or {}
    ptypes = {t.lower() for t in rec.get("accepted_enhancement_types") or []}
    commons, specials = [], []
    for c in COMMON_IOS["common_ios"]:
        n = c["name"].lower()
        if _COMMON_ACCEPTS.get(n, n) in ptypes:
            commons.append({"uid": c["uid"], "name": c["name"],
                            "enhances": c["enhances"],
                            "image": c.get("image") or ""})
    for c in COMMON_IOS.get("special_ios", []):
        if _special_accepts(c["uid"], c["enhances"]) & ptypes:
            u = c["uid"].lower()
            fam = next((f for pre, f in _SPECIAL_FAMILY if u.startswith(pre)),
                       "Special")
            specials.append({"uid": c["uid"], "name": c["name"], "family": fam,
                             "enhances": c["enhances"],
                             "image": c.get("image") or ""})
    return jsonify({"accepted_set_category_ids": cat_ids,
                    "set_count": len(result), "sets": result,
                    "commons": commons, "specials": specials})


# ── IO detail card + slotted-set progress (feature pair, display-only) ──────
# data/set_details.json = AUTHENTIC in-game text extracted from the client bins
# (tools/extract_set_details.py): piece titles, help TEMPLATES with
# {Boost.Attrib.X.Scale} placeholders, attuned wording, rosters, tier text.
try:
    SET_DETAILS = _load("set_details.json")
except Exception:  # noqa: BLE001 — feature degrades gracefully without the file
    SET_DETAILS = {}
_SD_META = SET_DETAILS.get("_meta") or {}
_SD_ALIASES = {k: tuple(v) for k, v in (_SD_META.get("attrib_aliases") or {}).items()}
_SD_PLACEHOLDER = re.compile(r"\{Boost\.Attrib\.([A-Za-z_]+)\.Scale\}")
# set uid per piece uid (for pieces arriving without their set context)
_SET_UID_BY_PIECE = {p["piece_uid"]: uid for uid, rec in SET_DETAILS.items()
                     if uid != "_meta" for p in rec.get("pieces", [])}


def _render_enh_help(template, piece_uid, io_level, boost, attuned, archetype):
    """Substitute the game's {Boost.Attrib.X.Scale} placeholders with the
    piece's level-scaled values — engine._scaled_boosts IS the math, so the
    card always agrees with the totals. Unmatched placeholders render as '?'
    (the extractor's coverage gate makes that unreachable for shipped data)."""
    ctx = _stat_ctx(archetype or "Class_Blaster")
    slot = {"piece_uid": piece_uid, "io_level": io_level,
            "boost": boost, "attuned": attuned}
    vals = defaultdict(float)
    for asp, v in engine._scaled_boosts(slot, ctx):
        vals[asp] += v

    def _sub(m):
        attrib = m.group(1)
        for cand in (attrib,) + _SD_ALIASES.get(attrib, ()):
            if cand in vals:
                return f"{round(vals[cand] * 100.0, 1):g}"
        low = {k.lower(): k for k in vals}
        if attrib.lower() in low:
            return f"{round(vals[low[attrib.lower()]] * 100.0, 1):g}"
        return "?"
    return _SD_PLACEHOLDER.sub(_sub, template or "")


def _tier_values(set_rec, pieces_required, archetype):
    """This exact tier's bonus values (PvE), formatted with magnitudes."""
    hp_ctx = _hp_bonus_ctx(archetype)
    out = []
    for b in set_rec.get("bonuses", []):
        if b.get("pieces_required") != pieces_required or b.get("pv_mode") == 2:
            continue
        for e in b.get("effects", []):
            et = e.get("effect")
            lab = _EFFECT_LABEL_MAP.get(et) or {"Endurance": "max endurance",
                                                "MezResist": "status resistance",
                                                "Heal": "heal strength"}.get(et, et)
            v = e.get("value") or 0
            if not lab or not v:
                continue
            if et == "HitPoints":
                v = engine.hp_bonus_fraction(v, hp_ctx)
            # unit conventions (verified against the data's own ranges):
            # Endurance stores flat max-end points (1.8 = +1.8%); MezResist
            # mixes duration-resist fractions (0.025) with whole-point
            # slow-resist values (10.0) — >1 means points, else fraction.
            if et == "Endurance" or (et == "MezResist" and abs(v) > 1):
                pct = round(v, 2)
            else:
                pct = round(v * 100.0, 2)
            pct = int(pct) if float(pct).is_integer() else pct
            dt = e.get("damage_type")
            dt = "" if dt in (None, "None", "Special") else f"{dt.lower()} "
            out.append(f"+{pct}% {dt}{lab}")
    # Compact per Joel's eyeball: a mez-resist bonus stores one identical value
    # per mez type ("+5% status resistance" ×6) — the label already aggregates,
    # so repeats add nothing. Dedupe preserving order; unequal values stay apart.
    seen = set()
    return [v for v in out if not (v in seen or seen.add(v))]


def _boostability(piece_uid, attuned):
    """Eligibility honesty for the booster preview (Joel's spec): say WHY a
    piece can't boost, never silently skip. Game rules: only regular crafted
    IOs (incl. purples) take boosters; attuned pieces (incl. ATOs/Winter,
    which only exist attuned) scale with your level instead; HO/D-Sync
    strength comes from their own level (50/53), no boosters."""
    # Attunement arrives two ways: the slot flag (imports) OR the piece's own
    # Attuned_* uid (solver-placed pieces carry no flag — found live when an
    # Attuned_Overwhelming_Force chit offered the stepper).
    if attuned or str(piece_uid or "").startswith("Attuned_"):
        return {"boostable": False, "reason":
                "Attuned enhancements can't take boosters — they scale with "
                "your level instead, and keep scaling down when you exemplar."}
    if str(piece_uid or "").startswith(_SPECIAL_PIECE_PREFIXES):
        return {"boostable": False, "reason":
                "Hamidon/Titan/Hydra Origins and D-Syncs can't take boosters "
                "— their strength comes from their own level (50/53)."}
    if piece_uid not in PIECE_BOOSTS:
        return {"boostable": False,
                "reason": "No enhancement values stored for this piece."}
    return {"boostable": True}


# ── Custom build-targets (Maelwys item 4, Joel's four rulings 2026-07-09) ──
@app.route("/targets/preset")
def targets_preset():
    """The RESOLVED numeric targets for a content×role×exposure pick — seeds
    the Customize-build-targets editor so the user edits from an informed
    default, never a blank guess (choice doctrine)."""
    content = request.args.get("content") or ""
    role = request.args.get("role") or ""
    at = ARCH_BY_NAME.get(request.args.get("archetype") or "")
    res_cap = round(at["res_cap"] * 100, 1) if at else engine.RESISTANCE_HARD_CAP
    pre = ai_build.preset_targets(content, role, res_cap=res_cap,
                                  exposure=request.args.get("exposure") or None,
                                  primary=request.args.get("primary") or None,
                                  secondary=request.args.get("secondary") or None)
    t = {k: v for k, v in pre["targets"].items() if k != "scenario"}
    return jsonify({"ok": True, "targets": t, "res_cap": res_cap,
                    "defense_types": engine.DEFENSE_TYPES,
                    "resistance_types": engine.RESISTANCE_TYPES})


def _target_presets_path():
    return os.path.join(_saves_dir(), "target_presets.json")


def _load_target_presets():
    try:
        with open(_target_presets_path(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001 — absent/corrupt file = empty library
        return {}


@app.route("/target_presets", methods=["GET", "POST"])
def target_presets():
    """The user's own named target presets (Joel's ruling 4: reusable, the
    user's explicit act — shipped presets remain the offered path; anything
    solved under these is derived, never champion-certified)."""
    presets = _load_target_presets()
    if request.method == "GET":
        return jsonify({"ok": True, "presets": presets})
    body = request.get_json(force=True) or {}
    name = (body.get("name") or "").strip()[:60]
    if not name:
        return jsonify({"ok": False, "error": "A preset needs a name."}), 400
    presets[name] = body.get("targets") or {}
    with open(_target_presets_path(), "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=1)
    return jsonify({"ok": True, "presets": presets})


@app.route("/target_presets/<name>", methods=["DELETE"])
def target_presets_delete(name):
    presets = _load_target_presets()
    presets.pop(name, None)
    with open(_target_presets_path(), "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=1)
    return jsonify({"ok": True, "presets": presets})


@app.route("/enhancement/detail", methods=["POST"])
def enhancement_detail():
    """Feature A+B: the full in-game detail card for one slotted piece, plus
    the parent set's roster/tier progress against the CURRENT build. Display
    only — reads the same data the totals run on, writes nothing."""
    body = request.get_json(force=True) or {}
    piece_uid = body.get("piece_uid") or ""
    archetype = body.get("archetype")
    io_level = body.get("io_level")
    boost = body.get("boost") or 0
    attuned = bool(body.get("attuned"))
    power_full = body.get("power_full_name")
    powers = body.get("powers") or []

    # The piece knows its set — prefer the extraction's own piece→set map over
    # the caller's set_uid, which arrives in legacy variants ("Shield Breaker"
    # with a space) that miss the SET_DETAILS key and silently downgraded real
    # set pieces to the minimal no-set card (found via Hack's franken view).
    set_uid = _SET_UID_BY_PIECE.get(piece_uid) or body.get("set_uid")
    sd = SET_DETAILS.get(set_uid) if set_uid else None
    set_rec = SET_BY_UID.get(set_uid) if set_uid else None
    piece_sd = next((p for p in (sd or {}).get("pieces", [])
                     if p["piece_uid"] == piece_uid), None)
    our_piece = next((pc for pc in (set_rec or {}).get("pieces", [])
                      if pc.get("uid") == piece_uid), None)

    # graceful minimal card for commons/HOs/unknown pieces (no set context)
    if not (sd and piece_sd):
        boosts = PIECE_BOOSTS.get(piece_uid) or []
        lines = [f"+{round(engine._scale_io(b['value'], b.get('schedule'), min(io_level or 50, 50), PIECE_REF_LEVEL.get(piece_uid) or 50, MULT_IO) * 100.0, 1):g}% {b['aspect']}"
                 for b in boosts]
        return jsonify({"ok": True, "piece": {
            "title": body.get("piece_name") or piece_uid,
            "description": " · ".join(lines) or "No stored detail for this piece.",
            "static": False,
            "boost_preview": _boostability(piece_uid, attuned)}, "set": None})

    desc = piece_sd["help_template"] if piece_sd.get("static") else \
        _render_enh_help(piece_sd["help_template"], piece_uid, io_level,
                         boost, attuned, archetype)
    piece = {
        "title": piece_sd["title"], "short": piece_sd.get("short") or "",
        "description": desc, "static": bool(piece_sd.get("static")),
        # composed (not a stored client string — the game builds this from
        # flags): our unique flags validate against the game's slotting rules.
        "unique_line": ("Unique: only one copy of this enhancement can be "
                        "slotted across your whole build."
                        if (our_piece or {}).get("unique") else None),
        "attuned_note": _SD_META.get("attuned_note") if attuned else None,
        "boost_preview": _boostability(piece_uid, attuned),
    }
    # roster status vs the current build (feature B)
    here = {(s or {}).get("piece_uid") for s in next(
        (p.get("slots") or [] for p in powers
         if p.get("full_name") == power_full), [])}
    elsewhere = {(s or {}).get("piece_uid")
                 for p in powers if p.get("full_name") != power_full
                 for s in (p.get("slots") or []) if s}
    roster = [{"piece_uid": p["piece_uid"], "title": p["title"],
               "short": p.get("short") or "",
               "status": ("slotted-here" if p["piece_uid"] in here else
                          "elsewhere" if p["piece_uid"] in elsewhere else
                          "missing")}
              for p in sd["pieces"]]
    n_here = sum(1 for r in roster if r["status"] == "slotted-here")
    tiers = []
    for t in sd.get("tiers", []):
        need = t["pieces_required"]
        # Honesty marker: 112 of 1,049 bonus records (103 PvE-side) carry EMPTY
        # effect lists in our data — the slow-resist/movement/range/mez-
        # duration/KB-protection families. Through this join that marks 143 of
        # 1,056 rendered tier rows (the client stores 52 duplicate same-piece-
        # count tier rows; 40 of them land on empty records). The game grants
        # these but the totals can't count them yet — the card says so instead
        # of rendering a bare name that looks like an oversight. Join is
        # unambiguous in shipped data: no tier has two pv_mode!=2 records at
        # one piece count, and no tier is PVP-only (counted 2026-07-09).
        b_rec = next((b for b in (set_rec or {}).get("bonuses", [])
                      if b.get("pieces_required") == need
                      and b.get("pv_mode") != 2), None)
        tiers.append({"pieces_required": need,
                      "bonus_title": t["bonus_title"],
                      "bonus_short": t.get("bonus_short") or "",
                      "values": _tier_values(set_rec or {}, need, archetype),
                      "unpriced": bool(b_rec is not None
                                       and not b_rec.get("effects")),
                      "attained": n_here >= need,
                      "next": n_here + 1 == need})
    return jsonify({"ok": True, "piece": piece, "set": {
        "uid": set_uid, "display": sd["display"],
        "category_label": sd.get("category_label"),
        "min_level": sd.get("min_level"), "max_level": sd.get("max_level"),
        "slotted_here": n_here, "roster": roster, "tiers": tiers}})


@app.route("/setbonuses/<path:setname>")
def get_setbonuses(setname):
    s = SET_BY_UID.get(setname) or SET_BY_NAME.get(setname.lower())
    if not s:
        return jsonify({"error": "set not found", "setname": setname}), 404
    return jsonify({
        "name": s["name"], "uid": s["uid"], "category": s["category"],
        "level_min": s["level_min"], "level_max": s["level_max"],
        "pieces": s["pieces"], "bonuses": s["bonuses"],
    })


# ── SLOTTING RATIONALE ──────────────────────────────────────────────────────
# Every power's slotting follows one of a few master patterns; without a label an
# expert reads a proc-bombed nuke or a global-mule Health as "spaghetti thrown at a
# wall" (Maelwys, 2026-07-06) when it's the intended high-end plan. _slot_plan makes
# the intent visible: it says WHY a power is slotted the way it is.
_GLOBAL_DESC = {
    "luck of the gambler": "+7.5% global recharge",
    "steadfast protection": "+3% defense (all)",
    "gladiators armor": "+3% defense (all)",
    "shield wall": "+5% resistance (all)",
    "reactive defenses": "scaling resist proc",
    "unbreakable guard": "+7.5% max HP",
    "preventive medicine": "absorb proc",
    "kismet": "+6% to-hit",
    "numina": "+regen / +recovery",
    "miracle": "+recovery",
    "regenerative tissue": "+regen",
    "performance shifter": "+recovery proc",
    "power transfer": "heal-on-use proc",
    "panacea": "+HP / +recovery proc",
    # 2026-07-20 (Joel's globals-list check, from the Nimbus Overwhelming Force
    # question): build-wide global uniques the list was MISSING — knockback
    # protection (Karma / Blessing of the Zephyr), slow resistance (Winter's Gift),
    # and the third +End proc (Theft of Essence, sibling of Performance Shifter /
    # Power Transfer). Verified game-first from set_details short-help. NOTE the
    # deliberate EXCLUSIONS: Overwhelming Force / Sudden Acceleration are "converts
    # knockback to KNOCKDOWN" — a PER-POWER effect, not a build-wide global.
    "karma": "knockback protection",
    "blessing of the zephyr": "knockback protection",
    "winters gift": "+slow resistance",
    "theft of essence": "+endurance proc",
}
# effect -> short label for naming the set bonuses a committed set actually earns
_EFFECT_LABEL = [
    ("RechargeTime", "recharge"), ("Defense", "defense"), ("Resistance", "resistance"),
    ("DamageBuff", "damage"), ("Recovery", "recovery"), ("Regeneration", "regen"),
    ("HitPoints", "max HP"), ("ToHit", "to-hit"),
]
_EFFECT_LABEL_MAP = dict(_EFFECT_LABEL)


def _piece_is_proc(s):
    return bool(s and (s.get("_proc")
                       or (s.get("piece_uid") and proc_pass._is_proc_uid(s["piece_uid"]))))


def _global_key(set_name):
    # apostrophe-insensitive: slot set names carry apostrophes ("Winter's Gift")
    # while set_details display names drop them ("Winters Gift") — normalize both
    # so the match works regardless of source (2026-07-20).
    n = (set_name or "").lower().replace("'", "")
    return next((k for k in _GLOBAL_DESC if k in n), None)


def _earned_bonus_kinds(set_name, n):
    """The distinct set-bonus KINDS a set earns at `n` pieces (bonuses stack cumulatively
    up to the piece count), ordered recharge/defense/resistance first — what an expert
    slots the set FOR. Names the kinds, not the exact percentages (the totals panel has
    those); the point here is intent."""
    s = SET_BY_NAME.get((set_name or "").lower())
    if not s:
        return []
    seen = set()
    for b in s.get("bonuses", []):
        if (b.get("pieces_required") or 99) > n or b.get("pv_mode") == 2:
            continue
        for e in b.get("effects", []):
            lab = _EFFECT_LABEL_MAP.get(e.get("effect"))
            if lab and (e.get("value") or 0) > 0:
                seen.add(lab)
    return [lab for _eff, lab in _EFFECT_LABEL if lab in seen][:3]


def _hp_bonus_ctx(archetype):
    """Minimal ctx for engine.hp_bonus_fraction — the HitPoints unit conversion."""
    at = ARCH_BY_NAME.get(archetype) or {}
    return {"modifier_tables": MODIFIER_TABLES, "at_column": AT_COLUMN.get(archetype),
            "at_base_hp": at.get("hitpoints")}


def _earned_bonus_values(set_name, n, archetype=None):
    """The top set bonuses a set ACTUALLY earns at `n` pieces, with magnitudes —
    '+7.5% recharge', '+1.88% melee defense'. Field report (Maelwys round 2): a card
    note must state what the slotting DOES, not a vague kind list."""
    s = SET_BY_NAME.get((set_name or "").lower())
    if not s:
        return []
    hp_ctx = _hp_bonus_ctx(archetype)
    agg = {}
    for b in s.get("bonuses", []):
        if (b.get("pieces_required") or 99) > n or b.get("pv_mode") == 2:
            continue
        for e in b.get("effects", []):
            lab = _EFFECT_LABEL_MAP.get(e.get("effect"))
            v = e.get("value") or 0
            if not lab or v <= 0:
                continue
            if e.get("effect") == "HitPoints":
                v = engine.hp_bonus_fraction(v, hp_ctx)   # HealSelf scale → fraction
            dt = e.get("damage_type")
            key = (lab, dt if dt not in (None, "None", "Special") else None)
            agg[key] = agg.get(key, 0.0) + v
    order = {lab: i for i, (_e, lab) in enumerate(_EFFECT_LABEL)}
    out = []
    for (lab, dt), v in sorted(agg.items(), key=lambda kv: (order.get(kv[0][0], 99),
                                                            kv[0][1] or "")):
        pct = round(v * 100.0, 2)
        pct = int(pct) if float(pct).is_integer() else pct
        out.append(f"+{pct}% {(dt.lower() + ' ') if dt else ''}{lab}")
    return out[:3]


# Special multi-aspect enhancements (Hamidon/Titan/Hydra Origins, D-Syncs): stack freely,
# earn no set bonuses — a card note must name them, never count them toward a "set".
_SPECIAL_PIECE_PREFIXES = ("Hamidon_", "Titan_", "Hydra_", "DSync_", "Dsync_")


def _res_job_note(power, all_powers):
    """Field report (Joel, Melt Armor): a base-slotted −res power's note said
    'budget went elsewhere' when the honest answer is WHERE the −res job went —
    the −res procs anchored in another host at better PPM uptime. Universal rule:
    any 1-slot power that carries an innate −res debuff or accepts a −res proc
    category names the power actually holding the proc(s)."""
    if not all_powers:
        return None
    rec = POWER_BY_FULL.get(power.get("full_name")) or {}
    innate_res = any((d.get("effect") == "Resistance")
                     for d in rec.get("debuff_effects") or [])
    res_cats = set((proc_pass._catalog().get("res_procs") or {}))
    could_host = bool(res_cats & set(rec.get("accepted_set_categories") or []))
    if not (innate_res or could_host):
        return None
    res_uids = {p["uid"] for procs in (proc_pass._catalog().get("res_procs") or {}).values()
                for p in procs if p.get("uid")}
    hosts = []
    for p in all_powers:
        if p is power:
            continue
        if any(s and s.get("piece_uid") in res_uids for s in p.get("slots") or []):
            nm = p.get("display_name") or (p.get("full_name") or "?").split(".")[-1]
            if nm not in hosts:
                hosts.append(nm)
    if not hosts:
        return None
    where = " and ".join(hosts[:2])
    job = "Its −resistance job" if innate_res else "The −resistance proc it could host"
    return (f" {job} is anchored in {where} — the −res procs roll there at better "
            f"uptime, so slots here would buy debuff uptime the optimizer prices "
            f"below your other sets.")


_CUSTOM_SCALAR_CLAMPS = {"recharge": 400, "recovery": 300, "regen": 1000,
                         "max_hp": 100, "tohit": 60}


def _apply_custom_targets(targets, custom, res_cap):
    """User-authored targets replace the preset's NUMERIC fields; the preset's
    non-numeric context (scenario for the accuracy term) survives. Clamps to
    game reality — defense 0-60, resistance 0-the AT's cap, scalars per table.
    Zero/absent = no target on that axis (dropping a target is a choice)."""
    out = {}
    if targets.get("scenario"):
        out["scenario"] = targets["scenario"]
    defs = {t: min(60.0, max(0.0, float(v)))
            for t, v in (custom.get("defense") or {}).items()
            if t in engine.DEFENSE_TYPES and _num(v) and float(v) > 0}
    if defs:
        out["defense"] = defs
    res = {t: min(float(res_cap), max(0.0, float(v)))
           for t, v in (custom.get("resistance") or {}).items()
           if t in engine.RESISTANCE_TYPES and _num(v) and float(v) > 0}
    if res:
        out["resistance"] = res
    for fld, cap in _CUSTOM_SCALAR_CLAMPS.items():
        v = custom.get(fld)
        if _num(v) and float(v) > 0:
            out[fld] = min(float(cap), max(0.0, float(v)))
    # v35: mark which axes the USER declared, so the solver can rank them senior
    # to every heuristic term (a declared ask is a promise — "shipped >= promised",
    # work order A; the measured end-proc repricing exposed that ordinary coverage
    # weights let side-value out-bid the last sliver of a declared axis).
    out["_declared"] = {"defense": sorted(defs), "resistance": sorted(res),
                        "scalars": [f for f in _CUSTOM_SCALAR_CLAMPS if f in out]}
    return out


def _num(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def _totals_kind(full_name, rec, power=None, ctx=None):
    """Classify a power for the totals checkbox's replacement UI (Joel's Σ-checkbox
    design: the game gives each power TYPE a different real on/off story, so the
    control has to match). Returns None for powers that need no control at all
    (plain attacks — checking/unchecking them changes nothing; they carry no
    self_effects). Three kinds:
      locked      — power_type Auto: no off-state in-game, always counted.
      toggle      — the checkbox's legitimate home (mule hosts, situational what-ifs).
      click_buff  — a timed self-buff/burst click (Hasten, Build Up, godmodes):
                    preview one at a time, default off, distinct from sustained totals.
    Game data can't cleanly split "cycling utility buff" (Hasten) from "attack-window
    burst" (Build Up) — both are Click powers with self-targeted buff effects and no
    stored flag distinguishes them — so both render as one click_buff kind pending a
    verified split.
    IMPORTANT (bug fixed 2026-07-09, Joel's live 5080 eyeball): classify by the power's
    REAL power_type only — never by "Inherent." full_name prefix. That prefix means
    "auto-granted, not a player pick" (why the card wall sorts these last), a totally
    different fact from "has no off-switch in-game". Sprint/Rest/Prestige Power Slide
    are all Inherent-namespaced AND real toggles (power_type 2) — locking them lied.
    """
    if not rec:
        return None
    pt = rec.get("power_type")
    if pt == 1:      # Auto
        return {"kind": "locked"}
    if pt == 2:      # Toggle
        return {"kind": "toggle"}
    if pt == 0 and (rec.get("self_effects") or rec.get("strength_effects")):
        # Click w/ a self-targeted buff — or a pure amplifier (Power Boost's
        # value is its strength_effects; its lone ToHit ride-along is minor).
        durs = [e.get("duration") or 0 for e in rec.get("self_effects") or []]
        durs += [s.get("duration") or 0 for s in rec.get("strength_effects") or []]
        out = {"kind": "click_buff", "base_recharge": rec.get("base_recharge") or 0,
               "buff_duration": max(durs) if durs else 0}
        # Amplifier chip (Power Boost class): its preview multiplies OTHER
        # checked powers' buffable Defense/ToHit — its own exclusivity group,
        # so Power Boost + Farsight can preview together (the Maelwys case)
        # while bursts stay one-at-a-time among themselves.
        amp = [s for s in rec.get("strength_effects") or []
               if s.get("modifies") in ("Defense", "ToHit")]
        if amp:
            out["amplifier"] = True
            out["amp_scale"] = max(s.get("scale") or 0 for s in amp)
        # Honest cycle math for the uptime note: the power's OWN slotted recharge
        # (post-ED) adds to global recharge in the game's formula. Without it,
        # Hasten's own recharge IOs vanish from the note and uptime reads ~45%
        # when the real figure is ~67% — a dishonest number is worse than none.
        if power and ctx:
            tot = 0.0
            for slot in power.get("slots") or []:
                if not slot or not slot.get("piece_uid"):
                    continue
                for asp, val in engine._scaled_boosts(slot, ctx):
                    if asp == "RechargeTime":
                        tot += val
            if tot:
                out["recharge_enh"] = round(engine.apply_ed_sched(
                    engine.ED_SCHEDULE.get("RechargeTime", 0), tot,
                    ctx["mult_ed"]), 4)
        return out
    return None       # plain Click attack — no self_effects, no control needed


def _global_host_phrase(power):
    """Copy fix (Maelwys round 3, Joel-approved direction): a RUNNING power that
    hosts globals is not a 'mule' — the tag read as 'this power is dead weight'
    on Fire Shield/Weave, which the engine counts and the player actually runs.
    Key on the power's real mechanic; Click powers keep honest mule wording."""
    rec = POWER_BY_FULL.get(power.get("full_name")) or {}
    pt = rec.get("power_type", power.get("power_type"))
    if pt == 1:
        return ("Hosts global uniques — this power is always on; "
                "its slots carry build-wide bonuses")
    if pt == 2:
        return ("Hosts global uniques — this toggle runs; "
                "its slots carry build-wide bonuses")
    return None


def _slot_plan(power, archetype=None, all_powers=None):
    """A one-line rationale for a power's slotting: proc bomb / proc hybrid / committed
    set / franken / global mules. Returns {"kind","text"} or None when there's nothing
    worth explaining. Field report (Maelwys round 2): the note must describe the ACTUAL
    slotting decision on the card — real piece counts ('4 of 6', never '4x ... a full
    set'), real bonus magnitudes, and no 'Proc bomb' badge on a 2-slot power."""
    slots = [s for s in (power.get("slots") or []) if s]
    if len(slots) == 1:
        # Field report (Joel's Stalker): 1-slot toggles showed NO note, so the card
        # couldn't defend itself. Be honest about what the single slot is doing.
        s = slots[0]
        gk = _global_key(s.get("set_name"))
        if gk:
            host = _global_host_phrase(power)
            if host:
                return {"kind": "global-host",
                        "text": f"{host}: {s.get('set_name')} "
                                f"({_GLOBAL_DESC[gk]}) — works from this single slot."}
            return {"kind": "global-mules",
                    "text": f"Global mule: {s.get('set_name')} ({_GLOBAL_DESC[gk]}) — "
                            "a build-wide unique that works from this single slot."}
        if not s.get("set_uid") and (power.get("accepted_set_category_ids")
                                     or power.get("accepted_set_categories")):
            return {"kind": "placeholder",
                    "text": f"Base slot only — a generic {s.get('piece_name') or 'IO'}. "
                            "The solve spent the 67-slot budget elsewhere; move slots "
                            "here if you want more from this power."
                            + (_res_job_note(power, all_powers) or "")}
        return None
    if len(slots) < 2:
        return None
    procs = [s for s in slots if _piece_is_proc(s)]
    nonproc = [s for s in slots if not _piece_is_proc(s)]
    hos = [s for s in nonproc
           if str(s.get("piece_uid") or "").startswith(_SPECIAL_PIECE_PREFIXES)]
    setters = [s for s in nonproc if s not in hos]
    hist = Counter(s.get("set_name") or "?" for s in setters if s.get("set_name"))
    # Only a REAL enhancement set (in the set index) earns bonuses — a stack of common IOs
    # is plain enhancement, never "a full set", so it must not masquerade as one.
    committed = sorted([(nm, n) for nm, n in hist.items()
                        if n >= 2 and SET_BY_NAME.get(nm.lower())], key=lambda x: -x[1])
    glob = [nm for nm in hist if hist[nm] == 1 and _global_key(nm)]

    def _glist(names):
        return ", ".join(f"{g} ({_GLOBAL_DESC[_global_key(g)]})" for g in names)

    def _res_note():
        return any(k in (s.get("set_name") or "").lower()
                   for s in procs for k in ("annihilation", "achilles",
                                            "fury of the gladiator",
                                            "touch of lady grey", "shield breaker"))

    ho_txt = (f"{len(hos)}x Acc/Dam Hamidon Origin{'s' if len(hos) > 1 else ''}"
              if hos else "")
    # 1) HO PROC HYBRID — an Acc/Dam Hamidon Origin core + procs (the Dominate pattern)
    if len(hos) >= 2 and len(procs) >= 2 and len(setters) <= 1:
        return {"kind": "ho-hybrid",
                "text": f"Proc hybrid: {ho_txt} as the accuracy/damage core + {len(procs)} "
                        "procs. A long-recharge power rolls each proc at high odds, and the "
                        "HOs add no recharge, so every proc keeps its full chance (the "
                        "Dominate master pattern). Identical HOs stack legally."}
    # 2) PROC BOMB — 4+ procs, (nearly) every other slot an HO or lone piece
    if len(procs) >= 4 and len(setters) <= 1:
        lead = (f"Proc bomb: {len(procs)} procs, one a -resistance proc that multiplies the "
                "whole team's damage spawn-wide." if _res_note()
                else f"Proc bomb: {len(procs)} damage procs.")
        acc = (" An Acc/Dam Hamidon Origin rides along so the procs actually hit."
               if hos else "")
        return {"kind": "proc-bomb",
                "text": lead + " On a big-radius power these out-damage a slotted set, so "
                        "set bonuses are given up here on purpose." + acc}
    # 3) A FEW PROCS — 2-3 procs is a rider, not a bomb (a 2-slot aura is not a 'Proc bomb')
    if len(procs) >= 2 and len(setters) <= 1:
        res = " (one a spawn-wide -resistance proc)" if _res_note() else ""
        return {"kind": "procs",
                "text": f"{len(procs)} damage procs{res}"
                        + (f" + {ho_txt} for accuracy" if hos else "")
                        + " — extra damage in the spare slots, no set bonus intended."}
    # 4) COMMITTED SET(S) / FRANKENSLOT — honest piece counts + the bonuses actually earned
    if committed:
        # A set's OWN proc piece IS a set piece (Joel's walk catch, 2026-07-20:
        # 6x Javelin Volley — whose 6th piece is the set's damage proc — read as
        # "5 + a foreign proc" = Frankenslot; it is a genuine FULL set, and the
        # game counts the proc toward the 6-piece bonus). Count same-set procs
        # into each committed set; only procs from OTHER sets are franken extras.
        def _set_procs(nm):
            return sum(1 for s in procs if (s.get("set_name") or "") == nm)
        parts = []
        for nm, n in committed:
            srec = SET_BY_NAME.get(nm.lower()) or {}
            total = len(srec.get("pieces") or []) or 6
            n_eff = n + _set_procs(nm)
            frame = (f"full {n_eff}-piece {nm}" if n_eff >= total
                     else f"{n_eff} of {total} {nm}")
            vals = _earned_bonus_values(nm, n_eff, archetype)
            parts.append(frame + (f" — earns {', '.join(vals)}" if vals else ""))
        tail = f". Plus global{'s' if len(glob) > 1 else ''}: {_glist(glob)}" if glob else ""
        if len(committed) > 1:
            return {"kind": "frankenslot",
                    "text": "Frankenslot: " + "; ".join(parts)
                            + " — stacked for their set bonuses" + tail + "."}
        # ONE committed set. "Full set" means COMPLETE (Joel, 2026-07-20: a 3-of-6
        # + procs slotting is a frankenstein, not a full set). A single COMPLETE
        # set (globals may ride along) = a clean Full set; a PARTIAL set mixed with
        # OTHER-set procs/HOs/pieces = a frankenslot; a clean partial (only globals
        # or empties beside it) = an honest "partial set" — never "Full set".
        nm0, n0 = committed[0]
        srec0 = SET_BY_NAME.get(nm0.lower()) or {}
        total0 = len(srec0.get("pieces") or []) or 6
        n0_eff = n0 + _set_procs(nm0)
        is_full = n0_eff >= total0
        # franken = OTHER-set procs/HOs or single pieces from OTHER sets mixed in.
        # Universal globals (LotG/Kismet/Steadfast — the `glob` list) ride any set
        # cleanly and do NOT make a partial a frankenstein, so exclude them.
        franken_extras = ((len(procs) - _set_procs(nm0)) + len(hos)
                          + max(0, len(setters) - n0 - len(glob)))
        if is_full:
            return {"kind": "committed", "text": parts[0] + tail + "."}
        if franken_extras > 0:
            return {"kind": "frankenslot",
                    "text": "Frankenslot: " + parts[0] + tail + "."}
        return {"kind": "partial-set", "text": parts[0] + tail + "."}
    # 5) GLOBAL MULES — a power carrying only build-wide unique globals.
    # Running powers (auto/toggle) get host wording, not mule wording.
    if glob and len(glob) == len(nonproc):
        host = _global_host_phrase(power)
        if host:
            return {"kind": "global-host",
                    "text": host + ": " + _glist(glob) + ". Each works from a "
                            "single slot — no set bonus intended."}
        return {"kind": "global-mules",
                "text": "Global mules: " + _glist(glob) + ". Each piece is a build-wide "
                        "unique that works from a single slot — no set bonus intended."}
    # 6) globals + filler
    if glob:
        return {"kind": "mixed", "text": "Globals + enhancement: " + _glist(glob) + "."}
    # 7) set-less power slotted with commons (Hasten's 2x Recharge) — say so plainly
    if (not power.get("accepted_set_category_ids")
            and not power.get("accepted_set_categories")
            and slots and all(not s.get("set_uid") for s in slots)):
        names = Counter((s.get("piece_name") or "IO") for s in slots)
        return {"kind": "placeholder",
                "text": "Generic slotting: "
                        + ", ".join(f"{n}x {nm}" if n > 1 else nm
                                    for nm, n in names.items())
                        + " — this power takes no enhancement sets, so plain IOs are "
                          "the right (and only) investment."}
    return None


def _under_invested(power):
    """A power that COULD earn set bonuses but doesn't: it accepts set categories, carries
    3+ enhancement slots, yet its slotting has no committed set, proc bomb, or global mule
    (_slot_plan is None) — i.e. it's filled with common IOs or a lone fragment. Powers that
    can't hold a set at all (Hasten, Sprint) are excluded, so this never false-flags them."""
    if (power.get("full_name") or "").startswith("Inherent"):
        return False
    filled = sum(1 for s in (power.get("slots") or [])
                 if s and (s.get("set_name") or s.get("piece_uid")))
    if filled < 3:
        return False
    rec = POWER_BY_FULL.get(power.get("full_name")) or {}
    if not rec.get("accepted_set_categories"):
        return False                      # can't hold a set — nothing a respec would change
    return _slot_plan(power) is None


# ---------------------------------------------------------------------------
# Build endpoints
# ---------------------------------------------------------------------------
_AT_SUFFIX_RE = re.compile(r"_(TankBrute|Tank|Brute|ScrapStalk|Scrapper|Stalker|Sentinel|Blaster|"
                           r"DefCorr|Defender|Corruptor|Controller|Dominator|Mastermind|Arachnos|"
                           r"Epic|Villain|Hero)$", re.IGNORECASE)


def _epic_prereq_count(tier):
    """How many OTHER powers from an epic/ancillary pool you must already have to take a
    power at this data-tier. The ONE authority for the rule (used by the validator, slot
    schedule, autopick gateway, and legality check). Corpus-validated — Guyver's 2,255
    builds + Maelwys's field report (2026-07-06): the first two (level 35) are free, the
    next two (level 38/41 — Physical Perfection is level 41) need ONE, and only the top
    power (level 44) needs TWO. (The power data carries no per-power prereq, so tier is
    our proxy; the corpus confirms this mapping across every ancillary pool.)"""
    return 0 if tier <= 1 else (1 if tier <= 3 else 2)


def _epic_prereq_errors(powers):
    """Epic/ancillary powers taken WITHOUT their tier prerequisites. Epic pools are a
    tier ladder: the first two powers are free, the third needs ONE other power from
    the pool, and the top tiers (the pets — Ice Elemental, Summon Spiderlings…) need
    TWO. Counted per power, so 'pet + one attack' is correctly flagged as one short."""
    by_ps = defaultdict(list)
    for p in (powers or []):
        rec = POWER_BY_FULL.get(p.get("full_name"))
        if rec and (rec.get("powerset_full_name") or "").startswith("Epic."):
            by_ps[rec["powerset_full_name"]].append(rec)
    out = []
    for ps, recs in by_ps.items():
        tiers = _pool_tiers(ps)
        setname = _AT_SUFFIX_RE.sub("", ps.split(".")[-1]).replace("_", " ")
        n_others = len(recs) - 1
        for r in recs:
            t = tiers.get(r.get("full_name"), 0)
            need = _epic_prereq_count(t)
            if n_others < need:
                short = need - n_others
                out.append(
                    f"{r.get('display_name')} can't be taken yet: the game requires "
                    f"{need} other {setname} power{'s' if need > 1 else ''} first — "
                    f"this build has {n_others}. Add {short} more lower-tier "
                    f"{setname} power{'s' if short > 1 else ''} to make it legal in-game.")
    return out


@app.route("/build/validate", methods=["POST"])
def build_validate():
    build = request.get_json(force=True) or {}
    res = engine.validate_build(build)
    prereq = _epic_prereq_errors(build.get("powers") or [])
    if prereq:
        res.setdefault("errors", []).extend(prereq)
    sched = _slot_schedule_errors(build.get("powers") or [])
    if sched:
        res.setdefault("errors", []).extend(sched)
    l1 = _l1_pick_errors(build.get("powers") or [], build.get("archetype"))
    if l1:
        res.setdefault("errors", []).extend(l1)
    # Origin-themed pools are one-per-build in game — flag a manual double-pick.
    _origin = sorted({(p.get("full_name") or "").rsplit(".", 1)[0]
                      for p in (build.get("powers") or [])
                      if (p.get("full_name") or "").rsplit(".", 1)[0] in _EXCLUSIVE_POOLS})
    if len(_origin) > 1:
        res.setdefault("errors", []).append(
            "Only ONE of Sorcery / Experimentation / Force of Will may be taken per build "
            f"(you have {', '.join(ps.split('.')[-1].replace('_', ' ') for ps in _origin)}).")
    # Common-build-mistakes coaching (soft, HC-accurate) — a distinct stream from hard errors/warnings.
    res["coaching"] = _build_coaching(build.get("archetype"), build.get("powers") or [])
    return jsonify(res)


@app.route("/build/calculate", methods=["POST"])
def build_calculate():
    build = request.get_json(force=True) or {}
    at = ARCH_BY_NAME.get(build.get("archetype"))
    res_cap = round(at["res_cap"] * 100, 1) if at else engine.RESISTANCE_HARD_CAP
    ctx = _stat_ctx(build.get("archetype"))
    # When incarnates are folded into the totals, an Alpha res/def boost needs each
    # armor toggle's OWN base res/def — enrich the (frontend) powers with the DB
    # fields _attach_base_resdef relies on, then attach it. Gated so a normal
    # recompute pays nothing extra.
    if build.get("include_incarnates"):
        for p in build.get("powers", []):
            rec = POWER_BY_FULL.get(p.get("full_name"))
            if not rec:
                continue
            for k in ("accepted_enhancement_types", "is_attack", "power_type", "base_recharge"):
                if not p.get(k):
                    p[k] = rec.get(k)
        _attach_base_resdef(build.get("powers", []), build.get("archetype"), ctx, res_cap)
    res = engine.calculate_build(build, SET_BONUSES, res_cap=res_cap, ctx=ctx)
    # AoE-88 FIX (Joel's Stalker eyeball, question 3 — 0.12.20 cut-blocker):
    # passive totals show suppressible defense UNSUPPRESSED (Hide alone is
    # +45.6 AoE def on the Rad/Dark champion → an "impossible" 77-88% AoE
    # reading), which is the Mids display convention but misleads as a fight
    # stat. The honest fix that never lies in EITHER direction: whenever the
    # out-of-combat view is showing, compute the in-combat number too and
    # attach it per defense row where they differ — the UI prints the fight
    # value right next to the headline one. No default flips, no toggle-state
    # to manage; the Σ in-combat view still works exactly as before. (The
    # scorer was never fooled — its survival math already ignores AoE.)
    if not build.get("suppression"):
        try:
            _sup = engine.calculate_build(dict(build, suppression=True),
                                          SET_BONUSES, res_cap=res_cap, ctx=ctx)
            for _t, _row in (res.get("defense") or {}).items():
                _sv = ((_sup.get("defense") or {}).get(_t) or {}).get("value")
                if _sv is not None and abs(_sv - _row.get("value", 0)) > 0.05:
                    _row["in_combat"] = _sv
        except Exception:  # noqa: BLE001 — the companion number is a nicety
            pass
    # Self-heal pick levels on every recompute: saved builds from older versions carry
    # naive assignments (both Poison powers at level 1) or none at all — re-seat them
    # and hand the corrected levels back so the build grid never shows an illegal order.
    pw = build.get("powers") or []
    real = [p for p in pw if not (p.get("full_name") or "").startswith("Inherent")]
    if real and (not all(p.get("pick_level") for p in real)
                 or not _schedule_feasible(real)
                 or not _l1_seating_ok(real, build.get("archetype"))):
        _assign_pick_levels(pw, build.get("archetype"))
        res["pick_levels"] = {p["full_name"]: p["pick_level"]
                              for p in pw if p.get("pick_level")}
    # Slotting rationale per power (the transparency chips), attached on EVERY recompute so a
    # RESUMED or IMPORTED build shows them too — not only a freshly solved one (field report:
    # chips missing after Resume, which read as the update being ignored).
    plans = {}
    under = []
    for p in pw:
        fn = p.get("full_name")
        if not fn:
            continue
        plan = _slot_plan(p, build.get("archetype"), pw)
        if plan:
            plans[fn] = plan
        elif _under_invested(p):
            rec = POWER_BY_FULL.get(fn) or {}
            under.append(rec.get("display_name") or fn.split(".")[-1].replace("_", " "))
    res["slot_plans"] = plans
    # Totals-checkbox kind per power (Σ-checkbox redesign): locked/toggle/click_buff,
    # attached every recompute so Resumed/Imported builds get it too.
    kinds = {}
    for p in pw:
        fn = p.get("full_name")
        if not fn:
            continue
        k = _totals_kind(fn, POWER_BY_FULL.get(fn), p, ctx)
        if k:
            kinds[fn] = k
    res["power_kinds"] = kinds
    # RESPEC HINT: powers that CAN hold a set and have the slots for one, but earn no set
    # bonus (just commons / a lone fragment). Purely factual — same signal the chips show —
    # so the tool can honestly say "a respec could put these slots to work" without judging.
    # Never fires on a well-slotted build (every real power is committed / proc / global).
    if len(under) >= 2:
        res["respec_hint"] = {"count": len(under), "powers": under[:6]}
    return jsonify(res)


def _attach_base_resdef(powers, archetype, ctx, res_cap):
    """For each armor RES/DEF toggle, compute its OWN base resistance/defense by type
    (no slots), as fractions, and stash on p['_base_rd'] — the solver credits the
    enhancement a res/def set gives the toggle so it sizes the set up to cap survival."""
    for p in powers:
        types = {t.lower() for t in (p.get("accepted_enhancement_types") or [])}
        is_res = p.get("power_type") == 2 and not p.get("is_attack") and "resist damage" in types
        is_def = (p.get("power_type") == 2 and not p.get("is_attack")
                  and "defense buff" in types and not is_res)
        if not (is_res or is_def):
            continue
        bt = engine.calculate_build({"archetype": archetype, "powers": [
            {"full_name": p["full_name"], "power_type": p["power_type"],
             "include_in_totals": True, "slots": []}]}, SET_BONUSES, res_cap=res_cap, ctx=ctx)
        kind, disp = ("Resistance", "resistance") if is_res else ("Defense", "defense")
        rd = {}
        for t, d in bt[disp].items():
            v = d.get("raw", d.get("value", 0)) / 100.0
            if v > 0.001:
                rd[(kind, t)] = v
        p["_base_rd"] = rd
        # The toggle's REAL drain (end/sec) — the solver's end-cost term (Maelwys
        # round 2): a set's endurance aspect relieves this drain, so an expensive
        # toggle (Weave 0.325/s, Maneuvers 0.39/s) is a strictly better set host
        # than a near-free one (Combat Jumping 0.065/s).
        rec = POWER_BY_FULL.get(p.get("full_name")) or {}
        ec, ap2 = rec.get("end_cost") or 0.0, rec.get("activate_period") or 0.0
        p["_end_drain"] = (ec / ap2) if (ec and ap2) else 0.0


def _add_typed_def_route(powers, targets, archetype=None):
    """A typed-def armor toggle (Scorpion Shield = S/L/E, Frozen/Charged Armor…) defines a SQUISHY
    build's REACHABLE defense route. The content presets chase POSITIONAL 45s a squishy often can't
    reach (lands ~20-26%), and a typed toggle contributes nothing to those — so the ILP left the
    shield at ONE slot: a patron unlock bought and never enhanced. Masters do the opposite: enhance
    the shield and soft-cap ITS types. So when a squishy's build carries a real def toggle, add its
    types as 45% targets (never lowering anything) — the ILP then enhances the shield (via
    _armor_def crediting) AND harvests typed set bonuses toward the reachable soft-cap. Native-armor
    ATs (incl. EATs) are exempt — their tuned positional routes stay untouched."""
    if archetype in _ARMORED_ATS or archetype in _EPIC_ATS:
        return
    for p in powers:
        for (kind, ty), v in (p.get("_base_rd") or {}).items():
            if kind == "Defense" and v >= 0.05:
                dd = targets.setdefault("defense", {})
                dd[ty] = max(dd.get(ty, 0), 45)


def _power_base_damage(rec, ctx):
    """Base (un-enhanced) damage of a power for this archetype — Σ|magnitude| over its
    damage_effects. Shared by the build-quality warning and the solver's damage weighting."""
    col = ctx.get("at_column")
    mt = ctx.get("modifier_tables") or {}
    base = 0.0
    for d in rec.get("damage_effects") or []:
        if not engine._pv_ok(d.get("pv_mode", 0), False):
            continue
        row = mt.get(d.get("modifier_table"))
        if row and col is not None and col < len(row):
            base += abs(engine._resolve_mag(d, row, col))
    return base


def _attach_base_dmg(powers, ctx):
    """Tag each attack with its base damage on p['_base_dmg'] so the solver allocates slots
    to the hardest hitters first (a premium attack gets a full damage set, not 2 mule slots)."""
    for p in powers:
        rec = POWER_BY_FULL.get(p.get("full_name"))
        if rec and (p.get("is_attack") or rec.get("is_attack")):
            p["_base_dmg"] = _power_base_damage(rec, ctx)


class _TargetGuard:
    """A2 (work order A, Joel's green light 2026-07-15): post-ILP target
    conservation, engine-verified per swap. The ILP meets the declared targets;
    no later pass may unmake them — proc_pass calls guard.ok(powers) after
    every tentative swap and reverts on False. A swap violates when a targeted
    axis ends below its target AND below its pre-swap value (spending SURPLUS
    above a met target stays legal — that headroom is the decay segment's
    territory, and procs are exactly what it should buy). Rule-of-five and
    every stacking subtlety are inherited from engine.calculate_build, so a
    swap that breaks a bonus the cap was already eating passes (measured: 4 of
    the 5 fire-farm swaps were free; only the Winter 6-piece break stole).
    Pinned origin: Spines/FA custom 45 fire def — ILP shipped 45.52, the
    unguarded bomb path shipped 40.52.

    TWO PROTECTION TIERS (measured on the Bots/Marine battery case, whose
    axes sit far below the preset asks): preset def/res targets are HARVEST
    PROXIES (ai_build's own words) — on a build that can't reach them, the
    bomb trade (set bonuses → damage) is the scorer-endorsed master pattern,
    so a SHORT preset axis may still pay for procs. `strict=True` (custom
    targets — the user's DECLARED ask, Joel's dominance rule) additionally
    forbids making any short user axis shorter. Met axes stay met under
    both tiers."""
    _SCALARS = (("recharge", "recharge"), ("recovery", "recovery"),
                ("regen", "regeneration"), ("max_hp", "max_hp"),
                ("tohit", "tohit"))
    _EPS = 0.05                       # percent points of float noise, not slack

    def __init__(self, archetype, targets, ctx, res_cap, strict=False):
        self.strict = strict
        self.archetype, self.ctx, self.res_cap = archetype, ctx, res_cap
        self.asks = []                # (engine kind, type-or-None, target pct)
        for t, v in (targets.get("defense") or {}).items():
            if isinstance(v, (int, float)) and v > 0:
                self.asks.append(("defense", t, float(v)))
        for t, v in (targets.get("resistance") or {}).items():
            if isinstance(v, (int, float)) and v > 0:
                self.asks.append(("resistance", t, float(v)))
        for fld, ekey in self._SCALARS:
            v = targets.get(fld)
            if isinstance(v, (int, float)) and v > 0:
                self.asks.append((ekey, None, float(v)))
        self.base = None

    def _vals(self, powers):
        tot = engine.calculate_build({"archetype": self.archetype,
                                      "powers": powers},
                                     SET_BONUSES, res_cap=self.res_cap,
                                     ctx=self.ctx)
        return [(((tot.get(kind) or {}).get(t) or {}).get("value", 0.0)
                 if t is not None else (tot.get(kind) or {}).get("value", 0.0))
                for kind, t, _tgt in self.asks]

    def snapshot(self, powers):
        if self.asks:
            self.base = self._vals(powers)

    def ok(self, powers):
        if not self.asks:
            return True
        if self.base is None:         # defensive: snapshot() not called yet
            self.base = self._vals(powers)
            return True
        vals = self._vals(powers)
        for (kind, t, tgt), old, new in zip(self.asks, self.base, vals):
            if new < tgt - self._EPS:
                if old >= tgt - self._EPS:
                    return False      # dropped a MET axis below its ask
                if self.strict and new < old - self._EPS:
                    return False      # made a short USER-DECLARED axis shorter
        self.base = vals              # accepted swap becomes the new baseline
        return True


def _assess_solve(archetype, powers_in, targets, tier, perk_focus, roles,
                  pvp, preserve, keep_layout, with_powers=False):
    """Run ONE solve and return the engine totals (for comparing routes) — or
    (totals, solved_powers) when with_powers, for the joint think-ahead loop. Mirrors
    /build/solve's core; returns None on any failure."""
    powers = []
    for p in powers_in:
        rec = POWER_BY_FULL.get(p.get("full_name"))
        if not rec:
            continue
        powers.append({"full_name": rec["full_name"], "display_name": rec["display_name"],
                       "powerset_full_name": rec["powerset_full_name"],
                       "accepted_set_category_ids": rec.get("accepted_set_category_ids", []),
                       "accepted_set_categories": rec.get("accepted_set_categories", []),
                       "power_type": rec.get("power_type"), "is_attack": rec.get("is_attack"),
                       "base_recharge": rec.get("base_recharge"),
                       "max_slot_count": rec.get("max_slot_count"),
                       "accepted_enhancement_types": rec.get("accepted_enhancement_types", []),
                       "_existing_slots": p.get("slots") or [],
                       "_earned": p.get("earned_slot_count")
                       or len([s for s in (p.get("slots") or []) if s]),
                       "_buff_priority": _is_support_powerset(rec["powerset_full_name"])})
    if not powers:
        return None
    ctx = _stat_ctx(archetype)
    at = ARCH_BY_NAME.get(archetype)
    res_cap = round(at["res_cap"] * 100, 1) if at else engine.RESISTANCE_HARD_CAP
    binit = {"archetype": archetype, "powers": [
        {"full_name": p["full_name"], "power_type": p["power_type"],
         "include_in_totals": p["power_type"] in (1, 2), "slots": []} for p in powers]}
    bt = engine.calculate_build(binit, SET_BONUSES, res_cap=res_cap, ctx=ctx)
    _endurance_recovery_floor(bt, targets)   # physics-derived +recovery vs this build's drain
    base = {}
    for t, d in bt["defense"].items():
        base[("Defense", t)] = d["value"] / 100.0
    for t, d in bt["resistance"].items():
        base[("Resistance", t)] = d["value"] / 100.0
    _attach_base_resdef(powers, archetype, ctx, res_cap)
    _add_typed_def_route(powers, targets, archetype)
    _attach_base_dmg(powers, ctx)
    try:
        sol = solver.solve_ilp(powers, targets, SETS_BY_CATEGORY, engine.PIECE_GLOBALS,
                               base, slot_cap=67 + len(powers), tier=tier,
                               perk_focus=perk_focus, roles=roles, pvp=pvp,
                               preserve=preserve, keep_layout=keep_layout, archetype=archetype,
                               **_at_solve_phys(archetype))
    except Exception:  # noqa: BLE001
        return None
    tot = engine.calculate_build({"archetype": archetype, "powers": sol["powers"], "pvp": pvp},
                                 SET_BONUSES, res_cap=res_cap, ctx=ctx)
    if with_powers:
        return tot, sol["powers"]
    return tot


# ── JOINT selection+slotting (Phase 3 v1) — the think-ahead loop ────────────────────────────
# The heuristic pipeline decides picks FIRST (priority rules), slots SECOND — which is why it
# needed a growing rulebook (Boxing cap, armor floors…) to make the two agree. This loop makes
# selection answer to solved OUTCOMES instead: propose a pick swap → SOLVE the whole slotting →
# score the finished build on the AT's PAYOFF (the exact metrics the benchmark judges) → keep the
# swap only if the finished build is better. No per-power rules: a power stays because the solved
# build with it beats the solved build without it.
def _payoff_of(archetype, solved_powers, ctx=None):
    ctx = ctx or _stat_ctx(archetype)
    ctx["power_by_full"] = POWER_BY_FULL
    at = ARCH_BY_NAME.get(archetype)
    res_cap = round(at["res_cap"] * 100, 1) if at else engine.RESISTANCE_HARD_CAP
    tot = engine.calculate_build({"archetype": archetype, "powers": solved_powers},
                                 SET_BONUSES, res_cap=res_cap, ctx=ctx)
    return role_output.payoff_metrics(archetype, solved_powers, ctx, tot)


def _static_value(rec, role, ctx):
    """Cheap pre-screen for swap candidates (which solves are worth paying for) — NOT the decider."""
    v = 0.0
    if rec.get("damage_effects"):
        v += _power_base_damage(rec, ctx) * (1.5 if engine.is_aoe(rec) else 1.0)
    v += role_output.power_control_output(rec, ctx) * (2.0 if role in ("controller", "control") else 0.5)
    v += 8.0 * sum(1 for d in rec.get("debuff_effects", []) if d.get("effect") == "Resistance")
    t, s, _ = role_output.power_heal_output(rec, ctx)
    v += 2.0 * t + s
    return v


def joint_refine(archetype, primary, secondary, role, content, powers_in,
                 rounds=3, tries_per_round=5, scorer="payoff"):
    """Hill-climb the POWER SELECTION by solved outcome. v1 scope: swaps within primary+secondary
    (pools/epic/travel keep the seed's choices). Returns (best_powers_solved, report).
    scorer: 'payoff' = the AT_PAYOFF map (hand-taught); 'first_principles' = the encounter model
    (pure game arithmetic — no targets, no AT map; roles/softcaps/perma are DERIVED)."""
    import first_principles as fp
    role = (role or ai_build.CONTENT_PRESETS.get(content or "", {}).get("default_role")
            or _AT_DEFAULT_ROLE.get(archetype, "damage"))
    # The AT's REAL res cap (yellowthief1's find): the hardcoded 75 undercut
    # tank-role/CAP-entry targets on high-cap ATs. Same fix as deep_optimize.
    pre = ai_build.preset_targets(
        content, role,
        res_cap=round(((ARCH_BY_NAME.get(archetype) or {}).get("res_cap") or 0.75) * 100, 1),
        archetype=archetype)
    targets, roles, perk = pre["targets"], pre["roles"], pre["perk_focus"]
    ctx = _stat_ctx(archetype)
    ctx["power_by_full"] = POWER_BY_FULL
    arch_row = ARCH_BY_NAME.get(archetype)

    def solve(pws):
        import copy as _c
        r = _assess_solve(archetype, _c.deepcopy(pws), _c.deepcopy(targets), "premium",
                          perk, roles, False, False, False, with_powers=True)
        return r if r else (None, None)

    def fp_score(solved_powers):
        res_cap = round(arch_row["res_cap"] * 100, 1) if arch_row else engine.RESISTANCE_HARD_CAP
        tot = engine.calculate_build({"archetype": archetype, "powers": solved_powers},
                                     SET_BONUSES, res_cap=res_cap, ctx=ctx)
        return fp.encounter_value(archetype, solved_powers, ctx, tot, scenario=content,
                                  arch_row=arch_row, role_output_mod=role_output)

    cur = list(powers_in)
    tot, solved = solve(cur)
    if not solved:
        return None, {"error": "seed solve failed"}
    baseline = _payoff_of(archetype, solved, ctx)
    if scorer == "first_principles":
        fp0 = fp_score(solved)
        baseline = dict(baseline, **fp0)
        best_score = fp0["contribution"]
    else:
        best_score = role_output.payoff_score(archetype, baseline, baseline)   # = len(payoff)+tie
    swaps_done = []
    ps_pair = (primary, secondary)
    for _ in range(rounds):
        picked = {p["full_name"] for p in cur}
        drops = [p for p in cur if (p.get("powerset_full_name") or "").startswith(ps_pair)
                 and POWER_BY_FULL.get(p["full_name"]) is not None]
        adds = [q for ps in ps_pair for q in (POWERS.get(ps) or [])
                if q["full_name"] not in picked and q.get("slottable")]
        # rank swap candidates by static value delta; try the most promising few with FULL solves
        cand = []
        for d in drops:
            dv = _static_value(POWER_BY_FULL[d["full_name"]], role, ctx)
            for a in adds:
                av = _static_value(a, role, ctx)
                if av > dv:
                    cand.append((av - dv, d, a))
        cand.sort(key=lambda x: -x[0])
        improved = False
        for _, d, a in cand[:tries_per_round]:
            trial = [p for p in cur if p["full_name"] != d["full_name"]]
            trial.append({"full_name": a["full_name"],
                          "pick_level": max(d.get("pick_level") or 1, a.get("level_available") or 1)})
            t_tot, t_solved = solve(trial)
            if not t_solved:
                continue
            if scorer == "first_principles":
                sc = fp_score(t_solved)["contribution"]
            else:
                sc = role_output.payoff_score(archetype, _payoff_of(archetype, t_solved, ctx), baseline)
            if sc > best_score * (1.002 if scorer == "first_principles" else 1.0) + 1e-3:
                cur, solved, best_score = trial, t_solved, sc
                swaps_done.append({"dropped": d["full_name"].split(".")[-1],
                                   "added": a["full_name"].split(".")[-1],
                                   "score": sc})
                improved = True
                break                      # re-rank from the new build
        if not improved:
            break
    final = _payoff_of(archetype, solved, ctx)
    if scorer == "first_principles":
        final = dict(final, **fp_score(solved))
    return solved, {"swaps": swaps_done, "score": best_score,
                    "baseline": baseline, "final": final}


def _pool_tiers(ps):
    """{full_name: tier index} for a Pool.*/Epic.* powerset, in data (tier) order."""
    return {p["full_name"]: i for i, p in enumerate(POWERS.get(ps) or [])}


# ── SLOT-SCHEDULE-AWARE PICK LEVELS (field report: a 5-slotted power "picked at 49") ──
# In game every enhancement slot is granted at a specific level and can only be placed
# in a power you already have — a respec follows the same ladder. So a level-49 pick can
# never hold more than 4 slots (its free one + the 3 granted at 50), the 47 and 49 picks
# together share the 6 slots granted at 48+50, and so on up the tail. Pick levels must
# therefore be assigned with the SLOTTING in mind: heavy powers early, 1-slot utility late.

def _sched_avail(p):
    return max(1, int(p.get("level_available")
                      or (POWER_BY_FULL.get(p.get("full_name"), {}) or {}).get("level_available") or 1))


def _sched_added(p):
    return max(0, len(p.get("slots") or [None]) - 1)


def _grants_from(level):
    """Total enhancement slots still granted at levels >= `level` (grant levels and
    pick levels never coincide on the Homecoming ladder, so >= is exact)."""
    return sum(v for g, v in leveling_schedule.SLOT_GRANTS.items() if g >= level)


def _tier_need(full_name):
    """Same-set powers required BEFORE this one (the Pool/Epic tier ladder rule)."""
    ps = (full_name or "").rsplit(".", 1)[0]
    if not ps.startswith(("Pool.", "Epic.")):
        return 0
    return _epic_prereq_count(_pool_tiers(ps).get(full_name, 0))


def _pick_order_legal(seq):
    """Every power in pick order satisfies availability + its set's tier ladder."""
    seen = defaultdict(int)
    for lv, p in seq:
        if _sched_avail(p) > lv:
            return False
        ps = (p.get("full_name") or "").rsplit(".", 1)[0]
        if seen[ps] < _tier_need(p.get("full_name")):
            return False
        seen[ps] += 1
    return True


def _schedule_feasible(real_powers):
    """True if the powers' existing pick_levels can actually receive their slots —
    for every pick level L, the slots added to powers picked at or after L must fit
    inside the slots the game still grants at levels >= L."""
    seq = sorted(real_powers, key=lambda p: int(p.get("pick_level") or 1))
    tail = 0
    for p in reversed(seq):
        tail += _sched_added(p)
        if tail > _grants_from(int(p.get("pick_level") or 1)):
            return False
    return True


def _set_first_two(ps):
    """A set's first two PICKABLE powers (the level-1 creation choice), by level then
    data order. level_available 0 = auto-granted set mechanics (Pack Mentality…),
    which are never picks."""
    seq = sorted([x for x in (POWERS.get(ps) or []) if x.get("level_available") != 0],
                 key=lambda x: (x.get("level_available") or 1))
    return [x["full_name"] for x in seq[:2]]


def _at_canon(archetype):
    """Canonical archetype key ("Class_Defender") — tolerant of display names
    ("Defender"), so the creation-pair rules never silently no-op on a mismatch."""
    if not archetype or archetype in POWERSETS["by_archetype"]:
        return archetype
    for k, rec in ARCH_BY_NAME.items():
        if rec.get("display_name") == archetype:
            return k
    return archetype


def _l1_creation_pair(powers, archetype):
    """The two powers that belong at level 1: in game, character creation asks for ONE
    of the SECONDARY's first two powers FIRST, then ONE of the primary's first two
    (field-verified by the user in the creator; the corpus confirms both are choices —
    2202/2211 master builds seat exactly primary+secondary at L1, with T2-at-1 common).
    Returns (secondary_pick, primary_pick) IN THAT ORDER — either may be None. VEATs
    are excluded (their two-phase career has its own walk)."""
    archetype = _at_canon(archetype)
    if not archetype or leveling_schedule.eat_type(archetype) == "veat":
        return None, None
    groups = POWERSETS["by_archetype"].get(archetype) or {}
    prims = {e["full_name"] for e in (groups.get("primary") or [])}
    secs = {e["full_name"] for e in (groups.get("secondary") or [])}
    by_full = {p.get("full_name"): p for p in powers}

    def _pick(setnames):
        for ps in {p.get("powerset_full_name") for p in powers}:
            if ps in setnames:
                for fn in _set_first_two(ps):        # prefer the T1 when both are in the build
                    if fn in by_full:
                        return by_full[fn]
        return None
    prim_pick = _pick(prims)
    sec_pick = _pick(secs)
    if sec_pick is prim_pick:
        sec_pick = None
    return sec_pick, prim_pick


def _l1_seating_ok(powers, archetype):
    """True when the powers' EXISTING pick levels put a legal creation pair at level 1
    (one primary + one secondary, each from its set's first two). Saved builds from
    older versions carry naive assignments (Alkaloid AND Envenom both at 1) — those
    must be re-seated, not respected."""
    archetype = _at_canon(archetype)
    if not archetype or leveling_schedule.eat_type(archetype) is not None:
        return True
    real = [p for p in powers if not (p.get("full_name") or "").startswith("Inherent")]
    if len(real) < 2:
        return True
    l1 = [p for p in real if int(p.get("pick_level") or 0) == 1]
    if len(l1) != 2:
        return False
    groups = POWERSETS["by_archetype"].get(archetype) or {}
    prims = {e["full_name"] for e in (groups.get("primary") or [])}
    secs = {e["full_name"] for e in (groups.get("secondary") or [])}
    kinds = set()
    for p in l1:
        ps = p.get("powerset_full_name")
        if p.get("full_name") not in _set_first_two(ps or ""):
            return False
        kinds.add("p" if ps in prims else ("s" if ps in secs else "?"))
    return kinds == {"p", "s"}


def _assign_pick_levels(powers, archetype=None):
    """Stamp pick_level onto every non-inherent power: the level-1 creation pair first
    (one primary + one secondary from each set's first two), then natural seating
    (earliest available first on the real pick ladder), then repaired by swapping heavy
    late picks with light early ones until the slot schedule is satisfiable. Mutates
    the power dicts. Returns True when the final assignment is fully feasible."""
    real = [p for p in powers if not (p.get("full_name") or "").startswith("Inherent")]
    for p in powers:
        if (p.get("full_name") or "").startswith("Inherent"):
            p["pick_level"] = 1
    if not real:
        return True
    ladder = list(leveling_schedule.POWER_PICK_LEVELS)
    seats, pinned = [], 0                            # [[level, power], ...] ascending
    l1a, l1b = _l1_creation_pair(real, archetype)
    for lp in (l1a, l1b):
        if lp is not None:
            seats.append([ladder[pinned], lp])       # the two level-1 seats
            pinned += 1
    seated = {id(p) for _, p in seats}
    order = sorted([p for p in real if id(p) not in seated],
                   key=_sched_avail)                 # stable → in-set tier order survives
    si = pinned
    for p in order:
        while si < len(ladder) and ladder[si] < _sched_avail(p):
            si += 1
        seats.append([ladder[si] if si < len(ladder) else min(49, _sched_avail(p)), p])
        si += 1

    def _excess():
        """Total slot overweight across all pick-ladder suffixes (0 = feasible)."""
        tail = over = 0
        for i in range(len(seats) - 1, -1, -1):
            tail += _sched_added(seats[i][1])
            over += max(0, tail - _grants_from(seats[i][0]))
        return over

    def _try(op):
        """Apply op(); keep it only if legal and strictly less overweight."""
        before = _excess()
        undo = op()
        if _pick_order_legal(seats) and _excess() < before:
            return True
        undo()
        return False

    for _ in range(80):
        if _excess() == 0:
            break
        # The level-1 creation pair (seats < pinned) never moves — the game fixes it.
        order_by_added = sorted(range(pinned, len(seats)), key=lambda k: _sched_added(seats[k][1]))
        improved = False
        # 1) plain swap: a heavy late power trades seats with a light early one.
        for j in sorted(range(pinned, len(seats)), key=lambda j: -_sched_added(seats[j][1])):
            for k in order_by_added:
                if k >= j or _sched_added(seats[k][1]) >= _sched_added(seats[j][1]):
                    continue
                if _sched_avail(seats[j][1]) > seats[k][0]:
                    continue

                def _op(j=j, k=k):
                    seats[j][1], seats[k][1] = seats[k][1], seats[j][1]
                    def undo(j=j, k=k):
                        seats[j][1], seats[k][1] = seats[k][1], seats[j][1]
                    return undo
                if _try(_op):
                    improved = True
                    break
            if improved:
                break
        if improved:
            continue
        # 2) rotate-left: when a heavy power is pinned behind its own set's prereqs
        # (Ice Elemental behind two Ice Mastery picks), a swap can't help — instead
        # pull a light power out of seat k, shift everything after it one seat
        # earlier (the whole chain moves together, order preserved), and re-seat the
        # light power at the end of the rotated span.
        for k in order_by_added:
            for j in range(len(seats) - 1, k, -1):
                if _sched_added(seats[j][1]) <= _sched_added(seats[k][1]):
                    continue
                if any(_sched_avail(seats[m][1]) > seats[m - 1][0] for m in range(k + 1, j + 1)):
                    continue                          # someone can't shift a seat earlier

                def _op(j=j, k=k):
                    moved = seats[k][1]
                    for m in range(k, j):
                        seats[m][1] = seats[m + 1][1]
                    seats[j][1] = moved
                    def undo(j=j, k=k):
                        back = seats[j][1]
                        for m in range(j, k, -1):
                            seats[m][1] = seats[m - 1][1]
                        seats[k][1] = back
                    return undo
                if _try(_op):
                    improved = True
                    break
            if improved:
                break
        if not improved:
            break                                    # no legal move left — report best effort
    for lv, p in seats:
        p["pick_level"] = lv
    return _excess() == 0


def _sched_budget_caps(powers):
    """After an unrepairable pick-level pass: per-power TOTAL-slot caps that make the
    tail placeable (walk the seats from 49 down, never letting a suffix outweigh the
    slots the game still grants there). Feed to the solver as _sched_budget and re-solve
    so the weight migrates to earlier powers instead of being silently dropped."""
    real = [p for p in powers
            if not (p.get("full_name") or "").startswith("Inherent") and p.get("pick_level")]
    caps, consumed = {}, 0
    for p in sorted(real, key=lambda p: -int(p["pick_level"])):
        allow = max(0, _grants_from(int(p["pick_level"])) - consumed)
        add = _sched_added(p)
        if add > allow:
            caps[p["full_name"]] = 1 + allow
            consumed += allow
        else:
            consumed += add
    return caps


def _l1_pick_errors(powers, archetype):
    """Character creation picks one of the primary's first two powers and one of the
    secondary's first two — a build containing neither (for either set) can't exist.
    (Corpus-verified: 2202/2211 master builds seat exactly primary+secondary at L1.)"""
    archetype = _at_canon(archetype)
    if not archetype or leveling_schedule.eat_type(archetype) in ("veat", "kheldian"):
        return []
    groups = POWERSETS["by_archetype"].get(archetype) or {}
    have = {(p.get("full_name") or "") for p in powers or []}
    build_sets = {p.get("powerset_full_name") for p in powers or []}
    errs = []
    for label, grp in (("primary", "primary"), ("secondary", "secondary")):
        names = {e["full_name"] for e in (groups.get(grp) or [])}
        ps = next((s for s in build_sets if s in names), None)
        if not ps:
            continue
        first2 = _set_first_two(ps)
        if first2 and not (set(first2) & have):
            disp = [fn.split(".")[-1].replace("_", " ") for fn in first2]
            errs.append(f"At character creation the game makes you take {disp[0]} or "
                        f"{disp[1]} (the first two {ps.split('.')[-1].replace('_', ' ')} "
                        f"powers) — this build has neither.")
    return errs


def _slot_schedule_errors(powers):
    """Validator messages for slots that could never be placed at the build's own
    pick levels. Only speaks when pick levels are present (imported/solved builds)."""
    real = [p for p in powers or []
            if not (p.get("full_name") or "").startswith("Inherent") and p.get("pick_level")]
    if not real:
        return []
    errs = []
    for p in real:
        lv = int(p["pick_level"])
        cap = 1 + _grants_from(lv)
        have = 1 + _sched_added(p)
        if have > cap:
            name = p.get("display_name") or (p.get("full_name") or "").split(".")[-1].replace("_", " ")
            errs.append(f"{name} is picked at level {lv} — after that the game only grants "
                        f"{_grants_from(lv)} more slots, so it can hold at most {cap} "
                        f"(this build gives it {have}). Take it earlier or move slots to an earlier power.")
    if not errs and not _schedule_feasible(real):
        errs.append("The late picks carry more added slots than the game grants at those levels "
                    "(each slot can only go into a power you already have) — move some slots "
                    "to earlier powers or re-Solve to reshuffle the pick order.")
    return errs


# The origin-themed pools are ONE-PER-BUILD (homecoming.wiki Power Pools: "you can only
# have one of these pools in a given build") — unlike ordinary pools. Gadgetry/Utility
# Belt join this group if/when Homecoming ships them.
_EXCLUSIVE_POOLS = {"Pool.Sorcery", "Pool.Experimentation", "Pool.Force_of_Will",
                    "Pool.Gadgetry", "Pool.Utility_Belt"}

# ── VEAT DUAL SET ACCESS (planner-trap catalog §1): after the level-24 respec a Soldier/
# Widow keeps the BASE sets alongside the chosen branch — a Crab build may legally take
# base Wolf Spider powers. Map: branch set → its base set (same for secondaries).
_VEAT_BASE_SET = {
    "Arachnos_Soldiers.Bane_Spider_Soldier":  "Arachnos_Soldiers.Arachnos_Soldier",
    "Arachnos_Soldiers.Crab_Spider_Soldier":  "Arachnos_Soldiers.Arachnos_Soldier",
    "Training_Gadgets.Bane_Spider_Training":  "Training_Gadgets.Training_and_Gadgets",
    "Training_Gadgets.Crab_Spider_Training":  "Training_Gadgets.Training_and_Gadgets",
    "Widow_Training.Night_Widow_Training":    "Widow_Training.Widow_Training",
    "Widow_Training.Fortunata_Training":      "Widow_Training.Widow_Training",
    "Teamwork.Widow_Teamwork":                "Teamwork.Teamwork",
    "Teamwork.Fortunata_Teamwork":            "Teamwork.Teamwork",
}
# Base-vs-branch DUPLICATE powers are mutually exclusive in game (the wiki flags both):
# taking the base version forbids the Crab version and vice versa.
_VEAT_DUPLICATE_PAIRS = [
    ("Arachnos_Soldiers.Arachnos_Soldier.Frag_Grenade",
     "Arachnos_Soldiers.Crab_Spider_Soldier.CS_Frag_Grenade"),
    ("Arachnos_Soldiers.Arachnos_Soldier.Venom_Grenade",
     "Arachnos_Soldiers.Crab_Spider_Soldier.CS_Venom_Grenade"),
]


def _veat_accessible_sets(primary, secondary):
    """All powersets a VEAT build may draw from: the chosen (branch) sets PLUS their base
    sets. Non-VEAT sets return just (primary, secondary)."""
    out = [primary, secondary]
    for ps in (primary, secondary):
        base = _VEAT_BASE_SET.get(ps)
        if base and base not in out:
            out.append(base)
    return out


def _picks_legal(fns, primary, secondary):
    """In-game legality of a pick-set: ≤4 pools; only ONE origin-themed pool
    (Sorcery/Experimentation/Force of Will); pool/epic tier prereqs (T1-2 free, T3 needs 1
    other from its pool, T4-5 need 2); at least one level-1 pick from BOTH primary and secondary
    (the game grants one of each at L1)."""
    pools, tiered = {}, {}
    for fn in fns:
        ps = fn.rsplit(".", 1)[0]
        if ps.startswith("Pool."):
            pools.setdefault(ps, set()).add(fn)
            tiered.setdefault(ps, set()).add(fn)
        elif ps.startswith("Epic."):
            # Epic/ancillary pools follow the SAME tier ladder (T1-2 free, T3 needs
            # one other, T4-5 — the pets like Ice Elemental — need two others), but
            # do NOT count toward the 4-pool cap.
            tiered.setdefault(ps, set()).add(fn)
    if len(pools) > 4:
        return False
    if len(set(pools) & _EXCLUSIVE_POOLS) > 1:
        return False
    for a, b in _VEAT_DUPLICATE_PAIRS:      # base vs branch versions of the same grenade
        if a in fns and b in fns:
            return False
    for ps, members in tiered.items():
        tiers = _pool_tiers(ps)
        for fn in members:
            need = _epic_prereq_count(tiers.get(fn, 0))
            if len(members) - 1 < need:
                return False
    for want in (primary, secondary):
        # VEAT dual access: the base set satisfies the level-1 seat for its branch
        # (post-24 respec, the L1 picks may legitimately come from the base set).
        ok_sets = {want}
        base = _VEAT_BASE_SET.get(want)
        if base:
            ok_sets.add(base)
        if not any(fn.rsplit(".", 1)[0] in ok_sets
                   and ((POWER_BY_FULL.get(fn) or {}).get("level_available") or 1) <= 1
                   for fn in fns):
            return False
    # LADDER-FIT (certification legality item from the 0.12.19 gate, built for
    # the wave 2026-07-15): the game grants picks at fixed levels
    # (POWER_PICK_LEVELS: 1,1,2,4,6,…) and a respec walks the same ladder — so
    # the i-th earliest-available pick must be available by the ladder's i-th
    # grant. The pulled Night Widow/Water-Kin champions converged with only two
    # picks available below level 4: no level-2 pick existed, the build could
    # not be leveled or respec'd as picked, and the serve-time seater refused
    # them. The SEARCH now refuses such rosters itself (Hall's condition on
    # sorted availability), so a certification can never converge unseatable.
    avails = sorted(
        ((POWER_BY_FULL.get(fn) or {}).get("level_available") or 1)
        for fn in fns if not fn.rsplit(".", 1)[0].startswith("Inherent"))
    ladder = leveling_schedule.POWER_PICK_LEVELS
    if len(avails) > len(ladder):
        return False
    for i, lv in enumerate(avails):
        if lv > ladder[i]:
            return False
    return True


# A level-50 character owns exactly 24 power PICKS (inherents excluded) — the search must
# treat unused pick levels as capacity to fill, never as acceptable convergence.
_PICK_CAP = 24


def _endurance_relief_pass(powers, archetype, ctx, res_cap):
    """Post-solve endurance relief (sweep fix, master-faithful): if the solved build still
    drains >3× recovery (worse than the user's shared iTrial master at 2.9×), swap the LAST
    piece of the costliest toggles for an Endurance Reduction common IO — exactly what
    masters do (their Venomous Gas runs 3 EndRdx HOs). Never touches globals/procs/uniques,
    never toggles with <2 slots; stops as soon as the ratio is playable. Fails safe."""
    try:
        for _ in range(4):
            tot = engine.calculate_build({"archetype": archetype, "powers": powers},
                                         SET_BONUSES, res_cap=res_cap, ctx=ctx)
            e = tot.get("endurance") or {}
            drain, rec = e.get("drain_per_sec") or 0, e.get("recovery_per_sec") or 0.01
            if drain <= 3.0 * rec:
                return powers
            cands = []
            _global_sets = {g.get("set", "").lower() for g in engine.PIECE_GLOBALS}
            for p in powers:
                rec_p = POWER_BY_FULL.get(p.get("full_name")) or {}
                if rec_p.get("power_type") != 2:
                    continue
                slots = p.get("slots") or []
                if len(slots) < 2:
                    continue
                last = slots[-1] or {}
                uid = last.get("piece_uid") or ""
                lset = (last.get("set_name") or "").lower()
                if (last.get("_proc") or last.get("_ho")
                        or uid == "Crafted_Endurance_Discount"
                        or lset in _global_sets):     # never eat a LotG-class global
                    continue
                # never ORPHAN a pair: swapping the 2nd piece of a 2-piece set leaves
                # a dead 1-piece fragment (field report: Tactics RRx2 -> RRx1+EndRdx)
                if lset and sum(1 for s in slots
                                if s and (s.get("set_name") or "").lower() == lset) == 2:
                    continue
                cost = (rec_p.get("end_cost") or 0) / max(
                    rec_p.get("activate_period") or 1.0, 0.25)
                if cost > 0:
                    cands.append((cost, p, slots))
            if not cands:
                return powers
            cands.sort(key=lambda x: -x[0])
            _c, p, slots = cands[0]
            slots[-1] = {"set_uid": "Endurance Reduction", "set_name": "Endurance Reduction",
                         "piece_name": "Endurance Reduction IO",
                         "piece_uid": "Crafted_Endurance_Discount",
                         "category_id": (slots[0] or {}).get("category_id")}
        return powers
    except Exception:  # noqa: BLE001
        return powers


def _endurance_recovery_floor(bt, targets):
    """PHYSICS-DERIVED recovery target (sweep fix: 397 combos ran hotter than master
    practice). From the UNSLOTTED baseline's drain estimate, require enough +recovery that
    drain ≤ ~3× recovery (the user's shared iTrial master runs 2.9× with Ageless assumed).
    Slotted end-redux typically trims ~25% of base drain — credited before sizing. Only
    RAISES an existing target, never lowers one the user/preset asked for."""
    endb = (bt or {}).get("endurance") or {}
    drain0 = endb.get("drain_per_sec") or 0.0
    base_rec = endb.get("recovery_per_sec") or 0.0
    if drain0 <= 0 or base_rec <= 0:
        return
    need = drain0 * 0.75 / 3.0
    if need > base_rec:
        pct = min(80.0, round((need / base_rec - 1.0) * 100.0))
        if pct > (targets.get("recovery") or 0):
            targets["recovery"] = pct


def deep_optimize(archetype, primary, secondary, role, content, powers_in,
                  scorer="first_principles", max_solves=1500, restarts=3, seed=1337,
                  ban=None, role_mix=None, pin=None, form=None):
    """Run the selection search TO THE END (the user's doctrine — see user-optimization-doctrine):
    evaluate the FULL swap neighborhood (best-improvement, nothing silently pruned — ordering only),
    iterate until a complete sweep finds nothing better ("this is as good as it gets" — earned, not
    declared), then PERTURB and re-climb (restarts) to escape local optima, keeping the global best.
    LEARNS across runs (learn.py): warm-starts from the CHAMPION build this context has already
    converged to, orders moves by mined per-power marginals from the whole exploration log
    (ordering only — nothing pruned), persists every explored build, and saves the new champion.
    MOVE SPACE: primary/secondary swaps + POOL and EPIC membership (drop/extend chains, drop a
    whole utility pool — Hasten included) under in-game legality (_picks_legal); the seed's
    TRAVEL power and inherents are protected. Returns an honest CERTIFICATE — converged vs
    budget-truncated. Objective = the first-principles encounter model, NOT master-comparison."""
    import copy as _c
    import random
    import first_principles as fp
    import learn
    rng = random.Random(seed)
    # BAN list (the pin/ban user-constraint feature): banned picks are stripped from the seed,
    # excluded from every add, and a champion warm start containing one is rejected — a USER
    # veto (e.g. no Hasten) is a hard constraint, not a preference the physics can outvote.
    ban = set(ban or ())
    # PIN list (the other half of pin/ban, 2026-07-12 — Joel's per-form Kheldian
    # champions): pinned picks are injected into the seed, never dropped, never
    # perturbed away (perturbs draw from the same neighborhood), and a champion
    # warm start MISSING one is rejected. `form` tags the saved champion's key
    # so a form champion lives beside the human one, never over it.
    pin = set(pin or ())
    if pin & ban:
        return None, {"error": f"pin/ban conflict: {sorted(pin & ban)}"}
    # v31: a farm content preset carries its own role story (AFK = survival,
    # active = damage) — content default wins over the AT default when the
    # caller declared neither.
    role = (role or ai_build.CONTENT_PRESETS.get(content or "", {}).get("default_role")
            or _AT_DEFAULT_ROLE.get(archetype, "damage"))
    # The AT's REAL res cap (yellowthief1's find, 2026-07-14): the old
    # hardcoded 75 undercut tank-role/CAP-entry targets for Tanker/Brute (90)
    # and Kheldians/VEATs (85). Evidence for the record: NO existing champion
    # certificate was affected — every one certified itrial + default role,
    # whose resistance asks (50/50/40/40) sit below 75, so the clamp never
    # engaged. Future tank-role/farm certifications would have hit it.
    pre = ai_build.preset_targets(
        content, role,
        res_cap=round(((ARCH_BY_NAME.get(archetype) or {}).get("res_cap") or 0.75) * 100, 1),
        archetype=archetype)
    targets, roles, perk = pre["targets"], pre["roles"], pre["perk_focus"]
    ctx = _stat_ctx(archetype)
    ctx["power_by_full"] = POWER_BY_FULL
    arch_row = ARCH_BY_NAME.get(archetype)
    res_cap = round(arch_row["res_cap"] * 100, 1) if arch_row else engine.RESISTANCE_HARD_CAP

    # NODE CAP (2026-07-16, the farm_active plateau pathology): the SEARCH's
    # candidate solves bound CBC's branch-and-bound nodes, so a plateau
    # marathon (20s-to-20-min bound-proving; ~1% of farm_active's sparse-ask
    # neighborhood, four 14-21-min CBC children observed blocking 30 sweep
    # threads in the field) returns its incumbent instead of stalling the
    # sweep barrier. Node-based, not wall-clock → same result on any machine.
    # Capped candidates are counted into the certificate; the WINNER re-solves
    # UNCAPPED in the finale, so nothing capped ever certifies AND the
    # certified score always equals the canonical (uncapped) evaluation —
    # without that re-solve, the next evaluate-first would flag every
    # capped-search champion as MOVED. Env restored in the finale (a crash
    # mid-run can leave it set in THIS process; workers are per-run processes,
    # the hub restarts on release — stated, accepted).
    _cap_prev = os.environ.get("HC_SOLVER_NODE_CAP")
    os.environ["HC_SOLVER_NODE_CAP"] = os.environ.get("HC_DEEP_NODE_CAP", "50000")
    _capped_before = len(solver.CAPPED_SOLVES)

    cache = {}                      # frozenset(picks) -> (score, solved_powers, breakdown)
    explored = []                   # log lines for the learning substrate
    n_solves = [0]
    _n_lock = __import__("threading").Lock()   # parallel sweeps: exact budget count

    def evaluate(pws):
        key = frozenset(p["full_name"] for p in pws)
        if key in cache:
            return cache[key]
        with _n_lock:
            if n_solves[0] >= max_solves:
                return (None, None, None)
            n_solves[0] += 1        # claim the budget slot BEFORE the solve —
            #                         exact accounting under parallel sweeps
        r = _assess_solve(archetype, _c.deepcopy(pws), _c.deepcopy(targets), "premium",
                          perk, roles, False, False, False, with_powers=True)
        if not r:
            cache[key] = (None, None, None)
            return cache[key]
        _tot, solved = r
        # Score what will actually SHIP: /build/solve applies the proc pass after the ILP
        # (proc bombs + the Achilles' Heel debuff anchor), and under MODEL_VERSION >= 10 the
        # encounter model reads slotted -res procs — so the search must see them too.
        # No guard here: certification/preset targets are harvest proxies and
        # the scorer IS the objective — see the A2 scope note at the
        # /build/solve call site. When deep_optimize gains declared-target
        # objectives (work order D farm champions), the strict guard comes
        # with them.
        solved = proc_pass.apply_proc_pass(solved, POWER_BY_FULL, role=role,
                                           content=content)
        solved = _endurance_relief_pass(solved, archetype, ctx, res_cap)
        tot = engine.calculate_build({"archetype": archetype, "powers": solved},
                                     SET_BONUSES, res_cap=res_cap, ctx=ctx)
        ev = fp.encounter_value(archetype, solved, ctx, tot, scenario=content,
                                arch_row=arch_row, role_output_mod=role_output)
        # ROLE LENS (v21) × PLAYSTYLE (v22) × FOCUS SPLIT (v23): the search maximizes the
        # DECLARED role's contribution — or the user's own percentage split when they
        # answered the "how do you want to divide your focus?" question — blended by the
        # scenario's team size (full role purity on a league, self-sufficiency solo).
        _tm = (fp.SCENARIOS.get(content) or fp.SCENARIOS["general"]).get("teammates", 0)
        cache[key] = (fp.role_contribution(ev, role_mix or role, teammates=_tm), solved, ev)
        explored.append({"picks": sorted(key), "score": ev["contribution"],
                         "deal": ev["my_dps"], "amplify": ev["amplified"],
                         "prevent": ev["prevented"], "avail": ev["availability"]})
        return cache[key]

    # Learned knowledge for this context: move ordering from mined per-power marginals.
    lm = learn.marginals(archetype, primary, secondary, content)
    _travel_fns = set(_TRAVEL.values())

    def _fn_ps(fn):
        return fn.rsplit(".", 1)[0]

    def neighborhood(cur):
        picked = {p["full_name"] for p in cur}
        epic_ps = next((_fn_ps(fn) for fn in picked if fn.startswith("Epic.")), None)
        drops = []
        for p in cur:
            fn = p["full_name"]
            ps = _fn_ps(fn)
            if fn in _travel_fns or fn in pin or ps.startswith("Inherent"):
                continue        # travel/pins are the user's choice; inherents aren't picks
            if (ps in _veat_accessible_sets(primary, secondary)
                    or ps.startswith("Pool.") or ps.startswith("Epic.")):
                drops.append(p)
        adds = []
        for ps in _veat_accessible_sets(primary, secondary):
            adds += [q for q in (POWERS.get(ps) or [])
                     if q["full_name"] not in picked and q.get("slottable")]
        cur_pools = {_fn_ps(fn) for fn in picked if fn.startswith("Pool.")}
        # FULL pool space (explore, don't prune): every pool is a candidate — including the
        # origin trio (Sorcery/Experimentation/Force of Will: Rune of Protection, Unleash
        # Potential…). _picks_legal polices the 4-pool cap, tier prereqs, and the
        # one-origin-pool rule, so lawfulness is enforced, not pre-filtered.
        cand_pools = cur_pools | {ps for ps in POWERS if ps.startswith("Pool.")}
        for ps in cand_pools:
            adds += [q for q in (POWERS.get(ps) or [])
                     if q["full_name"] not in picked and q.get("slottable")]
        if epic_ps:
            adds += [q for q in (POWERS.get(epic_ps) or [])
                     if q["full_name"] not in picked and q.get("slottable")]
        moves = [(d, a) for d in drops for a in adds
                 if a["full_name"] != d["full_name"] and a["full_name"] not in ban]
        # PURE-ADD moves: a build UNDER the 24-pick level-50 budget grows instead of only
        # trading. (Without these, a ban-stripped or short seed "converged" while leaving
        # empty pick levels — the missing-pools bug: swaps can never refill capacity.)
        n_picks = sum(1 for p in cur if not _fn_ps(p["full_name"]).startswith("Inherent"))
        if n_picks < _PICK_CAP:
            moves += [(None, a) for a in adds if a["full_name"] not in ban]
        # PURE-DROP moves: a pick can be NET-NEGATIVE (a mule attack's forced set floor
        # steals slots from real homes — Cross Punch measured −1.8%). The search must be
        # able to simply shed it, not only trade it for something else.
        moves += [(d, None) for d in drops]
        # ORDER by learned marginals (percentile knowledge from every past run), static value as
        # tiebreak — ordering only, never pruning: every legal move is evaluated before
        # convergence is claimed, and the certificate says so if the budget cuts it short.
        def mkey(m):
            d, a = m
            an = a["full_name"].split(".")[-1] if a else None
            dn = d["full_name"].split(".")[-1] if d else None
            learned = ((lm.get(an, 0.0) if a else 0.0)
                       - (lm.get(dn, 0.0) if d else 0.0)) * 1000.0
            static = ((_static_value(POWER_BY_FULL.get(a["full_name"], a), role, ctx)
                       if a else 0.0)
                      - (_static_value(POWER_BY_FULL.get(d["full_name"], {}) or {}, role, ctx)
                         if d else 0.0))
            return -(learned + 0.001 * static)
        moves.sort(key=mkey)
        return moves

    def apply(cur, d, a):
        if a and any(p["full_name"] == a["full_name"] for p in cur):
            return None                            # would duplicate a pick — illegal build
        t = [p for p in cur if d is None or p["full_name"] != d["full_name"]]
        if a is None:                              # pure DROP — shed a net-negative pick
            if not _picks_legal({p["full_name"] for p in t}, primary, secondary):
                return None
            return t
        if d is None:                              # pure ADD — only while under the pick cap
            if sum(1 for p in t if not _fn_ps(p["full_name"]).startswith("Inherent")) \
                    >= _PICK_CAP:
                return None
        alvl = a.get("level_available") or (POWER_BY_FULL.get(a["full_name"], {})
                                            .get("level_available") or 1)
        t.append({"full_name": a["full_name"],
                  "pick_level": max((d.get("pick_level") or 1) if d else 1, alvl)})
        if not _picks_legal({p["full_name"] for p in t}, primary, secondary):
            return None                            # pool tiers / 4-pool cap / L1 rule violated
        return t

    # CHAMPION WARM START: begin where this context's knowledge ended, not from the heuristic seed.
    powers_in = [p for p in powers_in if p["full_name"] not in ban]
    for _fn in sorted(pin):                 # pinned picks join the seed if absent
        if _fn in POWER_BY_FULL and not any(p["full_name"] == _fn for p in powers_in):
            powers_in.append({"full_name": _fn,
                              "pick_level": POWER_BY_FULL[_fn].get("level_available") or 1})
    heuristic_picks = [p["full_name"] for p in powers_in]   # what the PROPOSER offered (for the retrospective)
    seed_src = "autopick"
    champ = learn.load_champion(archetype, primary, secondary, content, form)
    if champ and all(fn in POWER_BY_FULL for fn in champ) \
            and not (ban & set(champ)) and pin <= set(champ) \
            and _picks_legal(set(champ), primary, secondary):
        powers_in = [{"full_name": fn,
                      "pick_level": POWER_BY_FULL[fn].get("level_available") or 1}
                     for fn in champ]
        seed_src = "champion"
    cur = list(powers_in)
    sc, solved, ev = evaluate(cur)
    if solved is None:
        return None, {"error": "seed solve failed"}
    # Reserve the retrospective's baseline UP FRONT (budget exhaustion refused it post-loop and
    # silently zeroed the miss count): score the heuristic proposer's own build now.
    h_sc = sc
    if seed_src == "champion":
        h_powers = [{"full_name": fn,
                     "pick_level": POWER_BY_FULL.get(fn, {}).get("level_available") or 1}
                    for fn in heuristic_picks if fn in POWER_BY_FULL]
        h_sc, _hs, _he = evaluate(h_powers)
    best = (sc, cur, solved, ev)
    path = []
    # ⚠ WHAT "converged" ACTUALLY CLAIMS (Joel's ruling, 2026-07-16 — the IG
    # flip). This flag means the SEARCH stopped finding improvements ON ITS OWN
    # OBJECTIVE (the in-run score, computed over search-constructed candidate
    # dicts). It does NOT claim the picks are optimal under the CANONICAL
    # evaluator whose number we publish — those are two different numbers, and
    # the farm_active proof case shows the gap is decision-changing: that build
    # certified at in-run 497.6 / canonical 432.1 with sweeps 30, restarts 6,
    # truncated False — and a ONE-POWER swap (Long_Jump -> Irradiated Ground)
    # scores 473.0 canonically, +40.9 over the champion the search certified
    # (reproduced fresh-process, twice, to the decimal). The certificate was
    # honest about the search and silent about the divergence; the wording now
    # states its own scope so nobody reads more into it than it proves.
    # ROOT-CAUSE WORK ORDER (queued behind the 0.12.21 cut): one objective, not
    # two — make the search optimise the number we certify, or certify the
    # number the search optimises.
    cert = {"sweeps": 0, "converged": False, "restarts_done": 0,
            "budget_truncated": False,
            "claim": "converged on the SEARCH objective (in-run scoring); "
                     "canonical_score is the portable number and is NOT "
                     "claimed optimal — see the one-objective work order",
            "canonical_optimality_checked": False}
    # PARALLEL SWEEPS (2026-07-14, Joel's word): a sweep's moves are independent
    # solves, and the CBC subprocess releases the GIL — evaluating them
    # concurrently is where the 4-6x lives. DETERMINISM IS PRESERVED: budget
    # slots are claimed in MOVE ORDER before any submission (the exact serial
    # semantics — a budget cutoff lands on the same move it always did), and
    # the reduce walks results in move order with the same strict-> comparison,
    # so tie-breaks match the serial sweep byte for byte. HC_PARALLEL_SWEEP=0
    # is the fallback switch.
    # HC_SWEEP_WORKERS overrides the thread count — the context-parallel
    # orchestrator (tools/converge_parallel.py) divides the machine between
    # worker PROCESSES, so each one's sweep pool must shrink to its share.
    _workers = 1 if os.environ.get("HC_PARALLEL_SWEEP") == "0" \
        else int(os.environ.get("HC_SWEEP_WORKERS")
                 or max(1, min(8, (os.cpu_count() or 4) - 2)))
    _tpe = __import__("concurrent.futures", fromlist=["ThreadPoolExecutor"])
    for r in range(restarts + 1):
        while True:                                  # climb THIS basin to the top
            sweep_best, sweep_move = None, None
            complete = True
            moves = neighborhood(cur)
            # Phase 1, in MOVE ORDER: exact serial semantics — the budget
            # check comes FIRST (top of the serial loop), so a cutoff lands on
            # the same move it always did; cache hits consume no budget.
            ordered = []          # (idx, d, a, trial, cached_result_or_None)
            claims = 0
            for idx, (d, a) in enumerate(moves):
                if n_solves[0] + claims >= max_solves:
                    complete = False
                    break
                trial = apply(cur, d, a)
                if trial is None:
                    continue
                key = frozenset(p["full_name"] for p in trial)
                if key in cache:
                    ordered.append((idx, d, a, trial, cache[key]))
                    continue
                claims += 1
                ordered.append((idx, d, a, trial, None))
            # Phase 2: evaluate the uncached trials concurrently.
            pending = [(i, t) for i, (idx, d, a, t, res) in enumerate(ordered)
                       if res is None]
            if pending and _workers > 1:
                with _tpe.ThreadPoolExecutor(max_workers=_workers) as ex:
                    futs = {ex.submit(evaluate, t): i for i, t in pending}
                    for f in _tpe.as_completed(futs):
                        i = futs[f]
                        idx, d, a, t, _ = ordered[i]
                        ordered[i] = (idx, d, a, t, f.result())
            else:
                for i, t in pending:
                    idx, d, a, t2, _ = ordered[i]
                    ordered[i] = (idx, d, a, t2, evaluate(t2))
            # Phase 3, in MOVE ORDER: the serial reduce, unchanged semantics.
            for idx, d, a, trial, res in ordered:
                tsc = res[0] if res else None
                if tsc is not None and (sweep_best is None or tsc > sweep_best[0]):
                    sweep_best, sweep_move = (tsc, trial, res[1], res[2]), (d, a)
            cert["sweeps"] += 1
            # Heartbeat (2026-07-12, the 24h-blind Peacebringer lesson): one line
            # per sweep so a long convergence is WATCHABLE — score, solve budget
            # spent, restart round. Output-only; certification is untouched.
            print(f"      sweep {cert['sweeps']:3d} r{r} best={best[0]:.1f} "
                  f"cur={sc:.1f} solves={n_solves[0]}/{max_solves}", flush=True)
            # Swaps must clear a 0.2% noise threshold (they can oscillate); a PURE ADD is
            # monotone — an empty pick level is filled by ANY strict improvement (a level-50
            # character owns 24 picks; leaving them empty needs proof, not a noise gate).
            _accept = sc * 1.002 if (sweep_move and sweep_move[0]) else sc
            if sweep_best and sweep_best[0] > _accept:
                sc, cur, solved, ev = sweep_best
                path.append({"dropped": (sweep_move[0]["full_name"].split(".")[-1]
                                         if sweep_move[0] else None),
                             "added": (sweep_move[1]["full_name"].split(".")[-1]
                                       if sweep_move[1] else None),
                             "score": sc})
                if sc > best[0]:
                    best = (sc, cur, solved, ev)
            else:
                if complete:
                    cert["converged"] = True         # a FULL sweep found nothing better
                    if r == 0:
                        # The PRIMARY basin (the champion itself) was proven locally optimal by a
                        # complete no-improvement sweep — restarts running out of budget later must
                        # not erase this earned certificate (it did, in run 11 — understating truth).
                        cert["primary_converged"] = True
                else:
                    cert["budget_truncated"] = True  # honesty: ran out, NOT proven optimal
                break
        if r >= restarts or n_solves[0] >= max_solves:
            break
        # PERTURB: kick 2 random swaps (accepting worse) and re-climb — escape this basin.
        # Moves are recomputed AFTER each kick (a stale move list once produced a duplicate pick).
        for _ in range(2):
            moves = [mv for mv in neighborhood(cur) if apply(cur, *mv) is not None]
            if moves:
                d, a = moves[rng.randrange(len(moves))]
                cur = apply(cur, d, a)
        r2 = evaluate(cur)
        if r2[1] is None:
            cur = list(best[1])
        else:
            sc, solved, ev = r2
        cert["restarts_done"] += 1
    if n_solves[0] >= max_solves:
        cert["budget_truncated"] = True
        cert["converged"] = False        # the FULL search (incl. restarts) wasn't finished…
        # …but a primary-basin proof, once earned, stands (cert["primary_converged"] survives).
    # FILL TO CAP (user doctrine: "an empty pick level is never better than a real power").
    # The legacy ILP set-floors can make EVERY 24th-pick candidate score slightly negative —
    # a slot-economics artifact scheduled for retirement — which let converged champions ship
    # under-cap. Until the floors go, the champion still ships 24 picks: take the LEAST-COSTLY
    # add each round and disclose it in the certificate.
    cert["picks_filled"] = 0
    max_solves += 250                    # reserved grace budget for the fill rounds
    while True:
        sc_b, cur_b = best[0], best[1]
        n = sum(1 for p in cur_b if not _fn_ps(p["full_name"]).startswith("Inherent"))
        if n >= _PICK_CAP or n_solves[0] >= max_solves:
            break
        best_add = None
        for d, a in neighborhood(cur_b):
            if d is not None or a is None:
                continue                 # pure adds only
            trial = apply(cur_b, None, a)
            if trial is None:
                continue
            tsc, tsol, tev = evaluate(trial)
            if tsc is not None and (best_add is None or tsc > best_add[0]):
                best_add = (tsc, trial, tsol, tev)
        if not best_add:
            break
        best = best_add                  # accepted even if slightly below sc_b — disclosed
        cert["picks_filled"] += 1
    # Learning substrate: persist EVERYTHING this run explored.
    try:
        logp = os.path.join(ROOT, "benchmarks", "exploration_log.jsonl")
        with open(logp, "a", encoding="utf-8") as f:
            for line in explored:
                f.write(json.dumps({"archetype": archetype, "primary": primary,
                                    "secondary": secondary, "content": content, **line}) + "\n")
    except Exception:  # noqa: BLE001
        pass
    sc_b, cur_b, solved_b, ev_b = best
    champion_picks = [p["full_name"] for p in cur_b]
    # NODE-CAP FINALE: restore the exact-solve contract, then re-solve the
    # winner UNCAPPED — unconditionally, because capped solves are NOT
    # reliably detectable (CBC's node-limit stop can parse as "Optimal" in
    # PuLP; measured 2026-07-16: a 35s candidate returned in 2.5s at cap 1000
    # with status Optimal, so CAPPED_SOLVES is only a floor). A capped
    # incumbent must never ship as a champion build.
    # RETRACTION (same day, field-measured): this re-solve does NOT make the
    # stored score equal the canonical baseline, as first claimed — the very
    # first field run scored 430.0 here while the canonical chain reproduces
    # 387.3 from a fresh process (same picks, same code, stable across
    # re-runs). In-process state after a 7,000-solve 30-thread run changes
    # the evaluation in a way a fresh process does not (mechanism NOT yet
    # root-caused; the historical run-vs-canonical gap, e.g. Mind Control
    # 927.6/705.1, is the same phenomenon). The stored score remains a
    # WITHIN-RUN ranking; canonical_score, written by evaluate_first from a
    # fresh process, remains the only portable number.
    if _cap_prev is None:
        os.environ.pop("HC_SOLVER_NODE_CAP", None)
    else:
        os.environ["HC_SOLVER_NODE_CAP"] = _cap_prev
    cert["node_cap"] = {"cap": int(os.environ.get("HC_DEEP_NODE_CAP", "50000")),
                        "capped_solves_floor":
                            len(solver.CAPPED_SOLVES) - _capped_before}
    r = _assess_solve(archetype, _c.deepcopy(cur_b), _c.deepcopy(targets),
                      "premium", perk, roles, False, False, False,
                      with_powers=True)
    if r:
        _tot2, solved2 = r
        solved2 = proc_pass.apply_proc_pass(solved2, POWER_BY_FULL,
                                            role=role, content=content)
        solved2 = _endurance_relief_pass(solved2, archetype, ctx, res_cap)
        tot2 = engine.calculate_build({"archetype": archetype,
                                       "powers": solved2},
                                      SET_BONUSES, res_cap=res_cap, ctx=ctx)
        ev2 = fp.encounter_value(archetype, solved2, ctx, tot2,
                                 scenario=content, arch_row=arch_row,
                                 role_output_mod=role_output)
        _tm2 = (fp.SCENARIOS.get(content)
                or fp.SCENARIOS["general"]).get("teammates", 0)
        sc2 = fp.role_contribution(ev2, role_mix or role, teammates=_tm2)
        cert["node_cap"]["final_resolve_delta"] = round(sc2 - sc_b, 2)
        sc_b, solved_b, ev_b = sc2, solved2, ev2
    # v31 AFK sustain label (Joel's ruling, 2026-07-16): any content that asks
    # the AFK regen floor certifies with the tier the build DOES sustain stated
    # on the certificate — the floor is never relaxed, a shortfall is never
    # silent, and a combo that covers the worst case through its own sustained
    # self-heal (auto-fire) says exactly that. Universal: keyed off the preset
    # flag, not a content-name special case.
    if (ai_build.CONTENT_PRESETS.get(content or "", {}) or {}).get("afk_regen_floor"):
        try:
            tot_b = engine.calculate_build({"archetype": archetype, "powers": solved_b},
                                           SET_BONUSES, res_cap=res_cap, ctx=ctx)
            cert["afk_sustain"] = fp.afk_sustain_assessment(
                solved_b, tot_b, arch_row, ctx, role_output_mod=role_output,
                assume_accolades=bool(
                    (ai_build.CONTENT_PRESETS.get(content or "", {}) or {})
                    .get("assumes_accolades")))
        except Exception:  # noqa: BLE001
            cert["afk_sustain"] = {"error": "assessment failed - investigate before release"}
    # Grow the knowledge: this context's champion is now whatever this run proved best.
    try:
        learn.save_champion(archetype, primary, secondary, content, champion_picks, sc_b, cert,
                            form=form)
    except Exception:  # noqa: BLE001
        pass
    # THE RETROSPECTIVE ("why did I miss those fits 693 times?"): score the heuristic proposer's
    # own build under this model, count how many explored builds beat it (the misses), diff the
    # proposer's picks vs the proven champion, and persist the lessons — seed_adjustments() feeds
    # them back into autopick so the PROPOSER itself improves, not just the search.
    retrospective = None
    try:
        misses = sum(1 for line in explored if h_sc is not None and line["score"] > h_sc)
        retrospective = learn.record_lessons(archetype, primary, secondary, content,
                                             heuristic_picks, champion_picks, misses,
                                             model_version=fp.MODEL_VERSION)
        retrospective["heuristic_score"] = h_sc
        retrospective["champion_score"] = sc_b
    except Exception:  # noqa: BLE001
        pass
    return solved_b, {"score": sc_b, "breakdown": ev_b, "path": path, "certificate": cert,
                      "builds_explored": len(explored), "solves": n_solves[0],
                      "seed": seed_src, "learned_moves": len(lm),
                      "retrospective": retrospective}


def _alt_routes(targets, res_cap):
    """Alternative emphases to pre-compute, each a perturbed target profile + the
    perk dial that matches it. Only MEASURED axes (damage isn't quantified yet)."""
    import copy as _copy
    routes = []
    t = _copy.deepcopy(targets); t["recharge"] = (t.get("recharge") or 0) + 30
    routes.append({"key": "recharge", "label": "More recharge", "targets": t,
                   "perk_focus": "recharge"})
    # AoE/farm damage: throughput is recharge-bound, so push recharge to perma range —
    # the resulting AoE DPS delta is shown via _headline_deltas' AoE-throughput term.
    t = _copy.deepcopy(targets); t["recharge"] = max((t.get("recharge") or 0), 100) + 20
    routes.append({"key": "aoe", "label": "More AoE damage", "targets": t,
                   "perk_focus": "recharge"})
    t = _copy.deepcopy(targets); rd = t.setdefault("resistance", {})
    for ty in (list(rd) or ["Smashing", "Lethal", "Fire", "Cold", "Energy", "Negative"]):
        rd[ty] = min(res_cap, max(rd.get(ty, 0), 50) + 15)
    routes.append({"key": "survival", "label": "Tougher (more resist)", "targets": t,
                   "perk_focus": "resistance"})
    t = _copy.deepcopy(targets); dd = t.setdefault("defense", {})
    for ty in (list(dd) or ["Ranged", "AoE"]):
        dd[ty] = min(45, max(dd.get(ty, 0), 32) + 8)
    routes.append({"key": "defense", "label": "More defense", "targets": t,
                   "perk_focus": "defense"})
    t = _copy.deepcopy(targets); t["recovery"] = (t.get("recovery") or 0) + 30
    routes.append({"key": "recovery", "label": "Better endurance", "targets": t,
                   "perk_focus": "recovery"})
    return routes


def _headline_deltas(cur, alt):
    """The stats that meaningfully change between two solved builds (>= 2 points),
    biggest first — so a route reads 'More recharge -> +18% rech, -4% Fire res'."""
    out = []
    # AoE throughput (farm damage) — the headline number for a damage dealer.
    ca = (cur.get("offense") or {}).get("aoe_dps", 0) or 0
    ba = (alt.get("offense") or {}).get("aoe_dps", 0) or 0
    if abs(ba - ca) >= 0.5:
        out.append({"stat": "AoE DPS", "d": round(ba - ca, 1)})
    for label, key in (("Recharge", "recharge"), ("Recovery", "recovery"),
                       ("Regen", "regeneration")):
        a = cur.get(key, {}).get("value", 0)
        b = alt.get(key, {}).get("value", 0)
        if abs(b - a) >= 2:
            out.append({"stat": label, "d": round(b - a, 1)})
    for kind, kk in (("res", "resistance"), ("def", "defense")):
        for ty in set(list(cur.get(kk, {})) + list(alt.get(kk, {}))):
            a = cur.get(kk, {}).get(ty, {}).get("value", 0)
            b = alt.get(kk, {}).get(ty, {}).get("value", 0)
            if abs(b - a) >= 2:
                out.append({"stat": f"{ty} {kind}", "d": round(b - a, 1)})
    out.sort(key=lambda x: -abs(x["d"]))
    return out[:5]


@app.route("/build/assess", methods=["POST"])
def build_assess():
    """Post-solve assessment: what the build optimized + where it landed, plus 2-4
    PRE-COMPUTED alternative routes with their real stat deltas (re-solved, not
    guessed) so the user can re-prioritize with eyes open. Deterministic, no AI."""
    body = request.get_json(force=True) or {}
    archetype = body.get("archetype")
    powers_in = body.get("powers") or []
    goal = (body.get("goal") or "").strip()
    tier = body.get("tier") or "premium"
    perk_focus = body.get("perk_focus") if isinstance(body.get("perk_focus"), str) else None
    roles = [r for r in (body.get("roles") or []) if isinstance(r, str)]
    content, role = body.get("content"), body.get("role")
    pvp = bool(body.get("pvp"))
    preserve = body.get("preserve", True)
    keep_layout = bool(body.get("keep_layout"))
    at = ARCH_BY_NAME.get(archetype)
    res_cap = round(at["res_cap"] * 100, 1) if at else engine.RESISTANCE_HARD_CAP
    _mp, _ms = _main_sets(powers_in)
    preset = ai_build.preset_targets(content, role, res_cap=res_cap,
                                     primary=_mp, secondary=_ms,
                                     goal=goal) if (content or role) else None
    if body.get("targets"):
        targets = body["targets"]
    elif preset:
        targets = {k: (dict(v) if isinstance(v, dict) else v)
                   for k, v in preset["targets"].items()}
        if goal:
            _merge_targets(targets, ai_build.goal_targets(goal, res_cap=res_cap))
        if not roles:
            roles = list(preset["roles"])
        if not perk_focus:
            perk_focus = preset.get("perk_focus")
    else:
        targets = ai_build.goal_targets(goal, res_cap=res_cap) if goal else {}
    if not (archetype and powers_in and targets):
        return jsonify({"ok": False})
    cur = _assess_solve(archetype, powers_in, targets, tier, perk_focus, roles,
                        pvp, preserve, keep_layout)
    if not cur:
        return jsonify({"ok": False})
    alternatives = []
    for emph in _alt_routes(targets, res_cap):
        alt = _assess_solve(archetype, powers_in, emph["targets"], tier,
                            emph.get("perk_focus", perk_focus), roles, pvp, preserve, keep_layout)
        if not alt:
            continue
        deltas = _headline_deltas(cur, alt)
        # keep routes that can't improve too, flagged 'maxed' — transparency: the
        # user sees every option was tried, and which are already at their ceiling.
        alternatives.append({"key": emph["key"], "label": emph["label"],
                             "perk_focus": emph.get("perk_focus"), "deltas": deltas,
                             "maxed": not deltas, "targets": emph["targets"]})
    return jsonify({"ok": True, "optimized": _targets_summary(targets),
                    "achieved": _solve_report(targets, cur), "alternatives": alternatives})


@app.route("/build/preset", methods=["POST"])
def build_preset():
    """Preview the target profile for a CONTENT/ROLE preset (for the user's
    archetype) so the UI can show what it'll aim for before solving."""
    body = request.get_json(force=True) or {}
    content = body.get("content")
    role = body.get("role")
    archetype = body.get("archetype")
    _at = ARCH_BY_NAME.get(archetype)
    rescap = round(_at["res_cap"] * 100, 1) if _at else engine.RESISTANCE_HARD_CAP
    if not (content or role):
        return jsonify({"ok": False})
    pre = ai_build.preset_targets(content, role, res_cap=rescap,
                                  primary=body.get("primary"), secondary=body.get("secondary"),
                                  goal=body.get("goal"))
    labels = [x for x in (ai_build.CONTENT_PRESETS.get(content, {}).get("label"),
                          ai_build.ROLE_PRESETS.get(role, {}).get("label")) if x]
    return jsonify({"ok": True, "summary": _targets_summary(pre["targets"]),
                    "labels": labels, "perk_focus": pre.get("perk_focus")})


# ── RESPEC PLAN ─────────────────────────────────────────────────────────────
# A concrete respec for a loaded build: the per-power slotting changes, a grocery list
# (what to acquire + what to unslot & sell), and the stat gains — so the suggestion isn't
# just "this could be better" but "here's exactly what to change and buy."
_RESPEC_GAINS = [
    ("S/L def", "defense", "Smashing"), ("Fire/Cold def", "defense", "Fire"),
    ("Energy def", "defense", "Energy"), ("Ranged def", "defense", "Ranged"),
    ("AoE def", "defense", "AoE"), ("Melee def", "defense", "Melee"),
    ("S/L res", "resistance", "Smashing"), ("Fire res", "resistance", "Fire"),
    ("Cold res", "resistance", "Cold"), ("Energy res", "resistance", "Energy"),
    ("Recharge", "recharge", None), ("Recovery", "recovery", None),
    ("Regen", "regeneration", None), ("Max HP", "max_hp", None),
]


def _respec_gains(cur, opt, res_cap):
    """Meaningful stat improvements (>=2 pts) from current -> optimized, biggest first."""
    out = []
    for label, k, sub in _RESPEC_GAINS:
        a = cur[k].get(sub, {}).get("value", 0) if sub else cur[k]["value"]
        b = opt[k].get(sub, {}).get("value", 0) if sub else opt[k]["value"]
        if k == "resistance":                 # over-cap gains aren't real
            a, b = min(a, res_cap), min(b, res_cap)
        if b - a >= 2:
            out.append({"stat": label, "from": round(a, 1), "to": round(b, 1),
                        "delta": round(b - a, 1)})
    out.sort(key=lambda g: -g["delta"])
    return out[:8]


def _unslot_advice(rarity):
    """What to do with a piece a respec frees up (you're pulling it OUT)."""
    if rarity in ("purple", "pvp", "winter", "ato"):
        return "premium — sells high on the market, or bank it if you'll reuse it"
    if rarity:
        return "standard set — sell on the market or convert as fodder"
    return "common IO — vendor or craft-and-sell"


def _respec_grocery(counts, selling):
    """Turn {set_name: pieces} into a shopping/sell list with rarity + advice."""
    out = []
    for s, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        rec = SET_BY_NAME.get((s or "").lower())
        rarity = converter.rarity_of(rec) if rec else None
        row = {"set": s, "pieces": n, "rarity": rarity}
        if selling:
            row["advice"] = _unslot_advice(rarity)
        out.append(row)
    return out


def _respec_plan(powers_in, optimized, cur_totals, opt_totals, res_cap):
    """Diff the player's CURRENT slotting against the optimized one at set granularity
    (how players shop and slot): per-power add/remove + aggregated acquire/sell grocery
    lists + stat gains. Returns None when nothing would change."""
    def _sets(power):
        c = {}
        for s in power.get("slots") or []:
            if s and s.get("set_name") and SET_BY_NAME.get(s["set_name"].lower()):
                c[s["set_name"]] = c.get(s["set_name"], 0) + 1
        return c
    opt_by_full = {p.get("full_name"): p for p in optimized}
    changes, acquire, sell = [], {}, {}
    for p in powers_in:
        fn = p.get("full_name")
        before, after = _sets(p), _sets(opt_by_full.get(fn) or {})
        if before == after:
            continue
        adds = {s: after[s] - before.get(s, 0) for s in after if after[s] > before.get(s, 0)}
        drops = {s: before[s] - after.get(s, 0) for s in before if before[s] > after.get(s, 0)}
        if not adds and not drops:
            continue
        pname = (POWER_BY_FULL.get(fn, {}).get("display_name")
                 or (fn or "").split(".")[-1].replace("_", " "))
        # full BEFORE/AFTER set composition (for the strike-through old → new display),
        # plus the deltas (for the grocery aggregation).
        commons_before = sum(1 for s in (p.get("slots") or [])
                             if s and (not s.get("set_name")
                                       or not SET_BY_NAME.get((s.get("set_name") or "").lower())))
        changes.append({"power": pname, "full_name": fn,
                        "before": [{"set": s, "n": n} for s, n in before.items()],
                        "after": [{"set": s, "n": n} for s, n in after.items()],
                        "before_commons": commons_before,
                        "add": [{"set": s, "n": n} for s, n in adds.items()],
                        "remove": [{"set": s, "n": n} for s, n in drops.items()]})
        for s, n in adds.items():
            acquire[s] = acquire.get(s, 0) + n
        for s, n in drops.items():
            sell[s] = sell.get(s, 0) + n
    if not changes:
        return None
    # A set that leaves one power and enters another is MOVED, not sold-then-rebought — net
    # the overlap out so the grocery list only lists genuine new buys and genuine sales.
    for s in list(acquire.keys()):
        if s in sell:
            moved = min(acquire[s], sell[s])
            acquire[s] -= moved
            sell[s] -= moved
            if not acquire[s]:
                del acquire[s]
            if not sell[s]:
                del sell[s]
    return {"changes": changes,
            "acquire": _respec_grocery(acquire, selling=False),
            "sell": _respec_grocery(sell, selling=True),
            "gains": _respec_gains(cur_totals, opt_totals, res_cap),
            "power_count": len(changes)}


@app.route("/build/solve", methods=["POST"])
def build_solve():
    """Constraint solver: take the build's POWERS + a target profile (from the
    goal, or explicit), and assign every slot optimally to hit the targets,
    then spend leftovers on perks. Deterministic, no AI. Returns the re-slotted
    powers + an achieved-vs-target report."""
    body = request.get_json(force=True) or {}
    archetype = body.get("archetype")
    powers_in = body.get("powers") or []
    goal = (body.get("goal") or "").strip()
    tier = body.get("tier") or "premium"
    perk_focus = body.get("perk_focus")    # hp|recovery|regen|recharge|defense|resistance
    if not isinstance(perk_focus, str):    # ignore non-string (e.g. a stray click event)
        perk_focus = None
    roles = [r for r in (body.get("roles") or []) if isinstance(r, str)]
    content = body.get("content")          # preset: fire_farm|itrial|team|general
    role = body.get("role")                # preset: buffer|healer|damage|tank
    # FOCUS SPLIT (user doctrine: when the intent is ambiguous, ASK — "what percentage on
    # Henchmen, how much on Empathy?"): {role: fraction} from the UI's split control. The
    # dominant role drives targets/presets; the full mix drives deep-optimize scoring.
    role_mix = body.get("role_mix") if isinstance(body.get("role_mix"), dict) else None
    if role_mix and not role:
        role = max(role_mix, key=lambda k: role_mix.get(k) or 0)
    exposure = body.get("exposure")        # flex|front|back — shapes the defense vector
    pvp = bool(body.get("pvp"))            # solve with PvP set bonuses + PvP totals
    # preserve = keep existing set IOs + unique globals, re-slot only generic/empty
    # slots (the default "complete my fit"); False = full re-slot from scratch.
    preserve = body.get("preserve", True)
    # keep_layout = also stay within each power's PLACED slot count (don't add slots)
    # and keep any cheap IO the solve doesn't upgrade. Tightest, lowest-cost option.
    keep_layout = bool(body.get("keep_layout"))
    _at = ARCH_BY_NAME.get(archetype)
    _rescap = round(_at["res_cap"] * 100, 1) if _at else engine.RESISTANCE_HARD_CAP
    # PRESET path: a CONTENT and/or ROLE pick generates the targets (no typing needed).
    # A free-text goal stays OPTIONAL — it just layers extra named caps on top.
    _mp2, _ms2 = _main_sets(body.get("powers"))
    # v31: farm contents carry their own role story when none was picked
    role = role or ai_build.CONTENT_PRESETS.get(content or "", {}).get("default_role")
    preset = ai_build.preset_targets(content, role, res_cap=_rescap, exposure=exposure,
                                     primary=body.get("primary") or _mp2,
                                     secondary=body.get("secondary") or _ms2,
                                     goal=body.get("goal"),
                                     archetype=archetype) if (content or role) else None
    preset_labels = []
    if body.get("targets"):
        targets = body["targets"]
    elif preset:
        targets = {k: (dict(v) if isinstance(v, dict) else v)
                   for k, v in preset["targets"].items()}
        if goal:                            # optional free-text adds extra named caps
            _merge_targets(targets, ai_build.goal_targets(goal, res_cap=_rescap))
        if not roles:
            roles = list(preset["roles"])
        if not perk_focus:
            perk_focus = preset.get("perk_focus")
        cl = ai_build.CONTENT_PRESETS.get(content, {}).get("label")
        rl = ai_build.ROLE_PRESETS.get(role, {}).get("label")
        preset_labels = [x for x in (cl, rl) if x]
    else:
        targets = ai_build.goal_targets(goal, res_cap=_rescap) if goal else {}
    # Interpret the free-text goal (instant, no AI) so the result can echo back
    # WHAT it understood. Use the SAME interpretation goal_targets() uses (no
    # powerset context) so the labels shown always match the targets solved.
    understood = preset_labels + (
        [m["label"] for m in ai_build.interpret_goal(goal).get("matched", [])] if goal else [])
    _orn = _off_role_notice(archetype, role, body.get("primary"), body.get("secondary"))
    if _orn:
        understood.insert(0, _orn)     # off-role/extension is a deliberate, ECHOED choice
    # CUSTOM BUILD-TARGETS (Maelwys item 4, Joel's rulings 2026-07-09): the
    # user's numbers REPLACE the preset's numeric targets wholesale — the
    # editor is seeded from the preset, so what it sends is the whole intended
    # truth (a dropped defense target is a choice, not an omission — the
    # Axe/FA case). Content/role still drive everything non-numeric (scenario
    # accuracy context, role kinds, perk focus). Values clamp to game reality;
    # champions are keyed to certified presets, so a custom solve is DERIVED —
    # labeled below, never certified.
    custom = body.get("custom_targets") or None
    if custom:
        targets = _apply_custom_targets(targets, custom, _rescap)
        understood.insert(0, "Custom targets (yours)")
    target_summary = _targets_summary(targets)
    if not (archetype and powers_in):
        return jsonify({"ok": False, "response": "Need an archetype and a build "
                        "with powers."}), 400
    if not (targets.get("defense") or targets.get("resistance")
            or any(k in targets for k in ("recharge", "recovery", "regen"))):
        msg = ("I couldn't tell what to target from "
               f"\"{goal}\". Try mentioning defense, resistance, recharge, or a "
               "specific aim like 'soft-cap defense, fire-farm survival'."
               if goal else "Set a goal first (e.g. 'fire-farm survivability, "
               "high recharge').")
        return jsonify({"ok": False, "response": msg, "understood": understood}), 400

    powers = []
    for p in powers_in:
        rec = POWER_BY_FULL.get(p.get("full_name"))
        if not rec:
            continue
        powers.append({"full_name": rec["full_name"],
                       "display_name": rec["display_name"],
                       "powerset_full_name": rec["powerset_full_name"],
                       "accepted_set_category_ids": rec.get("accepted_set_category_ids", []),
                       "accepted_set_categories": rec.get("accepted_set_categories", []),
                       "power_type": rec.get("power_type"),
                       "is_attack": rec.get("is_attack"),
                       "base_recharge": rec.get("base_recharge"),
                       "max_slot_count": rec.get("max_slot_count"),
                       "accepted_enhancement_types": rec.get("accepted_enhancement_types", []),
                       # current slotting, so preserve mode can lock existing sets.
                       # WORK ORDER C (2026-07-15): a FULL re-slot ignores the
                       # inbound layout entirely — with these fields live under
                       # preserve=False, the echoed-back result changed the
                       # NEXT press's input (_earned drove top-ups), so the
                       # same button pressed twice gave two different builds
                       # before settling. Full re-slot is now idempotent from
                       # press one: layout in, layout out, only picks matter.
                       "_existing_slots": (p.get("slots") or []) if (preserve or keep_layout) else [],
                       # slots the player actually placed (keep-layout cap)
                       "_earned": (p.get("earned_slot_count")
                                   or len([s for s in (p.get("slots") or []) if s]))
                       if (preserve or keep_layout) else 0})
    if not powers:
        return jsonify({"ok": False, "response": "None of the build's powers were "
                        "recognized."}), 400
    # flag support-set buffs so the buffing role (if ticked) reserves their slots
    for p in powers:
        p["_buff_priority"] = _is_support_powerset(p.get("powerset_full_name"))

    ctx = _stat_ctx(archetype)
    at = ARCH_BY_NAME.get(archetype)
    res_cap = round(at["res_cap"] * 100, 1) if at else engine.RESISTANCE_HARD_CAP
    # base innate (powers, no slots) -> solver fraction keys
    binit = {"archetype": archetype, "powers": [
        {"full_name": p["full_name"], "power_type": p["power_type"],
         "include_in_totals": p["power_type"] in (1, 2), "slots": []} for p in powers]}
    bt = engine.calculate_build(binit, SET_BONUSES, res_cap=res_cap, ctx=ctx)
    _endurance_recovery_floor(bt, targets)   # physics-derived +recovery vs this build's drain
    base = {}
    for t, d in bt["defense"].items():
        base[("Defense", t)] = d["value"] / 100.0
    for t, d in bt["resistance"].items():
        base[("Resistance", t)] = d["value"] / 100.0
    _attach_base_resdef(powers, archetype, ctx, res_cap)
    _add_typed_def_route(powers, targets, archetype)
    _attach_base_dmg(powers, ctx)

    _generated = not any(p.get("_earned") for p in powers_in)
    # In-game slot rule: each power has 1 FREE base slot; you distribute 67
    # ADDITIONAL slots (MidsReborn MaxSlots=67). So total placeable slots =
    # 67 + one base per power.
    slot_cap = 67 + len(powers)
    # Up to one re-solve: if the slotting can't be seated on the real pick ladder
    # (a level-49 pick holds at most 4 slots; 47+49 share 6), cap the tail offenders
    # and let the solver move that weight to earlier powers.
    for _sched_round in range(2):
        try:
            sol = solver.solve_ilp(powers, targets, SETS_BY_CATEGORY,
                                   engine.PIECE_GLOBALS, base, slot_cap=slot_cap, tier=tier,
                                   perk_focus=perk_focus, roles=roles, pvp=pvp,
                                   preserve=preserve, keep_layout=keep_layout, archetype=archetype,
                                   **_at_solve_phys(archetype))
        except Exception as e:  # noqa: BLE001
            return jsonify({"ok": False, "response": f"Solver failed: {e}"})

        # Proc-bombing pass (doctrine §3): for offense builds, convert damage auras + filler
        # AoEs into proc bombs — the #1 master-build damage lever. Fails safe (no-op on error).
        # Runs on a full re-slot, AND (v24) on GENERATED builds even in preserve mode — a
        # fresh wizard/autopick build has no player IO choices to preserve, and skipping the
        # pass there was why generated kits shipped proc-less in the proc meta.
        if not preserve or _generated:
            # A2 GUARD SCOPE (measured 2026-07-15, evaluate-first on all 19
            # certified contexts): the guard runs ONLY for user-DECLARED
            # targets (custom). Preset asks are harvest proxies — at
            # certification the true scorer consistently ENDORSES the proc
            # trade even where it dips a preset axis (guarding presets cost
            # every armor context 70-300 true-score points), so protecting a
            # proxy against the objective it proxies is backwards. A declared
            # ask is a promise; a preset is a heuristic. Work order D's farm
            # certifications declare their asks — they run this guard strict.
            sol["powers"] = proc_pass.apply_proc_pass(
                sol["powers"], POWER_BY_FULL, role=role, content=content,
                guard=(_TargetGuard(archetype, targets, ctx, _rescap,
                                    strict=True) if custom else None))
            sol["powers"] = _endurance_relief_pass(sol["powers"], archetype, ctx, _rescap)

        if _assign_pick_levels(sol["powers"], archetype) or _sched_round == 1:
            break
        caps = _sched_budget_caps(sol["powers"])
        if not caps:
            break
        for p in powers:
            if p["full_name"] in caps:
                p["_sched_budget"] = min(caps[p["full_name"]], p.get("_sched_budget") or 6)

    resolved = {"powers": sol["powers"]}
    _fill_slot_images(resolved)
    final = engine.calculate_build(
        {"archetype": archetype, "powers": sol["powers"], "pvp": pvp},
        SET_BONUSES, res_cap=res_cap, ctx=ctx)
    report = _solve_report(targets, final)

    # Flag any EXPENSIVE (set) IOs the solve removed vs the build it started from,
    # so respec'ing investment is always explicit — never silent. (In preserve mode
    # this should be empty; in full re-slot it lists what was traded away.)
    def _set_counts(slots):
        c = {}
        for s in (slots or []):
            if s and s.get("set_uid"):
                key = s.get("set_name") or s["set_uid"]
                c[key] = c.get(key, 0) + 1
        return c
    name_of = {p.get("full_name"): (POWER_BY_FULL.get(p.get("full_name"), {}).get(
        "display_name") or p.get("full_name")) for p in powers_in}
    after_by_full = {p["full_name"]: _set_counts(p.get("slots")) for p in sol["powers"]}
    removed_expensive = []
    for p in powers_in:
        before = _set_counts(p.get("slots"))
        after = after_by_full.get(p.get("full_name"), {})
        for setname, n in before.items():
            if after.get(setname, 0) < n:
                removed_expensive.append({
                    "power": name_of.get(p.get("full_name"), p.get("full_name")),
                    "set": setname, "before": n, "after": after.get(setname, 0)})

    # Optimization headroom: when we PRESERVED the player's sets, run a shadow
    # full-respec to show what going further would GAIN vs what it would COST (which
    # of their sets a respec would change) — so they can decide if it's worth it.
    # Skipped on perk-chip re-solves (perk_focus set) to keep those instant.
    headroom = None
    if sol.get("preserved") and goal and not perk_focus:
        try:
            full = solver.solve_ilp(copy.deepcopy(powers), targets, SETS_BY_CATEGORY,
                                    engine.PIECE_GLOBALS, base, slot_cap=slot_cap,
                                    tier=tier, roles=roles, pvp=pvp, preserve=False,
                                    archetype=archetype, **_at_solve_phys(archetype))
            ft = engine.calculate_build(
                {"archetype": archetype, "powers": full["powers"], "pvp": pvp},
                SET_BONUSES, res_cap=res_cap, ctx=ctx)
            headroom = _optimization_headroom(final, ft, powers_in, full["powers"],
                                              name_of, _set_counts, res_cap)
        except Exception:  # noqa: BLE001
            headroom = None

    # Gap-aware incarnate recommendations (always-on first, redirect-when-capped).
    inc_role = role or ("buffer" if any(_is_support_powerset(p.get("powerset_full_name"))
                                        for p in powers) else "damage")
    incarnate_recs = ai_build.recommend_incarnates(archetype, content, inc_role,
                                                   final, targets, res_cap)
    # per-content loadouts (incarnates are swappable per encounter) — fire-farm vs
    # iTrial/league vs AV picks for THIS build, so the right set is one click away.
    incarnate_loadouts = ai_build.incarnate_loadouts(archetype, inc_role, final, res_cap)
    # Attach a plain-language slotting rationale to each power so the build explains its own
    # intent (proc-bomb / committed set / global mules) instead of reading as random scatter.
    for _p in sol["powers"]:
        _plan = _slot_plan(_p, archetype, sol["powers"])
        if _plan:
            _p["slot_plan"] = _plan
    # RESPEC PLAN: on a FULL respec, diff the loaded build against the optimized one into a
    # concrete change list + grocery list (acquire / unslot & sell) + stat gains, so the
    # "suggest a respec" card can show exactly what to do. None when nothing changes.
    respec_plan = None
    if not preserve:
        try:
            cur_totals = engine.calculate_build(
                {"archetype": archetype, "powers": powers_in, "pvp": pvp},
                SET_BONUSES, res_cap=res_cap, ctx=ctx)
            respec_plan = _respec_plan(powers_in, sol["powers"], cur_totals, final, res_cap)
        except Exception:  # noqa: BLE001 — the plan is a nicety; never fail the solve over it
            respec_plan = None
    # WORK ORDER C (yellowthief1 find #3, root-caused 2026-07-15): the solve
    # always lays out the LEVEL-50 plan (all 67 added slots). On an imported
    # sub-50 character (earned < plan) with preserve off, that read as "it
    # gives you more slots than what you have" — slot conservation against
    # the 50 allotment holds in every measured arm (server x3, UI x3, stable
    # across repeated presses); the defect was the SILENCE about the level
    # gap. Say it plainly, server-side, so every client inherits the honesty.
    _warnings = _build_warnings(sol["powers"], archetype, final, content, role,
                                exposure)
    _earned_added = sum(max(0, int(p.get("earned_slot_count") or 0) - 1)
                        for p in powers_in if p.get("earned_slot_count"))
    _plan_added = sol.get("added_slots") or 0
    if not preserve and 0 < _earned_added < _plan_added:
        _warnings.insert(0, {
            "kind": "level_plan",
            "text": f"This is the level-50 plan — it places all {_plan_added} "
                    f"added slots. Your imported character currently owns "
                    f"{_earned_added} added slots; the rest arrive as you "
                    f"level (the leveling wall shows when each lands). "
                    f"Turn 'Preserve my sets' on to stay within today's "
                    f"slots."})
    return jsonify({"ok": True, "powers": sol["powers"], "respec_plan": respec_plan,
                    "warnings": _warnings,
                    "slots_used": sol["slots_used"],
                    "added_slots": sol.get("added_slots"),
                    "added_budget": sol.get("added_budget", 67),
                    "targets": targets,
                    # Derived-build labeling (Joel's constraint): a custom-
                    # target solve never reads as a certified/champion result.
                    "custom_targets": bool(custom),
                    "understood": understood,        # human-readable goal interpretation
                    "target_summary": target_summary,
                    "totals": final, "report": report,
                    "preserved": sol.get("preserved", False),
                    "kept_sets": sol.get("kept_sets", []),
                    "removed_expensive": removed_expensive,
                    "incarnate_recs": incarnate_recs,
                    "incarnate_loadouts": incarnate_loadouts,
                    "headroom": headroom})


def _optimization_headroom(preserve_totals, full_totals, powers_in, full_powers,
                           name_of, set_counts, res_cap):
    """Compare a preserve-solve vs a full respec: the stat GAINS of going further,
    the COST (the player's sets a respec would change), and a plain verdict — so
    the user can judge whether respec'ing is worth it."""
    GAINS = [("Fire res", "resistance", "Fire"), ("S/L res", "resistance", "Smashing"),
             ("Cold res", "resistance", "Cold"), ("Energy res", "resistance", "Energy"),
             ("S/L def", "defense", "Smashing"), ("Fire def", "defense", "Fire"),
             ("Cold def", "defense", "Cold"), ("AoE def", "defense", "AoE"),
             ("Ranged def", "defense", "Ranged"), ("Recharge", "recharge", None),
             ("Regen", "regeneration", None), ("Recovery", "recovery", None),
             ("Max HP", "max_hp", None)]
    gains = []
    for label, k, sub in GAINS:
        a = preserve_totals[k].get(sub, {}).get("value", 0) if sub else preserve_totals[k]["value"]
        b = full_totals[k].get(sub, {}).get("value", 0) if sub else full_totals[k]["value"]
        if k == "resistance":          # over-cap gains aren't real
            a, b = min(a, res_cap), min(b, res_cap)
        if b - a >= 2:
            gains.append({"stat": label, "from": round(a, 1), "to": round(b, 1),
                          "delta": round(b - a, 1)})
    gains.sort(key=lambda g: -g["delta"])
    full_by_full = {p["full_name"]: set_counts(p.get("slots")) for p in full_powers}
    lost = []
    for p in powers_in:
        before = set_counts(p.get("slots"))
        after = full_by_full.get(p.get("full_name"), {})
        for sn, n in before.items():
            if after.get(sn, 0) < n:
                lost.append({"power": name_of.get(p.get("full_name")), "set": sn})
    n = len(lost)
    if not gains:
        verdict = ("You're already at the best your current sets allow — a full "
                   "respec would gain little. Stay as you are.")
    elif n == 0:
        verdict = "A full respec wouldn't drop any of your sets — safe to optimize further."
    elif n <= 2:
        verdict = f"Modest rework — a respec would change {n} set(s) for the gains above."
    elif n <= 5:
        verdict = f"Significant rework — a respec would change {n} of your sets."
    else:
        verdict = (f"Major rework — a respec would replace {n} of your sets "
                   "(effectively a fresh build). Weigh that against the gains before "
                   "you re-buy those IOs.")
    return {"gains": gains[:6], "lost": lost, "n_lost": n, "verdict": verdict}


def _merge_targets(dst, src):
    """Merge src target profile into dst, taking the MAX per stat (so an optional
    free-text goal can only raise a preset's targets, never weaken them)."""
    for kind in ("defense", "resistance"):
        for t, v in (src.get(kind) or {}).items():
            dst.setdefault(kind, {})[t] = max(dst.get(kind, {}).get(t, 0), v)
    for fld in ("recharge", "recovery", "regen", "max_hp", "tohit"):
        if fld in src:
            dst[fld] = max(dst.get(fld, 0), src[fld])
    return dst


def _targets_summary(t):
    """Readable one-line summary of the numeric targets, so the result can echo
    back exactly what it aimed for (e.g. 'Fire def 45%/res 75%, Lethal res 75%…')."""
    def fmt(v):  # tolerate a non-numeric target like "CAP" that slipped past preset resolution
        return f"{v:g}" if isinstance(v, (int, float)) else str(v).lower()
    parts = []
    d = t.get("defense") or {}
    r = t.get("resistance") or {}
    for ty in sorted(set(list(d) + list(r))):
        bits = []
        if ty in d:
            bits.append(f"def {fmt(d[ty])}%")
        if ty in r:
            bits.append(f"res {fmt(r[ty])}%")
        parts.append(f"{ty} {' / '.join(bits)}")
    for fld, lab in (("recharge", "recharge"), ("recovery", "recovery"),
                     ("regen", "regen")):
        if fld in t:
            parts.append(f"{lab} +{fmt(t[fld])}%")
    return "; ".join(parts)


def _solve_report(targets, totals):
    """achieved-vs-target lines for display."""
    rows = []
    for t, tv in (targets.get("defense") or {}).items():
        cur = totals["defense"].get(t, {}).get("value", 0)
        rows.append({"stat": f"{t} Def", "have": round(cur, 1), "want": tv,
                     "met": cur >= tv - 0.5})
    for t, tv in (targets.get("resistance") or {}).items():
        cur = totals["resistance"].get(t, {}).get("value", 0)
        rows.append({"stat": f"{t} Res", "have": round(cur, 1), "want": tv,
                     "met": cur >= tv - 0.5})
    for fld, key in (("recharge", "recharge"), ("recovery", "recovery"),
                     ("regen", "regeneration")):
        if fld in targets:
            cur = totals[key]["value"]
            rows.append({"stat": fld.capitalize(), "have": round(cur, 1),
                         "want": targets[fld], "met": cur >= targets[fld] - 0.5})
    return rows


@app.route("/build/export", methods=["POST"])
def build_export():
    """Produce a Mids Reborn .mbd (JSON) for the current build."""
    payload = request.get_json(force=True) or {}
    mbd = mids_export.build_mbd(
        payload, DB_NAME, DB_VERSION,
        level_lookup=lambda fn: POWER_BY_FULL.get(fn, {}).get("level_available", 1))
    name = (payload.get("name") or "coh_build").strip().replace(" ", "_")
    return jsonify({"ok": True, "filename": f"{name}.mbd", "mbd": mbd})


def _critique_build(build, totals):
    """Fast, deterministic read of an imported build's strengths/weaknesses.
    Returns a list of {kind: good|warn|info, text}. No AI, no latency."""
    out = []
    defs = totals.get("defense", {})
    res = totals.get("resistance", {})
    soft = 45.0
    capped = [k for k, d in defs.items() if d["value"] >= soft]
    pos = {k: defs[k]["value"] for k in ("Melee", "Ranged", "AoE") if k in defs}
    if capped:
        out.append({"kind": "good", "text": f"Defense soft-capped (≥45%) on "
                    f"{len(capped)} type(s): {', '.join(capped)}."})
    near = [k for k, v in pos.items() if 32 <= v < soft]
    if near:
        out.append({"kind": "warn", "text": "Close to the defense soft cap but not "
                    f"there on {', '.join(f'{k} {pos[k]:.1f}%' for k in near)} — a "
                    "few more % would cap it (big survivability jump)."})
    res_cap = (totals.get("caps", {}) or {}).get("resistance_hard_cap", 75)
    top_res = sorted(res.items(), key=lambda kv: kv[1]["value"], reverse=True)[:3]
    if top_res and top_res[0][1]["value"] > 0:
        out.append({"kind": "info", "text": "Top resistances: " + ", ".join(
            f"{k} {d['value']:.0f}%" for k, d in top_res) + f" (cap {res_cap:.0f}%)."})
    rech = totals.get("recharge", {}).get("value", 0)
    out.append({"kind": "good" if rech >= 70 else "info",
                "text": f"Global recharge +{rech:.0f}%."})
    capped_sigs = totals.get("rule_of_five_capped", [])
    if capped_sigs:
        out.append({"kind": "warn", "text": f"{len(capped_sigs)} set-bonus type(s) "
                    "are over the rule-of-5 cap — those extra slots are wasted and "
                    "could be redirected."})
    # Slots: count ADDED slots (beyond each power's free base slot) vs the 67 budget.
    powers = build.get("powers", [])
    added = sum(max(0, len(p.get("slots") or []) - 1) for p in powers if p.get("slots"))
    over = added - 67
    out.append({"kind": "warn" if over > 0 else "info",
                "text": f"{added}/67 added slots used across {len(powers)} powers "
                f"(+1 free base each), {totals.get('applied_bonus_count', 0)} set "
                f"bonuses active." + (f" ⚠ {over} over the 67-slot budget — not "
                "buildable as-is." if over > 0 else "")})
    bare = [p["display_name"] for p in powers if not (p.get("slots"))]
    if len(bare) > 3:
        out.append({"kind": "info", "text": f"{len(bare)} powers have no enhancement "
                    "slots — possible set-bonus real estate if they accept sets."})
    # IN-PROGRESS SLOTTING (Joel, 2026-07-20 — the Dark Consumption case): a power
    # with earned-but-EMPTY slots is unfinished (he couldn't afford the recommended
    # set yet). An imported build must never present its empty slots as a finished
    # plan — say so plainly so the state is obvious at a glance.
    inprog = [(p.get("display_name"), sum(1 for s in (p.get("slots") or [])
                                          if not (s and s.get("piece_uid"))))
              for p in powers]
    inprog = [(nm, n) for nm, n in inprog if n]
    if inprog:
        total_empty = sum(n for _, n in inprog)
        shown = ", ".join(f"{nm} ({n})" for nm, n in inprog[:4])
        out.append({"kind": "warn", "text": f"In progress — {total_empty} empty slot"
                    f"{'s' if total_empty != 1 else ''} across {len(inprog)} power"
                    f"{'s' if len(inprog) != 1 else ''}: {shown}"
                    + ("…" if len(inprog) > 4 else "")
                    + ". Fill these to finish the build — an unfinished import is not "
                    "yet a complete plan."})
    # Level legality: a power can't be chosen before its available level.
    early = [f"{p['display_name']} (L{p.get('pick_level')} < L{p.get('level_available')})"
             for p in powers
             if p.get("pick_level") and p.get("level_available")
             and p["pick_level"] < p["level_available"]]
    if early:
        out.append({"kind": "warn", "text": "Picked before available (not a legal "
                    "in-game order): " + ", ".join(early[:6])
                    + (" …" if len(early) > 6 else "")})
    return out


# Squishy ATs: no armor secondary -> they borrow the defensive pillar from the team, or must
# IO-buy it. (Doctrine roles-and-context.md §3.) Used by the context-aware warning.
_SQUISHY_ATS = {"Class_Blaster", "Class_Defender", "Class_Controller", "Class_Corruptor",
                "Class_Dominator", "Class_Mastermind"}


def _attack_enh_rows(powers, ctx):
    """Per real-attack (>=3 invested slots) base damage + slotted Damage/Accuracy
    enhancement — so the warning can flag attacks that hit for base damage or whiff +4."""
    rows = []
    for power in powers:
        rec = POWER_BY_FULL.get(power.get("full_name"))
        if not rec or not rec.get("is_attack"):
            continue
        slots = [s for s in (power.get("slots") or []) if s]
        if len(slots) < 3:
            continue
        nproc = sum(1 for s in slots if s.get("_proc")
                    or (s.get("piece_uid") and proc_pass._is_proc_uid(s["piece_uid"])))
        if nproc >= len(slots) - 1:
            continue                      # a proc bomb is intentional — never flag it as weak
        nset = sum(1 for s in slots if s.get("set_uid"))   # slotted with a real IO set?
        dmg = acc = 0.0
        for s in slots:
            if s and s.get("piece_uid"):
                for asp, val in engine._scaled_boosts(s, ctx):
                    if asp == "Damage":
                        dmg += val
                    elif asp == "Accuracy":
                        acc += val
        base = _power_base_damage(rec, ctx)
        # nset/nproc let the warning stay quiet on invested attacks. Field report
        # (Maelwys 2026-07-06): an IMPORTED attack with a full damage set + procs (71.5%
        # damage) was mis-flagged "BASE damage only" because our per-piece boost read
        # came up short on unfamiliar imported piece data. A power carrying a real set
        # (>=2 set pieces) or any proc is invested — never "base damage only".
        rows.append((rec.get("display_name"), base, dmg, acc, nset, nproc))
    return rows


def _build_warnings(powers, archetype, totals, content, role, exposure=None):
    """Reliable, structural build-quality flags (doctrine roles-and-context.md): catches the
    exact failures the user hit — attacks doing no damage / whiffing +4, a squishy with no
    mitigation, a squishy sent to the FRONT LINE without the defense to survive there, and thin
    farm AoE coverage. No fragile DPS estimate involved."""
    out = []
    try:
        ctx = _stat_ctx(archetype)
        rows = _attack_enh_rows(powers, ctx)
        if rows:
            mx = max(r[1] for r in rows) or 1.0
            # "base damage only" ONLY for a truly bare attack: big base hit, ~no damage
            # enhancement, AND no real set (< 2 set pieces) AND no procs. A set or procs =
            # investment we don't second-guess (avoids false positives on imports).
            weak = [n for n, b, d, a, nset, nproc in rows
                    if b >= 0.35 * mx and d < 0.25 and nset < 2 and nproc == 0]
            miss = [n for n, b, d, a, nset, nproc in rows
                    if b >= 0.35 * mx and d >= 0.25 and a < 0.2 and nset < 2 and nproc == 0]
            if weak:
                out.append({"kind": "warn", "text": "⚔️ No damage enhancement on " +
                            ", ".join(weak[:5]) + " — these hit for BASE damage only. "
                            "Re-slot them with a damage set (full re-slot fixes this)."})
            if miss:
                out.append({"kind": "warn", "text": "🎯 Thin accuracy on " + ", ".join(miss[:5]) +
                            " — they'll miss +3/+4 enemies. Add accuracy / a +ToHit."})
        defs = totals.get("defense", {}) or {}
        res = totals.get("resistance", {}) or {}
        maxpos = max([defs.get(k, {}).get("value", 0) for k in ("Melee", "Ranged", "AoE")] + [0])
        maxres = max([res.get(k, {}).get("value", 0) for k in ("Smashing", "Lethal", "Fire")] + [0])
        if archetype in _SQUISHY_ATS and maxpos < 25 and maxres < 30:
            out.append({"kind": "warn", "text": "🛡️ No real mitigation layer (defense <25%, "
                        "resistance <30%). On a TEAM a tank holds aggro and you're devastating — "
                        "but SOLO or in a farm this build will faceplant. Buy ranged/melee "
                        "defense + a sustain, or run it on teams."})
        # A squishy (no armor secondary) put on the FRONT LINE eats every melee + AoE hit. Standing
        # there it lives or dies on DEFENSE soft-cap — resistance on a low-HP body in the middle of
        # the spawn isn't enough. "More damage doesn't help if you're dead." (roles-and-context.md)
        melee_def = (defs.get("Melee", {}) or {}).get("value", 0)
        aoe_def = (defs.get("AoE", {}) or {}).get("value", 0)
        if archetype in _SQUISHY_ATS and exposure == "front" and min(melee_def, aoe_def) < 35:
            at_lbl = archetype.replace("Class_", "")
            out.append({"kind": "warn", "text": f"🩸 Front-line glass cannon: a {at_lbl} has no armor, "
                        f"so in melee it survives on DEFENSE — and this build has only "
                        f"{round(min(melee_def, aoe_def))}% melee/AoE defense (soft-cap is 45%). "
                        "Resistance won't save a low-HP squishy standing in the spawn. Either invest "
                        "heavily toward ~45% positional defense (+ a sustain if the set has one), keep a "
                        "team tank holding aggro, or fight from RANGE where distance is your defense — "
                        "more damage doesn't help if you're on the floor."})
        if content == "fire_farm":
            aoe = 0
            for power in powers:
                rec = POWER_BY_FULL.get(power.get("full_name")) or {}
                # real geometry: an attack that hits an AREA, or a damage aura/patch toggle
                if ((rec.get("is_attack") and engine.is_aoe(rec)) or
                        (rec.get("power_type") == 2 and (rec.get("summons") or rec.get("damage_effects")))):
                    aoe += 1
            if aoe < 3:
                out.append({"kind": "warn", "text": f"🔥 Only {aoe} AoE damage source(s). Top "
                            "fire-farmers stack 3+ (a damage aura + Burn + AoEs) — this pairing "
                            "will clear noticeably slower."})
        # Weak epic/ancillary POWER PICKS for an offense build — single-target control where the
        # same set offers AoE / -resistance. (Re-solving keeps imported powers, so flag it.)
        if role in ("damage", "tank") or content == "fire_farm":
            by_ps = {}
            for power in powers:
                rec = POWER_BY_FULL.get(power.get("full_name"))
                ps = rec and (rec.get("powerset_full_name") or "")
                if ps and (ps.startswith("Epic.") or "_Mastery" in ps):
                    by_ps.setdefault(ps, []).append(rec)
            for ps, taken in by_ps.items():
                weak = [r for r in taken if r.get("is_attack") and _epic_atk_score(r) < 4]
                if not weak:
                    continue
                taken_fns = {r["full_name"] for r in taken}
                better = sorted([p for p in (POWERS.get(ps) or [])
                                 if p["full_name"] not in taken_fns and _epic_atk_score(p) >= 10],
                                key=lambda p: -_epic_atk_score(p))
                if better:
                    out.append({"kind": "warn", "text": "💥 " +
                                ", ".join(r["display_name"] for r in weak[:2]) +
                                " are single-target control — weak picks for a damage/farm build. "
                                "From the same set, " +
                                ", ".join(p["display_name"] for p in better[:2]) +
                                " give AoE + -resistance instead. Re-pick them in a respec "
                                "(re-solving only re-slots, it keeps your chosen powers)."})
        # RECHARGE-from-TRAVEL tip: Super Speed lives in the SAME pool as Hasten (Speed), so taking
        # it as travel costs NO extra pool — which frees a 4th pool for Combat Jumping, a Luck of the
        # Gambler +recharge mule (~+7.5% recharge + defense). Any OTHER travel (Teleport/Fly/Jump)
        # spends a whole pool on travel and gives that up. Flag it when recharge is short on a role
        # that lives on recharge, so the cost of the travel pick is visible, not silent.
        rech = round((totals.get("recharge") or {}).get("value", 0)) if isinstance(totals.get("recharge"), dict) else 0
        nm_set = {(p.get("full_name") or "").split(".")[-1] for p in (powers or [])}
        if (role not in ("tank",) and "Hasten" in nm_set and "Super_Speed" not in nm_set
                and rech and rech < 85):
            out.append({"kind": "tip", "text": "⚡ Recharge tip: your travel pool is spent on travel. "
                        "Super Speed shares its pool with Hasten — switching to it frees a 4th pool "
                        "for Combat Jumping (a Luck of the Gambler +recharge mule), worth ~14% global "
                        "recharge + some defense. Keep your travel if you prefer it; just know the cost."})
    except Exception:  # noqa: BLE001 — warnings must never break a solve/import
        pass
    return out


# ---------------------------------------------------------------------------
# In-game build discovery. /build_save_file writes <Homecoming>\accounts\
# <account>\<character>.txt — instead of making the player hike there with a
# file picker, scan the usual install locations (plus any folder the user
# taught us, remembered in settings.json next to the saves) and offer what's
# found. The file picker remains as the fallback for exotic installs.
# ---------------------------------------------------------------------------
def _settings_path():
    return os.path.join(os.path.dirname(_saves_dir()), "settings.json")


def _load_settings():
    try:
        with open(_settings_path(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def _save_settings(s):
    try:
        with open(_settings_path(), "w", encoding="utf-8") as f:
            json.dump(s, f, indent=1)
    except OSError:
        pass


def _find_accounts_dirs(extra_root=None):
    """Existing 'accounts' directories from remembered/user-given roots plus the
    usual install parents. Fixed shallow candidates only — never walks a drive."""
    import glob as g
    roots = []
    remembered = _load_settings().get("game_root")
    if remembered:
        roots.append(remembered)
    if extra_root:
        roots.append(extra_root)
    found = []
    for r in roots:
        r = r.strip().strip('"')
        if os.path.basename(r).lower() == "accounts" and os.path.isdir(r):
            found.append(r)
        elif os.path.isdir(os.path.join(r, "accounts")):
            found.append(os.path.join(r, "accounts"))
    candidates = []
    for drive in ("C:", "D:", "E:"):
        candidates += [rf"{drive}\Games", rf"{drive}\Homecoming", rf"{drive}\City of Heroes"]
    for env in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        if os.environ.get(env):
            candidates.append(os.environ[env])
    for c in candidates:
        found += [p for p in g.glob(os.path.join(c, "accounts")) if os.path.isdir(p)]
        found += [p for p in g.glob(os.path.join(c, "*", "accounts")) if os.path.isdir(p)]
    seen, out = set(), []
    for p in found:
        k = os.path.normcase(os.path.abspath(p))
        if k not in seen:
            seen.add(k)
            out.append(os.path.abspath(p))
    return out


@app.route("/ingame/scan")
def ingame_scan():
    import glob as g
    extra = (request.args.get("root") or "").strip() or None
    accs = _find_accounts_dirs(extra)
    files = []
    for acc in accs:
        for path in g.glob(os.path.join(acc, "*", "*.txt")) + g.glob(os.path.join(acc, "*.txt")):
            try:
                if os.path.getsize(path) > 512 * 1024:
                    continue                      # build saves are a few KB
                with open(path, encoding="utf-8", errors="ignore") as f:
                    head = f.read(4096)
                if not ingame_import.looks_like_ingame(head):
                    continue
                parent = os.path.dirname(path)
                files.append({"path": path,
                              "character": os.path.splitext(os.path.basename(path))[0],
                              "account": os.path.basename(parent) if os.path.normcase(parent) != os.path.normcase(acc) else "",
                              "modified": os.path.getmtime(path)})
            except OSError:
                continue
    files.sort(key=lambda x: -x["modified"])
    if files:
        # remember the game root that worked, so the next scan is instant
        acc_dir = os.path.dirname(files[0]["path"])
        while acc_dir and os.path.basename(acc_dir).lower() != "accounts":
            acc_dir = os.path.dirname(acc_dir)
        if acc_dir:
            s = _load_settings()
            s["game_root"] = os.path.dirname(acc_dir)
            _save_settings(s)
    return jsonify({"ok": True, "files": files[:40], "searched": accs})


@app.route("/ingame/read", methods=["POST"])
def ingame_read():
    """Read a build save the scan offered. The path must live under a known
    accounts directory — this endpoint is not a general file reader."""
    body = request.get_json(force=True) or {}
    path = os.path.abspath(body.get("path") or "")
    allowed = [os.path.normcase(a) for a in _find_accounts_dirs()]
    inside = any(os.path.normcase(path).startswith(a + os.sep) for a in allowed)
    if not (inside and path.lower().endswith(".txt") and os.path.isfile(path)):
        return jsonify({"ok": False, "response": "That file isn't in a known accounts folder — "
                        "use the file picker instead."}), 400
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return jsonify({"ok": True, "text": f.read(),
                            "name": os.path.splitext(os.path.basename(path))[0]})
    except OSError as e:
        return jsonify({"ok": False, "response": f"Couldn't read the file: {e}"}), 500


# ── GAME-LOG CAPTURE (P1: import + insights; see server/gamelog.py) ─────────
import gamelog  # noqa: E402
import pulse_feed  # noqa: E402  — Lite-parity: boards + consented feed

if getattr(sys, "frozen", False):
    gamelog.STATE_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"),
                                     "HeroCompanion", "gamelog")
else:
    gamelog.STATE_DIR = os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "gamelog"))


def _watch_dirs(st):
    """The set of watched Logs folders, migrating the old single-account state."""
    dirs = st.get("watch_dirs")
    if dirs is None and st.get("log_dir"):
        dirs = [st["log_dir"]]
    return list(dirs or [])


@app.route("/gamelog/scan", methods=["POST"])
def gamelog_scan():
    """Accounts (with/without Logs folders) so the user picks which to watch — a
    dual-boxer can watch more than one at once."""
    body = request.get_json(force=True) or {}
    accounts = gamelog.find_log_accounts(_find_accounts_dirs(body.get("root")))
    st = gamelog.load_state()
    return jsonify({"ok": True, "accounts": accounts, "watching": _watch_dirs(st)})


@app.route("/gamelog/watch", methods=["POST"])
def gamelog_watch():
    """Set the watched Logs folders (dual-box = more than one). Each path must live under
    a known accounts directory — same containment rule as /ingame/read. Accepts `log_dirs`
    (list) or `log_dir` (single, back-compat)."""
    body = request.get_json(force=True) or {}
    raw = body.get("log_dirs") or ([body["log_dir"]] if body.get("log_dir") else [])
    allowed = [os.path.normcase(a) for a in _find_accounts_dirs(body.get("root"))]
    dirs = []
    for d in raw:
        p = os.path.abspath(d or "")
        if any(os.path.normcase(p).startswith(a + os.sep) for a in allowed):
            dirs.append(p)
    if raw and not dirs:
        return jsonify({"ok": False, "response": "That folder isn't under a known accounts "
                        "directory."}), 400
    st = gamelog.load_state()
    st["watch_dirs"] = dirs
    st.pop("log_dir", None)             # fully migrated to the list
    gamelog.save_state(st)
    return jsonify({"ok": True, "watching": dirs})


@app.route("/gamelog/pulse", methods=["POST"])
def gamelog_pulse():
    """Turn pulse capture (public-channel recruitment facts) on or off. Its OWN consent,
    separate from log capture, per the choice doctrine: channel lines contain other
    players' text, so even local structured capture is an explicit, reversible opt-in.
    Only structured facts (channel/speaker/content/spots/difficulty) are ever stored;
    raw chat lines never are."""
    body = request.get_json(force=True) or {}
    st = gamelog.load_state()
    st["pulse_capture"] = bool(body.get("enabled"))
    gamelog.save_state(st)
    return jsonify({"ok": True, "pulse_capture": st["pulse_capture"]})


@app.route("/gamelog/ingest", methods=["POST"])
def gamelog_ingest():
    """Incrementally read every watched account's log files and return fresh insights.
    The report is honest about coverage: unrecognized reward-shaped lines are counted and
    sampled so real logs keep improving the parser."""
    st = gamelog.load_state()
    dirs = _watch_dirs(st)
    if not dirs:
        return jsonify({"ok": False, "response": "Pick an account to watch first."}), 400
    # Companion Lite may be running as the capture daemon — if it holds the ingest lock,
    # don't race it: its events land in the same store, so insights stay fresh anyway.
    if not gamelog.acquire_ingest("full"):
        owner = gamelog.ingest_owner() or {}
        return jsonify({"ok": True, "report": {"captured_by": owner.get("tag", "other")},
                        "insights": _gamelog_insights(),
                        "status": {"has_files": True, "external_capture": True}})
    agg = {"files": 0, "new_lines": 0, "parsed": 0, "unparsed_interesting": 0,
           "unparsed_samples": []}
    newest = None
    for d in dirs:
        _, rep = gamelog.ingest(d, st)
        for k in ("files", "new_lines", "parsed", "unparsed_interesting"):
            agg[k] += rep.get(k, 0)
        for s in rep.get("unparsed_samples", []):
            if len(agg["unparsed_samples"]) < 20:
                agg["unparsed_samples"].append(s)
        stt = gamelog.log_status(d, time.time())
        if stt.get("has_files"):
            newest = stt
    gamelog.save_state(st)
    # Lite-parity feed: fires only with the release-build key + shown-terms
    # consent + the reversible toggle on; self-throttled to one upload per
    # 5 minutes and never raises (a feed hiccup must not break insights).
    pulse_feed.maybe_upload()
    return jsonify({"ok": True, "report": agg, "insights": _gamelog_insights(),
                    "status": newest or {"has_files": False}})


@app.route("/gamelog/insights", methods=["GET"])
def gamelog_insights():
    return jsonify({"ok": True, "insights": _gamelog_insights()})


# ── Pulse Boards parity (Joel's order 2026-07-12: every Companion Lite feature
# lives in the full app too). server/pulse_feed.py is the faithful port; the
# capture/parser layer was ALREADY shared (gamelog), so this adds the three
# Lite-only surfaces: private board, public preview, and the consented feed. ──
@app.route("/gamelog/board")
def gamelog_board():
    """The PRIVATE local pulse board — your scorecards, market ledger, raids,
    built from your own capture store. Local data only, never uploaded."""
    try:
        return pulse_feed.build_board(public=False)
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "response": f"Board build failed: {e}"}), 500


@app.route("/gamelog/board/public")
def gamelog_board_public():
    """The sanitized PUBLIC-variant preview — exactly what sharing shows,
    so the choice to feed is an informed one."""
    try:
        return pulse_feed.build_board(public=True)
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "response": f"Board build failed: {e}"}), 500


@app.route("/gamelog/feed", methods=["GET", "POST"])
def gamelog_feed():
    """Feed status (GET) or consent/toggle (POST). POST accepts
    {accept_terms: true} — records the shown-terms consent the uploader
    requires — and/or {enabled: bool} — the remembered, reversible off switch.
    Without the release-build upload key the feed is structurally inert."""
    if request.method == "POST":
        body = request.get_json(force=True) or {}
        if body.get("accept_terms"):
            pulse_feed.accept_terms()
        if "enabled" in body:
            pulse_feed.set_feed_enabled(bool(body.get("enabled")))
    return jsonify({"ok": True, "terms": pulse_feed.TERMS, **pulse_feed.feed_status()})


def _fit_set_index(fit_id):
    """set_name (lower) -> [power display names] for every enhancement set slotted in a
    saved build. Lets the Play Log tell a player a drop is FOR THEIR build, and exactly
    which power wants it. Empty dict if the save can't be read."""
    if not fit_id:
        return {}
    path = os.path.join(_saves_dir(), _save_slug(fit_id) + ".json")
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    idx = {}
    for p in ((data.get("build") or {}).get("powers") or []):
        pname = p.get("display_name") or (p.get("full_name") or "?").split(".")[-1].replace("_", " ")
        for sl in (p.get("slots") or []):
            nm = (sl or {}).get("set_name")
            if nm:
                idx.setdefault(nm.lower(), [])
                if pname not in idx[nm.lower()]:
                    idx[nm.lower()].append(pname)
    return idx


def _saved_fit_for(character):
    """The saved build to associate with a logged-in character, and how confident we are.
    An EXPLICIT link (character -> save id, set by the user) wins and survives renames /
    fixes wrong guesses; otherwise we GUESS by name (exact, then contains). Returns
    (fit_dict, linked_bool) or (None, False). Field note: players sometimes rename, which
    breaks name-matching — that's exactly why the explicit link exists."""
    if not character:
        return None, False
    saves = _all_saves()
    links = gamelog.load_state().get("fit_links") or {}
    linked_id = links.get(character)
    if linked_id:
        hit = next((v for v in saves if v.get("id") == linked_id), None)
        if hit:
            return hit, True
    low = character.lower()
    guess = (next((v for v in saves if (v.get("name") or "").lower() == low), None)
             or next((v for v in saves if low in (v.get("name") or "").lower()), None))
    return guess, False


@app.route("/gamelog/link", methods=["POST"])
def gamelog_link():
    """Explicitly tie a character to a saved fit (rename-proof), or clear the tie."""
    body = request.get_json(force=True) or {}
    character = (body.get("character") or "").strip()
    if not character:
        return jsonify({"ok": False, "response": "No character."}), 400
    st = gamelog.load_state()
    links = st.setdefault("fit_links", {})
    if body.get("save_id"):
        links[character] = body["save_id"]
    else:
        links.pop(character, None)
    gamelog.save_state(st)
    return jsonify({"ok": True, "insights": _gamelog_insights()})


def _gamelog_insights():
    """Summarized events + haul verdicts + WHO is logged in. A recipe drop maps to its
    enhancement set by the name before the ':'; the verdict follows the converter doctrine
    by rarity. Events are attributed to the character active at the time (Welcome markers),
    so stats break out per character and the active character links to its saved fit."""
    st = gamelog.load_state()
    dirs = _watch_dirs(st)
    accounts = [os.path.basename(os.path.dirname(d)) for d in dirs]
    chars_by_acct = st.get("characters") or {}
    s = gamelog.summarize(gamelog.load_events(), accounts=accounts)
    # Per-account fit set-index: what sets each watched character's saved build actually
    # uses, so a drop that fits the plan is flagged KEEP-FOR-YOU no matter its generic rarity
    # verdict. Keyed by account so a dual-boxer's two characters never cross-match.
    fit_idx_by_acct = {}
    for acct in accounts:
        ch = chars_by_acct.get(acct)
        fit, _lk = _saved_fit_for(ch)
        fit_idx_by_acct[acct] = (ch, _fit_set_index(fit["id"]) if fit else {})
    haul, fit_haul = [], 0
    for d in s["drops"][-80:]:
        item = d.get("item") or ""
        kind = d.get("kind", "salvage")
        acct = d.get("account")
        verdict, why, setname = "—", "", None
        # Resolve the enhancement SET this item belongs to (recipes AND crafted IO drops),
        # so fit-matching works regardless of drop kind.
        base = re.sub(r"\s*\(Recipe\)$", "", item)
        base = re.sub(r"^Invention:\s*", "", base)
        rec = SET_BY_NAME.get(base.split(":")[0].strip().lower())
        setname = rec.get("name") if rec else None
        if kind == "recipe" or rec:
            if rec:
                r = converter.rarity_of(rec)
                if r in ("purple", "pvp", "winter"):
                    verdict, why = "KEEP", f"{r} pool — premium; convert within the pool if unneeded"
                elif r == "ato":
                    verdict, why = "KEEP", "archetype set — By-Set converts only"
                else:
                    verdict, why = "CONVERT/SELL", "standard set — By-Category fodder, or sell to fund seeds"
            else:
                verdict, why = "SELL", "generic/common recipe — craft-and-sell or vendor"
        elif kind == "incarnate":
            verdict, why = "—", "incarnate salvage — just bank it and spend later, nothing to decide"
        elif kind == "incarnate_merit":
            verdict, why = "—", "incarnate merit — bank it and spend later, nothing to decide"
        elif kind == "crafting":
            verdict, why = "—", "crafting material (catalyst/converter) — bank it; useful later or sellable"
        else:
            verdict, why = "SELL", "salvage — sell the surplus, keep what your recipes need"
        # FIT-AWARE HAUL: does the watched character's build actually slot this set? If so it's
        # a KEEP for THEM — a standard set you'd normally vendor is an upgrade when it's your plan.
        ch, fidx = fit_idx_by_acct.get(acct, (None, {}))
        uses = fidx.get(setname.lower()) if setname else None
        for_build = None
        if uses:
            for_build = {"character": ch, "powers": uses}
            verdict = "KEEP"
            why = (f"in {ch}'s build — slotted in {', '.join(uses[:2])}"
                   + ("…" if len(uses) > 2 else ""))
            fit_haul += 1
        haul.append({"ts": d.get("ts"), "item": item, "kind": kind, "account": acct,
                     "set": setname, "verdict": verdict, "why": why, "for_build": for_build})
    # Per-watched-account "who is playing" + that character's fit link. For a dual-boxer
    # this is one entry per client (Rattle on one account, the farmer on the other).
    who = []
    for acct in accounts:
        ch = chars_by_acct.get(acct)
        fit, linked = _saved_fit_for(ch)
        who.append({"account": acct, "character": ch,
                    "fit": {"id": fit["id"], "name": fit["name"], "linked": linked} if fit else None})
    # keep single-character fields for back-compat (first watched account)
    first = who[0] if who else {"character": None, "fit": None}
    return {"summary": {k: v for k, v in s.items() if k not in ("drops",)},
            "haul": haul, "fit_haul": fit_haul, "who": who,
            "character": first.get("character"), "fit": first.get("fit")}


@app.route("/build/import", methods=["POST"])
def build_import():
    """Import a Mids Reborn .mbd: parse -> resolve -> totals -> quick critique.
    The frontend then offers goal/role/tier + Solve to produce an improved build."""
    body = request.get_json(force=True) or {}
    data = body.get("mbd")
    # Two import formats share this endpoint: Mids .mbd (JSON) and the in-game
    # /build_save_file text export. Detect the in-game text first by its header.
    if ingame_import.looks_like_ingame(data):
        parsed = ingame_import.parse_ingame_build(data, _import_lookups())
    else:
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception as e:  # noqa: BLE001
                return jsonify({"ok": False, "response": f"Not valid .mbd JSON: {e}"})
        if not isinstance(data, dict):
            return jsonify({"ok": False, "response": "No build content provided."})
        parsed = mids_import.parse_build(data, _import_lookups())
    if not parsed.get("ok"):
        return jsonify({"ok": False, "response": parsed.get("error", "Parse failed.")})

    build = parsed["build"]
    if build.get("archetype") not in ARCH_BY_NAME:
        return jsonify({"ok": False, "response": "Unknown archetype "
                        f"'{build.get('archetype')}' — is this a Homecoming build?"})
    pvp = bool(body.get("pvp"))
    build["pvp"] = pvp
    at = ARCH_BY_NAME.get(build["archetype"])
    res_cap = round(at["res_cap"] * 100, 1) if at else engine.RESISTANCE_HARD_CAP
    totals = engine.calculate_build(build, SET_BONUSES, res_cap=res_cap,
                                    ctx=_stat_ctx(build["archetype"]))
    _fill_slot_images(build)
    critique = _critique_build(build, totals)
    critique += _build_warnings(build.get("powers", []), build["archetype"], totals,
                                body.get("content") or "general", body.get("role"),
                                body.get("exposure"))
    note = ""
    if parsed["unresolved_enh"]:
        note = ("Couldn't map these enhancements (kept the slots, no set bonus): "
                + ", ".join(parsed["unresolved_enh"][:8])
                + (" …" if len(parsed["unresolved_enh"]) > 8 else ""))
    return jsonify({"ok": True, "build": build, "name": parsed["name"],
                    "totals": totals, "critique": critique, "note": note,
                    "unresolved_enh": parsed["unresolved_enh"],
                    "unresolved_powers": parsed["unresolved_powers"]})


@app.route("/build/powercust", methods=["POST"])
def build_powercust():
    """Produce a Homecoming .powerCust (power color/glow customization) for the
    build's powers from a color scheme. Color1 = primary tint, Color2 = glow."""
    body = request.get_json(force=True) or {}
    powers = body.get("powers") or []
    default_scheme = body.get("default") or {}
    by_powerset = body.get("by_powerset") or {}
    if not powers:
        return jsonify({"ok": False, "response": "Add some powers first."}), 400
    blocks = mids_powercust.scheme_blocks(powers, default_scheme, by_powerset)
    if not blocks:
        return jsonify({"ok": False, "response": "Pick at least one color scheme."})
    text = mids_powercust.build_powercust(blocks)
    name = (body.get("name") or "coh_colors").strip().replace(" ", "_") or "coh_colors"
    # resolved per-power colors for the preview
    preview = [{"full_name": b["full_name"], "c1": b["c1"][:3], "c2": b["c2"][:3]}
               for b in blocks]
    return jsonify({"ok": True, "filename": f"{name}.powerCust", "text": text,
                    "preview": preview, "count": len(blocks)})


@app.route("/ai/query", methods=["POST"])
def ai_query():
    gate = _ai_gate()
    if gate:
        return gate
    body = request.get_json(force=True) or {}
    build = body.get("current_build", body.get("build", {}))
    question = body.get("question", "").strip()
    if not question:
        return jsonify({"ok": False, "response": "No question provided."}), 400
    at = ARCH_BY_NAME.get(build.get("archetype"))
    res_cap = round(at["res_cap"] * 100, 1) if at else engine.RESISTANCE_HARD_CAP
    totals = engine.calculate_build(build, SET_BONUSES, res_cap=res_cap,
                                    ctx=_stat_ctx(build.get("archetype")))
    result = claude_bridge.ask_claude(build, question, totals)
    return jsonify(result)


def _gen_context(archetype, primary, secondary):
    """Shared setup for the generate / refine endpoints."""
    at = ARCH_BY_NAME.get(archetype)
    at_display = at["display_name"] if at else archetype
    by_at = POWERSETS["by_archetype"].get(archetype, {})
    epics = [e["full_name"] for e in by_at.get("epic", [])]
    pools = [e["full_name"] for e in POWERSETS.get("pools", [])]
    label_of = {}
    for grp in (by_at.get("primary", []), by_at.get("secondary", []),
                by_at.get("epic", []), POWERSETS.get("pools", [])):
        for e in grp:
            label_of[e["full_name"]] = e["display_name"]
    # The Fitness inherents (Swift/Health/Hurdle/Stamina) are auto-granted on
    # Homecoming — free, no power pick — and Health/Stamina are prime set-bonus
    # mules, so always offer them to the AI.
    label_of["Inherent.Fitness"] = "Inherent Fitness (free — always available)"
    power_index, powers_grouped = {}, {}
    for ps in [primary, secondary] + pools + epics + ["Inherent.Fitness"]:
        names = []
        for p in POWERS.get(ps, []):
            power_index.setdefault(p["display_name"].lower(), p)
            names.append(p["display_name"])
        if names:
            powers_grouped[label_of.get(ps, ps.split(".")[-1].replace("_", " "))] = names
    sets_by_cat = {}
    for s in ENH_SETS:
        sets_by_cat.setdefault(s["category"], []).append(s["name"])
    inc_slots_prompt = {sl["slot"]: [c["display_name"] for c in sl["choices"]]
                        for sl in INCARNATES["slots"]}
    inc_index = {sl["slot"]: {c["display_name"].lower():
                              {"full_name": c["full_name"], "display_name": c["display_name"]}
                              for c in sl["choices"]}
                 for sl in INCARNATES["slots"]}
    return {"at": at, "at_display": at_display, "label_of": label_of,
            "pools": pools, "epics": epics, "power_index": power_index,
            "powers_grouped": powers_grouped, "sets_by_cat": sets_by_cat,
            "inc_slots_prompt": inc_slots_prompt, "inc_index": inc_index}


def _resolved_totals(resolved, archetype):
    """Compute the passive stat totals for a resolved build (incarnates excluded,
    matching the Stats panel's default) so tier cards can show numbers."""
    inc_full = {slot: v.get("full_name")
                for slot, v in (resolved.get("incarnates") or {}).items()}
    calc_build = {"archetype": archetype, "powers": resolved.get("powers", []),
                  "incarnates_full": inc_full, "include_incarnates": False}
    at = ARCH_BY_NAME.get(archetype)
    res_cap = round(at["res_cap"] * 100, 1) if at else engine.RESISTANCE_HARD_CAP
    return engine.calculate_build(calc_build, SET_BONUSES, res_cap=res_cap,
                                  ctx=_stat_ctx(archetype))


@app.route("/ai/interpret-goal", methods=["POST"])
def ai_interpret_goal():
    """Instant (no AI call) interpretation of a free-text goal into concrete
    priorities, for the confirm-before-generate step."""
    body = request.get_json(force=True) or {}
    return jsonify(ai_build.interpret_goal((body.get("goal") or "").strip(),
                   primary=body.get("primary"), secondary=body.get("secondary")))


# A complete level-50 build spends ~64-67 enhancement slots. If a generation
# comes in well under that, it left value on the table — auto-run one fill pass.
_SLOT_TARGET = 62


_SLOT_CAP = 67   # a level-50 build has exactly 67 enhancement slots total


def _slots_used(resolved):
    return sum(len(p.get("slots") or []) for p in resolved.get("powers", []))


def _cap_slots(resolved, cap=_SLOT_CAP):
    """Enforce the hard 67-slot budget. If a build exceeds it (an over-eager
    refine can), trim the last slot from the fattest powers until legal —
    preferring to trim powers that are NOT a clean single full set (frankenslot/
    generic-heavy first) so complete set bonuses survive where possible."""
    powers = resolved.get("powers", [])

    def total():
        return sum(len(p.get("slots") or []) for p in powers)

    def trim_score(p):
        slots = p.get("slots") or []
        sets = {s.get("set_uid") for s in slots if s and s.get("set_uid")}
        # higher = trim first: many slots, and mixed/generic rather than one set
        return (len(slots), len(sets) != 1)

    guard = 0
    while total() > cap and guard < 300:
        guard += 1
        cand = max((p for p in powers if len(p.get("slots") or []) > 1),
                   key=trim_score, default=None)
        if not cand:
            break
        cand["slots"].pop()
        cand["slotCount"] = len(cand["slots"])
    return resolved


def _build_issues(resolved, goal_labels, totals):
    """Evaluate the build against what the goal actually requires. Returns a list
    of concrete problems (empty = good enough). Thresholds are LENIENT — they
    catch builds that clearly missed the goal, not imperfect ones, so the loop
    converges instead of chasing unreachable caps."""
    issues = []
    used = _slots_used(resolved)
    if used < _SLOT_TARGET:
        issues.append(f"it used only {used} of 67 enhancement slots — fill the "
                      "empty slots and complete partial sets")
    dmax = max((v["value"] for v in totals["defense"].values()), default=0)
    rmax = max((v["value"] for v in totals["resistance"].values()), default=0)
    fire_res = totals["resistance"]["Fire"]["value"]
    fire_def = totals["defense"]["Fire"]["value"]
    if "Fire-farm survival" in goal_labels and fire_res < 45 and fire_def < 40:
        issues.append(f"FIRE mitigation is far too low (Fire res {fire_res:.0f}% / "
                      f"Fire def {fire_def:.0f}%) for a fire farm — take Gloom, "
                      "Tenebrous Tentacles and Blackstar and slot Superior "
                      "Winter's Bite / Frozen Blast / Avalanche in them for "
                      "Fire/Cold resistance + Ranged/AoE defense, and slot Fire "
                      "Shield with a full Aegis set")
    if "Soft-capped defense (45%)" in goal_labels and dmax < 40:
        issues.append(f"defense is not near the 45% soft cap (best is {dmax:.0f}%) "
                      "— add Luck of the Gambler / defense sets and Weave, "
                      "Maneuvers, Combat Jumping")
    if "Capped resistance" in goal_labels and rmax < 55:
        issues.append(f"resistance is low (best is {rmax:.0f}%) — slot resistance "
                      "sets in Tough and the armor toggles")
    return issues


def _generate_one(g, archetype, primary, secondary, goal, tier, focus=None):
    """Run one tier's generation end-to-end. Returns a resolved-build dict
    (with ok/error), safe to call from a worker thread. After generating, it
    evaluates the build against the goal and runs up to MAX_FIX targeted
    correction passes if it fell short (an evaluate-and-correct loop, not
    best-of-N)."""
    prompt = ai_build.generate_prompt(
        g["at_display"], g["label_of"].get(primary, primary),
        g["label_of"].get(secondary, secondary), goal,
        g["powers_grouped"], g["sets_by_cat"], g["inc_slots_prompt"],
        tier=tier, focus=focus, set_hints=_set_hints(goal))
    res = claude_bridge.run_prompt(prompt, timeout=540)
    if not res["ok"]:
        return {"ok": False, "tier": tier, "response": res["response"]}
    try:
        cjson = ai_build.extract_json(res["response"])
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "tier": tier,
                "response": f"Claude returned text that wasn't valid JSON: {e}",
                "raw": res["response"][:1500]}

    resolved = ai_build.resolve_build(cjson, g["power_index"], SET_BY_NAME,
                                      CAT_BY_ID, g["inc_index"], COMMON_IO_MAP)
    _cap_slots(resolved)

    # --- Evaluate-and-correct loop: run once, check whether the build actually
    # met the goal; if not, tell the AI exactly what fell short and have it fix
    # that specific thing. Re-evaluate and repeat, up to MAX_FIX passes. (This is
    # a targeted correction loop, NOT best-of-N dice-rolling.) ---
    goal_labels = [m["label"] for m in ai_build.interpret_goal(
        goal, primary=primary, secondary=secondary)["matched"]]
    totals = _resolved_totals(resolved, archetype)
    issues = _build_issues(resolved, goal_labels, totals)
    MAX_FIX = 2
    for _ in range(MAX_FIX):
        if not issues:
            break
        cur = {"powers": resolved.get("powers", []),
               "incarnates": resolved.get("incarnates", {})}
        fill_note = ("Your build did NOT fully meet the goal. Problems to FIX: "
                     + "; ".join(issues) + ". Correct exactly these.")
        rprompt = ai_build.refine_prompt(
            g["at_display"], g["label_of"].get(primary, primary),
            g["label_of"].get(secondary, secondary), goal, cur, totals,
            g["powers_grouped"], g["inc_slots_prompt"], tier=tier, focus=focus,
            fill_note=fill_note)
        res2 = claude_bridge.run_prompt(rprompt, timeout=540)
        if not res2.get("ok"):
            break
        try:
            cand = ai_build.resolve_build(
                ai_build.extract_json(res2["response"]), g["power_index"],
                SET_BY_NAME, CAT_BY_ID, g["inc_index"], COMMON_IO_MAP)
        except Exception:  # noqa: BLE001
            break
        if not cand.get("powers"):
            break
        _cap_slots(cand)
        cand_totals = _resolved_totals(cand, archetype)
        cand_issues = _build_issues(cand, goal_labels, cand_totals)
        # accept only as an improvement (fewer problems, or same count but fuller)
        if len(cand_issues) < len(issues) or (
                len(cand_issues) == len(issues)
                and _slots_used(cand) > _slots_used(resolved)):
            resolved, totals, issues = cand, cand_totals, cand_issues
            resolved["refilled"] = True
        else:
            break   # not improving — stop rather than thrash
    _fill_slot_images(resolved)
    resolved["ok"] = True
    resolved["tier"] = tier
    resolved["tier_meta"] = ai_build.TIER_META.get(tier, {})
    resolved["archetype"] = archetype
    resolved["primary"] = primary
    resolved["secondary"] = secondary
    resolved["slots_used"] = _slots_used(resolved)
    used = set(resolved["powersets_used"])
    resolved["pools_used"] = [ps for ps in g["pools"] if ps in used]
    resolved["epic_used"] = next((ps for ps in g["epics"] if ps in used), None)
    resolved["totals"] = _resolved_totals(resolved, archetype)
    return resolved


@app.route("/ai/generate-build", methods=["POST"])
def ai_generate_build():
    gate = _ai_gate()
    if gate:
        return gate
    body = request.get_json(force=True) or {}
    archetype = body.get("archetype")          # class name, e.g. Class_Tanker
    primary = body.get("primary")              # powerset full_name
    secondary = body.get("secondary")          # powerset full_name
    goal = (body.get("goal") or "").strip()
    tier = body.get("tier") or "balanced"
    focus = body.get("focus")        # confirmed-priority text from interpret-goal
    if not (archetype and primary and secondary and goal):
        return jsonify({"ok": False,
                        "response": "Choose an archetype, primary, secondary, "
                                    "and enter a goal first."}), 400
    g = _gen_context(archetype, primary, secondary)
    return jsonify(_generate_one(g, archetype, primary, secondary, goal, tier, focus=focus))


def _solved_base(archetype, powers):
    """Innate (no-slot) totals for the solver, in fraction keys."""
    ctx = _stat_ctx(archetype)
    at = ARCH_BY_NAME.get(archetype)
    res_cap = round(at["res_cap"] * 100, 1) if at else engine.RESISTANCE_HARD_CAP
    binit = {"archetype": archetype, "powers": [
        {"full_name": p["full_name"], "power_type": p["power_type"],
         "include_in_totals": p["power_type"] in (1, 2), "slots": []} for p in powers]}
    bt = engine.calculate_build(binit, SET_BONUSES, res_cap=res_cap, ctx=ctx)
    base = {}
    for t, d in bt["defense"].items():
        base[("Defense", t)] = d["value"] / 100.0
    for t, d in bt["resistance"].items():
        base[("Resistance", t)] = d["value"] / 100.0
    return base, ctx, res_cap


@app.route("/ai/generate-solved", methods=["POST"])
def ai_generate_solved():
    gate = _ai_gate()
    if gate:
        return gate
    """The chained flow: ONE LLM call picks the powers, then the deterministic
    solver slots them at each tier (budget/balanced/premium). Replaces three
    slow LLM builds with one call + three instant optimal solves."""
    body = request.get_json(force=True) or {}
    archetype = body.get("archetype")
    primary = body.get("primary")
    secondary = body.get("secondary")
    goal = (body.get("goal") or "").strip()
    roles = body.get("roles") or []        # what to base the build on (blendable)
    pvp = bool(body.get("pvp"))            # build for PvP (PvP set bonuses + totals)
    if not (archetype and primary and secondary and goal):
        return jsonify({"ok": False, "response": "Choose an archetype, primary, "
                        "secondary, and enter a goal first."}), 400

    g = _gen_context(archetype, primary, secondary)
    focus = ai_build.interpret_goal(goal, primary=primary, secondary=secondary)["focus"]
    prompt = ai_build.powers_prompt(
        g["at_display"], g["label_of"].get(primary, primary),
        g["label_of"].get(secondary, secondary), goal,
        g["powers_grouped"], g["inc_slots_prompt"], focus=focus)
    res = claude_bridge.run_prompt(prompt, timeout=300)
    if not res["ok"]:
        return jsonify({"ok": False, "response": res["response"]})
    try:
        cjson = ai_build.extract_json(res["response"])
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False,
                        "response": f"Claude returned non-JSON power list: {e}",
                        "raw": res["response"][:1500]})
    picked = ai_build.resolve_powers(cjson, g["power_index"], g["inc_index"])
    if not picked["powers"]:
        return jsonify({"ok": False, "response": "No valid powers were picked."})

    targets = ai_build.goal_targets(goal)
    base, ctx, res_cap = _solved_base(archetype, picked["powers"])
    used_ps = set(picked["powersets_used"])
    pools_used = [ps for ps in g["pools"] if ps in used_ps]
    epic_used = next((ps for ps in g["epics"] if ps in used_ps), None)
    inc_full = {s: v.get("full_name") for s, v in picked["incarnates"].items()}

    _enrich_solver_powers(picked["powers"])
    _attach_base_dmg(picked["powers"], ctx)
    # Support build (buff/debuff primary like Kinetics) → ensure the buffing role is
    # on, so the solver recharge/accuracy-slots the signature buffs (which accept no
    # IO sets) while the goal's survival targets still get solved with the rest.
    if (g["label_of"].get(primary, primary).lower() in ai_build.SUPPORT_SETS
            or g["label_of"].get(secondary, secondary).lower() in ai_build.SUPPORT_SETS):
        if "buffing" not in roles:
            roles = roles + ["buffing"]
        # the support set's own buffs are the priority for slot reservation (over
        # generic recharge clicks like Hasten)
        sup = {s for s in (primary, secondary)
               if g["label_of"].get(s, s).lower() in ai_build.SUPPORT_SETS}
        for p in picked["powers"]:
            p["_buff_priority"] = p.get("powerset_full_name") in sup

    tiers = []
    # 67 ADDITIONAL slots beyond each power's free base slot (in-game rule).
    slot_cap = 67 + len(picked["powers"])
    for tier in ai_build.TIER_ORDER:
        _pw = copy.deepcopy(picked["powers"])
        for _sched_round in range(2):
            sol = solver.solve_ilp(copy.deepcopy(_pw), targets,
                                   SETS_BY_CATEGORY, engine.PIECE_GLOBALS,
                                   dict(base), slot_cap=slot_cap, tier=tier, roles=roles, pvp=pvp,
                                   archetype=archetype, **_at_solve_phys(archetype))
            # Pick order must fit the slot schedule (a 49 pick holds at most 4 slots) —
            # if it can't be repaired by reordering, cap the tail and re-solve once.
            if _assign_pick_levels(sol["powers"], archetype) or _sched_round == 1:
                break
            caps = _sched_budget_caps(sol["powers"])
            if not caps:
                break
            for p in _pw:
                if p["full_name"] in caps:
                    p["_sched_budget"] = min(caps[p["full_name"]], p.get("_sched_budget") or 6)
        resolved = {"powers": sol["powers"]}
        _fill_slot_images(resolved)
        final = engine.calculate_build(
            {"archetype": archetype, "powers": sol["powers"],
             "incarnates_full": inc_full, "pvp": pvp},
            SET_BONUSES, res_cap=res_cap, ctx=ctx)
        tiers.append({
            "ok": True, "tier": tier, "tier_meta": ai_build.TIER_META.get(tier, {}),
            "archetype": archetype, "primary": primary, "secondary": secondary,
            "powers": sol["powers"], "incarnates": picked["incarnates"],
            "pools_used": pools_used, "epic_used": epic_used,
            "summary": picked["summary"], "warnings": picked["warnings"],
            "totals": final, "slots_used": sol["slots_used"],
            "report": _solve_report(targets, final)})
    return jsonify({"ok": True, "goal": goal, "archetype": archetype,
                    "primary": primary, "secondary": secondary,
                    "targets": targets, "tiers": tiers, "roles": roles, "pvp": pvp,
                    "power_count": len(picked["powers"])})


@app.route("/ai/refine-build", methods=["POST"])
def ai_refine_build():
    gate = _ai_gate()
    if gate:
        return gate
    """Optimize an existing build toward the goal: compute its totals, feed them
    back to Claude, return a refined build. Runs only on demand (one pass)."""
    body = request.get_json(force=True) or {}
    archetype = body.get("archetype")
    primary = body.get("primary")
    secondary = body.get("secondary")
    goal = (body.get("goal") or "").strip()
    tier = body.get("tier") or "balanced"
    build = body.get("build") or {}
    if not (archetype and primary and secondary and goal and build.get("powers")):
        return jsonify({"ok": False, "response": "Need a current build (with "
                        "powers), archetype, primary, secondary, and a goal."}), 400

    g = _gen_context(archetype, primary, secondary)
    at = g["at"]
    rescap = round(at["res_cap"] * 100, 1) if at else engine.RESISTANCE_HARD_CAP
    totals1 = engine.calculate_build(
        {"archetype": archetype, "powers": build["powers"]},
        SET_BONUSES, res_cap=rescap, ctx=_stat_ctx(archetype))
    cur = {
        "powers": [{"display_name": p.get("display_name") or p.get("full_name"),
                    "slotCount": len(p.get("slots") or []),
                    "slots": p.get("slots") or []} for p in build["powers"]],
        "incarnates": {k: {"display_name": v}
                       for k, v in (build.get("incarnates") or {}).items()},
    }
    focus = body.get("focus") or ai_build.interpret_goal(goal)["focus"]
    rprompt = ai_build.refine_prompt(
        g["at_display"], g["label_of"].get(primary, primary),
        g["label_of"].get(secondary, secondary), goal, cur, totals1,
        g["powers_grouped"], g["inc_slots_prompt"], tier=tier, focus=focus)
    res = claude_bridge.run_prompt(rprompt, timeout=540)
    if not res["ok"]:
        return jsonify({"ok": False, "response": res["response"]})
    try:
        cjson = ai_build.extract_json(res["response"])
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False,
                        "response": f"Claude returned non-JSON: {e}",
                        "raw": res["response"][:2000]})
    resolved = ai_build.resolve_build(cjson, g["power_index"], SET_BY_NAME,
                                      CAT_BY_ID, g["inc_index"], COMMON_IO_MAP)
    _fill_slot_images(resolved)
    resolved["ok"] = True
    resolved["refined"] = True
    resolved["tier"] = tier
    resolved["totals_before"] = ai_build.totals_summary(totals1)
    resolved["archetype"] = archetype
    resolved["primary"] = primary
    resolved["secondary"] = secondary
    used = set(resolved["powersets_used"])
    resolved["pools_used"] = [ps for ps in g["pools"] if ps in used]
    resolved["epic_used"] = next((ps for ps in g["epics"] if ps in used), None)
    return jsonify(resolved)


# ---------------------------------------------------------------------------
# Auto power-picker: choose a sensible, LEGAL ~24-power selection for an AT +
# primary/secondary + role/exposure/content, so "Respec 50" and "Start new" can
# produce a build the solver then optimizes. Heuristic v1 (not provably optimal):
# core primary/secondary by role priority + prereq-valid pool packages by
# exposure/role + a content-fitting epic, assigned legal pick levels.
# ---------------------------------------------------------------------------
_PICK_LEVELS = [1, 1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32,
                35, 38, 41, 44, 47, 49]   # the 24 power picks, by character level
_POOL_PACKAGES = {   # prereq-valid sequences (full_names resolved defensively)
    "fighting":   ["Pool.Fighting.Boxing", "Pool.Fighting.Tough", "Pool.Fighting.Weave"],
    "recharge":   ["Pool.Speed.Hasten"],
    "leaping":    ["Pool.Leaping.Combat_Jumping"],
    "leadership": ["Pool.Leadership.Defense", "Pool.Leadership.Tactics", "Pool.Leadership.Assault"],
}
# Travel power — ALWAYS taken EARLY (L4). Taken late it's gone the moment you exemplar
# into an old Task Force, leaving you running everywhere. All are available at L4.
_TRAVEL = {"super_speed": "Pool.Speed.Super_Speed", "fly": "Pool.Flight.Fly",
           "teleport": "Pool.Teleportation.Teleport", "super_jump": "Pool.Leaping.Long_Jump"}


_CONTROL_CATS = {"holds", "confuse", "immobilize", "sleep", "stuns", "disorient", "fear", "knockback"}


def _power_class(p):
    accepts = {t.lower() for t in (p.get("accepted_enhancement_types") or [])}
    setcats = {c.lower() for c in (p.get("accepted_set_categories") or [])}
    return {"atk": bool(p.get("is_attack")),
            "armor": (p.get("power_type") == 2 and not p.get("is_attack")
                      and ("resist damage" in accepts or "defense buff" in accepts)),
            # SUPPORT = any non-attack power in a dedicated buff/debuff powerset (Empathy, Kinetics,
            # Dark Miasma…) OR one carrying buff/debuff effects. Powerset is the reliable signal:
            # a pure heal / regen / recovery / mez-protect buff (Healing Aura, Recovery Aura, Clear
            # Mind) often LACKS buff_effects, so effect-flags alone misclassify it as filler — which
            # is how a healer's signature auras get out-prioritised by the secondary's blasts.
            "support": (not p.get("is_attack")
                        and (bool(p.get("buff_effects") or p.get("debuff_effects"))
                             or _is_support_powerset(p.get("powerset_full_name")))),
            "control": bool(setcats & _CONTROL_CATS),   # accepts a control set = it's a control power
            "pet": bool(p.get("summons"))}


# Damage-BUFF support — the data files these outside buff_effects (Siphon Power's boost
# is in debuff_effects; Build Up/Soul Drain in self ToHit), so detect by name. These are
# DPS enablers, not generic support — a damage build must not drop them. Exact last-
# segment match (avoids "Barrage" attacks); _ps_priority only sees primary/secondary so
# inherent "Rage_Buff" / IO sets never reach here.
_DMG_ENABLER_NAMES = {"build_up", "build_momentum", "aim", "soul_drain", "spirit_drain",
                      "fiery_embrace", "against_all_odds", "follow_up", "rage", "siphon_power",
                      "fulcrum_shift", "power_build_up", "power_boost", "power_build_up"}


def _ps_priority(p, role, exposure, content=None):
    c = _power_class(p)
    s, front = 1.0, exposure == "front"   # baseline: most powerset powers are worth taking
    if p["full_name"].split(".")[-1].lower() in _DMG_ENABLER_NAMES:
        s += 9 if role in ("damage", "tank") else 6   # Fulcrum/Build Up/Soul Drain: core to anything that deals damage
    if role in ("controller", "control", "debuffer"):
        if c["control"]:
            setcats = {x.lower() for x in (p.get("accepted_set_categories") or [])}
            robust = bool(setcats & {"holds", "immobilize", "stuns", "confuse"})
            fragile = bool(setcats & {"sleep", "fear"}) and not robust
            # A Sleep/Fear control is ROBUST solo but on a TEAM/iTrial the first AoE/PBAoE undoes it
            # — keep it pickable as an alpha-absorb opener, but don't rank it with the holds/confuse
            # that survive damage. Robust control IS the kit; fragile control is a situational opener.
            s += 5 if (fragile and content in ("itrial", "team")) else 9
        if c["pet"]: s += 9        # the PET (Fly Trap, Singularity, Jack Frost…) is a top-tier
                                   # controller power — huge sustained damage + control. NEVER skip it.
        if c["support"]:
            s += 8                 # debuffs/buffs (Poison, Rad, etc.)
            if p.get("power_type") == 2:
                s += 3             # a CONSTANT debuff/buff AURA toggle (Venomous Gas, Radiation
                                   # Infection, Darkest Night) is always-on role OUTPUT — the masters
                                   # ALWAYS take it; rank it above click buffs/debuffs/heals.
            if p.get("heal_effects"):
                s += 2             # a RELIABLE heal (Radiant Aura) must outrank situational
                                   # clicks (Fallout needs a DEAD teammate) when picks get tight
                                   # — the sweep caught 4 combos taking Fallout over the heal.
        if c["atk"]: s += 3
        if c["armor"]: s += 3
    elif role in ("buffer", "healer"):
        # EVERY power in a support PRIMARY (Empathy, Pain Dom, etc.) serves the role — the heals
        # AND the auras/Clear Mind/Resurrect. Don't rely on effect-flags alone: a pure heal/regen/
        # recovery/mez-protect buff often lacks `buff_effects`, so it'd score as filler and get cut
        # BELOW the secondary blasts (exactly how a healer ends up missing Recovery/Regen Aura).
        if c["support"] or _is_support_powerset(p.get("powerset_full_name")):
            s += 10
            if p.get("power_type") == 2:
                s += 3             # constant debuff/buff AURA toggle = always-on role output
        if c["pet"]: s += 9
        if c["atk"]: s += 3
        if c["armor"]: s += 7 if front else 3
    elif role == "tank":
        if c["armor"]: s += 10
        if c["atk"]: s += 5
        if c["support"]: s += 3
    else:  # damage
        if c["atk"]: s += 9
        if c["pet"]: s += 9
        if c["armor"]: s += 6 if front else 3
        if c["support"]: s += 2
        # -RES IS DAMAGE (v12+ physics: it multiplies the whole team's output including your
        # own) - a damage-role Corruptor skipping Freezing Rain/Melt Armor was the sweep's
        # debuff_blind cluster (Storm/Thermal/Marine). Rank spawn-wide -res debuffs with
        # the attacks they amplify.
        if c["support"] and any((d.get("effect") == "Resistance")
                                for d in (p.get("debuff_effects") or [])):
            s += 6
    # RANGE × EXPOSURE (real geometry): a damage dealer prioritises attacks at the distance it
    # fights from. Gentle nudge — reorders filler, won't drop a signature nuke. Mostly matters
    # for mixed-range kits (a Blaster's melee/PBAoE secondary: blapper-front takes it, backline
    # skips it). Same-range primaries (all-melee Brute) get a uniform shift = no-op.
    if role in ("damage", "tank") and c["atk"] and exposure in ("front", "back"):
        sh = _power_shape(p)
        if exposure == "front":                       # melee / point-blank
            if sh["pbaoe"] or sh["melee"] or sh["cone"]:
                s += 3                                # close-range = your bread & butter up close
            elif sh["ranged"] and not sh["aoe"]:
                s -= 2                                # pure ranged single-target = filler in melee
        else:                                         # back / ranged
            if sh["ranged"] and not (sh["pbaoe"] or sh["melee"]):
                s += 3                                # ranged attack = stay at distance
            elif sh["melee"] and not sh["aoe"]:
                s -= 3                                # melee single-target = you'd have to dive in
    return s


# Ranking epic/ancillary ATTACKS for an offense build. A master TW/Fire takes Melt Armor
# (-res/-def: force-multiplies the WHOLE spawn) + Fire Ball (AoE nuke) from Pyre Mastery —
# NOT Ring of Fire + Char (single-target control), which is what blind powerset-order gives.
_EPIC_DEBUFF_CATS = {"Defense Debuff", "Accurate Defense Debuff",
                     "To Hit Debuff", "Accurate To-Hit Debuff"}
_EPIC_CTRL_CATS = {"Immobilize", "Holds", "Stuns", "Sleep", "Confuse", "Fear"}
_EPIC_ST_DMG_CATS = {"Ranged Damage", "Melee Damage", "Universal Damage"}


def _epic_atk_score(p):
    cats = set(p.get("accepted_set_categories") or [])
    sc = 0.0
    if engine.is_aoe(p) and p.get("damage_effects"):  sc += 12  # AoE nuke (real geometry × damage)
    if cats & _EPIC_DEBUFF_CATS:    sc += 10   # Melt Armor: -res/-def multiplies spawn-wide damage
    if cats & _EPIC_ST_DMG_CATS:    sc += 4    # any single-target damage
    if cats & _EPIC_CTRL_CATS:      sc -= 5    # single-target control (Ring of Fire/Char) = poor dmg pick
    return sc


def _power_res_debuff(rec):
    """Magnitude of a power's -Resistance debuff (per type, uniform across types) — the
    spawn-wide DAMAGE multiplier. Melt Armor / Tar Patch = 3, Arctic Breath = 1.5, else 0."""
    return max([-(d.get("scale") or 0) for d in (rec.get("debuff_effects") or [])
                if d.get("effect") == "Resistance" and (d.get("scale") or 0) < 0], default=0.0)


def _epic_power_value(rec, exposure="flex"):
    """Melee-DPS value of an epic power. A FRONT-LINE brute fires AoEs from inside the spawn
    and force-multiplies it with -Res (Melt Armor / Tar Patch) — it gets ~nothing from a ranged
    SINGLE-TARGET blast (Dark Blast, Mu Lightning). So AoE + -Res rank high; ranged-ST is
    downranked hard for `front`; single-target control is a poor offense pick."""
    cats = set(rec.get("accepted_set_categories") or [])
    sc = 0.0
    is_aoe = engine.is_aoe(rec) and bool(rec.get("damage_effects"))   # AoE DAMAGE (real geometry)
    if is_aoe:
        sc += 12                                   # AoE nuke / cone — spawn clear from melee
    res = _power_res_debuff(rec)
    if res > 0:
        sc += 4 + 3 * min(res, 3)                  # -Res = spawn-wide dmg multiplier (Melt Armor 13, Tar Patch 13)
    elif cats & {"Defense Debuff", "Accurate Defense Debuff"}:
        sc += 4                                    # -Def only: helps the team land hits
    if (cats & _EPIC_ST_DMG_CATS) and not is_aoe:  # single-target damage
        sc += 1 if (exposure == "front" and "Ranged Damage" in cats) else 4
    if cats & _EPIC_CTRL_CATS:
        sc -= 5                                     # single-target control = weak offense pick
    return sc


# Epic value for a control/debuff/buff role: the pick must ADD A LAYER of the role — another ROBUST
# hold, a -Res/-Def/-ToHit debuff, or Power Boost (amplifies every debuff magnitude + control
# duration) — NOT damage. Fragile Sleep/Fear control is downranked (one team AoE undoes it).
_SUPPORT_EPIC_ROLES = {"controller", "control", "dominator", "debuffer", "buffer", "healer", "support"}
_EPIC_BOOST_NAMES = {"power_boost", "power_build_up", "power_buildup"}


def _epic_support_value(rec):
    cats = set(rec.get("accepted_set_categories") or [])
    nm = (rec.get("full_name") or "").split(".")[-1].lower()
    sc = 0.0
    if nm in _EPIC_BOOST_NAMES:
        sc += 16                                    # Power Boost — multiplies the whole debuff/control kit
    res = _power_res_debuff(rec)
    if res > 0:
        sc += 6 + 3 * min(res, 3)                   # -Res patch = spawn-wide damage layer
    if cats & {"Defense Debuff", "Accurate Defense Debuff", "To Hit Debuff", "Accurate To-Hit Debuff"}:
        sc += 8                                     # -Def / -ToHit debuff layer
    if cats & {"Holds", "Immobilize", "Stuns", "Confuse"}:
        sc += 9                                     # ROBUST control layer (survives team AoE)
    if cats & {"Sleep", "Fear"}:
        sc -= 3                                     # FRAGILE control — one AoE undoes it
    _types = {t.lower() for t in (rec.get("accepted_enhancement_types") or [])}
    if rec.get("power_type") == 2:
        if "defense buff" in _types:
            sc += 22   # a DEFENSE toggle (Scorpion Shield) — the squishy's SOFTCAP KEYSTONE: with
                       # Weave + Maneuvers + set bonuses it carries a controller to the def softcap
        elif "resist damage" in _types:
            sc += 6    # a resistance toggle — survival, but doesn't unlock the positional softcap
    return sc


def _epic_has_def_toggle(ps):
    """True if the epic pool offers a DEFENSE toggle (Scorpion Shield / Charged Armor-def / Frozen
    Armor …) — the keystone that lets a squishy reach the defense softcap."""
    for p in (POWERS.get(ps) or []):
        if p.get("power_type") == 2 and "defense buff" in {
                t.lower() for t in (p.get("accepted_enhancement_types") or [])}:
            return True
    return False


def _pick_epic(archetype, content, role="damage", exposure="flex"):
    by_at = POWERSETS["by_archetype"].get(archetype) or {}
    epics = [e["full_name"] for e in by_at.get("epic", [])]
    if not epics:
        return []
    # "pyre" added so a fire farmer's Pyre Mastery matches (the set name has no "fire"/"flame").
    pref = {"fire_farm": ("flame", "fire", "pyre"), "av": ("dark", "soul", "mu", "elec"),
            "itrial": ("dark", "soul", "elec")}.get(content, ())
    offense = role in ("damage", "tank") or content == "fire_farm"
    # Control/debuff/buff role: pick the epic for the LAYER it adds (robust hold, -res/-def/-tohit,
    # Power Boost), not damage. _epic_support_value scores that; offense path is unchanged.
    support = role in _SUPPORT_EPIC_ROLES and content != "fire_farm"
    val = (lambda p: _epic_support_value(p)) if support else (lambda p: _epic_power_value(p, exposure))

    def parts(ps):
        powers = POWERS.get(ps) or []
        armor = [p for p in powers if _power_class(p)["armor"]]   # real res/def toggle, not a stun aura
        # Payloads = attacks/debuffs (offense) OR debuff+control LAYER powers (support), found by value.
        offs = [p for p in powers if p.get("is_attack") or val(p) >= 8]
        return armor, offs

    def pool_score(ps):
        armor, offs = parts(ps)
        best = sorted((val(p) for p in offs), reverse=True)
        sc = sum(best[:2])                                      # the pool's best two payloads (for the role)
        if support:
            # A DEFENSE-toggle epic is the squishy's survival KEYSTONE (Scorpion Shield → def softcap
            # with Weave/Maneuvers/set bonuses) — weight it ABOVE the content theme; a -tohit theme
            # matters far less than reaching the softcap. The debuff/control layers (best[:2]) ride along.
            sc += 45 if _epic_has_def_toggle(ps) else (10 if armor else 0)
            sc += 10 if any(k in ps.lower() for k in pref) else 0
        else:
            sc += 25 if armor else 0                            # a res/def epic armor = survivability
            sc += 40 if any(k in ps.lower() for k in pref) else 0   # content theme — strong nudge, not absolute
        return sc
    ps = max(epics, key=pool_score)
    armor, offs = parts(ps)
    # Offense builds: rank payloads by melee value (AoE + -Res > -Def > single-target; ranged-ST
    # near-worthless to a front-liner). Support builds: rank by the debuff/control LAYER added
    # (robust hold + -res/-def/-tohit + Power Boost first), so a controller gets Petrifying Gaze +
    # the -tohit AoE, not a single-target blast.
    if offense or support:
        offs = sorted(offs, key=val, reverse=True)
    take = (armor[:1] + offs[:2]) if role != "tank" else (armor[:2] + offs[:1])
    seen, uniq = set(), []                                      # a payload can also be the armor — de-dup
    for p in take:
        if p["full_name"] not in seen:
            seen.add(p["full_name"]); uniq.append(p)
    take = uniq
    # LEGALITY: epic/ancillary pools are a tier ladder — T1-2 free, T3-4 need ONE other
    # power from the pool, only the top T5 (the pets: Ice Elemental, Summon Spiderlings…)
    # needs TWO. Keep prepending the best still-legal lower-tier power until every pick's
    # prerequisite count is satisfied.
    allp = POWERS.get(ps) or []
    if allp and take:
        tiers = _pool_tiers(ps)

        def _needs(fn):
            return _epic_prereq_count(tiers.get(fn, 0))

        for _ in range(4):                    # at most a few gateways ever needed
            max_need = max((_needs(q["full_name"]) for q in take), default=0)
            if len(take) - 1 >= max_need:
                break
            have = {q["full_name"] for q in take}
            # candidates whose own prerequisite is already met by the current picks
            entries = [q for q in allp if q["full_name"] not in have
                       and _needs(q["full_name"]) <= len(take)]
            if not entries:
                break
            entries.sort(key=lambda q: (tiers.get(q["full_name"], 0),
                                        -_epic_power_value(q, exposure), q["full_name"]))
            take = [entries[0]] + take
    return [(p["full_name"], p.get("level_available") or 35) for p in take]


def _champion_picks(archetype, primary, secondary, content, form=None):
    """If the deep optimizer has a CONVERGED-knowledge champion for this context, return it as the
    pick list (with legal pick levels) — the buttonless delivery of the learning loop: what the
    frontier chain proved best simply becomes what autopick proposes. Returns None if no champion
    (or it fails current legality/data checks) — the heuristic proposer then runs as usual.
    `form` (Joel's per-form Kheldian route, 2026-07-12): dwarf/nova serves that
    form's own champion — the build a player who wants that form bases theirs on."""
    try:
        import learn as _learn
        champ = _learn.load_champion(archetype, primary, secondary, content, form)
    except Exception:  # noqa: BLE001
        return None
    if not champ or not all(fn in POWER_BY_FULL for fn in champ):
        return None
    real = [fn for fn in champ if not fn.startswith("Inherent")]
    if not _picks_legal(set(real), primary, secondary):
        return None
    # Champions predating the creation rule may lack a level-1 pick from one of the
    # sets (one of each set's first two is FORCED at creation) — those can't be
    # seated legally; fall back to the heuristic, which injects the required pair.
    if leveling_schedule.eat_type(archetype) is None:
        for want in (primary, secondary):
            first2 = _set_first_two(want)
            if first2 and not (set(first2) & set(real)):
                return None
    out = [{"full_name": fn, "pick_level": 1} for fn in champ if fn.startswith("Inherent")]
    slots = list(_PICK_LEVELS)
    # L1 rule first (one primary + one secondary), then greedy by availability.
    ordered = sorted(real, key=lambda fn: (POWER_BY_FULL[fn].get("level_available") or 1))
    for want in (primary, secondary):
        fn = next((f for f in ordered if f.rsplit(".", 1)[0] == want
                   and (POWER_BY_FULL[f].get("level_available") or 1) <= 1), None)
        if fn and slots:
            out.append({"full_name": fn, "pick_level": slots.pop(0)})
            ordered.remove(fn)
    for fn in ordered:
        lv = POWER_BY_FULL[fn].get("level_available") or 1
        i = next((j for j, sl in enumerate(slots) if sl >= lv), None)
        if i is None:
            return None                       # can't seat legally — fall back to the heuristic
        out.append({"full_name": fn, "pick_level": slots.pop(i)})
    return out


def _auto_pick_powers(archetype, primary, secondary, role="damage",
                      exposure="flex", content="general", travel="super_speed",
                      form=None):
    # Default to the ARCHETYPE's role (same map the tray uses), not a blanket "damage" — a
    # Defender/Corruptor/MM picked with no explicit role must build support, not a blaster.
    role = role or _AT_DEFAULT_ROLE.get(archetype, "damage")
    # Deep-optimizer knowledge, delivered buttonlessly: if the frontier chain has a champion for
    # this context, propose THAT selection (Solve still slots it for the chosen role/goal).
    # A Kheldian FORM choice serves that form's champion; no champion for the
    # form yet → the heuristic runs and the UI says the champion is coming.
    champ = _champion_picks(archetype, primary, secondary, content, form)
    if champ:
        return champ
    is_ctrl = role in ("controller", "control", "debuffer")
    # Epic ATs (Kheldians + Arachnos Soldiers/Widows) are self-sufficient ARMORED hybrids: their
    # masters all run the DEFENSE pools (Fighting=Weave, Leadership=Maneuvers) to softcap POSITIONAL
    # defense and home 5× Luck of the Gambler (+global recharge). Treated as plain "damage" they'd
    # skip both and collapse on positional def (crab ranged def 12 vs master 38). Force the pools in.
    is_eat = archetype in _EPIC_ATS
    # A SQUISHY AT (no armor set — Blaster/Controller/Defender/Corruptor/Dominator/Mastermind) has
    # NO defensive powerset, so its ONLY positional defense is the pool STACK (Fighting=Weave +
    # Leadership=Maneuvers + Combat Jumping) plus set bonuses — which is exactly what the masters run
    # (a master Fire/Fire Blaster stacks Tough/Weave + Maneuvers). Treated as plain "damage" the tool
    # took neither and collapsed to ~4% def vs masters' 20-25%. Force the def pools in for squishies.
    is_squishy = (archetype not in _ARMORED_ATS) and not is_eat
    # Candidate pool packages in PRIORITY order — leaping (just Combat Jumping) is LAST so
    # it's the first dropped when we hit the 4-pool cap.
    pkgs = []
    # Fighting (Tough/Weave) is UNIVERSAL master practice — armored melee too (the sweep
    # found Scrapper/Stalker/Sentinel stopping at 23/24 picks with no Fighting pool while
    # every master melee build runs Tough+Weave). The 4-pool cap below still prunes.
    pkgs.append("fighting")
    pkgs.append("recharge")              # Hasten — near-universal
    if role in ("buffer", "healer") or is_ctrl or is_eat or is_squishy:
        pkgs.append("leadership")        # team auras (Maneuvers/Tactics); squishy/EAT = positional def + LotG
    pkgs.append("leaping")               # Combat Jumping — cheap LotG mule, lowest priority
    # KHELDIANS travel INNATELY (Energy Flight @1 / Shadow Step @1, Combat Flight @10) —
    # a pool travel power is redundant by default; taking one anyway is an explicit choice
    # (travel="fly" etc. from the UI). travel="none" always means no pool travel.
    if archetype in ("Class_Peacebringer", "Class_Warshade") and travel in (None, "", "default"):
        travel = "none"
    if travel == "none":
        travel_fn = None
    else:
        tfn = _TRAVEL.get(travel or "super_speed", _TRAVEL["super_speed"])
        travel_fn = tfn if tfn in POWER_BY_FULL else None

    # CoH allows AT MOST 4 power pools. Count the travel pool first, then keep packages in
    # priority order until 4 distinct pools are used. A package that SHARES the travel pool
    # (e.g. Hasten/recharge when travelling by Super Speed = both Speed pool) costs nothing.
    def _pool_of(fn):
        return fn.split(".")[1] if fn and fn.startswith("Pool.") else None
    pools_used = set()
    if travel_fn:
        pools_used.add(_pool_of(travel_fn))
    kept_pkgs = []
    for pk in pkgs:
        pp = _pool_of(_POOL_PACKAGES[pk][0])
        if pp in pools_used or len(pools_used) < 4:
            pools_used.add(pp)
            kept_pkgs.append(pk)
    # Each kept pool is a PREREQ CHAIN (Boxing→Tough→Weave, Maneuvers→Tactics→Assault).
    # Assign effective levels that STRICTLY INCREASE down the chain so the greedy placer
    # can never seat a dependent (Tough/Weave) before its prerequisite (Boxing).
    pool_lvl = {}
    for pk in kept_pkgs:
        prev = 0
        for fn in _POOL_PACKAGES[pk]:
            if fn not in POWER_BY_FULL:
                continue
            lv = max(POWER_BY_FULL[fn].get("level_available") or 1, prev + 1)
            pool_lvl[fn] = lv
            prev = lv
    pool = list(pool_lvl.items())

    epic = _pick_epic(archetype, content, role, exposure)
    reserved = (1 if travel_fn else 0)
    budget = max(0, 24 - len(pool) - len(epic) - reserved)
    # THE PROPOSER LEARNS (retrospective feedback loop): lessons from every converged deep run —
    # "the search had to ADD X / DROP Y that I proposed" — adjust the heuristic ranking, so the
    # misses of past searches make future SEEDS start closer to proven optima. ±8 at full vote
    # strength: flips close calls, can't override the structural factors.
    try:
        import learn as _learn
        import first_principles as _fp
        _adj = _learn.seed_adjustments(archetype, primary, secondary, content,
                                       model_version=_fp.MODEL_VERSION)
    except Exception:  # noqa: BLE001
        _adj = {}
    cand = []
    for ps in _veat_accessible_sets(primary, secondary):
        for p in (POWERS.get(ps) or []):
            pri0 = _ps_priority(p, role, exposure, content) \
                + 8.0 * _adj.get(p.get("power_name") or "", 0.0)
            cand.append((pri0, p.get("level_available") or 1, p["full_name"]))
    cand.sort(key=lambda x: (-x[0], x[1]))
    psfns = [(fn, lvl) for (_, lvl, fn) in cand[:budget]]
    # EXEMPLAR-FRIENDLY: front-load TRAVEL (gone = running everywhere) + any primary/secondary
    # armor toggle at its earliest slot. POOL armor (Tough/Weave) is NOT front-loaded — its
    # order is fixed by the prereq-chain effective levels above (front-loading it was exactly
    # what put Weave/Tough ahead of Boxing). Everything else fills by level.
    allp = psfns + pool + epic
    early = [(travel_fn, POWER_BY_FULL[travel_fn].get("level_available") or 4)] if travel_fn else []
    early += [(fn, lvl) for (fn, lvl) in psfns if _power_class(POWER_BY_FULL.get(fn) or {})["armor"]]
    # Front-load the FIGHTING survival chain (Boxing→Tough→Weave) so it clusters early for
    # exemplaring — using the chain's effective levels keeps Boxing ahead of Tough/Weave.
    early += [(fn, pool_lvl[fn]) for fn in pool_lvl if _pool_of(fn) == "Fighting"]
    # PROTECT THE EPIC/PATRON PICKS from downstream truncation. _pick_epic returns a set that
    # is legal AS A WHOLE (each power's tier prerequisite satisfied by its siblings). On a
    # power-dense AT (VEATs carry many inherent/branch powers) the greedy level-ordered fill
    # below can run out of high pick-slots before a high-tier epic (e.g. Widow Arctic_Breath at
    # L41) is seated — orphaning a lower-tier sibling that then fails its own prereq. Seating
    # epics with the early batch guarantees the legal set survives intact.
    early += [(fn, lvl) for (fn, lvl) in epic]
    early_set = {fn for fn, _ in early}
    rest = [(fn, lvl) for (fn, lvl) in allp if fn not in early_set]

    out, slots, placed = [], list(_PICK_LEVELS), set()

    def place(fn, lvl):
        if fn in placed:
            return
        for i, sl in enumerate(slots):
            if sl >= lvl:
                out.append({"full_name": fn, "pick_level": sl})
                slots.pop(i); placed.add(fn); return

    # CoH rule: level 1 grants exactly ONE primary + ONE secondary power — you can never
    # spend both level-1 picks on the primary. Seat the highest-priority level-1 pick from
    # EACH set into the two L1 slots FIRST (psfns is already in priority order), so the
    # greedy fill below can't hand both L1 slots to the primary (an illegal in-game order).
    for ps in (primary, secondary):
        _ok = {ps, _VEAT_BASE_SET.get(ps)} - {None}
        best = next((fn for (fn, lvl) in psfns
                     if (POWER_BY_FULL.get(fn) or {}).get("powerset_full_name") in _ok
                     and ((POWER_BY_FULL.get(fn) or {}).get("level_available") or 1) <= 1),
                    None)
        if not best:
            # The creation pick is NOT optional: the game forces one of the set's first
            # two powers at level 1 (field report: a debuffer kit skipped both Sonic T1
            # blasts entirely, so nothing legal could sit at level 1). Inject the
            # better-scoring of the pair even though the priority list passed on it.
            pair = [fn for s in _ok for fn in _set_first_two(s) if fn in POWER_BY_FULL]
            pair.sort(key=lambda fn: -_ps_priority(POWER_BY_FULL[fn], role, exposure, content))
            best = pair[0] if pair else None
        if best:
            place(best, 1)
    for fn, lvl in sorted(early, key=lambda x: x[1]):
        place(fn, lvl)
    for fn, lvl in sorted(rest, key=lambda x: x[1]):
        place(fn, lvl)
    # FILL TO CAP (sweep fix): a level-50 character owns 24 picks — if the priority lists
    # ran dry with pick levels left over, fill them with the best legal leftovers (rest of
    # the epic set, spare primary/secondary powers, tier-1 toggles of pools already in use).
    # An unused pick level is never better than a real power.
    if len(placed) < 24:
        fill = []
        epic_sets = {fn.rsplit(".", 1)[0] for fn in placed if fn.startswith("Epic.")}
        for ps in _veat_accessible_sets(primary, secondary) + sorted(epic_sets):
            fill += [q for q in (POWERS.get(ps) or [])
                     if q.get("slottable") and q["full_name"] not in placed]
        for pl in sorted({fn.split(".")[1] for fn in placed if fn.startswith("Pool.")}):
            fill += [q for q in (POWERS.get("Pool." + pl) or [])
                     if q.get("slottable") and q["full_name"] not in placed
                     and (q.get("level_available") or 1) <= 14]   # tier-1/2 only (no prereqs)
        fill.sort(key=lambda q: (q.get("level_available") or 1))
        for q in fill:
            if len(placed) >= 24:
                break
            place(q["full_name"], q.get("level_available") or 1)

    # Inherent FITNESS — Health + Stamina are AUTO-GRANTED (free, don't cost a power pick). A master
    # build SLOTS them: Health = the recovery/regen uniques (Numina / Miracle / Panacea / Preventive
    # Medicine), Stamina = endmod + Performance Shifter / Power Transfer procs. This is the SUSTAIN
    # engine that lets a build LAST a long fight — the tool never included them before. They're
    # appended outside the 24-pick budget; the solver then allocates spare slots + globals to them.
    for fn in ("Inherent.Fitness.Health", "Inherent.Fitness.Stamina"):
        if fn in POWER_BY_FULL and fn not in placed:
            out.append({"full_name": fn, "pick_level": 2})
            placed.add(fn)
    out.sort(key=lambda x: x["pick_level"])
    return out


# ---------------------------------------------------------------------------
# POWER TRAY LAYOUT — arrange a build's powers into the in-game 4-row trays,
# the way a player actually keeps them: Tray 1 = the active rotation (ordered
# left→right as a sensible cast sequence), Tray 2 = always-on toggles + main
# travel, Tray 3 = situational buffs + travel/zone macros, Tray 4 = movement +
# emotes. Each slot carries a TYPE glyph (Tabler icon) since the tool has no
# in-game power-icon assets. Suggested macros (e.g. a league low-FX toggle) are
# added to trays 3 and 4 as non-power entries.
# ---------------------------------------------------------------------------
_TRAVEL_MAIN = {"Fly", "Super_Speed", "Super_Jump", "Long_Jump", "Teleport",
                "Mystic_Flight", "Speed_of_Sound", "Mighty_Leap", "Infiltration"}
_TRAVEL_EXTRA = {"Hover", "Afterburner", "Combat_Teleport", "Evasive_Maneuvers",
                 "Jaunt", "Translocation", "Group_Fly"}
_SPRINTS = {"Sprint", "Walk", "Ninja_Run", "Beast_Run", "Athletic_Run"}
# "Hard" control = the mez types that DEFINE a control power. Excludes Stuns/Knockback,
# which damaging attacks accept as a rider (so Boxing/Umbral Torrent stay attacks).
_HARD_CTRL = {"holds", "confuse", "immobilize", "sleep", "fear"}
_TRAY_MACROS = {  # (label, hover, glyph) — utility/macros, not powers in the build
    3: [("Low FX", "macro LowFX:  maxParticles 500 $$ suppressCloseFx 1  — cut league "
         "visual noise so the client doesn't choke and you can see the target", "ti-eye"),
        ("Full FX", "macro FullFX:  restore particle count + close FX", "ti-eye-off"),
        ("Rest", "Rest — parked at the end of the set-and-forget tray, next to the "
         "recovery clicks (community convention)", "ti-bed")],
    4: [("Base TP", "macro — Base Teleport", "ti-building-arch"),
        ("LRT", "Long Range Teleporter", "ti-map-pin"),
        ("Team TP", "Assemble the Team / Mission Teleporter", "ti-users-group"),
        ("Emote", "emote macro", "ti-mood-smile"),
        ("Insp", "inspiration-combine macro", "ti-pill")],
}
_INC_TRAY = {  # incarnate slot -> (tray, glyph); Alpha/Interface are passive (skip)
    "Destiny": (3, "ti-sparkles"), "Judgement": (1, "ti-flame"),
    "Hybrid": (2, "ti-shield-bolt"), "Lore": (3, "ti-paw"),
}


try:
    # DATA_DIR, not __file__-relative: in the packaged exe the data lives under the
    # bundle root, and the __file__-relative path silently loads nothing (no tray icons).
    with open(os.path.join(DATA_DIR, "power_icon_map.json"), encoding="utf-8") as _pif:
        _POWER_ICON_MAP = json.load(_pif)        # full_name -> in-game icon basename
except Exception:                                # noqa: BLE001
    _POWER_ICON_MAP = {}

# Same-power-name fallback: many powers exist in several powersets (Murky Cloud is in Dark
# Armor AND the Dark Mastery epics) but the icon carve only matched some. A power's icon is
# the SAME wherever it appears, so an unmapped copy can borrow the most-common icon of its
# same-named siblings — fixes Murky Cloud / Umbral Torrent (Dark Mastery epics) + ~400 others.
_POWER_ICON_BY_NAME = {}
for _fn, _ic in _POWER_ICON_MAP.items():
    _POWER_ICON_BY_NAME.setdefault(_fn.split(".")[-1], {}).setdefault(_ic, 0)
    _POWER_ICON_BY_NAME[_fn.split(".")[-1]][_ic] += 1
_POWER_ICON_BY_NAME = {pn: max(counts, key=counts.get)
                       for pn, counts in _POWER_ICON_BY_NAME.items()}


def _power_icon_url(fn):
    if not fn:
        return None
    base = _POWER_ICON_MAP.get(fn) or _POWER_ICON_BY_NAME.get(fn.split(".")[-1])
    return ("/static/icons/powers/" + base + ".png") if base else None


def _power_glyph(p, cls):
    """A Tabler icon name representing the power's TYPE."""
    nm = (p.get("full_name") or "").split(".")[-1]
    if nm in _TRAVEL_MAIN or nm in _TRAVEL_EXTRA:
        return "ti-plane" if "Fl" in nm or nm == "Hover" else "ti-run"
    if nm in _SPRINTS or nm.startswith("prestige"):
        return "ti-run"
    if nm == "Hasten":
        return "ti-clock-bolt"
    cats = {c.lower() for c in (p.get("accepted_set_categories") or [])}
    if cls["pet"]:
        return "ti-paw"
    if cls["armor"]:
        return "ti-shield"
    if cats & _HARD_CTRL:       # damaging immobs/holds (Roots, Strangler) are control-first
        return "ti-lock"
    if cls["atk"]:
        return "ti-sword"
    if cls["support"]:
        return "ti-trending-down" if p.get("debuff_effects") else "ti-heart-plus"
    return "ti-flag" if (p.get("power_type") == 2) else "ti-circle"


# Default combat identity per AT when the caller doesn't pass a role — drives the rotation
# ORDER (what an archetype leads with): control ATs open with control for Containment/
# Domination, support ATs with debuffs, everyone else leads with steroids + attacks.
# Default role per archetype — MUST be a role the prioritisers actually handle (see
# _ps_priority / _tray_layout). "support" was an orphan (no branch, no ROLE_PRESETS entry) so it
# silently fell through to the DAMAGE default — a Defender/Corruptor/MM was built like a Blaster.
_AT_DEFAULT_ROLE = {
    "Class_Controller": "control", "Class_Dominator": "control",
    "Class_Defender": "buffer", "Class_Corruptor": "buffer",
    "Class_Mastermind": "buffer",
}

# Epic ATs — self-sufficient armored hybrids whose master builds all run the DEFENSE pools
# (Weave + Maneuvers) for a positional-defense softcap + 5× Luck of the Gambler. The autopicker
# forces those pools for these ATs (see _auto_pick_powers) instead of treating them as glass damage.
_EPIC_ATS = {"Class_Peacebringer", "Class_Warshade",
             "Class_Arachnos_Widow", "Class_Arachnos_Soldier"}

# ── Role STANDARD interpretation ─────────────────────────────────────────────────────
# Role is the ABSOLUTE default standard per archetype. It bends ONLY to an explicit signal —
# the Role picker, or an off-role intent stated in the goal text. The tool ECHOES its
# understanding (standard vs override, and why) BEFORE committing, so the user confirms it
# rather than hoping the solver "gets it".
_ROLE_FRAMING = {
    "buffer":     ("support-first", "buffs & debuffs lead — attacks are a secondary contribution"),
    "support":    ("support-first", "buffs & debuffs lead — attacks are a secondary contribution"),
    "healer":     ("support-first", "heals & team buffs lead — attacks are a secondary contribution"),
    "controller": ("control-first", "lockdown & debuffs lead — procs/attacks are the damage"),
    "control":    ("control-first", "lockdown & debuffs lead — procs/attacks are the damage"),
    "debuffer":   ("debuff-first", "-res/-def/-tohit lead — attacks are a secondary contribution"),
    "damage":     ("offense-first", "attacks lead — survival is the floor"),
    "tank":       ("survival-first", "armor & aggro lead — attacks are secondary"),
}
# Off-role intent in free text — conservative, strong signals only (the confirm step is the net).
_OFFROLE_KEYWORDS = [
    ("damage",     ("damage dealer", "dps", "front line", "front-line", "main damage", "deal damage",
                    "hard hitter", "hard-hitter", "blapper", "nuker", "glass cannon", "kill fast",
                    "offensive", "do damage", "deal more damage")),
    ("tank",       ("tank", "tanker", "soak the alpha", "hold aggro", "aggro magnet", "taunt")),
    ("healer",     ("healer", "pure heal", "healbot", "heal bot", "keep the team alive", "main healer")),
    ("buffer",     ("buff bot", "force multiplier", "team buffs", "support bot", "buffer")),
    ("controller", ("lockdown", "perma-control", "perma control", "lock everything down", "hard control")),
    ("debuffer",   ("debuffer", "resistance debuff", "strip defense", "strip resistance")),
]
# Role families: a same-family pick is a refinement; crossing families is a real override.
_ROLE_FAMILY = {
    "buffer": "support", "support": "support", "healer": "support",
    "controller": "control", "control": "control", "debuffer": "control",
    "damage": "offense", "tank": "survival",
}


def _role_label(role):
    return (ai_build.ROLE_PRESETS.get(role) or {}).get("label", (role or "").title())


def _detect_role_from_text(text):
    """First strong off-role signal in the goal text → (role, matched_phrase), else (None, None)."""
    t = (text or "").lower()
    if not t.strip():
        return None, None
    for role, kws in _OFFROLE_KEYWORDS:
        for kw in kws:
            if kw in t:
                return role, kw
    return None, None


def _interpret_request(archetype, role, primary, secondary, content, goal_text=""):
    """Resolve the governing role (firm AT standard vs an explicit override) and produce a
    plain-language UNDERSTANDING for the user to confirm before any solve commits."""
    at = ARCH_BY_NAME.get(archetype) or {}
    standard = _AT_DEFAULT_ROLE.get(archetype, "damage")
    detected, phrase = _detect_role_from_text(goal_text)
    role = role or None
    # Precedence: explicit Role picker > goal-text declaration > the archetype standard.
    resolved = role or detected or standard
    override = None
    if role and role != standard:
        override = {"by": "the Role picker", "detail": f"you selected the {_role_label(role)} role"}
    elif detected and detected != standard and not role:
        override = {"by": "your goal text", "detail": f"your goal says “{phrase}”"}
    conflict = bool(role and detected and role != detected)   # two signals disagree → user resolves
    lead, framing = _ROLE_FRAMING.get(resolved, _ROLE_FRAMING["damage"])
    is_standard = (override is None) and (resolved == standard)
    # Same-FAMILY deviations (buffer→healer) are refinements; CROSS-family (support→damage) is a
    # true override worth flagging loudly — that's the "front-line damage Defender" the user means.
    cross_family = _ROLE_FAMILY.get(resolved) != _ROLE_FAMILY.get(standard)
    pslabel = " / ".join(s.split(".")[-1].replace("_", " ") for s in (primary, secondary) if s)
    at_label = at.get("display_name") or (archetype or "").replace("Class_", "")
    if is_standard:
        head = (f"\U0001F4CB Building as **{_role_label(resolved)}** — the firm standard for a "
                f"{at_label}. {lead.capitalize()}: {framing}.")
        switch = "Want a different focus? Pick another Role (e.g. Damage) and I'll rebuild to that."
    elif not cross_family:
        head = (f"\U0001F4CB Building as **{_role_label(resolved)}** — your focus within the usual "
                f"{_role_label(standard)} standard for a {at_label}. {lead.capitalize()}: {framing}.")
        switch = f"Prefer the broad {_role_label(standard)} standard? Clear the Role to use it."
    else:
        why = override["detail"] if override else "your selection"
        head = (f"⚠️ Building as **{_role_label(resolved)}** — OVERRIDING the usual "
                f"{_role_label(standard)} standard for a {at_label}, because {why}. "
                f"{lead.capitalize()}: {framing}.")
        switch = f"Not what you meant? Clear the override to return to the {_role_label(standard)} standard."
    return {
        "archetype": archetype, "archetype_label": at_label, "powersets": pslabel,
        "resolved_role": resolved, "role_label": _role_label(resolved),
        "standard_role": standard, "standard_label": _role_label(standard),
        "is_standard": is_standard, "override": override, "conflict": conflict,
        "lead": lead, "framing": framing, "banner": head, "switch_hint": switch,
        "detected_role": detected, "detected_phrase": phrase,
    }


@app.route("/build/interpret", methods=["POST"])
def build_interpret():
    """State the solver's understanding (firm role standard vs override + what it will prioritise)
    BEFORE committing — so the user confirms intent instead of hoping the solver gets it."""
    body = request.get_json(force=True) or {}
    archetype = body.get("archetype")
    if not archetype:
        return jsonify({"ok": False})
    interp = _interpret_request(archetype, body.get("role"), body.get("primary"),
                                body.get("secondary"), body.get("content"),
                                body.get("goal") or body.get("goal_text") or "")
    _at = ARCH_BY_NAME.get(archetype)
    rescap = round(_at["res_cap"] * 100, 1) if _at else engine.RESISTANCE_HARD_CAP
    pre = ai_build.preset_targets(body.get("content"), interp["resolved_role"], res_cap=rescap,
                                  primary=body.get("primary"), secondary=body.get("secondary"),
                                  goal=body.get("goal") or body.get("goal_text"))
    interp["targets_summary"] = _targets_summary(pre["targets"]) if pre else ""
    return jsonify({"ok": True, "interpretation": interp})


# AoE classification lives in engine.is_aoe (real Mids geometry: radius + effect_area). Mids
# eEffectArea: 0 None, 1 Character (single OR PBAoE if radius>0), 2 Sphere, 3 Cone, 4 Location.
_is_aoe = engine.is_aoe


def _power_shape(rec):
    """Authoritative geometry from the Mids data (effect_area/radius/range/arc/max_targets) —
    replaces guessing AoE from accepted set categories. AoE = area (radius>0 or Sphere/Cone/
    Location); cone = arc>0 or Cone; PBAoE = area centered on self/melee (range≈0); single =
    not AoE; melee vs ranged by range. (Burn=PBAoE r8/range0; Paralytic=single r0; Carrion=
    Location patch eArea4; Seeds=Cone r50.)"""
    radius = rec.get("radius") or 0.0
    rng = rec.get("range") or 0.0
    arc = rec.get("arc") or 0
    aoe = _is_aoe(rec)
    cone = arc > 0 or (rec.get("effect_area") or 0) == 3
    return {
        "aoe": aoe, "cone": cone,
        "pbaoe": aoe and rng <= 15 and not cone, "targeted_aoe": aoe and rng > 15 and not cone,
        "single": not aoe, "melee": rng <= 15, "ranged": rng > 15,
        "radius": radius, "range": rng, "max_targets": rec.get("max_targets") or 0,
    }


def _shape_label(rec):
    """Human-readable geometry of a power (real Mids range/radius/arc), so the hover tells you
    whether a power is point-blank, a cone, or ranged — and how far it reaches."""
    sh = _power_shape(rec)
    rng, rad = round(sh["range"]), round(sh["radius"])
    if sh["cone"]:                            # check cone before PBAoE (a short cone has range≤15 too)
        return f"cone · {rng}ft reach"
    if sh["pbaoe"]:
        return f"PBAoE · {rad}ft radius (point-blank)"
    if sh["targeted_aoe"]:
        return f"targeted AoE · {rad}ft radius @ {rng}ft"
    if sh["aoe"]:
        return f"AoE · {rad}ft radius"
    if sh["melee"]:
        return f"melee · {rng}ft"
    return f"ranged · {rng}ft"


def _is_recovery_click(rec):
    """An endurance-management click (Consume, Energy Absorption, Power Sink) — fired to
    REFUEL, not as part of the damage chain, even though some also deal minor AoE."""
    return (rec.get("power_type") == 0
            and "Endurance Modification" in (rec.get("accepted_set_categories") or []))


_MELEE_ATS = {"Class_Brute", "Class_Scrapper", "Class_Stalker", "Class_Tanker"}


def _prefers_melee(archetype, exposure):
    """Where the build fights from: front → melee, back → ranged, else infer from the AT (melee
    ATs fight close, ranged ATs at distance). Drives whether close or distance powers fill tray 1."""
    if exposure == "front":
        return True
    if exposure == "back":
        return False
    return archetype in _MELEE_ATS


def _rotation_phase(rec, cls, role, dpa, prefers_melee=False):
    """Phase of the active rotation a power belongs to (lower = earlier). The order encodes how an
    archetype fights: set up the spawn (steroids → debuffs → pets), then your ENGAGEMENT-RANGE
    powers (a ranged dealer's distance AoE, a melee dealer's close attacks) fill tray 1, with the
    OFF-range powers (a fire blaster's melee/PBAoE, a brute's ranged epic) and single-target as the
    tray-2 overflow, then refuel, then nuke. Within a band the caller sorts by DPA (hardest first)."""
    fn = (rec.get("full_name") or "")
    if "judgement" in fn.lower():
        return 900                                 # Judgement nuke — fire on cooldown, last
    nm = fn.split(".")[-1].lower()
    cats = set(rec.get("accepted_set_categories") or [])
    is_attack = bool(rec.get("damage_effects"))
    # A Fighting-pool attack (Boxing/Kick) is a Tough/Weave PREREQ, not a control — even though
    # it carries a token disorient that makes _power_class call it "control". Never feature it.
    is_pool_atk = fn.startswith("Pool.") and is_attack
    is_steroid = nm in _DMG_ENABLER_NAMES          # Build Up / Fiery Embrace / Soul Drain …
    is_recovery = _is_recovery_click(rec)
    is_ctrl = bool(cls.get("control")) and not is_pool_atk
    is_setup_debuff = (not is_attack) and (_power_res_debuff(rec) > 0 or bool(cats & {
        "Defense Debuff", "Accurate Defense Debuff", "To Hit Debuff", "Accurate To-Hit Debuff"}))
    # Pets/summons (Carrion Creepers, rains): the SUMMON power has radius 0 (its pets carry the
    # AoE), so flag it by its summons list. is_setup_debuff is checked first, so -res patches
    # like Tar Patch stay in the debuff phase rather than here.
    pet = (cls.get("pet") or "recharge intensive pets" in {c.lower() for c in cats}
           or bool(rec.get("summons")))
    # AoE straight from the real geometry (radius + effect_area). No category-guessing —
    # Paralytic Poison reads single-target, Seeds/Spore/Carrion read AoE, Burn reads PBAoE.
    is_aoe = _is_aoe(rec)
    # Openers — cast first to set up the spawn:
    if is_steroid:      return 100                 # +Dmg/+ToHit steroids
    if is_setup_debuff: return 200                 # -Res / -Def / -ToHit (Tar Patch, Envenom, Weaken)
    if pet:             return 300                 # pets / patches (Carrion Creepers)
    if is_recovery:     return 800                 # Consume — refuel endurance (near the end)
    # Main body: ENGAGEMENT RANGE is the hard split. Powers that match how you fight (a ranged
    # dealer's distance attacks; a front-liner's close PBAoE + cone + melee single-target) ALL
    # fill tray 1 together — that's the front-line rotation. OFF-range powers (a fire blaster's
    # melee/PBAoE; a brute's ranged epic) drop to tray 2. Within a range band the caller sorts by
    # value (DPA + a mild AoE lead, so a hard-hitting melee attack isn't buried under a weak AoE);
    # CONTROLLERS still lead with control (Containment) inside the band.
    is_close = (rec.get("range") or 0) <= 15
    off_range = 0 if (is_close == prefers_melee) else 30   # match your engagement → tray 1
    if role in ("controller", "control", "dominator", "debuffer"):
        return 400 + off_range + (0 if is_ctrl else 10)    # control leads, then attacks
    return 400 + off_range                                 # damage: AoE-vs-ST is the DPA-sort's job


def _positioning_clause(pos):
    """Where this build fights, from the real geometry (range/radius) of its attacks/controls."""
    if not pos:
        return ""
    close = pos.get("pbaoe", 0) + pos.get("melee", 0)
    far = pos.get("ranged_aoe", 0) + pos.get("ranged", 0)
    pb = pos.get("pbaoe", 0)
    if close and close >= far * 2:
        tail = f" ({close} close-range, incl. {pb} point-blank)" if pb else ""
        return f" 🎯 You fight up close — most of your damage is melee/point-blank{tail}, so stay in the spawn."
    if far and far >= close * 2:
        return " 🎯 Ranged engagement — you can attack from distance and kite; you don't need to be in melee."
    return (f" 🎯 Mixed range — {pb} point-blank + {pos.get('ranged_aoe',0)} ranged AoE; "
            "position so your PBAoE/cones still catch the spawn.")


def _tray_notes(role, totals, rotation_end=0.0, pos=None):
    """One line per tray: WHY it matters + the expected outcome in real numbers (DPS, spawn-wide
    -res, the endurance balance, the engagement range, the survival floor). Empty if no totals."""
    notes = {}
    if not isinstance(totals, dict):
        return notes
    off = totals.get("offense") or {}
    gv = lambda d, k: round((d.get(k) or {}).get("value", 0)) if isinstance(d, dict) else 0
    st, aoe, burst = off.get("st_dps"), off.get("aoe_dps"), off.get("aoe_burst")
    resdeb = next((abs(d.get("pct", 0)) for d in off.get("debuffs", [])
                   if d.get("effect") == "Resistance"), 0)
    is_support = role in ("buffer", "healer")
    out = " · ".join(x for x in [f"~{st} single-target DPS" if st else "",
                                 f"~{aoe} AoE/target" if aoe else "",
                                 f"~{burst} alpha" if burst else ""] if x)
    eb = totals.get("endurance") or {}
    # v35: the travel toggle is NEVER silently dropped from the displayed ledger (the
    # Nimbus gap) — show it whenever it exists, and say whether the fight counts it.
    trav = eb.get("travel_toggle_drain_per_sec")
    trav_line = ""
    if trav:
        trav_line = (f" Travel toggle adds {trav}/s"
                     + (" (counted — you fight from range)." if eb.get("travel_in_combat")
                        else " (shown, not counted — grounded in the fight; declare a ranged "
                             "playstyle and it counts)."))
    if eb.get("sustainable"):
        end_line = (f" 🔋 Endurance: sustainable — ~{eb.get('recovery_per_sec')}/s recovery "
                    f"covers the ~{eb.get('drain_per_sec')}/s rotation + toggles.{trav_line}")
    elif eb:
        end_line = (f" 🔋 Endurance: drains ~{eb.get('drain_per_sec')}/s "
                    f"({eb.get('chain_drain_per_sec')} chain + {eb.get('toggle_drain_per_sec')} toggles) "
                    f"vs ~{eb.get('recovery_per_sec')}/s recovery (no incarnates assumed) — attacking "
                    f"nonstop you bottom out in ~{eb.get('empty_after_sec')}s and long fights throttle "
                    f"your real output after that. Add +recovery/endurance reduction, or accept it and "
                    f"lean on Ageless/Consume — your call, stated here so it's a choice.{trav_line}")
    else:
        end_line = ""
    rch0 = round((totals.get("recharge") or {}).get("value", 0)) if isinstance(totals.get("recharge"), dict) else 0
    if is_support:
        # Tray 1 IS the job — cycle buffs/heals to keep the team alive; recharge = buff uptime.
        notes[1] = ("💚 Why it matters: this is the job — cycle your buffs and heals to keep the team "
                    "alive: rotate single-target buffs onto your anchors, drop team auras on cooldown, "
                    f"and top off with your heals. +{rch0}% recharge = buff/heal uptime, the more uptime "
                    "the more the team outlives the spawn.")
        if st or aoe:
            setup = f"−{resdeb}% defense spawn-wide · " if resdeb else ""
            notes[3] = (f"⚔️ Secondary — between buffs, contribute damage + debuff: {setup}{out}. "
                        f"Your role is keeping the team up; this is the bonus on top.{end_line}")
    elif st or aoe:
        ctrl = role in ("controller", "control", "dominator", "debuffer")
        lead = ("lock the spawn so every hit lands DOUBLED (Containment), then "
                if ctrl else "stack your openers, then ")
        setup = f"−{resdeb}% resistance spawn-wide · " if resdeb else ""
        notes[1] = f"⚔️ Why it matters: {lead}swing hardest-first — {setup}{out}.{end_line}{_positioning_clause(pos)}"
    res, dfn = totals.get("resistance") or {}, totals.get("defense") or {}
    rech = round((totals.get("recharge") or {}).get("value", 0)) if isinstance(totals.get("recharge"), dict) else 0
    notes[2] = (f"🛡️ Survival floor (always-on): {gv(res,'Fire')}% fire / {gv(res,'Smashing')}% S/L "
                f"resist · {gv(dfn,'Melee')}% melee defense · +{rech}% recharge — set once.")
    notes.setdefault(3, "🧰 Click when the moment calls — heals, situational buffs, travel & zone macros.")
    notes[4] = "🚶 Out-of-combat — movement, rest, inspirations."
    return notes


def _tray_layout(powers, incarnates=None, archetype=None, role=None, totals=None, exposure=None):
    """Sort a build's powers into the 4 in-game trays. `powers` = frontend power dicts (need
    full_name); `incarnates` = {slot: {full_name, display_name}}. Tray 1 is ordered as a REAL
    rotation (steroids → -res → hardest-hitting chain → refuel → nuke), archetype-aware, using
    per-attack DPA from `totals.offense` (the /build/calculate result) so the chain leads with
    the biggest hits — not pick order. Each tray also gets a `note` (why it matters + stats)."""
    role = role or _AT_DEFAULT_ROLE.get(archetype, "damage")
    prefers_melee = _prefers_melee(archetype, exposure)   # which range fills tray 1
    offense = (totals or {}).get("offense") if isinstance(totals, dict) else None
    dpa_by = {}                              # display_name -> DPA, from the engine's offense
    for a in (offense or {}).get("attacks", []):
        if a.get("name") is not None:
            dpa_by[a["name"]] = a.get("dpa") or 0
    trays = {1: [], 2: [], 3: [], 4: []}
    rotation_end = 0.0                        # Σ end_cost of one full rotation cycle (real data)
    pos = {"pbaoe": 0, "melee": 0, "ranged_aoe": 0, "ranged": 0}   # engagement-range tally
    for pw in powers or []:
        fn = pw.get("full_name")
        rec = POWER_BY_FULL.get(fn) or pw
        nm = (fn or "").split(".")[-1]
        cls = _power_class(rec)
        disp = pw.get("display_name") or rec.get("display_name") or nm.replace("_", " ")
        glyph = _power_glyph(rec, cls)
        # Show the real geometry on hover (point-blank / cone / ranged + reach), and tally the
        # build's engagement range from its attacks/controls (not toggles/buffs).
        title = f"{disp}"
        if rec.get("damage_effects") or cls.get("control"):
            sh = _power_shape(rec)
            title = f"{disp} — {_shape_label(rec)}"
            if sh["pbaoe"]:
                pos["pbaoe"] += 1
            elif sh["aoe"] and sh["melee"]:
                pos["melee"] += 1
            elif sh["aoe"]:
                pos["ranged_aoe"] += 1
            elif sh["melee"]:
                pos["melee"] += 1
            else:
                pos["ranged"] += 1
        ptype = rec.get("power_type")
        steroid = nm.lower() in _DMG_ENABLER_NAMES
        # --- assign a tray + a within-tray band (community standard, forum-researched):
        # tray 1 = the active rotation; tray 2 = mid-fight CLICKS (self-buffs → heals →
        # endurance recovery, grouped last); tray 3 = set-and-forget (toggles in switch-on
        # order, then utility, Rest parked at the end); tray 4 = travel, isolated from
        # combat keys so it's never fat-fingered mid-fight.
        sub = 0
        cats = set(rec.get("accepted_set_categories") or [])
        if nm in _SPRINTS or nm.startswith("prestige"):
            tray = 4
        elif nm == "Rest":
            tray, sub = 3, 9
        elif nm in _TRAVEL_EXTRA:
            tray, sub = 3, 3                 # Hover/CJ — toggles, live with the toggles
        elif nm in _TRAVEL_MAIN:
            tray = 4
        elif nm == "Hasten":
            tray, sub = 2, 0
        elif ptype == 2:                     # toggle: switch-on order = armors → epic → pools
            tray = 3
            sub = 1 if fn.startswith("Epic.") else (2 if fn.startswith("Pool.") else 0)
        elif ptype == 1:                     # auto/passive — no tray slot
            continue
        else:                                # click
            is_support_power = (cls["support"] or _is_support_powerset(rec.get("powerset_full_name"))
                                or bool(rec.get("buff_effects")))
            is_heal = "Healing" in cats
            is_refuel = _is_recovery_click(rec) or "Endurance Modification" in cats
            if role in ("buffer", "healer"):
                # A SUPPORT primary's ROTATION is its buffs/heals (Fortitude, Adrenalin Boost, the
                # Auras, Clear Mind, Heal Other) — that's the job. Attacks/steroids are the SECONDARY
                # contribution (damage + -def debuff): occasional mid-fight clicks, tray 2.
                tray = 1 if (is_support_power and not cls["atk"]) else 2
            elif (cls["atk"] or cls["control"] or steroid
                    or (cls["support"] and rec.get("debuff_effects"))):
                # Active rotation = attacks, control, debuff-patches, AND damage steroids (Build
                # Up / Fiery Embrace are OPENERS you fire before a burst — not "secondary buffs").
                tray = 1
            elif cls["pet"] or rec.get("summons"):
                tray, sub = 3, 4             # pet summons = occasional utility (community norm)
            else:                            # mid-fight clicks: buffs → heals → recovery LAST
                tray = 2
                sub = 2 if is_refuel else (1 if is_heal else 0)
        if tray == 1:
            rotation_end += rec.get("end_cost") or 0.0
        dpa = dpa_by.get(disp, 0) or 0
        slot = {"label": disp, "short": disp, "icon": _power_icon_url(fn),
                "glyph": glyph, "title": title,
                "_o": _rotation_phase(rec, cls, role, dpa, prefers_melee) if tray == 1 else sub,
                # Single-target chain leads its band (slots 1-3 muscle memory); AoEs/cones after.
                "_aoe": 1 if (tray == 1 and _is_aoe(rec)) else 0,
                "_dpa": dpa}
        trays[tray].append(slot)
    # incarnates
    for slotname, v in (incarnates or {}).items():
        info = _INC_TRAY.get(slotname)
        if not info or not (v and v.get("full_name")):
            continue
        t, glyph = info
        disp = v.get("display_name") or slotname
        trays[t].append({"label": disp, "short": disp, "glyph": glyph,
                         "title": f"{disp} ({slotname} incarnate)",
                         # Judgement = the nuke, pinned last; Destiny/Lore = utility band
                         "_o": 900 if t == 1 else (5 if t == 3 else 0), "_dpa": 0})
    # Tray 1 = the rotation: by phase; within a phase the SINGLE-TARGET chain leads
    # (slots 1-3, hardest-hitting first — the community's muscle-memory row), then
    # AoEs/cones; Judgement/nukes are phase-pinned to the end. Trays 2/3 sort by their
    # bands (buffs → heals → recovery; armors → epic → pools → travel-toggles → Rest).
    trays[1].sort(key=lambda s: (s.get("_o", 99), s.get("_aoe", 0), -(s.get("_dpa") or 0)))
    trays[2].sort(key=lambda s: s.get("_o", 0))
    trays[3].sort(key=lambda s: s.get("_o", 0))
    macros = {t: [{"label": m[0], "short": m[0], "glyph": m[2], "title": m[1], "macro": True}
                  for m in ms] for t, ms in _TRAY_MACROS.items()}
    if role in ("buffer", "healer"):
        base = {1: "support rotation  ·  buffs + heals you cycle to keep the team up",
                2: "mid-fight clicks  ·  attacks & -def debuff between buffs → heals → recovery",
                3: "set and forget  ·  toggles (armors → pools) → utility → Rest",
                4: "travel + sprints + emotes  ·  away from combat keys"}
    else:
        base = {1: "rotation  ·  openers → single-target chain → AoEs → refuel → nuke",
                2: "mid-fight clicks  ·  self-buffs → heals → endurance recovery",
                3: "set and forget  ·  toggles (armors → pools) → utility → Rest",
                4: "travel + sprints + emotes  ·  away from combat keys"}
    notes = _tray_notes(role, totals, rotation_end, pos)
    out = []
    phys = 1
    cap = 10                       # an in-game power tray holds exactly 10 slots (keys 1-9, 0)
    for t in (1, 2, 3, 4):
        slots = trays[t] + macros.get(t, [])
        if not slots:
            continue               # don't render an empty tray
        chunks = [slots[i:i + cap] for i in range(0, len(slots), cap)]
        for ci, chunk in enumerate(chunks):
            cont = f"  ·  cont. {ci + 1}/{len(chunks)}" if len(chunks) > 1 else ""
            out.append({"n": phys, "group": t, "label": f"Tray {phys} — {base[t]}{cont}",
                        "slots": chunk, "note": notes.get(t) if ci == 0 else None})
            phys += 1
    return out


@app.route("/build/trays", methods=["POST"])
def build_trays():
    body = request.get_json(force=True) or {}
    powers = body.get("powers") or []
    archetype = body.get("archetype")
    role = body.get("role")
    totals = body.get("totals")              # the frontend's last /build/calculate result (DPA + stats)
    # Fall back to computing it here if the caller didn't pass it (so the rotation orders by
    # real damage and the notes have numbers). Cheap on localhost; never fatal.
    if not isinstance(totals, dict) and archetype:
        try:
            totals = engine.calculate_build({"archetype": archetype, "powers": powers,
                                             "pvp": bool(body.get("pvp"))},
                                            SET_BONUSES, ctx=_stat_ctx(archetype))
        except Exception:  # noqa: BLE001
            totals = None
    layout = _tray_layout(powers, body.get("incarnates") or {}, archetype, role, totals,
                          body.get("exposure"))
    return jsonify({"ok": True, "trays": layout})


@app.route("/build/autopick", methods=["POST"])
def build_autopick():
    body = request.get_json(force=True) or {}
    at, primary, secondary = body.get("archetype"), body.get("primary"), body.get("secondary")
    if not (at and primary and secondary):
        return jsonify({"ok": False, "error": "Need archetype + primary + secondary."}), 400
    picks = _auto_pick_powers(at, primary, secondary, role=body.get("role"),
                              exposure=body.get("exposure"), content=body.get("content"),
                              travel=body.get("travel"), form=body.get("form"))
    powers = []
    for pk in picks:
        rec = POWER_BY_FULL.get(pk["full_name"])
        if not rec:
            continue
        powers.append({"full_name": rec["full_name"], "display_name": rec["display_name"],
                       "powerset_full_name": rec["powerset_full_name"],
                       "accepted_set_category_ids": rec.get("accepted_set_category_ids", []),
                       "accepted_set_categories": rec.get("accepted_set_categories", []),
                       "power_type": rec.get("power_type"), "pick_level": pk["pick_level"],
                       "level_available": rec.get("level_available"),
                       "slots": [None], "slotCount": 1})
    return jsonify({"ok": True, "powers": powers, "count": len(powers)})


# ---------------------------------------------------------------------------
# Discovery recommender: "what do you want to do (role) × where (content) × from
# where (exposure)" -> ranked archetypes, with the DEFINING set (support is often a
# SECONDARY: Corruptor/Controller/Mastermind), roles fluid, easiest-not-only framing.
# ---------------------------------------------------------------------------
_ROLE_SUFFIX = {"buffer": ("buff",), "healer": ("buff",),
                "damage": ("ranged", "melee", "offensive", "assault"),
                "tank": ("defense", "defensive"), "control": ("control",), "pets": ("summon",)}
_ROLE_RANK = {   # easiest/most effective FIRST — but every entry is a valid route, never "the only way"
    "buffer":  ["Class_Defender", "Class_Corruptor", "Class_Controller", "Class_Mastermind"],
    "healer":  ["Class_Defender", "Class_Corruptor", "Class_Controller", "Class_Mastermind"],
    "damage":  ["Class_Blaster", "Class_Scrapper", "Class_Brute", "Class_Stalker",
                "Class_Corruptor", "Class_Sentinel", "Class_Dominator"],
    "tank":    ["Class_Tanker", "Class_Brute", "Class_Scrapper", "Class_Stalker", "Class_Sentinel"],
    "control": ["Class_Controller", "Class_Dominator"],
    "pets":    ["Class_Mastermind"],
    # "a bit of everything": ATs whose two sets natively span roles (damage+support,
    # damage+tank, control+support) — the Kheldians ARE the canonical generalists
    # ("the whole team of diversity in one character", the role-lens solo blend).
    "mixed":   ["Class_Corruptor", "Class_Controller", "Class_Brute", "Class_Sentinel",
                "Class_Mastermind", "Class_Warshade", "Class_Peacebringer"],
}
_AT_FLAVOR = {
    "Class_Defender": "strongest buffs/debuffs — support is your PRIMARY",
    "Class_Corruptor": "buffs/debuffs as your secondary + Scourge damage — shines solo and on farms",
    "Class_Controller": "support secondary layered on hard control (lockdown + heals)",
    "Class_Mastermind": "support secondary commanding a squad of pets that tank and deal the damage",
    "Class_Blaster": "the highest raw ranged damage in the game",
    "Class_Scrapper": "high single-target melee with critical hits",
    "Class_Brute": "melee that ramps with Fury, plus near-Tanker survival",
    "Class_Tanker": "the toughest survival, with AoE-leaning melee",
    "Class_Stalker": "stealth + Assassin Strike burst",
    "Class_Sentinel": "ranged damage with its own armor — a durable blaster",
    "Class_Dominator": "control + high Assault damage (perma-Domination is the payoff)",
}


def _role_slot(at_name, role):
    at = ARCH_BY_NAME.get(at_name) or {}
    suf = _ROLE_SUFFIX.get(role, ())
    if any(s in (at.get("primary_group") or "").lower() for s in suf):
        return "primary"
    return "secondary"


# Self-sufficient ATs bring their OWN armor + damage, so they survive SOLO without a team to tank
# or finish kills. Squishy/support ATs assume a team supplies survival and the killing blow — solo,
# that gap is where characters get abandoned. So SOLO content re-weights toward the durable picks
# (and the ranged/melee vector the player wants), and every rec carries an honest solo note.
# Team/league/farm rankings are UNCHANGED — there a team covers the squishies.
_SELF_SUFFICIENT_ATS = {"Class_Sentinel", "Class_Scrapper", "Class_Brute",
                        "Class_Tanker", "Class_Stalker"}
_RANGED_ATS = {"Class_Blaster", "Class_Sentinel", "Class_Corruptor",
               "Class_Defender", "Class_Dominator", "Class_Controller"}
_MELEE_ATS = {"Class_Scrapper", "Class_Brute", "Class_Stalker", "Class_Tanker"}
_SOLO_CONTENT = {"general", "av"}


def _discover(role, exposure=None, content=None):
    role = role if role in _ROLE_RANK else "damage"
    ranked = _ROLE_RANK[role]
    # content nudge: a fire farm rewards a support that ALSO adds damage (Corruptor)
    order = list(ranked)
    if content == "fire_farm" and role in ("buffer", "healer") and "Class_Corruptor" in order:
        order.remove("Class_Corruptor"); order.insert(0, "Class_Corruptor")
    solo = content in _SOLO_CONTENT
    if solo:                    # durability leads solo; honor the ranged/melee vector too
        base = {a: i for i, a in enumerate(order)}
        def _solo_score(a):
            s = -base[a]
            if a in _SELF_SUFFICIENT_ATS: s += 7      # its own armor = survives alone
            if exposure == "back":                    # wants to fight at RANGE → durable ranged (Sentinel) leads
                s += 4 if a in _RANGED_ATS else (-4 if a in _MELEE_ATS else 0)
            elif exposure == "front":                 # wants to fight in MELEE
                s += 4 if a in _MELEE_ATS else (-4 if a in _RANGED_ATS else 0)
            return s
        order = sorted(order, key=_solo_score, reverse=True)
    out = []
    for i, at_name in enumerate(order):
        at = ARCH_BY_NAME.get(at_name)
        if not at:
            continue
        slot = _role_slot(at_name, role)
        by_at = POWERSETS["by_archetype"].get(at_name) or {}
        defining = [s["display_name"] for s in by_at.get(slot, [])]
        other_slot = "secondary" if slot == "primary" else "primary"
        other = [s["display_name"] for s in by_at.get(other_slot, [])]
        ease = "Easiest route" if i == 0 else ("Strong alternative" if i < 3 else "Also works")
        note = ""
        if solo:
            if at_name in _SELF_SUFFICIENT_ATS:
                note = "✓ Durable solo — brings its own armor, so you stay alive while you deal the damage."
            elif role == "damage":
                note = "⚠ High damage but GLASS — solo you'll have to buy your own survival (defense/procs) or faceplant a lot. Shines most on a team."
            elif role in ("buffer", "healer", "control"):
                note = "⚠ Built to buff/debuff a TEAM — solo it kills slowly. If you'll mostly solo, a self-sufficient pick is friendlier."
        out.append({"archetype": at_name, "display": at.get("display_name"),
                    "role_slot": slot, "defining_label": f"your {slot} set",
                    "defining_sets": defining[:12], "other_sets": other[:12],
                    "why": _AT_FLAVOR.get(at_name, ""), "ease": ease, "note": note})
    return out


def _level_key_stats(t):
    def num(x):
        return round((x.get("value") if isinstance(x, dict) else x) or 0)
    r, d, off = t["resistance"], t["defense"], (t.get("offense") or {})
    return {"sl_res": num(r["Smashing"]), "fire_res": num(r["Fire"]),
            "melee_def": num(d["Melee"]), "ranged_def": num(d["Ranged"]), "aoe_def": num(d["AoE"]),
            "recharge": num(t.get("recharge")), "recovery": num(t.get("recovery")),
            "regen": num(t.get("regeneration")), "max_hp": num(t.get("max_hp")),
            "st_dps": round(off.get("st_dps") or 0), "aoe_dps": round(off.get("aoe_dps") or 0)}


# Contextual leveling tips surfaced as the character reaches each level (shown once, at
# the first pick at/after the tip's level).
_LEVEL_TIPS = [
    (1,  "This is a JOURNEY, not a race to 50 — the leveling IS the game. There's no traditional end-game "
         "gate waiting; rush there (AE farms, power-leveling) and you arrive without ever learning to PLAY "
         "your character, having skipped content you may wish you'd seen. If you DO outrun it, no harm done: "
         "Ouroboros flashback lets you exemplar back down and experience what you missed — one power at a "
         "time, the way the game teaches itself."),
    (1,  "Stop by the START / P2W vendor in any starting zone (free on Homecoming): grab a cheap "
         "travel temp power, XP boosters, and prestige Sprints to make the early levels fly."),
    (7,  "Read your CLUES (in the info window) — they're the story breadcrumbs missions drop. Following "
         "the threads they point to (new contacts, Ouroboros flashback arcs) is how you turn up side "
         "missions and badge arcs that never appear on the map."),
    (8,  "Task Forces start opening up — Positron Part One (lvl 8–15) is your first, with Part Two "
         "(11–16) right after. TFs give big XP plus Reward Merits you can spend on the IO recipes "
         "this build wants."),
    (10, "How EXEMPLARING works: join a lower-level TF and you drop to the team leader's level (capped "
         "at that TF's max). Powers you picked ABOVE that level switch off — that's why travel + survival "
         "are taken early. Two more catches: your Incarnate powers go INACTIVE below level 45, and "
         "high-level set bonuses fade unless the set is slotted Attuned."),
    (13, "If you enjoy badges, the hunt is a journey of its own — they come from exploring zone "
         "corners, defeating particular enemy groups, and finishing arcs & TFs. No rush; just collect "
         "them as you pass through."),
    (20, "From level 20, defeated foes can drop a TIP — a short mission with a moral choice. Run a "
         "string of them to shift your ALIGNMENT (Hero ↔ Vigilante ↔ Rogue ↔ Villain), which unlocks "
         "the other faction's zones, contacts, and Patron pools — and they pay Reward Merits too."),
    (15, "Synapse TF (15–20). The quick low-level trials Death from Below & Drowning in Blood are easy "
         "team XP and each hands you a free set IO."),
    (20, "Sister Psyche / Yin TF (20–25)."),
    (22, "Worth chasing ACCOLADE badges around now: sets like Atlas Medallion & Portal Jockey grant "
         "PERMANENT +Max HP and +Endurance — they push toward the very caps this build is built around."),
    (25, "Citadel TF (25–30)."),
    (30, "Manticore TF (30–35)."),
    (35, "Numina TF (35–40) — and your Epic / Ancillary pool is now available."),
    (40, "Higher-end TFs run toward 50; at 50 you unlock Incarnate content (iTrials) for the always-on "
         "incarnate powers in this plan."),
]
_PATRON_EPICS = ("mace_mastery", "mu_mastery", "soul_mastery", "leviathan_mastery")

# ── Learn-to-PLAY coaching (from the "Life Outside the AE Building" guide) ───────
# Hands-on PLAY skills a normal-leveling player absorbs but a rushed one skips — woven
# into the walk by the band where each first matters. Timeless (not build/Homecoming-
# version facts), and AT-shaped: a Tanker is TOLD to take the hits; a squishy is told to
# let the tank go first. These teach how to PLAY the character, not what to slot.
_ARMORED_ATS = {"Class_Scrapper", "Class_Brute", "Class_Stalker", "Class_Tanker", "Class_Sentinel"}
_FRONTLINE_ATS = {"Class_Tanker", "Class_Brute"}
_MELEE_MOVE_ATS = {"Class_Scrapper", "Class_Brute", "Class_Stalker", "Class_Tanker"}


def _play_tips(archetype):
    """AT-aware (level, message) learn-to-play nudges, sorted by the level they first apply."""
    tips = [
        (1, "🎯 Bind a key to grab the nearest foe — type "
            "/bind t \"target_enemy_near\" — and use Tab to cycle targets. Targeting from the keyboard "
            "beats hunting with the mouse in a messy spawn. Click a teammate to “assist” (take their target)."),
        (1, "🧪 Carry INSPIRATIONS and actually pop them: green = heal, purple = harder to hit you, "
            "orange = less damage taken. Three of one color combine into any other — never sit on a full "
            "tray while you’re dying."),
        (2, "🧑‍🏫 Learn your character on SMALL teams (4 or fewer) or solo. On a big steamroller team "
            "everything dies in a blur and you learn nothing; small groups give you time to see what your "
            "powers actually do."),
        (6, "🎚️ Dying a lot? Lower your difficulty (Notoriety) at a Hero Corps Analyst (blue) / Fateweaver "
            "(red) — you can raise it back any time. Fighting +0/+1 enemies, not +3, is how the fights teach you."),
        (12, "👥 Watch your teammates’ HP AND endurance bars. A defender / controller / tank at zero "
             "endurance means no heals, no holds, no aggro hold — that’s your cue to play safe."),
        (20, "🔎 Read other players’ powers: don’t knockback the foes packed around an Invulnerability "
             "tank (its defense needs the crowd), and don’t kill a debuff ANCHOR that should be left alive."),
    ]
    if archetype in _MELEE_MOVE_ATS:
        tips.append((1, "🗡️ As a melee character, practice chasing a target WITHOUT auto-follow — you keep "
                        "control of your footing and can peel to the next foe faster."))
    else:
        tips.append((1, "🏹 As a ranged character, fight from RANGE — pick targets at a distance instead of "
                        "standing in melee. Position IS your armor."))
    if archetype in _FRONTLINE_ATS:
        tips.append((4, "🛡️ You’re the one meant to take the hits — engage FIRST, grab aggro, and slot your "
                        "defenses before your attacks. Don’t be shy about wading in; the team is counting on it."))
    elif archetype not in _ARMORED_ATS:
        tips.append((4, "🫥 You’re squishy — let the tank/brute engage and grab aggro before you open up, "
                        "especially with AoE. If you pull aggro, run TOWARD the tank, not away (fleeing just gets "
                        "you shot in the back)."))
    return sorted(tips, key=lambda t: t[0])


# ── Signature ("keystone") powers — curated & VERIFIED against the power DB ──────
# The guide: "virtually all sets have a keystone power that should be taken as soon as it's
# available." There is no signature flag in the data, so guessing would violate the tool's
# quality bar — instead this is a hand-verified starter map (power_name within a powerset,
# keyed by the powerset's short name). SILENT on any set not listed, so we never assert a
# wrong keystone. Grow it as more sets are confirmed. (Hasten is deliberately absent — it's a
# pool staple, not a set signature, and we don't push Hasten reliance.)
SIGNATURE_POWERS = {
    "Illusion_Control": {"Phantom_Army"},
    "Fire_Control": {"Fire_Imps"},
    "Kinetics": {"Fulcrum_Shift"},
    "Regeneration": {"Integration"},
    "Stone_Armor": {"Rooted"},
    "Dark_Melee": {"Soul_Drain"},
    "Pain_Domination": {"Painbringer"},
    # Location-AoE debuff keystones — modeled correctly now that pseudo-pet effects are
    # folded in (Freezing Rain's power_name is "Fog" on Controller/Defender, "Freezing_Rain"
    # on Corruptor/MM; both display as "Freezing Rain").
    "Storm_Summoning": {"Fog", "Freezing_Rain"},
    "Cold_Domination": {"Sleet", "Heat_Loss"},
}

# Travel MOVEMENT powers (Homecoming names) — the ones that actually get you across a zone.
# Combat Jumping / Combat Flight / Hasten are NOT travel (they're mules/utility), so they never
# trip the "too many travel powers" check.
_TRAVEL_POWER_NAMES = {"Super_Speed", "Leap", "Fly", "Teleport",
                       "Mystic_Flight", "Speed_of_Sound", "Translocation"}
# Low-value pool ATTACKS the guide says to drop first (Boxing/Kick are fine — Tough/Weave prereqs).
_FILLER_POOL_ATTACKS = {"Flurry", "Jump_Kick"}
# These never need extra slots.
_NO_EXTRA_SLOT_NAMES = {"Brawl", "Sprint", "Rest"}


def _main_sets(powers):
    """(primary, secondary) powerset full-names guessed from a power list — the first
    two non-pool/epic/inherent sets in pick order. For the meta-target positional swap."""
    seen = []
    for p in powers or []:
        ps = p.get("powerset_full_name") or ""
        if not ps or ps.startswith(("Pool.", "Epic.", "Inherent.", "Incarnate.")):
            continue
        if ps not in seen:
            seen.append(ps)
        if len(seen) >= 2:
            break
    return (seen[0] if seen else None), (seen[1] if len(seen) > 1 else None)


def _pname(p):
    """A power's short power_name, from the record or the DB."""
    return (p.get("power_name")
            or (POWER_BY_FULL.get(p.get("full_name"), {}) or {}).get("power_name")
            or (p.get("full_name") or "").split(".")[-1])


def _build_coaching(archetype, powers):
    """Gentle, HC-accurate 'Common Build Mistakes' notes on the ACTUAL build (coaching, not errors).
    Rules sourced from the guide but re-checked against Homecoming (e.g. Fitness is inherent now, so
    there is NO 'take Stamina' nag; travel can be taken from level 4)."""
    notes = []
    real = [p for p in powers if not (p.get("full_name") or "").startswith("Inherent.")]
    names = [_pname(p) for p in real]

    # 1) Travel powers — need one, rarely more than one.
    travels = [n for n in names if n in _TRAVEL_POWER_NAMES]
    if len(travels) > 1:
        notes.append("You have more than one travel power (" + ", ".join(sorted({t.replace('_', ' ') for t in travels}))
                     + "). Most builds only need one — a spare pick could go to something with more impact.")
    elif not travels and len(real) >= 18:   # only nag a near-complete build, never a mid-level one
        notes.append("No travel power picked. One of Super Speed / Leap / Fly / Teleport makes getting "
                     "around far less painful (and keeps teammates from waiting) — on Homecoming you can take "
                     "one as early as level 4.")

    # 2) Low-value pool attacks.
    filler = sorted({n.replace("_", " ") for n in names if n in _FILLER_POOL_ATTACKS})
    if filler:
        notes.append("Low-value pool attacks in your build (" + ", ".join(filler) + "). Most builds skip these "
                     "for a power that pulls its weight. (Boxing / Kick are fine — they’re Tough/Weave prereqs.)")

    # 3) Slots wasted on powers that never need them. (Brawl/Sprint/Rest are INHERENTS, so scan the
    # full list here, not just the non-inherent picks.)
    for p in powers:
        n = _pname(p)
        if n in _NO_EXTRA_SLOT_NAMES and len(p.get("slots") or []) > 1:
            notes.append(f"You’ve added slots to {n} — it never needs extra slots. Move them to a power that "
                         "benefits.")

    # 4) Missing a set's signature/keystone power (VERIFIED sets only; silent otherwise). Resolve
    # against the build's ACTUAL powerset so we name only the keystone that exists for THIS AT's
    # variant (Storm's is internally "Fog" on Controllers, "Freezing_Rain" on Corruptors) and report
    # its DISPLAY name ("Freezing Rain"), never the raw internal name.
    taken_names = {n for n in names}
    for p in real:
        ps_full = p.get("powerset_full_name") or ""
        sigs = SIGNATURE_POWERS.get(ps_full.split(".")[-1])
        if not sigs:
            continue
        for signame in sigs:
            cand = POWER_BY_FULL.get(ps_full + "." + signame)
            if not cand or signame in taken_names:      # not this AT's variant, or already taken
                continue
            disp = cand.get("display_name") or signame.replace("_", " ")
            note = (f"You skipped {disp} — usually the keystone of "
                    f"{ps_full.split('.')[-1].replace('_', ' ')}. Take it when it’s available; "
                    "builds without it tend to underperform.")
            if note not in notes:
                notes.append(note)
    return notes


@app.route("/converter/plan", methods=["POST"])
def converter_plan():
    """Per-set enhancement-converter plans for a build — the cheapest concrete path to each IO."""
    body = request.get_json(force=True) or {}
    plans = converter.plan_build(body.get("powers") or [], SET_BY_UID, SETS_BY_CATEGORY)
    return jsonify({"ok": True, "plans": plans, "summary": converter.summarize(plans)})


@app.route("/converter/assign", methods=["POST"])
def converter_assign():
    """FARM-EXIT MATCHMAKER: build + a haul of drops -> which drop seeds which needed set,
    cheapest conversion routes first; unmatchable drops -> sell list; unseeded needs -> buy list."""
    body = request.get_json(force=True) or {}
    out = converter.assign_haul(body.get("haul") or [], body.get("powers") or [],
                                SET_BY_UID, SETS_BY_CATEGORY)
    return jsonify({"ok": True, **out})


@app.route("/converter/catalog", methods=["GET"])
def converter_catalog():
    """Every set (all archetypes) for the interactive converter pickers."""
    return jsonify({"ok": True, "sets": converter.catalog(ENH_SETS)})


@app.route("/converter/from", methods=["POST"])
def converter_from():
    """FORWARD: 'I have this IO' → the three conversion choices it offers (the Y dropdown)."""
    s = SET_BY_UID.get((request.get_json(force=True) or {}).get("set_uid"))
    if not s:
        return jsonify({"ok": False, "error": "Unknown set."}), 404
    return jsonify({"ok": True, "options": converter.forward_options(s, ENH_SETS, SETS_BY_CATEGORY)})


@app.route("/converter/to", methods=["POST"])
def converter_to():
    """REVERSE: 'I want this IO' → the cheapest concrete path to obtain it."""
    body = request.get_json(force=True) or {}
    s = SET_BY_UID.get(body.get("set_uid"))
    if not s:
        return jsonify({"ok": False, "error": "Unknown set."}), 404
    piece = body.get("piece")
    cat_pool = len(SETS_BY_CATEGORY.get(s.get("category_id"), []))
    return jsonify({"ok": True, "plan": converter.plan_for_set(s, [piece] if piece else [], cat_pool)})


@app.route("/build/leveling-steps", methods=["POST"])
def leveling_steps():
    """Walk EVERY level 1..50 using the exact Homecoming schedule (leveling_schedule): at each level,
    exactly what happens — a POWER only at a power level, SLOTS only at a slot level — plus the build-
    so-far stats, milestone unlocks, and cost-smart slotting advice. Never suggests a choice that
    doesn't exist at that level. (The 4 Epic ATs don't follow this ladder — flagged via is_eat.)"""
    body = request.get_json(force=True) or {}
    archetype = body.get("archetype")
    powers = body.get("powers") or []
    # The walk needs each power's PICK LEVEL. Solve/autopick don't assign one, so derive it from the
    # real Homecoming ladder (POWER_PICK_LEVELS), earliest-available first — matching how you'd take
    # them in-game. Inherents (Fitness/Brawl…) are auto-granted, not picks: they seed the build at L1.
    def _lvl_avail(p):
        return max(1, int(p.get("level_available")
                          or (POWER_BY_FULL.get(p.get("full_name"), {}) or {}).get("level_available") or 1))
    inherent_powers = [p for p in powers if (p.get("full_name") or "").startswith("Inherent.")]
    real = [p for p in powers if not (p.get("full_name") or "").startswith("Inherent.")]
    # Pick levels must let every slot actually land (a slot granted at level g only fits
    # powers already picked) — recompute the seating slot-aware unless the build carries
    # a complete assignment that already works.
    if (not all(p.get("pick_level") for p in real) or not _schedule_feasible(real)
            or not _l1_seating_ok(real, archetype)):
        _assign_pick_levels(powers, archetype)
    real.sort(key=lambda p: (int(p["pick_level"]), _lvl_avail(p)))
    picks_by_level = defaultdict(list)
    for p in real:
        picks_by_level[max(1, int(p["pick_level"]))].append(p)
    # Creation order: the game asks for the SECONDARY power first, then the primary.
    if picks_by_level.get(1):
        _secs = {e["full_name"] for e in ((POWERSETS["by_archetype"].get(_at_canon(archetype)) or {})
                                          .get("secondary") or [])}
        picks_by_level[1].sort(key=lambda p: 0 if p.get("powerset_full_name") in _secs else 1)
    ctx = _stat_ctx(archetype)
    at = ARCH_BY_NAME.get(archetype)
    res_cap = round(at["res_cap"] * 100, 1) if at else engine.RESISTANCE_HARD_CAP
    is_eat = archetype in _EPIC_ATS

    # ── VEAT two-phase career ────────────────────────────────────────────────
    # Live play 1-23 can only draw on the BASE sets — branch sets open at the mandatory
    # level-24 respec, where every pick through 24 is RE-PLACED with all six sets legal
    # (retroactively, so a branch power can land in an early slot). The ladder assignment
    # above IS that post-respec re-place order; the live pre-24 walk is rebuilt here from
    # base-accessible powers only, padding with temporary free-choice picks if the final
    # build has fewer than 13 pre-24 powers (the respec erases them anyway).
    veat = leveling_schedule.eat_type(archetype) == "veat"
    live_by_level, respec_order = {}, None
    if veat:
        base_pool = sorted([p for p in real
                            if (p.get("powerset_full_name") or "") not in _VEAT_BASE_SET],
                           key=_lvl_avail)
        live_by_level, bi = defaultdict(list), 0
        for l in [pl for pl in _PL if pl < 24]:
            if bi < len(base_pool) and _lvl_avail(base_pool[bi]) <= l:
                live_by_level[l].append(base_pool[bi]); bi += 1
            else:
                live_by_level[l].append({"full_name": "", "powerset_full_name": "",
                                         "display_name": "Your choice — any available power (temporary)",
                                         "temp": True})
        respec_order = [
            {"level": lv, "name": p.get("display_name") or p["full_name"].split(".")[-1],
             "powerset": (p.get("powerset_full_name") or "").split(".")[-1].replace("_", " ")}
            for lv in sorted(picks_by_level) if lv <= 24 for p in picks_by_level[lv]]

    epic_ps = next((p.get("powerset_full_name") for p in powers
                    if (p.get("powerset_full_name") or "").startswith("Epic.")), None)
    is_patron = bool(epic_ps) and any(k in epic_ps.lower() for k in _PATRON_EPICS)
    epic_name = epic_ps.split(".")[-1].replace("_", " ") if epic_ps else None

    # Seed the build with the auto-granted inherents (Fitness etc.) so their contribution is baseline.
    cum = [{"full_name": p["full_name"], "power_type": p.get("power_type"),
            "include_in_totals": p.get("power_type") in (1, 2), "slots": p.get("slots") or []}
           for p in inherent_powers]
    inherent_seed = list(cum)

    def _cum_entry(p):
        return {"full_name": p["full_name"], "power_type": p.get("power_type"),
                "include_in_totals": p.get("power_type") in (1, 2), "slots": p.get("slots") or []}

    out, prev, slots_running = [], None, 0
    tips_done, epic_done = set(), False
    play_tips, play_done = _play_tips(archetype), set()
    for lvl in range(1, 51):
        ev = leveling_schedule.level_events(lvl)
        milestone = leveling_schedule.milestone_for(archetype, lvl)   # Epic-AT-aware
        respec_here = None
        if veat and lvl < 24:
            # live phase 1 — base sets only (temporary free-choice picks add nothing to totals)
            picks = live_by_level.get(lvl, [])
            cum.extend(_cum_entry(p) for p in picks if not p.get("temp"))
        elif veat and lvl == 24:
            # the mandatory respec: every pick through 24 is re-placed from the final order,
            # branch powers included — the running build resets to that re-place.
            picks = picks_by_level.get(24, [])
            respec_here = respec_order
            cum = inherent_seed + [_cum_entry(p) for lv2 in sorted(picks_by_level)
                                   if lv2 <= 24 for p in picks_by_level[lv2]]
        else:
            picks = picks_by_level.get(lvl, [])
            cum.extend(_cum_entry(p) for p in picks)
        slots_running += ev["slots"]
        if not (picks or ev["slots"] or milestone):
            continue                                   # nothing happens this level — skip it
        # recompute stats only when a power was added (slot-only levels don't change the totals here)
        if picks or respec_here or prev is None:
            s = _level_key_stats(engine.calculate_build(
                {"archetype": archetype, "powers": cum}, SET_BONUSES, res_cap=res_cap, ctx=ctx))
        else:
            s = prev
        tips = []
        # Level 1 = character creation: the game offers one of the FIRST TWO powers of
        # each of your two main sets — frame the picks as those choices, not free picks.
        if lvl == 1 and not veat and len(picks) >= 1:
            for p in picks:
                ps = p.get("powerset_full_name")
                f2 = _set_first_two(ps) if ps and not ps.startswith(("Pool.", "Epic.")) else []
                if len(f2) == 2 and p["full_name"] in f2:
                    other = [fn for fn in f2 if fn != p["full_name"]][0]
                    nm = p.get("display_name") or p["full_name"].split(".")[-1].replace("_", " ")
                    tips.append(f"At creation the game offers {ps.split('.')[-1].replace('_', ' ')}'s "
                                f"first two powers — this plan takes {nm} "
                                f"(the other option is {other.split('.')[-1].replace('_', ' ')}).")
        for i, (tlvl, msg) in enumerate(_LEVEL_TIPS):
            if lvl >= tlvl and i not in tips_done:
                tips.append(msg)
                tips_done.add(i)
        # learn-to-PLAY nudges — a separate stream from content tips, surfaced once at their band.
        play = []
        for i, (tlvl, msg) in enumerate(play_tips):
            if lvl >= tlvl and i not in play_done:
                play.append(msg)
                play_done.add(i)
        # Affirm a keystone/signature pick when it's taken (positive reinforcement, verified sets only).
        for p in picks:
            setshort = (p.get("powerset_full_name") or "").split(".")[-1]
            if _pname(p) in SIGNATURE_POWERS.get(setshort, set()):
                nm = p.get("display_name") or _pname(p).replace("_", " ")
                tips.append(f"⭐ {nm} is a KEYSTONE of {setshort.replace('_', ' ')} — great pick; take and "
                            "slot it as a priority.")
        if epic_ps and not epic_done and any((p.get("powerset_full_name") or "") == epic_ps for p in picks):
            tips.append(
                (f"“{epic_name}” is a PATRON power pool — unlock it at level 35 by completing a Patron arc "
                 f"(from a Patron contact in Grandville), or tag along with a teammate doing theirs.")
                if is_patron else
                f"Your epic pool ({epic_name}) opens at level 35 — no unlock needed, just pick it.")
            epic_done = True
        out.append({
            "level": lvl,
            "picks": [{"full_name": p["full_name"],
                       "name": p.get("display_name") or p["full_name"].split(".")[-1],
                       "powerset": (p.get("powerset_full_name") or "").split(".")[-1],
                       "temp": bool(p.get("temp"))} for p in picks],
            "respec_order": respec_here,
            "slots": ev["slots"],                      # enhancement slots granted AT this level
            "slots_running": slots_running,            # X / 67 placed through here
            "milestone": milestone,
            "enh_advice": ev["enh_advice"],
            "io_ok": ev["io_ok"],
            "stats": s,
            "delta": {k: s[k] - (prev[k] if prev else 0) for k in s},
            "tips": tips,
            "play": play,
        })
        prev = s
    return jsonify({"ok": True, "steps": out, "is_eat": is_eat,
                    "eat_type": leveling_schedule.eat_type(archetype),
                    "total_slots": leveling_schedule.TOTAL_ADDED_SLOTS})


@app.route("/discover", methods=["POST"])
def discover():
    body = request.get_json(force=True) or {}
    recs = _discover(body.get("role"), body.get("exposure"), body.get("content"))
    return jsonify({"ok": True, "role": body.get("role"), "recommendations": recs,
                    "note": "The first is the most straightforward route — never the only one."})


@app.route("/health")
def health():
    return jsonify({"ok": True,
                    "archetypes": len(PLAYABLE),
                    "powersets": len(POWERS),
                    "sets": len(ENH_SETS),
                    "ai_enabled": AI_ENABLED,
                    "claude_available": AI_ENABLED
                                        and (claude_bridge._api_creds()[0] is not None
                                             or claude_bridge._find_claude_bin() is not None)})


# ---------------------------------------------------------------------------
# Saved characters-in-progress (a from-scratch character is weeks of real play).
# Distribution-ready: in dev these live in the project's saves/; when packaged as a
# Windows .exe (sys.frozen) the bundle dir is READ-ONLY, so write to %APPDATA% — never
# a hardcoded personal path, so the GitHub/exe build needs no rework.
# ---------------------------------------------------------------------------
def _saves_dir():
    if getattr(sys, "frozen", False):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        d = os.path.join(base, "HeroCompanion", "saves")
    else:
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "saves")
    os.makedirs(d, exist_ok=True)
    return os.path.abspath(d)


def _save_slug(name):
    """Filesystem-safe id from a name. Also blocks path traversal (no slashes/dots)."""
    s = "".join(c if (c.isalnum() or c in "-_") else "-" for c in (name or "untitled").lower())
    s = "-".join(filter(None, s.split("-")))
    return s or "untitled"


def _all_saves():
    out = []
    d = _saves_dir()
    for fn in os.listdir(d):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(d, fn)
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        out.append({"id": fn[:-5], "name": data.get("name") or fn[:-5],
                    "archetype": data.get("archetype"),
                    "primary": data.get("primary_display"),
                    "secondary": data.get("secondary_display"),
                    "level": data.get("level_reached"),
                    # "new" = a character being leveled 1→50 (leveling-in-progress);
                    # "respec"/"import" = a finished level-50 kit. Lets the Continue
                    # screen label the two differently instead of lumping them together.
                    "mode": (data.get("plan") or {}).get("mode"),
                    "updated": os.path.getmtime(path)})
    out.sort(key=lambda x: x["updated"], reverse=True)
    return out


@app.route("/saves", methods=["GET"])
def saves_list():
    return jsonify({"saves": _all_saves()})


@app.route("/saves", methods=["POST"])
def saves_put():
    body = request.get_json(force=True) or {}
    name = (body.get("name") or "Untitled").strip() or "Untitled"
    sid = _save_slug(body.get("id") or name)
    b = body.get("build") or {}
    import first_principles as fp
    data = {"name": name, "archetype": b.get("archetype"),
            "primary_display": b.get("primary_display"),
            "secondary_display": b.get("secondary_display"),
            "level_reached": body.get("level_reached"),
            "plan": body.get("plan") or {},
            "notes": body.get("notes") or "",
            # Version stamp: which optimizer/app produced this save. On resume, a save
            # stamped by an OLDER model triggers the version-drift respec offer — a
            # competently-slotted old build passes the structural under-invest check
            # even though the current solver + game data would build it better.
            "versions": {"app": APP_VERSION, "model": fp.MODEL_VERSION},
            "build": b}
    with open(os.path.join(_saves_dir(), sid + ".json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    return jsonify({"ok": True, "id": sid, "name": name})


@app.route("/saves/<sid>", methods=["GET"])
def saves_get(sid):
    path = os.path.join(_saves_dir(), _save_slug(sid) + ".json")
    if not os.path.exists(path):
        return jsonify({"ok": False, "error": "Save not found."}), 404
    data = json.load(open(path, encoding="utf-8"))
    # Heal the save at serve time: older saves stored slots without io_level/image
    # (field report: resumed builds showed set pieces with no level badge while
    # common IOs showed 50). Enriching on GET fixes every save on disk, not just
    # ones written after the fix — the same pass solve/import already run.
    if isinstance(data.get("build"), dict):
        _fill_slot_images(data["build"])
    # Version drift: the save predates the current optimizer model (or carries no
    # stamp at all — every save from before stamping is by definition old). The
    # client shows the "the optimizer has learned since this was built" respec
    # offer. Not persisted — recomputed against whatever model is current.
    import first_principles as fp
    saved_model = (data.get("versions") or {}).get("model")
    if saved_model is None or (isinstance(saved_model, (int, float))
                               and saved_model < fp.MODEL_VERSION):
        data["version_drift"] = {"saved_model": saved_model,
                                 "current_model": fp.MODEL_VERSION}
    return jsonify({"ok": True, "save": data})


@app.route("/saves/<sid>", methods=["DELETE"])
def saves_delete(sid):
    path = os.path.join(_saves_dir(), _save_slug(sid) + ".json")
    if os.path.exists(path):
        os.remove(path)
    return jsonify({"ok": True})


@app.route("/saves/<sid>/respec", methods=["POST", "DELETE"])
def saves_respec(sid):
    """Persist (or clear) the RESPEC WORKSHEET on a saved character — the plan plus the
    player's check-off progress and applied/undo state — so it survives closing the app and
    can be tracked over days of crafting. Patches only this field, so a checkbox toggle
    doesn't rewrite the whole build."""
    path = os.path.join(_saves_dir(), _save_slug(sid) + ".json")
    if not os.path.exists(path):
        return jsonify({"ok": False, "error": "Save not found."}), 404
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return jsonify({"ok": False, "error": "Save unreadable."}), 500
    if request.method == "DELETE":
        data.pop("respec_worksheet", None)
    else:
        data["respec_worksheet"] = (request.get_json(force=True) or {}).get("worksheet")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    print(f"CoH Build Planner running at http://localhost:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
