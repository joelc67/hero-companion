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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CompanionLite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
