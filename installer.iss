; Inno Setup script for Wavrik · Media Downloader PRO.
; Build with: iscc /DMyAppVersion=2.3.0 installer.iss  (the release workflow passes the tag version)
#define MyAppName "Media Downloader PRO"
#ifndef MyAppVersion
  #define MyAppVersion "2.3.0"
#endif
#define MyAppPublisher "Wavrik contributors"
#define MyAppURL "https://github.com/intity01/Wavrik"
#define MyAppExeName "MediaDownloaderPRO.exe"

[Setup]
AppId={{E68A8D2A-0A7E-4F3D-9457-4E6ACD84BF22}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\MediaDownloaderPRO
DisableDirPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes
VersionInfoVersion={#MyAppVersion}
LicenseFile=LICENSE
InfoAfterFile=THIRD_PARTY_NOTICES.md
OutputDir=dist
OutputBaseFilename=MediaDownloaderPRO-v{#MyAppVersion}-Setup
SetupIconFile=Downloader\src\core\app.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} v{#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\MediaDownloaderPRO\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "Downloader\src\core\app.ico"; DestDir: "{app}\src\core"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\src\core\app.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\src\core\app.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
