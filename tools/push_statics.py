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
    # ⚠ THE WHOLE TREE, NOT JUST THE TOP LEVEL (found 2026-08-05). This listed
    # `os.listdir(SRC)` files only, so static/vendor/ and static/icons/ were
    # never synced — a new vendored font landed in the repo, the CSS that used
    # it landed in both frozen copies, and the font itself reached neither. The
    # tool printed "2 of 2 known copies updated" over the miss, which is exactly
    # the assumed-not-visible failure it was written to end.
    names = sorted(os.path.relpath(os.path.join(dp, n), SRC)
                   for dp, _, fs in os.walk(SRC) for n in fs)
    found = 0
    for base in TARGETS:
        dest = os.path.join(base, "_internal", "static")
        if not os.path.isdir(dest):
            print(f"  skip   {base}  (not installed here)")
            continue
        found += 1
        wrote = 0
        for n in names:
            s, d = os.path.join(SRC, n), os.path.join(dest, n)
            st = os.stat(s)
            if os.path.exists(d):
                dt = os.stat(d)
                if dt.st_size == st.st_size and dt.st_mtime >= st.st_mtime:
                    continue          # already current (icons are ~6k files)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            wrote += 1
        print(f"  ✓ {wrote:>4} of {len(names)} files written -> {dest}")
    # Coverage denominator, same rule as every other checker here: say the number
    # and fail loudly rather than report success over an empty sweep.
    print(f"\n{found} of {len(TARGETS)} known copies updated")
    if not found:
        print("NOTHING WAS UPDATED — no frozen copy found")
        sys.exit(1)
    print("⚠ relaunch each copy: statics load at launch, F5 does nothing in WebView2")


if __name__ == "__main__":
    main()
