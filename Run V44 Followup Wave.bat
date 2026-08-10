@echo off
rem ============================================================================
rem v44 FOLLOW-UP WAVE (2026-08-09) - the 5 contexts the first wave MISSED.
rem
rem The first wave was scoped by 'does this build HOLD a power carrying a new
rem row?' and got 19. evaluate_first then showed 16 canonical scores moved, and
rem FIVE were contexts that test had excluded. Holding a patched power is
rem SUFFICIENT but not NECESSARY: v42's RechargeTime fix reaches timed PET
rem uptime (hence the Mastermind and the farm build) and scenario channels move
rem scores with no patched power picked at all.
rem
rem These five have a REFRESHED canonical against a build never re-converged
rem under v44. That is what this wave fixes.
rem   Spines/Fiery_Aura [farm_afk]        375.9 ->  227.6  (-148.3)
rem   Radiation_Emission/Sonic_Attack    1644.2 -> 1739.0   (+94.8)
rem   Umbral_Blast/Umbral_Aura [base]    1452.6 -> 1361.7   (-90.9)
rem   Demon_Summoning/Radiation_Emission 1275.8 -> 1330.7   (+54.9)
rem   Plant_Control/Poison               1808.1 -> 1773.2   (-34.9)
rem
rem DETACHED, shards-only (NO --merge). Verdict by context, table to Joel, and
rem champions.json commits only after his word. One worker per context so no
rem context waits behind another; 6 sweep threads each of 32 logical cores.
rem ============================================================================
cd /d %~dp0
set "PYTHON=python"
where python >nul 2>nul || set "PYTHON=C:\\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe"
set "HC_SOLVER_NODE_CAP=50000"
echo ===== v44 follow-up wave launch %DATE% %TIME% ===== >> wave_v44b.log
"%PYTHON%" tools\converge_parallel.py --recert --workers 5 --shard-prefix champions_shard_v44b --keys "Class_Brute|Brute_Melee.Spines|Brute_Defense.Fiery_Aura|farm_afk,Class_Controller|Controller_Control.Plant_Control|Controller_Buff.Poison|itrial,Class_Defender|Defender_Buff.Radiation_Emission|Defender_Ranged.Sonic_Attack|itrial,Class_Mastermind|Mastermind_Summon.Demon_Summoning|Mastermind_Buff.Radiation_Emission|itrial,Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial" >> wave_v44b.log 2>&1
echo ===== wave exited %ERRORLEVEL% at %DATE% %TIME% ===== >> wave_v44b.log
