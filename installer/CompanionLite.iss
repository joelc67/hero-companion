; Companion Lite — Inno Setup installer (Windows Citizenship, 2026-07-17).
; Build:  ISCC.exe installer\CompanionLite.iss   (after PyInstaller produces dist\CompanionLite)
; Per-user install (no admin), Start Menu entry, clean uninstall. The capture
; store lives in %APPDATA%\HeroCompanion\gamelog and is NEVER touched by uninstall.
; Auto-start is OPT-IN, asked by the app at first run (choice doctrine) — the
; installer sets nothing; the uninstaller removes the Run value if the app set it.

; Bump per Lite release (matches run_lite.py LITE_VERSION — two-place bump, like
; the smoke pins).
#define AppName "Companion Lite"
#define AppVersion "0.1.18"
#define AppPublisher "Pulsekin (joelc67)"
#define AppURL "https://github.com/joelc67/hero-companion"
#define RunValue "CompanionLite"

[Setup]
AppId={{2F9E6B10-3C4D-4A8E-9F1B-7C2A5D8E4B60}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={userpf}\CompanionLite
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=CompanionLite-Setup-{#AppVersion}
SetupIconFile=..\assets\HeroCompanion.ico
UninstallDisplayIcon={app}\CompanionLite.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE
; Lite is a windowless tray app — nothing to close politely, so end it for the user.
CloseApplications=force
RestartApplications=no
DirExistsWarning=no

[Code]
// A tray app is invisible; end it before installing over it or uninstalling.
// Nothing is lost — the capture store is in %APPDATA% and writes on change.
procedure TaskKillApp();
var
  R: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM CompanionLite.exe', '',
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

[Files]
Source: "..\dist\CompanionLite\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\{#AppName}"; Filename: "{app}\CompanionLite.exe"

[Run]
Filename: "{app}\CompanionLite.exe"; Description: "Launch {#AppName} now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; The app writes an HKCU Run value only if the user opts into auto-start at first
; run. Remove it on uninstall regardless (choice doctrine: a remembered "yes"
; leaves nothing behind). Harmless if the value was never created.
Filename: "{sys}\reg.exe"; Parameters: "delete ""HKCU\Software\Microsoft\Windows\CurrentVersion\Run"" /v {#RunValue} /f"; Flags: runhidden; RunOnceId: "DelLiteAutostart"

[UninstallDelete]
; the app folder only — the capture store in %APPDATA%\HeroCompanion is the player's
Type: filesandordirs; Name: "{app}"
