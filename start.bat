@echo off
echo Starting CoH Build Planner...
cd /d %~dp0

rem --- Locate the Claude Code CLI (handles the MSIX/Store packaged app) ---
set "CLAUDE_BIN="
for /f "delims=" %%i in ('dir /b /s "%LOCALAPPDATA%\Packages\Claude*\LocalCache\Roaming\Claude\claude-code\claude.exe" 2^>nul') do set "CLAUDE_BIN=%%i"
if not defined CLAUDE_BIN for /f "delims=" %%i in ('dir /b /s "%APPDATA%\Claude\claude-code\claude.exe" 2^>nul') do set "CLAUDE_BIN=%%i"

rem --- Load the persisted Claude auth token straight from the registry, in ---
rem --- case Explorer's cached environment is stale and didn't inherit it ---
for /f "tokens=2,*" %%a in ('reg query "HKCU\Environment" /v CLAUDE_CODE_OAUTH_TOKEN 2^>nul ^| findstr /i "CLAUDE_CODE_OAUTH_TOKEN"') do set "CLAUDE_CODE_OAUTH_TOKEN=%%b"
if defined CLAUDE_CODE_OAUTH_TOKEN echo   AI token: loaded from registry.
if not defined CLAUDE_CODE_OAUTH_TOKEN echo   AI token: NOT found - run claude setup-token, then setx.

rem --- Prefer python on PATH; fall back to the known install location ---
set "PYTHON=python"
where python >nul 2>nul || set "PYTHON=C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe"

echo.
echo NOTE: If the app is already running in another window, close that window
echo first. (If you see "Address already in use" below, that is the reason.)
echo.
echo Launching server... keep this window open; close it to stop the app.
start "" http://localhost:5000
"%PYTHON%" server\server.py
echo.
echo Server stopped. Press any key to close this window.
pause >nul
