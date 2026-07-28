@echo off
rem Scheduled (no-prompt) variant of resume-wave.bat — output goes to
rem wave_resume_log.txt so the result is readable after the fact. The
rem resume itself launches converge_parallel DETACHED, so this bat exits
rem seconds after firing while the workers keep running.
"C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe" "%~dp0tools\wave_resume.py" > "%~dp0wave_resume_log.txt" 2>&1
