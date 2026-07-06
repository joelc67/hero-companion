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

POLL_SECONDS = 15

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


def _game_menu_paths():
    """Where the .mnu belongs in each discovered game install:
    <game root>\\data\\texts\\English\\Menus\\companion.mnu"""
    out = []
    for accounts in _accounts_roots():
        game_root = os.path.dirname(accounts)
        out.append(os.path.join(game_root, "data", "texts", "English", "Menus",
                                "companion.mnu"))
    return out


def _msgbox_yesno(title, text):
    import ctypes
    MB_YESNO, MB_ICONQUESTION, MB_TOPMOST, IDYES = 0x4, 0x20, 0x40000, 6
    return ctypes.windll.user32.MessageBoxW(
        None, text, title, MB_YESNO | MB_ICONQUESTION | MB_TOPMOST) == IDYES


def install_ingame_menu():
    """Ask permission, then write companion.mnu into each game install. Returns a
    human status string."""
    paths = _game_menu_paths()
    if not paths:
        return "No game install found (no accounts folder discovered)."
    listing = "\n".join(f"  {p}" for p in paths)
    if not _msgbox_yesno(
            "Companion Lite — install in-game menu?",
            "This writes ONE small text file (a popmenu) into your game's data folder "
            "so you can enable chat logging from inside the game:\n\n" + listing +
            "\n\nIt changes nothing else, and 'Remove in-game menu' deletes it again. "
            "Install?"):
        return "Not installed (you said no — remembered until you choose Install again)."
    done = []
    for p in paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(_MENU_TEXT)
        done.append(p)
    st = gamelog.load_state()
    st["ingame_menu"] = {"installed": done, "ts": time.time()}
    gamelog.save_state(st)
    return ("Installed. RESTART the game client, then type:  /popmenu Companion\n"
            "Handy bind:  /bind ctrl+h \"popmenu Companion\"")


def remove_ingame_menu():
    st = gamelog.load_state()
    removed = 0
    for p in (st.get("ingame_menu") or {}).get("installed", []) or _game_menu_paths():
        try:
            os.remove(p)
            removed += 1
        except OSError:
            pass
    st.pop("ingame_menu", None)
    gamelog.save_state(st)
    return f"Removed {removed} menu file(s)."


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

    def _quit(icon, _item):
        _stop.set()
        icon.stop()

    def _show_status(icon, _item):
        icon.notify(_status_text(), "Companion Lite")

    def _open_boards(_icon, _item):
        # regenerate from the current store, then open — the alpha Pulse Boards,
        # fed by this machine's eyes only
        import webbrowser
        try:
            import build_pulse_boards
            build_pulse_boards.build()
        except Exception:  # noqa: BLE001 — open whatever the last build produced
            pass
        webbrowser.open("file:///" + os.path.join(APPDIR, "pulse_boards.html").replace("\\", "/"))

    def _install_menu(icon, _item):
        icon.notify(install_ingame_menu(), "Companion Lite")

    def _remove_menu(icon, _item):
        icon.notify(remove_ingame_menu(), "Companion Lite")

    menu = pystray.Menu(pystray.MenuItem("Open Pulse Boards (alpha)", _open_boards),
                        pystray.MenuItem("Install in-game menu…", _install_menu),
                        pystray.MenuItem("Remove in-game menu", _remove_menu),
                        pystray.MenuItem("Status", _show_status),
                        pystray.MenuItem("Quit", _quit))
    icon = pystray.Icon("CompanionLite", img, "Companion Lite", menu)
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
    try:
        _run_tray()
    except Exception:  # noqa: BLE001 — no pystray → console fallback
        print("(tray unavailable — running in console mode)")
        sys.argv = [sys.argv[0], "--console"]
        main()


if __name__ == "__main__":
    main()
