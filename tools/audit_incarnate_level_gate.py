"""PIN for the endgame-eligibility WARN-BUT-ALLOW gate (Joel's ruling
2026-07-17, choice doctrine): Epic/Ancillary powers unlock at level 35 (Patron
pools also need their Patron arc), incarnates at level 50. The 1-50 leveling
walk PREVIEWS the finished build, so we DON'T block — the player may toggle
incarnates on / keep epic picks, and we WARN that these aren't available at
their level yet. The "Build a new level-50 character" path never warns.

Client-side UI logic (the toggle + warning live in app.js), so these are
source-level assertions — the same shape as the card-strip pins.

Run:  py tools\\audit_incarnate_level_gate.py
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "static", "app.js")
IDX = os.path.join(ROOT, "static", "index.html")
app = open(APP, encoding="utf-8").read()
idx = open(IDX, encoding="utf-8").read()
checks = 0
fails = 0


def ok(cond, msg):
    global checks, fails
    checks += 1
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        fails += 1


# the unlock predicate keys on level_reached >= 50 (used for messaging)
gate = app.split("function incarnatesUnlocked(")[1].split("}")[0] \
    if "function incarnatesUnlocked(" in app else ""
ok(bool(gate) and "level_reached" in gate and ">= 50" in gate,
   "incarnatesUnlocked() gates on level_reached >= 50")

# WARN-BUT-ALLOW: the warnings function covers both gated classes with the
# right level thresholds and the Patron-arc caveat
w = app.split("function endgameWarnings(")[1].split("\nfunction ")[0] \
    if "function endgameWarnings(" in app else ""
ok(bool(w), "endgameWarnings() exists")
ok("isLevelingBuild()" in w,
   "warnings only fire on the 1-50 leveling walk (a fresh level-50 never warns)")
ok("include_incarnates" in w and "lv < 50" in w,
   "incarnate warning fires when previewing incarnates below level 50")
ok('"Epic."' in w and "lv < 35" in w,
   "epic warning fires when an Epic power is in the plan below level 35")
ok("Patron" in w,
   "the epic warning names the Patron-arc requirement (not just the level)")

# it must ALLOW, not block: the toggle handler no longer refuses/disables
h_anchor = '$("incarnate-peak-toggle").addEventListener'
h = app.split(h_anchor)[1].split("});")[0] if h_anchor in app else ""
ok("!incarnatesUnlocked()" not in h and "e.target.checked = false" not in h,
   "the peak-toggle handler ALLOWS the preview below 50 (no refusal/force-off)")
ok("cb.disabled" not in app,
   "the peak toggle is never disabled (warn, don't block)")

# the warning is rendered from recompute() and on level change, into a banner
rec = app.split("async function recompute(")[1].split("\nasync function ")[0]
ok("renderEndgameWarnings()" in rec,
   "recompute() renders the endgame warnings")
setlvl = app.split("window.setCurrentLevel")[1].split("};")[0] \
    if "window.setCurrentLevel" in app else ""
ok("renderEndgameWarnings()" in setlvl,
   "setCurrentLevel() refreshes the warning when the tracked level changes")
ok('id="endgame-warn"' in idx,
   "the warning banner container exists in index.html")

# honest labeling: the provenance line marks an active sub-50 preview
ok("endgame preview (unlock at 50)" in app,
   "the provenance line marks incarnates as an endgame preview when previewed below 50")

print(f"\n{checks} checks, {fails} failed")
sys.exit(1 if fails else 0)
