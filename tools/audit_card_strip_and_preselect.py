"""PINS for Joel's walk-2 defects (2026-07-16). Static/source-level checks, so
they run in the battery without a browser.

DEFECT 1 — the card-bottom set strip was CLIPPED on every power card.
  Measured in the live DOM: band 96px vs the card's NATURAL content 149px, so
  `.set-summary` (a flex child with margin:auto 0 0) was crushed to ~0 — the
  "sliver of green" on every card. Cause: the 0.12.20 "2d" change gave the
  power name its own top line (pc-head 22 + pc-sub 23 where they used to share
  one row) and grid-auto-rows never grew to match. Fix: band 96 -> 152px.
  ⚠ MEASURE THE FREED CARD, NOT THE BROKEN ONE: the first fix used the card's
  scrollHeight (120px) and still shipped a 2.4px sliver — scrollHeight was read
  WHILE the strip was crushed, a circular measurement. Cloning the card at
  height:auto gives the truth: 22+23+35+18+20+12 = 149.
  PIN: the band must stay >= the measured content ceiling. If someone adds
  another row to the card, this fails loudly instead of silently eating the
  strip again.

DEFECT 2 — accolade preselect fired ONLY on the wizard's Build; Joel's route
  and every other generator got nothing (ACCOLADES 0/28, no stated assumption).
  This is the ENTRY-POINT CLASS bug, the same shape as the reset defect: the
  rule is "EVERY level-50 generation path", and wiring one member is exactly
  how the last one bit us.
  PIN: every function that generates a build (calls /build/autopick and then
  assigns build.powers) must call preselectStandardAccolades(). New generators
  fail this check until wired.

Run:  py tools\\audit_card_strip_and_preselect.py
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "static", "app.js")
CSS = os.path.join(ROOT, "static", "style.css")

# the UNCONSTRAINED (cloned, height:auto) card height on a real solved build,
# 2026-07-16 — never the crushed scrollHeight, which reads low by design
MEASURED_CONTENT_CEILING = 149
fails = []


def check_band():
    css = open(CSS, encoding="utf-8").read()
    m = re.search(r"\.powers-wall\s*\{[^}]*?grid-auto-rows:\s*(\d+)px", css,
                  re.S)
    if not m:
        fails.append("could not find .powers-wall grid-auto-rows")
        return
    band = int(m.group(1))
    ok = band >= MEASURED_CONTENT_CEILING
    print(f"  card band: {band}px  vs measured content ceiling "
          f"{MEASURED_CONTENT_CEILING}px  -> {'OK' if ok else 'CLIPS THE STRIP'}")
    if not ok:
        fails.append(f"band {band}px < content {MEASURED_CONTENT_CEILING}px — "
                     f"the set-summary strip gets crushed (walk-2 defect 1)")


def check_generators():
    src = open(APP, encoding="utf-8").read()
    # every function body that autopicks AND assigns build.powers is a generator
    fn_re = re.compile(
        r"(?:async\s+function\s+(\w+)|window\.(\w+)\s*=\s*async\s+function)\s*\([^)]*\)\s*\{",
        re.S)
    starts = [(m.start(), m.group(1) or m.group(2)) for m in fn_re.finditer(src)]
    starts.append((len(src), None))
    generators, wired = [], []
    for i in range(len(starts) - 1):
        a, name = starts[i]
        b = starts[i + 1][0]
        body = src[a:b]
        if "/build/autopick" not in body:
            continue
        if not re.search(r"build\.powers\s*=", body):
            continue                      # preview-only surfaces don't generate
        generators.append(name)
        if "preselectStandardAccolades" in body:
            wired.append(name)
    print(f"  build generators found: {generators}")
    print(f"  preselect wired in    : {wired}")
    missing = [g for g in generators if g not in wired]
    if missing:
        fails.append(f"generation paths WITHOUT the accolade preselect: "
                     f"{missing} — walk-2 defect 2 (entry-point class)")
    if not generators:
        fails.append("no generators detected — the check cannot state its "
                     "denominator, so it must not pass")


def check_no_cached_failure():
    """WALK-3 ROOT CAUSE: loadAccolades() cached a FAILED fetch as [] — truthy,
    so `if (ACCOLADES_ROWS) return` handed back the empty roster forever with no
    retry, and every accolade feature silently no-opped while the server was
    healthy. Joel hit it because a 5080 restart failed the single fetch his page
    made. PIN: the cache may only be assigned from a SUCCESSFUL response, and
    the guard must distinguish "never loaded" (null) from "loaded" (an array)."""
    src = open(APP, encoding="utf-8").read()
    m = re.search(r"async function loadAccolades\(\)\s*\{(.*?)\n\}", src, re.S)
    if not m:
        fails.append("loadAccolades() not found")
        return
    body = m.group(1)
    ok_guard = "ACCOLADES_ROWS !== null" in body
    # the poison pattern: caching the result of a failure-tolerant ternary
    poisoned = re.search(r"ACCOLADES_ROWS\s*=\s*\([^)]*\)\s*\?[^:]*:\s*\[\]", body)
    print(f"  guard distinguishes never-loaded from loaded: "
          f"{'OK' if ok_guard else 'NO — a failure will be cached'}")
    print(f"  caches only a successful response: "
          f"{'NO — poison ternary present' if poisoned else 'OK'}")
    if not ok_guard:
        fails.append("loadAccolades guard must test `!== null`, or a failed "
                     "fetch caches [] forever (walk-3 root cause)")
    if poisoned:
        fails.append("loadAccolades assigns the cache from a failure-tolerant "
                     "ternary — a failed fetch poisons it permanently")


def check_reset_clears_accolades():
    """The stale-state family, third sighting: ACCOLADES_CHECKED is module-level,
    so without an explicit clear it leaks across characters (tick on one, start
    another, inherit its ticks) — exactly the custom-targets contamination
    shape. PIN: resetBuildScopedState must clear it."""
    src = open(APP, encoding="utf-8").read()
    m = re.search(r"function resetBuildScopedState\(\)\s*\{(.*?)\n\}", src, re.S)
    if not m:
        fails.append("resetBuildScopedState() not found")
        return
    ok = "ACCOLADES_CHECKED.clear()" in m.group(1)
    print(f"  reset clears the accolade ticks: {'OK' if ok else 'NO — they leak'}")
    if not ok:
        fails.append("resetBuildScopedState must clear ACCOLADES_CHECKED — "
                     "accolade ticks are per-character and this Set is "
                     "module-level (stale-state family)")


print("WALK-2 DEFECT PINS")
print("\ndefect 1 — card-bottom strip visible on every card:")
check_band()
print("\ndefect 2 — accolade preselect on EVERY level-50 generation path:")
check_generators()

print("\nwalk-3 — a failed accolade fetch must never poison the cache:")
check_no_cached_failure()
print("\nstale-state — reset must clear the accolade ticks:")
check_reset_clears_accolades()

print()
if fails:
    for f in fails:
        print(f"FAIL: {f}")
    sys.exit(1)
print("all walk-2 + walk-3 pins PASS")
