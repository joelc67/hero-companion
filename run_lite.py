"""Hero Companion LITE — the capture daemon.

A tiny tray app (light-blue P icon — the full app's P is green) whose only job is
watching the game's chat logs and turning them into the same local event store the full
app reads (%APPDATA%\\HeroCompanion\\gamelog). Runs happily ALONGSIDE the full app: a
heartbeat lock (gamelog.acquire_ingest) makes whichever process is active the single
ingester, so they never race the byte offsets — when the full app's UI is open it
captures, and Lite picks the job back up ~90s after the UI goes quiet.

CAPTURES ALL ACCOUNTS: every account folder with logging enabled is watched — the
account list is re-discovered on every poll, so enabling /logchat on a second (dual-box)
account mid-session starts capturing within one poll cycle, no restart.

No Flask, no solver, no data bundles — just the gamelog module, the chat lexicon, and
a tray icon. Consent flags live in the SHARED state (pulse_capture is its own opt-in,
set from the full app or via --pulse on|off here).

Run:  py run_lite.py            (tray icon; Quit from the menu)
      py run_lite.py --console  (foreground, Ctrl+C to stop)
      py run_lite.py --pulse on (enable channel/pulse capture, then run)
"""
import glob
import json
import os
import sys
import threading
import time

_FROZEN = bool(getattr(sys, "frozen", False))
_HERE = os.path.dirname(os.path.abspath(sys.executable if _FROZEN else __file__))
if not _FROZEN:
    sys.path.insert(0, os.path.join(_HERE, "server"))
    sys.path.insert(0, os.path.join(_HERE, "tools"))
import gamelog  # noqa: E402

APPDIR = os.path.join(os.environ.get("APPDATA", _HERE), "HeroCompanion")
gamelog.STATE_DIR = os.path.join(APPDIR, "gamelog")

LITE_VERSION = "0.1.16"
_UPDATE_VERSION_URL = ("https://raw.githubusercontent.com/joelc67/hero-companion/"
                       "master/lite_version.txt")
_RELEASES_URL = "https://github.com/joelc67/hero-companion/releases"

TERMS_VERSION = 2   # v2 (2026-07-10): discloses public character names on the
#                     boards (Team Leaders) and per-item price contributions.

TERMS = """Companion Lite feeds the live CoH Pulse Boards. Using it means you
accept these terms; if you do not accept them, quit and uninstall it.

WHAT IT CAPTURES (from your game chat log, only while logging is on):
  - your own rewards: XP, influence, drops, merits, badges, defeats
  - recruitment facts from public channels (what's forming, and the
    recruiting CHARACTER's name — it was broadcast publicly in game).
    Never raw chat. Private messages (tells, whispers) are never
    captured.
  - your auction-house lines, so confirmed per-item SALE PRICES can
    feed the public price board.

WHAT IT UPLOADS: that captured play data, and nothing else. Uploads are
tagged with an anonymous install id. Your account login names never
leave this machine (they are replaced with meaningless codes first).
Machine names, file paths, and anything outside the game log are never
read or sent.

WHERE IT GOES: into the project's locked storage that the general
public cannot read. What the PUBLIC board shows: what's forming and
when, the character names of public-channel recruiters (public in game
already), and per-item sale prices. It never shows account names,
anyone's money totals, who sold what, or machine details.

YOUR CONTROLS: turn game logging off any time (/logchat in game) and
nothing is captured; quit Companion Lite and nothing is uploaded;
uninstall and it is gone. That is the whole agreement."""

ABOUT = f"""Companion Lite v{LITE_VERSION}

The little brother of Hero Companion. The FULL app plans, optimizes,
and levels builds; Lite does exactly ONE job: capture your game logs
and feed the live Pulse Boards.

{TERMS}

Runs safely beside the full Hero Companion: whichever is active captures
(a lock guarantees exactly one at a time), the other reads - no
conflicts, no duplicate data, whichever order you start them in.

Blue P = Lite.  Green P = the full Hero Companion."""

POLL_SECONDS = 15


def _already_running():
    """Named-mutex single-instance guard — double-clicking the exe twice was spawning a
    SECOND tray icon (field report: 'cannot get rid of it'; Quit only killed one copy)."""
    import ctypes
    ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\CompanionLiteSingleton")
    return ctypes.windll.kernel32.GetLastError() == 183   # ERROR_ALREADY_EXISTS


_stats = {"started": time.time(), "polls": 0, "owned": 0, "events": 0,
          "recruit": 0, "last_error": None}
_stop = threading.Event()


def _accounts_roots():
    """Same shallow discovery the full app uses: the remembered game root (shared
    settings.json) plus the usual install parents. Never walks a drive."""
    roots = []
    try:
        with open(os.path.join(APPDIR, "settings.json"), encoding="utf-8") as f:
            remembered = (json.load(f) or {}).get("game_root")
        if remembered:
            roots.append(remembered.strip().strip('"'))
    except Exception:  # noqa: BLE001
        pass
    found = []
    for r in roots:
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
        found += [p for p in glob.glob(os.path.join(c, "accounts")) if os.path.isdir(p)]
        found += [p for p in glob.glob(os.path.join(c, "*", "accounts")) if os.path.isdir(p)]
    seen, out = set(), []
    for p in found:
        k = os.path.normcase(os.path.abspath(p))
        if k not in seen:
            seen.add(k)
            out.append(os.path.abspath(p))
    return out


def _watch_dirs(state):
    """EVERY account Logs folder that has files — the union of what the full app
    configured and everything discoverable, re-checked each poll so a dual-box account
    that enables /logchat mid-session starts capturing without a restart."""
    dirs = {os.path.normcase(d): d for d in (state.get("watch_dirs") or [])
            if os.path.isdir(d)}
    for acct in gamelog.find_log_accounts(_accounts_roots()):
        if acct.get("has_logs"):
            dirs.setdefault(os.path.normcase(acct["log_dir"]), acct["log_dir"])
    return list(dirs.values())


AUTOPUBLISH_SECONDS = 15 * 60


def _maybe_autopublish():
    """The owner's board lives ONLINE, not on the game machine: when a publish token is
    present (owner machines only — everyone else never touches the network), keep the
    live page current automatically. At most one publish per AUTOPUBLISH_SECONDS, and
    only when capture has ingested something since the last one (plus one catch-up
    publish shortly after launch, so a reboot never leaves the live board stale)."""
    if _stats["events"] <= _stats.get("published_events", -1):
        return
    if time.time() - _stats.get("published_ts", 0) < AUTOPUBLISH_SECONDS:
        return
    if not _publish_token():                  # defined below; resolved at call time
        return
    _stats["published_ts"] = time.time()      # set even on failure: never hammer the API
    import build_pulse_boards
    build_pulse_boards.OUT = os.path.join(APPDIR, "pulse_boards_public.html")
    build_pulse_boards.APPDIR = APPDIR
    out, _n = build_pulse_boards.build(state_dir=gamelog.STATE_DIR, public=True)
    with open(out, encoding="utf-8") as f:
        status = _publish_live(f.read())
    if status == "ok":
        _stats["published_events"] = _stats["events"]
    else:
        _stats["last_error"] = f"autopublish {status}"


# ── Board feed: capture → GitHub inbox (private) → rendered live board ───────────────
# Joel's architecture: ANY player's Lite uploads its capture over HTTPS to the
# project's PRIVATE inbox repo (the "secure database") — no accounts, tokens, or setup
# for the user, and nothing in an upload is readable by the general public (the inbox
# is private; only the rendered, scrubbed board page ever becomes public). A GitHub
# Action imports fresh uploads into the live board within minutes. The upload key
# baked below is scoped to the inbox ONLY — it cannot write the public site.
# Consent is Joel-doctrine: informed opt-in in the tray, asked once, remembered,
# reversible. publish_token.txt remains a dormant power-user path.
UPLOAD_SECONDS = 300
_INBOX_REPO = "joelc67/hero-companion-inbox"


def _inbox_token():
    """The product's upload key — scoped to the private inbox repo ONLY (it cannot
    write the public site). Bundled OBFUSCATED at release build time as
    data/inbox_key.bin, which is gitignored: the key lives in release builds, never in
    the repo. Absent (source runs, forks) the feed is simply inert."""
    try:
        base = os.path.join(getattr(sys, "_MEIPASS", _HERE), "data") if _FROZEN \
            else os.path.join(_HERE, "data")
        with open(os.path.join(base, "inbox_key.bin"), "rb") as f:
            raw = f.read()
        return bytes(b ^ 0x5A for b in raw).decode("ascii").strip() or None
    except Exception:  # noqa: BLE001
        return None


def _install_id(st):
    """Anonymous per-install id — never a hostname or username."""
    iid = st.get("install_id")
    if not iid:
        import uuid
        iid = uuid.uuid4().hex[:16]
        st["install_id"] = iid
        gamelog.save_state(st)
    return iid


def _gh_request(method, path, body=None):
    import urllib.request
    req = urllib.request.Request(
        f"https://api.github.com/repos/{_INBOX_REPO}/{path}",
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Authorization": f"token {_inbox_token()}",
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "CompanionLite"},
        method=method)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


def _inbox_put(path, data, message, need_sha=False):
    import base64
    body = {"message": message,
            "content": base64.b64encode(data).decode("ascii")}
    if need_sha:
        try:
            body["sha"] = _gh_request("GET", f"contents/{path}").get("sha")
        except Exception:  # noqa: BLE001 — file doesn't exist yet: create it
            pass
    _gh_request("PUT", f"contents/{path}", body)


def _pseudonym(iid, account):
    """Account LOGIN names never leave the machine — the board only needs a stable
    GROUPING key per account, so uploads carry an unlinkable per-install pseudonym."""
    import hashlib
    return "a" + hashlib.sha256(f"{iid}|{account}".encode("utf-8")).hexdigest()[:12]


def _anonymize_chunk(chunk, iid):
    """Rewrite the 'account' field of every event line to its pseudonym."""
    out = []
    for line in chunk.decode("utf-8", "replace").splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
            if ev.get("account"):
                ev["account"] = _pseudonym(iid, ev["account"])
            out.append(json.dumps(ev))
        except Exception:  # noqa: BLE001 — an unparseable line is dropped, never leaked
            continue
    return ("\n".join(out) + "\n").encode("utf-8") if out else b""


def _maybe_upload():
    """Send NEW capture bytes to the inbox — only with consent, only when the store
    grew, at most once per UPLOAD_SECONDS. Incremental: each upload is a small chunk
    file of just the new lines (the renderer stitches chunks in order); the sent byte
    offset persists in state, so restarts never re-send. If the store ever shrinks
    (rebuilt), a reset chunk replaces the source's history. Account login names are
    pseudonymized BEFORE upload — they never leave the machine."""
    st = gamelog.load_state()
    # Consent model (Joel's): the TERMS are the consent — using the app IS agreeing to
    # feed the live board. Uploads never start before the terms have been shown once.
    if not _inbox_token() or st.get("terms_version", 0) < TERMS_VERSION:
        return
    if time.time() - _stats.get("uploaded_ts", 0) < UPLOAD_SECONDS:
        return
    src = os.path.join(gamelog.STATE_DIR, "events.jsonl")
    size = os.path.getsize(src) if os.path.isfile(src) else 0
    offset = int(st.get("upload_offset", 0))
    if offset > size:
        # store rebuilt (rare): start over under a FRESH install id so the pipeline
        # can never mix pre- and post-rebuild history; the stale source ages out.
        import uuid
        st["install_id"] = uuid.uuid4().hex[:16]
        st["upload_offset"] = offset = 0
        gamelog.save_state(st)
    if size == 0 or size == offset:
        return
    _stats["uploaded_ts"] = time.time()
    try:
        with open(src, "rb") as f:
            f.seek(offset)
            chunk = f.read()
        if not chunk.endswith(b"\n"):                  # never ship a torn last line
            cut = chunk.rfind(b"\n")
            if cut < 0:
                return
            chunk = chunk[:cut + 1]
        sent = len(chunk)                               # local bytes consumed
        iid = _install_id(st)
        chunk = _anonymize_chunk(chunk, iid)
        if not chunk:
            return
        # chunk named by its LOCAL byte offset: a retried upload overwrites the same
        # file instead of creating a duplicate — events can never double-count.
        _inbox_put(f"sources/{iid}/c{offset:012d}.jsonl", chunk,
                   f"capture from {iid}", need_sha=True)
        chars = {_pseudonym(iid, a): c
                 for a, c in (st.get("characters") or {}).items()}
        # char_shards holds only WITNESSED characters (auto-detected from the game's
        # own playerslot.txt) — character names are public in game; the roster is not
        # read beyond lookups and never uploaded.
        char_shards = st.get("char_shards") or {}
        state_body = json.dumps({"characters": chars, "char_shards": char_shards,
                                 "shards": sorted(set(char_shards.values()))}).encode()
        # Push state ONLY when it changed (field report 2026-07-10): the
        # unconditional every-cycle state push doubled the inbox's commit —
        # and therefore CI-run — count all night for identical content.
        import hashlib as _hl
        state_hash = _hl.sha256(state_body).hexdigest()
        if st.get("state_upload_hash") != state_hash:
            _inbox_put(f"sources/{iid}/state.json", state_body,
                       f"state from {iid}", need_sha=True)
            st["state_upload_hash"] = state_hash
            gamelog.save_state(st)
        st = gamelog.load_state()                       # re-load: capture may have run
        st["upload_offset"] = offset + sent
        gamelog.save_state(st)
        _stats["uploaded_bytes"] = _stats.get("uploaded_bytes", 0) + len(chunk)
        _stats["uploaded_last"] = time.strftime("%H:%M:%S")
    except Exception as e:  # noqa: BLE001
        _stats["last_error"] = f"board feed {type(e).__name__}: {e}"


def _capture_loop():
    while not _stop.is_set():
        try:
            _stats["polls"] += 1
            if gamelog.acquire_ingest("lite"):
                _stats["owned"] += 1
                st = gamelog.load_state()
                for d in _watch_dirs(st):
                    events, _rep = gamelog.ingest(d, st)
                    _stats["events"] += len(events)
                    _stats["recruit"] += sum(1 for e in events if e.get("type") == "recruit")
                gamelog.save_state(st)
            _maybe_upload()
            _maybe_autopublish()
        except Exception as e:  # noqa: BLE001 — the daemon never dies on one bad poll
            _stats["last_error"] = f"{type(e).__name__}: {e}"
        _stop.wait(POLL_SECONDS)


def _status_text():
    st = gamelog.load_state()
    up = int((time.time() - _stats["started"]) / 60)
    owner = gamelog.ingest_owner() or {}
    who = "Lite" if owner.get("tag") == "lite" else (
        "full app" if owner.get("tag") == "full" else "idle")
    watching = _watch_dirs(st)
    accounts = sorted({os.path.basename(os.path.dirname(d)) for d in watching})
    up = _stats.get("uploaded_last")
    if _publish_token():
        board = f"ONLINE (auto-publish every {AUTOPUBLISH_SECONDS // 60} min) — {_PUBLISH_LIVE_URL}"
    elif not _inbox_token():
        board = "feed inert (no upload key in this build)"
    else:
        board = ("feeding the live board"
                 + (f" (last upload {up}, {_stats.get('uploaded_bytes', 0):,} bytes "
                    f"this run)" if up else
                    f" (uploads within {UPLOAD_SECONDS // 60} min of new play)"))
    return (f"Companion Lite — up {up} min\n"
            f"capture owner: {who}\n"
            f"events captured this run: {_stats['events']} "
            f"({_stats['recruit']} recruitment)\n"
            f"pulse capture (channels): {'ON' if st.get('pulse_capture', True) is not False else 'off'}\n"
            f"board home: {board}\n"
            f"watching {len(watching)} log folder(s): {', '.join(accounts) or 'none — run /logchat 1 in game'}"
            + (f"\nlast error: {_stats['last_error']}" if _stats["last_error"] else ""))


# ── in-game menu: one-click logging from INSIDE the game ─────────────────────────────
# A popmenu (.mnu) written into the game's data override folder — the sanctioned mod
# surface (same mechanism as FastTravel/VidiotMaps; file overlays only, never injection).
# Syntax taken from the client's own texts/english/menus/fasttravel.mnu; command forms
# (/logchat toggle, /build_save_file) are the ones our Play Log setup guide validated.
# CONSENT RULE (Joel's): a pop-up asks permission BEFORE the first write to the game
# folder; the choice is remembered and fully reversible (Remove deletes the files).
_MENU_TEXT = """\
// Hero Companion in-game menu (generated by Companion Lite - safe to delete).
// Use in game:  /popmenu Companion      (restart the game client after install)
// Handy bind:   /bind ctrl+h "popmenu Companion"
Menu "Companion"
{
\tTitle "Hero Companion"
\tOption "Toggle chat logging (on / off)" "logchat"
\tOption "Save this build for Hero Companion" "build_save_file"
\tDivider
\tOption "What is this? (logging feeds the live Pulse Boards)" "nop"
}
"""


_OUR_MENU_MARKER = "generated by Companion Lite"


def _game_menu_paths():
    """Where the .mnu belongs in each discovered game install:
    <game root>\\data\\texts\\English\\Menus\\companion.mnu"""
    out = []
    for accounts in _accounts_roots():
        game_root = os.path.dirname(accounts)
        out.append(os.path.join(game_root, "data", "texts", "English", "Menus",
                                "companion.mnu"))
    return out


def _cleanup_our_menus():
    """Remove every companion.mnu we ever wrote across all discovered installs — a prior
    broken/partial attempt, a stale state entry, whatever. Only deletes files carrying our
    marker, so a user's own popmenu is never touched. Returns how many were removed."""
    seen, removed = set(), 0
    candidates = list(_game_menu_paths())
    candidates += (gamelog.load_state().get("ingame_menu") or {}).get("installed", [])
    for p in candidates:
        key = os.path.normcase(os.path.abspath(p))
        if key in seen or not os.path.isfile(p):
            continue
        seen.add(key)
        try:
            with open(p, encoding="utf-8") as f:
                is_ours = _OUR_MENU_MARKER in f.read()
            if is_ours:
                os.remove(p)
                removed += 1
        except Exception:  # noqa: BLE001
            pass
    return removed


def _msgbox_yesno(title, text):
    return _messagebox(title, text, yesno=True)


def _msgbox_info(title, text):
    """Native dialog — tray balloon toasts are suppressed on many Windows setups."""
    _messagebox(title, text, yesno=False)


def _messagebox(title, text, yesno=False):
    """Native MessageBox. MUST be called from a NON-tray-callback thread (see _safe) so
    the tray menu's mouse capture is already released — otherwise the dialog appears but
    button clicks never reach it (field report: Yes/No did nothing, fullscreen game,
    Task-Manager-only kill). MB_SETFOREGROUND pulls it above the game."""
    import ctypes
    MB_YESNO, MB_OK = 0x4, 0x0
    MB_ICONQUESTION, MB_ICONINFO = 0x20, 0x40
    MB_TOPMOST, MB_SETFOREGROUND = 0x40000, 0x10000
    IDYES = 6
    flags = ((MB_YESNO | MB_ICONQUESTION) if yesno else (MB_OK | MB_ICONINFO)) \
        | MB_TOPMOST | MB_SETFOREGROUND
    return ctypes.windll.user32.MessageBoxW(0, text, title, flags) == IDYES


def install_ingame_menu(assume_yes=False):
    """Write companion.mnu into each game install. Returns a human status string.
    assume_yes=True: the caller already got consent (the native submenu 'Yes, install
    it' click), so skip the modal — only the folder picker may still appear if no game
    is found. This is the reliable path; the modal path is a legacy fallback."""
    paths = _game_menu_paths()
    if not paths:
        # Auto-discovery failed (game lives somewhere unusual) — ask, don't give up.
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
            picked = filedialog.askdirectory(
                title="Companion Lite — pick your City of Heroes game folder "
                      "(the one containing 'accounts')")
            root.destroy()
        except Exception:  # noqa: BLE001
            picked = None
        if picked and os.path.isdir(os.path.join(picked, "accounts")):
            # remember it in the SHARED settings so capture discovery gains it too
            sp = os.path.join(APPDIR, "settings.json")
            try:
                with open(sp, encoding="utf-8") as f:
                    settings = json.load(f) or {}
            except Exception:  # noqa: BLE001
                settings = {}
            settings["game_root"] = picked
            os.makedirs(APPDIR, exist_ok=True)
            with open(sp, "w", encoding="utf-8") as f:
                json.dump(settings, f)
            paths = _game_menu_paths()
        if not paths:
            return ("No game install found. Expected a folder containing 'accounts' "
                    "(e.g. C:\\Games\\HC2). Use Install again to retry with the picker.")
    if not assume_yes:
        listing = "\n".join(f"  {p}" for p in paths)
        if not _msgbox_yesno(
                "Companion Lite — install in-game menu?",
                "This writes ONE small text file (a popmenu) into your game's data "
                "folder so you can enable chat logging from inside the game:\n\n"
                + listing + "\n\nEverything stays on this machine; NOTHING is shared. "
                "'Remove' deletes it again. Install?"):
            return "Not installed."
    _cleanup_our_menus()               # wipe any prior/broken attempt first — self-healing
    done = []
    for p in paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(_MENU_TEXT)
        done.append(p)
    st = gamelog.load_state()
    st["ingame_menu"] = {"installed": done, "ts": time.time()}
    gamelog.save_state(st)
    return "INSTALLED::" + "\n".join(done)


def remove_ingame_menu():
    removed = _cleanup_our_menus()
    st = gamelog.load_state()
    st.pop("ingame_menu", None)
    gamelog.save_state(st)
    return f"Removed {removed} menu file(s)."


_PUBLISH_REPO = "joelc67/hero-companion"
_PUBLISH_PATH = "docs/pulse/index.html"
_PUBLISH_LIVE_URL = "https://joelc67.github.io/hero-companion/pulse/"


def _publish_token():
    """The owner's GitHub token, read from a LOCAL file only (never bundled, never in the
    repo). Absent for everyone but the owner, so the publish feature is inert by default."""
    p = os.path.join(APPDIR, "publish_token.txt")
    try:
        with open(p, encoding="utf-8") as f:
            t = f.read().strip()
        return t or None
    except Exception:  # noqa: BLE001
        return None


def _publish_live(html):
    """Owner-sync: PUT the generated board HTML to the Pages file via the GitHub contents
    API, so joelc67.github.io/.../pulse shows THIS machine's data. Publishing your own
    data to your own public site — one explicit click per publish. Returns a status str."""
    import base64
    import urllib.request
    token = _publish_token()
    if not token:
        return "no-token"
    api = f"https://api.github.com/repos/{_PUBLISH_REPO}/contents/{_PUBLISH_PATH}"
    hdr = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json",
           "User-Agent": "CompanionLite"}
    sha = None
    try:                                             # current file SHA (needed to update)
        cur = json.load(urllib.request.urlopen(
            urllib.request.Request(api + "?ref=master", headers=hdr), timeout=15))
        sha = cur.get("sha")
    except Exception:  # noqa: BLE001 — file may not exist yet; create it
        sha = None
    payload = {"message": "Publish Pulse Boards from Companion Lite",
               "content": base64.b64encode(html.encode("utf-8")).decode("ascii"),
               "branch": "master"}
    if sha:
        payload["sha"] = sha
    try:
        req = urllib.request.Request(api, data=json.dumps(payload).encode(),
                                     headers={**hdr, "Content-Type": "application/json"},
                                     method="PUT")
        urllib.request.urlopen(req, timeout=30).read()
        return "ok"
    except Exception as e:  # noqa: BLE001
        return f"failed: {e}"


def _latest_lite_asset():
    """(version, exe_download_url) for the newest lite-v* release, or (None, None).
    Lite releases are pre-releases, so /releases/latest won't find them — query the list."""
    import urllib.request
    try:
        data = json.load(urllib.request.urlopen(
            "https://api.github.com/repos/joelc67/hero-companion/releases", timeout=8))
    except Exception:  # noqa: BLE001
        return None, None
    for rel in data:
        tag = rel.get("tag_name", "")
        if tag.startswith("lite-v"):
            for a in rel.get("assets", []):
                if a.get("name", "").lower().endswith(".exe"):
                    return tag.replace("lite-v", ""), a.get("browser_download_url")
    return None, None


def _self_update(url):
    """Download the new exe and swap it in via a detached updater script (a running exe
    can't overwrite itself). Only works on the FROZEN build. Returns a status string.

    SAFETY (0.1.8 regression: an update left the user with nothing running): the new exe
    is fully downloaded AND validated (real Windows PE, sane size) BEFORE anything is
    stopped. Only THIS process (by exact PID) is ever waited on — no kill-by-name, so it
    can never touch the full Hero Companion or anything else. If the swap fails, the batch
    still relaunches the existing exe, so Lite always comes back."""
    import subprocess
    import urllib.request
    if not _FROZEN:
        return "Self-update only works in the packaged app (running from source)."
    target = os.path.abspath(sys.executable)
    newexe = target + ".new"
    try:
        with urllib.request.urlopen(url, timeout=120) as r, open(newexe, "wb") as f:
            f.write(r.read())
    except Exception as e:  # noqa: BLE001
        return f"Download failed (nothing was changed): {e}"
    # VALIDATE before we stop anything: a real onefile exe is a PE ("MZ") and megabytes.
    try:
        ok = os.path.getsize(newexe) > 1_000_000
        with open(newexe, "rb") as f:
            ok = ok and f.read(2) == b"MZ"
    except Exception:  # noqa: BLE001
        ok = False
    if not ok:
        try:
            os.remove(newexe)
        except OSError:
            pass
        return "The downloaded update looked corrupt, so nothing was changed. Try again."
    bat = os.path.join(os.path.dirname(target), "_lite_update.bat")
    pid = os.getpid()
    # Wait for THIS exact process (by PID) to exit, then swap and relaunch. No taskkill by
    # image name — only our own PID is ever involved. RELAUNCH VIA EXPLORER: the previous
    # `start` from a windowless helper silently no-op'd (a detached script has no console
    # session for `start`), so the swap completed but the app never came back (field
    # report: "stalled at the same spot"). explorer.exe launches the exe in the user's
    # shell session — has a console, runs de-elevated, and antivirus (Bitdefender here)
    # treats an Explorer-initiated launch far more kindly than a script spawning a fresh
    # download. CREATE_NO_WINDOW (not DETACHED) gives the helper a hidden console so its
    # own commands run reliably.
    with open(bat, "w", encoding="utf-8") as f:
        f.write("@echo off\r\n"
                ":wait\r\n"
                f'tasklist /FI "PID eq {pid}" | find "{pid}" >nul '
                "&& (ping -n 2 127.0.0.1 >nul & goto wait)\r\n"
                "ping -n 2 127.0.0.1 >nul\r\n"
                f'move /Y "{newexe}" "{target}" >nul 2>&1\r\n'
                f'explorer.exe "{target}"\r\n'
                'del "%~f0"\r\n')
    subprocess.Popen(["cmd", "/c", bat], creationflags=0x08000000)   # CREATE_NO_WINDOW
    _stop.set()
    return "updating"


def _open_in_default_browser(path):
    """Open a local HTML file in the user's DEFAULT HTTP BROWSER — not whatever
    app owns the .html FILE association. webbrowser.open("file:///…") routes
    through ShellExecute and the .html association, so on a machine where a text
    editor has claimed .html the page opens as raw source in the editor (field
    report, 2026-07-08: the update-check result opened "in a text file"). The
    browser that handles http links is what the user means by "my browser"."""
    import subprocess
    import webbrowser
    url = "file:///" + path.replace("\\", "/")
    try:
        import winreg
        with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\Shell\Associations"
                r"\UrlAssociations\http\UserChoice") as k:
            progid = winreg.QueryValueEx(k, "ProgId")[0]
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,
                            progid + r"\shell\open\command") as k:
            cmd = winreg.QueryValueEx(k, None)[0]
        exe = cmd.split('"')[1] if cmd.startswith('"') else cmd.split()[0]
        subprocess.Popen([exe, url])
    except Exception:  # noqa: BLE001 — any registry surprise: old behavior
        webbrowser.open(url)


def _result_page(title, body_html):
    """Show a result in the BROWSER instead of a modal dialog. A browser window is a
    normal top-level app the user can always alt-tab to and click — unlike a modal
    popped from a tray menu, which can lose input to the fullscreen game (field report)."""
    p = os.path.join(APPDIR, "lite_message.html")
    os.makedirs(APPDIR, exist_ok=True)
    html = (f"<!doctype html><meta charset='utf-8'><title>{title}</title>"
            "<body style='background:#0c1220;color:#dbe4f5;font-family:Segoe UI,sans-serif;"
            "max-width:640px;margin:40px auto;padding:0 20px;line-height:1.6'>"
            f"<h2 style='color:#5abeff'>{title}</h2>{body_html}</body>")
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    _open_in_default_browser(p)


def _make_icon_image():
    """Light-blue circle with a white P — the full app's tray P is green, so the two
    read as siblings at a glance."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, 62, 62], fill=(90, 190, 255, 255))       # light blue vs the full app's green
    font = None
    for cand in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"):
        try:
            font = ImageFont.truetype(cand, 40)
            break
        except Exception:  # noqa: BLE001
            continue
    if font:
        d.text((32, 30), "P", font=font, anchor="mm", fill=(255, 255, 255, 255))
    else:
        d.text((22, 16), "P", fill=(255, 255, 255, 255))
    return img


def _run_tray():
    import pystray
    img = _make_icon_image()

    def _safe(fn):
        """Run each menu action on its OWN thread so the pystray callback returns
        instantly — the tray menu then closes and releases its mouse capture BEFORE any
        dialog appears (the fix for 'Yes/No did nothing'). A short settle covers the
        menu teardown. Exceptions surface as a dialog instead of vanishing."""
        def _body(icon, item):
            time.sleep(0.2)                  # let the tray menu finish closing
            try:
                fn(icon, item)
            except Exception as e:  # noqa: BLE001
                _result_page("Companion Lite — error",
                             f"<p>That action failed:</p><pre>{type(e).__name__}: {e}</pre>")

        def wrapped(icon, item):
            threading.Thread(target=_body, args=(icon, item), daemon=True).start()
        return wrapped

    def _quit(icon, _item):
        _stop.set()
        icon.stop()

    def _show_status(icon, _item):
        _result_page("Companion Lite — status",
                     "<pre style='font-size:15px;white-space:pre-wrap'>"
                     + _status_text() + "</pre>")

    def _open_live_board(_icon, _item):
        import webbrowser
        webbrowser.open(_PUBLISH_LIVE_URL)

    def _install_confirm(_icon, _item):
        # Consent is the native submenu click "Yes, install it" — no modal to hang.
        # install_ingame_menu self-heals (wipes any prior/broken attempt) then writes fresh.
        msg = install_ingame_menu(assume_yes=True)
        if msg.startswith("INSTALLED::"):
            files = "".join(f"<li><code>{p}</code></li>"
                            for p in msg[len("INSTALLED::"):].splitlines())
            _result_page("Companion Lite — menu installed",
                         "<p>The in-game menu file is written (any earlier broken attempt "
                         f"was cleaned up first):</p><ul>{files}</ul>"
                         "<h3 style='color:#f0b93b'>Two steps left — the game can only load "
                         "the menu on a fresh start:</h3>"
                         "<ol style='font-size:16px'>"
                         "<li><b>Fully restart the City of Heroes client</b> (all the way to "
                         "the login screen and back in — a character reselect is not "
                         "enough).</li>"
                         "<li>In game, type <code>/popmenu Companion</code> and press Enter. "
                         "The Hero Companion menu appears.</li></ol>"
                         "<p style='color:#8fa0bd'>Tip: <code>/bind ctrl+h \"popmenu "
                         "Companion\"</code> puts it on Ctrl+H forever. Remove any time from "
                         "the tray → In-game logging menu → Remove it.</p>")
        else:
            _result_page("Companion Lite — in-game menu",
                         f"<p>{msg.replace(chr(10), '<br>')}</p>")

    def _install_explain(_icon, _item):
        paths = _game_menu_paths() or ["(no game folder found yet — choosing "
                                       "'Yes, install it' will let you pick it)"]
        listing = "".join(f"<li><code>{p}</code></li>" for p in paths)
        _result_page("What the in-game menu does",
                     "<p>It writes ONE small text file (a popmenu) into your game's data "
                     "folder so you can turn chat logging on from inside the game:</p>"
                     f"<ul>{listing}</ul>"
                     "<p>In game after a client restart: <code>/popmenu Companion</code>. "
                     "Logging feeds the live Pulse Boards (see the terms under About). "
                     "It changes nothing else and is fully reversible.</p>")

    def _remove_menu(icon, _item):
        _result_page("Companion Lite — in-game menu", f"<p>{remove_ingame_menu()}</p>")

    def _about(icon, _item):
        _result_page("About Companion Lite",
                     "<pre style='font-size:15px;white-space:pre-wrap'>" + ABOUT + "</pre>")

    def _check_updates(icon, _item):
        # A user CLICK, never automatic — same policy as the full app. If a newer Lite
        # exists, download + swap it in place (no more manual redownload). Falls back to
        # the download link if self-update can't run (e.g. running from source).
        def _t(v):
            return tuple(int(x) for x in v.split(".") if x.isdigit())
        latest, url = _latest_lite_asset()
        if not latest:
            _result_page("Companion Lite — updates",
                         "<p>Couldn't reach the update server — try again later.</p>")
            return
        if _t(latest) <= _t(LITE_VERSION):
            _result_page("Companion Lite — updates",
                         f"<p>You're up to date (v{LITE_VERSION}).</p>")
            return
        status = _self_update(url) if url else "no-asset"
        if status == "updating":
            _result_page("Companion Lite — updating",
                         f"<p>Downloading <b>v{latest}</b> and restarting Companion "
                         "Lite…</p><p style='color:#8fa0bd'>The blue P will reappear in "
                         "your tray in a few seconds.</p>")
            time.sleep(1.0)
            icon.stop()
        else:
            _result_page("Companion Lite — updates",
                         f"<p>Update available: <b>v{latest}</b> (you have v{LITE_VERSION}).</p>"
                         f"<p>Auto-update: {status}</p>"
                         f"<p><a href='{_RELEASES_URL}'>Download it manually →</a></p>")

    install_sub = pystray.Menu(
        pystray.MenuItem("What this does / where", _safe(_install_explain)),
        pystray.MenuItem("Yes, install it", _safe(_install_confirm)),
        pystray.MenuItem("Remove it", _safe(_remove_menu)))
    items = [pystray.MenuItem("Open the live Pulse Board", _safe(_open_live_board)),
             pystray.MenuItem("In-game logging menu", install_sub),
             pystray.MenuItem("Status", _safe(_show_status)),
             pystray.MenuItem("About Companion Lite (terms)", _safe(_about)),
             pystray.MenuItem("Check for updates", _safe(_check_updates)),
             pystray.MenuItem("Quit", _quit)]
    menu = pystray.Menu(*items)
    icon = pystray.Icon("CompanionLite", img, f"Companion Lite v{LITE_VERSION}", menu)
    # Running Lite IS the consent (single-purpose capture tool: use it or quit it), so it
    # always captures — including public-channel recruitment. No toggle to discover.
    _st = gamelog.load_state()
    if _st.get("pulse_capture") is not True:
        _st["pulse_capture"] = True
        gamelog.save_state(_st)
    # THE TERMS ARE THE CONSENT (Joel's model): accept them by using the app, or quit
    # and uninstall. Shown once per terms version; uploading never starts before the
    # terms have been shown (enforced in _maybe_upload).
    if _st.get("terms_version", 0) < TERMS_VERSION:
        _st["terms_version"] = TERMS_VERSION
        gamelog.save_state(_st)
        try:
            _result_page("Companion Lite — terms",
                         "<pre style='font-size:15px;white-space:pre-wrap'>" + TERMS
                         + "</pre><p><b>Keep running Companion Lite and you accept "
                         "these terms.</b> If you do not accept them: tray (blue P) → "
                         "Quit, then uninstall. These terms stay available under "
                         "About Companion Lite.</p>")
        except Exception:  # noqa: BLE001
            pass
    _stats["started"] = time.time()          # anchor uptime at tray start, not import
    t = threading.Thread(target=_capture_loop, daemon=True)
    t.start()
    icon.run()


def main():
    args = sys.argv[1:]
    if "--build-board" in args:
        # Smoke-test hook: build the board in the SAME frozen/windowed conditions the tray
        # uses (stdout=None), write a marker with the event count, exit 0/1. Lets a release
        # be verified as the actual exe before publishing.
        try:
            import build_pulse_boards
            build_pulse_boards.OUT = os.path.join(APPDIR, "pulse_boards.html")
            build_pulse_boards.APPDIR = APPDIR
            _out, n = build_pulse_boards.build(state_dir=gamelog.STATE_DIR)
            with open(os.path.join(APPDIR, "board_build_result.txt"), "w",
                      encoding="utf-8") as f:
                f.write(f"OK {n}")
            sys.exit(0)
        except Exception as e:  # noqa: BLE001
            os.makedirs(APPDIR, exist_ok=True)
            with open(os.path.join(APPDIR, "board_build_result.txt"), "w",
                      encoding="utf-8") as f:
                f.write(f"FAIL {type(e).__name__}: {e}")
            sys.exit(1)
    if "--feed-once" in args:
        # Release-smoke/field diagnostic: run ONE capture+upload cycle NOW and record
        # the outcome (windowed exe has no stdout). Exercises log ingest, shard
        # auto-detect, key load, terms gate, anonymization, and the real inbox
        # round-trip — the product's core promises, end to end.
        os.makedirs(APPDIR, exist_ok=True)
        st = gamelog.load_state()
        if gamelog.acquire_ingest("lite"):
            for d in _watch_dirs(st):
                gamelog.ingest(d, st)
            gamelog.save_state(st)
        _stats["uploaded_ts"] = 0
        _maybe_upload()
        st2 = gamelog.load_state()
        msg = (f"v{LITE_VERSION} key={'ok' if _inbox_token() else 'MISSING'} "
               f"terms={st.get('terms_version', 0)} "
               f"offset={st2.get('upload_offset', 0)} "
               f"err={_stats.get('last_error')}")
        with open(os.path.join(APPDIR, "feed_result.txt"), "w", encoding="utf-8") as f:
            f.write(msg)
        sys.exit(1 if _stats.get("last_error") else 0)
    if "--pulse" in args:
        val = args[args.index("--pulse") + 1].lower() in ("on", "1", "true")
        st = gamelog.load_state()
        st["pulse_capture"] = val
        gamelog.save_state(st)
        print(f"pulse_capture set to {val}")
    if "--console" in args:
        print(_status_text())
        t = threading.Thread(target=_capture_loop, daemon=True)
        t.start()
        try:
            while True:
                time.sleep(30)
                print(_status_text().replace("\n", " | "))
        except KeyboardInterrupt:
            _stop.set()
        return
    if _already_running():
        _result_page("Companion Lite",
                     "<p>Companion Lite is already running.</p><p>Look for the blue P in "
                     "your tray (it may be behind the ^ overflow arrow). Use its Quit "
                     "to stop it.</p>")
        return
    try:
        _run_tray()
    except Exception:  # noqa: BLE001 — no pystray → console fallback
        print("(tray unavailable — running in console mode)")
        sys.argv = [sys.argv[0], "--console"]
        main()


if __name__ == "__main__":
    main()
