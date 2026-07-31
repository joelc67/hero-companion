# Resume point — 2026-07-31 6:34 AM (machine going to work)

Nothing is running. No scheduled tasks armed. Working tree clean; everything
committed and pushed through the item-6 remainder commit. Safe to power off.

## Where things stand

Engine-accuracy work order items 1-5: DONE and proven. Item 6 (roster
re-certification): 23 of 24 contexts re-certified under the new solver.

**Awaiting Joel's word — nothing below has been done:**

1. **Merge the 6 supersedes** from the item-6 remainder wave:
   Crab Spider +248.9 - PB nova +391.2 - Poison/Sonic +131.6 -
   WS dwarf +85.6 - Sentinel Fire/Willpower +77.7 - Rad/Sonic +55.9.
   Command shape (the two supersedes from the movers wave already merged
   this way, 73aaab77):
     py tools\merge_champion_shards.py --replace --verdicts recert_verdicts.json <shards holding ONLY superseding contexts>
   Then validate_champions, then retire each shard (.merged_YYYY-MM-DD /
   .kept_incumbent_YYYY-MM-DD). MERGE BY CONTEXT — several i6r shards hold a
   mix of supersede and keep contexts, so they must be split, not merged
   wholesale.
   IMPORTANT: recert_verdicts.json currently holds the 17-context table.
   Regenerate it over every shard being merged before merging (the tool
   OVERWRITES per invocation).

2. **Finish Peacebringer dwarf** — the only context of the 18 that did not
   converge (mid-flight at the 5:30 pause, nothing lost). Resume with a
   DISTINCT shard prefix (collision rule):
     py tools\converge_parallel.py --recert --workers 1 --shard-prefix champions_shard_i6r_pbd --keys "Class_Peacebringer|Peacebringer_Offensive.Luminous_Blast|Peacebringer_Defensive.Luminous_Aura|itrial|dwarf"
   Launch detached (scheduled task + launch_hidden.vbs), trigger ONLY —
   never also Start-ScheduledTask (double-fire, cost recorded in CLAUDE.md).

3. **The gaming box never woke** all night: order sat unclaimed 4h15m, last
   heartbeat 2026-07-29 11:51 AM. Its 6 contexts were run on the laptop
   instead. Check the box (powered on? HC_RemoteWorker task alive?) before
   the next wave counts on it.

4. Optional, never started: the strict-dominance column-reduction attempt
   (the one unmeasured solver speed lever).

## Shards on disk = the save file. Do not delete.

  champions_shard_i6r_split1_p0-p3.json   12 contexts (laptop slice)
  champions_shard_i6rbox_p0-p2.json        5 contexts (relocated box slice)
  champions_shard_abmov_*.merged_2026-07-30 / .kept_incumbent_2026-07-30
                                           movers wave, already dispositioned

## Also staged, unreleased (Joel's release hold stands)

  Mids .mbd export alignment-casing fix (field report) + its 4-check battery,
  plus everything from the slotting-judgment batch. No release without his word.
