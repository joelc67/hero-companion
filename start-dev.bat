@echo off
echo Starting Hero Companion DEV copy (port 5080)...
cd /d %~dp0

rem The installed tray app owns port 5000 - the dev copy always lives on 5080
rem so both can run at the same time without shadowing each other.
set "PORT=5080"

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
echo Launching DEV server on http://localhost:5080 ... keep this window open;
echo close it to stop the dev copy. The installed app keeps port 5000.
start "" http://localhost:5080
"%PYTHON%" server\server.py
echo.
echo Server stopped. Press any key to close this window.
pause >nul
