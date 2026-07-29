@echo off
rem Scheduled (no-prompt) variant of pause-wave.bat — output APPENDS to
rem wave_pause_log.txt with a timestamp header so every firing stays readable
rem (2026-07-29: the 6:10 pause DID fire but its log got overwritten by a
rem later manual run and read as "schedule failed" — append, never clobber).
echo ===== scheduled pause fired %DATE% %TIME% ===== >> "%~dp0wave_pause_log.txt"
"C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe" "%~dp0tools\wave_pause.py" >> "%~dp0wave_pause_log.txt" 2>&1
