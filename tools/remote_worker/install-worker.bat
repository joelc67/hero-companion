@echo off
rem ============================================================================
rem REMOTE WORKER one-time install (run ON the gaming box, as your normal user).
rem Turns this machine into a champion-crunch worker the dev laptop conducts
rem via OneDrive. OUTBOUND-ONLY: this box polls OneDrive and pulls from GitHub;
rem nothing listens, no ports open, no inbound access needed - ever.
rem ============================================================================
setlocal
set "WORKDIR=%USERPROFILE%\code\hero-companion-worker"
rem Pin to Python 3.13 (the conductor laptop's version) so both machines run
rem the identical runtime; falls back to PATH python only if 3.13 is absent.
set "PYTHON=py -3.13"
py -3.13 --version >nul 2>nul || set "PYTHON=py -3.11"
py -3.13 --version >nul 2>nul || py -3.11 --version >nul 2>nul || set "PYTHON=python"

echo [1/5] Checking prerequisites...
where git >nul 2>nul || (echo   git is missing - install Git for Windows first & exit /b 1)
%PYTHON% --version >nul 2>nul || (echo   Python is missing - install Python 3.13 first & exit /b 1)
%PYTHON% --version 2>nul | findstr /c:" 3.13." >nul || echo   NOTE: not running 3.13 - install Python 3.13 for an identical runtime to the laptop
if "%OneDrive%"=="" (echo   OneDrive env var missing - sign into OneDrive first & exit /b 1)

echo [2/5] Cloning the repo to %WORKDIR% ...
if not exist "%WORKDIR%\.git" (
  git clone https://github.com/joelc67/hero-companion.git "%WORKDIR%" || exit /b 1
) else (
  echo   already cloned - ok
)

echo [3/5] Installing Python dependencies...
%PYTHON% -m pip install -r "%WORKDIR%\requirements.txt" || exit /b 1

echo [4/5] Creating the OneDrive mailbox folders...
mkdir "%OneDrive%\HeroCompanionCompute\orders" 2>nul
mkdir "%OneDrive%\HeroCompanionCompute\results" 2>nul
mkdir "%OneDrive%\HeroCompanionCompute\state" 2>nul

echo [5/5] Registering the watcher (every 5 minutes, hidden)...
schtasks /create /f /tn HC_RemoteWorker /sc minute /mo 5 ^
  /tr "wscript.exe \"%WORKDIR%\tools\remote_worker\launch_hidden_worker.vbs\" \"%WORKDIR%\tools\remote_worker\worker-tick.bat\"" || exit /b 1

echo.
echo Done. This box now claims any order the laptop drops into
echo   %OneDrive%\HeroCompanionCompute\orders\
echo within ~5 minutes of being awake. Progress heartbeats and finished
echo shards flow back the same way. To retire the worker later:
echo   schtasks /delete /f /tn HC_RemoteWorker
pause
