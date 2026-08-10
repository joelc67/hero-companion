"""Battery for the searchable help (2026-08-10): content structure + wiring.

Every topic must answer all four of Joel's questions (what / how / why / where),
sit in a named workflow stage, and every 'go' action must resolve to a REAL tab
or a REAL tour deep-link key - a help button that goes nowhere teaches distrust.
Checker proven against sabotaged copies, per the standing pattern.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGES = {"building", "updating", "tweaking", "manual", "reference"}

n = 0
def ok(cond, msg):
    global n
    n += 1
    assert cond, f"check {n} FAILED: {msg}"
    print(f"  {n}. ok - {msg}")


def problems(data, tab_ids, tour_keys):
    """Structural faults in a help_topics dict. Pure, so sabotages can drive it."""
    out = []
    for k in ("building", "updating", "tweaking", "manual"):
        if not (data.get("workflows") or {}).get(k):
            out.append(f"workflow text missing: {k}")
    if len(data.get("loop") or []) != 4:
        out.append("the loop must be exactly the four steps")
    seen = set()
    for t in data.get("topics") or []:
        name = t.get("term") or "?"
        if name.lower() in seen:
            out.append(f"duplicate term: {name}")
        seen.add(name.lower())
        for f in ("what", "how", "why", "where"):
            if not (t.get(f) or "").strip():
                out.append(f"{name}: '{f}' is empty - all four questions must be answered")
        if t.get("stage") not in STAGES:
            out.append(f"{name}: unknown stage {t.get('stage')!r}")
        for pair in t.get("go") or []:
            if len(pair) != 2:
                out.append(f"{name}: malformed go entry {pair!r}")
                continue
            action = pair[0]
            kind, _, arg = action.partition(":")
            if kind == "tab" and arg not in tab_ids:
                out.append(f"{name}: go tab '{arg}' is not a real tab")
            elif kind == "tour" and arg not in tour_keys:
                out.append(f"{name}: go tour key '{arg}' is not a tour deep link")
            elif kind not in ("tab", "tour"):
                out.append(f"{name}: unknown action kind '{kind}'")
    return out


def main():
    data = json.load(open(os.path.join(ROOT, "static", "help_topics.json"),
                          encoding="utf-8"))
    idx = open(os.path.join(ROOT, "static", "index.html"), encoding="utf-8").read()
    appjs = open(os.path.join(ROOT, "static", "app.js"), encoding="utf-8").read()
    tour = open(os.path.join(ROOT, "static", "tour.js"), encoding="utf-8").read()

    tab_ids = set(re.findall(r'id="tab-([a-z]+)"', idx))
    tour_keys = set(re.findall(r'key:\s*["\']([a-z0-9-]+)["\']', tour))
    ok(tab_ids >= {"powers", "stats", "leveling", "logging"},
       f"the four tabs exist in index.html ({sorted(tab_ids)})")

    faults = problems(data, tab_ids, tour_keys)
    ok(not faults, f"{len(data['topics'])} topics structurally clean: "
       + ("; ".join(faults[:5]) or "no faults"))
    ok(len(data["topics"]) >= 35,
       f"{len(data['topics'])} of >=35 expected topics present (coverage denominator)")

    # wiring: the modal, the menu item, and the module all exist and connect
    for el in ("help-search-btn", "help-search-modal", "help-search-input",
               "help-search-out", "help-search-close"):
        ok(f'id="{el}"' in idx, f"index.html carries #{el}")
    ok("initHelpSearch()" in appjs and "function initHelpSearch" in appjs,
       "app.js defines AND calls initHelpSearch")
    ok('fetch("/static/help_topics.json")' in appjs,
       "app.js fetches the exact content file this battery validated")
    ok("escHtml(t.what)" in appjs and "escHtml(t.how)" in appjs,
       "topic bodies render through escHtml (attribute-safety rule)")

    # sabotages: the checker must catch each fault class it claims to
    import copy
    s1 = copy.deepcopy(data); s1["topics"][0]["why"] = ""
    ok(any("'why' is empty" in p for p in problems(s1, tab_ids, tour_keys)),
       "SABOTAGE caught: an empty 'why' field fails")
    s2 = copy.deepcopy(data); s2["topics"][0]["go"] = [["tab:nosuchtab", "x"]]
    ok(any("not a real tab" in p for p in problems(s2, tab_ids, tour_keys)),
       "SABOTAGE caught: a go-action to a nonexistent tab fails")
    s3 = copy.deepcopy(data); s3["topics"][1]["go"] = [["tour:no-such-key", "x"]]
    ok(any("not a tour deep link" in p for p in problems(s3, tab_ids, tour_keys)),
       "SABOTAGE caught: a dead tour deep link fails")
    s4 = copy.deepcopy(data); s4["topics"].append(dict(s4["topics"][0]))
    ok(any("duplicate term" in p for p in problems(s4, tab_ids, tour_keys)),
       "SABOTAGE caught: a duplicate term fails")

    print(f"help-search battery: {n}/{n} OK")


if __name__ == "__main__":
    sys.exit(main() or 0)
