; سكربت Inno Setup لإنشاء ملف تثبيت نظام إدارة الأعمال (ERP)
; يتطلب تثبيت برنامج Inno Setup مجاناً من: https://jrsoftware.org/isdl.php
; بعد فتح هذا الملف بواسطة Inno Setup Compiler، اضغط Build > Compile

#define MyAppName "نظام إدارة الأعمال"
#define MyAppVersion "1.0"
#define MyAppExeName "ERP_System.exe"

[Setup]
AppId={{8F2C1A3E-4B5D-4E6F-9A0B-1C2D3E4F5A6B}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\ERP_System
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist_installer
OutputBaseFilename=setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern

[Languages]
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"

[Tasks]
Name: "desktopicon"; Description: "إنشاء أيقونة على سطح المكتب"; GroupDescription: "أيقونات إضافية:"

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "تشغيل النظام الآن"; Flags: nowait postinstall skipifsilent
