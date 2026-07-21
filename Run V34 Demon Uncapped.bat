@echo off
rem ============================================================================
rem v34 #13 — the ONE uncapped Demon/Rad MM re-convergence (Joel's Option B).
rem
rem WHY: the batched re-convergence ran under HC_SOLVER_NODE_CAP=50000 and its
rem Demon/Rad MM result LOST to the incumbent canonically (-120.6) — the flagship
rem MM context of the whole #13 batch, kept at its tier-1-pets-only incumbent. This
rem is its real, UNCAPPED convergence under v34: either it produces an honestly
rem better MM champion (re-verdict tomorrow under the earn-supersession gate), or
rem it fails and the incumbent ships with the one-objective work named as why.
rem
rem NO node cap set here (uncapped, full search). Detached + overnight.
rem Re-verdict in the morning: canonical-vs-canonical vs the incumbent (1309.0),
rem SUPERSEDE only if it beats by >0.5. Retire this shard at merge either way.
rem ============================================================================
cd /d %~dp0
set "PYTHON=python"
where python >nul 2>nul || set "PYTHON=C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe"
echo Started: %DATE% %TIME% > v34_demon_uncapped_log.txt
"%PYTHON%" tools\converge_parallel.py --recert --workers 1 --shard-prefix champions_shard_v34demon --keys "Class_Mastermind|Mastermind_Summon.Demon_Summoning|Mastermind_Buff.Radiation_Emission|itrial" >> v34_demon_uncapped_log.txt 2>&1
echo Finished: %DATE% %TIME% >> v34_demon_uncapped_log.txt
