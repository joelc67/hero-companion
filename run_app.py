"""Hero Companion — the packaged (PyInstaller) entry point.

Packaged builds run WINDOWLESS: the server starts in the background, the browser
opens, and a tray icon (the lime pulse, next to the clock) is the app's handle —
right-click it for Open / Quit. No console window, nothing to remember to close.
Console output goes to %APPDATA%\\HeroCompanion\\app.log in windowed mode.

Also runs from source:  python run_app.py   (console mode, Ctrl+C to stop)
Env knobs: PORT (default 5000), HC_NO_BROWSER=1 (don't auto-open a browser tab).
"""
import atexit
import json
import os
import sys
import threading
import webbrowser

if getattr(sys, "frozen", False):
    BASE = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "server"))
sys.path.insert(0, os.path.join(BASE, "ai"))

# Windowed (console=False) builds have no stdout — writing to it raises. Route
# prints to a log file BEFORE importing the server (which prints while loading).
_WINDOWED = getattr(sys, "frozen", False) and (sys.stdout is None or sys.stderr is None)
if _WINDOWED:
    _logdir = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "HeroCompanion")
    os.makedirs(_logdir, exist_ok=True)
    _log = open(os.path.join(_logdir, "app.log"), "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr = _log

import server  # noqa: E402  — the Flask app module; loads the game data on import


# ── SINGLE INSTANCE (field report: THREE copies running at once) ─────────────
# Every extra launch used to start another server on the next port while the
# browser tab stayed on the oldest copy — so users saw stale versions forever.
# The packaged app now defers to a live copy instead of starting a second one.
_APPDIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "HeroCompanion")
_LOCK = os.path.join(_APPDIR, "instance.lock")
_SINGLE = getattr(sys, "frozen", False) or os.environ.get("HC_SINGLE_INSTANCE") == "1"


def _live_instance_port():
    """Port of an already-running copy (lockfile + live /meta probe), or None."""
    try:
        with open(_LOCK, encoding="utf-8") as f:
            port = int(json.load(f).get("port", 0))
        if not port:
            return None
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/meta", timeout=2) as r:
            if json.load(r).get("app_version"):
                return port
    except Exception:  # noqa: BLE001 — no lock / stale lock / dead instance
        return None
    return None


def _write_lock(port):
    try:
        os.makedirs(_APPDIR, exist_ok=True)
        with open(_LOCK, "w", encoding="utf-8") as f:
            json.dump({"port": port, "pid": os.getpid()}, f)
        atexit.register(_clear_lock)
    except Exception:  # noqa: BLE001
        pass


def _clear_lock():
    try:
        with open(_LOCK, encoding="utf-8") as f:
            if int(json.load(f).get("pid", -1)) == os.getpid():
                os.remove(_LOCK)
    except Exception:  # noqa: BLE001
        pass


def _kill_other_copies():
    """After a self-update, any straggler process still serves the PRE-upgrade code
    (Windows keeps the old image alive) — remove them so the fresh copy owns port 5000.

    Ask the old copy to quit CLEANLY first (POST /app/shutdown) so it removes its own tray
    icon — a force-kill orphans that icon as a "ghost" that only clears when you mouse over
    the tray (the exact bug field-reported). Force-kill is the fallback for a copy that
    ignores the polite request."""
    import subprocess
    import time
    try:
        port = _live_instance_port()      # the OLD copy's port, from its lockfile
        if port:
            import urllib.request
            req = urllib.request.Request(f"http://127.0.0.1:{port}/app/shutdown", method="POST")
            urllib.request.urlopen(req, timeout=3).read()
            time.sleep(1.5)               # let it drop its tray icon and release the port
    except Exception:  # noqa: BLE001 — no live copy / already gone
        pass
    try:
        subprocess.run(["taskkill", "/F", "/IM", "HeroCompanion.exe",
                        "/FI", f"PID ne {os.getpid()}"], capture_output=True, timeout=15)
    except Exception:  # noqa: BLE001
        pass


def _pick_port(start):
    """First free port from `start` upward — so a double-launch (or a squatter on
    5000) opens on 5001 instead of dying silently."""
    import socket
    for p in range(start, start + 20):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return start


def _run_tray(port):
    """Tray icon with Open / Check for updates / Quit. Returns False if the tray can't
    start (then the caller just blocks so the server stays up).

    The tray is the app's handle: Hero Companion keeps serving after you close the browser
    tab (so re-opening is instant), and this menu is how you drive it — reopen the browser,
    check for a new version, or quit for real."""
    try:
        import pystray
        from PIL import Image
        img = Image.open(os.path.join(BASE, "assets", "HeroCompanion-icon-512.png"))

        def _open(icon, item):
            webbrowser.open(f"http://localhost:{port}")

        def _check_updates(icon, item):
            """Query our own local endpoint, report via a tray balloon, and open the app
            (where the one-click updater lives) when a new version exists."""
            try:
                import urllib.request
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/meta/update-check", timeout=8) as r:
                    d = json.load(r)
            except Exception:  # noqa: BLE001
                d = None
            try:
                if d and d.get("ok") and d.get("update_available"):
                    icon.notify(f"Version {d.get('latest')} is available "
                                f"(you have {d.get('current')}). Opening Hero Companion to update.",
                                "Hero Companion")
                    webbrowser.open(f"http://localhost:{port}")
                elif d and d.get("ok"):
                    icon.notify(f"You're up to date (v{d.get('current')}).", "Hero Companion")
                else:
                    icon.notify("Couldn't check right now — offline, or updates aren't "
                                "configured in this copy.", "Hero Companion")
            except Exception:  # noqa: BLE001 — notifications are best-effort
                pass

        def _quit(icon, item):
            icon.stop()            # stop() is what removes the tray icon (no ghost)
            _clear_lock()          # os._exit skips atexit — release the instance lock here
            os._exit(0)

        icon = pystray.Icon(
            "HeroCompanion", img, f"Hero Companion — running at localhost:{port}",
            menu=pystray.Menu(
                pystray.MenuItem("Open Hero Companion", _open, default=True),
                pystray.MenuItem("Check for updates…", _check_updates),
                pystray.MenuItem("Quit Hero Companion", _quit)))

        # Let a self-update (or any other instance) retire THIS copy cleanly via
        # POST /app/shutdown, or the app retire ITSELF before its installer force-kills it
        # (server._graceful_self_exit_for_update). icon.stop() is what removes the tray icon;
        # it runs on the tray's own message loop (this hook may be called from a Flask/worker
        # thread), so we give that loop a moment to actually delete the icon BEFORE os._exit —
        # exiting too fast re-orphans the icon as the very "ghost" we're preventing.
        def _graceful_quit():
            try:
                icon.stop()
            except Exception:  # noqa: BLE001
                pass
            import time
            time.sleep(0.6)          # let the message loop process the NIM_DELETE
            _clear_lock()
            os._exit(0)
        server.SHUTDOWN_HOOK = _graceful_quit

        icon.run()          # blocks until Quit
        return True
    except Exception as e:  # noqa: BLE001 — no tray support → fall back to blocking
        print(f"tray unavailable ({e}); running headless")
        return False


def main():
    after_update = "--after-update" in sys.argv
    if _SINGLE and after_update:
        _kill_other_copies()
    elif _SINGLE:
        existing = _live_instance_port()
        if existing:
            print(f"Hero Companion is already running at http://localhost:{existing} — "
                  "opening that copy instead of starting a second one.")
            if os.environ.get("HC_NO_BROWSER") != "1":
                webbrowser.open(f"http://localhost:{existing}")
            return
    want = int(os.environ.get("PORT", "5000"))
    port = _pick_port(want)
    print(f"Hero Companion v{server.APP_VERSION} — model v{__import__('first_principles').MODEL_VERSION}"
          f" — data {server.DB_VERSION}")
    if port != want:
        print(f"Port {want} is busy (another copy running?) — using {port} instead.")
    print(f"Running at http://localhost:{port}")

    if _SINGLE:
        _write_lock(port)
    threading.Thread(
        target=lambda: server.app.run(host="127.0.0.1", port=port, debug=False),
        daemon=True).start()
    if os.environ.get("HC_NO_BROWSER") != "1":
        if after_update:
            # Relaunched by the installer after a self-update. The tab the user
            # clicked "Update now" in is polling us and will reload itself into
            # the new version — give it time to reconnect before opening a
            # SECOND tab (the field-tested papercut: old tab + duplicate tab).
            def _open_if_no_tab():
                import time
                deadline = time.time() + 30
                while time.time() < deadline:
                    if server.SEEN_REQUEST:
                        print("after-update: the existing tab reconnected — not opening a new one")
                        return
                    time.sleep(1)
                print("after-update: no tab reconnected in 30s — opening the browser")
                webbrowser.open(f"http://localhost:{port}")
            threading.Thread(target=_open_if_no_tab, daemon=True).start()
        else:
            threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{port}")).start()

    if _WINDOWED:
        if not _run_tray(port):
            threading.Event().wait()      # tray failed — keep serving anyway
    else:
        print("Keep this window open while you use the app; Ctrl+C (or close it) to stop.")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
