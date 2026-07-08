"""Audit SLOTTING COHERENCE across every archetype — quantify the "spaghetti at a wall".

Maelwys's core critique: powers ending up with a scatter of one-off pieces from many
different sets (0 set bonuses earned) instead of committed sets or deliberate proc-bombs.
This measures it objectively so any optimizer change can be proven against a baseline.

For each AT (its first primary/secondary, damage role, general content) we autopick + solve,
then classify every slotted piece:
  * PROC        — a proc-pass piece (_proc). A power that is ALL procs = a deliberate proc-bomb.
  * GLOBAL      — a 1-piece unique global (LotG/Steadfast/Shield Wall/Kismet/…): does real work
                  alone, a legitimate mule.
  * COMMITTED   — a set contributing >=2 pieces in one power: earns its set bonuses.
  * FILLER      — a plain common IO (no set, no bonus): mediocre but sometimes needed.
  * FRAGMENT    — a real multi-piece SET contributing exactly 1 piece and NOT a global:
                  0 set bonus, pure spaghetti. THIS is the headline pathology.

Headline metric = total FRAGMENT pieces (lower is better). Also reports scatter powers
(>=3 slots, >=3 distinct non-proc sets, 0 sets reaching a bonus) and filler slots.

Run:  python tools/audit_slotting_coherence.py
"""
import os
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
import server as srv  # noqa: E402
import engine  # noqa: E402

# set-names that carry a build-wide GLOBAL usable at 1 piece (mule, not a fragment)
_GLOBAL_SETS = {g["set"].lower() for g in engine.PIECE_GLOBALS}
# a few more well-known +5%/proc globals that live in otherwise-slottable sets
_GLOBAL_SETS |= {"reactive defenses", "unbreakable guard", "preventive medicine",
                 "shield wall", "gladiator's armor", "steadfast protection",
                 "luck of the gambler", "kismet"}


def _is_common(set_name):
    """A plain common IO (no set): not present in the enhancement-set index."""
    if not set_name:
        return True
    return srv.SET_BY_NAME.get(set_name.lower()) is None


def _is_global(set_name):
    """True if a 1-piece slot from this set is a legitimate build-wide GLOBAL (a mule that
    does real work alone), not a dead fragment. Match by token so 'numina' catches the full
    display name 'Numina's Convalesence'."""
    n = (set_name or "").lower()
    return any(g in n for g in _GLOBAL_SETS)


def classify_power(slots):
    """Return (per-set piece histogram, list of (kind, set_name)) for a power's slots."""
    hist = Counter()
    procs = 0
    for s in slots or []:
        if not s:
            continue
        if s.get("_proc"):
            procs += 1
            continue
        hist[s.get("set_name") or "?"] += 1
    return hist, procs


def audit():
    frag_total = 0
    filler_total = 0
    procbomb_powers = 0
    scatter_powers = 0
    committed_powers = 0
    per_at = {}
    examples = []
    respec_misfires = []
    c = srv.app.test_client()

    # 0.12.15 REGRESSION PINS (Joel + Maelwys field reports, 2026-07-08). The audit's old
    # "coherent" definition was too loose — it missed a release where every common IO
    # rendered as an EMPTY slot and HO cores warned as duplicates. New hard-fail checks:
    #   * EMPTY-MIX: a solved power holding real pieces AND empty (None) slots
    #   * ICON-LESS: a slotted piece whose uid has no icon in PIECE_IMAGE (looks empty)
    #   * VALIDATION: /full validate on every solved build — 0 errors, 0 duplicate-piece
    #     warnings (HOs stack legally and must not warn)
    empty_mix = []
    iconless = {}
    validation_noise = []

    # COVERAGE DENOMINATOR (standing rule 2026-07-08): every eligible AT must be
    # SOLVED and audited — 15 is the pinned playable count. The old loop silently
    # skipped failed autopicks and fell back to UNSOLVED autopick powers when the
    # solve failed, so the audit could 'pass' while examining nothing real.
    EXPECTED_ATS = 15
    coverage_failures = []
    solved_ats = 0

    for at, groups in srv.POWERSETS["by_archetype"].items():
        prim = (groups.get("primary") or [{}])[0].get("full_name")
        sec = (groups.get("secondary") or [{}])[0].get("full_name")
        if not (prim and sec):
            continue
        ap = c.post("/build/autopick", json={"archetype": at, "primary": prim,
                                             "secondary": sec, "role": "damage",
                                             "content": "general", "exposure": "flex",
                                             "travel": "speed"}).get_json()
        if not ap.get("powers"):
            coverage_failures.append(f"{at}: autopick returned no powers")
            continue
        # Mirror the APP's solve payload (wizard/solve button), not a bare minimal one:
        # slots + earned_slot_count ride along, exposure/tier set — the path users hit.
        presolve = [{"full_name": p["full_name"], "slots": p.get("slots"),
                     "earned_slot_count": p.get("earned_slot_count")}
                    for p in ap["powers"]]
        sol = c.post("/build/solve", json={"archetype": at, "powers": presolve,
                                           "goal": "", "tier": "premium",
                                           "exposure": "flex", "preserve": False,
                                           "keep_layout": False,
                                           "content": "general", "role": "damage"}).get_json()
        if not sol.get("powers"):
            coverage_failures.append(f"{at}: solve failed — nothing audited for this AT")
            continue
        powers = sol["powers"]
        solved_ats += 1
        for p in powers:
            slots = p.get("slots") or []
            filled = [s for s in slots if s]
            if filled and len(filled) < len(slots):
                empty_mix.append(f"{at.split('_')[-1]}: {p.get('display_name')} "
                                 f"({len(slots) - len(filled)} empty of {len(slots)})")
            for s in filled:
                uid = s.get("piece_uid")
                if uid and not srv.PIECE_IMAGE.get(uid):
                    iconless.setdefault(uid, f"{at.split('_')[-1]}: "
                                        f"{p.get('display_name')} — {s.get('set_name')}")
        val = engine.validate_build({"powers": powers})
        for e in val.get("errors") or []:
            validation_noise.append(f"{at.split('_')[-1]} ERROR: {e}")
        for w in val.get("warnings") or []:
            if "duplicate piece" in w:
                validation_noise.append(f"{at.split('_')[-1]} DUP-WARN: {w}")
        # NO-MISFIRE GUARD: a freshly solved build is fully optimized, so the respec hint
        # (meant for under-invested loaded builds) must NEVER fire on it. Prove it every AT.
        calc = c.post("/build/calculate", json={"archetype": at, "powers": powers}).get_json()
        if calc.get("respec_hint"):
            respec_misfires.append(f"{at.split('_')[-1]}: {calc['respec_hint']}")
        at_frag = at_fill = 0
        for p in powers:
            slots = p.get("slots") or []
            if len(slots) < 2:
                continue
            hist, procs = classify_power(slots)
            nonproc = sum(hist.values())
            distinct = len(hist)
            committed = [s for s, n in hist.items() if n >= 2]
            # a deliberate proc-bomb: (almost) all slots are procs
            if procs >= 2 and nonproc <= 1:
                procbomb_powers += 1
                continue
            if committed:
                committed_powers += 1
            # FRAGMENTS: 1-piece real sets that aren't globals or commons
            frags = [s for s, n in hist.items()
                     if n == 1 and not _is_global(s) and not _is_common(s)]
            fillers = [s for s, n in hist.items() if n == 1 and _is_common(s)]
            at_frag += len(frags)
            at_fill += len(fillers)
            # TRUE scatter = a power carrying real FRAGMENTS (not the legitimate all-global
            # mule pattern like Health's 4 unique procs or Weave's LotG+Shield Wall+Kismet).
            if frags and nonproc >= 3 and not committed:
                scatter_powers += 1
            # list every power that holds a real fragment — the actual spaghetti to fix
            if frags and len(examples) < 30:
                examples.append(f"{at.split('_')[-1]:12s} {p.get('display_name','?'):22s} "
                                + "FRAG=[" + ", ".join(frags) + "]  all=["
                                + ", ".join(f"{s}x{n}" for s, n in hist.items()) + "]")
        frag_total += at_frag
        filler_total += at_fill
        per_at[at] = (at_frag, at_fill)

    print(f"{'archetype':26s} fragments  fillers")
    for at, (f, fl) in sorted(per_at.items(), key=lambda kv: -kv[1][0]):
        flag = "  <—" if f else ""
        print(f"  {at.split('_',1)[-1]:24s} {f:6d}   {fl:6d}{flag}")

    print(f"\n══ COHERENCE BASELINE ══")
    print(f"  FRAGMENT pieces (1-piece real sets, 0 bonus): {frag_total}")
    print(f"  FILLER slots (plain common IOs):              {filler_total}")
    print(f"  scatter powers (>=3 sets, 0 bonus earned):    {scatter_powers}")
    print(f"  deliberate proc-bomb powers:                  {procbomb_powers}")
    print(f"  committed powers (>=1 set at >=2 pieces):     {committed_powers}")
    print(f"  respec-hint MISFIRES on solved builds:        {len(respec_misfires)}"
          + ("  <— BUG" if respec_misfires else "  (good: the hint never nags an optimized build)"))
    for m in respec_misfires:
        print("   ", m)
    if examples:
        print("\n  scatter examples:")
        for e in examples:
            print("   ", e)

    print(f"\n══ REGRESSION PINS (0.12.15) ══")
    print(f"  EMPTY-MIX powers (pieces + empty slots):      {len(empty_mix)}"
          + ("  <— BUG" if empty_mix else ""))
    for e in empty_mix[:10]:
        print("   ", e)
    print(f"  ICON-LESS pieces (render as empty slots):     {len(iconless)}"
          + ("  <— BUG" if iconless else ""))
    for uid, where in list(iconless.items())[:10]:
        print(f"    {uid}  ({where})")
    print(f"  validation errors / duplicate-piece warnings: {len(validation_noise)}"
          + ("  <— BUG" if validation_noise else ""))
    for v in validation_noise[:10]:
        print("   ", v)
    print(f"\n  COVERAGE: {solved_ats} of {EXPECTED_ATS} expected archetypes solved+audited")
    for cf in coverage_failures:
        print("   ", cf)
    hard_fail = bool(empty_mix or iconless or validation_noise
                     or solved_ats < EXPECTED_ATS)
    print("\n  PINS:", "FAIL" if hard_fail else "PASS")
    if hard_fail:
        sys.exit(1)
    return frag_total, scatter_powers


if __name__ == "__main__":
    audit()
