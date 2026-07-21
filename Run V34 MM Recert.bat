@echo off
rem ============================================================================
rem v34 (#13 pet-buff batch) — re-convergence of the 9 evaluate-first MOVERS.
rem DETACHED + shards-only (NO --merge): the shard discipline (2026-07-16) forbids
rem wholesale merge; each context is verdict-checked (evaluate-first canonical-vs-
rem canonical) and the CANONICAL WINNER kept before anything merges to main.
rem
rem Game-first gate SATISFIED before launch (2026-07-20): copy_boosts=True on every
rem moved context's pets (Fallout/Carrion Creepers/Ice Elemental incl.) confirms the
rem game copies caster buff/boost state to them, so the pet-buff term's crediting is
rem honest — the 9-mover list is verified, not memory-tier.
rem
rem Node-capped per the certification-sweep rule (deterministic; the winner always
rem re-solves uncapped inside deep_optimize).
rem ============================================================================
cd /d %~dp0
set "PYTHON=python"
where python >nul 2>nul || set "PYTHON=C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe"
set "HC_SOLVER_NODE_CAP=50000"
echo Started: %DATE% %TIME% > v34_mm_recert_log.txt
"%PYTHON%" tools\converge_parallel.py --recert --workers 4 --shard-prefix champions_shard_v34mm --keys "Class_Arachnos_Soldier|Arachnos_Soldiers.Crab_Spider_Soldier|Training_Gadgets.Crab_Spider_Training|itrial,Class_Controller|Controller_Control.Plant_Control|Controller_Buff.Poison|itrial,Class_Defender|Defender_Buff.Poison|Defender_Ranged.Sonic_Attack|itrial,Class_Defender|Defender_Buff.Radiation_Emission|Defender_Ranged.Radiation_Blast|itrial,Class_Defender|Defender_Buff.Radiation_Emission|Defender_Ranged.Sonic_Attack|itrial,Class_Mastermind|Mastermind_Summon.Demon_Summoning|Mastermind_Buff.Radiation_Emission|itrial,Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial|dwarf,Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial|nova,Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial|triform" >> v34_mm_recert_log.txt 2>&1
echo Finished: %DATE% %TIME% >> v34_mm_recert_log.txt
