; ============================================================================
;  VendaFácil PDV — Script do instalador (Inno Setup)
; ============================================================================
;  Gera um instalador amigável (VendaFacilPDV-Setup.exe) a partir do executável
;  já buildado em dist_exe\VendaFacilPDV.exe.
;
;  Pré-requisitos:
;    1. Rodar build_exe.bat antes (gera dist_exe\VendaFacilPDV.exe).
;    2. Inno Setup 6 instalado (https://jrsoftware.org/isdl.php).
;
;  Compilar:  abra este arquivo no Inno Setup e clique em "Compile",
;             ou rode  installer\build_installer.bat
;
;  O instalador coloca o app em Program Files, cria atalhos no Menu Iniciar e
;  na Área de Trabalho, e registra o desinstalador. O banco de dados NÃO fica
;  em Program Files — vai para %LOCALAPPDATA%\VendaFacilPDV\dados (ver paths.py).
; ============================================================================

#define AppName "VendaFácil PDV"
#define AppVersion "1.0.0"
#define AppPublisher "SUA EMPRESA LTDA"          ; <-- troque pelo nome/CNPJ da sua empresa
#define AppURL "https://seudominio.com.br"        ; <-- troque pelo seu site
#define AppExe "VendaFacilPDV.exe"

[Setup]
AppId={{B7E3F2A1-9C4D-4E8B-A1F6-VENDAFACILPDV01}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
DefaultDirName={autopf}\VendaFacilPDV
DefaultGroupName=VendaFácil PDV
DisableProgramGroupPage=yes
OutputDir=..\dist_installer
OutputBaseFilename=VendaFacilPDV-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile={#SourcePath}\vendafacil.ico
UninstallDisplayIcon={app}\{#AppExe}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na Área de Trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "..\dist_exe\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\VendaFácil PDV"; Filename: "{app}\{#AppExe}"
Name: "{group}\Desinstalar VendaFácil PDV"; Filename: "{uninstallexe}"
Name: "{autodesktop}\VendaFácil PDV"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir o VendaFácil PDV agora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove os dados do usuário ao desinstalar? Por padrão NÃO apagamos o banco,
; para o lojista não perder as vendas por engano. Para apagar, descomente:
; Type: filesandordirs; Name: "{localappdata}\VendaFacilPDV"
