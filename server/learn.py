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
CHAMPIONS_PATH = os.path.join(_ROOT, "benchmarks", "champions.json")


def ctx_key(archetype, primary, secondary, content):
    return "|".join([archetype or "", primary or "", secondary or "", content or ""])


def _load_log():
    rows = []
    try:
        with open(LOG_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:  # noqa: BLE001
                        pass
    except FileNotFoundError:
        pass
    return rows


def marginals(archetype, primary, secondary, content):
    """{power_last_name: marginal percentile} for this context, from the whole exploration log.
    Positive = builds containing the power historically score higher. None-safe: {} if no data."""
    key = ctx_key(archetype, primary, secondary, content)
    rows = [r for r in _load_log()
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
        pass
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


def load_champion(archetype, primary, secondary, content):
    """The best converged build (list of full_names) known for this context, or None."""
    try:
        data = json.load(open(CHAMPIONS_PATH, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    e = data.get(ctx_key(archetype, primary, secondary, content))
    return e.get("picks") if e else None


def save_champion(archetype, primary, secondary, content, picks, score, certificate):
    try:
        data = json.load(open(CHAMPIONS_PATH, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        data = {}
    data[ctx_key(archetype, primary, secondary, content)] = {
        "picks": sorted(picks), "score": score, "certificate": certificate}
    with open(CHAMPIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
