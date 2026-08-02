"""BATTERY: the desktop-app batch (Joel's five pieces, 2026-08-02).

  1. native window instead of a browser (HC_WINDOW=1, pywebview -> WebView2)
  2. no tray -> window close = quit, and the SELF-UPDATE path still has a hook
  3. the update check runs on launch, not only on a click
  4. the autostart toggle lives in the app UI, not a tray menu
  5. the share prompt is asked once, with the specifics, and remembers the answer

Every check that can be negative-controlled is. Run:
    py tools\\test_desktop_app.py
"""
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
CHECKS = []
EXPECTED = 28          # coverage denominator — hard-fail if a check silently skips


def check(name, ok, detail=""):
    CHECKS.append(bool(ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if detail:
        print(f"        {detail}")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def main():
    print("DESKTOP APP BATTERY\n")
    run_app = read("run_app.py")
    app_js = read("static", "app.js")
    index = read("static", "index.html")

    # ── 0. The file has to PARSE before any string check about it means a thing
    #       (the audit_tour lesson: a missing node must FAIL, never silently pass).
    node = shutil.which("node")
    if not node:
        print("  FAIL  node is required to syntax-check app.js and is not on PATH")
        sys.exit(1)
    r = subprocess.run([node, "--check", os.path.join(ROOT, "static", "app.js")],
                       capture_output=True, text=True)
    check("app.js parses (node --check)", r.returncode == 0, r.stderr.strip()[:200])

    # ── 1. NATIVE WINDOW ────────────────────────────────────────────────────
    check("pywebview is installed", importlib.util.find_spec("webview") is not None,
          "pip install pywebview")
    check("HC_WINDOW selects the window (prototype flag, Joel's ask)",
          bool(re.search(r'_WINDOW\s*=\s*os\.environ\.get\("HC_WINDOW"\)\s*==\s*"1"', run_app)))
    check("main() tries the window BEFORE opening any browser",
          run_app.find("if _WINDOW and _run_window(port)") < run_app.find("webbrowser.open(f\"http://localhost:{port}\")",
                                                                          run_app.find("def main(")),
          "otherwise window mode also spawns a browser tab")

    # The fallback is the whole reason the flag is safe: no pywebview / no
    # WebView2 must return False, not take the app down.
    import run_app as ra
    saved, ra.server.SHUTDOWN_HOOK = ra.server.SHUTDOWN_HOOK, None
    real, sys.modules["webview"] = sys.modules.get("webview"), None   # import -> ImportError
    try:
        check("NEGATIVE CONTROL: no pywebview -> _run_window returns False, no crash",
              ra._run_window(65535) is False)
        check("...and a failed window leaves no shutdown hook behind",
              ra.server.SHUTDOWN_HOOK is None)
    finally:
        if real is not None:
            sys.modules["webview"] = real
        else:
            sys.modules.pop("webview", None)
        ra.server.SHUTDOWN_HOOK = saved

    # ── 2. NO TRAY -> the self-update path must still be able to retire us ──
    win_src = run_app[run_app.find("def _run_window"):run_app.find("def _run_tray")]
    check("window mode sets server.SHUTDOWN_HOOK (self-update / POST /app/shutdown)",
          "server.SHUTDOWN_HOOK = _quit" in win_src)
    check("...and the hook releases the instance lock before exiting",
          "_clear_lock()" in win_src and "os._exit(0)" in win_src,
          "a stale lock makes the next launch defer to a dead copy")
    check("window mode skips the tray's autostart MessageBox (UI owns that now)",
          "_maybe_ask_autostart" not in win_src)

    # ── 3. UPDATE CHECK: AUTOMATIC ON LAUNCH ────────────────────────────────
    flow = app_js[app_js.find("function initUpdateFlow"):]
    flow = flow[:flow.find("\n}") + 2]
    check("initUpdateFlow runs the check itself", "runStartupUpdateCheck()" in flow)
    check("NEGATIVE CONTROL: the first-run 'check at startup?' question is GONE",
          "Yes, check at startup" not in app_js,
          "a leftover ask would mean the check is still opt-in")
    check("...and it is still reversible ('off' short-circuits)",
          '"hc_update_check") === "off"' in flow)
    check("the Settings toggle can turn it back on",
          "setUpdatePref(this.checked ? 'on' : 'off')" in app_js)

    # ── 4. AUTOSTART LIVES IN THE UI ────────────────────────────────────────
    check("run_app hands the SETTER to the server (read-only would be useless)",
          "server.AUTOSTART_SET_FN = _set_autostart" in run_app)
    check("the About/Settings dialog renders the toggle when supported",
          "setAutostart(this.checked)" in app_js and "META.autostart || {}" in app_js)
    check("the checkbox re-renders from the ANSWER, not the click",
          "META.autostart = { supported: true, enabled: r.enabled }" in app_js,
          "a refused registry write must not leave the box showing the wish")

    import server as srv
    c = srv.app.test_client()
    srv.AUTOSTART_SET_FN = None
    got = c.post("/app/autostart", json={"enabled": True}).get_json()
    check("NEGATIVE CONTROL: unpackaged app refuses to set autostart",
          got.get("ok") is False and got.get("reason") == "not_packaged", str(got))
    state = {"on": False}
    srv.AUTOSTART_SET_FN = lambda on: state.__setitem__("on", on)
    srv.AUTOSTART_STATE_FN = lambda: state["on"]
    got = c.post("/app/autostart", json={"enabled": True}).get_json()
    check("packaged app sets it and reads the state back", got == {"ok": True, "enabled": True}, str(got))
    got = c.post("/app/autostart", json={"enabled": False}).get_json()
    check("...and turns it off again", got == {"ok": True, "enabled": False}, str(got))
    srv.AUTOSTART_SET_FN = srv.AUTOSTART_STATE_FN = None

    # ── 5. THE SHARE PROMPT ─────────────────────────────────────────────────
    check("the prompt exists in the page", 'id="share-modal"' in index and 'id="share-body"' in index)
    check("it waits for the entry screen to clear (no stacked overlays)",
          "maybeAskShare()" in app_js[app_js.find("function hideEntry"):
                                      app_js.find("function hideEntry") + 400])
    check("NEGATIVE CONTROL: ✕ stores nothing — only the buttons answer",
          "shareAnswer" not in app_js[app_js.find('$("share-close")'):
                                      app_js.find('$("share-close")') + 200],
          "closing is not a decision")
    ask = app_js[app_js.find("async function maybeAskShare"):app_js.find("window.shareAnswer")]
    check("it only asks where it could do something (key + never answered here)",
          "st.key_present" in ask and "st.asked_here" in ask)
    check("the specifics are spelled out, not paraphrased into vagueness",
          all(s in ask for s in ["Never raw chat", "character names ARE included",
                                 "auction-house sale", "public-channel recruiters"]))
    check("the boards link is the real one",
          "hero-companion.com/pulse" in read("client_config.json"))

    # asked_here is what makes "asked once" true — exercised for real against an
    # isolated state dir, all three states.
    import gamelog
    import pulse_feed
    saved_dir = gamelog.STATE_DIR
    with tempfile.TemporaryDirectory() as d:
        gamelog.STATE_DIR = d
        try:
            fresh = pulse_feed.feed_status()
            pulse_feed.set_feed_enabled(False)
            said_no = pulse_feed.feed_status()
            pulse_feed.set_feed_enabled(True)
            said_yes = pulse_feed.feed_status()
        finally:
            gamelog.STATE_DIR = saved_dir
    check("a fresh install is UNASKED (so the prompt fires once)",
          fresh["asked_here"] is False and fresh["opted_in_here"] is False, str(fresh["asked_here"]))
    check("a remembered NO counts as asked (it is never re-asked)",
          said_no["asked_here"] is True and said_no["opted_in_here"] is False)
    check("a YES counts as asked AND opts in", said_yes["asked_here"] is True
          and said_yes["opted_in_here"] is True)

    print(f"\n{len(CHECKS)} of {EXPECTED} expected checks ran")
    if len(CHECKS) != EXPECTED:
        print("COVERAGE FAILURE — a check did not run")
        sys.exit(1)
    if not all(CHECKS):
        print(f"{CHECKS.count(False)} FAILURE(S)")
        sys.exit(1)
    print("== ALL CHECKS PASS ==")


if __name__ == "__main__":
    main()
