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
    c = srv.app.test_client()

    for at, groups in srv.POWERSETS["by_archetype"].items():
        prim = (groups.get("primary") or [{}])[0].get("full_name")
        sec = (groups.get("secondary") or [{}])[0].get("full_name")
        if not (prim and sec):
            continue
        ap = c.post("/build/autopick", json={"archetype": at, "primary": prim,
                                             "secondary": sec, "role": "damage",
                                             "content": "general"}).get_json()
        if not ap.get("powers"):
            continue
        sol = c.post("/build/solve", json={"archetype": at, "powers": ap["powers"],
                                           "content": "general", "role": "damage"}).get_json()
        powers = sol.get("powers") or ap["powers"]
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
    if examples:
        print("\n  scatter examples:")
        for e in examples:
            print("   ", e)
    return frag_total, scatter_powers


if __name__ == "__main__":
    audit()
