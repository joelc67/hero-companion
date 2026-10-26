"""Shared game-name lookup for patch_display_names.py and reality_check_names.py.

GAME-FIRST: the authority is a Bin Crawler export of the installed client
(per-set index.json: `powers` parallel to `power_display_names`, plus the set's
own `display_name`). Pass the export to read with --export (default: the
committed-location out_full); exports of the live client and the open beta are
both valid inputs.

The trap this module exists to close: client INTERNAL names are historical and
REUSED. In Tactical Arrow the record internally named Gymnastics is displayed
"Oil Slick Arrow", and the real Gymnastics sits under another internal name.
Joining by internal name alone would "rename" our Gymnastics to Oil Slick Arrow.
So a mismatch is a RENAME only when the game's set no longer shows our name on
any power; if our name is still shown by another power in the same game set,
it is an internal-name SWAP and our name stays.
"""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_EXPORT = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
ALIASES = os.path.join(ROOT, "tools", "gamedata", "power_aliases.json")


def norm(s):
    return " ".join((s or "").split()).strip().lower()


def game_maps(export=DEFAULT_EXPORT, our_full_names=()):
    """(power full_name -> game display, set full_name -> game display,
    game set full_name -> {normalized displays shown in that set})."""
    gp, gpool, set_shows = {}, {}, {}
    for idx in glob.glob(os.path.join(export, "**", "index.json"), recursive=True):
        try:
            r = json.load(open(idx, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if r.get("key") and r.get("display_name"):
            gpool[r["key"]] = r["display_name"]
        names, disp = r.get("powers") or [], r.get("power_display_names") or []
        # never zip mismatched parallel arrays (would corrupt names)
        if len(names) != len(disp):
            continue
        for fn, d in zip(names, disp):
            if d:
                gp[fn] = d
                set_shows.setdefault(fn.rsplit(".", 1)[0], set()).add(norm(d))
    # our name -> game key where they diverge (Temporal_Manipulation = Time_Manipulation)
    game_key = {fn: fn for fn in gp}
    if os.path.exists(ALIASES):
        for our_fn, g in json.load(open(ALIASES, encoding="utf-8")).get("aliases", {}).items():
            if our_fn not in gp and g in gp:
                game_key[our_fn] = g
    # namespace divergence: our Incarnate_Pets.* is the game's Incarnate.* (same set, same leaf)
    for our_fn in our_full_names:
        if our_fn not in game_key and our_fn.startswith("Incarnate_Pets."):
            g = "Incarnate." + our_fn[len("Incarnate_Pets."):]
            if g in gp:
                game_key[our_fn] = g
    return gp, gpool, set_shows, game_key


def classify(our_fn, our_display, gp, set_shows, game_key):
    """'unmatched' | 'ok' | 'rename' | 'swap' for one of our powers."""
    g = game_key.get(our_fn)
    if g is None:
        return "unmatched", None
    shown = gp[g]
    if norm(shown) == norm(our_display):
        return "ok", shown
    if norm(our_display) in set_shows.get(g.rsplit(".", 1)[0], ()):
        return "swap", shown
    return "rename", shown
