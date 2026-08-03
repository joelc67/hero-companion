"""Hero Companion — the packaged (PyInstaller) entry point.

Hero Companion opens in its OWN WINDOW and closing that window quits it. The
Flask server runs in the background on localhost and the window (pywebview ->
the WebView2 runtime that already ships with Windows 10/11) is the view onto it.
There is no tray icon: nothing keeps running once the window is shut.
Console output goes to %APPDATA%\\HeroCompanion\\app.log in windowed builds.

Also runs from source:  python run_app.py
Env knobs: PORT (default 5000), HC_WINDOW=0 (fall back to a browser tab — the
escape hatch if WebView2 is genuinely absent), HC_NO_BROWSER=1 (with HC_WINDOW=0,
don't open a tab either — headless smokes).
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
# ⚠ The first-run TRAY NOTICE that shipped 2026-08-01 (270f03bb) is gone with the
# tray. It existed because BasiliskXVIII found a background process that never
# introduced itself — "something else is running on your machine, which you then
# have to know is there and manually quit from". A window that closes when you
# close it answers that complaint at the root instead of apologising for it.
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


# ── Auto-start (Windows Citizenship order A, 2026-07-22; CHOICE DOCTRINE) ────
# Parity with Companion Lite 0.1.18: opt-in, per-user (HKCU Run, no admin),
# ASKED once at first run of the INSTALLED app — never silently on — remembered,
# and reversible from the tray menu. The installer's uninstaller also removes
# the Run value, so a remembered "yes" leaves nothing behind. Dev runs (not
# frozen) never touch autostart. The Run value launches with --from-autostart:
# a login start stays quiet in the tray (no browser tab) — opening the app is
# the user's click, not the boot's.
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_VALUE = "HeroCompanion"
_FROZEN = getattr(sys, "frozen", False)
# app_state.json existed only to remember that the autostart MessageBox had been
# asked. The box is gone, so the file is too — the registry IS the state now, and
# /meta reads it live.


def _autostart_enabled():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
            winreg.QueryValueEx(k, _RUN_VALUE)
        return True
    except OSError:
        return False


def _set_autostart(on):
    import winreg
    if on and _FROZEN:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, _RUN_VALUE, 0, winreg.REG_SZ,
                              f'"{sys.executable}" --from-autostart')
    else:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0,
                                winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, _RUN_VALUE)
        except OSError:
            pass


# ⚠ The first-run autostart MessageBox is gone too. It asked the question before
# the user had seen the app, and its answer ("change this any time from the tray
# menu") pointed at a menu that no longer exists. The toggle lives in the app's
# own About & Settings now, where it is visible whenever they think to look.


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


# ── THE WINDOW — how Hero Companion runs (Joel, 2026-08-02) ──────────────────
# pywebview drives the WebView2 runtime that already ships with Windows 10/11, so
# end users install nothing extra. Flask still serves on localhost; the window is
# a chrome-less view onto it. THE TRAY IS GONE: closing the window quits the app.
#
# HC_WINDOW=0 is the escape hatch back to a browser tab, kept for the case where
# WebView2 is genuinely absent and for headless smokes. It is an opt-OUT now.
_WINDOW = os.environ.get("HC_WINDOW") != "0"


def _run_window(port):
    """Hero Companion in its own window. Blocks until the window closes, which
    quits the app — no tray, no background copy left running. False if pywebview
    or the WebView2 runtime is unavailable (caller falls back to the browser)."""
    try:
        import webview
    except Exception as e:  # noqa: BLE001 — missing dependency is a fallback, not a crash
        print(f"native window unavailable ({e}); falling back to a browser tab")
        return False

    def _quit():
        _clear_lock()          # os._exit skips atexit — release the instance lock here
        os._exit(0)

    # The self-update path (POST /app/shutdown, server._graceful_self_exit_for_update)
    # retires this copy through the same hook the tray used. There is no icon to
    # remove, so the exit is immediate — the tray's "let the message loop delete the
    # icon first" delay was solving a problem that no longer exists.
    server.SHUTDOWN_HOOK = _quit

    # ⚠ The window reference lives HERE, in a closure — NEVER as an attribute on
    # the js_api object. pywebview walks the api object to build the JS bridge,
    # and a Window attribute handed it the whole window graph to serialize ON
    # the GUI thread: the app froze at "(Not Responding)" before first input
    # (cost: one hung build, 2026-08-03).
    _winref = {}

    class _Api:
        """What the page tells the window. Kept to the minimum that the close
        decision needs, because anything the handler has to ASK for is a call
        onto the GUI thread it is already running on."""
        dirty = False

        def set_dirty(self, flag):
            _Api.dirty = bool(flag)
            return True

        def pick_folder(self):
            """Native folder browser for 'where is your game installed' —
            typing a path is the fallback, not the front door (Joel,
            2026-08-03). Same off-GUI-thread js_api seam as save_file."""
            try:
                import webview as _wv
                w = _winref.get("w")
                if w is None:
                    return {"ok": False, "error": "window not ready"}
                res = w.create_file_dialog(_wv.FOLDER_DIALOG)
                if not res:
                    return {"ok": False, "cancelled": True}
                p = res[0] if isinstance(res, (list, tuple)) else res
                return {"ok": True, "path": str(p)}
            except Exception as e:  # noqa: BLE001 — surface it to the page, don't die
                return {"ok": False, "error": str(e)}

        def save_file(self, filename, text):
            """Real Save As for exports. ALLOW_DOWNLOADS stays False (the
            download flyout is a browser tell), so the page routes every
            file it produces through here; js_api methods run OFF the GUI
            thread, so the dialog cannot deadlock the way closing did."""
            try:
                import webview as _wv
                w = _winref.get("w")
                if w is None:
                    return {"ok": False, "error": "window not ready"}
                path = w.create_file_dialog(
                    _wv.SAVE_DIALOG, save_filename=str(filename or "export.txt"))
                if not path:
                    return {"ok": False, "cancelled": True}
                if isinstance(path, (list, tuple)):
                    path = path[0]
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                return {"ok": True, "path": str(path)}
            except Exception as e:  # noqa: BLE001 — surface it to the page, don't die
                return {"ok": False, "error": str(e)}

    _api = _Api()
    try:
        # ⚠ EVERY LINE BELOW IS A "THIS IS STILL A BROWSER" TELL, TURNED OFF
        # (Joel, 2026-08-02: "it appears to be a browser still… not a self
        # contained application like Mids Reborn"). pywebview's defaults are a
        # browser's defaults; an application's are different.
        #
        # The right-click menu is the loudest one — WebView2's default offers
        # Back / Reload / Save as / View source, none of which mean anything in
        # an app. text_select/zoomable are already app-like defaults; they are
        # named here so a future pywebview flipping them is a visible change.
        webview.settings["SHOW_DEFAULT_MENUS"] = False
        # ⚠ ALLOW_DOWNLOADS=False SILENTLY EATS blob downloads — the .mbd export
        # clicked its <a download> and NOTHING happened, no file, no error (found
        # 2026-08-03 driving the advanced path). Every file the page produces
        # must route through _Api.save_file (a real Save As dialog) instead.
        # The setting stays False on purpose: the download flyout is a browser tell.
        webview.settings["ALLOW_DOWNLOADS"] = False
        # …and OPEN_EXTERNAL_LINKS_IN_BROWSER stays True on purpose: the wiki and
        # forum links belong in the user's real browser, not trapped in the app.
        # ⚠ MUST be a .ico — a PNG here throws deep inside System.Drawing.Icon on a
        # .NET thread, OUTSIDE this try/except, and kills the app with no window and
        # no fallback (cost: one silent exit, 2026-08-02). The frozen build carries
        # the .ico as its exe icon too (see HeroCompanion.spec).
        # ⚠ SIZE TO THE SCREEN, NOT TO A NUMBER. A fixed 1600x1000 "dedicated
        # size" opened wider than this machine's display and hung off the right
        # edge. Mids can pick a fixed size because its rows are one line tall;
        # this app has more to show, so it takes what the screen actually has and
        # the layout scales into it (fitZoom). Capped so a 4K panel gets a window,
        # not a wall.
        try:
            scr = webview.screens[0]
            win_w = max(1024, min(1680, int(scr.width * 0.92)))
            win_h = max(640, min(1050, int(scr.height * 0.92)))
        except Exception:  # noqa: BLE001 — no screen info: a sane fixed default
            win_w, win_h = 1280, 860
        print(f"window: {win_w}x{win_h}")
        icon = os.path.join(BASE, "assets", "HeroCompanion.ico")
        win = webview.create_window(
            "Hero Companion", f"http://127.0.0.1:{port}",
            # Mids Reborn opens at roughly 1075x800 and that is the size this
            # tool is judged against (Joel, 2026-08-03: "a dedicated size similar
            # to the size that mids reborn has by default"). A little taller,
            # because five tabs of content need the vertical room Mids spends on
            # a single dense screen. min_size is small enough to still resize
            # onto a laptop; the layout scales to whatever it is given.
            width=win_w, height=win_h, min_size=(900, 600),
            text_select=False, zoomable=False, js_api=_api,
            background_color="#11151c")   # style.css --bg: no white browser flash on open
        _winref["w"] = win                # save_file's dialog owner (closure, not api attr)
        # ⚠ CLOSING IS NOT A LICENCE TO THROW WORK AWAY (Joel, 2026-08-03). The
        # window quits the app, so an unnamed character with powers picked would
        # vanish on the X. The page owns the question — it knows WHAT is unsaved
        # and can name it — so the close is vetoed once and handed back to it.
        #
        # ⚠⚠ NEVER CALL evaluate_js FROM INSIDE THE CLOSING HANDLER. The first
        # version did, and it DEADLOCKED the app dead — "Hero Companion (Not
        # Responding)" on the very first close. The handler runs ON the GUI
        # thread; evaluate_js dispatches to that same thread and waits, so it
        # waits on itself. Both halves are fixed here:
        #   - the dirty flag is PUSHED from the page (js_api.set_dirty), so the
        #     handler only reads a variable and never calls into JS;
        #   - the prompt is fired from a worker thread, off the GUI thread.
        _closing_asked = {"done": False}

        def _on_closing():
            if _closing_asked["done"] or not _api.dirty:
                return True
            _closing_asked["done"] = True          # one-time veto: never a trap
            threading.Thread(
                target=lambda: win.evaluate_js("window.confirmQuit && confirmQuit()"),
                daemon=True).start()
            return False        # stay open; the page is asking now

        win.events.closing += _on_closing

        # ⚠⚠ private_mode DEFAULTS TO TRUE, which throws localStorage away on every
        # launch — that is the alignment theme, the update-check switch, the tour's
        # saved spot and its "finished" flag, all silently forgotten each time the
        # app opens. An app remembers; a private browsing window is what forgets.
        # storage_path keeps it beside the app's other state.
        webview.start(private_mode=False,
                      storage_path=os.path.join(_APPDIR, "webview"),
                      icon=icon if os.path.exists(icon) else None)
    except Exception as e:  # noqa: BLE001
        print(f"native window failed to start ({e}); falling back to browser + tray")
        server.SHUTDOWN_HOOK = None
        return False
    _quit()
    return True


def main():
    after_update = "--after-update" in sys.argv
    from_autostart = "--from-autostart" in sys.argv
    if _SINGLE and after_update:
        _kill_other_copies()
    elif _SINGLE:
        existing = _live_instance_port()
        if existing:
            if from_autostart:
                # Login race: the user (or a previous session) already has a copy
                # up. The boot start bows out silently — no browser, no dialog.
                print(f"autostart: a copy is already live on port {existing} — exiting quietly")
                return
            print(f"Hero Companion is already running at http://localhost:{existing} — "
                  "opening that copy instead of starting a second one.")
            if os.environ.get("HC_NO_BROWSER") != "1":
                webbrowser.open(f"http://localhost:{existing}")
            return
    if _FROZEN:
        # /meta answers autostart state through the live registry read — the
        # setting shown anywhere can never disagree with registry reality.
        server.AUTOSTART_STATE_FN = _autostart_enabled
        # …and the setter, so the toggle can live in the app UI. With no tray menu
        # the UI is the ONLY place this choice exists (Joel, 2026-08-02).
        server.AUTOSTART_SET_FN = _set_autostart
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
    # The window owns the whole lifecycle: it blocks here, and closing it quits.
    # Everything below is the fallback for HC_WINDOW=0 or a machine with no
    # WebView2 — a browser tab, exactly as the app worked before.
    if _WINDOW and _run_window(port):
        return
    if os.environ.get("HC_NO_BROWSER") != "1" and not from_autostart:
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

    # ⚠ NO TRAY HERE ANY MORE. In the browser fallback the app has no icon and no
    # menu, so a windowed (console-less) build would serve forever with nothing to
    # close — the exact "something is running and I can't quit it" complaint. Say
    # where it is and how to stop it; the log is the only voice this path has.
    if _WINDOWED:
        print(f"No app window available, so Hero Companion opened your browser at "
              f"http://localhost:{port} instead. It keeps running until you end "
              f"HeroCompanion.exe from Task Manager.")
    else:
        print("Keep this window open while you use the app; Ctrl+C (or close it) to stop.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
