@echo off
REM ============================================================================
REM  Assinatura de código (code signing) do VendaFácil PDV.
REM
REM  Sem assinatura, o Windows SmartScreen mostra "Editor desconhecido" e
REM  assusta o cliente. Para assinar você precisa de:
REM    - Um certificado de Code Signing (OV ou EV) de uma CA confiavel
REM      (ex.: Certisign, Valid, DigiCert, Sectigo). Custa ~US$100-400/ano.
REM    - O signtool.exe (vem no Windows SDK).
REM
REM  Uso:
REM    sign.bat caminho\para\arquivo.exe
REM
REM  Edite as variaveis abaixo conforme seu certificado.
REM  - Certificado em arquivo .pfx:  use CERT_PFX + CERT_PASS
REM  - Certificado no repositorio de certificados do Windows / token:
REM      troque por  /n "Nome no certificado"  ou  /sha1 <thumbprint>
REM ============================================================================
setlocal

if "%~1"=="" (
    echo Uso: sign.bat caminho\para\arquivo.exe
    exit /b 1
)

set "ALVO=%~1"
set "CERT_PFX=C:\caminho\para\seu-certificado.pfx"
set "CERT_PASS=SUA_SENHA_DO_PFX"
set "TIMESTAMP=http://timestamp.digicert.com"

REM Localiza o signtool (ajuste a versao do SDK se necessario)
set "SIGNTOOL="
for /f "delims=" %%i in ('where signtool 2^>nul') do set "SIGNTOOL=%%i"
if "%SIGNTOOL%"=="" (
    echo ERRO: signtool.exe nao encontrado. Instale o Windows SDK.
    exit /b 1
)

"%SIGNTOOL%" sign /f "%CERT_PFX%" /p "%CERT_PASS%" /fd SHA256 /tr "%TIMESTAMP%" /td SHA256 "%ALVO%" || exit /b 1
"%SIGNTOOL%" verify /pa "%ALVO%"

echo.
echo OK! Assinado: %ALVO%
endlocal
