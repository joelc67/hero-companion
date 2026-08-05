"""Copy static/ into EVERY frozen Hero Companion copy on this machine.

⚠ WHY THIS EXISTS (2026-08-05). There are two frozen copies on Joel's box:

    %LOCALAPPDATA%\\Programs\\HeroCompanion   (the installer's)
    <repo>\\dist\\HeroCompanion               (PyInstaller's output)

I spent a session copying statics into the installed one, screenshotting it, and
reporting the work verified — while Joel was launching the OTHER one and seeing
none of it. "It still shows the AI choice" was true: his copy still had the old
files. Verifying against a copy the user does not open is verification theater
with extra steps.

So the sync is mechanical now, not something to remember: this writes to every
copy it finds and PRINTS each one, so a copy that is missed is visible rather
than assumed.

⚠ Statics load at LAUNCH in the WebView2 shell (F5 does nothing) — relaunch after
running this. server.py / run_app.py changes are NOT statics: they live inside
the PYZ and need a real rebuild.

Run:  py tools\\push_statics.py
"""
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "static")

TARGETS = [
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "HeroCompanion"),
    os.path.join(ROOT, "dist", "HeroCompanion"),
]


def main():
    if not os.path.isdir(SRC):
        print(f"no static/ at {SRC}")
        sys.exit(1)
    names = [n for n in os.listdir(SRC) if os.path.isfile(os.path.join(SRC, n))]
    found = 0
    for base in TARGETS:
        dest = os.path.join(base, "_internal", "static")
        if not os.path.isdir(dest):
            print(f"  skip   {base}  (not installed here)")
            continue
        found += 1
        for n in names:
            shutil.copy2(os.path.join(SRC, n), os.path.join(dest, n))
        print(f"  ✓ {len(names):>3} files -> {dest}")
    # Coverage denominator, same rule as every other checker here: say the number
    # and fail loudly rather than report success over an empty sweep.
    print(f"\n{found} of {len(TARGETS)} known copies updated")
    if not found:
        print("NOTHING WAS UPDATED — no frozen copy found")
        sys.exit(1)
    print("⚠ relaunch each copy: statics load at launch, F5 does nothing in WebView2")


if __name__ == "__main__":
    main()
