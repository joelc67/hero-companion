; Hero Companion — Inno Setup installer script.
; Build:  ISCC.exe installer\HeroCompanion.iss   (after PyInstaller has produced dist\HeroCompanion)
; Per-user install (no admin prompt), Add/Remove Programs entry with uninstaller,
; optional desktop icon, Start Menu entry, in-place upgrades. Saves are never touched:
; they live in %APPDATA%\HeroCompanion, which the uninstaller deliberately leaves alone.

#define AppName "Hero Companion"
#define AppVersion FileRead(FileOpen("..\VERSION"))
#define AppPublisher "Pulsekin (joelc67)"
#define AppURL "https://github.com/joelc67/hero-companion"

[Setup]
AppId={{7B1C5A44-9A2E-4C63-B0D0-9E1A61B7C0DE}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={userpf}\HeroCompanion
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=HeroCompanion-Setup-{#AppVersion}
SetupIconFile=..\assets\HeroCompanion.ico
UninstallDisplayIcon={app}\HeroCompanion.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE
; The app runs WINDOWLESS in the tray, so users upgrading won't know it's running —
; close it for them (force: a tray app has no window to ask politely).
CloseApplications=force
RestartApplications=no
; Reinstalling over an existing folder is normal (upgrades, repairs) — don't interrogate.
DirExistsWarning=no

[Code]
// A tray app is invisible; users can't be expected to quit it first. End it outright
// before installing over it or uninstalling it (nothing is lost — saves are server-side
// in %APPDATA% and write on change).
procedure TaskKillApp();
var
  R: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM HeroCompanion.exe', '',
       SW_HIDE, ewWaitUntilTerminated, R);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  TaskKillApp();
  Result := '';
end;

function InitializeUninstall(): Boolean;
begin
  TaskKillApp();
  Result := True;
end;

function WantRelaunch(): Boolean;
begin
  Result := ExpandConstant('{param:RELAUNCH|0}') = '1';
end;

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "..\dist\HeroCompanion\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "Add Shortcuts.bat"

[Icons]
Name: "{userprograms}\{#AppName}"; Filename: "{app}\HeroCompanion.exe"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\HeroCompanion.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\HeroCompanion.exe"; Description: "Launch {#AppName} now"; Flags: nowait postinstall skipifsilent
; One-click self-update path: the app runs this installer silently with /RELAUNCH=1
; and expects to be brought back to life afterward.
Filename: "{app}\HeroCompanion.exe"; Flags: nowait; Check: WantRelaunch

[UninstallDelete]
; the app folder only — saves in %APPDATA%\HeroCompanion are the player's, not ours to delete
Type: filesandordirs; Name: "{app}"
