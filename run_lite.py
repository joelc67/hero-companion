"""Hero Companion LITE — the capture daemon.

A tiny tray app whose only job is watching the game's chat logs and turning them into
the same local event store the full app reads (%APPDATA%\\HeroCompanion\\gamelog).
Runs happily ALONGSIDE the full app: a heartbeat lock (gamelog.acquire_ingest) makes
whichever process is active the single ingester, so they never race the byte offsets —
when the full app's UI is open it captures, and Lite picks the job back up ~90s after
the UI goes quiet.

No Flask, no solver, no data bundles — just the gamelog module, the chat lexicon, and
a tray icon. Consent flags live in the SHARED state (pulse_capture is its own opt-in,
set from the full app or via --pulse on|off here).

Run:  py run_lite.py            (tray icon; Quit from the menu)
      py run_lite.py --console  (foreground, Ctrl+C to stop)
      py run_lite.py --pulse on (enable channel/pulse capture, then run)
"""
import json
import os
import sys
import threading
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "server"))
import gamelog  # noqa: E402

APPDIR = os.path.join(os.environ.get("APPDATA", _HERE), "HeroCompanion")
gamelog.STATE_DIR = os.path.join(APPDIR, "gamelog")

POLL_SECONDS = 15
DEFAULT_ROOTS = [r"C:\Games\HC2\accounts"]

_stats = {"started": time.time(), "polls": 0, "owned": 0, "events": 0,
          "recruit": 0, "last_error": None}
_stop = threading.Event()


def _watch_dirs(state):
    """The full app's configured watch list; else every account Logs dir we can find."""
    dirs = [d for d in (state.get("watch_dirs") or []) if os.path.isdir(d)]
    if dirs:
        return dirs
    found = []
    for acct in gamelog.find_log_accounts(DEFAULT_ROOTS):
        if acct.get("has_logs"):
            found.append(acct["log_dir"])
    return found


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
    return (f"Hero Companion Lite — up {up} min\n"
            f"capture owner: {who}\n"
            f"events captured this run: {_stats['events']} "
            f"({_stats['recruit']} recruitment)\n"
            f"pulse capture (channels): {'ON' if st.get('pulse_capture') else 'off'}\n"
            f"watching: {len(_watch_dirs(st))} log folder(s)"
            + (f"\nlast error: {_stats['last_error']}" if _stats["last_error"] else ""))


def _run_tray():
    import pystray
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=(63, 210, 255, 255))      # pulse-cyan dot ≠ full app icon
    d.line([14, 34, 26, 34, 32, 20, 38, 46, 44, 34, 52, 34], fill=(12, 18, 32, 255), width=5)

    def _quit(icon, _item):
        _stop.set()
        icon.stop()

    def _show_status(icon, _item):
        icon.notify(_status_text(), "Hero Companion Lite")

    menu = pystray.Menu(pystray.MenuItem("Status", _show_status),
                        pystray.MenuItem("Quit", _quit))
    icon = pystray.Icon("HeroCompanionLite", img, "Hero Companion Lite — capturing", menu)
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
        main_args = sys.argv
        sys.argv = [main_args[0], "--console"]
        main()


if __name__ == "__main__":
    main()
