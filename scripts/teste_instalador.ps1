param(
    [string]$SetupAnterior = (Join-Path $PSScriptRoot '..\dist_installer\VendaFacilPDV-Setup-1.0.12.exe'),
    [string]$SetupAtual = (Join-Path $PSScriptRoot '..\dist_installer\VendaFacilPDV-Setup-1.0.14.exe')
)

$ErrorActionPreference = 'Stop'
$identidade = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identidade)
if (!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Output 'B8: a sessao nao esta elevada. Nenhum instalador foi executado.'
    exit 2
}

$antigo = (Resolve-Path -LiteralPath $SetupAnterior).Path
$novo = (Resolve-Path -LiteralPath $SetupAtual).Path
$python = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\backend\.venv\Scripts\python.exe')).Path
$chaves = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
if (Get-ItemProperty -Path $chaves -ErrorAction SilentlyContinue | Where-Object DisplayName -Like 'VendaF* PDV') {
    throw 'Existe uma instalacao do PDV. Execute o teste em uma maquina Windows descartavel.'
}
if (Get-Process VendaFacilPDV -ErrorAction SilentlyContinue) {
    throw 'Existe um PDV aberto. Feche-o antes de testar o Setup anterior.'
}
if (Get-NetTCPConnection -LocalPort 3021 -State Listen -ErrorAction SilentlyContinue) {
    throw 'A porta de teste 3021 esta ocupada.'
}

$pastaTeste = Join-Path ([IO.Path]::GetTempPath()) ("vf-installer-" + [Guid]::NewGuid().ToString('N'))
$programa = Join-Path $pastaTeste 'Programa'
$perfil = Join-Path $pastaTeste 'Perfil'
$exe = Join-Path $programa 'VendaFacilPDV.exe'
$banco = Join-Path $perfil 'VendaFacilPDV\dados\vendafacil.db'
$base = 'http://127.0.0.1:3021'
New-Item -ItemType Directory -Path $pastaTeste | Out-Null

function Invocar-Setup([string]$Arquivo, [string]$NomeLog) {
    $log = Join-Path $pastaTeste $NomeLog
    $opcoes = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR=`"$programa`" /TASKS=desktopicon /LOG=`"$log`""
    $processo = Start-Process -FilePath $Arquivo -ArgumentList $opcoes -Wait -PassThru -WindowStyle Hidden
    if ($processo.ExitCode -ne 0) { throw "Setup falhou com codigo $($processo.ExitCode). Log em $log" }
}

function Obter-AtalhosDoTeste {
    $shell = New-Object -ComObject WScript.Shell
    foreach ($tipo in @('CommonDesktopDirectory','DesktopDirectory','CommonPrograms','Programs')) {
        $pasta = [Environment]::GetFolderPath($tipo)
        if (!$pasta) { continue }
        Get-ChildItem -LiteralPath $pasta -Filter 'VendaF*PDV.lnk' -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $shell.CreateShortcut($_.FullName).TargetPath -eq $exe }
    }
}

function Testar-PrimeiroAcesso([bool]$Criar) {
    $processo = Start-Process -FilePath $exe -PassThru -WindowStyle Hidden
    try {
        $limite = (Get-Date).AddSeconds(40)
        $saude = $null
        while ((Get-Date) -lt $limite -and !$saude -and !$processo.HasExited) {
            try { $saude = Invoke-RestMethod "$base/health" -TimeoutSec 1 } catch { Start-Sleep -Milliseconds 250 }
        }
        if ($saude.app -ne 'vendafacil-pdv') { throw 'Instalacao nao respondeu como VendaFacil.' }
        $identificacao = @{usuario='teste-instalador'; senha='Fixture-instalador@26'}
        if ($Criar) {
            $cadastro = $identificacao.Clone()
            $cadastro.nome = 'Operador teste'
            $null = Invoke-RestMethod "$base/api/auth/registro" -Method Post -ContentType 'application/json' -Body ($cadastro | ConvertTo-Json)
        }
        $sessao = Invoke-RestMethod "$base/api/auth/login" -Method Post -ContentType 'application/json' -Body ($identificacao | ConvertTo-Json)
        $cabecalho = @{Authorization="Bearer $($sessao.token)"}
        if ($Criar) {
            $produto = @{nome='Amostra'; preco_custo=1; preco_venda=2; estoque=3}
            $null = Invoke-RestMethod "$base/api/produtos" -Method Post -Headers $cabecalho -ContentType 'application/json' -Body ($produto | ConvertTo-Json)
        } elseif ($saude.version -ne '1.0.14') {
            throw 'A atualizacao nao reportou 1.0.14.'
        }
        if (!(Test-Path -LiteralPath $banco)) { throw 'Banco ausente no LOCALAPPDATA isolado.' }
    } finally {
        if (!$processo.HasExited) { & taskkill.exe /PID $processo.Id /T /F | Out-Null }
        $processo.WaitForExit()
    }
}

function Obter-Contagens {
    $script = @'
import sqlite3, sys
from pathlib import Path
with sqlite3.connect(Path(sys.argv[1]).resolve().as_uri() + '?mode=ro', uri=True) as db:
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    print(','.join(str(db.execute('SELECT COUNT(*) FROM ' + tabela).fetchone()[0])
                   for tabela in ('users', 'produtos', 'clientes', 'vendas', 'notas_fiscais')))
'@
    $numeros = & $python -X utf8 -I -c $script $banco
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao conferir o SQLite da instalacao.' }
    return $numeros
}

$envTeste = @{
    LOCALAPPDATA=$perfil; VENDAFACIL_DATA_DIR=$null; VENDAFACIL_PORT='3021'
    VENDAFACIL_HOST='127.0.0.1'; VENDAFACIL_PAINEL_URL=''; VENDAFACIL_NO_BROWSER='1'
    VENDAFACIL_JWT_SECRET=$null; PYTHONPATH=$null
}
$ambienteOriginal = @{}
foreach ($chave in $envTeste.Keys) {
    $ambienteOriginal[$chave] = [Environment]::GetEnvironmentVariable($chave, 'Process')
    [Environment]::SetEnvironmentVariable($chave, $envTeste[$chave], 'Process')
}
try {
    Invocar-Setup $antigo 'instalacao-anterior.log'
    if (!(Test-Path -LiteralPath $exe) -or @(Obter-AtalhosDoTeste).Count -lt 2) {
        throw 'Executavel ou atalhos ausentes apos instalacao.'
    }
    Testar-PrimeiroAcesso $true
    $antes = Obter-Contagens
    Write-Output "E04: instalacao e atalhos conferidos. SQLite antes: $antes"

    Invocar-Setup $novo 'atualizacao.log'
    Testar-PrimeiroAcesso $false
    if ((Obter-Contagens) -ne $antes -or @(Obter-AtalhosDoTeste).Count -lt 2) {
        throw 'Atualizacao mudou as contagens ou perdeu atalhos.'
    }
    Write-Output 'E05: versao 1.0.14, atalhos e contagens preservados.'

    $desinstalador = Get-ChildItem -LiteralPath $programa -Filter 'unins*.exe' -File | Select-Object -First 1
    if (!$desinstalador) { throw 'Desinstalador ausente.' }
    $fim = Start-Process -FilePath $desinstalador.FullName -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' -Wait -PassThru -WindowStyle Hidden
    if ($fim.ExitCode -ne 0 -or (Test-Path -LiteralPath $exe) -or @(Obter-AtalhosDoTeste).Count -ne 0 -or (Obter-Contagens) -ne $antes) {
        throw 'Desinstalacao nao preservou os dados ou deixou arquivos do programa.'
    }
    Write-Output "E06: desinstalacao removeu programa/atalhos e preservou SQLite. Evidencias em $pastaTeste"
} finally {
    foreach ($chave in $ambienteOriginal.Keys) {
        [Environment]::SetEnvironmentVariable($chave, $ambienteOriginal[$chave], 'Process')
    }
}
