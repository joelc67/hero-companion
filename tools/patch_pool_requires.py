"""Additive patcher: pool/epic power REQUIRES expressions from the live client.

WHY (2026-07-29 stop-the-line): our pool legality modeled POSITION-COUNT
("third pick needs 1 prior, 4th-5th need 2"); the game enforces per-power
REQUIRES expressions (client: Tough = Boxing||Kick; Weave/Cross Punch = two of
the pool). The divergence certified ~13 game-illegal champions and poisoned
the learning stack. This patch brings the client's own expressions into
powers.json so ONE evaluator (server._requires_ok) can be the authority for
autopick, _picks_legal, the wizard, and validation.

Family rules honored: additive only (`requires` key on existing Pool./Epic.
records), binary-preserving compact write, idempotent, coverage denominator
printed + hard-fail below 95%, strip-verify byte-identical.

Run:  py tools\\patch_pool_requires.py [--write]
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POWERS = os.path.join(ROOT, "data", "powers.json")
OUT_FULL = os.path.join(ROOT, "tools", "gamedata", "bin-crawler", "out_full")

sys.stdout.reconfigure(encoding="utf-8")


# Mids-era abbreviations and fused two-AT set names vs the client's spellings.
_WORD_EXPAND = {"corr": ("corruptor",), "def": ("defender",),
                "elec": ("electricity",), "lev": ("leviathan",),
                "psi": ("psionic",), "scrap": ("scrapper",),
                "stalk": ("stalker",),
                "tankbrute": ("tank", "brute"),
                "defcorr": ("defender", "corruptor"),
                "scrapstalk": ("scrapper", "stalker")}
# AT words never define the FAMILY — the family is what's left after removing them.
_AT_WORDS = {"blaster", "brute", "controller", "corruptor", "defender",
             "dominator", "mastermind", "scrapper", "sentinel", "stalker",
             "tank", "tanker", "veat", "melee", "domingator"}  # sic: client typo dir


def _words(ps):
    out = []
    for w in ps.lower().split("_"):
        out.extend(_WORD_EXPAND.get(w, (w,)))
    return out


def _norm_key(full_name):
    """Word-order-insensitive identity with abbreviation expansion. Key =
    (category, frozenset of expanded set-name words, power name)."""
    cat, ps, pw = full_name.split(".", 2)
    return (cat.lower(), frozenset(_words(ps)), pw.lower())


def _family_key(full_name):
    """The set FAMILY: expanded set words minus AT words (flame/mastery...)."""
    cat, ps, pw = full_name.split(".", 2)
    fam = frozenset(w for w in _words(ps) if w not in _AT_WORDS)
    return (cat.lower(), fam, pw.lower())


def client_requires_index():
    idx, norm = {}, {}
    for f in glob.glob(os.path.join(OUT_FULL, "pool", "*", "*.json")) + \
             glob.glob(os.path.join(OUT_FULL, "epic", "*", "*.json")):
        if os.path.basename(f) == "index.json":
            continue
        try:
            rec = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        fn = rec.get("full_name")
        r = (rec.get("requires") or "").strip()
        if fn:
            idx[fn] = r          # empty string is MEANINGFUL: no prereq
            norm.setdefault(_norm_key(fn), []).append(fn)
            norm.setdefault(("FAM",) + _family_key(fn), []).append(fn)
    return idx, norm


def main(write=False):
    raw = open(POWERS, "rb").read()
    data = json.loads(raw)
    idx, norm = client_requires_index()
    print(f"client export: {len(idx)} pool/epic power records "
          f"({sum(1 for v in idx.values() if v)} with a requires expression)")

    # OUR full_names, and a normalized map of them — expression tokens arrive
    # in CLIENT naming and must be translated to OUR naming or the evaluator
    # would silently never match them (over-strict = the same defect class
    # this patch exists to kill, in the opposite direction).
    ours = {p.get("full_name") for lst in data.values() for p in lst}
    ours_norm = {}
    for o in ours:
        if o and o.count(".") == 2:
            ours_norm.setdefault(_norm_key(o), []).append(o)

    def translate(expr):
        out = []
        for tok in expr.split():
            if tok.count(".") == 2 and tok not in ours:
                c = ours_norm.get(_norm_key(tok), [])
                if len(c) == 1:
                    tok = c[0]
            out.append(tok)
        return " ".join(out)

    expected = matched = changed = norm_matched = 0
    misses, ambiguous = [], []
    for ps, lst in data.items():
        if not (ps.startswith("Pool.") or ps.startswith("Epic.")):
            continue
        for p in lst:
            fn = p.get("full_name")
            expected += 1
            src = fn if fn in idx else None
            expr = None
            if src is None:
                cands = norm.get(_norm_key(fn), [])
                if len(cands) == 1:
                    src = cands[0]
                    norm_matched += 1
                elif len(cands) > 1:
                    ambiguous.append((fn, cands))
                    continue
                else:
                    # FAMILY fallback (shared/fused AT sets): acceptable ONLY
                    # when every family candidate agrees on the translated
                    # expression — disagreement is reported, never guessed.
                    fam = norm.get(("FAM",) + _family_key(fn), [])
                    exprs = {translate(idx[c]) for c in fam}
                    if len(exprs) == 1:
                        expr = exprs.pop()
                        norm_matched += 1
                    elif len(exprs) > 1:
                        ambiguous.append((fn, sorted(fam)))
                        continue
                    else:
                        misses.append(fn)
                        continue
            matched += 1
            if expr is None:
                expr = translate(idx[src])
            if p.get("requires") != expr:
                p["requires"] = expr
                changed += 1
    print(f"{matched} of {expected} Pool/Epic powers matched "
          f"({norm_matched} via word-order normalization; {changed} changed this run)")
    if ambiguous:
        print(f"  AMBIGUOUS normalized matches ({len(ambiguous)}) — left unpatched:")
        for fn, cands in ambiguous[:10]:
            print(f"    {fn} -> {cands}")
    if misses:
        # full list, never truncated — the "page the whole list" rule
        print(f"  unmatched ({len(misses)}), by set:")
        for s in sorted({m.rsplit(".", 1)[0] for m in misses}):
            n = sum(1 for m in misses if m.rsplit(".", 1)[0] == s)
            print(f"    {s} ({n})")
    if expected == 0 or matched < 0.95 * expected:
        print("HARD FAIL: coverage below 95% — not writing.")
        sys.exit(1)
    if not write:
        print("(report only — rerun with --write to apply)")
        return
    out = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    check = json.loads(out)
    orig = json.loads(raw)
    for d in (check, orig):
        for ps, lst in d.items():
            for p in lst:
                p.pop("requires", None)
    if check != orig:
        print("HARD FAIL: strip-verify mismatch — not writing.")
        sys.exit(1)
    with open(POWERS, "wb") as f:
        f.write(out)
    print(f"written: {POWERS}")


if __name__ == "__main__":
    main(write="--write" in sys.argv)
