# CLAUDE.md — instruções para o agente

Este repositório é o **VendaFácil PDV**. Se você é um agente que pegou este repo
para **gerar o executável Windows (.exe)**, siga este guia. Os comandos de build
já estão **pré-autorizados** em `.claude/settings.json` (não deve pedir permissão).

> "APK" às vezes é citado por engano: **o artefato é o `.exe` do Windows**
> (PyInstaller + instalador Inno Setup). Não há projeto Android neste repo.

## O que é o projeto

- **PDV** (`backend/` FastAPI + `src/` React/Vite): roda **offline-first**,
  empacotado como **um .exe**. O FastAPI serve o build do React embutido.
- **painel/**: backend SaaS separado (Render+Supabase) — **NÃO** faz parte do .exe;
  ignore ao gerar o executável.

## Build automático (GitHub Actions)

Já existe `.github/workflows/build-exe.yml`: a cada push no `master` (e em tags
`vX.Y.Z`) a GitHub gera o `.exe` + instalador num runner Windows. Baixe em
**Actions → Artifacts**, ou em **Releases** (nas tags). Conferido em 12/11/2026:
as execuções do workflow "Build Windows EXE" no `master` estão verdes
(`gh run list --workflow build-exe.yml`). A entrega atual é a **1.0.17**
(caixa e unidade com preços diferentes, ver `docs/CAIXA_E_UNIDADE.md`; vender sem
abrir caixa e sem aviso, ver `docs/CAIXA.md`). Build local validado em
14/11/2026: `dist_installer\VendaFacilPDV-Setup-1.0.17.exe` (40.002.839 bytes,
SHA-256 `E892829B0D836644D7CC3B68A134F141EFECC3ADB43ED1614117352A2B8FBC68`) e `dist_exe\VendaFacilPDV.exe` (39.716.710 bytes,
SHA-256 `853F0A2C3B1F8EF117279C3A3F418687F8A804865A877D813F5FCC1FAEF8E227`). O Setup do Actions tem outro hash (o build não é
reprodutível byte a byte). A 1.0.16 foi publicada e substituída no mesmo dia.
A 1.0.15 era `b3477e2` (run
[43549468463](https://github.com/alvaro209890/VendaFacil_PDV/actions/runs/43549468463)).
O entregável validado, porém, é o gerado localmente e conferido pelo roteiro
abaixo. Para gerar localmente, siga abaixo.

## Pré-requisitos (na máquina Windows)

- **Node.js 20+** (o Vite recusa Node 18) e **Python 3.10+** (com "Add to PATH").
- **Inno Setup 6** (para o instalador): https://jrsoftware.org/isdl.php

## Gerar o .exe (passo a passo)

Tudo a partir da **raiz do repositório**:

```bat
:: 1) (opcional) ligar o .exe ao painel — edite backend\painel_config.py:
::    PAINEL_URL = "https://vendafacil-painel.onrender.com"   (ou "" para modo local)

:: 2) Gerar o executável (faz npm install + npm run build + PyInstaller)
build_exe.bat

:: 3) Gerar o instalador amigável (precisa do Inno Setup instalado)
installer\build_installer.bat
```

Equivalente manual, se preferir rodar etapa por etapa:

```bat
npm install
npm run build
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements-build.txt
.venv\Scripts\pyinstaller vendafacil.spec --noconfirm --distpath ..\dist_exe --workpath ..\build
cd ..
```

## Saídas (artefatos)

- **`dist_exe\VendaFacilPDV.exe`** — executável único (o que roda o sistema).
- **`dist_installer\VendaFacilPDV-Setup-*.exe`** — instalador para entregar ao
  lojista (cria atalhos e desinstalador).

As duas pastas estão no `.gitignore` e **nenhum binário fica no git**: por
decisão do Álvaro (D2, 12/11/2026) os binários antigos (`dist_exe/VendaFacilPDV.exe`
e Setups 1.0.3/1.0.10/1.0.11) saíram do repositório (continuam só no histórico).
O instalador é entregue a partir do build local validado ou dos Artifacts/Releases
do Actions. Use sempre `git add <caminho>` explícito, nunca `git add -A`/`git add .`.

Registre caminho, tamanho e SHA-256 (`Get-FileHash <arquivo> -Algorithm SHA256`).

## Validar

1. Dois cliques em `dist_exe\VendaFacilPDV.exe` → o navegador abre em
   `http://127.0.0.1:3020/`.
2. Roteiro automático contra o `.exe` (dados descartáveis, porta 3021, SEFAZ
   sintética de homologação):
   ```bat
   backend\.venv\Scripts\python -X utf8 -I scripts\roteiro_exe.py --chromium --cupons output\fase6\notas-simuladas.json
   py -3.12 -X utf8 -I scripts\verificar_cupons_pdf.py output\fase6\notas-simuladas.json
   ```
3. Roteiro manual completo: **`docs/TESTE_WINDOWS.md`**. Instalar/atualizar/
   desinstalar: `scripts\teste_instalador.ps1` (PowerShell como administrador,
   máquina descartável).

## Observações importantes

- **Não assinamos** o .exe (decisão do projeto). O Windows pode mostrar o aviso
  do SmartScreen — é esperado ("Mais informações → Executar assim mesmo").
- O banco do .exe fica em `%LOCALAPPDATA%\VendaFacilPDV\dados` (gravável mesmo
  instalado em Program Files). Backups automáticos em `...\dados\backups`.
- **Não commitar** segredos, `dados/`, `dist_exe/`, `dist_installer/`, `build/`.
- Detalhes completos do empacotamento: **`docs/BUILD_WINDOWS.md`** e
  **`docs/EMPACOTAMENTO_EXE.md`**.

## Rodar os testes (opcional, antes de empacotar)

Sem `PYTHONPATH` herdado e com `-X utf8 -I` (outro Python desta máquina injeta
bibliotecas incompatíveis):

```bat
backend\.venv\Scripts\python -X utf8 -I -m pip install -r backend\requirements-dev.txt
cd backend && .venv\Scripts\python -X utf8 -I -m pytest -q --tb=short && cd ..
cd painel && .venv\Scripts\python -X utf8 -I -m pytest -q --tb=short && cd ..
npm run build && npx eslint .
node --test frontend-tests/*.test.mjs
npx playwright test --workers=1
```

Em 12/11/2026 (1.0.13): backend 460 verdes e 9 desmarcados (`homologacao`,
exigem os dados reais da loja), painel 23, Node 36, E2E 91. Antes do Playwright,
aponte `TEMP`/`TMP`/`TMPDIR` para fora do repositório.

## Plano de produção

O estado da entrega, os bloqueios de terceiros (certificado, CSC, elevação do
Windows…) e o relatório final ficam em **`plano_producao/`**: comece por
`00_PAINEL.md`, `RETOMADA.md` e `RELATORIO_FINAL.md`. O fiscal fica sempre em
**homologação** até ordem explícita do Álvaro.

## Quando terminar

Reporte os caminhos dos artefatos gerados (`dist_exe\...` e `dist_installer\...`)
e o resultado do teste rápido. Não é necessário commitar nada para gerar o .exe.
