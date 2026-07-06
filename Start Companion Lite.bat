@echo off
rem Hero Companion LITE - background capture daemon (tray icon, cyan dot).
rem Safe to run alongside the full app: whichever is active captures, never both.
cd /d "%~dp0"
start "" /min py run_lite.py
