# -*- mode: python ; coding: utf-8 -*-


import os

# the inbox upload key is gitignored and BUILD-TIME only — a release build without it
# would ship an inert feed, so fail loudly rather than package a broken product
_datas = [('data/chat_lexicon.json', 'data')]
if os.path.exists('data/inbox_key.bin'):
    _datas.append(('data/inbox_key.bin', 'data'))
else:
    raise SystemExit('data/inbox_key.bin missing - bake the inbox upload key first')

a = Analysis(
    ['run_lite.py'],
    pathex=['server', 'tools'],
    binaries=[],
    datas=_datas,
    hiddenimports=['build_pulse_boards', 'gamelog'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# ONEDIR (Windows Citizenship, 2026-07-17): Lite was a onefile exe, whose
# self-unpacking-to-temp behaviour is a packer heuristic AV flags. onedir (an
# EXE + an _internal folder, like the full app's HeroCompanion.spec) removes
# that heuristic and starts faster. UPX is a second AV magnet — never pack.
# The dir is wrapped by the Inno installer (installer/CompanionLite.iss) and
# the whole tree is Artifact-Signing signed by tools/sign_artifacts.py.
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='CompanionLite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                 # UPX-packed exes trip antivirus heuristics — never pack
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/HeroCompanion.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='CompanionLite',
)
