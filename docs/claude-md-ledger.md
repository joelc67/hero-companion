# CLAUDE.md ledger — superseded history moved out of the always-loaded file

Moved 2026-08-14 from coh-builder/CLAUDE.md on Joel's ruling: embed old knowledge
in the repo + graphify instead of the per-session context. Content verbatim,
nothing edited. CLAUDE.md keeps standing rules; this file keeps the history.

- **⏰ (superseded, kept for the reasoning) RE-ENABLE THE INBOX WORKFLOWS ON 2026-08-01 (both `disabled_manually` since 2026-07-27).** `gh workflow enable "Collect mailbox" --repo joelc67/hero-companion-inbox` and the same for `"Inbox maintenance"`. **Why disabled:** the private repo's billed Actions minutes ran out after the 7/14 runaway; from 7/16 every scheduled run failed at startup in 2-4s with zero steps and mailed Joel each morning. Nothing lost. **Cost was always $0** (GitHub Free refuses to start jobs rather than bill; billing page: gross $53.32 fully offset, billed $0 every day). **Leave the spending limit at $0 — that is what guarantees it can never cost money.** After re-enabling, confirm the next scheduled run succeeds; failing in seconds with zero steps = allowance not reset. ⚠ Do NOT "fix" this in the workflow files — there is no workflow bug. ⚠ Billing API needs gh `user` scope (not granted; don't re-auth).

## Project history (condensed; transcripts in ~/.claude/projects/, memory files in ~/.claude/projects/C--Users-joelc-code/memory/)

- **2026-06-16→19**: Flask+vanilla-JS prototype from Mids .mhd data → the solver thesis ("it's an equation — 3D chess") → ILP (PuLP/CBC); AI generation removed from the client; costume side-quest killed (parked `_archive_costume/`).
- **2026-06-29→07-02**: import & correctness era (unique flags, in-game .txt + .mbd round-trip, preserve modes, per-AT caps); the COMPANION pivot (entry cards, discovery, 1-50 stepper); role system + first_principles encounter model + deep_optimize + learning stack; model v10→v23; masters corpus as the floor.
- **2026-07-03 LAUNCH**: repo public, HC forum topic 64761 (as Pulsekin), LICENSE/TERMS/CREDITS/help PDF, AI-free client (`HC_AI=1` seam), 0.9.0→0.10.0 (installer/tray/self-update).
- **2026-07-04→08**: Guyver's 4,187 builds → v24; masonry UI; slot-grant schedule; Maelwys rounds 1-2 → game-client bins became the authoritative source; henchmen priced from live game; 0.12.9→0.12.15 ("verified-data release"); regression day fixes behind demo_single_build_fixes.
- **Release ledger since:** 0.12.16 "inheritance" (7/09, v29 henchman set-bonus inheritance + heal-strength) · 0.12.17 "display-only" (7/10, custom targets + booster preview + Power Boost amplifier + IO detail cards) · 0.12.18-0.12.20 (v30-v31, roster split, ladder-fit gate, AFK farm champion "+3x8" honest label) · 0.12.22 "FIRST SIGNED" (7/21, v34 MM pet-buff; release-night walk loop = 4 pinned class fixes incl. the invisible-confirm hang) · 0.12.23 (7/21, v35 endurance physics + full-roster wave + Build-Assistant locks/targets) · 0.12.24 (7/23, Leveling Journey v1 + wizard one-copy + farm gates + v36 meters + opt-in auto-start) · 0.12.25 "THE JOURNEY GROWS UP" (7/23, zone splash art + badge locations/directions + TF levels + challenge checklists + con reads + routes + alignment preview) · 0.12.26 (7/24, Web3Forms in-app bug reports + power icons 4949→6033 via patch/extract pipeline + Journey polish + Play Log dedup) · 0.12.27 (7/26, refuse-with-remedy fixes for legendaryjman + Troo — first release driven entirely by field reports) · 0.12.28 "security" (7/27, escHtml/XSS/realpath/stack-trace fixes) · **0.12.29 "The guided tour" (7/27T22:58Z, af28d2bf: 56-step tour + CSRF guard + corrected help)** · 0.12.30 "Accuracy pass" (7/31, v38 + 24/24 recert) · **0.12.32 "The Stats page becomes a workbench" (8/06T23:02Z, e164fd13: per-IO worth measured by counterfactual + Swap/Remove in place + the universal edit receipt with Undo + the swap picker pricing every candidate via `/build/slot_compare` + the unique-once-per-build picker gate + the green-marks legend + the 390-badge catalogue with `/thumbtack` rows + Flashback landing + honest empty art states + the exploration-log streaming read (89.3s/6.17GB → 29.3s/393MB, byte-identical) + reduced motion reaching the JS scrolls; data 2026.1.1242 and model v38 BOTH unchanged, so no score moves)** · **0.12.33 "Knowing what to do next" (8/07T22:35Z, 898653a: the order-to-work-in band + tour step, the Assistant/Stats ledes, the epic-swap refill, the Gymnastics repair, the phantom receipt + undo-stack leak + per-character sweep, the three panel outlines; data 2026.1.1242 and model v38 unchanged, zero champion exposure on the one data edit)** · **0.12.31 "The desktop app" (8/05T20:35 ET, b2161e12: WebView2 window/no tray, four tabs, four-way alignment + wordmarks + emblems, exemplar arc, split role + output panel, per-power improvement report, buff/debuff reads slotting incl. recharge, one import door + Mids round-trip pin + special-origin names, portable-update refusal, rebuilt 63-step tour, 94 Alpha icons; docs/index.html disclosure flipped to the window truth in the same pass)**. All signed CN=Joel Andrew Chambers from 0.12.22 on; every release: frozen smoke + gold 24/24 SERVED; data currency 2026.1.1242 / model v38 since 0.12.30.


- **🖼 (history) the filler's three failed rounds.** The
  art is REAL and now extracted (`charectercreationui/archetypescreenshotsassets`,
  512×512 × 3 shots × 16 ATs; `extract_gui_emblems.py` pulls shot 0 to
  `static/icons/at_art/`, 15 of 16 — Guardian has none). The PLACEMENT never
  painted in the frozen shell: panel background + blend, absolute `::after` at
  0.16, then 0.55 with no mask — because all three were anchored to
  **`#powers-list`, which holds the wall AND the catalogue**, so bottom-right of
  it is the bottom of the CATALOGUE, nowhere near the hole. Joel spotted it
  ("I saw one image for one build but it was small") and that one sentence
  located the bug three measurement rounds could not. **Anchor to
  `.powers-wall`**, size to the hole its last row leaves (measured 978×152),
  `z-index:-1` inside the wall's own stacking context so the opaque cards mask
  it. ⚠ The textures are a ~512×314 picture **padded to a power of two with a
  flat block** — `contain` fitted the pad and put a blue slab on screen; the
  extractor crops it now. ⚠ A cropped BAND fills the strip but the crop lands
  differently per class (Defender lost its legs, Brute lost its heads), so it
  fits by HEIGHT and shows whole at ~245px. ⚠ A dead `.cat-art` rule proved an
  EARLIER session tried this and abandoned it. **Generalize: when three
  measurement rounds disagree with the screen, the thing being measured is the
  wrong element.**

- **(superseded) the 2026-08-07 report.** The client ships, per power,
  self-targeted `Strength` templates across all EIGHT damage types (scale 0.8
  and 4.0, duration 15s/30s) beside the ToHit ones. **Our records carry only the
  ToHit half.** Verified on Aim, Build Up, Rage, Follow Up, Power Build Up, Soul
  Drain, Spirit Drain: 6 of 6 have no self +Damage. Root cause is the known
  `parse_mids` Enhancement-relabel allowlist — ToHit is in it, **Damage is
  not** — the same family as the v28 accuracy and v29 heal-strength bugs, but
  far wider than the queue records. **THE CODE ALREADY KNOWS**: server.py's
  `_DMG_ENABLER_NAMES` comment says *"the data files these outside buff_effects
  … Build Up/Soul Drain in self ToHit, so detect by name"*, and it compensates
  BY NAME at the picker (`_ps_priority` +9) and the slotter (`is_steroid`) — so
  these powers get taken and slotted while the MAGNITUDE is never modelled.
  **MEASURED through /build/calculate: adding Aim moves displayed ST DPS by
  0.0.** Exposure, counted over 624 picks: Build Up in 6 champions, Aim in 2 =
  **7 of 24 certified champions**, so crediting it is a MODEL BUMP owing a
  re-cert — Joel's ruling. ⚠ **It is the same capability as Fury / Power Boost
  and must be built with them**: a temporary MODE with an uptime, not a flat
  add. Maelwys's point (a 240s Soul Drain cannot be cycled with a nuke while a
  120s Spirit Drain can) is this same gap seen from the gameplay side — our
  picker scores both at 19.0 because with no magnitude and no uptime the only
  lever left is a name in a list.

## 🧱 (superseded) THE PERFECT WALL packer (2026-08-04 night, 472a76a3)

"Open all the drop downs on the first tab, then move the items around until
they fit into a perfect wall with zero gaps any where." The architecture:
- **All folds default OPEN** (`_foldOpen`: absent key = open; explicit closes
  remembered). The wall is judged with everything expanded.
- **packPowersTab()** seats the two COLUMN TILES (#endgame-plan-panel,
  #endgame-panel) into whichever column is currently shorter — measured
  live, on render/recompute/toggle/resize/tab-arrival (hidden tab = zero
  geometry, skip). The balanceColumns lesson: measure, never predict.
- **BASE SLABS**: trays, level plan, converters are giant references — in a
  column any one strands a void. They sit FULL WIDTH under the columns where
  their content flows horizontally (the wide-brick CSS: the 24-row respec
  order becomes a 5-across course). ⚠ Found twice the hard way: conv guide
  first, level plan second — a "tile" taller than everything else can never
  be balanced; promote it to a slab.
- **GROUT**: each column's last tile stretches to the shared bottom edge
  (`.powers-main/.powers-side > :last-child { flex: 1 0 auto }`) — the
  residual discrete tiles can't split is panel surface, never raw page.
- The builder flex-stretch rule is DELETED (it painted the void); the 3-up
  fold row is gone; accolades are a free tile in index.html again.


- **🧾 v38+HO WAVE COMPLETE 24/24 — ✅ MERGED (superseded by the 2026-07-31 recert above; kept for the deltas).** `recert_verdicts.json` (written 2026-07-30 00:10): **4 SUPERSEDE** (Crab_Spider_Soldier +181.3 — this also CLOSES the named autopick defect that failed every leg of the previous wave · Spines/Fiery_Aura +92.4 · Poison/Sonic_Attack +50.9 · Broad_Sword/Super_Reflexes +4.1) / **20 KEEP**, zero collapsed runs, zero eval failures. The gate re-scores BOTH sides fresh under v38 (canonical vs canonical, CBC pinned) so the deltas are real; a mostly-KEEP outcome is the NORMAL shape of a recert wave (the prior wave was 3/20), not a defect. Large negatives cluster on Kheldian per-form contexts, where the form context BANS powers the incumbent build holds — the recert searches a strictly smaller space and cannot win by construction. **Merge = by context, `--verdicts`, canonical winner kept, shards retired `.merged_2026-07-30` — awaits Joel's word.**

- **Wave-run history worth keeping:** ran across the laptop + gaming box; the box was stopped mid-order and its 2 finished champions came home via the new orphan-rescue (2505c2a0) rather than being lost. Drop-dead pauses fired clean twice (4:10 PM, then armed 6 AM). ⚠ `bench_solver_e2e` running beside the wave killed 10 in-flight contexts — several hours of compute, nothing corrupted; see the speed-ledger guard warning.

