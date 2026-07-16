@echo off
rem ============================================================================
rem Rad/FA farm_active RE-CONVERGENCE - DETACHED launcher (2026-07-16 night).
rem The held shard is retired to .held_search_defect_2026-07-16 (out of the
rem union), so this context re-converges from scratch; the standing mechanics
rem apply (node cap on sweep candidates, winner re-solved uncapped).
rem Joel's ruling 7/16 evening: this runs TONIGHT under the current search;
rem the one-objective fix is tomorrow's engineering, not a gate on this run.
rem Merge rules: BY CONTEXT, verdict before --write, evaluate-first gate -
rem a canonically-worse fresh run never supersedes an incumbent.
rem Launched via a Windows scheduled task (NOT Start-Process): the detached
rem Start-Process pattern failed to survive twice on 2026-07-16.
rem ============================================================================
cd /d %~dp0
set "PYTHON=python"
where python >nul 2>nul || set "PYTHON=C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe"

echo ===== farm_active v34 recert launch %DATE% %TIME% ===== >> farm_active_v34.log
"%PYTHON%" tools\converge_parallel.py ^
  --keys "Class_Brute|Brute_Melee.Radiation_Melee|Brute_Defense.Fiery_Aura|farm_active" ^
  --recert --workers 1 --shard-prefix champions_shard_v34 >> farm_active_v34.log 2>&1
echo farm_active recert exited with code %ERRORLEVEL% >> farm_active_v34.log
