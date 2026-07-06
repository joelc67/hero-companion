@echo off
rem Gold-standard champion refresh - runs ENTIRELY on this machine (no AI, no network).
rem Expect several hours; each champion saves as it finishes, so interrupting is safe.
cd /d "%~dp0"
py tools\refresh_champions.py > champions_refresh_log.txt 2>&1
echo.
echo Done. Summary is at the end of champions_refresh_log.txt
pause
