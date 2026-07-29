"""PREREQ REALITY CHECK — the game's OWN words vs our prerequisite model.

WHY THIS EXISTS (2026-07-29, and it cost a wave): I parsed a `requires`
expression out of the client bins, decided our count model was wrong, called
~20 shipping champions illegal, and burned 12 hours of certification. Then the
game's own help text said plainly: "You must be at least level 14 and have ONE
OTHER Fighting Powers" — any one. The count model was right all along.

So: never infer a rule from an undocumented field again. The client STATES its
prerequisites in English, per power, in display_help. This reads that
statement for EVERY pool/epic power and compares it to what our model would
enforce (server._epic_prereq_count over the set's tier order). Any
disagreement is printed as a hard failure with both sides quoted, so the
question is settled by the game's words rather than anyone's parse.

Coverage denominator: every Pool./Epic. power in data/powers.json that the
client export can be matched to (same resolvers as the shipped patchers).
Powers whose help states no prerequisite are checked to need 0.

Run:  py tools\\reality_check_prereqs.py [--verbose]
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
import server as srv  # noqa: E402

OUT_FULL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")
VERBOSE = "--verbose" in sys.argv

_WORDNUM = {"no": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
# The client's own sentence, e.g. "you must be at least level 14 and have one
# other Fighting Powers before selecting Tough" / "have two other Primal Forces
# Mastery Powers". Deliberately tolerant of the game's own grammar slips.
_RE_NEED = re.compile(
    # the game says this several ways: "have one other Fighting Powers",
    # "have trained any two other Concealment powers" — a narrow regex read
    # the second form as "no prerequisite", which is how a parser lies.
    r"have\s+(?:trained\s+)?(?:any\s+)?(\w+)\s+other\s+(.{0,60}?)\s*Powers?\b",
    re.I | re.S)


def _norm(ps):
    return frozenset(w for w in ps.lower().split("_"))


def client_index():
    """full_name -> display_help, plus a word-set index for the Mids-vs-client
    set-name split (Epic.Dark_Mastery_Controller vs Epic.Controller_Dark_...)."""
    idx, by_words = {}, {}
    for f in glob.glob(os.path.join(OUT_FULL, "pool", "*", "*.json")) + \
             glob.glob(os.path.join(OUT_FULL, "epic", "*", "*.json")):
        if os.path.basename(f) == "index.json":
            continue
        try:
            rec = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        fn, help_ = rec.get("full_name"), rec.get("display_help") or ""
        if not fn:
            continue
        idx[fn] = help_
        cat, ps, pw = fn.split(".", 2)
        by_words.setdefault((cat.lower(), _norm(ps), pw.lower()), []).append(fn)
    return idx, by_words


def stated_need(help_text):
    """What the GAME says this power needs: N other powers of its set, or None
    when it states no prerequisite."""
    m = _RE_NEED.search(help_text or "")
    if not m:
        return None
    return _WORDNUM.get(m.group(1).lower())


def main():
    idx, by_words = client_index()
    data = json.load(open(os.path.join(ROOT, "data", "powers.json"),
                          encoding="utf-8"))
    expected = checked = agree = 0
    unmatched, mismatches, unparsed = [], [], []

    for ps, lst in sorted(data.items()):
        if not (ps.startswith("Pool.") or ps.startswith("Epic.")):
            continue
        for p in lst:
            fn = p.get("full_name")
            expected += 1
            help_ = idx.get(fn)
            if help_ is None:
                cat, psn, pw = fn.split(".", 2)
                cands = by_words.get((cat.lower(), _norm(psn), pw.lower()), [])
                helps = {idx[c] for c in cands}
                if len(cands) >= 1 and len({stated_need(h) for h in helps}) == 1:
                    help_ = next(iter(helps))
                else:
                    unmatched.append(fn)
                    continue
            checked += 1
            ours = srv._prereq_need(fn, ps)   # what the APP enforces
            theirs = stated_need(help_)
            if theirs is None:
                # game states no prerequisite sentence -> it needs none
                theirs = 0
                if "before selecting" in (help_ or "").lower():
                    unparsed.append((fn, help_[:120]))
                    continue
            if ours == theirs:
                agree += 1
                if VERBOSE:
                    print(f"  ok   {fn}: both say {ours}")
            else:
                # SELF-SKEPTICISM (the lesson of 2026-07-29): the client's help
                # sentence sometimes names a DIFFERENT power than the record it
                # sits on (Vengeance's says "before selecting Victory Rush").
                # A mismatch whose sentence names someone else is EVIDENCE
                # ABOUT THE TEXT, not about the rule — never act on it without
                # a second source.
                m = re.search(r"before selecting ([A-Za-z' \-]+)", help_ or "")
                named = (m.group(1).strip() if m else "")
                own = fn.rsplit(".", 1)[-1].replace("_", " ")
                suspect = bool(named) and named.lower() != own.lower()
                mismatches.append((fn, ours, theirs, help_, suspect, named))

    print(f"\nPREREQ REALITY CHECK — the game's words vs our model")
    print(f"  {checked} of {expected} Pool/Epic powers checked "
          f"({len(unmatched)} unmatched in the client export)")
    solid = [m for m in mismatches if not m[4]]
    suspect = [m for m in mismatches if m[4]]
    print(f"  {agree} agree, {len(mismatches)} DISAGREE "
          f"({len(solid)} on the power's OWN sentence, {len(suspect)} whose "
          f"sentence names a DIFFERENT power — text evidence, not rule "
          f"evidence), {len(unparsed)} unparsable prerequisite")
    for fn, ours, theirs, help_, susp, named in solid + suspect:
        sent = next((s.strip() for s in re.split(r"<br>|\. ", help_ or "")
                     if "other" in s.lower() and "power" in s.lower()), "")
        tag = f"  ⚠ SENTENCE NAMES '{named}' — needs a second source" if susp else ""
        print(f"\n  MISMATCH {fn}{tag}\n    ours: needs {ours} other set powers"
              f"\n    game: needs {theirs} — \"{sent[:140]}\"")
    for fn, snippet in unparsed:
        print(f"\n  UNPARSED PREREQ {fn}: \"{snippet}\"")
    if unmatched and VERBOSE:
        print("\n  unmatched (no client record):")
        for fn in unmatched:
            print(f"    {fn}")

    bad = bool(mismatches or unparsed)
    print("\n" + ("REALITY CHECK FAILED — the game disagrees with our model above"
                  if bad else
                  "ALL CHECKED POWERS AGREE — our prerequisite model matches "
                  "the game's own stated rules"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
