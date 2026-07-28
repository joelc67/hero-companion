@echo off
rem ============================================================================
rem v38+HO COMBINED CERTIFICATION WAVE (2026-07-28, Joel's "Run the wave").
rem The slotting-judgment batch finale: Piece 2 (MODEL v38 pet hit chance) +
rem Piece 3 (HO solver options, R2 endgame gate). ALL 24 certified contexts are
rem itrial/farm content, so the HO gate alone makes the whole roster movers;
rem the pet contexts (MM, pet controllers, Crab Spider...) ride along under v38.
rem
rem DETACHED + shards-only (NO --merge), per the 2026-07-16 shard discipline:
rem merge BY CONTEXT, verdict (recert_verdicts/evaluate_first) BEFORE anything
rem touches champions.json; verdict table goes to Joel first. Node-capped per
rem the certification-sweep rule (winner re-solves uncapped in deep_optimize).
rem While this runs, champions.json + shards belong to THIS process.
rem ============================================================================
cd /d %~dp0
set "PYTHON=python"
where python >nul 2>nul || set "PYTHON=C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe"
set "HC_SOLVER_NODE_CAP=50000"
echo ===== v38+HO wave launch %DATE% %TIME% ===== >> wave_v38ho.log
"%PYTHON%" tools\converge_parallel.py --recert --workers 6 --shard-prefix champions_shard_v38ho --keys "Class_Arachnos_Soldier|Arachnos_Soldiers.Crab_Spider_Soldier|Training_Gadgets.Crab_Spider_Training|itrial,Class_Arachnos_Widow|Widow_Training.Night_Widow_Training|Teamwork.Widow_Teamwork|itrial,Class_Blaster|Blaster_Ranged.Fire_Blast|Blaster_Support.Energy_Manipulation|itrial,Class_Brute|Brute_Melee.Battle_Axe|Brute_Defense.Fiery_Aura|itrial,Class_Brute|Brute_Melee.Spines|Brute_Defense.Fiery_Aura|farm_afk,Class_Controller|Controller_Control.Plant_Control|Controller_Buff.Poison|itrial,Class_Corruptor|Corruptor_Ranged.Water_Blast|Corruptor_Buff.Kinetics|itrial,Class_Defender|Defender_Buff.Poison|Defender_Ranged.Sonic_Attack|itrial,Class_Defender|Defender_Buff.Radiation_Emission|Defender_Ranged.Radiation_Blast|itrial,Class_Defender|Defender_Buff.Radiation_Emission|Defender_Ranged.Sonic_Attack|itrial,Class_Dominator|Dominator_Control.Mind_Control|Dominator_Assault.Fiery_Assault|itrial,Class_Mastermind|Mastermind_Summon.Demon_Summoning|Mastermind_Buff.Radiation_Emission|itrial,Class_Peacebringer|Peacebringer_Offensive.Luminous_Blast|Peacebringer_Defensive.Luminous_Aura|itrial,Class_Peacebringer|Peacebringer_Offensive.Luminous_Blast|Peacebringer_Defensive.Luminous_Aura|itrial|dwarf,Class_Peacebringer|Peacebringer_Offensive.Luminous_Blast|Peacebringer_Defensive.Luminous_Aura|itrial|nova,Class_Peacebringer|Peacebringer_Offensive.Luminous_Blast|Peacebringer_Defensive.Luminous_Aura|itrial|triform,Class_Scrapper|Scrapper_Melee.Broad_Sword|Scrapper_Defense.Super_Reflexes|itrial,Class_Sentinel|Sentinel_Ranged.Fire_Blast|Sentinel_Defense.Willpower|itrial,Class_Stalker|Stalker_Melee.Radiation_Melee|Stalker_Defense.Dark_Armor|itrial,Class_Tanker|Tanker_Defense.Invulnerability|Tanker_Melee.Super_Strength|itrial,Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial,Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial|dwarf,Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial|nova,Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial|triform" >> wave_v38ho.log 2>&1
echo ===== wave exited %ERRORLEVEL% at %DATE% %TIME% ===== >> wave_v38ho.log
