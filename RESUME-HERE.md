# ✅ Resume point - 2026-08-10 (later), the audit-of-the-audit is DONE

The block below this one ordered four things. Three are done, one is Joel's.

## 1. THE AUDIT HOLE IS CLOSED
`tools/reality_check_liveness.py`: current powers.json record names + offered
powersets vs the SAME files at the highest release tag (v0.12.35 today). Any
diff hard-fails BOTH ways unless dispositioned with evidence in
`tools/liveness_dispositions.json` - which is EMPTY, the goal state: 10,980
records / 458 offered sets, zero drift vs shipped. Wired into
`converge_parallel` beside the prereq gate (proven: a sabotaged disposition
aborts the launch before any worker spawns). Battery `tools/test_liveness.py`,
6 checks / 4 sabotages. Real new content arrives via PATCH-WATCH and the
release that ships it moves the baseline tag forward by existing.

## 2. ALL SIX MODEL VERSIONS VERIFIED INDEPENDENTLY
Fresh probes through the real routes (test_client /build/calculate + fp), not
the batteries. Every falsification check passed, most to the exact digit:
- **v39** damage_buff 0 -> 0.1111, ST DPS 14.4 -> 16.0 (exact)
- **v40** Wet Ice alone reads slow_resist 110% in bonus_extras
- **v41** Agile 6.92 exact; the table's "48.44" is the FIVE-power subset
  (6.92x3 + 13.84x2); all nine SR powers sum 86.51 (adds Evasion 13.84,
  Elude 6.23 duty-cycled, Practiced Brawler 18.0 - all client-derived rows)
- **v42** Particle Shielding absorb 401.6 HP via bonus_extras only (top level
  clean); 3 recharge IOs move Rage 0.40 -> 0.7963
- **v43** floor 0.225, 0.5 at +122% and capped, Controller reads 0
- **v44** 251 rows / 245 powers, Scrapper_/Stalker_ only, and **251/251 equal
  a fresh derivation from the client** (patch_power_crits.crit_rows re-run).
  ⚠ Two glosses in the old table were imprecise, the data is right: the floor
  is per DAMAGE TYPE from the client's own stated chances (Eviscerate/Head
  Splitter state a FLAT 0.15, Storm Kick's minion branch states 0.10 - taking
  those IS the floor rule), and "crit row == base row" holds as the SUM of the
  base components (Claws Slash: two 0.66 rows, crit 1.32), not per row.

## 3. RELEASE PREP BACKED OUT
VERSION, both smoke tools and the help PDF are byte-identical to v0.12.35
again (checked with `git diff v0.12.35 --stat`, empty). The CHANGELOG keeps
its UNRELEASED 0.12.36 entry with the RETRACTED section - that is normal
staging. The release procedure re-bumps all four mechanically when Joel says
cut.

## 4. STILL JOEL'S, unchanged
- **The clean re-cert.** All three waves ran with fake content in the option
  space. The 22 uncontaminated champions are legal and correctly scored but
  not provably optimal in the true space; the 2 contaminated ones were
  re-converged clean (v44c). ~17 hours to know for sure.
- Cutting 0.12.36 (carries the retraction; champions.json bundles, so the
  re-cert decision naturally comes first).
- The standing scenario asks: `mez_in`, the stack-meter constant, a spawn
  rank mix, the third clean Fury attack log.

---

# ⛔ (RESOLVED 2026-08-10, see above) READ THIS BEFORE TRUSTING ANYTHING FROM 2026-08-08..10

**Assume this session's work is unverified.** It landed six model versions and
a full re-certification, and it also added 34 records of content that IS NOT IN
THE GAME and had to be retracted. The same judgement produced both. Your job is
to find out which parts are real.

## THE ERROR, so you do not repeat it
I added Wind Control (20 records), Pool.Gadgetry (6), Pool.Utility_Belt (6) and
Boomerang Slice (4) because the CLIENT BINS carry them in full - display names,
help text, icons, `available_level` arrays shaped exactly like known-live sets.
**None of that is evidence of release.** Joel: *"There is NO GADGETRY pool"*,
*"Boomerang Slice is not live"*, *"We do not know if old code in game never
matured into actual live game used live."*

⚠⚠ **THE LIVENESS AUTHORITY IS THE MIDS-DERIVED SNAPSHOT** (`data/powers.json`
as shipped in the last release), because Mids tracks LIVE Homecoming. If the
bins have it and that snapshot does not, it is NOT live. I had this signal,
wrote down that the absence was "honest, not a defect", and overrode it anyway.

⚠ Measured so you do not repeat the search: **no client field separates live
from dev content** (Wind Control's index entry is indistinguishable from Ice
Control's), and **the play logs cannot answer it** - a name search returned 0
for Wind Control AND 0 for Storm Summoning, which is certainly live.

💥 Cost: the fake pools reached two certified champions and sat in the solver's
option space for **all three re-cert waves, ~17.3 hours of compute**.

## STATE RIGHT NOW (measured 2026-08-10)
- All 34 fake records **removed**. Nothing v0.12.35 shipped was lost (checked
  both directions). Roster **24/24 served, 24/24 legal, 0 references to removed
  powers**. Prereq gate 467/467.
- Batteries green: gate 24, model-stamp 8, crits 12, domination 16, mode-tags
  19, absorb 27, empty-records 17, verdict-legality, pvp-variant, plateau,
  exemplar, display-name-collisions.
- Reality checks green: effect coverage (32 gaps pinned), mode tags 47/47,
  missing powers (8 pinned, incl. the retractions), empty records.
- ⚠ `reality_check_powers` exits 1 on `range 2, cast_time 1` drift. **This is
  PRE-EXISTING** - verified stale at HEAD before this session touched anything.

## ⛔ RELEASE IS HELD, AND HALF-PREPPED
`VERSION` is bumped to **0.12.36 but nothing shipped**. Also already changed:
the five smoke pins (`smoke_release` x2, `smoke_gold` x3 incl. model 44), and
the help PDF is rebuilt at 0.12.36. The CHANGELOG 0.12.36 entry is marked
UNRELEASED and carries a RETRACTED section. **Either finish the release or back
all of that out - do not leave it half-set.**

## WHAT MIGHT BE REAL, AND HOW TO CHECK IT YOURSELF
Six model versions landed. Each was measured at the time, but so was the
content that turned out fake. Verify independently:

| version | claim | the check that would falsify it |
|---|---|---|
| v39 | self +damage buffs priced at duty cycle | add Build Up via /build/calculate; damage_buff 0 -> 0.111, ST DPS 14.4 -> 16.0 |
| v40 | power-granted slow resistance | Wet Ice alone should read a real slow_resist in bonus_extras |
| v41 | defence debuff resistance, 178 powers | Agile 6.92%, full SR 48.44%, capped 95% |
| v42 | absorb + the dead `Recharge` word | absorb via bonus_extras (NOT top level); 3 recharge IOs move Rage 0.40 -> 0.796 |
| v43 | Domination +50% control duration | floor 0.225 at no recharge, 0.5 at +122%, 0 for a Controller |
| v44 | Scrapper/Stalker criticals at the stated floor | crit row scale == base row scale; only Scrapper_/Stalker_ records |

⚠ **The thing I could NOT verify and neither can the batteries: whether the
champions are optimal.** All three waves ran with fake content in the option
space. The 22 that never took a fake power are legal and correctly scored, but
whether they would converge identically in the TRUE space is unproven. **A
clean re-cert is the only way to know, and it is Joel's call whether it is
worth another ~17 hours.**

## SUGGESTED ORDER FOR THE NEXT SESSION
1. **Audit the audit.** Every check I built compares the CLIENT to our data;
   not one asks whether the client's content is live. Add that test, or accept
   that the whole coverage suite is blind to the failure that actually happened.
2. Re-verify the six model terms from the table above, independently.
3. Decide the clean re-cert (Joel).
4. Then finish or unwind the release prep.

## DORMANT TOOLS (kept deliberately, DO NOT RUN)
`add_wind_control.py`, `add_origin_pools.py`, `add_boomerang_slice.py` - they
re-add content that is not in the game. Kept only so it is one command away IF
the game ever ships it. Their batteries were deleted.

---

# Resume point - 2026-08-10, THE ROSTER IS FULLY v44 - both waves merged

## STATE
HEAD `d4183fc5`, pushed. Nothing running. Data **2026.1.1242**, **model v44**.
Roster **24 contexts · 24/24 SERVED · 24/24 legal · all canonical fresh**.
⚠⚠ **`evaluate_first` now reports 52 unaffected, 0 MOVED, 0 failed.** Every
context has been re-converged under v44 and every stored canonical equals a
fresh evaluation. **The v40-v44 model bump is fully absorbed. No re-cert owed.**

## THE TWO WAVES
**Wave 1** (19 contexts, 880.6 min, 6 workers): 8 supersede / 11 keep, merged
`306370bb`. **Wave 2** (5 contexts, 142.4 min, 5 workers): 2 supersede / 3 keep,
merged `d4183fc5`. All 11 workers rc=0 across both; every certificate converged
with no budget truncation. 10 champions replaced in total.

### ⚠⚠ THE SCOPING LESSON, which is the durable part
Wave 1 was scoped by **"does this build HOLD a power carrying a new row?"** and
got 19. `evaluate_first` afterwards showed **16 moved, five of them excluded**.
Holding a patched power is SUFFICIENT, NOT NECESSARY: v42's RechargeTime fix
reaches **timed PET uptime** (hence the Mastermind and the farm build) and
scenario channels move a score with no patched power picked at all.
**THE RIGHT SCOPE TEST IS AN EVALUATE-FIRST PASS BEFORE THE WAVE - re-score
every context under the new model and take the movers.** The tool exists for
exactly this and I ran it afterwards instead of first, costing a second wave.

### ⚠ SPINES/FIERY_AURA - do not quote the old farm number
The shipped farm champion fell **375.9 -> 227.6** under v40-v44; the re-converge
recovers it only to **283.4**. Not a wave failure - the new terms price that
build lower than v38 did and a fresh search cannot reach the old figure. Any
public farm claim resting on 375.9 is stale.

### What KEPT is as informative as what moved
The v43 and v44 targets ALL kept: Dominator -385.1, Stalker Rad_Melee -344.3,
Scrapper Broad_Sword -198.3. The new terms are more accurate but did not produce
better builds. Supersedes again CONCENTRATE in Kheldian form-locked contexts.

### Verification that is NOT in the tools
⚠ The verdict log never mentions legality. Both times I ran `_picks_legal` by
hand over challengers AND standing incumbents: **zero illegal**. Silence in a
log is not proof, and this is the exact failure that shipped 8 unbuildable
champions in 0.12.30. **Keep doing this by hand until the gate prints it.**

## HOUSEKEEPING DONE
31 stale shards retired (`.retired_2026-08-09`), both waves' shards retired at
merge (`.merged_2026-08-09`); only the 3 `e_gt` ground truths remain in the
`certified_union` glob. Wave-1 verdicts preserved as
`recert_verdicts_wave1.json.kept_2026-08-09`.

## ✅ DONE 2026-08-10: the model stamp (`e042a5e6`)
`merge_champion_shards` stamps `model_version` at its single write point and
the 24 are back-filled with v44. **"Have we updated all the champions?" is now
answerable by inspection** — `(v.get("model_version") or 0) < fp.MODEL_VERSION`
returns nothing. Metadata only: proven byte-identical with the stamp stripped,
and no scoring module may read it (battery, 8 checks, 3 sabotages).

⚠ It surfaced that the NEW POOLS ARE BEING CHOSEN: `test_origin_pools`' "exposure
is zero" went red because the re-cert let the solver pick them, and **both
follow-up supersedes did** (Defender Rad_Emission → Freerunning, Brute Spines →
Nano Net). Exposure 0 → 2. Check updated to pin the truth.

## STILL OPEN (all Joel's, none blocking)
`mez_in` · the stack-meter scenario constant · a spawn RANK MIX (would let the
crits take the 0.10 branch instead of the 0.05 floor) · a Brute farm log with 3+
single-target attacks for Fury · Fiery Embrace's Fire-typed-vs-global question
(zero champion exposure, so it blocks nothing).

---

# ⏳ FOLLOW-UP WAVE RUNNING - 2026-08-09 21:29 ET, the 5 the first wave missed

## IF THE SESSION DIED, READ THIS FIRST
**5 contexts are re-converging.** Launched detached 21:29:40 (task since
unregistered); orchestrator + 5 workers, ONE context each.
⚠ **champions.json and the shards belong to that process until it exits.**

- launcher `Run V44 Followup Wave.bat` · orchestrator log `wave_v44b.log`
- workers `champions_shard_v44b_p0..p4.log` · shards `champions_shard_v44b_p*.json`
- `--recert --workers 5 --shard-prefix champions_shard_v44b`, node cap 50000,
  **NO --merge**

### The five, and why they were missed
```
  Spines/Fiery_Aura [farm_afk]        375.9 ->  227.6   (-148.3)
  Radiation_Emission/Sonic_Attack    1644.2 -> 1739.0    (+94.8)
  Umbral_Blast/Umbral_Aura [base]    1452.6 -> 1361.7    (-90.9)
  Demon_Summoning/Radiation_Emission 1275.8 -> 1330.7    (+54.9)
  Plant_Control/Poison               1808.1 -> 1773.2    (-34.9)
```
The first wave was scoped by "does the build HOLD a patched power?" - which is
SUFFICIENT but not NECESSARY. v42's RechargeTime fix reaches timed PET uptime
(the Mastermind, the farm build) and scenario channels move scores with no
patched power picked. **The right scope test is an evaluate-first pass BEFORE
the wave, taking the movers.** Use that next time.

### When it finishes
1. `recert_verdicts champions_shard_v44b_p0..p4.json` in ONE invocation (it
   overwrites its output per run). ⚠ This will OVERWRITE recert_verdicts.json,
   which currently holds the first wave's 19 - that one is already merged and
   committed at `306370bb`, so losing it is harmless, but know it.
2. ⚠ Check legality by hand - the verdict log never mentions it and silence is
   not proof. `_picks_legal` over challengers AND standing incumbents.
3. Table to Joel. **No merge without his word.** Then merge by context with
   `--verdicts`, retire the shards, validate, evaluate_first --write.

## ALREADY DONE THIS SESSION
First wave merged at `306370bb`: 19 contexts, 8 supersede / 11 keep, roster 24,
24/24 SERVED, 24/24 legal, all canonical scores fresh. Shards retired.

---

# Resume point - 2026-08-09, WAVE MERGED - and I under-scoped it by 5 contexts

## STATE
HEAD `306370bb`. Nothing running. Data **2026.1.1242**, **model v44**.
Roster **24 contexts, 24/24 SERVED, 24/24 legal**, all canonical scores fresh.
Wave: 19 of 24 re-converged, 880.6 min, 6 workers rc=0, **8 supersede / 11 keep**,
merged on Joel's word. Shards retired `.merged_2026-08-09`.

## ⚠⚠ THE THING TO FIX NEXT: MY WAVE SCOPE WAS WRONG
I scoped the wave by asking **"does this build HOLD a power carrying a new
row?"** (DDR / slow-resist / mode / crit) plus Dominators, and got 19. Then
`evaluate_first --write` reported **16 canonical scores moved, and FIVE of them
were contexts I had excluded**:

```
  Spines/Fiery_Aura [farm_afk]        375.9 ->  227.6   (-148.3)
  Radiation_Emission/Sonic_Attack    1644.2 -> 1739.0    (+94.8)
  Umbral_Blast/Umbral_Aura [base]    1452.6 -> 1361.7    (-90.9)
  Demon_Summoning/Radiation_Emission 1275.8 -> 1330.7    (+54.9)
  Plant_Control/Poison               1808.1 -> 1773.2    (-34.9)
```

**Why the test was wrong:** a term does not have to sit on a power the build
HOLDS in order to move its score. v42's RechargeTime fix reaches **timed PET
uptime** - which is why the Mastermind and the farm build moved - and scenario
and team-buff channels move scores without any patched power being picked.
**Holding a patched power is sufficient, not necessary.** The right scope test
is an evaluate-first pass BEFORE the wave: re-score every context under the new
model and take the movers. That is what `evaluate_first` is for, and I used it
afterwards instead of first.

⚠ Consequence: those five now have a REFRESHED canonical but a build that was
optimised under an older model and never re-converged. The eleven KEEPs are
fine - they were re-converged and the challenger honestly lost.

**A small follow-up wave of those 5 is owed. NOT started - Joel's call.**

## VERDICT SUMMARY
8 supersede: Battle_Axe/FA +314.5 · PB dwarf +256.4 · PB triform +160.5 ·
WS nova +136.5 · Poison/Sonic +120.4 · WS dwarf +89.3 · Water/Kin +54.1 ·
Invuln/SS +13.1. Supersedes again CONCENTRATE in Kheldian form-locked contexts.
⚠ The v43/v44 targets all KEEP - Dominator -385.1, Stalker -344.3, Scrapper
-198.3. The new terms did not produce better builds.

## WHAT I VERIFIED BY HAND (the verdict log does not say)
Legality: ran `_picks_legal` over all 19 challengers and 11 standing incumbents
- **zero illegal**. Silence in a log is not proof, and this is the exact failure
that shipped 8 unbuildable champions in 0.12.30.

---

# ⏳ A WAVE IS RUNNING - 2026-08-09 04:45 ET, v43+v44 re-certification

## IF YOU ARE READING THIS AND THE SESSION DIED, READ THIS BLOCK FIRST
**19 of 24 contexts are re-converging RIGHT NOW.** Launched detached at
**04:45:45** via a scheduled task (since unregistered); orchestrator + 6 workers.
⚠ **champions.json and every shard belong to THAT process until it exits** - no
`git add -A`, no checkout, no merge.

- launcher: `Run V44 Recert Wave.bat` · orchestrator log: `wave_v44.log`
- worker logs: `champions_shard_v44_p0..p5.log` · shards: `champions_shard_v44_p*.json`
- flags: `--recert --workers 6 --shard-prefix champions_shard_v44`, node cap 50000,
  **NO --merge** (deliberate - verdicts first, then Joel's word)
- estimated finish **~11:00-12:00 ET** (worker 5 holds PB triform, the 261-minute
  context; the others are median ~77)

### To check on it
`tail champions_shard_v44_p*.log` - each `[Nm]` marker is one context finishing.
Confirm progress with TWO snapshots, never one.

### When it finishes, in this order
1. ~~Retire the stale root shards~~ **DONE 2026-08-09 08:15, mid-wave**
   (`12ce6647`). 30 renamed to `*.retired_2026-08-09`; shards shadowing an
   owed key at a future launch went **26 -> 0**. Safe mid-wave for two
   independent reasons, both checked: `buildout_champions` globs every root
   shard BUT under `--recert` discards the result and rebuilds the skip set
   from its own shard alone, and the glob runs once at startup hours earlier.
   Verified after: 7 processes alive, logs still advancing on two snapshots.
   ✅ **The v34 orphan is EXPLAINED and now retired too** (suffix
   `.retired_2026-08-09_dropped_scenario`). `champions_shard_v34_p0.json` held
   `Class_Brute|Radiation_Melee|Fiery_Aura|farm_active` - a CONVERGED champion
   for a content type **the roster no longer carries at all**: there are zero
   `farm_active` contexts in champions.json, and the only Brutes certified are
   Battle_Axe/itrial and Spines/farm_afk. Its `canonical_score` was never
   evaluated and the model has moved v34 -> v44, so nothing was lost. ⚠ It was
   still a shadow hazard in its own way: a future `--pending` run would have
   read it as "farm_active is certified" when the roster does not certify it.
   Held back one round on purpose so the reason could be established rather
   than swept - the file is renamed, never deleted.
   ⚠ KEPT: the 3 `champions_shard_e_gt_*` ground truths (never merged, belong
   in the union) and the live `champions_shard_v44_p*`.
2. `recert_verdicts` / `evaluate_first` per context. ⚠ recert_verdicts OVERWRITES
   its output per invocation - regenerate COMPLETE before any merge.
3. **Verdict table to Joel. Do not merge without his word.** Then merge BY
   CONTEXT with `--verdicts`, keep the canonical winner, retire the shards.

## WHY THESE 19
Measured, not assumed: the union of every context holding a power touched by
v40 slow-resist (8), v41 DDR (9), v42's RechargeTime fix (17), v43 Domination
(1) and v44 crits (2). The other **5 are owed nothing** and their incumbents
stand: Spines/FA farm_afk, Plant/Poison, Rad_Emission/Sonic, Demon/Rad, and the
base Warshade itrial.

## PRE-FLIGHT THAT WAS RUN (all green)
prereq gate 477/477 · 12 batteries · 7 reality checks/audits · zero live workers
· **Fiery Embrace exposure measured at ZERO**, so the one open correctness
question (its Fire-typed buff vs our type-blind global) does not block this.
⚠ Laptop-only, and that is a justified idle rather than a silent one: the gaming
box has written **no heartbeat since 2026-07-29** and its last order was
withdrawn, so there is no healthy worker to split to.

---

# Resume point - 2026-08-09 (latest), v44 crits - the mode/meter class is done

## STATE
HEAD `e3362892` pushed. Nothing running. Data **2026.1.1242**, **model v44**.
⚠⚠ **THREE CONTEXTS OWE A RE-CERT AND NONE IS STARTED** - the Dominator (v43),
and the Scrapper Broad_Sword/SR + Stalker Rad_Melee/Dark_Armor (v44). All three
are already inside the existing **20 of 24** v39/v40 union, so the wave is not
bigger, just more overdue. **Joel's call.**

## v44 CRITS
A crit adds **100% of the attack's own damage** - the crit row IS the base row -
at **0.05 vs a minion, 0.10 above**. 253 rows on 247 powers. **The FLOOR is
taken**: crediting the 0.10 needs a spawn rank mix and no scenario carries one.
⚠⚠ Three leaks, each caught by measuring: **a chance of 1.0 is not a die roll**
(StealthCrit = the guaranteed crit while HIDDEN); **pet/redirect records carry
the tags** but a pet does not crit as its owner; and ⚠⚠ **`Epic.*` records are
SHARED across archetypes**, so a first pass gave crits to Defenders, Tankers and
Kheldians through epic picks - exposure 14 of 24 until restricted, then 2.
⚠ The invariance guard REFUSED to write while the baseline still held the last
pass's rows; that failure is the only reason the over-broad data did not ship.

## ⚠⚠ THREE STALE 'BLOCKED' NOTES CAUGHT IN ONE ARC
The self +damage buff was already landed; Defiance's templates are NOT all
scale 0.0; and **Containment has been modelled since v36** (grounded from the
paired templates, weighted by `ctrl_land` - which IS the mezzed-target share it
was supposedly waiting on). All three were written as conclusions rather than
measurements. **Re-measure any pinned "blocked" claim before quoting it.**

## THE MODE/METER CLASS, FINAL STATE
Done: the 47-tag classification (hard-fails both ways) · the self +damage buff
(already there) · Domination's duration half (v43) · the crits (v44) ·
Containment (already there, now correctly labelled DERIVED).

Left, each naming its input:
1. **The stack meters** (23 groups): Static, Frenzy, Contaminated, Disintegrate,
   Energy Focus, the combo systems, Bio's stance. One scenario constant each or
   one ruling for the class - **Joel's, the `mez_in` family**.
2. **The crit premium above the floor** - needs a spawn RANK MIX, which would
   sharpen other terms too. The single highest-value scenario input now.
3. **Domination's magnitude half** - ambiguous in the client, 3 of 41 pairs fit
   neither reading.
4. ⚠ **Fiery Embrace** - the client's buff is **Fire-TYPED** while our engine
   folds every DamageBuff into one type-blind global. Measure before touching;
   adding the Fire templates first is the 2026-08-06 inflation trap.

## STILL BLOCKED ON JOEL
`mez_in` · the stack-meter constant · a spawn rank mix · a Brute farm log with
3+ single-target attacks for Fury · whether to run the 3-context re-cert.

---

# Resume point - 2026-08-09, v43 Domination shipped

## STATE
HEAD `4fc76239`. Nothing running. Data **2026.1.1242**, **model v43**.
⚠ **A RE-CERT IS OWED FOR 1 OF 24 CONTEXTS** — `Class_Dominator|Mind_Control|
Fiery_Assault|itrial`. **NOT STARTED; Joel's call.** The v39/v40 re-cert union
is still 20 of 24 and this does not widen it (the Dominator is already in it).

## v43 DOMINATION
Size stated twice by the game: the inherent's help says control powers "will
typically last 50 percent longer", and **41 of 41** encoded client pairs carry
exactly **1.5x** the base duration scale. Uptime from the inherent's own
numbers: a **90s Set_Mode on a 200s recharge**, floor 45%, reaching 1.0 at
**+122% global recharge** - the perma-dom threshold players build to, and
capped there. Measured: control output **999.5 -> 1211.3** at no recharge,
**-> 1423.1** at +100%.

⚠⚠ **UNIVERSAL, NOT PER ENCODED POWER.** The client writes variant rows on only
**12 of 26** Dominator sets - Plant's Strangler has one, Mind's identical
Dominate does not. Encoding asymmetry, not a game one. Pricing only the encoded
12 would bias the solver toward those sets. Rides the existing `mez_dur`
channel, so there is one mechanism rather than two.

⚠ **The MAGNITUDE half is deliberately NOT credited.** Whether the variant's
magnitude adds to the base (doubling a mag-3 hold) or replaces it is ambiguous
in the client and **3 of 41 pairs fit neither**. Too big to infer. If anyone
settles it, that is a second model bump and a wider re-cert.

## WHAT IS LEFT IN THE MODE/METER CLASS
1. **The stack meters + Containment** (144 groups): one scenario constant each,
   or one ruling for the class. Joel's, the `mez_in` family.
2. **The crits** (453 PROB groups): the chance is stated PER TARGET RANK, so
   the missing input is the encounter's rank mix. Understates every Scrapper.
3. ⚠ **FieryEmbrace** (305 groups): the client's buff is **Fire-TYPED** while
   our engine folds every DamageBuff into one type-blind global. Measure before
   touching; adding the Fire templates first is the 2026-08-06 inflation trap.

## STILL BLOCKED ON JOEL
`mez_in` and the stack-meter scenario input - a Brute farm log with 3+
single-target attacks for Fury - and whether to run the owed 1-context re-cert.

---

# Resume point - 2026-08-09, the mode/meter capability is classified

## STATE
HEAD `6186fbee` pushed. Nothing running. Data **2026.1.1242**, model **v42**
unchanged, **re-cert union 20 of 24**. Champion exposure zero this pass.

## THE CAPABILITY IS THE CLASSIFICATION
`tools/mode_tags.py` adjudicates all **47** tags that reach a scored group of a
power we carry, each with its evidence; `reality_check_mode_tags.py` hard-fails
both ways (unadjudicated tag, or a stale entry). Five classes: **LABEL 22 ·
PROB 14 · MODE 4 · SCENARIO 6 · DERIVED 1**.

⚠⚠ **A TAG IS NOT AUTOMATICALLY A GATE, and assuming so was a live bug I
shipped yesterday.** Skipping every tagged group is right for FieryEmbrace and
wrong for `FireBlastBonusDoT`, the client's own name for Blaze's Fire DoT.
**Three mechanical tests were tried and each got some of the 48 wrong in BOTH
directions** - PowerBoostA gates but names no mode or power; `Damage` and
`Taunt` name real powers but are labels. Hence a hand-adjudicated table.

## ✅ THE BIGGEST ITEM WAS ALREADY DONE - THE ENTRY WAS STALE
"The self +damage buff is missing from the entire Build-Up class, OPEN, owes a
re-cert" has been in CLAUDE.md since 2026-08-07. **It is landed:** 275 powers
carry a self `DamageBuff` row with the game's own duration and recharge, and
through the real route **Build Up moves damage_buff 0 -> 0.1111 and ST DPS
14.4 -> 16.0**. ⚠ The "0.0" behind that entry came from a probe that added
`Scrapper_Melee.Martial_Arts.Build_Up`, **a full_name that does not exist**. I
repeated the mistake today before catching it. **Assert the record RESOLVED
before believing a zero.** No re-cert is owed and none ever was.

## WHAT IS LEFT IN THE CLASS, each naming its missing input
1. **The stack meters + Containment** (144 groups): BuildStatic, BuildFrenzy,
   Contaminated, Disintegrate, EnergyRelease, ComboBuild, Perfection x3, Bio
   adaptation. One scenario constant each, or one ruling for the class -
   **Joel's, the `mez_in` family.**
2. **Domination** (87 groups): the duty cycle IS derivable (client-stated 90s
   on a 200s recharge) but it multiplies CONTROL magnitude and `role_output`
   has no mode path. An engine change that moves Dominator champions, so it
   wants its own measured pass.
3. **The crits** (453 PROB groups): the chance is stated PER TARGET RANK, so
   the missing input is the encounter's rank mix, not the chance. Dropped
   today by the targeting/condition rule - honest, but it understates every
   Scrapper and Stalker.
4. ⚠ **FieryEmbrace (305 groups) hides a real question.** The client's Fiery
   Embrace grants `Fire_Dmg` at aspect Strength - a **Fire-TYPED** buff - and
   our engine folds every `DamageBuff` into one type-blind global. So it
   currently raises ALL damage at an 11.1% duty cycle while the game adds Fire
   components and boosts those. **Do not add the Fire templates** until the
   type question is measured; that is the 2026-08-06 inflation trap.

## ALSO CORRECTED
Defiance's templates are **not** all scale 0.0 - 25 distinct scales up to 0.176
- so the DERIVED skip prevents a real double-count rather than being a
formality. Two Wind Control checks that had been passing for the wrong reason
were rewritten to pin what is measured (battery back to 23).

## STILL BLOCKED ON JOEL, unchanged
`mez_in` · a Brute farm log with 3+ single-target attacks for Fury · the
re-cert wave (21 contexts: 13 for v39, 8 for v40) is NOT started.

---

# Resume point - 2026-08-08, both origin pools SHIPPED + the mode gate found

## STATE
HEAD pushed, tracked tree clean. Nothing running. Data **2026.1.1242**, models
**v39-v42** unchanged, **re-cert union 20 of 24** - nothing this pass moved a
score, and all 24 certified builds remain legal.

## GADGETRY AND UTILITY BELT ARE IN (`22b7be2f`)
The last two absences the missing-powers check was pinning. **10 pickable powers,
served to all 15 archetypes**, prerequisites read from the game's own requires
expression and enforced by `_picks_legal`. `reality_check_missing_powers` now
reads **0 genuinely absent** - every client power we lack is renamed, filed
elsewhere, never-pickable, or an `_Aux` variant, each accounted for.

⚠ Turbo Boost and Athletics are ABSENT ON PURPOSE (auto-issue sentinel, the
`Fly_Boost` ruling). ⚠ Jetpack's archetype bar (Peacebringer, Warshade) is
RECORDED and reported - the tool has no per-power archetype gate for pools.
⚠ The one-origin-pool rule is **not in any `requires` expression** (checked);
it is server-side and unverifiable from the bins. Battery
`tools/test_origin_pools.py` - 32 checks, 7 sabotages, all caught.

## ⚠⚠ THE BIG ONE: `tags` IS THE CLIENT'S MODE GATE, AND IT ALWAYS WAS
This project has recorded since 2026-08-06 that the crawler was **not capturing**
the Fiery Embrace gate. **That was wrong.** The gate is an effect-group field
nothing had read: **349 groups on 342 powers carry `tags: ["FieryEmbrace"]`**,
and the same field carries **Containment 119 · Domination 90 · Overpower 86 ·
Defiance 33 · PowerBoostA/B · the Scrapper crit trio** and ~150 more.

**Why it matters beyond today:** the whole mode/meter capability - Fury, Rage,
Domination, Power Boost, the self +damage buff class - now has a **mechanical
roster**. Whoever starts that work no longer has to find the affected powers.
The tag names the mode; it does NOT give the uptime, and uptime was always the
part needing Joel's ruling.

## ⚠⚠ WIND CONTROL SHIPPED INFLATED THIS MORNING, AND IS CORRECTED
The pools exposed it: the client writes an attack's damage **once per archetype
and again per game state**, so Wrist Blaster carries **23 damage groups for one
attack**. Testing for `critter`/`player` alone let all 22 variants through -
they name `critter`/`player` too. Two rules now, both measured corpus-wide:

1. **A tagged group is skipped and counted** (see above).
2. **Targeting is not a condition.** Strike out the pure-targeting clauses
   (`enttype target>`, `entref target.owner>`, `target.isFriend?`, operators)
   and **5,123 of 7,323** expression-carrying groups reduce to nothing; every
   residue is a real condition (archetype, `kMeter`, `Source.Mode?`, `rand`).

⚠ **`chance: 0.0` means UNSET, not never** - the crawler writes 0.0 for an
absent field. Poisoned Dagger's -DMG reads 0.0 while the game's help states it.

Result: 18 Wind Control row-sets changed, all downward. **Vacuum's Lethal DoT
drops to zero** - the game gates it on 6 stacks of the set's own Pressure
mechanic - and that is REPORTED per power, never silently dropped.
⚠ Its battery had a check passing for the WRONG REASON (it compared Controller
against Dominator and found a difference that WAS the mode group). Rewritten.

## ⚠⚠ AUTOPICK WAS PROPOSING ILLEGAL BUILDS - 61 of 2,721
`place()` filtered twins from **a hand-written list of two pairs** while our
records mark **thirteen**, so Broad Sword proposals held Slice and Boomerang
Slice together on 43 combos. `_picks_legal` and the validator had already been
generalised to read `excludes`; autopick had not. Built from the data now.

⚠⚠ **Fixing it EXPOSED a latent second defect.** The creation-pick fallback
seats "the better-scoring of the set's first two", and **first-two-by-tier is
not available-at-level-1**: Fortunata Teamwork's second is **Mask Presence at
level 20**, which out-scored Fate Sealed and was seated into the LEVEL-1 slot.
Every Fortunata proposal was unbuildable. Measured three ways: HEAD 61 · twin
fix alone 1 · both fixes **2,721 of 2,721 legal**. The audit gained a check that
states the actual rule (a pick level must be >= the power's `level_available`),
so the next set shaped that way is NAMED rather than showing up as a symptom.

## SMALLER, EACH WITH ITS EVIDENCE
- `min_others` gained **the mirror of a rule it already had**: a NEGATED
  archetype gate swaps the polarities but not the question. One expression
  reclassified (Jetpack), count 0 either way, **zero data change** (proven by
  running the patcher: 0 changed). Prereq gate **477 of 477 agree**.
- `reality_check_powers` re-pinned **52 -> 43**. Measured **stale at HEAD**, not
  moved by this work; the nine left when the alias map gained its display-name
  rung. ⚠ The pin is two-way: a shrink is as much a signal as a growth.
- `Ninja_Run` dispositioned in the coverage check (v30 movement exclusion) - it
  entered scope only when the pools landed. **Every family classified.**
- Life Support System's heal-over-time is decoded from the client's own RPN at
  the **full-health floor** and multiplied by its 9 ticks, because a heal row
  carries no duration and `role_output` divides by recharge. The game says
  potency rises as health falls; crediting that needs a scenario nobody ruled.

## WHAT IS OPEN
- **Blocked on Joel, unchanged:** `mez_in` (the mez term is built and proven but
  inert without it) and a Brute farm log with 3+ single-target attacks for Fury.
- **The re-cert wave has NOT been started** and must not be until the scope is
  settled: **21 contexts** (13 for v39, 8 for v40). Nothing today widened it.
- The mode/meter capability, now with a roster (see `tags` above).

---
# Resume point - 2026-08-08, Wind Control SHIPPED + all issues closed

## STATE
HEAD pushed, tracked tree clean. Nothing running. Data **2026.1.1242**, models
**v39-v42**, **re-cert union 20 of 24** - nothing this pass moved a score.

## WIND CONTROL IS IN (`982a8572`, `343d028d`)
A whole shipping powerset the tool could not plan: **20 records across Controller
and Dominator, offered in the app, priced end to end including the pets** (the
Vortex pet reads 7.6 DPS). Everything from the game client; every mapping
measured against powers we already hold. **No wiki was used for any of it.**

⚠⚠ **`targets_affected` IS THE SIDE, NOT `target_type`.** Thundergust and Wind
Shear are both `target_type: Self` - meaning *centred on you* - and land entirely
on FOES. Reading target_type would have written a cone attack's damage as a self
buff. The generator refused until this was right.

⚠ **Clear Skies carries nothing on purpose** - every effect is gated on
`kClearSkies Source.Mode?`, the mode class. Pickable, unpriced, stated.

⚠ **Joel's ruling applied**: Controller and Dominator share the Vortex entity.

## CONTROL DRIFT CLOSED, GAME-FIRST (`70f97249`)
Our control encoding agreed with the client on 539 powers and **disagreed on 29**.
25 synced (the game wins): ten epic holds read 12.0 where the game says 10.0,
four Electric Shackles 8.0 -> 10.0, Hymn of Dissonance magnitude 1 -> 3, and
**Telekinesis was recorded as a HOLD when the game says "Foe Immobilize"**.
⚠ Four left alone and reported - Synaptic Overload, Cryo Freeze Ray, EM Pulse and
Seismic Smash are multi-row ENCODINGS, not wrong values, and collapsing one is a
different question from correcting a number. ✓ Exposure zero of 24.

## THE 269 UNRESOLVED SUMMONS: NOT A DEFECT
Pricing reads the SPEC, which carries uid/count/class inline (197 of the 234
distinct uids have one), so the entity map is metadata rather than a pricing
input. The one case drivable end to end (Shadow Field) produces no pet damage
because its pseudo-pet genuinely has none.

## ⚠⚠ A TRAP THAT COST 17 MB, AND THE FIX
**`open(path, "wb").write(expr)` TRUNCATES BEFORE IT EVALUATES `expr`.** A
NameError in that expression emptied `powers.json` to zero bytes. Recovered
whole from git plus the tools - every change since the last commit is generated -
but the writers build all bytes first and only then open anything.
⚠ Related: **match each file's own serialisation.** powers.json and summons.json
are compact single-line; **powersets.json is indent=1 with CRLF**, and writing it
compact turned a two-entry addition into a 3,102-line diff. Fixed in `343d028d`.

## STILL ABSENT (2 pins)
`Pool.Gadgetry` (6) and `Pool.Utility_Belt` (6). Same record-synthesis path Wind
Control just proved twice; no blockers known.

# Resume point - 2026-08-08 (latest), Wind Control specified, not built

## STATE
HEAD pushed, tracked tree clean. Nothing running. Data **2026.1.1242**, models
**v39-v42**, **re-cert union 20 of 24**. No data changed this pass.

## WHAT THIS PASS DID (`09d24a0d`) - and what it deliberately did NOT
Wind Control is 10 powers x 2 archetypes the tool cannot plan. **Every mapping
is now pinned and measured** (`docs/wind-control-spec.md`), so the build is
mechanical. I stopped before building, and not for effort:

- `level_available` = client **+1** (5,478 of 5,589 matched powers agree)
- control encoding: client `scale`->our `scale`, client `magnitude`->our `nmag`,
  critter group -> `pv_mode 1` — **539 powers agree**, 29 do not (see below)
- control `kind`: hard/soft **by mez name**, unanimous across every existing row
- set categories by name + TWO aliases derived from powers we already hold:
  "Universal Damage Sets"->"Universal Damage" (1,128x), "Ranged AoE
  Damage"->"Targeted AoE Damage" (452x)
- summons resolve by **normalising underscores** (client
  `Pets_WindControl_Vacuum_Controller` = our `Pets_Wind_Control_Vacuum_Controller`);
  570 exact + 7 via normalisation. **The pet entities already exist.**
- damage from templates AND `child_effects` (the Boomerang Slice pattern)

## ⚠ THE TWO THINGS THAT STOPPED IT — the first is Joel's
1. **The Controller's Vortex pet.** The client has TWO entity defs
   (`Pets_WindControl_Vortex_Controller` and `Pets_WindControl_Vortex`); our
   data has ONE. Sharing one across Controller and Dominator is a documented
   pattern here (v26 says so), so it is probably right - but it is an assumption
   about the game on a **TIER 9**, and this project rules on those.
2. **Exposing a powerset is a bigger act than any data patch.** Adding it to
   `powersets.json` makes it selectable: the solver will optimise into it and a
   player will trust the numbers. **A mis-priced set is worse than an absent
   one**, so that switch gets flipped deliberately, not as a side effect.

## TWO FINDINGS THAT FELL OUT (pre-existing, unrelated to Wind Control)
- **29 control powers we ALREADY SHIP disagree with the client** on (mez, scale,
  magnitude): Hymn of Dissonance reads mag 1 where the client says 3, Entangle
  4 vs 3, Synaptic Overload's whole ladder is shifted. Deserves its own pass.
- **269 of our `summons[]` entries resolve to no entity** in summons.json.
  Mostly pseudo-pets (`PL_StaticObject`), never classified.

# Resume point - 2026-08-08 (latest), Boomerang Slice + the legality hole

## STATE
HEAD pushed, tracked tree clean. Nothing running. Data **2026.1.1242**, models
**v39-v42**, **re-cert union 20 of 24** (no score moved this pass).

## WHAT THIS PASS DID (`35c97c6f`)
**⚠⚠ THE TOOL ALLOWED BUILDS THE GAME REFUSES.** Boomerang Slice is mutually
exclusive with Slice, so I checked how we enforce that - and **nine pairs were
already in our data on both sides**, with nothing stopping a user OR A
CERTIFICATION WAVE from taking both: **Dark Regeneration <-> Obscure Sustenance
on five archetypes**, Master Brawler <-> Practiced Brawler, the Widow's Build Up
<-> Follow Up, and two VEAT grenade pairs. `validate_build` raised nothing and
`_picks_legal` knew about TWO of the nine, hand-typed as
`_VEAT_DUPLICATE_PAIRS`. Same class as 0.12.30's eight illegal champions.
✓ Exposure counted first: **zero of 24** hold both sides. Fixed at the source -
13 client-derived mirrored pairs, the validator names the pair, and the gate
reads the data instead of the hand-list.

**BOOMERANG SLICE ADDED** - a real level-1 Broad Sword attack on four
archetypes, the only whole power the audit found missing. Client for what the
power IS, sibling Slice for the app-schema fields (the client says both accept
identical categories and boosts). Live: **40.7 damage, 1.83s cast, cone**,
served at level 2 beside Slice and refusing to coexist with it.

## TRAPS FROM THIS PASS
- **⚠⚠ `child_effects` IS A LEVEL NOBODY HAD READ.** Boomerang Slice's damage
  groups look EMPTY at the top level; the damage hangs one level down. This
  nearly ended as "the client has no damage for it". **Second time today** a
  field existed and no probe had descended into it (the first was
  `magnitude_expression`) - treat an empty-looking group as UNREAD, not empty.
- **⚠ `available_level` is 0-BASED, ours is 1-based** (5,478 of 5,589 agree).
- **⚠ A SABOTAGE THAT MATTERED:** "adding the partner makes it illegal" PASSED
  with the exclusion rule deleted, because a 25th pick breaks the ladder cap on
  its own. The check SWAPS a pick now, so only the exclusion can refuse it.
- **⚠ The 15s Rending Slice bonus is NOT priced** (gated on a Set_Mode, the
  meter class) - the power is understated rather than guessed at.

## ONE CONSEQUENCE TO STATE
No certified score moves, but the ONE Broad Sword context can now re-pick into
Boomerang Slice, so a future wave may legitimately choose it over Slice. That is
the search space widening, not a number changing.

## STILL ABSENT (pins down to 4)
Wind Control (Controller + Dominator, 20 powers), Pool.Gadgetry (6),
Pool.Utility_Belt (6). The app does not offer them, so nothing is broken on
screen. Adding them is the same record-synthesis path Boomerang Slice just
proved out - **a known-cost job now rather than an unknown one**, and Joel's
call whether it is worth it.

# Resume point - 2026-08-08 (latest), the missing-powers retraction

## STATE
HEAD pushed, tracked tree clean. Nothing running. Data **2026.1.1242**, models
**v39-v42**, **re-cert union 20 of 24**. This pass changed no data.

## ⚠⚠ RETRACTION, and it is the important part (`0f585868`)
The previous handoff said **"459 client player powers absent, including whole
shipping powersets - Wind Control, Shock Therapy, Blaster Time Manipulation,
Gadgetry"**. Two of those four are WRONG:

- **Shock Therapy IS in the tool** - it is our **Electrical Affinity** (display
  roster match 1.0, all 9 powers).
- **Blaster Time Manipulation IS in the tool** - our **Temporal Manipulation**.
- **19 powersets are RENAMED, not missing**, all at roster 1.0, including
  `Pool.Fitness` = `Inherent.Fitness` and 13 Epic sets already on the bridge.

The three-namespaces rule, walked into while writing up a different finding.
**A raw set difference is not a measurement.**

## WHAT IS ACTUALLY ABSENT: 32 powers
- **Wind Control** (Controller + Dominator, 10 each) - a shipping set the tool
  cannot plan; we hold its pet and none of its player powers.
- **Pool.Gadgetry** (6) and **Pool.Utility_Belt** (6) - two whole pools.
- **Boomerang Slice** (4 records) - a real level-1 Broad Sword attack in a set
  we have. The only single-power absence in the whole sweep.

⚠ **The app does not OFFER any of the three sets** (powersets.json has none of
them), so nothing is broken on screen - a player simply cannot plan them. Honest
absence, not a defect. Adding them means synthesising records from the client
(effects, scales, slotting categories, icons, pick levels), which is a new
pipeline rather than an additive patcher. **Joel's call whether it is worth it.**

Accounted for and printed rather than counted as missing: 24 namespace
differences (Kheldian forms live under `Inherent` for us), 6 never-pickable
auto-issue powers, 15 `_Aux` redirect variants, and pet records.

## THE NEW CHECK TIES INTO PATCH-WATCH
`reality_check_missing_powers.py` answers, after any client re-export, **what is
genuinely new versus what merely moved name** - the exact question a Homecoming
patch raises and the one I just got wrong by hand. Add it to the PATCH-WATCH
step list.

## OPEN - JOEL'S, three questions, each one number or one call
1. **`mez_in`** - unblocks 289 powers (self mez 229, ally mez 29, four
   debuff-resistance families 31).
2. **An operating health** for the 13 health-scaling powers. Recommended **50%**
   (these curves are linear in health; a linear curve's average over the bar is
   its midpoint - derived, not invented).
3. **Wind Control / Gadgetry / Utility Belt** - worth a records pipeline or not?
4. **Fury** - still a Brute farm log with 3+ single-target attacks.

## OPEN - MINE
- The ally channel (ally mez + ally absorb + ally slow resist, built once).
- Data-only once a branch exists: +Accuracy on Combat Training: Offensive x2,
  EnduranceDiscount on Conserve Power x6, Field Medic's +Heal strength.
- Power Boost `Set_Mode` (143) · gated-only powers (8) · ~460 cap/radius rows ·
  knockback protection · the Fighting-pool cross-boost · Boomerang Slice.

# Resume point - 2026-08-08 (latest), health-scaling decoded

## STATE
HEAD pushed, tracked tree clean. Nothing running, nothing scheduled. Data
**2026.1.1242**. Models **v39-v42**. **Re-cert union stays 20 of 24** - champion
exposure on today's last two passes is zero.

## WHAT THIS PASS DID (`a2451a1b`)
**⚠⚠ THE MAGNITUDE IS NOT ALWAYS IN THE SCALE.** Every client template carries a
`magnitude_expression` in RPN and for 226 player powers that is where the real
number lives. Ablative Carapace's is `Max.kHitPoints source> 0.3 * @Strength *`
= **30% of max HP** - which is why its scale is a bare 1.0 and why I pinned it
as "units unknown" last pass. It was never unknown; nobody had read the field.

- **MAX-HP-PROPORTIONAL (10 powers): landed, no ruling needed.** Ablative
  Carapace 30% of max HP x5, Parasitic Aura 10% x4, Parasitic Leech 14.3%.
  Measured: Scrapper **401.7 HP** of 1339, Tanker **562.2** of 1874. Bio Armor's
  whole absorb sustain existed nowhere before today.
- **HEALTH-DEPENDENT (13 powers): decoded, PINNED, one number away.** SR's
  scaling resistance = 20% at zero HP falling to 0% at 60%; Gamma Boost's regen
  and recovery run in OPPOSITE directions off the same bar. See the ask below.
- **⚠ Computed against BASE hp**, never the boosted pool - `totals["max_hp"]` is
  still accumulating in that loop and reading it would make the answer depend on
  power order (the v39 recharge rule again).

## TWO HOLES CLOSED IN THE CHECKER
- **Rule 4 hid a real family.** "A zero-scale template carries no magnitude" was
  written for Defiance - but zero scale PLUS an expression is exactly how SR's
  scaling resistance is stored. It now requires both.
- That surfaced **Defiance's own templates**, which must stay OUT of the data
  (v36 derives them) - a double-count caught within a minute of looking.
  Dispositioned by expression, with the token/meter, distance and
  Fighting-pool-cross-boost classes (Boxing/Kick/Cross Punch boost each other -
  real, unmodelled, now named).

## ⚠⚠ NEW FINDING, DIFFERENT CLASS: 459 CLIENT POWERS WE DO NOT CARRY AT ALL
Whole shipping powersets are absent from our Mids-derived snapshot: **Wind
Control** (Controller + Dominator), **Shock Therapy** (Corruptor, Mastermind,
Controller), **Blaster Time Manipulation**, the **Gadgetry** pool. The tool
cannot plan them at all. **Neither classification check can see this by
construction** - they only compare powers we already have. Joel's call on how to
handle it; it is probably the largest remaining data gap in the project.

## OPEN - JOEL'S, and both are now ONE NUMBER EACH
1. **`mez_in`** - unblocks 289 powers (self mez 229, ally mez 29, the four
   debuff-resistance families 31).
2. **An operating health** for the 13 health-scaling powers. Recommendation:
   **50%**, because these curves are linear in health and a linear curve's
   average over the bar is its midpoint value - derived, not invented.
3. **Fury** - still a Brute farm log with 3+ single-target attacks.

## OPEN - MINE
- The ally channel (build once for ally mez + ally absorb + ally slow resist).
- Data-only once a branch exists: +Accuracy on Combat Training: Offensive x2,
  EnduranceDiscount on Conserve Power x6, Field Medic's +Heal strength.
- Power Boost `Set_Mode` (143) · gated-only powers (8) · ~460 cap/radius rows ·
  knockback protection · the Fighting-pool cross-boost.

# Resume point - 2026-08-08 (latest), the ally side is swept

## STATE
HEAD pushed, tracked tree clean. Nothing running, nothing scheduled. Data
**2026.1.1242**. Models **v39-v42**, none re-certified. **Re-cert union stays
20 of 24** - this pass moved no number, by design.

## WHAT THIS PASS DID (`4e3f68f9`)
**The coverage check only ever tested `target == "Self"`.** Every buff placed on
someone ELSE was invisible to the one instrument built to see everything: 151
Friend-targeted powers, **45 uncarried families**. All classified, residue 0.

**⚠⚠ NO NEW TERM SHIPPED, deliberately.** The ally half of the absorb patcher
was written, measured, and REVERTED: only Insulating Circuit is unambiguous
(Spirit Ward's two groups disagree), and a term for one power no champion holds
is not worth building before the ally channel is built properly for the 29 mez
powers that need the same channel.

## ⚠ THE `mez_in` ASK IS NOW THE HIGHEST-LEVERAGE THING IN THE QUEUE
One ruling unblocks **289 powers across three families that score nothing
today**: self mez protection (229, built and inert), **ally mez protection +
resistance (29 - Clear Mind, Clarity, Thaw, Increase Density, Shadow Fall; the
biggest support gap in the tool)**, and the four debuff-resistance families (31).

## TRAPS FROM THIS PASS
- **⚠⚠ `AnyAffected` IS NOT `ALLY`.** It means whoever the power affects - a
  friend on Clear Mind, the FOES on a Brute cone attack. My first sweep read it
  as a side and called Repulsing Torrent's -damage template a team buff. The
  power's **`target_type`** (Friend/Foe/Self/Location) is the authority. Pins
  are keyed by side now so the two can never be confused.
- **A `Strength` aspect placed on someone else amplifies THEIR OWN effects**
  (Amp Up) and we model no ally's build - a general disposition that retired
  nine would-be pins, not nine coincidences.

## OPEN - MINE, IN ORDER
1. **The ally channel** - build it once, for ally mez (29) + ally absorb (2)
   together, when `mez_in` lands. Ally slow resistance (8) needs the same
   channel: `slow_in` exists but only slows MY damage, never the team's.
2. **Health-scaling effects** (Gamma Boost x5, Agile's scaling resistance, the
   19 `*_Ones` absorb records).
3. Data-only once a branch exists: +Accuracy on Combat Training: Offensive x2,
   EnduranceDiscount on Conserve Power x6, Field Medic's +Heal strength.
4. **Power Boost `Set_Mode`** (143 powers) · the 8 gated-only powers · ~460
   unclassified cap/radius rows · knockback protection.

## OPEN - JOEL'S
- **`mez_in`** - see the leverage note above.
- **Fury** - a Brute farm log with 3+ single-target attacks.

# Resume point - 2026-08-08 (latest), absorb + the dead recharge word

## STATE
HEAD pushed, tracked tree clean. Nothing running, nothing scheduled. Data
**2026.1.1242**. Models **v39 / v40 / v41 / v42**, none re-certified.

## ⚠ THE RE-CERT UNION IS NOW 20 OF 24 (was 17)
Counted from the artifact: v39 mode powers **17** · v41 DDR **9** · timed pets
**8** · v40 slow resist **8** · v42 absorb **0**. The widening is NOT absorb, it
is the recharge-word fix below. One wave over the union, after the queue settles.

## WHAT THIS PASS DID (`fc8e6ead`, `3b0ac15d`)
**1. Absorb is modelled.** 38 powers grant a shield and we carried none of it;
the engine had no branch either. Two totals that must never be added: `absorb`
is the shield SIZE (Scrapper Particle Shielding **401.6 HP**), `absorb_hps` is
what it is WORTH (**3.35 HP/s** = pool ÷ its 120s recharge, because a shield
soaks its pool once per cast). Consumed beside regen and self-heal. Only
heal-table rows taken; 19 `*_Ones` 1.0 records are pinned, not guessed.

**2. ⚠⚠ `Recharge` IS A DEAD WORD - THE ASPECT IS `RechargeTime`.** No piece in
the game carries `Recharge`; 633 carry `RechargeTime`; **three sites asked for
the dead one**, so recharge slotting reached NONE of the v39 mode duty cycle, a
click buff's uptime, or timed pet uptime. Measured with three recharge IOs:
Rage's damage buff **0.40 → 0.796**, Category Five pet DPS **+96.8%**, Auto
Turret **+87.5%**, Lightning Storm **+53.8%**. Found only because the absorb
cadence reused the same spelling and its battery measured no movement.

## TRAPS FROM THIS PASS
- **⚠ The enhance aspect is `Absorb`, not `Heal`.** The client's boosts_allowed
  says Heal, so "Heal" looks right and enhances NOTHING. `Crafted_Heal` boosts
  Heal, HitPoints, Regeneration **and Absorb** - that is the aspect to name.
- **⚠ A click's self rows are dropped from totals**, so an absorb row has to be
  admitted beside the v39 mode buffs or a correct back-fill measures 0.0. That
  is now the THIRD time this session a correct data patch read zero for a
  reason that was not the data (power_type, the click gate, the dead word).
- **✅ Three pins moved and every one FAILED FIRST** - the coverage check's
  Absorb gap, the empty-record check's absorb-no-branch (3 → 2, the survivors
  are ally-targeted), and the DDR battery's `MODEL_VERSION == 41`, which was
  frozen where it should have been `>=`.

## OPEN - MINE, IN ORDER
1. **Ally-targeted buffs have no consumer.** Clear Mind / Clarity ×8 (mez
   protection) and Insulating Circuit / Spirit Ward (absorb) are all blank or
   inert for the same reason: nothing scores a buff placed on someone else.
   One design decision would unblock all ten.
2. **Health-scaling effects** (Gamma Boost ×5, Agile's scaling resistance, the
   19 `*_Ones` absorb records).
3. Data-only once a branch exists: **+Accuracy** on Combat Training: Offensive
   ×2, **EnduranceDiscount** on Conserve Power ×6, **Field Medic's +Heal
   strength**.
4. **Power Boost `Set_Mode`** (143 powers) · the 8 gated-only powers · ~460
   unclassified cap/radius rows · knockback protection.

## OPEN - JOEL'S (unchanged)
- **`mez_in`**, which also blocks ToHit / end-drain / regen / recovery debuff
  resistance (31 powers, all real, all inert without a rate).
- **Fury** - a Brute farm log with 3+ single-target attacks.

# Resume point - 2026-08-08 (later), the empty-record class is classified too

## STATE
HEAD pushed, tracked tree clean. Nothing running, nothing scheduled. Data
**2026.1.1242**. Models **v39 / v40 / v41**, none re-certified. Re-cert union
unchanged at **17 of 24** - this pass added nothing to it.

## WHAT THIS PASS DID (`f7077f5a`)
876 records held ZERO effect rows while the client populated them. **Classified:
632 are not player powers, 210 are plumbing-only, 32 are real and pinned in
seven named gaps, and exactly 2 were a plain data gap.** Both fixed, champion
exposure zero, so no score moved and no model bump.

- **Bo Ryaku** (Ninjitsu) 0 → **7.5% resistance to all eight damage types**.
- **Active Defense on Stalker** → **11.25% melee defence + 11.25% S/L
  resistance** (Brute reads 12.75; that is the archetype column, not a bug).

## THREE TRAPS FROM THIS PASS
- **⚠⚠ THE STUB WAS WRONG IN TWO FIELDS.** Both records also carried
  `power_type: 0` (a click) where the game says "Toggle:" and "Auto:". The
  engine only counts self effects on an auto or toggle, so a CORRECT effect
  back-fill measured 0.0 through the real route. Always check both.
- **⚠ THE FIRST YIELDING GROUP WINS WHOLE**, not row by row: the client's second
  group is the PvP variant and adds vectors (Shield Defense's Psionic defence)
  that our populated siblings keep at pv_mode 2.
- **⚠ GAMMA BOOST IS NOT A BACK-FILL.** The game's help says the regeneration
  and recovery halves are opposite ends of ONE health-scaling curve, so the
  client's flat 1.0/1.0 can never both apply. Writing them would credit +100% of
  each. Same class as Agile's scaling resistance (export carries it at 0.0).

## OPEN - MINE, IN ORDER
1. **Absorb is not modelled anywhere** (no engine branch) - Master Brawler,
   Insulating Circuit, Spirit Ward, Particle Shielding. A term is owed.
2. **Ally mez protection** - Clear Mind / Clarity x8 are blank, so an Empathy
   Defender's signature buff does nothing. Data is easy; **nothing scores mez
   protection on an ALLY**, so it needs the consumer first.
3. **Health-scaling effects** (Gamma Boost x5, Agile's scaling resistance).
4. Small and data-only once a branch exists: **+Accuracy** on Combat Training:
   Offensive x2, **EnduranceDiscount** on Conserve Power x6, **Field Medic's
   +Heal strength**.
5. **Power Boost `Set_Mode`** (143 powers) · the 8 gated-only powers · ~460
   unclassified cap/radius rows · knockback protection.

## OPEN - JOEL'S (unchanged)
- **`mez_in`**, which also blocks ToHit / end-drain / regen / recovery debuff
  resistance (31 powers between them - all real, all inert without a rate).
- **Fury** - a Brute farm log with 3+ single-target attacks.

## THE STANDING CHECKS NOW COVER BOTH CLASSES
`reality_check_effect_coverage.py` (families, 10 gaps pinned) and
`reality_check_empty_records.py` (whole records, 7 gaps pinned). Both pin by
COUNT and fail in BOTH directions. That paid off the same day: fixing the two
records drove ten coverage pins to zero and the check failed on the STALE
entries instead of passing quietly.

# Resume point - 2026-08-08 (later), the families are classified

## STATE
HEAD pushed, tracked tree clean. Nothing running, nothing scheduled. Data
**2026.1.1242**. Models now **v39 · v40 · v41**, none re-certified.

## WHAT THIS PASS DID
The coverage check hard-failed on 104 families. **Residue is now ZERO**, and the
largest family in the client export was a real bug.

- **v41: DEFENCE DEBUFF RESISTANCE, 178 powers** (`39cd0872`, `7e9c1fdf`). The
  game says it in its own words - Agile prints "Res(DeBuff DEF)". The scorer has
  applied incoming -def pressure since v10 under the comment "a squishy has ZERO
  defense-debuff resistance", and that was true of every build it could see
  because DDR is power-granted only. Super Reflexes took a Blaster's haircut.
  **Needed nothing from you** - the pressure term already existed. Measured:
  Agile 6.92%, five SR powers 48.44%, Tough Hide 25%, Elude 6.23% (duty-cycled,
  180s on a 1000s recharge), negative control 0.0.
- **Every other family classified** (`37cbade5`): 269 template instances
  source-excluded (Alpha/Genesis boost DEFINITIONS are enhancement records, not
  powers; pet records), 42 dispositioned with the ruling behind each, **20 real
  gaps PINNED by power count** so they can neither go quiet nor hard-fail
  forever. The pin fails BOTH ways - grown means a new defect, shrunk means a
  stale entry.

## RE-CERT SCOPE, counted from the artifact
v39 **13** · v40 **8** · v41 **9** → **UNION 17 of 24**. (The 13 and 8 reproduce
the earlier handoff exactly, which is what makes the 9 trustworthy.) One wave
over the union, and only after the queue below is settled.

## OPEN - JOEL'S
1. **`mez_in`** - unchanged, and it now blocks FOUR more families: ToHit-debuff
   resistance (13 powers), endurance-drain resistance (8), regen-debuff (7),
   recovery-debuff (3). All real, all the same shape as DDR, all inert because
   **nothing applies that pressure in any scenario**. One scenario number each,
   or one ruling covering the class.
2. **Fury** - a Brute farm log with 3+ single-target attacks.

## OPEN - MINE, IN ORDER (the check now names all of these)
3. **877 powers hold ZERO effect rows while the client populates them.** Gamma
   Boost prints "Auto: Self +Regen, +Recovery, Special" and carries NOTHING; so
   do Master Brawler, Active Defense, Smoke Flash, every Taunt, the Staff
   Fighting Forms. This is the next real piece, and it is a class, not a family.
4. **Absorb is not modelled anywhere** (no engine branch) - Particle Shielding
   and Master Brawler are invisible. A term is owed.
5. **Three data-only fixes on axes that already exist:** +Accuracy on Terra
   Firma and Combat Training: Offensive, Field Medic's +Heal strength.
6. **Power Boost `Set_Mode`** (143 powers; the v39 mode machinery exists).
7. The 8 gated-only powers · ~460 unclassified cap/radius rows · knockback
   protection (now visibly the same class as DDR and slow resist).

## TRAPS ADDED THIS PASS
- **Translate the VOCABULARY, not just the case.** Ours says `AoE` and
  `Negative` where the client says `Area` and `Negative_Energy`; Cloaking Device
  carries all eleven defence vectors and still reported two missing. The
  121-phantom-debuffs lesson in a second coat.
- **A champion's picks live at `champion["picks"]`,** not `["build"]["powers"]`.
  My first exposure count read 0 of 24 for a 178-power family. Counting v39 and
  v40 with the same probe and reproducing the known 13 and 8 is what proved it.
- **`/build/calculate` wants `Class_Scrapper` and `slots: [None]`.** With the
  wrong payload shape every number reads 0.0, including the ones that work.
  Read a known-good axis in the same probe or you cannot tell whose bug it is.
- **A second family carrying v39's `mode` flag exposed a latent dedup bug** -
  the key was (scale, duration, stack) with no effect name. Fixed at the key.

# Resume point - 2026-08-08 (Saturday), the game-knowledge audit

## STATE
HEAD pushed, tracked tree clean. **v0.12.35 released** (stamp `d76c043`, signed,
both assets, installed copy mirrored). Nothing running, nothing scheduled.
Data **2026.1.1242**; client bins are the **July 7 build, which IS the newest
Homecoming patch** - the snapshot is live, not stale.
Models bumped today: **v39** (self +Damage at honest duty cycle) and **v40**
(power-granted slow resistance). Neither has been re-certified yet.

## WHAT TODAY WAS
Joel: "after 30+ releases we keep finding bugs related to in-game based
knowledge. Review EVERYTHING." Root cause found and it is not carelessness:
`reality_check_effect_structure.py` states in its own docstring that its scope is
*deliberately* five survival families and NOT damage/control templates. Every gap
of this class has therefore been found reactively from a field report - accuracy
v28, heal-strength v29, +MaxEnd v35, and today's four.

## SHIPPED (0.12.34 / 0.12.35)
epic swap dropping picks | leveling chart hiding open seats | an apostrophe that
broke 40 enhancement sets **since the first commit** | the export pointer.

## COMMITTED, NOT RELEASED
3 target-cap/radius drifts | self +Damage **275 powers** | slow resistance **126**
| mez protection + resistance **229** | Granite Armor **-30%** and Bio Armor
Defensive Adaptation **-25%** (never modelled) | v39 + v40 | mez availability term
(built, proven, inert) | `reality_check_effect_coverage.py` | 3 sabotage-proven
batteries.

## OPEN - JOEL'S, AND BOTH BLOCK THE RE-CERT
1. **`mez_in`** - how often content mezzes you. In NO bin; 43 MB of logs carry 14
   mez-shaped lines. Cannot be extracted or measured. The mez term multiplies by
   1.0 until it is set (kb_in precedent, PROVISIONAL). Because the design is
   protection-dominant it ONLY governs unprotected builds.
2. **Fury** - needs a Brute farm log whose rotation has 3+ single-target attacks.
   Two clean attacks cannot separate a multiplier from a flat term.

## OPEN - MINE, IN ORDER
3. **104 undispositioned families** in the widened check (hard-fails on them).
   `Melee_Ones` was 1 table of 45 and hid ONE real defect in 4,306 instances.
   Do the rest biggest first, each family fixed or dispositioned with evidence.
4. **Power Boost `Set_Mode`** (143 powers; the v39 mode machinery now exists).
5. **The 8 gated-only powers** (Hardened Carapace, Cosmic Balance, Dark
   Sustenance) - conditional, need the same scenario input mez does.
6. **~460 unclassified cap/radius rows.**
7. **Knockback protection** - pre-existing, filed as a "stated understatement",
   now visibly the SAME CLASS as slow resist and mez. Worth reopening.

## RE-CERT SCOPE when it is finally run
13 contexts for the v39 damage term, 8 for v40 slow resist. NOT 24. Run one wave
over the union AFTER 3 is done, or a family found later forces a re-run.

## TRAPS LEARNED TODAY - these cost real time, do not re-pay
- **A value the engine computes but never SURFACES cannot be verified.**
  `calculate_build` returns a curated 20-key response; `slow_resist` lives at
  `bonus_extras.slow_resist.value`. Probing the top level returns None however
  well the code works - this made me REVERT A CORRECT BRANCH, and the battery had
  the same bad probe baked in, passing 12/12 while blessing anything.
- **Raw scale is not resolved magnitude.** I quoted mez protection as "30" all
  session; through `Melee_Res_Boolean` it is **10.4** (Unyielding's real value),
  20.8 stacked. Coverage 98.4%, not 98.9%.
- **Compare modifier tables CASE-INSENSITIVELY** - ours `Ranged_DeBuff_ToHit`,
  client `Ranged_Debuff_ToHit`. One capital B invented 121 phantom missing debuffs.
- **Ask whether we carry the ATTRIB under any name before calling it absent.**
- **ASPECT is part of the identity** - self RechargeTime is slow RESISTANCE at
  aspect=Resistance and a recharge BUFF at aspect=Strength. 78 records would have
  been corrupted.
- **Zero-scale templates carry no magnitude** - every Blaster blast has one
  (Defiance is derived from cast time), and counting them made 13 champion
  contexts look exposed and stalled a re-cert over a double-count that could
  never fire.
- **Anything an inherent term already DERIVES stays out of the data** (Vigilance,
  Defiance) or it is counted twice.
- ⚠ **I wrote CRLF files as LF again** (`newline=''` on a text write): 3,147
  insertions on a 92-line change. The whitespace-blind `git diff --stat` caught it.

## THE PATTERN WORTH KEEPING
Eight of my own numbers needed correcting today and EVERY ONE was caught by a
check, never by re-reading. Measure before claiming; a probe that looks reasonable
can be wrong in the same way the code is.

# Resume point — 2026-08-07 (new session starts here)

## ✅ CLEAN START. Nothing is running, nothing is owed to a half-finished task.

**v0.12.33 "Knowing what to do next" is RELEASED and ANNOUNCED.**
Build stamp `898653a`, signed, API-verified, both assets. Installed copy mirrored
and relaunched (its header reads 0.12.33). Joel posted the announcement to topic
64761 himself on 2026-08-07. Tree clean and pushed. No scheduled tasks, no
monitors, no dev server, no wave.

Data **2026.1.1242** and model **v38** unchanged, so no certified score has moved
and **no re-cert is owed**.

### ⚠ Three things the post created, all recorded in CLAUDE.md
1. **Nothing public has ever announced that the app stopped being a browser
   tab.** The 0.12.31 and 0.12.32 drafts were never posted, and Joel cut the
   catch-up paragraph ("I never posted about 0.12.31"). If a field report reads
   as "why does this not open in my browser", that is why. Not a bug.
2. **A public correction was made** (the update check runs on launch, not only
   when clicked). That stale-reply watch item is CLOSED.
3. **The post says `/thumbtack` is untested in game.** If anyone confirms the
   marker lands, that is the trigger to strengthen the claim.

### ▶ MINE, unblocked, in the order I would take them
- **Fury meter + Power Boost as ONE piece.** Blocked on data, not on design: it
  needs a THIRD clean single-target attack from a Brute farm log. Only two
  isolate today, and two points cannot separate a multiplier from a flat term.
  ⚠ AoEs can never be reconstructed from this log format.
- **Leveling Companion batch** (shares the Journey surface).
- **pricing #31** (single-claim pairing).
- **strict-dominance solver experiment** (optional).
- Cheap and worthwhile: the **budget/balanced/premium dial** is vestigial and
  Joel wants it to be a real player choice again (his R3 answer, its own item).

### ▶ JOEL'S
- **FP / whitelist submissions** for the 0.12.33 signed artifacts, per
  `docs/signing-runbook.md`. ⚠ Bitdefender often kills the app on release nights.
- **github.com/settings/billing** — the inbox workflows still cannot get a
  runner; both stay `disabled_manually`. Billing needs a gh scope deliberately
  not granted, so this cannot be chased from here.
- **The Iron Man / Adamant badge**: does it actually grant its accolade power?
  A character holding it either shows the HP/End bump or does not.
- **The gaming box** has not woken since 2026-07-29.
- **The i24 torrent** (zone display names ride on it).
- **Design calls still open**: naming which set bonus changed, pairing the wide
  diff tables, whether meters move displayed damage, and whether the app should
  track a character's origin at all.

### Where the detail lives
`session-report.md` (outbound, newest first) has the full account of the last
session. `CLAUDE.md` holds every standing rule; the newest entries are the
per-character state sweep, the tour scene trap, the epic-swap refill, the
PvP-variant disposition and the scripted-write CRLF warning.

# Resume point — 2026-08-06

## ⏸⏸ SESSION CLOSED — 2026-08-06, read THIS block first

**HEAD `226b6db0`, pushed, tracked tree clean. Published `v0.12.32`. Installed
copy frozen stamp `e164fd1`. App not running. Nothing scheduled, no monitors.**

⚠ **The installed copy's STATICS are ahead of its stamp** (the button-cap CSS
went in via `push_statics.py` after the 0.12.32 build). Do not read the stamp as
"what the app contains". A rebuild resolves it whenever one happens next.

### The ONE staged item
CHANGELOG "Unreleased" holds a single entry: **action buttons share one width**
(`button { max-width: 420px }` + a row-control opt-out). It is in Joel's app but
not in any release. Everything else shipped in 0.12.32.

### ⚠⚠ TWO RETRACTIONS FROM THIS SESSION — do not act on the old versions
1. **−recharge debuff pinning: ALREADY DONE** (`6b503c0c`, 2026-08-05). The
   "Slow enhancements / under-credited" line was stale; I chased finished work
   because of it. Recharge is credited both directions, verified live
   (Neurotoxic Breath −81.2% unslotted → −102.6% slotted).
2. **"Radiation Melee per-attack damage is wrong": FALSE, retracted same day.**
   I compared ENHANCED engine damage to BASE client scales on differently
   slotted attacks. Our base is exact (74.1 / 154.2 = client 1.48 / 3.08 ×
   50.07/50.06; base ratio 0.481 = client 0.481). No data bug.

**The lesson both share, and it is the expensive one: check what a number
MEASURED before repeating it, and close an item in the records the same commit
that closes it in the code.**

### Where Fury actually stands
`tools/measure_fury_residual.py` v2 is built (component-summed swing
reconstruction, the v36 memo's named instrument). Spread **228% → 25.2%**.
Blocked, precisely: **only two attacks isolate cleanly, and two points cannot
separate a multiplier from a flat term** (`expected×F + C = observed` gives
F≈0.995 / C≈48.9 with nothing left to validate). **Needs a THIRD clean
single-target attack** — farm logs from a Brute whose rotation has 3+ of them.
AoEs can NEVER be reconstructed from this log format: farm mobs share display
names, so grouping merges hits on different enemies (Atom Smasher logs up to 18
components for a 2-component attack).
⚠ **New trap recorded:** 86 of 108 Brute melee attacks carry a `Fire_Dmg`
template with an EMPTY gate in the export. That is **Fiery Embrace**; our data
correctly omits it. Never "fix" it by trusting `requires_expression == ""`.

### Power Boost — untouched, and it is the same work as Fury
The client shows it is a `Set_Mode` (BoostPower, 15s), not a flat bonus, so it
belongs with the meter/mode capability. Zero champion exposure, so it can never
move a certified score. The displayed-damage half is Joel's ruling.

## ⏸ PLACE SAVED — 2026-08-06 late, after the button fix

**HEAD `d54415f0`, pushed, tracked tree clean. Published `v0.12.32`. App not
running. Nothing scheduled.**

⚠ **The installed copy's STATICS are ahead of its stamp.** Frozen stamp is
`e164fd1` (the 0.12.32 build); the button-cap CSS reached it via
`push_statics.py` afterwards. That is fine — the change is CSS only with no
server dependency — but do not read the stamp as "what the app contains".

**▶ ONE ITEM STAGED FOR THE NEXT RELEASE** (CHANGELOG "Unreleased"): the action
buttons now share one width. See the `button { max-width: 420px }` block in
style.css for why it is a CAP and not `width: auto` — that choice is the entire
no-layout-break guarantee, and the comment carries the measurement (246 buttons
snapshotted with and without the cap; exactly one changed).

## ⏸ PLACE SAVED — 2026-08-06 night, after v0.12.32

**HEAD `e164fd13`, pushed, tracked tree clean. Published `v0.12.32`. Installed
copy = `e164fd1` and reports 0.12.32. App not running. Nothing scheduled.**
Two releases landed today: 0.12.31 (the desktop app) and 0.12.32 (everything
from Joel's review after it). Data 2026.1.1242 and model v38 both unchanged in
0.12.32, so no certified score moved and no re-cert is owed.

**▶ FIRST THINGS NEXT SESSION**
1. **The 0.12.32 announcement post is written and NOT posted** — it is in the
   chat transcript, ready for topic 64761. ⚠ Its badge sentence is deliberately
   weak: it says `/thumbtack` is the command the client registers for placing a
   minimap marker, and does NOT claim the marker lands correctly. Nobody has
   confirmed that in game (Joel said skip it). Strengthen only after someone has.
2. **FP / whitelist submissions** for the new signed 0.12.32 artifacts, per
   docs/signing-runbook.md. ⚠ Bitdefender often kills the app on release nights.
3. **The render watch was armed and never fired** (monitor `bev2z5b0h`, baseline
   run 31128638583). The Pages deploy-job removal (`0c06b9df`) is proven by ONE
   good build; confirm the next few scheduled renders still publish cleanly.

**▶ MINE AND UNBLOCKED, in the order I would take them**
- ~~Pin the −recharge-debuff question~~ **ALREADY DONE — `6b503c0c`, 2026-08-05.**
  The Slow hypothesis was disproven by the client and Recharge is credited in
  both directions; verified live (Neurotoxic Breath −81.2% unslotted → −102.6%
  slotted). This line was stale and sent a session chasing finished work.
- **Fury meter + Power Boost as ONE piece** — the client shows Power Boost is a
  `Set_Mode`, not the flat bonus it was queued as. Zero champion exposure. Only
  the displayed-damage half needs Joel.
- ~~the 8 irreducible Chrono_Shift rows~~ **CLOSED 2026-08-07** — PvP variants
  (`pv_mode 2`), exactly 5.33× the client's own timed heal scales on all four AT
  variants. Gated off in PvE, proven live. The census instrument gained the
  class it was missing: residue 240 → 184. See CLAUDE.md.
- ~~alias-map roster reconciliation~~ **CLOSED 2026-08-07** — a display-name
  rung took roster diffs 12 → 3 with zero existing aliases changed; the 3 left
  are real roster differences, each named with its evidence and hard-failed if
  left undispositioned. It surfaced a real defect — Blaster Tactical Arrow
  showed "Oil Slick Arrow" twice and never "Gymnastics" — **✅ FIXED the same
  day on Joel's word** (`patch_display_name_collisions.py`: 1 record, 7 fields,
  verified through the served `/powers` route; zero champion exposure, no
  re-cert owed). See CLAUDE.md for the two follow-ons the fix required.
- Leveling Companion batch · pricing #31 · strict-dominance experiment
  (optional).

**▶ JOEL'S, UNCHANGED** — github.com/settings/billing (inbox runner block, both
workflows stay `disabled_manually`) · the Iron Man badge look · the gaming box,
silent since 2026-07-29 · the i24 torrent · and five open design calls (name
which set bonus, pair the wide diff tables, meters on displayed damage,
budget/balanced/premium, whether the app tracks character origin at all).

## ▶▶ AGENDA SWEEP (2026-08-06 night) — two solved, two closed, two re-scoped

**SOLVED**
- **Exploration-log parse** (`9360ae81`): `marginals()` streamed instead of
  loading 2.2 GB into dicts. Measured on the real log: **89.3 s → 29.3 s, 6,174
  MB → 393 MB peak (15.7×)**, result byte-identical (SHA-256 compared). Cost
  fix only, moves no number, no re-cert. Battery `test_learn_stream.py` (11),
  3 sabotages. ⚠ The pre-filter's danger is a FALSE NEGATIVE — `ctx_key` still
  decides membership, the substring test only pre-rejects.
- **Reduced motion** (`55d40c67`): the CSS block existed, but
  `scroll-behavior: auto !important` cannot override a `behavior:"smooth"`
  passed in JS — 11 sites did. One `scrollBehavior()` helper, read at call time.
  test_desktop_app 129 → 132, sabotage-proven.

**CLOSED — nothing to fix, do not re-open**
- **18 inherent icons.** All seven player-visible granted inherents already have
  icons. The 40 unmapped ones are internal machinery (`AutoLevel20`,
  `COMBO_LEVEL_1`, `SR_HP_Slider`, `FAST_MODE`) that the CLIENT gives no icon
  name — inventing art there breaks the game-first rule.
- **Origin plates.** Extracted and unreferenced because **the app has no
  character-origin concept at all**. "Placing" them means inventing an origin
  field + picker + persistence — a product decision, not art placement. Joel's.

**RE-SCOPED**
- **Power Boost + the Fury meter class are ONE piece of work** — see the
  CLAUDE.md entry. Power Boost is a `Set_Mode`, not a flat bonus. Display half
  is already Joel's ruling. Zero champion exposure either way.
- **Zone display names** stay blocked game-first until the i24 pass.

## ✅ THE PAGES RACE IS FIXED (`0c06b9df`) — and the inbox is still Joel's

**Fixed:** two deployers had been racing since 07-27 (GitHub's per-push legacy
build + a `deploy` job in `render-pulse.yml` left behind by a half-revert of the
07-20 change). The job is removed; the render's commit publishes. **Proven:** a
dispatched render succeeded (one job, 11 steps), its board commit produced the
first SUCCESSFUL Pages build in hours, and Pages status went `errored` → `built`.
Board live, current date. See the CLAUDE.md entry for the standing rule that the
source setting and the deploy job are one decision.
⚠ Watch the next few scheduled renders — one good build is encouraging, not
proof. The daily freshness canary is the backstop.

**NOT fixed, and not mine:** the inbox workflows still cannot get a runner
(proving run 31127012557: queued 55.9 min, cancelled, zero steps, `runner: ""`).
Both remain `disabled_manually` so the daily failure mail stays off.
**github.com/settings/billing is Joel's** — billing needs a gh scope
deliberately not granted; do not re-auth to chase it.

## ⏸ SAVED PLACE — 2026-08-06 evening (Joel headed home)

**HEAD = `de80a2b0`, pushed, tracked tree clean.** Installed app is frozen stamp
`bdc7f48` and holds ALL the code (the two commits after it are docs only). The
app is not currently running. Release still HELD at 0.12.31; everything below is
staged under CHANGELOG "Unreleased".

**✅ RESOLVED, and the answer was no.** Proving run 31127012557 sat **QUEUED for
55.9 minutes and was cancelled with ZERO steps** — it never got a runner. The
allowance has NOT reset, so both workflows are `disabled_manually` again (done
the same evening, so tomorrow's failure mail does not resume). **The next move
is Joel's: github.com/settings/billing** — a declined payment method would not
self-heal on a monthly reset, and nothing was consumed in August because the
workflows were off all month, so "ran out of minutes" does not fit. Do not
re-auth gh to chase this. Boards verified unaffected (200, current date).

**What today's inbox finding was:** Joel's Companion Lite 0.1.18 on his gaming PC
is uploading fine (captures every ~5 min). But `Collect mailbox` and `Inbox
maintenance` were STILL `disabled_manually` — five days past the recorded
2026-08-01 re-enable date — and the inbox had accumulated **2,633 commits since
07-27**, which is what the weekly squash exists to prevent (8.4 MB, ~288
commits/day). Both are `active` again. The boards were never affected: the
render lives in the PUBLIC repo and reads the inbox directly.

**Still owed, none blocking:**
1. **Paste a `/thumbtack` in game and watch the X land** — the one claim in the
   badge work nobody has confirmed. Joel's eyes only.
2. The diff says "Set bonuses 41 → 42" without naming WHICH bonus. Offered to
   him, not built, he has not asked.
3. The forum reply (v5 draft) is still unsent, and the 0.12.31 announcement post
   was handed to him in chat but not posted to topic 64761.
4. FP/whitelist submissions for the 0.12.31 signed artifacts.

## ▶▶ LATEST: the picker refuses what the game refuses (`bdc7f488`)

**⚠ SERVER CHANGE → REBUILT.** dist rebuilt (stamp `bdc7f48`), frozen smoke PASS
+ gold 24/24, mirrored to the installed copy (uninstaller preserved), relaunched,
and `/meta` verified shipping the override in the LIVE app. VERSION still the
released 0.12.31, ISCC NOT run, `dist\HeroCompanion-Setup-0.12.31.exe` intact.

A unique held in ANOTHER power is now greyed with the reason naming that power,
and `pickPiece` enforces it as well as the greying. ⚠⚠ The over-blocking guard
is the important half: `/meta` ships `engine.NON_UNIQUE_OVERRIDES` (LotG global
recharge) and the check FAILS OPEN with no meta. Verified live on a solved
Claws/SR. Battery `test_slot_rules.js` (9, four sabotages).

## the swap picker prices every replacement (`47c52dfb`)

**⚠ THIS ONE CHANGED `server.py`, so it needed a REBUILD, not a statics push.**
dist rebuilt + frozen smoke PASS + gold 24/24, mirrored to the installed copy
(stamp `47c52df`, `unins000.exe` preserved), relaunched, and the route verified
live in the running app. VERSION is still the released 0.12.31 and ISCC was NOT
run, so `dist\HeroCompanion-Setup-0.12.31.exe` is untouched.

New `POST /build/slot_compare`: every candidate priced by rebuilding the
character with it in the slot, in one batched request (4.9 ms each, measured
first — 165 candidates < 1s). Axis = the selected stat, set-bonus count always
alongside. See the CLAUDE.md entry for the four traps.
⚠ On an optimised build every swap on the optimised stat is a deficit — the
truth; the gain direction is separately proven. Battery `test_slot_compare.py`.

## every edit reports itself + Undo (`3871f25c`)

"What changed" appears on Stats after ANY build-mutating edit — the hook is
`recordEdit` (called by every surface), not the popover's buttons, so it is
universal by construction; proven with a plain `clearSlot`. Carries **↶ Undo
this change**. Measured: Remove → Lethal 27.5→23.8, bonuses 42→41 marked as
losses; Undo → piece back, 42, Lethal 27.51, no second receipt.
⚠ `_placeIoPop` re-centres when its anchor chit is destroyed (closing would take
the Undo with it). ⚠ `renderImproveDiff` labels are per-caller now
(`opts.labels`); test_improve_diff 13 → 15, sabotage-proven.

## Stats is the MANUAL surface (`ec1f09d6`)

Joel's framing: Powers & Slots owns the Assistant's global "more X, Y, Z"
re-solve; **Stats is where a player changes one piece at a time**. So the
popover now carries **Swap this enhancement… / Remove it**, on the same
`openSlot`/`clearSlot` every other surface uses — no second editing path.
Verified the prediction IS the outcome: predicted Without-it Lethal 23.8 /
Smashing 23.8 / Melee 45.1 / bonuses 41 → Remove delivered 23.76 / 23.76 /
45.08 / 41. Swap opens the picker on the right slot with the popover closed.

## the per-IO answer is a popover at the chit (`2548a27f`)

Clicking an enhancement used to answer into `#stat-breakdown`, below the wall —
so the answer was off screen. His stated purpose ("what to sacrifice for the
LEAST impact") is a comparison, so the page must not move: `#io-worth-pop`
anchors to the chit, follows chit-to-chit clicks with zero page scroll, clamps
to the viewport, closes on ✕ or an outside click (never Escape — it does not
reach the page in this shell). **The stat breakdown underneath is untouched**,
so a stat can stay selected with its contributors ringed while each is probed.
Measured at 1240: 6px under the chit, 287px tall, right-edge clamp holds
(chit x=1153 → popover right 1232 of 1240), 6px again after a scroll settles.
⚠ Per-power table opens FOLDED, or the popover wants its own scrollbar.

## the contributions column is back at his width (`23fbe8e6`)

⚠ **I got his previous message wrong first.** "Display along side what is
clicked" meant *the right-hand column, where it used to be, with the arrow* —
not a new inline position. The fault was the BREAKPOINT: `.stats-provlayout`
collapsed below 1400px and the 1.6× shell zoom put his effective width under it,
so the column was switched off. It holds to **1000px** now (that side column is
real content, not a void, unlike the powers rail which keeps 1400). Measured at
1240: two columns 811+380, panel beside the row, green ➜ intact, 8 power cards.
Below 1000 it still stacks and the JS keeps it under the clicked row (2px).
`test_desktop_app` 128 → 129; the "both collapse at 1400" pin now pins each at
its own width + a sabotage-proven negative control.

## the breakdown follows the clicked row below 1000px (`e4248462`)

Joel's screenshot: the right-hand contributions column was "missing". It was
1750px below the row — `#stat-breakdown` is the last child of the stats grid,
and the 1400px rule had collapsed that grid to ONE column. **His window is wide;
the 1.6× shell zoom is what pushes the EFFECTIVE width under the threshold.**
One column now re-homes the panel directly after the selected row (2px gap,
follows the selection); two columns is unchanged. ⚠ Re-homing puts it inside the
rows container that gets innerHTML-rewritten every recompute — `_breakdownHost()`
holds the element and re-attaches it, proven by driving a real recompute.
Also fixed: the mini-wall header rendered twice (lengthened past 26 words →
`collapseLongExplanations`; it has `.keep-whole` now).

## per-IO worth + the green-marks legend (`fa8d9506`, `b867df72`)

Both in **both frozen copies** and the app relaunched (statics only; frozen
stamp stays the release `b2161e1`). Staged under CHANGELOG "Unreleased".

- **Click any enhancement in the Stats miniature wall → what it is worth**,
  measured by rebuilding the character without it. See the CLAUDE.md entry for
  why the analytic shortcut is wrong and for the two traps (`buildPayload()`,
  and `/build/calculate` returning totals directly).
- **The two green marks have a legend** — a ring on an enhancement vs a box on a
  power's NAME. It was only ever explained in a footnote that appeared solely on
  powers that had the built-in contribution.
- Batteries: `test_improve_diff` 9 → 13 (2 sabotages), `test_journey_macro` 35.
- ⚠ **Open, worth offering him:** the diff says "Set bonuses 41 → 42" without
  naming WHICH bonus. Naming it needs the applied-bonus list diffed by name, not
  just counted. Small, not built, and he has not asked.

## ▶▶ THE BADGE CATALOGUE REBUILD + FLASHBACK LANDING (`04219ff3`)

Joel's two follow-up orders, built, verified live, pushed, and **in both frozen
copies** (statics only; the frozen stamp stays the release `b2161e1`).

- **Every badge is on the surface and its name is the button.** 390 chips under
  57 zones, 382 clickable, 8 inert-by-design (no coordinates → plain text, never
  a fake control). The drawer keeps the prose and names what it holds; the
  how-to is stated once at the catalogue head. Copy handler now keys on
  `[data-cmd]` so chip and wide row are ONE mechanism — see the CLAUDE.md entry.
- **Flashback lands on Praetoria** when you arrive from a stop outside its 1–20
  range, and hands your stop back when you leave (`_praeSnapIndex`, pure and
  battery-driven). Verified: hero L50 → Flashback (Nova Praetoria) → hero L50.
- Battery `tools/test_journey_macro.js` **35 checks, 9 sabotages proven**.
- ⚠ **STILL UNCONFIRMED IN GAME: nobody has pasted a `/thumbtack` and watched
  the X land.** That is the one open question on all of this work.
- ⚠ Visible in his screenshot and NOT fixed (it is a standing ruling): zone keys
  are raw internal prefixes, so the grid shows `AbSewerNetwork` and both
  `CapAuDiable` and `CapauDiable`. Display names ride the i24 server-data pass.

## (earlier the same evening) badge macros + the Flashback art empty state (`12bc2b63`)

Post-0.12.31 work from Joel's two observations. Committed and pushed, staged
under CHANGELOG "Unreleased".

**⚠ NOW IN BOTH FROZEN COPIES (pushed 2026-08-05 late, after Joel went looking
for it).** I first withheld the statics so his app would match the release, said
so at the end of a long reply, and offered a choice — he went to the desktop
shortcut to look instead and reported "nothing was updated." He was right, and
the friction was mine. **Generalize: when someone has just asked about a fix,
the default is to put it where they can see it, not to hand them a choice about
plumbing.** `push_statics.py` (2 of 3123 files → both copies) + relaunch;
statics-only, no server dependency (the coordinate and zone data were already
being served), so no half-update lie. Installed copy still reads *installed*
and its frozen stamp is still the release `b2161e1` — only the statics moved.

- **`/thumbtack <x> <y> <z>` is the game's own map-marker command**, pinned from
  `cityofheroes.exe`'s command table — see the CLAUDE.md game-facts entry for
  why the pairing is self-proving and why `/loc` must NOT be claimed from the
  same dump. Every badge with coordinates (382 of 390) carries a click-to-copy
  row reusing the shipped `.cmd-row` handler.
- **⚠ UNCONFIRMED IN GAME:** nobody has pasted one and watched the X land.
  Joel's eyes settle it — that is the one open question on this work.
- **The Flashback art slot stopped claiming "zone art pending"** above level 20,
  where Praetoria simply ends; the range is derived from the zone data.
- **25 badges were hiding their coordinates** because the numbers were nested in
  the directions block. Fixed at the root.
- Battery `tools/test_journey_macro.js` — 20 checks, proven against 6 sabotages.
  Regressions green: tour, tabs 10/10, links, desktop app, improve-diff 9/9,
  `demo_single_build_fixes` 24/24.
- ⚠ Known, NOT changed: `/journey/badges` serves only `locations[0]`, so the 39
  badges with more than one spot show one. Say so before "fixing" it.

## 🚀 v0.12.31 "The desktop app" IS PUBLISHED (2026-08-05 8:35 PM ET)

Joel reviewed the installed app, gave the thumbs-up, and the full release
procedure ran clean: VERSION + both smoke pins bumped, CHANGELOG's stale
Unreleased block rewritten as the real 0.12.31 entry, docs/index.html
disclosure flipped to the window truth (the recorded release step), help PDF
rebuilt, clean-stamp frozen build `b2161e1` (release-prep committed FIRST so
the stamp is not "-dirty"), frozen smoke PASS, gold 24/24 SERVED, exe +
installer signed and verified (CN=Joel Andrew Chambers), portable zip built,
`gh release create v0.12.31` with both assets, API-verified. Installed copy
mirrored from dist (robocopy /MIR, unins000.* preserved) and relaunched —
Joel's shortcut now opens the released build. Release announcement post
handed to Joel in chat + session-report (no em dashes). Remaining his-hand
items: post it to topic 64761, FP/whitelist submissions per signing runbook,
watch for the Bitdefender release-night kill (verify the app relaunches once).

## ✅ POWER-ICON PASS: the i24 glob bug is fixed — `7a67c48c`

The two-line fix and the finding that made it pay: `extract_power_icons.py`
globbed `texture_*.pigg` (zero matches in the i24 set — its archives are
`tex*`/`stage*`), and the still-missing `e_icon_gen_*` names live under
`GUI/Icons/Enhancements` (i24 stage2.pigg), a prefix the tool never searched.
23 textures extracted, **94 Incarnate Alpha boost sub-powers** now carry the
game's own generic enhancement art (coverage 6033→6122). 7 textures are absent
from BOTH asset sets and stay reported, not faked. Gate 24/24. Data + statics
change — rides the next rebuild; nothing pushed to the frozen copies (a
missing icon renders the fallback, so no half-update lie is possible).

⚠ Stale-queue note: the **verdict-gate legality hole is ALREADY CLOSED**
(`07ce596e` + `tools/test_verdict_legality.py`) — older open-queue lines
naming it are superseded.

**HEAD = `c78f552b`, pushed, tracked tree clean. Nothing running.** Release still
HELD at 0.12.30.

## ✅ RECHARGE IS CREDITED, and the client settled it — `6b503c0c`

Joel: "lets give recharge its accreditation." My exclusion was a GUESS (that
−recharge rides Slow enhancements) and the client disproves it AND answers the
question properly:
- `Crafted_Curtail_Speed_A`, a Slow IO, enhances RunningSpeed / FlyingSpeed /
  JumpingSpeed + Accuracy. **No RechargeTime — Slow is not the route.**
- Neurotoxic Breath's −recharge is `attribs ['RechargeTime'], aspect Strength,
  target AnyAffected`, and its `boosts_allowed` carries `Recharge`.
- Speed Boost and Accelerate Metabolism hold the same template pointed at
  allies and allow `Recharge` too — so it is credited in BOTH directions.

Measured: the saved Poison build has no recharge in Neurotoxic Breath so its
−recharge row correctly does not move; add one recharge IO and it goes
**−83.2 → −117.4**. Both arms are pinned, so the positive case cannot pass by
accident. The three remaining exclusions now cite the game's own per-power
allow-lists rather than "no such category exists". `test_buff_debuff_enh` 9 → 11.

## 🖥 HIS INSTALLED APP IS CURRENT (stamp `116d1ce`)

Joel, 2026-08-06: *"The deliberately means nothing to me, its giberish without
context."* Fair — the dist/installed split is my plumbing, not his problem.
**The installed copy is now updated from the smoked dist build by robocopy /MIR
(excluding `unins000.*`, so the uninstaller and ARP entry survive).** Do this
after any server-side change rather than explaining a distinction to him.
⚠ Statics and PYZ must move TOGETHER — see the CLAUDE.md rule.

## ✅ THE SLOT INVITATION IS A CLAIM NOW — `018b539d`

Joel: *"This appears no matter if slots are all filled or not."* "All 24 powers
picked. **Now slot them**" was decoration on a full pick list. It shows only when
the pool has free slots or a **real** power holds an empty one, and it names the
reason; otherwise "All 24 powers picked, every slot filled" with no CTA.
⚠ **The seven granted inherents are excluded** — Brawl/Sprint/Rest carry a base
slot the solver is capped out of by design, so counting them makes the nag
permanent. Negative-controlled on screen (emptying Health does nothing; emptying
a real power brings it back). His build genuinely has two empty slots (Alkaloid,
Weave), so his line now says why.

## ⛔ THE CLASS-ART FILLER IS REMOVED AT HIS WORD — `018b539d`

*"Remove the one image, from your attempts. I will try and find something."*
The CSS rule, the `--at-art` variable and all 15 PNGs (3.8 MB) are gone from the
repo **and from both frozen copies**. ⚠ `extract_gui_emblems.py` keeps the
capability behind an explicit **`--art`** flag — finding the art was the work
(`charectercreationui/archetypescreenshotsassets`, 512×314 after crop, 3 shots
per archetype, 15 of 16; Guardian has none) — but a routine emblem run must
never drop unused megabytes back into `static/`. **He is sourcing his own art.**

## (superseded) THE CLASS-ART FILLER — `c9265561`

His idea: *"some filler graphics representing each class being worked on while
picking powers might be nice."* Half done, and the half that failed is stated.

- ✅ **The game has real art for this**: `charectercreationui/
  archetypescreenshotsassets`, 512×512, three shots per archetype.
  `extract_gui_emblems.py` now pulls shot 0 → `static/icons/at_art/` (15 of 16;
  **Guardian has none in the client**, reported not faked). The 32px emblems in
  `icons/at/` are ICONS — at panel size they are mush, which is why this needed
  its own source.
- ❌ **It would not paint in the frozen shell.** Three mechanisms tried (panel
  background + blend mode; absolute `::after` at 0.16; same at 0.55, no mask).
  In the dev copy every measurement says it is there — var resolves, box
  computes 291×176, image loads — and the real window shows nothing. Stopped at
  three rather than ship a fourth shape for one feature in one evening.
- ⚠ **The idea has now been tried TWICE**: a dead `.cat-art` rule (archetype
  watermark in the catalogue, rendered by nothing) was found and removed.
- **Nothing references the art**, so nothing changed on screen. It is committed
  because extracting it was the hard part.
- ✅ **FIXED after his "I saw one image for one build but it was small":** it was
  painting all along, anchored to `#powers-list` — which holds the wall **and the
  catalogue**, so bottom-right of it is the bottom of the CATALOGUE. Now anchored
  to **`.powers-wall`**, sized to the measured 978×152 hole its last row leaves,
  at `z-index: -1` inside the wall's own stacking context so the opaque cards
  mask it (a fuller last row just covers more — no card count in the CSS).
- ⚠ **The textures are a ~512×314 picture padded to a power of two with a flat
  blue block under it.** `contain` fitted the pad too and put a blue slab on
  screen. The extractor crops now (detector + a 314-row fallback for three shots
  whose pad the sampler can't separate from their dark sky); all 15 verified.
- ⚠ **A cropped BAND filled the strip but decapitated half the roster** — the
  Defender floats in the upper third and lost its legs, the Brute fills its frame
  and lost its heads. So it fits by HEIGHT and shows whole: correct for all 15,
  **at ~245px rather than filling the strip. Joel's call if he wants it bigger**
  — that needs either a per-class crop focal point or more vertical room.

## ✅ DONE: the buff/debuff panel reads enhancement — `be8641db`

Joel's ruling, acted on. `_debuff_buff_summary` priced every row at base scale ×
modifier table with no slot boosts; it now multiplies by the host power's own
post-ED enhancement in the aspect of the effect's name.

- **The rule needs no table:** effect names and enhancement-aspect names are the
  same client vocabulary, and whether a power may hold an enhancement is already
  answered by its own slots.
- **Four exclusions, the game's own:** across 3,650 powersets the client ships no
  resistance-debuff, no −regeneration and no −damage category, because those
  enhancements do not exist. RechargeTime was excluded separately at first, then
  ✅ **CREDITED the next day (`6b503c0c`)** — the Slow hypothesis was wrong and
  the client settled it (a Slow IO carries no RechargeTime; the −recharge
  template's own `boosts_allowed` includes Recharge).
- Measured (Poison/Sonic): Envenom −Def **68.8 → 106.3**, Neurotoxic Breath Slow
  **768.8 → 1099.3**; −res / −regen / −damage do not move at all. −recharge DOES
  move as of `6b503c0c`: Neurotoxic Breath **−81.2% → −102.6%**.
- **NO MODEL BUMP, NO RE-CERT — traced, not assumed.** `first_principles._deb()`
  reads `role_output.enhanced_debuff_totals` whenever a role_output module is
  supplied and every serving call site supplies one, so this summary is only its
  fallback; role_output was untouched and `encounter_value` is identical to nine
  decimals (contribution 1672.0 → 1672.0). ⚠ The other consumer,
  `payoff_metrics["support"]`, is reachable ONLY from `joint_refine(scorer=
  "payoff")` — **which has no callers anywhere**; wire it up again and that path
  starts moving with slotting.
- Copy follows the numbers: both headers now say "with your slotting", and the
  stat breakdown no longer claims "not from IOs".
- Battery `tools/test_buff_debuff_enh.py` (9, negative-controlled both ways).

⚠⚠ **STATICS WERE DELIBERATELY NOT PUSHED TO THE INSTALLED COPY.** Its server is
still `297ddcf`, so pushing the new wording there would put "with your slotting"
above numbers that are still unenhanced — a lie on his machine. The installed
copy stays wholly on the old text until he chooses to install. **`dist` has
both halves and is the copy to open** (`be8641d`, smoke PASS, gold 24/24).

## 🔨 THE FROZEN REBUILD IS DONE — but only `dist` has it

`dist\HeroCompanion` is rebuilt and stamped **`c78f552`** (was `297ddcf`), so the
2026-08-05 server work finally exists in a frozen artifact: the portable-update
refusal (`_install_kind`) and the special-origin names in `PIECE_BY_UID`.
Frozen smoke PASS · frozen gold **24 of 24 SERVED**.

⚠ **The INSTALLED copy is still `297ddcf`** — `%LOCALAPPDATA%\Programs\HeroCompanion`
carries statics from today but the OLD server inside its PYZ, and that is the
copy Joel's shortcut opens. Getting the server fixes there means running the
installer (ISCC + install), which **overwrites `dist\HeroCompanion-Setup-0.12.30.exe`**
— the released signed installer, preserved as `.released-signed.exe` — and
changes how the app lives on his machine. **His call, not mine.** Until then:
launch `dist\HeroCompanion\HeroCompanion.exe` to see the server-side fixes.

## ✅ DONE, last thing before Joel left: no side bar on Powers & Slots — `809c9190`

His words: *"The output of a build assistant is terrible on the far right. Why
not put it and the whole epic and incarnate right below the All 24 powers picked
section. Epic and incarnate first, then Build Assistant. Let it take up the
entire horizontal width so no side bar appears at all, unless IO details are
asked to be displayed."* Built and eyes-verified on the installed window.

- `#endgame-plan-panel` then `#assistant` are full-width sections under the
  builder. `.powers-side` keeps the ⓘ card and nothing else.
- The column is opened **by the card, in CSS** —
  `.powers-layout:has(#power-info:not(.hidden))`. ⚠ The 1400px and 980px
  overrides must REPEAT that whole selector (`:has()` takes its argument's
  specificity, so a bare `.powers-layout` loses to the id inside it).
- Dead `has-info` class deleted; the grout rule retired with the second column.
- Measured: wall 4 cards → 6, catalogue's 7 powerset columns in ONE row, the
  improvement table 1489px wide with every row a single 22px line (it used to
  wrap in the 340px column — that WAS his complaint).
- `test_desktop_app` 121 → 126, every new check sabotage-proven.

**▶ Two things worth his eye next session:**
1. The two diff tables (totals + power-by-power) now each span ~1490px, which is
   generous for four numeric columns. Offer to pair them side by side.
2. ⚠ His app was left showing **Hero**; it was on Villain when the session
   started. Alignment lives in localStorage and I cycled all four verifying the
   wordmarks — set it back if he notices.
⚠ Relaunch the app: statics were pushed to both frozen copies AFTER the window
he last had open.

---

## ✅ DONE: per-power deltas in the improvement report — `10a7ed0b`

The last ❌ in the big-ask table below is closed. Every attack the engine priced
is diffed by its **Cycled DPS** (the same number the ⓘ card shows) plus a
per-hit row, and **pets are credited to the power that summons them** ("Jack
Frost → Ice Elemental, 72.4 → 78.3 DPS"). Own `<details>` table under the
totals; it stands alone when a per-power move is too small to shift any total.

- ⚠ **Buffs/debuffs are deliberately NOT diffed per power.** The rows carry
  provenance (`_debuff_buff_summary`'s dsrc/bsrc → `row.sources`) but the
  magnitudes come from `_resolve_mag` — base scale × table, **no slot boosts** —
  so a re-solve can never move them and every row would read 0.
- ⚠ **That is also a real gap worth ruling on:** the whole buff/debuff panel is
  unenhanced, so a debuffer who slots accurate defence-debuff or −regen sets
  sees nothing move anywhere. It hits the invisible-role doctrine hardest.
  Engine work, not display work — not started.
- Battery `tools/test_improve_diff.js` (**node**, 9 checks) lifts the REAL
  function out of app.js and drives it; takes an alternative app.js as `argv[2]`
  and was **proven against six sabotaged copies**, each caught by the right
  check. Verified end-to-end in the running app on a real Poison/Sonic solve.

## ✅ DONE: the four alignment wordmarks — `3a01bcf3`

Joel's `C:\Users\joelc\Downloads\Art\Hero Companion Wordmarks.html` is **not
four images** — it is text in **Anton** with a treatment per alignment, and it
ships its own header-size row. The app wears it as TEXT.

- Anton vendored (`static/vendor/anton-latin.woff2` + `anton-OFL.txt`, credited).
  ⚠ Vendored, never linked: the app has no network, a Google Fonts href renders
  nothing.
- **Each alignment needs its own `body.align-<key>` class** — theme-hero /
  theme-villain / align-mid make only three states and the two middles are
  different marks.
- **Sized to the space that was there** (his instruction). Sheet = 30px = 171px
  wide; old title = 136px; shipped at **20px = 132px**, masthead unchanged at
  47.5px. Widest name within 3px of before.
- Verified with EYES on the installed window, all four cycled via the View menu.
- ⚠⚠ **`push_statics.py` was copying static/'s TOP LEVEL ONLY** — `vendor/` and
  `icons/` never synced. The CSS reached both frozen copies, the font reached
  neither, and it printed "2 of 2 known copies updated" over the miss. Fixed to
  walk the tree ("N of 3100 files written"). Anything that ever lands in a
  static SUBDIRECTORY was previously invisible to both frozen copies.

Verification at close: `demo_single_build_fixes` 24/24 · `test_desktop_app`
121/121 · `audit_tour` all · `audit_tabs` 10/10 · `audit_links` 177 refs with 5
planted defects caught · `test_improve_diff` 9/9 + 6 sabotages.

# Resume point — 2026-08-05 late

## ▶▶ START HERE: the ROLE / OUTPUT arc, and the one thing left in it

Joel's live thread of work. Everything below is committed and pushed.

**Shipped today, in order:** role descriptions verified already-done · Split role
(renamed from "Mixed / Generalist", N-way not 2-way, every role offered grouped,
shares forced to total 100, new rows pick nothing) · the **"What this build
delivers today"** panel (real numbers per named job) · the **invitation** when a
build has no role · the **Enhancement Unslotter** footer (client-verified) · tour
cards for split-role, the output panel and the unslotter (63 steps) · and the
**improvement report generalised** to diff every measured axis.

**▶ THE BIG ASK — where it stands (Joel's own framing: "tell them how their
choices actually came out at the end", in real numbers, per power).**

| Piece | State |
|---|---|
| Before/after on every solve | ✅ EXISTS (`solveBefore` → `renderImproveDiff`) |
| Diff covers ANY measured axis | ✅ DONE today (`653d94f0`) — typed def/res, scalars, v30 families, ST/AoE DPS, **pet DPS**, every buff/debuff row |
| "Nothing moved" explains itself | ✅ DONE today (names locked-power count) |
| **Per-power deltas** ("Empty Clips +18 DPS") | ✅ DONE 2026-08-06 (`10a7ed0b`) — attacks by Cycled DPS + per hit, pets by their summoning power. Buffs/debuffs excluded on purpose (unenhanced magnitudes); see the 08-06 block at the top. |
| Preview a split WITHOUT committing | ❌ Not built. Today a solve commits; Ctrl+Z undoes and names the edit. **Design decision, not coding** — Joel's steer was to see whether (1)+(2) make it unnecessary. |

⚠ Cost of a comparison: one solve, ~1-2s, doubled by serve-time physics
arbitration. Fine behind a button; **never on slider drag.**
⚠ Joel's constraint on all of it: only what the game really offers, never an
invented scenario. The generalised diff satisfies that by construction — a row
can only appear if the engine measured it from game data.

# Resume point — 2026-08-05 evening

Tracked tree clean, master pushed, **HEAD = `0966af1d`**. Nothing running; no
scheduled tasks armed. A 25-point sweep at close confirmed every deliverable of
the day is present in the tree; full audit suite green (see below).

⚠ **Stage commits BY NAME here, never `git add -A`** — the tree carries hundreds
of untracked benchmark artifacts (swap sweeps, pyspy SVG, stray .bat launchers).
`-A` staged all of them on 2026-08-05; caught by the `--stat` size check.

**Installed app: `%LOCALAPPDATA%\Programs\HeroCompanion`, UNSIGNED dev build,
frozen stamp `297ddcf` + statics current with HEAD.** Release still HELD at
0.12.30.

⚠⚠ **TWO frozen copies exist** — the installer's (Joel's shortcut targets this
one) and `dist\HeroCompanion`. **Use `py tools\push_statics.py`**, which writes
both and prints a coverage denominator; a hand copy reaches one and makes
"verified" a lie. Then RELAUNCH — statics load at LAUNCH only (F5/Ctrl+R do
nothing in WebView2). **server.py / run_app.py changes need a full rebuild.**
`WScript.Shell.AppActivate($pid)` fronts the window.

## 🔨 A FROZEN REBUILD IS OWED BEFORE ANY OF TODAY'S SERVER WORK REACHES JOEL

`server.py` changed twice on 2026-08-05 and the frozen build predates both:
1. `_install_kind()` + the portable refusal in `/update/install`
2. `_SPECIAL_ORIGIN_SETS` → Hamidon/Hydra/Titan/D-Sync in `PIECE_BY_UID`
   (imported HOs showing their internal name)
Everything else from the day is static and is already live in both copies.

## Verification at close (2026-08-05)

`demo_single_build_fixes` 24/24 · `test_desktop_app` 121/121 ·
`test_mbd_alignment` 9/9 · `test_exemplar_view` 18/18 · `audit_tour` (12, incl.
2 new content checks) · `audit_tabs` 10/10 · `audit_links` 178 refs with 5
planted defects caught.

## ✅ DONE: the forum report (BasiliskXVIII, topic 64761) — `d026c05f`

Both claims closed, plus the disclosure pages and the Lite framing. Detail in
session-report.md. What survives as live state:

- **⏰ RELEASE STEP for 0.12.31:** `docs/index.html` currently discloses **0.12.30's**
  behaviour ("keeps running in your notification area after you close the window",
  Joel's ruling: today's truth, flip on release). That paragraph is wrong the
  moment 0.12.31 publishes — replace it with the window truth (close = quit) as
  part of the release.
- **✅ SETTLED: what a PORTABLE copy gets = the refusal + the download page, and
  nothing more** (Joel, 2026-08-05: "I am following your lead").
  `server._install_kind()` tells them apart by Inno's `unins000.exe` beside the
  exe (unreadable dir reads *portable*, so the failure mode is a refusal);
  `/update/install` refuses upstream of the Popen with the unzip-over-the-folder
  remedy. No installer button beside a routine update prompt, no zip
  self-update. ⚠ **Server-side ⇒ needs a frozen rebuild; reaches users only in
  0.12.31.**
- **The forum reply's "the update check only runs when you click it" is still
  uncorrected in public.** Accurate replacement drafted in session-report.md.
- Full app's logging choice now lives on the Logging tab (`gamelogChoiceRow()`):
  a visible "Turn it off" (the "on" state used to be a one-way door) and the
  start-with-Windows checkbox with a live clause saying what each state means.
  Same `playlogConsent`/`setAutostart` as before — no second copy of the choice.
  ⚠ `setAutostart` must re-render the surface it was clicked from; an
  unconditional `showAbout()` opens the About modal on top of the Logging tab.

## ✅ DONE: one import door + the Mids round trip — `e56b8f4c`

- The menu's two import items were the same thing; one remains, and it opens a
  panel that TEACHES both routes instead of throwing an OS file dialog.
- The Mids round trip is now pinned at 9 checks and is sound: pieces, order,
  engine totals and set bonuses all survive, and it converges at hop 2.
- **Fixed: special origins (HO/Hydra/Titan/D-Sync) came back labelled with their
  internal uid.** Root was `PIECE_BY_UID` being built from `ENH_SETS` only; all
  62 now register there, which fixes the in-game .txt path at the same time.
- ⚠ `server.py` changed ⇒ the HO fix needs a **frozen rebuild** to reach the
  installed app. The static half (panel, menu, tour) is already copied in.

## ✅ DONE: the 2026-08-05 UI pass (all pushed; detail in session-report.md)

- **Build menu**: Refine with AI removed (dead in an AI-free client); every gated
  item now says WHY it is greyed. ⚠ The reported "cancel greys the menu" was NOT
  a state bug — reproduced identical before and after cancelling; the silence was
  the defect.
- **View menu**: End Game and Layout mode removed; **Exemplared view opens a
  dialog** that explains exemplaring before asking for a level.
- **Help menu**: Settings / Credits / About as three doors; Settings gained the
  Play Log switch. No tray toggle — the app has no icon and says so.
- **Pop-ups wear the alignment** (one `--accent` rule, all three shapes).
- **Leveling Guide**: side-preview menu moved under the title, Flashback
  explained; preview resets on leaving the tab AND yields to the real toggle.
- **Inherent → Archetype bonus stat** above Defence.
- **Small displays**: both two-column regions collapse below 1400px.
- **Level warning carries its own input**, and the crash it hit is fixed.
- **Tour**: 4 stale bodies + a misplaced mock element corrected; audit_tour now
  checks CONTENT, not just structure.

## ✉️ THE FORUM THREAD (topic 64761) — v5 REPLY DRAFTED, NOT SENT

⚠⚠ **THE v4 DRAFT (session-report, 2026-08-02) IS NOW DANGEROUS TO POST** — the
rebuild made four of its claims false ("The app lives in your system tray", "the
update check only runs when you click it", "the planner does not understand
exemping at all", plus two promises now delivered). **Use v5** (session-report,
2026-08-05), written in the cheeky-Australian voice Joel asked for, no em dashes.

⚠ **Governing fact for anything posted: 0.12.30 shipped 7/31, Basilisk posted
8/2, and every fix landed after. Nothing he can download today has any of it.**
The reply must say "next release" and never imply otherwise.

**✅ RETRACTED — THE ROLE PROMISE WAS KEPT, AND I SAID OTHERWISE.** I reported it
as the one unkept promise on the strength of a grep that searched lowercase for a
constant named `ROLE_HELP`. It was all done on 2026-08-02, and better than
promised — **screenshot-verified live**: `ROLE_HELP` gives every role a plain
sentence with the solver's REAL floors ("Mixed role: no specialisation on
purpose. Just a safety floor, recharge 70%, recovery 40%…"), rendered under the
picker with the numbers beside it; `renderRoleOptions` GROUPS the list per
archetype ("Natural for a Defender" / "Off-role — allowed, but it will fight
you" / "No single focus"); **the Mixed nag is exempted** (`if (role === "mixed")
return;`) so a Generalist no longer earns a warning it could never clear; and
`renderRoleFocusSplit` answers his Corruptor split-attention question with an
actual percentage slider. Sonic Resonance is answered too: Debuffer and Buffer
carry IDENTICAL weights in `ROLE_WEIGHTS` (0.15 / 1.00 / 1.00), so a set that
does both does not force a wrong choice.
⚠ **Lesson, twice today: a grep is a hypothesis.** Run the app before reporting
something missing.

**❌ Still genuinely open:** Troo's "manually selecting enhancements is harder
than it needs to be". ⚠ Unverified: his "low-contrast greys on light blues" — no
contrast audit exists, so do NOT claim it fixed.

✅ Everything else he raised is fixed and waiting on the release: tray, portable
update, tabs, assistant placement, type scale, verbose text, export button,
targeted level, Mighty Leap/Speed of Sound, Panacea. The separate Web3Forms
report (D:\CoH\Homecoming accounts folder) was already fixed 2026-08-03 — the
folder was found and the MESSAGE lied about it.

**▶ OPEN, needing Joel:**
1. **"Build this for me"** is dead in the shipped client for the same reason the
   AI item was (`gen-btn` hides whenever `AI_ON` is false). Point it at the
   wizard, or remove it. His call.
2. **Applying a meter to DISPLAYED damage** (Vigilance +30% solo). It is in the
   SCORE, not the shown DPS. Team-size dependent, so it needs a ruling —
   recommended: ride alongside, never replace (suppression precedent).
3. **"What changed?" / per-change history** — his idea of a change log per
   character with individually revertible entries. Not built; needs scoping.

## What landed the session before (all pushed)

- **Tabs are manila folders** in a filing cabinet: filed tabs sit lower in a darker
  color-mix of the active accent, the pulled one stands proud, labels typed on.
- **The tab's line owns its content**: `var(--accent)`, along the BOTTOM of the
  strip, down the sides through the build tile, closing under the panel — nothing
  drawn above the tabs, no gap. All four alignments carry it.
- **Menus**: right-anchored so they cannot clip; an open menu draws a dimmed
  per-theme edge that meets its panel; nothing at all until one is opened.
- **No sideways scrolling**: incarnate selects were 137px boxes holding 275px of
  option text. The road and the tab strip stay the only horizontal surfaces.
- **Alignment**: all four listed in the View menu under a heading, floating picker
  deleted; the middles' bright masthead line darkened to their own `--border`.
- **Stats**: every row is name · one-line meaning · number (49 rows, none blank),
  one type scale (was 6 sizes, now 4), and the offense board matches.
- **Stats ⓘ** now opens where the user is (it was rendering onto a hidden tab),
  breakdown slots say they are live, and **Ctrl+Z asks and names the edit** it will
  take back, skipping no-op snapshots.
- Tour caught up to 61 steps; layout mode is resize + hide only.

## ▶ Open queue

1. The catalogue's last empty cell (leave / one row of seven / epic spans it).
2. His layout draft whenever he wants: drag corners, ✕ hide, 📋 Copy, paste to me.
3. Set-bonuses-in-force + rule-of-five meter; "Gear this build" card; origin
   plates; `extract_power_icons.py` i24 glob bug.
4. Release when he says: rebuild the frozen exe first (statics + server drift),
   and flip the 0.12.30 disclosure paragraph in `docs/index.html` in the same pass.
5. Standing: verdict-gate legality hole, Iron Man accolade check, gaming box silent
   since 07-29, exploration-log parse.

## Session-local facts worth keeping

- `saves/poison-defender.json` in the repo is a COPY of his Joinny Healer save so
  the dev copy on 5081 has a real 9-box build to measure. Gitignored.
- Loop: dev server on 5081 + the Claude Browser pane for JS geometry (it lays out
  and runs JS **only while the pane is displayed**, never screenshots, and **never
  runs transitions or ResizeObservers**), then the frozen app + computer-use for
  eyes.
- ⚠ **Measure the width the USER has** (a rule set from a 1920 pane did the
  opposite of what he asked at his 1250 window).
- ⚠ **A var() inside a custom property resolves where it is DECLARED** — a `:root`
  token built on `var(--accent)` cannot follow a body-level theme.
- ⚠ **Test input with a real mouse**, never `dispatchEvent`; Escape never reaches
  the page in this shell.
