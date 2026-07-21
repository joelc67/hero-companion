@echo off
rem RESUME the v35 recert wave — re-runs ONLY the contexts not yet saved in
rem the shards. Safe to run any time; runs detached, window can close.
"C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe" "%~dp0tools\wave_resume.py"
pause
