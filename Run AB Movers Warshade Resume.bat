@echo off
rem Resume of the movers wave's 6th context (2026-07-30): Warshade base itrial
rem was mid-flight at the armed 4:05 PM pause. Distinct shard prefix per the
rem shard-prefix-collision rule (a resumed wave with fewer workers reassigns
rem _pN). Same contract as the wave: --recert, NO --merge, verdict before
rem anything touches champions.json.
cd /d %~dp0
set "PYTHON=python"
where python >nul 2>nul || set "PYTHON=C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe"
set "HC_SOLVER_NODE_CAP=50000"
echo ===== AB movers WARSHADE RESUME launch %DATE% %TIME% ===== >> wave_abmov.log
"%PYTHON%" tools\converge_parallel.py --recert --workers 1 --shard-prefix champions_shard_abmov_ws --keys "Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial" >> wave_abmov.log 2>&1
echo ===== WARSHADE RESUME exited %ERRORLEVEL% at %DATE% %TIME% ===== >> wave_abmov.log
