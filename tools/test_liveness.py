"""Battery for reality_check_liveness: 6 checks, 4 sabotages.

Proves the check fails in every direction it claims to guard - an added record
(the 2026-08-10 failure), a removed record, an added offer, and a stale
disposition - and passes at the goal state and with a correct disposition.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reality_check_liveness import check

shipped_p = {"A.B.One", "A.B.Two"}
shipped_s = {"A.B", "Pool.X"}

n = 0
def ok(cond, msg):
    global n
    n += 1
    assert cond, f"check {n} FAILED: {msg}"
    print(f"  {n}. ok - {msg}")

# 1. goal state: identical sets, no dispositions -> clean
ok(check(set(shipped_p), shipped_p, set(shipped_s), shipped_s, {}) == [],
   "identical snapshot passes with zero dispositions")

# 2. SABOTAGE (the real failure): a record synthesised from the bins
f = check(shipped_p | {"Wind_Control.Vacuum"}, shipped_p, set(shipped_s), shipped_s, {})
ok(any("power added" in x and "Vacuum" in x for x in f), "an un-shipped power record fails")

# 3. SABOTAGE: a shipped record silently removed
f = check({"A.B.One"}, shipped_p, set(shipped_s), shipped_s, {})
ok(any("power removed" in x for x in f), "a removed shipped record fails")

# 4. SABOTAGE: a powerset offered that the release never offered
f = check(set(shipped_p), shipped_p, shipped_s | {"Pool.Gadgetry"}, shipped_s, {})
ok(any("offer added" in x and "Gadgetry" in x for x in f), "an un-shipped offered set fails")

# 5. a dispositioned diff passes (the PATCH-WATCH route for real new content)
f = check(shipped_p | {"New.Set.Power"}, shipped_p, set(shipped_s), shipped_s,
          {"New.Set.Power": "Homecoming patch YYYY-MM-DD, Joel's word"})
ok(f == [], "a dispositioned addition passes")

# 6. SABOTAGE: a disposition left behind after the diff is gone
f = check(set(shipped_p), shipped_p, set(shipped_s), shipped_s, {"New.Set.Power": "stale"})
ok(any("STALE" in x for x in f), "a stale disposition fails (two-way pin)")

print(f"test_liveness: {n}/{n} OK")
