@echo off
REM ============================================================================
REM  Compila o instalador VendaFacilPDV-Setup.exe (Inno Setup).
REM  Pre-requisitos:
REM    1. Rodar build_exe.bat antes (gera ..\dist_exe\VendaFacilPDV.exe).
REM    2. Inno Setup 6 instalado (https://jrsoftware.org/isdl.php).
REM ============================================================================
setlocal
cd /d "%~dp0"

if not exist "..\dist_exe\VendaFacilPDV.exe" (
    echo ERRO: ..\dist_exe\VendaFacilPDV.exe nao encontrado.
    echo Rode build_exe.bat na raiz do projeto primeiro.
    exit /b 1
)

REM Caminho padrao do compilador do Inno Setup 6. Ajuste se instalou em outro lugar.
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo ERRO: ISCC.exe (Inno Setup) nao encontrado.
    echo Instale o Inno Setup 6: https://jrsoftware.org/isdl.php
    exit /b 1
)

"%ISCC%" vendafacil.iss || exit /b 1

echo.
echo OK! Instalador gerado em: dist_installer\VendaFacilPDV-Setup-*.exe
endlocal
