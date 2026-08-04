"""TOUR ACCURACY AUDIT — the thing that keeps the guided tour honest.

The tour explains the app by pointing at real controls. That is only useful while
the controls still exist, and a stale tour is worse than none: it teaches an
interface the user cannot find. Documentation rots silently; this makes it rot
LOUDLY, in the same run that renamed the control.

Checks, all with a stated denominator:
  1. every step's target resolves to an id that exists in index.html or is
     created by app.js
  2. every chapter named by a step is declared in TOUR_CHAPTERS
  3. every declared chapter is reachable (has at least one step)
  4. the short first-run tour (spine) covers every chapter, so nobody meets the
     app through a tour that skips a whole area

Run after ANY change to tour.js, index.html ids, or panel structure.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOUR = ROOT / "static" / "tour.js"
HTML = ROOT / "static" / "index.html"
APPJS = ROOT / "static" / "app.js"

fails = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if detail:
        print(f"        {detail}")
    if not ok:
        fails.append(name)


tour = TOUR.read_text(encoding="utf-8")
html = HTML.read_text(encoding="utf-8")
appjs = APPJS.read_text(encoding="utf-8")

# 0. the file actually PARSES. Every regex check below reads text, not syntax --
# on 2026-07-27 this audit reported ALL PASS on a tour.js that had stopped
# parsing entirely. A file that does not parse has zero working steps.
try:
    _syn = subprocess.run(["node", "--check", str(TOUR)],
                          capture_output=True, text=True, timeout=30)
    syn_ok, syn_detail = _syn.returncode == 0, (_syn.stderr or "").strip()
except FileNotFoundError:
    syn_ok, syn_detail = False, "node not found on PATH -- syntax cannot be verified, refusing to pass"
print()
check("tour.js parses as JavaScript (node --check)", syn_ok, syn_detail if not syn_ok else "")
if not syn_ok:
    print("\nTOUR AUDIT FAILURES: file does not parse; remaining checks are meaningless\n")
    sys.exit(1)

# ids that exist in the static page
static_ids = set(re.findall(r'id="([A-Za-z0-9_-]+)"', html))
# ids app.js creates at runtime (el.id = "x", id="x" inside a template literal)
dynamic_ids = set(re.findall(r'\.id\s*=\s*"([A-Za-z0-9_-]+)"', appjs))
dynamic_ids |= set(re.findall(r'id="([A-Za-z0-9_-]+)"', appjs))
known = static_ids | dynamic_ids

steps = re.findall(r'\{\s*chapter:\s*"([a-z]+)",\s*target:\s*"([^"]+)"', tour)
# Scope this to the TOUR_CHAPTERS block. A bare indent-anchored regex also matched
# the keys of any other 2-space-indented object literal in the file (chapter:,
# title:, body:...), which invented four phantom chapters.
_chap_block = re.search(r"const TOUR_CHAPTERS\s*=\s*\{(.*?)\n\};", tour, re.S)
chapters_declared = set(re.findall(r'^\s*([a-z]+):\s*"', _chap_block.group(1), re.M)) \
    if _chap_block else set()
spine_blocks = re.findall(r'chapter:\s*"([a-z]+)",\s*target:\s*"[^"]+",\s*spine:\s*true', tour)

print(f"\ntour audit — {len(steps)} steps, {len(chapters_declared)} chapters declared\n")

# 1. targets resolve
missing = []
for _ch, target in steps:
    ident = target.lstrip("#")
    if not target.startswith("#"):
        missing.append(f"{target} (only id selectors are checkable)")
    elif ident not in known:
        missing.append(target)
check(f"every step target exists ({len(steps) - len(missing)} of {len(steps)} resolve)",
      not missing,
      ("STALE: " + ", ".join(sorted(set(missing)))) if missing else "")

# 1b. every step target has a stand-in on the tour's mock screen. The tour
# highlights the MOCK (data-for="<real id>"), so a target the app has but the
# mock lacks would render a card pointing at nothing.
mock_for = set(re.findall(r'data-for="([A-Za-z0-9_-]+)"', tour))
unmocked = sorted({t.lstrip("#") for _c, t in steps} - mock_for)
check(f"every step target has a mock stand-in ({len(steps) - len(unmocked)} of {len(steps)})",
      not unmocked,
      ("no data-for in the mock: " + ", ".join(unmocked)) if unmocked else "")

# 1b2. every step anchor exists in the mock. Anchors are "[data-tm=x]" BY
# CONVENTION so this stays auditable; any other shape fails here rather than
# silently escaping the check.
anchor_raw = re.findall(r'anchor:\s*"([^"]+)"', tour)
anchor_tms = [m.group(1) for a in anchor_raw
              for m in [re.fullmatch(r"\[data-tm=([a-z0-9-]+)\]", a)] if m]
tm_defined = set(re.findall(r'data-tm="([a-z0-9-]+)"', tour))
bad_shape = [a for a in anchor_raw if not re.fullmatch(r"\[data-tm=[a-z0-9-]+\]", a)]
bad_tm = sorted(set(anchor_tms) - tm_defined)
check(f"every step anchor exists in the mock ({len(anchor_raw)} anchors)",
      not bad_shape and not bad_tm,
      (("not [data-tm=...] shaped: " + ", ".join(bad_shape) + "  ") if bad_shape else "")
      + (("missing from mock: " + ", ".join(bad_tm)) if bad_tm else ""))

# 1c. every deep link in the app resolves. A ? placed ON a control calls
# explainStep('<key>'); the key must belong to exactly one step or the click
# lands on the generic chooser instead of the promised explanation.
keys = re.findall(r'key:\s*"([a-z0-9-]+)"', tour)
links = set(re.findall(r"explainStep\('([a-z0-9-]+)'", html + appjs))
dup_keys = sorted({k for k in keys if keys.count(k) > 1})
dead_links = sorted(links - set(keys))
check(f"every deep link resolves to a unique step key ({len(links)} links, {len(keys)} keys)",
      not dead_links and not dup_keys,
      (("dead links: " + ", ".join(dead_links) + "  ") if dead_links else "")
      + (("duplicate keys: " + ", ".join(dup_keys)) if dup_keys else ""))

# 2. chapters used are declared
used = {c for c, _t in steps}
undeclared = used - chapters_declared
check(f"every chapter used is declared ({len(used)} used)",
      not undeclared,
      ("undeclared: " + ", ".join(sorted(undeclared))) if undeclared else "")

# 3. declared chapters are reachable
unreachable = chapters_declared - used
check(f"every declared chapter has steps ({len(chapters_declared)} declared)",
      not unreachable,
      ("no steps: " + ", ".join(sorted(unreachable))) if unreachable else "")

# 4. the short tour touches every area
spine_missing = used - set(spine_blocks)
check(f"the first-run tour covers every chapter ({len(set(spine_blocks))} of {len(used)})",
      not spine_missing,
      ("not in the short tour: " + ", ".join(sorted(spine_missing))) if spine_missing else "")

# 5. every CSS variable the tour styles use is actually DEFINED.
# This one exists because of a real failure (2026-07-27): the tour card used
# var(--fg) and var(--line), which this app has never defined -- the real names
# are --ink and --border. CSS falls back silently, so the card rendered near-
# black text on a dark navy panel and looked completely blank. Nothing errored,
# nothing logged; it just could not be read. An undefined variable in a themed
# app is a bug, so it fails here now.
css = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
marker = "/* ── Guided tour"
if marker not in css:
    check("tour style block present", False, "could not find the guided-tour CSS block")
else:
    defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", css))
    block = css[css.index(marker):]
    # --h* are set from JS at runtime (the spotlight rect), so they are expected
    # to be absent from the stylesheet. A var USED WITH A FALLBACK cannot
    # "render invisible" either — var(--chrome-h, 130px) degrades visibly —
    # so only fallback-less uses are held to the defined-in-stylesheet rule.
    used_vars = {v for v in re.findall(r"var\((--[a-z0-9-]+)\)", block)
                 if not v.startswith("--h")}
    undefined = sorted(used_vars - defined)
    check(f"every themed colour the tour uses is defined ({len(used_vars)} used)",
          not undefined,
          ("UNDEFINED, will fall back silently and may render invisible: "
           + ", ".join(undefined)) if undefined else "")


# -- 9. DIAGRAM GEOMETRY: a label must not be drawn underneath a control.
# WHY: the powerCard diagram drew the power name from x=134 while the info button
# sat at cx=196 r=7 (left edge 189), so 'Fire Blast' - 58.5px wide at 14px - was
# rendered UNDER the i button. Joel saw it on screen (2026-08-02). Every other
# check in this file passed throughout, because none of them look at POSITION.
#
# Width is estimated at 0.42 x font-size per char, calibrated against the real
# browser measurement (measured 58.5px, predicted 58.8).
#
# !! THIS CHECK CARRIES ITS OWN NEGATIVE CONTROL. A first version of it silently
# failed to fire on the very bug it was written for, and reported PASS - which is
# worse than no check at all. It now runs against a known-bad fixture first and
# hard-fails if it cannot see that, so it can never again pass by being blind.
_TXT_RE = re.compile('<text[^>]*x="([0-9.]+)"[^>]*class="([^"]*)"[^>]*>([^<]*)</text>')
_CTL_RE = re.compile('<circle[^>]*cx="([0-9.]+)"[^>]*r="([0-9.]+)"[^>]*class="([^"]*)"')


def _label_overlaps(body):
    """[(label, right_edge, control_left)] for every start-anchored d-name that
    runs into a control circle."""
    ctls = [(float(cx), float(r)) for cx, r, cls in _CTL_RE.findall(body)
            if 'd-ctl' in cls]
    hits = []
    for x, cls, txt in _TXT_RE.findall(body):
        if 'd-name' not in cls or 'd-end' in cls or 'd-mid' in cls:
            continue
        x = float(x)
        right = x + len(txt.strip()) * 14 * 0.42
        for cx, r in ctls:
            if x < cx - r < right:
                hits.append((txt.strip(), round(right), round(cx - r)))
    return hits


_BAD_FIXTURE = ('<text x="134" y="77" class="d-name">Fire Blast</text>'
                '<circle cx="196" cy="72" r="7" class="d-ctl d-hot"/>')
if not _label_overlaps(_BAD_FIXTURE):
    check('geometry check can detect a known overlap (negative control)', False,
          'THE CHECK IS BLIND - it would report PASS on the exact defect it exists for')
else:
    check('geometry check can detect a known overlap (negative control)', True,
          'fixture flagged as expected')
    geom_fails = []
    _diagrams = re.findall(r'^  (\w+): `([\s\S]*?)`,', tour, re.M)
    for _dname, _body in _diagrams:
        for _txt, _right, _left in _label_overlaps(_body):
            geom_fails.append(_dname + ": '" + _txt + "' reaches x=" + str(_right)
                              + ' but a control starts at x=' + str(_left))
    check('no diagram label is drawn under a control (' + str(len(_diagrams)) + ' diagrams)',
          not geom_fails, '; '.join(geom_fails) if geom_fails else '')

print(f"\n{'ALL TOUR CHECKS PASS' if not fails else 'TOUR AUDIT FAILURES: ' + ', '.join(fails)}\n")
sys.exit(1 if fails else 0)
