#define MyAppName "Monitor Dim Overlay"
#define MyAppVersion "2.1.2"
#define MyAppExeName "MonitorDimOverlay.exe"

[Setup]
AppId={{B56D4B46-8E3D-4FAE-A794-1A29770DD231}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\MonitorDimOverlay
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=MonitorDimOverlay-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"
Name: "autostart"; Description: "Iniciar con Windows"; GroupDescription: "Inicio automático:"

[Files]
Source: "..\dist\monitor_dim_overlay.exe"; DestDir: "{app}"; DestName: "{#MyAppExeName}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "MonitorDimOverlay"; ValueData: "{app}\{#MyAppExeName}"; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar {#MyAppName}"; Flags: nowait postinstall skipifsilent
