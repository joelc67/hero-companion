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
EXPECTED = 129          # coverage denominator — hard-fail if a check silently skips
#                        (54 -> 55, 2026-08-04: +1 for the End Game surfaces
#                        living inside the powers tab after the tab retirement;
#                        82 -> 88, 2026-08-05: portable-vs-installed detection
#                        and the Play Log's on-surface off switch;
#                        88 -> 94, same day: one import door + the leveling
#                        surface calling itself one thing;
#                        121 -> 126, 2026-08-06: no side bar unless the ⓘ
#                        card is open, and the two panels that left it;
#                        126 -> 128, same day: the slot invitation is a
#                        claim about the build, not a decoration;
#                        128 -> 129, same day: the stats side column holds to
#                        1000px, with a negative control that it has not gone
#                        back to collapsing at 1400 — the regression Joel read
#                        as the contributions column disappearing)


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
    # (packPowersTab is DEAD — Joel 2026-08-04: column see-saw, not design.
    # The cards live in the structural .pw-cardband; no packer may return.)
    check("the End Game surfaces live in the powers tab's card band; no packer",
          index.index('id="tab-powers"') < index.index('id="endgame-panel"')
          < index.index('id="tab-stats"')
          and index.index('id="tab-powers"') < index.index('id="endgame-plan-panel"')
          < index.index('id="tab-stats"')
          and 'class="pw-cardband"' in index
          and "function packPowersTab" not in app_js)
    # Joel's marked-up screenshot, 2026-08-04: Accolades owns its whole
    # horizontal line, and the three small cards moved UP into the voids he
    # circled — the inherent card into the side column's tail, ⌨ commands and
    # 💠 set bonuses into the catalogue grid's trailing cells.
    check("Accolades is full width, and the card strip sits above it",
          index.index('id="card-home"') < index.index('id="endgame-panel"')
          and index.index('id="endgame-panel"') < index.index('id="tray-out"'),
          "the strip is what follows the powerset rows; Accolades keeps its own row")
    # ⚠ The inherent LEFT Powers & Slots (Joel, 2026-08-05): "make it a stat just
    # above defense heading". It is the Archetype bonus group at the top of Stats
    # now, and nothing may hold a second copy on the powers tab.
    check("the inherent is a STAT above Defence, not a panel on Powers & Slots",
          'id="inherent-card"' not in index
          and index.index('id="at-bonus-group"') < index.index('id="defense-bars"'),
          "one home; the powers-tab card and its CSS are deleted, not hidden")
    # ⚠ NOTHING BESIDE THE COLUMNS (Joel's third markup, 2026-08-04): the cards'
    # sidebar was taking exactly the width the pool/epic boxes needed to tile, so it
    # bought two ragged voids. Both cards are STATIC in the strip now — no sidebar,
    # no JS re-parenting around the innerHTML write, nothing to eat them.
    check("the two small cards live in the strip, with no JS seating left",
          index.index('id="card-home"') < index.index('id="cmd-card"')
          < index.index('id="setbonus-blurb"') < index.index('id="endgame-panel"')
          and "cat-side" not in css.replace("/* (.cat-body / .cat-side are DELETED", "")
          and '_cc.append(n)' not in app_js and 'id="cat-side"' not in app_js,
          "matches the definitions, not the comments recording that the sidebar went")
    # ⚠ REVERTED and pinned (work order 2026-08-04 3:11 PM): multicol assigns
    # boxes to columns by HEIGHT, so it flowed column-major and stacked Primary
    # under Secondary. The catalogue's premise is one powerset per column.
    # 🧩 LAYOUT MODE — the design tool Joel asked for (2026-08-04). It must be a
    # VIEW-only tool: if it can ever touch build state it is a bug, not a feature.
    # ⚠ Reachable by KEYBOARD now, not the View menu (Joel, 2026-08-05 — it is my
    # design tool, and it sat under Alignment as if it were a player feature).
    # The tool itself is untouched; only its menu entry went.
    check("layout mode exists and is reachable (Ctrl+Shift+L)",
          "window.toggleLayoutMode" in app_js
          and 'e.ctrlKey && e.shiftKey && (e.key === "L" || e.key === "l")' in app_js
          and "body.layout-mode .lay-target" in css)
    # Scoping is the whole safety story: a layout-mode rule that touches an APP
    # selector without body.layout-mode in front of it would leak into the shipped
    # layout, and leaving the mode would no longer restore it. Rules that only
    # target the tool's own furniture (#lay-hud, .lay-*) are fine unscoped.
    _laycss = css[css.find("/* ── 🧩 LAYOUT MODE"):]
    _laysel = [ln.split("{")[0].strip() for ln in _laycss.splitlines() if "{" in ln
               and not ln.strip().startswith(("/*", "*"))]
    check("...and it is scoped: no layout-mode rule touches an app selector unscoped",
          bool(_laysel) and all("layout-mode" in s          # body.layout-mode, or
                                                            # body.lay-holding.layout-mode
                                or all(p.lstrip().startswith((".lay-", "#lay-"))
                                       for p in s.split(","))
                                for s in _laysel),
          f"checked {len(_laysel)} selectors; leaving the mode must restore the shipped layout")
    _lay = app_js[app_js.find("const LAY_AREAS"):app_js.find("init();", app_js.find("const LAY_AREAS"))]
    check("NEGATIVE CONTROL: layout mode never writes build state",
          not any(s in _lay for s in ("recordEdit(", "saveProgress(", "solveSlotting(",
                                      "autoSaveTick(", "/build/solve")),
          "a design tool that can dirty a character is a bug with a nice outline")
    check("the toolbar is a real element with real buttons",
          "_LAY_BAR" in _lay and 'class="lay-bar"' in _lay
          and "body.layout-mode .lay-bar" in css,
          "a ::before badge has pointer-events: none and can never be clicked")
    # ⛔ MOVING AREAS IS DELETED (Joel, 2026-08-04: "Let's remove all this moves
    # functions, they are simply not working"). Three shapes were tried in one
    # evening — HTML5 drag, a 12px ⤵ target, whole-area drop targets — and all three
    # went with it. Resizing is what survived; moving panels is a CSS job done from
    # his numbers. This is the pin, same class as "no packer, ever again".
    check("NEGATIVE CONTROL: no move machinery anywhere in layout mode",
          not any(s in _lay for s in ("LAY_PICK", "_layPlaceBefore", "_layHomes",
                                      "_layRecordOrder", "lay-holding", "dataTransfer",
                                      "dragstart", 'data-lay-act="pick"',
                                      'data-lay-act="place"', 'data-lay-act="col"'))
          and "lay-holding" not in css and ".lay-picked" not in css,
          "matches the definitions, in BOTH files, not the comments recording why")
    check("...and a legacy draft's saved moves are dropped, never re-applied",
          "delete d.order" in _lay,
          "an old draft must not re-parent panels after the feature is gone")
    check("hiding an area survives, and is REVERSIBLE",
          'data-lay-act="hide"' in _lay and "window.layShow" in _lay
          and "lay-restore" in css,
          "choice doctrine: a removed area that cannot come back is a trap")
    check("...and the size snapshot needs no layout callback to work",
          "new ResizeObserver" not in _lay and "_laySnapshot" in _lay
          and 'addEventListener("pointerup"' in _lay,
          "the pane fires no layout callbacks, so an observer here is untestable code")
    check("the catalogue is a GRID of wide tracks, never multicol",
          ".cat-cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(205px, 1fr))" in css
          and "column-width: 210px" not in css,
          "205px = four tracks in HIS ~870px column, so the 7 boxes tile as two rows")
    # Joel, 2026-08-04: "an exact color of the tab showing a line around the content
    # it belongs to… for every tab. Note this theme will follow the same alignment
    # color changes." The line must be the VARIABLE, not a copy of its value, or a
    # theme change splits the tab from its own outline.
    check("the tab's line is drawn in the same variable the active tab is",
          "background: var(--accent)" in css.split(".tab[aria-selected=\"true\"]")[1][:120]
          and ".tabpanel:not([hidden])" in css
          and "border: 2px solid var(--accent); border-top: 0;" in css,
          "one variable, so the four alignment themes move tab and outline together")
    check("...and it CONNECTS to the bottom of the tabs, with no gap and nothing above them",
          ".tabbar { border-bottom: 2px solid var(--accent); }" in css
          and ".build-tile { border-left: 2px solid var(--accent); border-right: 2px solid var(--accent); }" in css
          and "#tabpanels { padding: 0 0 var(--s3); }" in css,
          "the strip's bottom edge IS the top of the box; nothing is drawn around the tabs")
    # ⚠ NO SIDEWAYS SCROLLING (Joel, 2026-08-04, twice: the incarnate selects and
    # then "It also exists in the help drop down"). The journey road is the one
    # deliberate horizontal surface and stays.
    # The two allowed horizontal surfaces: the leveling road (deliberate) and the
    # tab strip (chrome — and wrapping it stacked the tabs, which was rejected).
    _oxlines = [ln.strip() for ln in css.splitlines() if "overflow-x: auto" in ln]
    check("nothing scrolls sideways except the leveling road and the tab strip",
          len(_oxlines) == 2 and any(".jny-strip" in ln for ln in _oxlines),
          f"{len(_oxlines)} overflow-x rules in the sheet")
    # Joel, 2026-08-04: the same tab-owns-its-content edge on the four menus, "but
    # not as bright" and "no highlight will appear at all, until a drop down is
    # chosen". So: nothing on a closed or hovered button, a DIMMED derived edge on
    # the open one, and the panel meets it with no gap.
    # ⚠ The mix is INLINE at each use site, never a :root custom property: a var()
    # inside a custom property resolves where it is DECLARED, so a --menu-edge on
    # :root baked in the root blue and Villain drew a blue menu edge (measured).
    # ⚠ Comments stripped first: the comment that RECORDS the deleted token names
    # it, and asserting against the raw sheet made this check fail on its own
    # explanation — the "match the definition, not the comment" rule, inverted.
    _css_nc = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    check("a menu draws its edge only while OPEN, in a dimmed per-theme colour",
          _css_nc.count("color-mix(in srgb, var(--accent) 55%, #05080d)") == 2
          and "--menu-edge:" not in _css_nc
          and ".menu-top:hover { color: var(--ink); }" in _css_nc,
          "two use sites, no token — a :root token could not follow the theme")
    # Joel, 2026-08-04: "All the fonts on the Stats page are not uniform. There is
    # also this gap between the name of the stat and the percentage. I would like a
    # short description of what each stat means on a single line."
    check("every stat row carries a one-line meaning between its name and number",
          "const _STAT_DESC = {" in app_js and "_statDesc(" in app_js
          and "grid-template-columns: minmax(88px, max-content) 1fr auto;" in css
          and ".o-desc" in css,
          "a three-column grid: the sentence fills what used to be dead space")
    # ⚠ The ⓘ on an IO promised full details and, from the Stats tab, rendered them
    # into #power-info — a panel on the HIDDEN powers tab (Joel, 2026-08-04: "it
    # does not show details"). It renders into the visible tab's panel now.
    check("the enhancement ⓘ opens where the user is, with a way back",
          "const _infoHost = () =>" in app_js
          and 'document.body.classList.contains("tab-stats")' in app_js
          and "window.closeEnhInfoToStat" in app_js
          and ".sb-back" in css,
          "on Stats it takes the breakdown's place; the powers rail is unchanged")
    check("...and the breakdown says its slots are live, not a picture",
          ".sbp-how" in css and "These are the real slots" in app_js,
          "same slotHtml as the wall — click, ⓘ and right-click all work here")
    # Joel's standing rule, 2026-08-04: "every change made somewhere... must refresh
    # the update everywhere", and Ctrl+Z must name what it will take back.
    check("Ctrl+Z ASKS, and names the specific edit",
          "_undoDescription()" in app_js and "_UNDO_ASKING" in app_js
          and 'title: "Undo?"' in app_js
          and "EDIT_HISTORY[_undoIndex()]" in app_js,
          "derived by diffing the snapshot — a hand-written label goes stale")
    check("...and neither undo nor its prompt can land on a no-op snapshot",
          "function _undoIndex()" in app_js and "const _sameBuild =" in app_js,
          "a snapshot equal to the live build made Ctrl+Z look broken")
    check("one edit refreshes every surface",
          "renderMiniWall();\n  renderStatBreakdown();" in app_js,
          "stats render ends by re-deriving the mini wall and any open breakdown")
    # COVERAGE DENOMINATOR for the copy (Joel: "we need similar descriptions for
    # all the empty stats - like enemy debuffs"). The denominator is the effect
    # vocabulary the DATA carries, listed in _OFF_EFFECTS — my first pass invented
    # names ("Recharge", "Speed", "Max HP") and three rows rendered blank on his
    # own build. Both sides of every effect must have a sentence.
    _effects = re.search(r"const _OFF_EFFECTS = \[(.*?)\];", app_js, re.S)
    _names = re.findall(r'"([A-Za-z]+)"', _effects.group(1)) if _effects else []
    _gaps = [f"{side}:{n}" for n in _names for side in ("debuff", "buff")
             if f'"{side}:{n}":' not in app_js]
    check(f"every debuff/buff effect has a one-line meaning, both sides "
          f"({len(_names) * 2} of {len(_names) * 2})",
          bool(_names) and not _gaps,
          "missing: " + ", ".join(_gaps) if _gaps else "denominator is the data's own vocabulary")
    check("...and the Stats board keeps ONE type scale and ONE row shape",
          "#stats .small, #stats .muted.small { font-size: 12px; }" in css
          and "#stats .aoe-tag, #stats .im-tag { font-size: 11px; }" in css
          # offense rows share the three-column grid, so the whole board matches
          and css.count("grid-template-columns: minmax(88px, max-content) 1fr auto;") == 2
          and ".offense .o-row.im-row { display: block; }" in css,
          "measured 6 sizes before (two 'small' spans rendered 14px), 4 after")
    check("...and the panel MEETS its button (no gap, no shift when it opens)",
          "position: absolute; top: 100%; right: 0; left: auto;" in css
          and ".menu-top {\n  border: 2px solid transparent; border-bottom: 0;" in css,
          "the transparent border is reserved so opening cannot move the row")
    check("menus open INWARD from the right edge, so they cannot clip",
          "right: 0; left: auto;" in css
          and "max-width: min(420px, calc(100vw - var(--s4) * 2));" in css,
          "left-anchored, a 330px menu on a right-hand button ran off the window")
    check("...and the inherent card's CSS went with the card",
          "#inherent-card" not in css and ".ih-row" not in css,
          "dead rules dressing nothing is how a sheet rots")
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
              # entry-ingame retired 2026-08-05 (Joel: "two options that do the
              # same thing") — #import-btn opens the panel it used to open.
              ("entry-continue", "entry-scratch", "entry-respec", "import-btn",
               "export-btn", "save-btn", "start-over-btn",
               "tour-btn", "help-btn", "bug-btn", "champ-btn", "update-btn")),
          "these are the ids app.js already binds — re-homed, not rewired")
    check("menu items keep their descriptions", index.count("<i>") >= 10,
          "easy to navigate means knowing what a thing does before clicking it")
    check("Escape and outside-click both close the menus",
          'e.key === "Escape"' in app_js
          and 'if (!e.target.closest(".menubar")) closeMenus();' in app_js)

    # ── 8. PORTABLE IS NOT INSTALLED (BasiliskXVIII, forum topic 64761) ────
    # The portable copy's "Check for updates" ran the Setup exe and silently
    # converted him into an installed user. Exercised for real against the
    # function, both arms, because the whole defect was a branch that did not
    # exist. The uninstaller is the tell: Inno writes unins000.exe beside the
    # exe, the zip never has one.
    import server as srv
    _frozen, _exe = getattr(sys, "frozen", None), sys.executable
    try:
        with tempfile.TemporaryDirectory() as d:
            sys.frozen = True           # type: ignore[attr-defined]
            sys.executable = os.path.join(d, "HeroCompanion.exe")
            check("a copy with no uninstaller beside it reads as portable",
                  srv._install_kind() == "portable")
            open(os.path.join(d, "unins000.exe"), "w").close()
            check("a copy with the Inno uninstaller beside it reads as installed",
                  srv._install_kind() == "installed",
                  "negative control for the line above — same dir, one file added")
    finally:
        sys.executable = _exe
        if _frozen is None:
            del sys.frozen              # type: ignore[attr-defined]
        else:
            sys.frozen = _frozen        # type: ignore[attr-defined]
    check("a source run still reads as source", srv._install_kind() == "source")
    srv_py = read("server", "server.py")
    check("portable is refused BEFORE the installer is ever launched",
          srv_py.index('kind == "portable"') < srv_py.index('"/SILENT"'),
          "the refusal has to be upstream of the Popen, not a message after it")

    # The Play Log's off switch and its when, on the surface that owns them.
    check("the Logging tab states the off switch and the startup choice",
          "function gamelogChoiceRow()" in app_js
          and "gamelogChoiceRow();" in app_js
          and 'playlogConsent(\'off\')' in app_js)
    check("the autostart checkbox does not open About from the Logging tab",
          '$("about-modal").classList.contains("hidden")' in app_js,
          "negative control: showAbout() unconditionally would stack a modal")

    # ── 9. ONE IMPORT DOOR (Joel, 2026-08-05) ──────────────────────────────
    # "There are two options that do the same thing, and neither do a good job
    # explaining how to do it." Both ended in importBuildText(); the menu now
    # carries one item, and it opens the panel that TEACHES both routes.
    check("the menu carries exactly one import item",
          'id="entry-ingame"' not in index and index.count('id="import-btn"') == 1)
    check("it opens the panel, not a bare OS file dialog",
          '$("import-btn").addEventListener("click", () => showEntry("ingame"));' in app_js,
          "negative control: the old wiring was () => $(\"import-file\").click()")
    check("the panel teaches BOTH ways of getting a file",
          "/build_save_file" in index and ".mbd" in index
          and index.count('class="imp-route"') == 2)
    check("both routes reach the same picker",
          'id="ingame-pick-go"' in index and 'id="ingame-mbd-go"' in index
          and app_js.count('$("import-file").click()') == 2)
    # ⚠ Comments STRIPPED first. A comment naming what was deleted is the record
    # of why; only a live RULE is a dead reference. This battery already learned
    # that lesson once ("matches the old EXPRESSION, not the comment").
    css_rules = re.sub(r"/\*.*?\*/", "", read("static", "style.css"), flags=re.S)
    # ⚠ ONE DISPLAY NAME PER SURFACE. The tab said "Leveling Guide" and the panel
    # it opened said "The Leveling Journey" (Joel, 2026-08-05). The internal
    # names stay journey-*/.jny-*/`/journey/...` on purpose — identifier, not
    # identity — so this pins the RENDERED text only.
    check("the leveling surface calls itself the same thing everywhere",
          "Leveling Journey" not in index and "Leveling Journey" not in app_js
          and "Leveling Journey" not in read("static", "tour.js")
          and "<h2>🗺️ Leveling Guide</h2>" in index,
          "tab label, panel heading, greeting and tour all read Leveling Guide")

    # ⚠ The side preview sits DIRECTLY under the Leveling Guide title (Joel,
    # 2026-08-05) — it used to render below the level-detail panel, most of a
    # page down, where nobody found Flashback at all. Pinned by ORDER, since
    # "it exists somewhere in the body" is exactly what was already true.
    _jny = app_js[app_js.find('$("journey-body").innerHTML ='):]
    _jny = _jny[:_jny.find("_wireJourneyDrag();")]
    check("the side preview renders above the road, not under it",
          -1 < _jny.find("jny-alignbar") < _jny.find("jny-roadrow")
          and _jny.find("jny-alignbar") < _jny.find('jny-panel" id="jny-panel"'),
          "order inside the one template that builds the guide")
    # ⚠ MOVED, NOT RESTRUCTURED (Joel: "I did not ask you to separate it, I asked
    # you to move it"). One row, one map over all five buttons — a filtered pair
    # of runs is the thing that was rejected.
    check("the menu moved WHOLE — one row, all five buttons",
          "jny-align-or" not in app_js and 'a.key !== "praetorian"' not in app_js
          and app_js.count("_ALIGNMENTS.map(a =>") == 1,
          "negative control: the split version filtered _ALIGNMENTS into two runs")
    # ⚠ PREVIEW MEANS PREVIEW (Joel, 2026-08-05). The reset lived only in
    # closeJourneyView(), which the tab strip never calls — so leaving via the
    # tabs kept the previewed side. It belongs in activateTab, the one route
    # every exit takes. Negative control: the old home must NOT still hold it,
    # or "one place owns it" is a comment rather than a fact.
    _act = app_js[app_js.find("function activateTab("):]
    _act = _act[:_act.find("\n}\n")]
    _close = app_js[app_js.find("function closeJourneyView("):]
    _close = _close[:_close.find("\n}\n")]
    check("the side preview resets on leaving the tab, by ANY route",
          'if (key !== "leveling") _JNY_ALIGN = null;' in _act
          and "_JNY_ALIGN = null" not in _close,
          "activateTab owns it; closeJourneyView no longer keeps a second copy")
    # ⚠ And the other direction (Joel): choosing a real alignment in the View
    # menu must WIN over a preview already showing. _journeyAlign() reads
    # `_JNY_ALIGN || cohAlignment`, so without this the stale preview outranked
    # the choice the user just made — theme flips, road does not.
    _apply = app_js[app_js.find("function applyAlignment("):]
    _apply = _apply[:_apply.find("\n}\n")]
    # ── 10. THE VIEW MENU, TRIMMED (Joel's marked-up screenshot, 2026-08-05) ──
    css_all = read("static", "style.css")
    _view = index[index.find('id="m-view"'):]
    _view = _view[:_view.find("</div>", _view.find("data-align=\"villain\""))]
    check("End Game is gone from the View menu",
          'data-jump="endgame-panel"' not in _view and ">End Game<" not in _view,
          "it pointed at panels on Powers & Slots, which this menu already lists")
    check("...but the ladder gates can still reach those panels",
          "window.openEndgame = function" in app_js
          and "openEndgame('endgame-plan-panel')" in app_js,
          "negative control: removing the menu item must not remove the route")
    check("Layout mode is gone from the View menu, with no dangling reference",
          'id="layout-mode-item"' not in index and "layout-mode-item" not in app_js,
          "my design tool, not a player feature — it sat under Alignment as if it were")
    check("...and Ctrl+Shift+L still opens it",
          'e.ctrlKey && e.shiftKey && (e.key === "L" || e.key === "l")' in app_js
          and "window.toggleLayoutMode" in app_js,
          "the tool is untouched; only its menu entry went")
    check("Exemplared view opens a dialog that EXPLAINS it, not a bare dial",
          'id="exemplar-modal"' in index
          and 'exemplarDialog' in app_js.replace("openExemplarDialog", "exemplarDialog")
          and "Exemplaring is the game dropping you to a lower level" in index
          and 'id="exemplar-sel-modal"' in index,
          "what it means AND what level, in the same place")
    check("...and all three dials stay one state",
          app_js.count('"exemplar-sel", "exemplar-sel-stats", "exemplar-sel-modal"') == 2,
          "the setter and the initialiser both know about the modal's dial")
    # Comments stripped: the note recording that the pulse went is the record of
    # why, not a live rule. (Second time today this exact shape bit me.)
    _css_rules = re.sub(r"/\*.*?\*/", "", css_all, flags=re.S)
    check("the walk-you-to-the-dial pulse went with the behaviour it served",
          "exemp-pulse" not in app_js and "exemp-pulse" not in _css_rules
          and "exempulse" not in _css_rules,
          "negative control: dead CSS left dressing nothing is how sheets rot")

    # ── 11. THE BUILD MENU (Joel's second marked-up screenshot, 2026-08-05) ──
    check("Refine with AI is gone from the Build menu",
          'data-act="opt-btn"' not in index,
          "the shipped client reports ai_enabled:false, so it could never be used")
    check("...and the AI seam itself is untouched (the hub still opts in)",
          "AI_ON = !!h.ai_enabled" in app_js and 'id="opt-btn"' in index,
          "negative control: removing the menu entry must not rip out HC_AI=1")
    # ⚠ The reported "cancel greys the menu" was NOT a state bug — the items were
    # greyed for real reasons the menu never stated, so a cancelled dialog got
    # the blame. Every gated item now carries its reason.
    _mb = index[index.find('id="m-build"'):]
    _mb = _mb[:_mb.find("</div>", _mb.find('data-act="reset-btn"'))]
    check("every gated Build item can say WHY it is unavailable",
          all(f'data-act="{a}"' in _mb and _mb.count("data-why=") >= 6
              for a in ("solve-btn", "gen-btn", "changes-btn", "undo-btn", "reset-btn")),
          "grey out, never hide — and put the reason on it")
    check("...and syncMenu swaps the reason in, restoring the real text after",
          "sub.dataset.orig" in app_js and 'mi.dataset.why' in app_js,
          "negative control: the original description must come back, not stay overwritten")

    # Pop-ups wear the alignment (Joel): --accent is the per-theme token, so ONE
    # rule follows all four rather than a colour per theme.
    check("all three pop-up shapes carry the alignment edge",
          all(f"{sel} {{" in css_all.replace("\n", " ") or sel in css_all
              for sel in (".modal-box", ".ask-card", ".ct-card"))
          and css_all.count("0 0 0 3px color-mix(in srgb, var(--accent) 22%, transparent)") == 3,
          "modal-box, ask-card and ct-card — the same edge on each")

    # ── 12. HELP MENU: Settings and Credits are their own doors ─────────────
    _mh = index[index.find('id="m-help"'):]
    _mh = _mh[:_mh.find("</div>", _mh.find("showAbout('about')"))]
    check("Settings, Credits and About are each reachable from Help",
          "showAbout('settings')" in _mh and 'id="credits-btn"' in _mh
          and "showAbout('about')" in _mh,
          "they were all buried inside one 'About & Settings' entry")
    check("Settings LEADS with the switches, About leads with the versions",
          'focus === "settings"\n    ? settings + versions' in app_js.replace("\r\n", "\n")
          or "? settings + versions" in app_js,
          "same dialog and same state — only the order changes")
    check("the Play Log switch is in Settings, wired to the SAME setter",
          "playlogConsent(this.checked ? 'on' : 'off')" in app_js
          and app_js.count("window.playlogConsent") == 1,
          "one state, one setter — never a second copy of the choice")
    check("Settings does not offer a tray toggle the app cannot honour",
          "Hero Companion has no" in app_js and "notification-area icon" in app_js,
          "the tray was deleted in 2026-08-02; a switch for it would be a lie")
    # ⚠ The header version click is `hv.onclick = showAbout`, which passes a
    # MouseEvent — the bare-handler trap already recorded against showEntry.
    check("showAbout only honours a STRING focus",
          'typeof focus === "string" ? focus : _ABOUT_FOCUS' in app_js,
          "negative control: a MouseEvent must not be read as a mode")

    # ── 13. SMALL DISPLAYS (Joel, 2026-08-05: "when I am not full screen the
    # right side creates a huge vertical gap ... fix that for people with
    # smaller displays"). Both two-column regions still collapse — the void has
    # nowhere to form — but they do it at DIFFERENT widths on purpose.
    # ⚠ CHANGED 2026-08-06 on Joel's ruling ("not where it used to be with an
    # arrow pointing to them all in a right hand column"): the stats side column
    # is 300-380px of REAL content that only exists while a stat is selected,
    # not a strip of nothing, and 1400px was collapsing it at his own effective
    # width. It now holds to 1000px. The powers rail keeps 1400. What this check
    # protects is unchanged: neither region may lose its collapse entirely.
    _narrow = css_all[css_all.find("@media (max-width: 1400px)"):]
    check("both two-column regions still collapse, at their own widths",
          "@media (max-width: 1400px)" in css_all
          and ".powers-layout:has(#power-info:not(.hidden)) { grid-template-columns: minmax(0, 1fr); }" in _narrow
          and "@media (max-width: 1000px)" in css_all
          and ".stats-provlayout { grid-template-columns: minmax(0, 1fr); }" in css_all,
          "powers-layout at 1400, stats-provlayout at 1000; neither may lose it")
    # The stats column must NOT go back to collapsing at 1400 — that is the
    # regression Joel reported, and it read to him as the column disappearing.
    # ⚠ Match the exact COLLAPSE declaration, not the bare selector — the base
    # `.stats-provlayout { display: grid; … }` rule sits between the two media
    # blocks and made a looser check fail on innocent CSS.
    _collapse = ".stats-provlayout { grid-template-columns: minmax(0, 1fr); }"
    _wide_narrow = css_all[css_all.find("@media (max-width: 1400px)"):
                           css_all.find("@media (max-width: 1000px)")]
    check("...and the stats column is not collapsed at 1400 any more",
          _collapse not in _wide_narrow and _collapse in css_all,
          "negative control: collapsing stats at 1400 is the bug he reported")
    # ⚠ :has() takes its ARGUMENT's specificity, so the narrow override must
    # repeat the whole selector — a bare `.powers-layout` there loses to the id
    # inside it, and a small display would still get a column when ⓘ opened.
    check("...and the narrow override repeats the :has() selector",
          "#power-info:not(.hidden)" in _narrow[:_narrow.find("}\n.powers-main")],
          "specificity: an id inside :has() outranks a bare class")

    # ── 13a. "NOW SLOT THEM" IS A CLAIM, NOT A DECORATION (Joel, 2026-08-06:
    # "This appears no matter if slots are all filled or not"). It may only show
    # when the shared pool has free slots or a REAL power holds an empty one —
    # the seven granted inherents are excluded, or the nag is permanent.
    check("the slot invitation is gated on there being slots to fill",
          "const head = full && (_freeSlots || _emptyHere)" in app_js
          and "All 24 powers picked, every slot filled." in app_js,
          "a full pick list is not the same claim as an unfinished slotting")
    check("...and the granted inherents cannot make it permanent",
          '_emptyHere = build.powers.some(p => !(p.full_name || "").startsWith("Inherent.")' in app_js,
          "Brawl/Sprint/Rest carry a base slot the solver is capped out of by design")

    # ── 13b. NO SIDE BAR UNLESS AN ENHANCEMENT IS ASKED FOR (Joel, 2026-08-06:
    # "the output of a build assistant is terrible on the far right ... let it
    # take up the entire horizontal width so no side bar appears at all, unless
    # IO details are asked to be displayed").
    _side = index[index.find('<div class="powers-side">'):]
    _side = _side[:_side.find("</div>")]
    check("the side column holds ONLY the ⓘ enhancement card",
          'id="power-info"' in _side
          and 'id="assistant"' not in _side and 'id="endgame-plan-panel"' not in _side,
          "the Assistant's output is tabular; 340px turned its tables into fragments")
    check("epic/incarnates come BEFORE the Assistant, both full width",
          0 < index.find('id="endgame-plan-panel"') < index.find('id="assistant"')
          and index.find('id="assistant"') < index.find('class="pw-cardband"'),
          "his order: epic and incarnate first, then Build Assistant, under the builder")
    check("one column by default, two only while the card is up",
          ".powers-layout {\n  display: grid; grid-template-columns: minmax(0, 1fr);" in css_all
          and ".powers-layout:has(#power-info:not(.hidden)) {" in css_all,
          "the CARD opens the column, in CSS — no class for JS to forget to clear")
    check("the dead has-info class is gone with the layout it never styled",
          "has-info" not in app_js and "powers-layout.has-info" not in css_all,
          "negative control: three JS toggles drove a class no app rule read")
    check("nothing stretches a column's last tile any more",
          ".powers-main > :last-child" not in css_all,
          "the grout rule would have stretched the ⓘ card to the builder's height")
    # The warning must carry its own remedy — his level-50 character was recorded
    # as level 1 and the only level input lived on another tab.
    check("the endgame warning carries the level control that fixes it",
          "warn-fix" in app_js and "setCurrentLevel(this.value)" in app_js
          and app_js.count("window.setCurrentLevel") == 1,
          "same setter as the Leveling Guide input — one writer, and it autosaves")
    # ⚠ setCurrentLevel runs from the STATS banner now, where the walk's steps are
    # not loaded. renderLevelStep did steps[i].picks and threw, which killed the
    # function BEFORE autoSaveTick — so the level the user typed was lost as well
    # as erroring. The guard belongs in renderLevelStep, where every caller routes.
    _rls = app_js[app_js.find("function renderLevelStep()"):]
    _rls = _rls[:_rls.find("\n}\n")]
    # ⚠ Scoped to renderLevelStep: the wizard's own render writes #wiz-plan-out
    # on the line after it CREATES it, which is safe and must not fail this.
    check("renderLevelStep survives being called off the tab that hosts it",
          "steps && steps[i]" in _rls and "if (!s || !out) return;" in _rls
          and '$("wiz-plan-out").innerHTML' not in _rls and "out.innerHTML" in _rls,
          "BOTH guards: unloaded steps AND a missing #wiz-plan-out (the real crash)")

    check("the real alignment toggle outranks an active preview",
          'localStorage.setItem("cohAlignment", al)' in _apply
          and "_JNY_ALIGN = null" in _apply
          and _apply.find('setItem("cohAlignment"') < _apply.find("_JNY_ALIGN = null"),
          "cleared in applyAlignment — the one funnel every real change uses")

    check("...and the preview never writes the character's real alignment",
          "_JNY_ALIGN" in app_js
          and 'localStorage.setItem("cohAlignment"' not in
              app_js[app_js.find("function _alignNote"):app_js.find("window.selectJourneyStop")],
          "it sets a view flag; cohAlignment/applyAlignment belong to the app toggle")

    check("Flashback carries its context without needing a click",
          "Needs the Ouroboros unlock and level 15+" in app_js
          and "is not a side" in app_js,
          "the tip plus a standing line; the full requirement is in _alignNote")

    check("no dead reference to the retired menu item survives",
          "entry-ingame" not in read("static", "tour.js")
          and "#entry-ingame" not in css_rules and ".entry-steps" not in css_rules,
          "the tour targeted it and the stylesheet dressed it")

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
