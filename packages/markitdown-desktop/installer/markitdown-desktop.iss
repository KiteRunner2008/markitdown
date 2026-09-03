#ifndef AppVersion
#define AppVersion "0.1.1"
#endif

#ifndef OutputDir
#define OutputDir "..\..\..\release"
#endif

#ifndef OutputBaseFilename
#define OutputBaseFilename "MarkItDownDesktop-0.1.1-setup"
#endif

#ifndef RepositoryUrl
#define RepositoryUrl ""
#endif

[Setup]
AppId={{6B1D4121-6F1C-4E33-9A65-6A836CE5C935}
AppName=MarkItDown Desktop
AppVersion={#AppVersion}
AppPublisher=MarkItDown Desktop contributors
#if RepositoryUrl != ""
AppPublisherURL={#RepositoryUrl}
AppSupportURL={#RepositoryUrl}/issues
AppUpdatesURL={#RepositoryUrl}
#endif
DefaultDirName={autopf}\MarkItDown Desktop
DefaultGroupName=MarkItDown Desktop
DisableProgramGroupPage=yes
LicenseFile=..\..\..\LICENSE
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBaseFilename}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\MarkItDownDesktop.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\..\dist\MarkItDownDesktop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MarkItDown Desktop"; Filename: "{app}\MarkItDownDesktop.exe"
Name: "{autodesktop}\MarkItDown Desktop"; Filename: "{app}\MarkItDownDesktop.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MarkItDownDesktop.exe"; Description: "{cm:LaunchProgram,MarkItDown Desktop}"; Flags: nowait postinstall skipifsilent
