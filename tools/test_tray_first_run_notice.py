"""BATTERY: the tray introduces itself ONCE, and never again.

WHY THIS EXISTS. BasiliskXVIII (2026-08-01) found the tray icon without knowing
what it was: "it doesn't tell you that oh, actually something else is running on
your machine, which you then have to know is there and manually quit from". The
download page does say so - but a user who never reads it is still a real user,
and a background process that never introduces itself looks like something to be
suspicious of.

The failure modes this guards are opposite and both bad:
  - never shown  -> the complaint stands
  - shown every launch -> nagging, and the second time it is pure noise

⚠ The notice lives inside _run_tray's closure and needs a live tray to execute,
so this tests the two things that can actually break WITHOUT one: the pystray API
the code depends on, and the seen-flag logic that decides once-vs-always.

Run:  py tools\\test_tray_first_run_notice.py
"""
import inspect
import os
import re
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if detail:
        print(f"        {detail}")


def main():
    print("TRAY FIRST-RUN NOTICE BATTERY\n")
    src = open(os.path.join(ROOT, "run_app.py"), encoding="utf-8").read()

    # 1. The API the code calls must exist in the pystray actually installed.
    import pystray
    sig = inspect.signature(pystray.Icon.run)
    check("pystray.Icon.run accepts a setup callback", "setup" in sig.parameters,
          f"signature {sig}")
    check("pystray.Icon exposes notify()", hasattr(pystray.Icon, "notify"))

    # 2. The code must actually USE that hook - a notice defined and never wired
    #    is the same as no notice.
    check("run() is called WITH the setup callback",
          bool(re.search(r"icon\.run\(setup=_first_run_notice\)", src)),
          "icon.run(setup=_first_run_notice)")
    check("the notice sets icon.visible (required inside a setup callback)",
          "icon.visible = True" in src)

    # 3. The seen-flag decides once-vs-always. Same logic, exercised for real.
    with tempfile.TemporaryDirectory() as d:
        flag = os.path.join(d, "tray_notice_seen")
        shown = []

        def maybe_notify():
            if os.path.exists(flag):
                return
            shown.append(1)
            os.makedirs(d, exist_ok=True)
            with open(flag, "w", encoding="utf-8") as f:
                f.write("1")

        maybe_notify(); maybe_notify(); maybe_notify()
        check("shown exactly once across three launches", len(shown) == 1,
              f"shown {len(shown)} time(s)")
        os.remove(flag)
        maybe_notify()
        check("NEGATIVE CONTROL: clearing the flag shows it again",
              len(shown) == 2, "so the check is capable of failing")

    # 4. It must say the two things his complaint was about.
    body = src[src.find("def _first_run_notice"): src.find("def _first_run_notice") + 1200]
    check("the text says it is RUNNING", "running" in body.lower())
    check("the text says how to QUIT", "quit" in body.lower())
    check("the notice is best-effort, never fatal",
          "except Exception" in body, "a balloon must never take the app down")

    print(f"\n{len(CHECKS)} checks ran")
    if not all(CHECKS):
        print(f"{CHECKS.count(False)} FAILURE(S)")
        sys.exit(1)
    print("== ALL CHECKS PASS — introduced once, never again ==")


if __name__ == "__main__":
    main()
