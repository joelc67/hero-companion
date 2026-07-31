@echo off
rem ============================================================================
rem ITEM-6 REMAINDER WAVE (2026-07-30 evening, Joel's "Run the remaining 18").
rem The 18 certified contexts not covered by the movers tranche, re-converged
rem under the current solver (eps tie-break + arbitrated finales, fc98aa05+).
rem FLEET SPLIT per the standing rule: split_wave.py LPT-partitions 12 local /
rem 6 remote (gaming box via OneDrive order, commit-pinned) and launches both.
rem Same contract as every wave: --recert semantics, NO merge — verdict table
rem to Joel before anything touches champions.json. Hard pause armed 5:30 AM
rem (laptop clock, Joel's word); box slice finishes on its own schedule and
rem returns results via the mailbox.
rem ============================================================================
cd /d %~dp0
set "PYTHON=python"
where python >nul 2>nul || set "PYTHON=C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe"
set "HC_SOLVER_NODE_CAP=50000"
echo ===== I6R wave launch %DATE% %TIME% ===== >> wave_i6r.log
"%PYTHON%" tools\remote_worker\split_wave.py --keys-file i6r_keys.txt >> wave_i6r.log 2>&1
echo ===== I6R splitter exited %ERRORLEVEL% at %DATE% %TIME% ===== >> wave_i6r.log
