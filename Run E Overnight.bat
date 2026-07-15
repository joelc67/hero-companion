@echo off
rem E-run overnight driver (2026-07-15 work order) - start before bed,
rem answer ONE question (the pricing ruling), leave it running.
cd /d %~dp0
set "PYTHON=python"
where python >nul 2>nul || set "PYTHON=C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe"
"%PYTHON%" tools\run_e_overnight.py
echo.
echo Driver exited. Press any key to close.
pause >nul
