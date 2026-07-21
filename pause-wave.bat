@echo off
rem PAUSE the v35 recert wave safely (progress is saved per-context in the
rem champions_shard_par*_p*.json shards). Double-click before shutting down.
"C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe" "%~dp0tools\wave_pause.py"
pause
