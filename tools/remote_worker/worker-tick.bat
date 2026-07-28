@echo off
rem One watcher tick: claim + run one order if present, else exit in seconds.
rem Fired by the HC_RemoteWorker scheduled task every 5 minutes (hidden).
cd /d "%~dp0..\.."
rem Pin to Python 3.13 — the conductor laptop's version. Identical runtime on
rem both machines keeps canonical scores beyond question (and our pinned
rem Flask/Werkzeug are unproven on 3.14+).
set "PYTHON=py -3.13"
py -3.13 --version >nul 2>nul || set "PYTHON=py -3.11"
py -3.13 --version >nul 2>nul || py -3.11 --version >nul 2>nul || set "PYTHON=python"
%PYTHON% tools\remote_worker\worker_watch.py --once >> tools\remote_worker\worker_tick.log 2>&1
