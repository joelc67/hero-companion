"""POOL/EPIC REQUIRES AUDIT — the check that would have caught 2026-07-29.

The game enforces per-power REQUIRES expressions; our gate modeled position
counts and certified ~13 game-illegal champions (Tough/Weave without
Boxing/Kick class). This battery pins the fixed gate and watches the roster:

  1. GATE PINS (hard): _picks_legal REFUSES the Fighting trio without
     Boxing/Kick and ACCEPTS it with Boxing — the exact defect, pinned both
     directions through the server's own evaluator (single authority; this
     audit implements NO second evaluator).
  2. CHAMPIONS (hard-fail with --strict-champions, report otherwise): every
     champions.json pick-set passes every pick's requires expression.
     Report-only until the corrected re-cert wave merges; strict after.
  3. AUTOPICK SEEDS (report): raw autopick output per certified context.
     Violations here are repaired at certification birth (seed repair drops
     offenders); the selection-time autopick fix is queued in Unreleased —
     when it lands, this section goes strict too.

Prints "N of M expected checked" with hard denominators throughout.

Run:  py tools\\audit_pool_requires.py [--strict-champions]
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv  # noqa: E402

fails = []
checks = 0


def check(name, ok, detail=""):
    global checks
    checks += 1
    print(f"  {'PASS' if ok else 'FAIL'}  {name}"
          + (f"\n        {detail}" if detail else ""))
    if not ok:
        fails.append(name)


def violations(picks):
    picked = set(picks)
    return sorted(p for p in picked
                  if srv._requires_ok(p, picked) is False)


def main():
    strict = "--strict-champions" in sys.argv

    # 1. gate pins — the exact 2026-07-29 defect, both directions.
    # Evaluator level (the authority): the trio fails without Boxing/Kick and
    # passes with Boxing. Gate level: full REAL pick-sets, because
    # _picks_legal also enforces ladder-fit which no tiny synthetic set can
    # satisfy (first pin construction failed on exactly that — a finding
    # about the pin, kept as a comment so it isn't re-tried).
    trio = {"Pool.Fighting.Cross_Punch", "Pool.Fighting.Tough",
            "Pool.Fighting.Weave"}
    check("EVALUATOR PIN: Tough fails its requires without Boxing/Kick",
          srv._requires_ok("Pool.Fighting.Tough", trio) is False)
    with_box = trio | {"Pool.Fighting.Boxing"}
    check("EVALUATOR PIN: trio + Boxing satisfies Tough, Weave AND Cross Punch",
          all(srv._requires_ok(fn, with_box) is True for fn in trio))

    champs = json.load(open(os.path.join(ROOT, "benchmarks", "champions.json"),
                            encoding="utf-8"))
    crab_key = next(k for k in champs if "Crab_Spider" in k)
    crab = champs[crab_key]
    parts = crab_key.split("|")
    check("GATE PIN: the stored (game-illegal) Crab Spider champion is refused",
          not srv._picks_legal(set(crab.get("picks") or []), parts[1], parts[2]))
    legal_full = [(k, r) for k, r in sorted(champs.items())
                  if not violations(r.get("picks") or [])]
    if legal_full:
        k0, r0 = legal_full[0]
        p0 = k0.split("|")
        check(f"GATE PIN: a requires-clean full champion is accepted "
              f"({p0[1].split('.')[-1]})",
              srv._picks_legal(set(r0.get("picks") or []), p0[1], p0[2]))
    else:
        check("GATE PIN: a requires-clean full champion is accepted", False,
              "no clean champion available to pin")

    # 2. champions
    bad = {k: violations(r.get("picks") or []) for k, r in champs.items()}
    bad = {k: v for k, v in bad.items() if v}
    mode = "STRICT" if strict else "report-only until the re-cert wave merges"
    check(f"CHAMPIONS: {len(champs) - len(bad)} of {len(champs)} pick-sets "
          f"satisfy every client requires expression ({mode})",
          not bad if strict else True,
          "; ".join(f"{k.split('|')[1].split('.')[-1]}/{k.split('|')[3]}: "
                    + ",".join(b.split(".")[-1] for b in v)
                    for k, v in sorted(bad.items())[:6])
          + (f" … +{len(bad) - 6} more" if len(bad) > 6 else "") if bad else "")

    # 3. autopick seeds per certified context
    client = srv.app.test_client()
    seed_bad = {}
    n_seeded = 0
    for key in sorted(champs):
        parts = key.split("|")
        at, prim2, sec2, content = parts[:4]
        ap = client.post("/build/autopick", json={
            "archetype": at, "primary": prim2, "secondary": sec2,
            "content": content}).get_json()
        if not (ap and ap.get("powers")):
            seed_bad[key] = ["AUTOPICK FAILED"]
            continue
        n_seeded += 1
        v = violations([p["full_name"] for p in ap["powers"]])
        if v:
            seed_bad[key] = v
    check(f"AUTOPICK SEEDS: {n_seeded} of {len(champs)} contexts seeded; "
          f"{len(seed_bad)} carry violations (report-only — seed repair "
          f"handles certification; selection-time fix queued)", True,
          "; ".join(f"{k.split('|')[1].split('.')[-1]}: "
                    + ",".join(b.split(".")[-1] for b in v)
                    for k, v in sorted(seed_bad.items())[:5])
          + (f" … +{len(seed_bad) - 5} more" if len(seed_bad) > 5 else ""))

    print(f"\n{checks} of 6 expected checks ran")
    if checks != 6:
        fails.append("coverage denominator")
    print("══ ALL CHECKS PASS ══" if not fails
          else "FAILURES: " + ", ".join(fails))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
