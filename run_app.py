"""Hero Companion — the packaged (PyInstaller) entry point.

Packaged builds run WINDOWLESS: the server starts in the background, the browser
opens, and a tray icon (the lime pulse, next to the clock) is the app's handle —
right-click it for Open / Quit. No console window, nothing to remember to close.
Console output goes to %APPDATA%\\HeroCompanion\\app.log in windowed mode.

Also runs from source:  python run_app.py   (console mode, Ctrl+C to stop)
Env knobs: PORT (default 5000), HC_NO_BROWSER=1 (don't auto-open a browser tab).
"""
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
    """Tray icon with Open / Quit. Returns False if the tray can't start (then the
    caller just blocks so the server stays up)."""
    try:
        import pystray
        from PIL import Image
        img = Image.open(os.path.join(BASE, "assets", "HeroCompanion-icon-512.png"))

        def _open(icon, item):
            webbrowser.open(f"http://localhost:{port}")

        def _quit(icon, item):
            icon.stop()
            os._exit(0)

        icon = pystray.Icon(
            "HeroCompanion", img, f"Hero Companion — running at localhost:{port}",
            menu=pystray.Menu(
                pystray.MenuItem("Open Hero Companion", _open, default=True),
                pystray.MenuItem("Quit", _quit)))
        icon.run()          # blocks until Quit
        return True
    except Exception as e:  # noqa: BLE001 — no tray support → fall back to blocking
        print(f"tray unavailable ({e}); running headless")
        return False


def main():
    want = int(os.environ.get("PORT", "5000"))
    port = _pick_port(want)
    print(f"Hero Companion v{server.APP_VERSION} — model v{__import__('first_principles').MODEL_VERSION}"
          f" — data {server.DB_VERSION}")
    if port != want:
        print(f"Port {want} is busy (another copy running?) — using {port} instead.")
    print(f"Running at http://localhost:{port}")

    threading.Thread(
        target=lambda: server.app.run(host="127.0.0.1", port=port, debug=False),
        daemon=True).start()
    if os.environ.get("HC_NO_BROWSER") != "1":
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
