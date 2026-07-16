@echo off
rem ============================================================================
rem v33 re-convergence wave — DETACHED launcher (the E-bat pattern).
rem
rem WHY THIS FILE EXISTS (2026-07-16 incident): the first v33 wave ran as a
rem session background task. An auth failure tore the session down and killed
rem both live workers mid-context (~13:23-13:24 UTC) — Battle_Axe at sweep 20
rem and farm_active at sweep 14, ~50 and ~55 minutes of convergence, gone.
rem deep_optimize does not checkpoint mid-context, so an interrupted context
rem restarts from scratch; only COMPLETED contexts are banked in their shard.
rem Expensive runs therefore launch DETACHED from the session, never as a
rem session-owned child process.
rem
rem Resumes by design: converge_parallel skips contexts already certified in a
rem shard, so the completed farm_afk (champions_shard_v33_p1.json) is untouched.
rem ============================================================================
cd /d %~dp0
set "PYTHON=python"
where python >nul 2>nul || set "PYTHON=C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe"

echo Relaunching the v33 wave (2 contexts: Battle_Axe/FA itrial, Rad/FA farm_active)...
"%PYTHON%" tools\converge_parallel.py ^
  --keys "Class_Brute|Brute_Melee.Battle_Axe|Brute_Defense.Fiery_Aura|itrial,Class_Brute|Brute_Melee.Radiation_Melee|Brute_Defense.Fiery_Aura|farm_active" ^
  --recert --workers 2 --shard-prefix champions_shard_v33 >> v33_wave.log 2>&1

echo Wave exited with code %ERRORLEVEL% >> v33_wave.log
