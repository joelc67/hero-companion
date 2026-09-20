# -*- mode: python ; coding: utf-8 -*-


import os

# the inbox upload key is gitignored and BUILD-TIME only — a release build without it
# would ship an inert feed, so fail loudly rather than package a broken product
_datas = [('data/chat_lexicon.json', 'data')]
if os.path.exists('data/inbox_key.bin'):
    _datas.append(('data/inbox_key.bin', 'data'))
else:
    raise SystemExit('data/inbox_key.bin missing - bake the inbox upload key first')

# ⚠ VERSION RESOURCE — same blank-Details defect the full app had through
# 0.12.49 (tools/version_res.py explains why it matters). Lite's version lives
# in run_lite.py's LITE_VERSION, and lite_version.txt only moves when a release
# actually publishes, so read the CODE's value — that is what the app reports.
import re as _re
import sys as _sys
_sys.path.insert(0, 'tools')
from version_res import write_version_file as _write_version_file

_lite_version = _re.search(r'^LITE_VERSION\s*=\s*"([^"]+)"',
                           open('run_lite.py', encoding='utf-8').read(),
                           _re.M).group(1)
_write_version_file('version_info_lite.txt', _lite_version, 'CompanionLite',
                    'Companion Lite — City of Heroes chat companion',
                    product='Companion Lite')
print(f'[spec] version resource: {_lite_version}')

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
    version='version_info_lite.txt',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='CompanionLite',
)
