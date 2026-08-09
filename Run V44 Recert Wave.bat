@echo off
rem ============================================================================
rem v43+v44 RE-CERTIFICATION WAVE (2026-08-09, Joel's "run the re-cert wave").
rem 19 of 24 contexts, MEASURED not assumed: the union of every context holding
rem a power touched by v40 slow-resist (8), v41 DDR (9), v42's RechargeTime fix
rem (17), v43 Domination (1) and v44 crits (2). The other FIVE are owed nothing
rem and their incumbents stand untouched.
rem
rem --recert is deliberate: it BYPASSES certified_union, which matters here
rem because 26 stale root shards shadow all 19 keys, so a plain --keys run would
rem have silently skipped the ENTIRE wave. Those shards still need retiring
rem before the verdict step.
rem
rem DETACHED + shards-only (NO --merge), per the 2026-07-16 shard discipline:
rem verdict BY CONTEXT before anything touches champions.json, and the verdict
rem table goes to Joel first. Node-capped per the certification-sweep rule.
rem While this runs, champions.json + shards belong to THIS process.
rem Laptop-only: the gaming box has written no heartbeat since 2026-07-29 and
rem its last order was withdrawn, so there is no healthy worker to split to.
rem ============================================================================
cd /d %~dp0
set "PYTHON=python"
where python >nul 2>nul || set "PYTHON=C:\\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe"
set "HC_SOLVER_NODE_CAP=50000"
echo ===== v43+v44 recert wave launch %DATE% %TIME% ===== >> wave_v44.log
"%PYTHON%" tools\converge_parallel.py --recert --workers 6 --shard-prefix champions_shard_v44 --keys "Class_Arachnos_Soldier|Arachnos_Soldiers.Crab_Spider_Soldier|Training_Gadgets.Crab_Spider_Training|itrial,Class_Arachnos_Widow|Widow_Training.Night_Widow_Training|Teamwork.Widow_Teamwork|itrial,Class_Blaster|Blaster_Ranged.Fire_Blast|Blaster_Support.Energy_Manipulation|itrial,Class_Brute|Brute_Melee.Battle_Axe|Brute_Defense.Fiery_Aura|itrial,Class_Corruptor|Corruptor_Ranged.Water_Blast|Corruptor_Buff.Kinetics|itrial,Class_Defender|Defender_Buff.Poison|Defender_Ranged.Sonic_Attack|itrial,Class_Defender|Defender_Buff.Radiation_Emission|Defender_Ranged.Radiation_Blast|itrial,Class_Dominator|Dominator_Control.Mind_Control|Dominator_Assault.Fiery_Assault|itrial,Class_Peacebringer|Peacebringer_Offensive.Luminous_Blast|Peacebringer_Defensive.Luminous_Aura|itrial,Class_Peacebringer|Peacebringer_Offensive.Luminous_Blast|Peacebringer_Defensive.Luminous_Aura|itrial|dwarf,Class_Peacebringer|Peacebringer_Offensive.Luminous_Blast|Peacebringer_Defensive.Luminous_Aura|itrial|nova,Class_Peacebringer|Peacebringer_Offensive.Luminous_Blast|Peacebringer_Defensive.Luminous_Aura|itrial|triform,Class_Scrapper|Scrapper_Melee.Broad_Sword|Scrapper_Defense.Super_Reflexes|itrial,Class_Sentinel|Sentinel_Ranged.Fire_Blast|Sentinel_Defense.Willpower|itrial,Class_Stalker|Stalker_Melee.Radiation_Melee|Stalker_Defense.Dark_Armor|itrial,Class_Tanker|Tanker_Defense.Invulnerability|Tanker_Melee.Super_Strength|itrial,Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial|dwarf,Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial|nova,Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial|triform" >> wave_v44.log 2>&1
echo ===== wave exited %ERRORLEVEL% at %DATE% %TIME% ===== >> wave_v44.log
