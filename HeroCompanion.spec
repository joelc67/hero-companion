# -*- mode: python ; coding: utf-8 -*-
# Hero Companion — PyInstaller build spec (onedir: friendlier to antivirus heuristics
# and faster to start than onefile). Build:  python -m PyInstaller HeroCompanion.spec
from PyInstaller.utils.hooks import collect_data_files

datas = [
    ("data", "data"),                      # parsed game database snapshot
    ("static", "static"),                  # UI + help PDF
    ("assets/HeroCompanion-icon-512.png", "assets"),   # tray icon image
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

# server/ and ai/ modules are imported via runtime sys.path — name them explicitly.
hiddenimports = [
    "server", "engine", "solver", "first_principles", "role_output", "converter",
    "leveling_schedule", "learn", "proc_pass", "mids_export", "mids_import",
    "mids_powercust", "ingame_import", "ai_build", "claude_bridge", "pulse_feed",
    "flask_cors", "requests",
    "pystray", "pystray._win32",           # tray icon backend
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

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="HeroCompanion",
    debug=False,
    strip=False,
    upx=False,                 # UPX-packed exes trip antivirus heuristics — never pack
    console=False,             # windowed: the TRAY ICON is the app's handle (Open/Quit);
                               # output goes to %APPDATA%\HeroCompanion\app.log
    icon="assets/HeroCompanion.ico",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="HeroCompanion",
)
