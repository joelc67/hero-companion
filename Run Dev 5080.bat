@echo off
rem Dev copy on 5080, DETACHED (same rule as the wave: the 2026-07-16 auth
rem failure killed the session-owned dev server too, so Joel's eyeball URL went
rem dead without warning). The installed tray app keeps port 5000.
cd /d %~dp0
set "PORT=5080"
set "PYTHON=python"
where python >nul 2>nul || set "PYTHON=C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe"
"%PYTHON%" server\server.py >> dev5080.log 2>&1
