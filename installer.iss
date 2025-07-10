#define MyAppName "Spare Parts Management System"
#define MyAppVersion "1.0"
#define MyAppPublisher "Aman Kflom & Nesredin Abdelrahim"
#define MyAppExeName "SparePartsMS.exe"

[Setup]
AppName=Spare Parts Management System
AppVersion=1.0
DefaultDirName={pf}\SparePartsMS
DefaultGroupName=Spare Parts MS
OutputDir=.
OutputBaseFilename=SparePartsMS_Setup
SetupIconFile=static\favicon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\SparePartsMS.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs
Source: "instance\*"; DestDir: "{app}\instance"; Flags: ignoreversion recursesubdirs
Source: "sparepart\*"; DestDir: "{app}\sparepart"; Flags: ignoreversion recursesubdirs
Source: "instance\spms.db"; DestDir: "{app}\instance"; Flags: ignoreversion
; Add other files as needed

[Icons]
Name: "{autodesktop}\Spare Parts MS"; Filename: "{app}\SparePartsMS.exe"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent