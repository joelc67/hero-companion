"""PIN for the incarnate level-50 gate (Joel's game rule, 2026-07-17): incarnate
abilities exist only on a level-50 character, so the leveling walk keeps them
OFF (flag forced false, toggle disabled) until level_reached hits 50.

Client-side UI logic (the toggle + the include_incarnates flag live in app.js),
so these are source-level assertions — the same shape as the card-strip pins.
The engine already applies incarnates ONLY when include_incarnates is true; this
rule is that the client never sends true below 50.

Run:  py tools\\audit_incarnate_level_gate.py
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "static", "app.js")
app = open(APP, encoding="utf-8").read()
checks = 0
fails = 0


def ok(cond, msg):
    global checks, fails
    checks += 1
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        fails += 1


# the gate predicate exists and keys on level_reached >= 50
gate = app.split("function incarnatesUnlocked(")[1].split("}")[0] \
    if "function incarnatesUnlocked(" in app else ""
ok(bool(gate) and "level_reached" in gate and ">= 50" in gate,
   "incarnatesUnlocked() gates on level_reached >= 50")

# applyIncarnateGate forces the flag off and disables the toggle when locked
ag = app.split("function applyIncarnateGate(")[1].split("\nfunction ")[0] \
    if "function applyIncarnateGate(" in app else ""
ok("build.include_incarnates = false" in ag,
   "applyIncarnateGate() forces include_incarnates off below 50")
ok("cb.disabled = !unlocked" in ag,
   "applyIncarnateGate() disables the peak toggle when locked")

# recompute() enforces the gate BEFORE building the totals payload
rec = app.split("async function recompute(")[1].split("\nasync function ")[0]
ok("applyIncarnateGate()" in rec,
   "recompute() applies the gate before totals (so a locked build never "
   "sends include_incarnates=true)")

# the toggle handler refuses to enable it below 50
anchor = '$("incarnate-peak-toggle").addEventListener'
h = app.split(anchor)[1].split("});")[0] if anchor in app else ""
ok("!incarnatesUnlocked()" in h,
   "the peak-toggle handler refuses to fold incarnates in below 50")

# level change re-applies the gate (crossing 50 unlocks, dropping re-locks)
setlvl = app.split("window.setCurrentLevel")[1].split("};")[0] \
    if "window.setCurrentLevel" in app else ""
ok("applyIncarnateGate()" in setlvl,
   "setCurrentLevel() re-applies the gate when the tracked level changes")

# both provenance footers state the lock honestly, not the preview prompt
ok(app.count("incarnates: unlock at level 50") >= 1,
   "Build Vitals provenance line says 'unlock at level 50' when locked")
ok(app.count("incarnates unlock at level 50, so these numbers are without them") >= 1,
   "the per-card footer states the lock honestly when below 50")

print(f"\n{checks} checks, {fails} failed")
sys.exit(1 if fails else 0)
