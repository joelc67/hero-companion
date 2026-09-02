# -*- mode: python ; coding: utf-8 -*-
# Hero Companion — PyInstaller build spec (onedir: friendlier to antivirus heuristics
# and faster to start than onefile). Build:  python -m PyInstaller HeroCompanion.spec
from PyInstaller.utils.hooks import collect_data_files

# ⚠ BUILD STAMP. A frozen build has no git, so the commit is written HERE, at build
# time, and shipped as data (server.py reads it when frozen). Added 2026-08-02 after
# an installed 0.12.30 and a freshly built 0.12.30 sat on one machine and neither of
# us could tell which was on screen — a bug got reported twice against a build that
# did not contain the fix. The About dialog already promises to name "this build";
# now it can, packaged or not. build_commit.txt is derived and gitignored.
import subprocess as _sp
try:
    _commit = _sp.check_output(["git", "describe", "--always", "--dirty",
                                "--exclude=*", "--abbrev=7"],
                               stderr=_sp.DEVNULL, text=True, timeout=5).strip()
except Exception:
    _commit = ""
with open("build_commit.txt", "w", encoding="utf-8") as _f:
    _f.write(_commit)
print(f"[spec] build stamp: {_commit or '(no git)'}")

datas = [
    ("build_commit.txt", "."),             # which commit this exe was built from
    ("data", "data"),                      # parsed game database snapshot
    ("static", "static"),                  # UI + help PDF
    ("assets/HeroCompanion-icon-512.png", "assets"),   # tray icon image
    ("assets/HeroCompanion.ico", "assets"),            # window icon (pywebview needs .ico)
    ("VERSION", "."),
    ("client_config.json", "."),           # GitHub-home pointers (REPLACE-ME until repo exists)
    ("CHANGELOG.md", "."),
    ("LICENSE", "."),
    ("CREDITS.md", "."),
    ("TERMS.md", "."),
    # The gold-standard champions: converged best-known builds per context, so END USERS
    # get the 3-hour convergence run's results, not the heuristic fallback.
    ("benchmarks/champions.json", "benchmarks"),
    # Pulse Boards parity (2026-07-12): the board renderer ships in the full app
    # (private board + public preview routes build with it). The upload key
    # (data/inbox_key.bin, gitignored) rides the ("data","data") entry above
    # automatically when the release procedure drops it in — source checkouts
    # have no key and the feed is structurally inert.
    ("tools/build_pulse_boards.py", "tools"),
]
# "Add Shortcuts.bat" belongs NEXT TO the exe (dist root), not inside _internal —
# COLLECT datas land in _internal, so it's copied post-build by tools/finish_dist.py
# (or manually). Kept out of `datas` on purpose.
datas += collect_data_files("pulp")        # bundles the CBC solver binary the ILP needs

# ⚠ BUILD GATE: PyInstaller only WARNS on a missing hidden import, so a build
# environment without pywebview freezes a browser-fallback app that LOOKS fine
# to headless smokes (HC_WINDOW=0) — exactly how 0.12.46 shipped windowless
# from the fresh dev-01 box (field report, 2026-09-02). Fail the build here
# instead: if the window stack cannot import, there is no release.
import webview                                    # noqa: F401
from webview.platforms import edgechromium        # noqa: F401
import clr_loader, pythonnet                      # noqa: F401

# server/ and ai/ modules are imported via runtime sys.path — name them explicitly.
hiddenimports = [
    "server", "engine", "solver", "first_principles", "role_output", "converter",
    "leveling_schedule", "learn", "proc_pass", "mids_export", "mids_import",
    "ingame_import", "ai_build", "claude_bridge", "pulse_feed",
    "requests",
    # The app's own window: pywebview drives the WebView2 runtime that already
    # ships with Windows 10/11, so nothing extra installs on the user's machine.
    # clr_loader/pythonnet are how the Windows backend is reached.
    # (pystray is GONE with the tray — 2026-08-02.)
    "webview", "webview.platforms.edgechromium", "clr_loader", "pythonnet",
]

a = Analysis(
    ["run_app.py"],
    pathex=["server", "ai"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy.testing"],
    noarchive=False,
)
pyz = PYZ(a.pure)

# ⚠ THE BOOTLOADER SPLASH (2026-08-10, the launch-latency fix's real half).
# Measured: the WebView2/.NET window costs ~3.7s to exist no matter when the
# game data loads — so the instant feedback must come from BELOW Python. The
# PyInstaller bootloader paints this PNG in well under a second; run_app
# closes it (pyi_splash.close()) the moment the real window is up. The image
# is generated (Pillow, brand colors from style.css) and committed.
splash = Splash(
    "assets/splash.png",
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    always_on_top=False,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    exclude_binaries=True,
    name="HeroCompanion",
    debug=False,
    strip=False,
    upx=False,                 # UPX-packed exes trip antivirus heuristics — never pack
    console=False,             # windowed: no console, ever — THE WINDOW is the app,
                               # and closing it quits. Output goes to
                               # %APPDATA%\HeroCompanion\app.log.
    icon="assets/HeroCompanion.ico",
)
coll = COLLECT(
    exe,
    splash.binaries,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="HeroCompanion",
)
