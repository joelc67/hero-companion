@echo off
rem Scheduled (no-prompt) variant of pause-wave.bat — output goes to
rem wave_pause_log.txt so the result is readable after the fact.
"C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe" "%~dp0tools\wave_pause.py" > "%~dp0wave_pause_log.txt" 2>&1
