@echo off
rem Hero Companion is a portable app (no installer). Double-click this to create
rem shortcuts to it on your Desktop and in your Start Menu. To get it on your
rem taskbar: launch the app, right-click its taskbar icon, "Pin to taskbar"
rem (Windows only allows you, not programs, to pin things there).
set "EXE=%~dp0HeroCompanion.exe"
if not exist "%EXE%" (
  echo Could not find HeroCompanion.exe next to this script. Run this from the app's folder.
  pause
  exit /b 1
)
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; foreach ($dir in @([Environment]::GetFolderPath('Desktop'), (Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs'))) { $s = $ws.CreateShortcut((Join-Path $dir 'Hero Companion.lnk')); $s.TargetPath = '%EXE%'; $s.WorkingDirectory = '%~dp0'; $s.IconLocation = '%EXE%'; $s.Description = 'Hero Companion - City of Heroes build optimizer'; $s.Save() }"
echo.
echo Done! "Hero Companion" is now on your Desktop and in your Start Menu.
echo (Tip: launch it, then right-click its taskbar icon to pin it there too.)
pause
