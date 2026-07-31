@echo off
rem ============================================================================
rem CONVERGED MOVERS A/B (2026-07-30, Joel's "Run the converged movers A/B").
rem The six contexts the solve-level plateau A/B moved most (+61.9%% Warshade
rem down to -20.3%% Blaster), re-converged under the CURRENT solver (eps
rem tie-break default + finale physics arbitration, commit 249e7f62) to decide
rem whether the tie-break work justifies an item-6 re-cert — Joel's ruling:
rem "never assume we need a re-cert. Always check."
rem
rem MEASUREMENT ONLY: --recert (certified movers, no certified-skip) but NO
rem --merge — shards get verdict tables (recert_verdicts/evaluate_first) and
rem then rename to .ab_2026-07-30; NOTHING touches champions.json without
rem Joel's word. Node-capped per the certification-sweep rule (winners
rem re-solve uncapped + physics-arbitrate in the finale).
rem FLEET NOTE (justified out loud per the 2026-07-29 rule): 6 contexts <= 6
rem laptop workers, so every context gets a dedicated worker on the faster
rem machine; the gaming box (~2x slower per context) cannot shorten any
rem context's wall time and would only add order latency. Makespan floor =
rem Battle Axe on the laptop. The box idles BECAUSE it cannot help here.
rem ============================================================================
cd /d %~dp0
set "PYTHON=python"
where python >nul 2>nul || set "PYTHON=C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe"
set "HC_SOLVER_NODE_CAP=50000"
echo ===== AB movers wave launch %DATE% %TIME% ===== >> wave_abmov.log
"%PYTHON%" tools\converge_parallel.py --recert --workers 6 --shard-prefix champions_shard_abmov --keys "Class_Warshade|Warshade_Offensive.Umbral_Blast|Warshade_Defensive.Umbral_Aura|itrial,Class_Blaster|Blaster_Ranged.Fire_Blast|Blaster_Support.Energy_Manipulation|itrial,Class_Scrapper|Scrapper_Melee.Broad_Sword|Scrapper_Defense.Super_Reflexes|itrial,Class_Brute|Brute_Melee.Battle_Axe|Brute_Defense.Fiery_Aura|itrial,Class_Stalker|Stalker_Melee.Radiation_Melee|Stalker_Defense.Dark_Armor|itrial,Class_Arachnos_Widow|Widow_Training.Night_Widow_Training|Teamwork.Widow_Teamwork|itrial" >> wave_abmov.log 2>&1
echo ===== AB movers wave exited %ERRORLEVEL% at %DATE% %TIME% ===== >> wave_abmov.log
