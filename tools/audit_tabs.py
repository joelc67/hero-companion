"""Tab-shell audit (tabbed-layout-spec.md step 7).

Checks, each with its denominator and a negative control:
  1. No duplicate ids in index.html.
  2. Tab wiring: the 5 expected tabs exist as button+panel pairs, every
     aria-controls resolves, every data-tab reference names a real tab.
  3. Every literal id referenced by app.js resolves to index.html or to
     markup app.js itself creates. A scanner that finds too few references
     FAILS (a broken regex must never bless the file).
  4. Every showTab("x") literal in app.js names a real tab key.

Exit 0 only when every check passes AND every negative control fails as
designed. tour.js is deliberately NOT audited here — audit_tour owns it and
is expected red until the tour is rebuilt against the tabbed shell.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

# The spec's information architecture is the independent denominator: these
# four tabs, no more, no fewer. (Was five: the End Game tab was retired
# 2026-08-04 — Joel's ruling — and its surfaces moved into Powers & Slots.)
EXPECTED_TABS = ["powers", "stats", "leveling", "logging"]

# app.js references at least this many distinct ids today (measured 2026-08-03).
# If the scanner ever reports fewer, the scanner broke — fail, don't bless.
MIN_REFERENCED_IDS = 80

FAILS = []


def check(ok, label):
    print(("  OK  " if ok else "  FAIL") + " " + label)
    if not ok:
        FAILS.append(label)


def html_ids(html):
    return re.findall(r'\bid="([^"]+)"', html)


def js_literal_ids(js):
    """ids referenced by app.js through literal lookups only."""
    refs = set()
    refs.update(re.findall(r'\$\(\s*"([\w-]+)"\s*\)', js))
    refs.update(re.findall(r'getElementById\(\s*"([\w-]+)"\s*\)', js))
    for sel in re.findall(r'querySelector(?:All)?\(\s*"([^"]+)"\s*\)', js):
        refs.update(re.findall(r"#([\w-]+)", sel))
    return refs


def js_created_ids(js):
    """ids app.js creates in its own markup strings (both quote styles and
    the escaped form inside double-quoted JS strings)."""
    made = set(re.findall(r'id=\\?"([\w-]+)\\?"', js))
    made.update(re.findall(r"id='([\w-]+)'", js))
    made.update(re.findall(r'\.id\s*=\s*"([\w-]+)"', js))
    return made


def run(html, js):
    """Run every check against the given sources; returns list of failures."""
    global FAILS
    FAILS = []
    ids = html_ids(html)
    id_set = set(ids)

    # 1. duplicates
    dups = sorted({i for i in ids if ids.count(i) > 1})
    print(f"[1] duplicate ids — {len(ids)} ids checked")
    check(not dups, f"no duplicate ids (dups: {dups[:5]})")

    # 2. tab wiring
    btns = dict(re.findall(r'<button[^>]*\bid="tab-btn-([\w-]+)"[^>]*aria-controls="([\w-]+)"', html))
    panels = re.findall(r'<section\s+id="tab-([\w-]+)"\s+class="tabpanel"', html)
    datatabs = set(re.findall(r'data-tab="([\w-]+)"', html))
    print(f"[2] tab wiring — {len(EXPECTED_TABS)} expected tabs, "
          f"{len(btns)} buttons / {len(panels)} panels / {len(datatabs)} data-tab refs found")
    check(sorted(btns) == sorted(EXPECTED_TABS), f"tab buttons are exactly {EXPECTED_TABS}")
    check(sorted(panels) == sorted(EXPECTED_TABS), f"tab panels are exactly {EXPECTED_TABS}")
    check(all(v == f"tab-{k}" and v in id_set for k, v in btns.items()),
          "every aria-controls points at its own existing panel")
    bad_dt = sorted(datatabs - set(EXPECTED_TABS))
    check(not bad_dt, f"every data-tab names a real tab (bad: {bad_dt})")

    # 3. app.js id references resolve
    refs = js_literal_ids(js)
    known = id_set | js_created_ids(js)
    missing = sorted(r for r in refs if r not in known)
    print(f"[3] id references — {len(refs)} distinct literal ids referenced by app.js")
    check(len(refs) >= MIN_REFERENCED_IDS,
          f"scanner found >= {MIN_REFERENCED_IDS} references (found {len(refs)}; fewer = broken scanner)")
    check(not missing, f"all referenced ids exist in index.html or app.js markup (missing: {missing[:8]})")

    # 4. showTab targets
    st = set(re.findall(r'''showTab\(\s*["']([\w-]+)["']''', js)) | \
         set(re.findall(r'''showTab\(&quot;([\w-]+)&quot;''', html)) | \
         set(re.findall(r'''showTab\(\\?['"]([\w-]+)\\?['"]''', html))
    bad_st = sorted(st - set(EXPECTED_TABS))
    print(f"[4] showTab targets — {len(st)} distinct targets found")
    check(len(st) > 0, "showTab scanner found targets (zero = broken scanner)")
    check(not bad_st, f"every showTab target is a real tab (bad: {bad_st})")

    return list(FAILS)


def negative_controls():
    """Each defect class, injected, must FAIL. A checker that can't see the
    planted defect is lying about the real file."""
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    import io
    from contextlib import redirect_stdout
    cases = [
        ("duplicate id", html + '<div id="masthead"></div>', js),
        ("missing referenced id", html, js + '\ngetElementById("zz-negative-control");'),
        ("data-tab to nowhere", html + '<button data-tab="zz-nowhere"></button>', js),
        ("showTab to nowhere", html, js + '\nshowTab("zz-nowhere");'),
    ]
    all_ok = True
    for label, h, j in cases:
        with redirect_stdout(io.StringIO()):
            fails = run(h, j)
        caught = bool(fails)
        print(("  OK  " if caught else "  FAIL") + f" negative control caught: {label}")
        all_ok &= caught
    return all_ok


def main():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    fails = run(html, js)
    print("[5] negative controls — 4 planted defects must each fail")
    neg_ok = negative_controls()
    n_checks = 10
    passed = n_checks - len(fails)
    print(f"\naudit_tabs: {passed} of {n_checks} checks passed; negative controls "
          + ("OK" if neg_ok else "FAILED"))
    if fails or not neg_ok:
        sys.exit(1)
    print("audit_tabs: PASS")


if __name__ == "__main__":
    main()
