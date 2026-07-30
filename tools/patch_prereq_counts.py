"""Additive patcher: per-power PREREQUISITE COUNTS, from the game's own words.

WHY (2026-07-29): our model derived a power's prerequisite count from its
POSITION in the set (first two free, third needs 1, top tiers need 2). The
game states the count per power in its own help text, and the two disagree on
24 of 413 checked powers — in BOTH directions (we over-require travel powers
the game gates freely; we under-require Weave-class tier-4s). See
tools/reality_check_prereqs.py for the census.

THE RULE THIS PATCHER FOLLOWS (learned the expensive way the same morning):
patch ONLY where TWO independent client signals agree.
  signal A  the help sentence: "have [trained any] N other X Powers"
  signal B  the requires expression's EXISTENCE (empty = the game gates
            nothing; non-empty = a real gate exists)
  agree  ⇒  A empty & B empty -> 0   |   A says N>0 & B non-empty -> N
  differ ⇒  HOLD (no key written; the tier model keeps handling it) and REPORT
Powers whose help sentence names a DIFFERENT power ("before selecting Victory
Rush") are HELD regardless — that is evidence about the text, not the rule.

Writes `prereq_count` on Pool./Epic. records. Additive, idempotent,
binary-preserving, strip-verified. server._epic_prereq_count prefers it.

Run:  py tools\\patch_prereq_counts.py [--write]
"""
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv  # the ONE tier authority
POWERS = os.path.join(ROOT, "data", "powers.json")
OUT_FULL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")

_WORDNUM = {"no": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
_RE_NEED = re.compile(
    r"have\s+(?:trained\s+)?(?:any\s+)?(\w+)\s+other\s+(.{0,60}?)\s*Powers?\b",
    re.I | re.S)
_RE_NAMED = re.compile(r"before (?:selecting|you can train) ([A-Za-z' \-]+)")


def _wordset(ps):
    return frozenset(ps.lower().split("_"))


def client_index():
    idx, by_words = {}, {}
    for f in glob.glob(os.path.join(OUT_FULL, "pool", "*", "*.json")) + \
             glob.glob(os.path.join(OUT_FULL, "epic", "*", "*.json")):
        if os.path.basename(f) == "index.json":
            continue
        try:
            rec = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        fn = rec.get("full_name")
        if not fn:
            continue
        idx[fn] = rec
        cat, ps, pw = fn.split(".", 2)
        by_words.setdefault((cat.lower(), _wordset(ps), pw.lower()), []).append(fn)
    return idx, by_words


def stated(rec, own_name):
    """(count, reason) — the count both signals support, or (None, why not).

    ⚠ signal B is "does the expression reference other POWERS", NOT "is it
    non-empty": most epic expressions are ARCHETYPE gates
    (`$archetype @Class_Scrapper ==`) and say nothing about prerequisites.
    Asking the wrong question of the data is how this whole morning went
    wrong; the question is now written down."""
    help_ = (rec.get("display_help") or "").replace("<br>", " ")
    raw_req = (rec.get("requires") or "").strip()
    reqs = " ".join(t for t in raw_req.split() if t.count(".") == 2)
    m = _RE_NEED.search(help_)
    named = _RE_NAMED.search(help_)
    if named:
        who = named.group(1).strip().lower()
        if who not in ("this power",) and who != own_name.lower():
            return None, f"sentence names '{named.group(1).strip()}'"
    if not m:
        if reqs:
            return None, "help states no count but a power-gate exists"
        return 0, "help+expression: no gate"
    n = _WORDNUM.get(m.group(1).lower())
    if n is None:
        return None, f"unparsed quantity '{m.group(1)}'"
    if n > 0 and reqs:
        return n, f"help+expression: {n}"
    # No power tokens in the expression — normal for EPIC sets, whose gating
    # the client carries structurally rather than as an expression. Single
    # signal, so it only stands when our existing model already agrees
    # (caller supplies that); otherwise HOLD. Never change a rule on one
    # source (2026-07-29).
    return (n, "help only — needs model corroboration")


def main(write=False):
    raw = open(POWERS, "rb").read()
    data = json.loads(raw)
    idx, by_words = client_index()

    # PRIMARY SIGNAL (2026-07-30, Joel: "check the game, make no assumptions").
    # The client states each prerequisite as an executable boolean expression
    # over named powers; tools/prereq_from_requires.py evaluates it for the
    # minimum satisfying count. That is the rule the game runs, so it outranks
    # the help PROSE (a player-facing summary, which disagrees with the
    # expression for 4 of 488) and outranks our tier proxy entirely. Only
    # "exact" counts are used -- ones that hold whether eligibility gates pass
    # or fail. Prose+model stays the fallback where no expression exists.
    expr = {}
    p_expr = os.path.join(ROOT, "tools", "prereq_counts_from_requires.json")
    if os.path.exists(p_expr):
        expr = {k: v for k, v in json.load(open(p_expr, encoding="utf-8")).items()
                if v.get("status") == "exact"}
        print(f"expression counts loaded: {len(expr)} powers (the game's own rule)")
    else:
        print("⚠ no expression counts on disk — run "
              "tools/prereq_from_requires.py --json first; falling back to prose")

    expected = patched = changed = 0
    from_expr = 0
    changes = []
    held, unmatched = [], []
    for ps, lst in sorted(data.items()):
        if not (ps.startswith("Pool.") or ps.startswith("Epic.")):
            continue
        for p in lst:
            fn = p.get("full_name")
            expected += 1
            rec = idx.get(fn)
            if rec is None:
                cat, psn, pw = fn.split(".", 2)
                cands = by_words.get((cat.lower(), _wordset(psn), pw.lower()), [])
                results = {stated(idx[c], pw)[0] for c in cands}
                if len(cands) >= 1 and len(results) == 1:
                    rec = idx[cands[0]]
                else:
                    unmatched.append(fn)
                    continue
            ex = expr.get(rec.get("full_name") or fn)
            if ex is not None:
                n = ex["needs"]
                patched += 1
                from_expr += 1
                if p.get("prereq_count") != n:
                    changes.append((fn, p.get("prereq_count"), n,
                                    ex.get("display_name")))
                    p["prereq_count"] = n
                    changed += 1
                continue
            n, why = stated(rec, fn.rsplit(".", 1)[-1].replace("_", " "))
            if n is None:
                held.append((fn, why))
                continue
            if why.startswith("help only"):
                # third signal: our existing tier model. Agreement = two
                # sources; disagreement = an open question for Joel, held.
                ours = srv._epic_prereq_count(srv._pool_tiers(ps).get(fn, 0))
                if ours != n:
                    held.append((fn, f"help says {n}, our model says {ours}, "
                                     f"no expression to break the tie"))
                    continue
                why = f"help+model: {n}"
            patched += 1
            if p.get("prereq_count") != n:
                p["prereq_count"] = n
                changed += 1

    print(f"{patched} of {expected} Pool/Epic powers patched from the game's "
          f"own words ({from_expr} from the requires EXPRESSION, "
          f"{patched - from_expr} from prose+model; {changed} changed this run)")
    for fn, was, now, disp in changes:
        print(f"    CHANGE {fn} [{disp}]: {was} -> {now}")
    print(f"  HELD (signals disagree or text is about another power): {len(held)}")
    for fn, why in held:
        print(f"    {fn}: {why}")
    print(f"  unmatched in the client export: {len(unmatched)}")
    if patched < 0.8 * expected:
        print("HARD FAIL: coverage below 80% — not writing.")
        sys.exit(1)
    if not write:
        print("(report only — rerun with --write to apply)")
        return
    out = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    check, orig = json.loads(out), json.loads(raw)
    for d in (check, orig):
        for _ps, lst in d.items():
            for p in lst:
                p.pop("prereq_count", None)
    if check != orig:
        print("HARD FAIL: strip-verify mismatch — not writing.")
        sys.exit(1)
    with open(POWERS, "wb") as f:
        f.write(out)
    print(f"written: {POWERS}")


if __name__ == "__main__":
    main(write="--write" in sys.argv)
