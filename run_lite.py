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

LITE_VERSION = "0.1.8"
_UPDATE_VERSION_URL = ("https://raw.githubusercontent.com/joelc67/hero-companion/"
                       "master/lite_version.txt")
_RELEASES_URL = "https://github.com/joelc67/hero-companion/releases"

ABOUT = f"""Companion Lite v{LITE_VERSION}

The little brother of Hero Companion. The FULL app plans, optimizes, and
levels builds; Lite does exactly ONE job: quietly capture your game logs
into local intel that feeds your Pulse Boards page.

What it captures (only with logging on and your consent):
  - your own rewards: XP, influence, drops, merits, badges, defeats
  - recruitment facts from public channels (what's forming, never raw chat)

What it shares: NOTHING. Everything stays on this machine. When the
community boards open, sharing will be a separate per-stat opt-in and
this app will ask you again, item by item.

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
    return (f"Companion Lite — up {up} min\n"
            f"capture owner: {who}\n"
            f"events captured this run: {_stats['events']} "
            f"({_stats['recruit']} recruitment)\n"
            f"pulse capture (channels): {'ON' if st.get('pulse_capture') else 'off'}\n"
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
\tOption "What is this? (logging feeds your local Pulse Boards)" "nop"
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
    # image name — only our own PID is ever involved. If the move fails, still relaunch
    # what's there so Lite is never left down.
    with open(bat, "w", encoding="utf-8") as f:
        f.write("@echo off\r\n"
                ":wait\r\n"
                f'tasklist /FI "PID eq {pid}" | find "{pid}" >nul '
                "&& (ping -n 2 127.0.0.1 >nul & goto wait)\r\n"
                "ping -n 2 127.0.0.1 >nul\r\n"
                f'move /Y "{newexe}" "{target}" >nul 2>&1\r\n'
                f'start "" "{target}"\r\n'
                'del "%~f0"\r\n')
    subprocess.Popen(["cmd", "/c", bat], creationflags=0x00000008)   # DETACHED_PROCESS
    _stop.set()
    return "updating"


def _result_page(title, body_html):
    """Show a result in the BROWSER instead of a modal dialog. A browser window is a
    normal top-level app the user can always alt-tab to and click — unlike a modal
    popped from a tray menu, which can lose input to the fullscreen game (field report)."""
    import webbrowser
    p = os.path.join(APPDIR, "lite_message.html")
    os.makedirs(APPDIR, exist_ok=True)
    html = (f"<!doctype html><meta charset='utf-8'><title>{title}</title>"
            "<body style='background:#0c1220;color:#dbe4f5;font-family:Segoe UI,sans-serif;"
            "max-width:640px;margin:40px auto;padding:0 20px;line-height:1.6'>"
            f"<h2 style='color:#5abeff'>{title}</h2>{body_html}</body>")
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open("file:///" + p.replace("\\", "/"))


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

    def _open_boards(_icon, _item):
        # regenerate from THIS machine's store (pass the resolved path so the frozen
        # build can never read the wrong events.jsonl), then open the local page.
        import webbrowser
        out = os.path.join(APPDIR, "pulse_boards.html")
        try:
            import build_pulse_boards
            build_pulse_boards.OUT = out
            build_pulse_boards.APPDIR = APPDIR
            build_pulse_boards.build(state_dir=gamelog.STATE_DIR)
        except Exception as e:  # noqa: BLE001
            _result_page("Companion Lite — boards",
                         f"<p>Couldn't build the board:</p><pre>{type(e).__name__}: {e}</pre>")
            return
        webbrowser.open("file:///" + out.replace("\\", "/"))

    def _publish_boards(_icon, _item):
        import build_pulse_boards
        build_pulse_boards.OUT = os.path.join(APPDIR, "pulse_boards.html")
        build_pulse_boards.APPDIR = APPDIR
        out, n = build_pulse_boards.build(state_dir=gamelog.STATE_DIR)
        html = open(out, encoding="utf-8").read()
        status = _publish_live(html)
        if status == "ok":
            _result_page("Companion Lite — published",
                         f"<p>Published <b>{n} events</b> to your live board:</p>"
                         f"<p><a href='{_PUBLISH_LIVE_URL}'>{_PUBLISH_LIVE_URL}</a></p>"
                         "<p style='color:#8fa0bd'>GitHub Pages takes a minute to "
                         "refresh. This is YOUR data on YOUR public site — only what you "
                         "just published, nothing more.</p>")
        elif status == "no-token":
            _result_page("Companion Lite — set up publishing",
                         "<p>To publish your board to the live site, this machine needs a "
                         "GitHub token (created by you, stored only here):</p><ol>"
                         "<li>On GitHub: Settings → Developer settings → Fine-grained "
                         "tokens → Generate. Repository access: <code>hero-companion</code>. "
                         "Permission: <b>Contents → Read and write</b>.</li>"
                         "<li>Save the token text into this file:<br>"
                         f"<code>{os.path.join(APPDIR, 'publish_token.txt')}</code></li>"
                         "<li>Click Publish again.</li></ol>"
                         "<p style='color:#8fa0bd'>The token stays on this machine — it is "
                         "never in the app or the repo.</p>")
        else:
            _result_page("Companion Lite — publish failed",
                         f"<p>Couldn't publish:</p><pre>{status}</pre>"
                         "<p>Check the token has Contents write on hero-companion.</p>")

    def _toggle_pulse(_icon, _item):
        # Channel/recruitment capture — its OWN consent (contains other players' text),
        # so it's a deliberate toggle, default off. Flips the shared state flag.
        st = gamelog.load_state()
        now = not st.get("pulse_capture")
        st["pulse_capture"] = now
        gamelog.save_state(st)
        _result_page("Companion Lite — pulse capture",
                     f"<p>Recruitment capture is now <b>{'ON' if now else 'off'}</b>.</p>"
                     + ("<p>Companion Lite will now note what's forming on your server "
                        "(LFG / Broadcast / Request / Coalition / SG) as structured facts "
                        "— what and how many spots, never the raw chat. Feeds the "
                        "'server pulse' on your boards.</p>" if now else
                        "<p>Only your own rewards and drops are captured now.</p>"))

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
                     "Logging feeds your <b>local</b> Pulse Boards only — nothing is "
                     "uploaded. It changes nothing else and is fully reversible.</p>")

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
    def _pulse_on(_i=None):
        return bool(gamelog.load_state().get("pulse_capture"))

    items = [pystray.MenuItem("Open Pulse Boards (alpha)", _safe(_open_boards)),
             pystray.MenuItem("Publish my board to the live site", _safe(_publish_boards)),
             pystray.MenuItem("In-game logging menu", install_sub),
             pystray.MenuItem("Capture server chatter (recruitment)",
                              _safe(_toggle_pulse), checked=_pulse_on),
             pystray.MenuItem("Status", _safe(_show_status)),
             pystray.MenuItem("About Companion Lite", _safe(_about)),
             pystray.MenuItem("Check for updates", _safe(_check_updates)),
             pystray.MenuItem("Quit", _quit)]
    menu = pystray.Menu(*items)
    icon = pystray.Icon("CompanionLite", img, f"Companion Lite v{LITE_VERSION}", menu)
    _stats["started"] = time.time()          # anchor uptime at tray start, not import
    t = threading.Thread(target=_capture_loop, daemon=True)
    t.start()
    icon.run()


def main():
    args = sys.argv[1:]
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
