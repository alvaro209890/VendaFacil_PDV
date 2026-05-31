@echo off
REM Gera o VendaFacilPDV.exe no Windows (executavel unico).
REM Pre-requisitos: Node 20+ e Python 3.10+ instalados e no PATH.
setlocal
cd /d "%~dp0"

echo ==^> Build do frontend (npm)
call npm install || goto :erro
call npm run build || goto :erro

echo ==^> Preparando ambiente Python
cd backend
set "PYTHON_CMD=python"
py -3.11 --version >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=py -3.11"
if not exist .venv (
    %PYTHON_CMD% -m venv .venv || goto :erro
)
call .venv\Scripts\python -m pip install --upgrade pip || goto :erro
call .venv\Scripts\pip install -q -r requirements-build.txt || goto :erro

echo ==^> Empacotando com PyInstaller
call .venv\Scripts\pyinstaller vendafacil.spec --noconfirm --distpath ..\dist_exe --workpath ..\build || goto :erro

echo.
echo OK! Executavel gerado em: dist_exe\VendaFacilPDV.exe
echo Distribua ESSE arquivo. Ao abrir, ele sobe o sistema e abre o navegador.
goto :fim

:erro
echo.
echo ERRO no build. Veja as mensagens acima.
exit /b 1

:fim
endlocal
