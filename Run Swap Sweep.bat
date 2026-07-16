@echo off
rem ============================================================================
rem SWAP-SWEEP - DETACHED launcher (2026-07-16 overnight work order).
rem Sizes the search-vs-canonical optimality damage across the certified
rem roster: full one-move neighborhood per champion under the CANONICAL
rem evaluator. READ-ONLY vs champions.json - certifies nothing.
rem Resumes by design: contexts with an existing output file are skipped.
rem Launched via a Windows scheduled task (NOT Start-Process): the detached
rem Start-Process pattern failed to survive twice on 2026-07-16.
rem ============================================================================
cd /d %~dp0
set "PYTHON=python"
where python >nul 2>nul || set "PYTHON=C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe"

echo ===== swap-sweep launch %DATE% %TIME% ===== >> swap_sweep.log
"%PYTHON%" tools\swap_sweep.py --workers 2 --threads 3 >> swap_sweep.log 2>&1
echo Swap-sweep exited with code %ERRORLEVEL% >> swap_sweep.log
