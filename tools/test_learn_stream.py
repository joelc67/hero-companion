"""Battery for the streaming exploration-log read (server/learn.py).

    py tools\\test_learn_stream.py

WHY THIS EXISTS. `marginals()` used to parse the WHOLE exploration log into
dicts and keep one context's worth — measured 2026-08-06 on the real 2.2 GB log:
89.3 s and 6.17 GB of peak Python memory for a result of 79 numbers. It now
streams, with a cheap substring reject applied to the raw line before
json.loads.

THE RISK THAT REJECT INTRODUCES IS A FALSE NEGATIVE: a row that belongs to the
context but is skipped before it is ever parsed. That would not crash anything
— it would quietly make the search learn from less history than it has, which is
the worst kind of bug because nothing says so. Every check below exists to pin
that: the streamed answer must equal a dumb full-scan reference, on fixtures
built to be awkward.
"""
import json
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import learn  # noqa: E402

CHECKS = []
EXPECTED = 11


def check(label, ok, why=""):
    CHECKS.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    if not ok and why:
        print(f"        {why}")


CTX = ("Class_Defender", "Defender_Buff.Poison",
       "Defender_Ranged.Sonic_Attack", "itrial")
POWERS = ["Pool.Fighting.Tough", "Pool.Fighting.Weave", "Pool.Speed.Hasten",
          "Defender_Buff.Poison.Envenom", "Defender_Buff.Poison.Weaken"]


def row(i, ctx=CTX, picks=None, score=None):
    a, p, s, c = ctx
    return {"archetype": a, "primary": p, "secondary": s, "content": c,
            "score": 100 + (i % 37) if score is None else score,
            "picks": picks if picks is not None else POWERS[: 2 + (i % 4)]}


def full_scan_reference(path, ctx):
    """The dumb version: parse EVERY line, then filter. What the streamed read
    must agree with, by construction."""
    key = learn.ctx_key(*ctx)
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if learn.ctx_key(r.get("archetype"), r.get("primary"),
                             r.get("secondary"), r.get("content")) == key:
                out.append(r)
    return out


def write_log(rows):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return path


def main():
    orig = learn.LOG_PATH
    try:
        # ── fixture: our context, plus rows built to trip a naive filter ─────
        rows = [row(i) for i in range(40)]
        # a DECOY: different context, but its text contains every one of our
        # identity strings (a note field). The substring reject will let this
        # through; ctx_key must throw it out.
        rows.append({"archetype": "Class_Corruptor",
                     "primary": "Corruptor_Ranged.Sonic_Attack",
                     "secondary": "Corruptor_Buff.Poison", "content": "itrial",
                     "score": 9999, "picks": POWERS,
                     "note": "Class_Defender Defender_Buff.Poison "
                             "Defender_Ranged.Sonic_Attack itrial"})
        # plain non-matching rows
        rows += [row(i, ctx=("Class_Scrapper", "Scrapper_Melee.Claws",
                             "Scrapper_Defense.Super_Reflexes", "general"))
                 for i in range(30)]
        # SAME primary and secondary, DIFFERENT content — these exist to make a
        # weakened needle set visible. Filtering on the powerset alone lets them
        # through; only the full identity rejects them.
        rows += [row(i, ctx=(CTX[0], CTX[1], CTX[2], "general"), score=1)
                 for i in range(25)]
        path = write_log(rows)
        learn.LOG_PATH = path

        # 1-2: the streamed read agrees with a full scan, and actually found the
        # rows (a filter that returns nothing would trivially "agree" on empty).
        streamed = list(learn._iter_log(
            (CTX[1], CTX[2], CTX[0], CTX[3])))
        key = learn.ctx_key(*CTX)
        streamed_ctx = [r for r in streamed
                        if learn.ctx_key(r.get("archetype"), r.get("primary"),
                                         r.get("secondary"), r.get("content")) == key]
        ref = full_scan_reference(path, CTX)
        check("streamed rows equal a full scan", streamed_ctx == ref,
              f"{len(streamed_ctx)} vs {len(ref)}")
        check("...and it is not trivially empty", len(ref) == 40, f"{len(ref)}")

        # 3: THE DECOY — a row whose text carries every needle but whose context
        # differs must not survive. The substring test is a pre-filter, never
        # the decider.
        check("a text-only match is dropped by ctx_key",
              all(r.get("archetype") == "Class_Defender" for r in streamed_ctx)
              and any(r.get("archetype") == "Class_Corruptor" for r in streamed),
              "the decoy should pass the needles and fail the key")

        # 4: marginals() itself is unchanged in behaviour
        m_stream = learn.marginals(*CTX)
        check("marginals returns numbers for this context", len(m_stream) > 0)

        # 5: NO FALSE NEGATIVES — every reference row is present in the stream.
        missing = [r for r in ref if r not in streamed_ctx]
        check("no matching row is skipped before parsing", not missing,
              f"{len(missing)} row(s) lost by the pre-filter")

        # 6: an unparseable line does not kill the read (the swallow still works)
        with open(path, "a", encoding="utf-8") as f:
            f.write("{not json at all\n")
            f.write(json.dumps(row(99)) + "\n")
        again = [r for r in learn._iter_log((CTX[1], CTX[2], CTX[0], CTX[3]))
                 if learn.ctx_key(r.get("archetype"), r.get("primary"),
                                  r.get("secondary"), r.get("content")) == key]
        check("a corrupt line is skipped, the rest still read", len(again) == 41,
              f"{len(again)}")

        # 7: a missing log is not an error — a fresh install has none
        learn.LOG_PATH = os.path.join(tempfile.gettempdir(), "no_such_log.jsonl")
        check("a missing log yields nothing and does not raise",
              list(learn._iter_log(("x",))) == [] and learn.marginals(*CTX) == {})

        # 8: with NO needles it streams everything — the general contract still
        # holds for any future caller that wants the whole file.
        learn.LOG_PATH = path
        check("no needles = every row", len(list(learn._iter_log())) == len(rows) + 1,
              f"{len(list(learn._iter_log()))} of {len(rows) + 1}")

        # 9: THE FILTER MUST ACTUALLY NARROW. Weakening the needle set is not a
        # correctness bug — ctx_key still saves the answer — so it would pass
        # every check above while silently throwing the speedup away on a 2.2 GB
        # file. The same-content rows above are what make that visible.
        full = tuple(p for p in (CTX[1], CTX[2], CTX[0], CTX[3]) if p)
        narrowed = len(list(learn._iter_log(full)))
        widened = len(list(learn._iter_log(full[:1])))
        check("the full needle set rejects more than a partial one",
              narrowed < widened,
              f"full={narrowed} vs primary-only={widened} — the pre-filter is not narrowing")

        # 10: NEGATIVE CONTROL ON ctx_key ITSELF. The decoy passes the substring
        # test and carries an extreme score; if marginals ever stopped applying
        # ctx_key it would quietly learn from other contexts. Removing the decoy
        # must not move the answer by so much as a digit.
        # ⚠ row(99) was appended to `path` by check 6, so the clean copy must
        # carry it too — otherwise this compares two different data sets and
        # fails on correct code (it did, first time).
        clean = write_log([r for r in rows if r.get("note") is None] + [row(99)])
        learn.LOG_PATH = clean
        m_clean = learn.marginals(*CTX)
        learn.LOG_PATH = path
        m_decoy = learn.marginals(*CTX)
        check("a decoy row cannot influence the answer", m_clean == m_decoy,
              "ctx_key is what decides membership, not the substring test")
        os.unlink(clean)

        # 11: …and marginals must hand the stream the WHOLE identity. Checks 9
        # and 10 both survive a weakened needle set — ctx_key still rescues the
        # answer, so the only symptom is that a 2.2 GB file gets parsed far more
        # than it needs to be. Nothing about the result would ever say so, which
        # is why this watches the call itself.
        real_iter = learn._iter_log
        seen_needles = []

        def spy(needles=()):
            seen_needles.append(tuple(needles))
            return real_iter(needles)

        learn._iter_log = spy
        try:
            learn.marginals(*CTX)
        finally:
            learn._iter_log = real_iter
        check("marginals filters on the full identity, not a subset",
              bool(seen_needles) and set(seen_needles[0]) == {p for p in CTX if p},
              f"passed {seen_needles!r} — a subset silently costs the speedup")

        os.unlink(path)
    finally:
        learn.LOG_PATH = orig

    print(f"\n{len(CHECKS)} of {EXPECTED} expected checks ran")
    if len(CHECKS) != EXPECTED:
        raise SystemExit("COVERAGE FAILURE — a check did not run")
    bad = CHECKS.count(False)
    print("══ ALL CHECKS PASS ══" if not bad else f"{bad} FAILURE(S)")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
