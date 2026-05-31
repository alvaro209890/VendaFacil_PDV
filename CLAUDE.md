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

Ambas as pastas são ignoradas pelo git (não commitar binários).

## Validar (teste rápido)

1. Dois cliques em `dist_exe\VendaFacilPDV.exe` → o navegador abre em
   `http://127.0.0.1:3020/`.
2. Siga o roteiro de teste manual: **`docs/TESTE_WINDOWS.md`**.

## Observações importantes

- **Não assinamos** o .exe (decisão do projeto). O Windows pode mostrar o aviso
  do SmartScreen — é esperado ("Mais informações → Executar assim mesmo").
- O banco do .exe fica em `%LOCALAPPDATA%\VendaFacilPDV\dados` (gravável mesmo
  instalado em Program Files). Backups automáticos em `...\dados\backups`.
- **Não commitar** segredos, `dados/`, `dist_exe/`, `dist_installer/`, `build/`.
- Detalhes completos do empacotamento: **`docs/BUILD_WINDOWS.md`** e
  **`docs/EMPACOTAMENTO_EXE.md`**.

## Rodar os testes (opcional, antes de empacotar)

```bat
backend\.venv\Scripts\pip install -r requirements-dev.txt
cd backend && .venv\Scripts\python -m pytest -q && cd ..
```

## Quando terminar

Reporte os caminhos dos artefatos gerados (`dist_exe\...` e `dist_installer\...`)
e o resultado do teste rápido. Não é necessário commitar nada para gerar o .exe.
