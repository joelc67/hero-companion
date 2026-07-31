@echo off
rem ============================================================================
rem I6R BOX SLICE, RUN LOCALLY (2026-07-30 ~11:45 PM). The gaming box never
rem woke: its order sat unclaimed 4h15m and its last heartbeat was 7/29. Three
rem of the laptop's four workers finished and went idle while these 6 contexts
rem sat unstarted — idling capacity is exactly what the fleet rule forbids, so
rem the laptop takes them. The order was WITHDRAWN first (renamed .withdrawn),
rem so the box can never claim these and duplicate the work.
rem
rem DISTINCT shard prefix (i6rbox) per the collision rule — the split1 workers
rem are still live on Peacebringer triform. --sweep-workers 5 keeps total
rem threads (~22) under the core count so the triform heavyweight is not
rem starved. Same contract: --recert, NO merge, verdict table to Joel.
rem Hard pause 5:30 AM already armed (HC_I6R_Pause_530) and covers these too.
rem ============================================================================
cd /d %~dp0
set "PYTHON=python"
where python >nul 2>nul || set "PYTHON=C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe"
set "HC_SOLVER_NODE_CAP=50000"
echo ===== I6R box-slice-local launch %DATE% %TIME% ===== >> wave_i6r.log
"%PYTHON%" tools\converge_parallel.py --recert --workers 3 --sweep-workers 5 --shard-prefix champions_shard_i6rbox --keys "Class_Peacebringer|Peacebringer_Offensive.Luminous_Blast|Peacebringer_Defensive.Luminous_Aura|itrial|dwarf,Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial|triform,Class_Tanker|Tanker_Defense.Invulnerability|Tanker_Melee.Super_Strength|itrial,Class_Dominator|Dominator_Control.Mind_Control|Dominator_Assault.Fiery_Assault|itrial,Class_Defender|Defender_Buff.Radiation_Emission|Defender_Ranged.Radiation_Blast|itrial,Class_Defender|Defender_Buff.Radiation_Emission|Defender_Ranged.Sonic_Attack|itrial" >> wave_i6r.log 2>&1
echo ===== I6R box-slice-local exited %ERRORLEVEL% at %DATE% %TIME% ===== >> wave_i6r.log
