"""PREREQ COUNT FROM THE GAME'S OWN REQUIRES EXPRESSION.

WHY THIS EXISTS (2026-07-30, Joel: "check the game, learn what is accurate,
make no assumptions"). We have guessed the pool/epic prerequisite count three
ways and been wrong twice:

  1. A position-based TIER PROXY (how far down the set a power sits). Wrong in
     both directions.
  2. Parsing the prerequisite SENTENCE out of display_help. Better, but prose
     is fragile: Field Medic's help has no prereq sentence at all, so the
     scraper matched a DESCRIPTION sentence and read "2" out of narrative text
     by luck. It also produced six false "the sentence names a different
     power" alarms -- which were never misattribution at all, but our INTERNAL
     name vs the game's DISPLAY name (Pool.Leaping.Leap IS "Acrobatics";
     Pool.Teleportation.Long_Range_Teleport IS "Fold Space";
     Pool.Leadership.Defense IS "Maneuvers").
  3. One catastrophic over-read of this very field, which called ~20 shipping
     champions illegal and burned a 12-hour wave (reverted, 00ed2a39).

The lesson of #3 was NOT "never read requires" -- it was "do not INFER a rule
from it." This does not infer. The client states each prerequisite as a
boolean expression over NAMED POWERS, in postfix, using three idioms:

  enumerated subsets  Boxing Kick && Boxing Tough && || Kick Tough && ||
                      -> any TWO of {Boxing, Kick, Tough}          (Weave)
  additive            Weaken_Resolve Project_Will + Mighty_Leap + 1 >
                      -> sum of owned > 1, i.e. at least TWO
  the game's own      Epic ownPowerNum? 1 >
  count operator      -> more than 1 owned in the set, i.e. at least TWO

So the count is not read, guessed, or scraped -- it is MEASURED by evaluating
the expression: the minimum number of other same-set powers that satisfies it.

Non-power gates (archetype eligibility `$archetype @Class_Brute ==`, patron
unlocks `SpidersKissPatron Owned?`, `accesslevel char> 0 >=`) are NOT power
prerequisites. They answer "may this character take this set at all", a
different question, and are evaluated as satisfied here. ownPowerNum?'s
category argument is likewise a set reference, not a power.

Run:  py tools\\prereq_from_requires.py            # validate + full report
      py tools\\prereq_from_requires.py --json     # machine-readable counts
"""
import glob
import json
import os
import re
import sys
from itertools import combinations

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_FULL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")

_BOOLOPS = {"&&", "||"}
_CMP = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
        "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
        "!=": lambda a, b: a != b}
# UNARY operators, learned from the client's own expressions. Getting these
# wrong is not a rounding error -- mistyping `char>` as an operand corrupted
# the stack arity and made "any two of three" evaluate as "needs none".
_UNARY = {"!", "Owned?", "char>", "ownPowerNum?"}
# A power reference is Category.Set.Power -- NOT just Pool./Epic. Fitness
# Stamina gates on `Inherent.Fitness.Stamina !`, and typing that as a gate
# made the expression unsatisfiable at any count.
_POWERREF = re.compile(r"^[A-Z][A-Za-z_]*\.[A-Za-z_0-9]+\.[A-Za-z_0-9]+$")


def evaluate(expr, owned, gate):
    """Is `expr` satisfied holding exactly `owned`, with non-power gates = `gate`?

    `gate` is the truth value given to things that are NOT power prerequisites:
    archetype eligibility, patron unlocks, beta flags, accesslevel. Those answer
    "may this character take this set at all", a different question. We never
    guess which way they fall -- the caller evaluates BOTH polarities and only
    reports a count when they agree.
    """
    g = 1 if gate else 0
    st = []
    for t in expr.split():
        if _POWERREF.match(t):
            st.append(1 if t in owned else 0)
        elif t in _BOOLOPS:
            b = st.pop() if st else 0
            a = st.pop() if st else 0
            st.append(1 if ((a and b) if t == "&&" else (a or b)) else 0)
        elif t == "!":
            st.append(0 if (st.pop() if st else 0) else 1)
        elif t == "Owned?":
            if st:
                st.pop()
            st.append(g)
        elif t == "char>":
            if st:
                st.pop()
            st.append(g)
        elif t == "ownPowerNum?":
            if st:
                st.pop()                      # the category argument
            st.append(len(owned))
        elif t == "+":
            b = st.pop() if st else 0
            a = st.pop() if st else 0
            st.append(a + b)
        elif t in _CMP:
            b = st.pop() if st else 0
            a = st.pop() if st else 0
            st.append(1 if _CMP[t](a, b) else 0)
        elif t == "==":
            b = st.pop() if st else 0
            a = st.pop() if st else 0
            # archetype/patron identity -- eligibility, not a power prereq
            st.append(g if (a == g or b == g or True) else 0)
        elif t.lstrip("-").isdigit():
            st.append(int(t))
        else:
            st.append(g)                      # a gate operand
    return bool(st[-1]) if st else True


def _min_for(expr, siblings, gate):
    for k in range(0, len(siblings) + 1):
        for combo in combinations(siblings, k):
            if evaluate(expr, set(combo), gate):
                return k
    return None


def min_others(expr, siblings):
    """Minimum count of OTHER same-set powers that satisfies expr.

    Returns (count, status): status is "exact" when the answer is the same
    whether eligibility gates pass or fail (so the power requirement stands on
    its own), "gate-dependent" when the two polarities disagree, and
    "unsatisfiable" when no subset of same-set powers works either way.
    """
    hi = _min_for(expr, siblings, True)       # gates pass
    lo = _min_for(expr, siblings, False)      # gates fail
    if hi is None and lo is None:
        return len(siblings), "unsatisfiable"
    if hi is not None and lo is not None and hi == lo:
        return hi, "exact"
    if hi is not None and lo is None:
        # only reachable when eligible -- the POWER count is still hi
        return hi, "exact"
    if lo is not None and hi is None:
        # ⚠ THE MIRROR CASE, and it is the same argument. A NEGATED archetype
        # gate ("$archtype @Class_Peacebringer == !") is satisfiable exactly
        # when the gate does NOT hold, so the polarities swap - but the
        # question being asked is unchanged: for every archetype that can take
        # the power at all, how many SIBLING POWERS does the game demand? That
        # answer is lo, and whether an archetype is barred outright is a
        # different axis (recorded as `archetype_excluded` on the record).
        # Found by Pool.Gadgetry.Jetpack, which the game bars from Kheldians;
        # without this it read "gate-dependent" and stopped the wave launcher.
        return lo, "exact"
    return (hi if hi is not None else lo), "gate-dependent"


def load_client():
    """{full_name: record} for every pool/epic power in the client export."""
    recs, index = {}, {}
    for f in (glob.glob(os.path.join(OUT_FULL, "pool", "*", "*.json"))
              + glob.glob(os.path.join(OUT_FULL, "epic", "*", "*.json"))):
        r = json.load(open(f, encoding="utf-8"))
        if os.path.basename(f) == "index.json":
            if r.get("key"):
                index[r["key"]] = r
            continue
        if r.get("full_name"):
            recs[r["full_name"]] = r
    return recs, index


def help_sentence(rec):
    """The prerequisite sentence the PLAYER is shown, if the help has one."""
    h = rec.get("display_help") or ""
    for s in re.split(r"<br>|(?<=\.)\s", h):
        low = s.lower()
        if "must" in low and "select" in low and "power" in low:
            return s.strip()
    return ""


_WORDNUM = {"no": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}


def help_count(sentence):
    """The count the player-facing sentence states, or None."""
    m = re.search(r"have\s+(\w+)\s+other", sentence or "", re.I)
    return _WORDNUM.get(m.group(1).lower()) if m else None


def main():
    recs, index = load_client()
    by_set = {}
    for fn in recs:
        by_set.setdefault(fn.rsplit(".", 1)[0], []).append(fn)

    rows, unresolved = [], []
    for fn, rec in sorted(recs.items()):
        expr = (rec.get("requires") or "").strip()
        setk = fn.rsplit(".", 1)[0]
        siblings = [s for s in by_set[setk] if s != fn]
        if not expr:
            rows.append((fn, rec, 0, "exact", ""))
            continue
        n, status = min_others(expr, siblings)
        rows.append((fn, rec, n, status, expr))
        if status != "exact":
            unresolved.append((fn, status, expr))

    # ---- VALIDATION FIRST: known truths, from the game's own help text ----
    # Each control is a power whose player-facing sentence states the count, so
    # the expression and the prose must agree. A control that fails means the
    # evaluator is wrong and nothing below it can be trusted.
    controls = {
        "Pool.Fighting.Tough": 1,               # "one other Fighting Powers"
        "Pool.Fighting.Weave": 2,               # "two other Fighting Powers"
        "Pool.Leadership.Tactics": 1,
        "Pool.Leadership.Vengeance": 2,
        "Pool.Force_of_Will.Unleash_Potential": 2,
        "Epic.Arctic_Mastery.Ice_Blast": 1,     # ownPowerNum? 0 >
        "Epic.Arctic_Mastery.Ice_Storm": 2,     # ownPowerNum? 1 >
    }
    got = {fn: n for fn, _r, n, _s, _x in rows}
    print("VALIDATION (evaluator vs the game's own stated counts):")
    bad = 0
    for fn, want in controls.items():
        have = got.get(fn)
        ok = have == want
        bad += 0 if ok else 1
        print(f"  {'PASS' if ok else 'FAIL'}  {fn:44} expected {want}, got {have}")
    if bad:
        print(f"\n{bad} CONTROL(S) FAILED — the evaluator is wrong; "
              "no counts below are trustworthy.")
        sys.exit(1)
    print(f"  all {len(controls)} controls pass\n")

    # ---- corroboration: expression vs the player-facing sentence ----
    agree = disagree = no_sentence = 0
    conflicts = []
    for fn, rec, n, _status, expr in rows:
        hc = help_count(help_sentence(rec))
        if hc is None:
            no_sentence += 1
        elif hc == n:
            agree += 1
        else:
            disagree += 1
            conflicts.append((fn, rec, n, hc, expr))

    print(f"COVERAGE: {len(rows)} pool/epic powers in the client export")
    print(f"  {agree} where the expression and the player's sentence AGREE")
    print(f"  {disagree} where they DISAGREE (listed below — expression wins, "
          "prose is player-facing summary)")
    print(f"  {no_sentence} carry no prerequisite sentence at all "
          "(expression is the only statement)")
    print(f"  {len(unresolved)} expression(s) gate-dependent or unsatisfiable "
          "from same-set powers alone")

    for fn, rec, n, hc, expr in conflicts:
        print(f"\n  CONFLICT {fn}  (player sees {rec.get('display_name')!r})")
        print(f"    expression -> needs {n}: {expr[:150]}")
        print(f"    sentence   -> says  {hc}: {help_sentence(rec)[:130]}")
    for fn, status, expr in unresolved[:12]:
        print(f"\n  {status.upper()} {fn}: {expr[:150]}")

    if "--json" in sys.argv:
        out = os.path.join(ROOT, "tools", "prereq_counts_from_requires.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump({fn: {"needs": n, "status": e,
                            "display_name": rec.get("display_name"),
                            "requires": x}
                       for fn, rec, n, e, x in rows}, f, indent=1)
        print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()
