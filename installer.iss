; Inno Setup Script for Media Downloader PRO v2.2.0
#define MyAppName "Media Downloader PRO"
#define MyAppVersion "2.2.0"
#define MyAppPublisher "MediaDownloaderPRO"
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
LicenseFile=LICENSE
InfoAfterFile=THIRD_PARTY_NOTICES.md
OutputDir=dist
OutputBaseFilename=MediaDownloaderPRO-v2.2.0-Setup
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
