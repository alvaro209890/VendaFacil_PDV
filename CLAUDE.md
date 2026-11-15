# CLAUDE.md — instruções para o agente

## Entrega 1.0.26 — revisão visual do front

Dinheiro em pt-BR por `moeda()` (`src/lib/numeros.ts`), rótulos de pagamento em
`src/lib/rotulos.ts`, busca e tabela legível em Produtos, `categoria_nome` na API
de produtos, venda cancelada marcada, preço sugerido da importação acompanha o
custo. Lista dos 16 defeitos, testes e hashes em `docs/ATUALIZACAO_1.0.26.md`.
Instalada no James: `/health` 1.0.26, produtos idênticos ao estado anterior.
Valor exibido usa `moeda()`; não voltar a `toFixed(2)` em texto de tela. Campos
de digitação seguem aceitando vírgula e ponto (testes de localização).

## Entrega 1.0.25 — vídeo de importação no PDV

Tutorial narrado/legendado da interface real em `public/tutoriais`, distribuído
no exe. Acesso em Produtos → Como importar XML? e no topo do Manual; reprodução
local, download e atalhos por capítulo. Roteiro e produtor em `scripts/tutorial_xml/`;
guia de entrega em `docs/ATUALIZACAO_1.0.25.md`.
Instalada no James: `/health` 1.0.25, tarefa Running, licença ativa e produtos
idênticos ao backup. Vídeo completo conferido por SHA-256, HTTP Range 206 e
VTT disponíveis. 105 testes de navegador, 3 de versão, build/lint e player
no exe aprovados. O vídeo é um asset do produto e precisa acompanhar o build.

## Entrega 1.0.24 — 15/11/2026

Contagem da nota separada da forma de venda, também nas reposições. Nota em
UN não multiplica só porque a mercadoria chegou em caixa. Cadastro/edição
com três formatos explícitos, dois preços quando aplicável, preservação do
código da unidade e conversão de estoque/custo conferida. Proteção de unidade
de estoque para preservar estornos de vendas anteriores. Guia e provas:
`docs/ATUALIZACAO_1.0.24.md`.
Instalada no James (Setup ExitCode 0, `/health` 1.0.24, tarefa Running,
licença ativa, produtos idênticos antes/depois e backup íntegro). Backend 557,
Node 46, navegador fonte 105 e executável 13 aprovados; roteiro do exe 49
requisições/zero 5xx. Guia rápido no desktop e manual do PDV atualizados.

## Entrega atual 1.0.23 — 14/11/2026

Tela de importação de XML em **cartões**: um por produto, com *Na nota · Entra no
estoque · Custo por unidade · Preço de venda* + lucro %; "Como vende?" uma vez só
(recolhida nos itens simples, amarela nos de caixa); margem para todos os novos;
custo total no rodapé; linhas repetidas da mesma NF (mesmo código) juntadas com
custo médio. Lógica e payload inalterados. Testes e2e localizam os campos por
`aria-label` "<rótulo> do item N" (não há mais tabela/columnheader).
Provas: `docs/ATUALIZACAO_1.0.23.md`.

## Entrega 1.0.22 — 14/11/2026

Importação de XML com a decisão explícita de caixa x unidade: *só por unidade*,
*caixa fechada e unidade* ou *só a embalagem fechada*; aviso de embalagem pelos
sinais da nota; `UN1`/`UND`/`PC` normalizados para UN; validação só do campo que
o operador consegue editar. Instalada no James e testada com a suíte completa.
Provas e limites: `docs/ATUALIZACAO_1.0.22.md`. Descrições abaixo são históricas.

## Entrega 1.0.21 — 14/11/2026

Instalada/reiniciada no James e no PDV local deste PC. Botão − Remover em cada
linha, menos remove a última unidade, pular produto desconhecido e foco no leitor.
Provas, hashes e limites: `docs/ATUALIZACAO_1.0.21.md`. Na 3020 local, o processo
antigo Python 3.11/1.0.14 foi substituído pelo Python da venv do projeto/1.0.21;
mantém `dados/`. No James, exe e tarefa de logon, com banco local preservado.
Descrições de versões anteriores abaixo são históricas.

## Entrega atual 1.0.20 — 14/11/2026

Instalada no PC James. Card de alertas abre `/produtos?estoque=alerta`, lista
completa de ativos com estoque <= mínimo, filtro removível e persistente na URL.
Build, hashes, testes e leitor: `docs/ATUALIZACAO_1.0.20.md`. Aceite inicial e
bloqueios externos: `docs/ACEITE_JAMES_1.0.19.md` (Point 403, SEFAZ 230, foto do
cupom e débito físico pendentes). As versões descritas abaixo são históricas.

## Atualização local 1.0.19 — 14/11/2026

Recebimento do fiado com forma de pagamento, cartão/PIX na Point e PIX copia e
cola independente, salvo para pagamento posterior. Veja `docs/CAIXA.md` e
`docs/TREINAMENTO_OPERADOR.md`. Artefatos atuais: `dist_exe/VendaFacilPDV.exe`
e `dist_installer/VendaFacilPDV-Setup-1.0.19.exe`. A descrição da 1.0.18 abaixo
é histórica. Instalada no James em 14/11: `docs/ACEITE_JAMES_1.0.19.md` registra
as provas, o 403 de Point Orders, o 230 de homologação e o aceite físico pendente.
Esta rodada não publicou no GitHub.

Aceite específico do binário, com banco descartável e sem terminal/SEFAZ reais:
`backend\.venv\Scripts\python -X utf8 -I scripts\verificar_fiado_exe.py`.
O roteiro verifica código salvo após reinício, venda liberada durante a espera,
formas corretas no histórico, baixa sem duplicação e dinheiro esperado.

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
(`gh run list --workflow build-exe.yml`). A entrega atual é a **1.0.18**
(caixa e unidade com preços diferentes, ver `docs/CAIXA_E_UNIDADE.md`; vender sem
abrir caixa e sem aviso, ver `docs/CAIXA.md`; janela de cadastro/entrada
rápida no PDV, ver `docs/MANUAL.md` §3). Build local validado em
14/11/2026: `dist_installer\VendaFacilPDV-Setup-1.0.18.exe` (40.003.652 bytes,
SHA-256 `A87EAD1073CE38C72E6FA905CE0D8A020957DB25900096058A2C36DA68676C6B`) e `dist_exe\VendaFacilPDV.exe` (39.718.718 bytes,
SHA-256 `3764AAA843FC8573ED69E80EC4558F4084710A8B3CB8730890B4983952F1958C`). O Setup do Actions tem outro hash (o build não é
reprodutível byte a byte). A 1.0.16 e a 1.0.17 foram publicadas e substituídas no mesmo dia.
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
