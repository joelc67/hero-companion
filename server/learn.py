"""learn.py — cross-run LEARNING for the deep optimizer (the user's doctrine: "this is not about
the best of 700 — it's learning how to make the best solution").

Two knowledge stores, both grown by every deep_optimize run:

  • benchmarks/exploration_log.jsonl — every build ever evaluated, with its contribution breakdown.
    Mined here into PER-POWER MARGINALS: across all explored builds in a context (archetype +
    powersets + content), how much better do builds containing power X score than builds without
    it? Scores are PERCENTILE-normalized within context so knowledge survives model revisions
    (absolute scores change when the physics improves; orderings largely don't).

  • benchmarks/champions.json — the best CONVERGED build per context. The next run WARM-STARTS
    from the champion instead of the heuristic autopick: search begins where knowledge ended,
    and spends its budget extending the frontier instead of rediscovering it.

The marginals also ORDER the search neighborhood (try the historically-promising moves first) —
ordering only, never pruning: every legal move still gets evaluated before convergence is claimed.
"""
import json
import os
import sys

import diag

if getattr(sys, "frozen", False):
    # Packaged app: the gold-standard champions SHIP in the bundle (read-only) so end
    # users get the converged builds instead of the heuristic fallback. Anything the
    # learning stack writes goes to the user's writable app dir, never the bundle.
    _ROOT = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    _WRITE = os.path.join(os.environ.get("APPDATA", _ROOT), "HeroCompanion")
    LOG_PATH = os.path.join(_WRITE, "exploration_log.jsonl")
else:
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOG_PATH = os.path.join(_ROOT, "benchmarks", "exploration_log.jsonl")
# HC_CHAMPIONS_PATH: write-shard override for PARALLEL certification workers
# (roster build-out 2026-07-10): each worker saves champions to its own shard
# so no two processes ever rewrite the same file; shards merge into the real
# champions.json after validation (tools/merge_champion_shards.py). Warm-start
# reads follow the same path — harmless for NEW contexts (nothing to warm from).
CHAMPIONS_PATH = (os.environ.get("HC_CHAMPIONS_PATH")
                  or os.path.join(_ROOT, "benchmarks", "champions.json"))


def ctx_key(archetype, primary, secondary, content, form=None):
    """Context identity. `form` (2026-07-12, Joel's per-form Kheldian champions)
    appends a 5th part — 'dwarf'/'nova' — so a form champion lives beside the
    human-form one instead of overwriting it. Absent = the classic 4-part key,
    byte-identical to every existing champion."""
    parts = [archetype or "", primary or "", secondary or "", content or ""]
    if form:
        parts.append(form)
    return "|".join(parts)


def _iter_log(needles=()):
    """Stream the exploration log a row at a time, yielding parsed rows.

    ⚠⚠ NEVER MATERIALISE THIS FILE. It is the append-only record of every build
    the search has ever scored — 2.2 GB and millions of rows as of 2026-08-06,
    and it grows with every wave. The old `_load_log()` parsed EVERY row into a
    dict, returned the lot, and its only caller then kept one context's worth
    and threw the rest away. Measured on a real context before this change:
    **89.3 s and 6.17 GB of peak Python memory** for a result of 79 numbers.
    That is what set the RAM ceiling for parallel certification — the recorded
    "fix the parse before buying 256GB" item.

    `needles` are the identity strings of the context being asked about. They
    are a CHEAP REJECT applied to the raw line before json.loads, which is where
    nearly all the CPU went: every identity field is a plain ASCII JSON string,
    so a row that matches must contain each one literally. A false positive
    costs one wasted parse and is then dropped by the caller's real key test; a
    false NEGATIVE would be a correctness bug, which is why the test that
    decides membership is still `ctx_key`, never this.
    """
    try:
        with open(LOG_PATH, encoding="utf-8") as f:
            for line in f:
                if needles and not all(n in line for n in needles):
                    continue
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception:  # noqa: BLE001
                    diag.swallowed("learn: exploration-log line",
                                   "skipping one unparseable row")
    except FileNotFoundError:
        return


def marginals(archetype, primary, secondary, content):
    """{power_last_name: marginal percentile} for this context, from the whole exploration log.
    Positive = builds containing the power historically score higher. None-safe: {} if no data."""
    key = ctx_key(archetype, primary, secondary, content)
    # Only THIS context's rows are ever held in memory — see _iter_log. The
    # ctx_key test is unchanged and is still what decides membership.
    # ⚠ ORDER IS THE POINT: `all()` short-circuits, so the MOST selective string
    # goes first. Archetype is the least selective — thousands of rows share
    # Class_Defender — so leading with it costs a second scan of nearly every
    # line in a 2.2 GB file. The powerset names reject almost everything on the
    # first test.
    needles = tuple(p for p in (primary, secondary, archetype, content) if p)
    rows = [r for r in _iter_log(needles)
            if ctx_key(r.get("archetype"), r.get("primary"), r.get("secondary"),
                       r.get("content")) == key]
    if len(rows) < 20:
        return {}
    scores = sorted(r.get("score", 0) for r in rows)
    n = len(scores)

    def pct(s):                                   # percentile rank — model-revision tolerant
        lo, hi = 0, n
        while lo < hi:
            mid = (lo + hi) // 2
            if scores[mid] < s:
                lo = mid + 1
            else:
                hi = mid
        return lo / n

    with_p, without_p = {}, {}
    for r in rows:
        p = pct(r.get("score", 0))
        picks = {fn.split(".")[-1] for fn in (r.get("picks") or [])}
        for nm in picks:
            with_p.setdefault(nm, []).append(p)
    all_names = set(with_p)
    for r in rows:
        p = pct(r.get("score", 0))
        picks = {fn.split(".")[-1] for fn in (r.get("picks") or [])}
        for nm in all_names - picks:
            without_p.setdefault(nm, []).append(p)
    out = {}
    for nm in all_names:
        w = with_p.get(nm) or []
        wo = without_p.get(nm) or []
        if len(w) >= 5 and len(wo) >= 5:
            out[nm] = round(sum(w) / len(w) - sum(wo) / len(wo), 4)
    return out


LESSONS_PATH = os.path.join(_ROOT, "benchmarks", "lessons.jsonl")


def record_lessons(archetype, primary, secondary, content, heuristic_picks, champion_picks,
                   heuristic_misses, model_version=None):
    """The retrospective (user doctrine: 'ask yourself why did I miss those fits 693 times'):
    after convergence, diff what the HEURISTIC proposed vs what the search PROVED best, and
    persist the wrong calls as lessons. heuristic_misses = how many explored builds scored
    above the heuristic seed (the count of better fits the proposer never offered)."""
    h = {fn.split(".")[-1] for fn in heuristic_picks}
    c = {fn.split(".")[-1] for fn in champion_picks}
    line = {"ctx": ctx_key(archetype, primary, secondary, content),
            "model_version": model_version,       # lessons from an older model are IGNORED
            "search_added": sorted(c - h),        # the proposer MISSED these
            "search_dropped": sorted(h - c),      # the proposer wrongly KEPT these
            "heuristic_misses": heuristic_misses}
    try:
        with open(LESSONS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")
    except Exception:  # noqa: BLE001
        diag.swallowed("learn: lesson append", "the lesson is NOT persisted")
    return line


def seed_adjustments(archetype, primary, secondary, content, model_version=None):
    """{power_last_name: -1..+1} distilled from accumulated lessons — the FEEDBACK that makes the
    heuristic proposer itself learn: powers the search repeatedly had to ADD get a positive
    adjustment (propose them next time); powers it repeatedly had to DROP get negative.
    Lessons stamped with an OLDER model version are ignored — a blinder model's conclusions
    must not bias the proposer after the physics improves."""
    key = ctx_key(archetype, primary, secondary, content)
    votes = {}
    try:
        with open(LESSONS_PATH, encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    line = json.loads(raw)
                except Exception:  # noqa: BLE001
                    continue
                if line.get("ctx") != key:
                    continue
                if model_version is not None and line.get("model_version") != model_version:
                    continue
                for nm in line.get("search_added", []):
                    votes[nm] = votes.get(nm, 0) + 1
                for nm in line.get("search_dropped", []):
                    votes[nm] = votes.get(nm, 0) - 1
    except FileNotFoundError:
        return {}
    if not votes:
        return {}
    peak = max(abs(v) for v in votes.values()) or 1
    return {nm: round(v / peak, 3) for nm, v in votes.items()}


def load_champion(archetype, primary, secondary, content, form=None):
    """The best converged build (list of full_names) known for this context, or None."""
    try:
        data = json.load(open(CHAMPIONS_PATH, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    e = data.get(ctx_key(archetype, primary, secondary, content, form))
    return e.get("picks") if e else None


def save_champion(archetype, primary, secondary, content, picks, score, certificate,
                  form=None):
    try:
        data = json.load(open(CHAMPIONS_PATH, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        data = {}
    data[ctx_key(archetype, primary, secondary, content, form)] = {
        "picks": sorted(picks), "score": score, "certificate": certificate}
    with open(CHAMPIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
