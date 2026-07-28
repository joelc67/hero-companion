@echo off
rem One watcher tick: claim + run one order if present, else exit in seconds.
rem Fired by the HC_RemoteWorker scheduled task every 5 minutes (hidden).
cd /d "%~dp0..\.."
set "PYTHON=python"
where python >nul 2>nul || set "PYTHON=py"
"%PYTHON%" tools\remote_worker\worker_watch.py --once >> tools\remote_worker\worker_tick.log 2>&1
