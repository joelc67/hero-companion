"""BATTERY: the desktop-app batch (Joel's five pieces, 2026-08-02).

  1. its own window instead of a browser (pywebview -> WebView2), by default
  2. the tray is DELETED -> window close = quit, self-update hook survived
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
EXPECTED = 55          # coverage denominator — hard-fail if a check silently skips
#                        (54 -> 55, 2026-08-04: +1 for the End Game surfaces
#                        living inside the powers tab after the tab retirement)


def check(name, ok, detail=""):
    CHECKS.append(bool(ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if detail:
        print(f"        {detail}")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _share_css(css):
    """Just the .entry-share block — so 'position: fixed' elsewhere in the sheet
    can't make the not-a-modal check pass or fail for the wrong reason."""
    i = css.find(".entry-share {")
    return css[i:css.find("\n.", css.find("pre", i))] if i >= 0 else ""


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
    check("the window is the DEFAULT (HC_WINDOW=0 is the opt-OUT)",
          bool(re.search(r'_WINDOW\s*=\s*os\.environ\.get\("HC_WINDOW"\)\s*!=\s*"0"', run_app)))
    check("main() tries the window BEFORE opening any browser",
          run_app.find("if _WINDOW and _run_window(port)") < run_app.find("webbrowser.open(f\"http://localhost:{port}\")",
                                                                          run_app.find("def main(")),
          "otherwise the app also spawns a browser tab")

    # ── THE "STILL A BROWSER" TELLS (Joel's verdict, 2026-08-02) ────────────
    win_cfg = run_app[run_app.find("def _run_window"):run_app.find("def main(")]
    check("WebView2's right-click browser menu is OFF",
          'webview.settings["SHOW_DEFAULT_MENUS"] = False' in win_cfg,
          "Back/Reload/Save as/View source is the loudest browser tell")
    check("text selection and zoom are pinned to app behaviour",
          "text_select=False" in win_cfg and "zoomable=False" in win_cfg)
    check("no white browser flash on open (background matches --bg)",
          'background_color="#11151c"' in win_cfg
          and "--bg: #11151c" in read("static", "style.css"),
          "and the check reads the REAL stylesheet value, so a theme change fails it")
    # ⚠⚠ pywebview defaults private_mode=True, which throws localStorage away every
    # launch: the alignment theme, the update switch, the tour's saved spot.
    check("localStorage SURVIVES a restart (private_mode off + a storage path)",
          "private_mode=False" in win_cfg and "storage_path=" in win_cfg,
          "an app remembers; a private browsing window is what forgets")
    # ⚠ A .png here throws inside System.Drawing.Icon on a .NET thread, OUTSIDE
    # the try/except — the app dies with no window and no fallback message.
    check("the window icon is a .ico, not a .png",
          'assets", "HeroCompanion.ico"' in win_cfg and ".png" not in win_cfg,
          "a PNG kills the app on a .NET thread that this code cannot catch")
    check("...and that .ico actually ships in the frozen build",
          '("assets/HeroCompanion.ico", "assets")' in read("HeroCompanion.spec"))
    # ⚠ Two frozen builds sharing a version number are indistinguishable in the UI,
    # which is how a bug got reported twice against a build without the fix. Both
    # ends of the stamp must be wired or the About dialog quietly says nothing.
    _spec, _srv = read("HeroCompanion.spec"), read("server", "server.py")
    check("a frozen build can say WHICH commit it is",
          'open("build_commit.txt", "w"' in _spec
          and '("build_commit.txt", ".")' in _spec
          and 'ROOT, "build_commit.txt"' in _srv,
          "spec stamps it at build time, server.py reads it when frozen")

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

    # ── 2. THE TRAY IS GONE, and the self-update path survived it ───────────
    check("no tray left anywhere in run_app.py",
          not any(s in run_app for s in ("pystray", "_run_tray", "icon.notify",
                                         "tray_notice_seen", "_maybe_ask_autostart")))
    check("pystray is out of the frozen build too",
          '"pystray' not in read("HeroCompanion.spec"),
          "matches a quoted hiddenimports ENTRY, not the comment saying it is gone")
    check("its battery went with it (a test for deleted code is noise)",
          not os.path.exists(os.path.join(ROOT, "tools", "test_tray_first_run_notice.py")))
    check("the window sets server.SHUTDOWN_HOOK (self-update / POST /app/shutdown)",
          "server.SHUTDOWN_HOOK = _quit" in win_cfg,
          "without this, in-place updates cannot retire the running copy")
    check("...and the hook releases the instance lock before exiting",
          "_clear_lock()" in win_cfg and "os._exit(0)" in win_cfg,
          "a stale lock makes the next launch defer to a dead copy")

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
    check("the prompt exists in the page", 'id="share-line"' in index)
    # ⚠⚠ IT IS NOT A MODAL, and that is the whole point (Joel, twice). A consent
    # question that must be dismissed before the app can be used IS the complaint,
    # whether it fires once or every time. It lives INSIDE the opening menu, in
    # flow, so it cannot cover a control the user is reaching for.
    _entry_box = index[index.find('<div class="entry-box">'):index.find('id="entry-overlay"') + 12000]
    # The opening menu it used to live in is gone (2026-08-03). It now sits with
    # the feed it governs, on the Logging tab — still in the flow, still not a
    # modal. The ruling that survives is "never a wall", not "which screen".
    _logging = index[index.find('id="tab-logging"'):index.find('id="tab-logging"') + 1200]
    check("the prompt lives with the feed it governs, in the flow",
          'id="share-line"' in _logging,
          "floating it would put it back on top of the app")
    check("NEGATIVE CONTROL: it is not a modal and does not float",
          'id="share-line"' in index and 'class="entry-share' in index
          and 'id="share-line" class="modal' not in index
          and "position: fixed" not in _share_css(read("static", "style.css")),
          "position:fixed or .modal would put it back on top of the app")
    # ⚠ It fired from hideEntry() at first, which runs on EVERY entry path — so the
    # consent question ambushed the first meaningful action every time, and ✕ stores
    # nothing by design, so it came right back on the next one. Joel: "when I load it
    # a new pop-up appears… a similar partial navigation occurs picking other menu
    # options." All three checks below are that bug, pinned.
    check("it fires at LAUNCH, from loadMeta", "maybeAskShare();" in
          app_js[app_js.find("  initUpdateFlow();"):app_js.find("  initUpdateFlow();") + 200])
    check("NEGATIVE CONTROL: hideEntry does NOT trigger it",
          "maybeAskShare" not in app_js[app_js.find("function hideEntry"):
                                        app_js.find("function hideEntry") + 300],
          "hideEntry runs on load / scratch / new-50 / import — every one would ambush")
    _ask = app_js[app_js.find("async function maybeAskShare"):app_js.find("window.shareAnswer")]
    check("...and it can only ask ONCE per run",
          "if (_SHARE_ASKED_THIS_RUN) return;" in _ask
          and "_SHARE_ASKED_THIS_RUN = true;" in _ask,
          "the guard is what keeps 'at launch' from meaning 'at every transition'")
    check("NEGATIVE CONTROL: ignoring it stores nothing — only the buttons answer",
          "asked_here" not in app_js[app_js.find("function hideEntry"):
                                     app_js.find("function hideEntry") + 300]
          and 'postJson(yes ?' in app_js,
          "walking past the question must not be recorded as an answer")
    ask = _ask
    check("it only asks where it could do something (key + never answered here)",
          "st.key_present" in ask and "st.asked_here" in ask)
    # whitespace-flattened: these phrases wrap across source lines, and a check
    # that fails on a line break is testing the formatter, not the promise.
    _flat = re.sub(r"\s+", " ", ask)
    check("the specifics are spelled out, not paraphrased into vagueness",
          all(s in _flat for s in ["Never raw chat", "character names ARE included",
                                   "auction-house sale prices", "public-channel recruiters"]))
    check("the boards link is the real one",
          "hero-companion.com/pulse" in read("client_config.json"))

    # ── 6. THE TABBED SHELL (2026-08-03) ───────────────────────────────────
    # ⚠ balanceColumns() and its six checks are GONE, deliberately: tabs split
    # the two columns it shuffled tiles between, so there is nothing to balance.
    # A test for deleted code is noise — same call as the tray battery. What
    # replaces them are the rules the tab layout must not break.
    css = read("static", "style.css")
    check("no balancer left to go stale",
          "function balanceColumns" not in app_js and "const _TILES" not in app_js,
          "matches the DEFINITION, not the comment recording that it was deleted")
    # (was "five tabs" — End Game retired 2026-08-04, its surfaces live on
    # Powers & Slots; the moved ids are checked right below)
    check("four tabs, four panels",
          all(f'id="tab-btn-{k}"' in index and f'id="tab-{k}"' in index
              for k in ("powers", "stats", "leveling", "logging"))
          and 'id="tab-btn-endgame"' not in index)
    check("the End Game surfaces live inside the powers tab (plan, then accolades)",
          index.index('id="tab-powers"') < index.index('id="endgame-plan-panel"')
          < index.index('id="endgame-panel"') < index.index('id="tab-stats"'))
    # ⚠ SPEC 5.1 — the rule a naive tab implementation breaks. recompute() writes
    # into elements on four different tabs; unmounting makes every write a no-op.
    check("panels are HIDDEN, never unmounted", "panel.hidden = !on;" in app_js,
          "a change on End Game has to reach Powers & Slots")
    check("[hidden] out-specifies a panel's own display rule",
          ".tabpanel[hidden] { display: none !important; }" in css,
          "without it, two tabs render at once")
    check("cross-tab door exists (Joel's note)",
          "window.showTab = activateTab;" in app_js,
          "content on another tab is reached by activating it, never by copying it")
    check("tablist keyboard contract",
          all(k in app_js for k in ("ArrowLeft", "ArrowRight", "Home", "End")))
    # ⚠ SPEC 5.3 — a hidden panel has zero geometry, so the fit reads the ACTIVE
    # one and re-solves on activation.
    # ⚠ ONE ZOOM FOR THE APP, from the TALLEST tab. Solving per tab measured fine
    # and used terribly: Powers landed at 0.85 and the near-empty Leveling Guide
    # at 1.25, so every tab click resized the masthead and the type. A tab strip
    # is one surface; it has to hold still.
    check("the fit is solved once, from the tallest tab",
          "const tallest = () =>" in app_js and "p.hidden = false;" in app_js,
          "a hidden panel measures zero, so each is briefly un-hidden to be read")
    check("...and that measuring never paints an intermediate state",
          "p.hidden = was;" in app_js,
          "all inside one synchronous task")
    # ⚠ NEVER SHRINK. Joel, 2026-08-03: "even on a high res monitor, the icons,
    # fonts, and controls are tiny." Zooming out to force a fit is what made them
    # tiny, so the floor is 1.0 and the ceiling grows the app on a big screen.
    check("the fit only ever scales UP",
          "ZOOM_MIN = 1.00" in app_js and "ZOOM_MAX = 1.60" in app_js)
    # ⚠ THE BUG THIS PINS. The obvious solve, z <- z * (avail / need) repeated,
    # OSCILLATES: zooming out adds a powers-wall column, which drops a row, which
    # makes the panel abruptly shorter, which asks to zoom back in. scrollHeight
    # is a STEP function of zoom, so there is no smooth fixed point. Measured it
    # settling at 1.04 while overflowing by 495px.
    check("the fit SEARCHES the range instead of iterating toward a fixed point",
          "if (fitsAt(mid)) lo = mid; else hi = mid;" in app_js
          and "Math.floor(z * (avail / need) * 100)" not in app_js,
          "matches the old EXPRESSION, not the comment explaining why it went")
    # ⚠ NO NESTED SCROLLBARS. Joel: "some elements force every tab to have slide
    # bars." A capped panel put a slide bar inside the app; a tab taller than the
    # window scrolls at the WINDOW edge, where a desktop app puts it.
    check("nothing inside a tab makes its own scrollbar",
          ".tabpanel.scrolls { overflow-y: auto; }" not in css
          and 'classList.add("scrolls")' not in app_js
          and ".jny-card { max-height: 240px; overflow-y: auto; }" not in css)

    # ── 7. THE ENTRY WALL IS GONE; the menus carry it ──────────────────────
    check("nothing blocks the app at launch",
          '<div id="entry-overlay" class="modal hidden">' in index,
          "Joel: removing the menu blocking everything before the main screen")
    check("both menus exist", 'id="m-character"' in index and 'id="m-help"' in index)
    check("every entry route survived into a menu",
          all(f'id="{i}"' in index for i in
              # entry-mids retired: #import-btn does the same job and was
              # already bound, so the menu carries the one that existed.
              ("entry-continue", "entry-scratch", "entry-respec", "import-btn",
               "export-btn", "entry-ingame", "save-btn", "start-over-btn",
               "tour-btn", "help-btn", "bug-btn", "champ-btn", "update-btn")),
          "these are the ids app.js already binds — re-homed, not rewired")
    check("menu items keep their descriptions", index.count("<i>") >= 10,
          "easy to navigate means knowing what a thing does before clicking it")
    check("Escape and outside-click both close the menus",
          'e.key === "Escape"' in app_js
          and 'if (!e.target.closest(".menubar")) closeMenus();' in app_js)

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
