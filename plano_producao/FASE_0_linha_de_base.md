# Fase 0 — Linha de base e auditoria

**Status:** ✅ concluída · **Depende de:** nada · **Toca em código:** não (só leitura, venv e esta pasta)

## Objetivo

Confirmar o ponto de partida com números medidos e transformar as pistas em fila de trabalho confirmada.

## Tarefas

- [x] F0.1 Conferir o repositório: `git log --oneline -1` = `6da6899`; `git status --porcelain` mostra só `M dist_exe/VendaFacilPDV.exe`, `?? PROMPT_CLAUDE_CODE_PRODUCAO.md` e `?? plano_producao/`. Diferença → registrar no diário antes de seguir — 6da6899 · git status --short --branch: somente binário modificado + rascunho + plano
- [x] F0.2 Provar o subagente: um `delegate_task` de 1 linha no `ag/gemini-3.8-flash-high` com raciocínio `high` responde — 6da6899 · delegate_task deleg_bdebea33: Subagente operacional (Gemini high, 1 chamada)
- [x] F0.3 Backend: `cd backend && .venv/Scripts/pip install -q -r ../requirements-dev.txt && .venv/Scripts/python -m pytest -q` → 76 passed — 6da6899 · env -u PYTHONPATH .venv/Scripts/python -I -m pytest -q: 76 passed, 3 warnings, 1.61s
- [x] F0.4 Painel: criar o venv (`py -3.11 -m venv .venv`), instalar `requirements.txt` + `../requirements-dev.txt`, rodar `pytest -q`. Registrar o número. Teste falhando no painel vira pista nova — 6da6899 · python -I -m pip install; python -I -m pytest -q: 7 passed, 3 warnings, 1.50s
- [x] F0.5 Front: `npm install`, `npm run build`, `npx eslint .` — registrar o resultado — 6da6899 · npm install; npm run build; npx eslint .: exit 0 (audit: 21 vulnerabilidades totais; 2 runtime)
- [x] F0.6 Ler: `CLAUDE.md`, `docs/CHECKLIST_COMERCIALIZACAO.md`, `docs/TESTES.md`, `docs/TESTE_WINDOWS.md`, `docs/TESTE_FISCAL_WINDOWS.md`, `docs/LEGISLACAO_FISCAL_MT.md`, `docs/VINCULO_PAGAMENTO_MT.md`, `docs/CONTINGENCIA_OFFLINE.md`, `docs/BACKUP.md`, `docs/CAIXA.md`, `docs/LICENCA.md` — 6da6899 · leitura integral dos 11 documentos; divergências de fiscal e CI serão corrigidas nas fases previstas
- [x] F0.7 Auditoria em paralelo: 1 subagente por módulo do backend (`database.py` dividido em 3 faixas de linhas) + 1 para `src/` + 1 para `painel/`. Retorno de cada um: `arquivo:linha · sintoma · como reproduzir · gravidade` — 6da6899 · seis auditorias deleg_4ebfcb98 + revisão em evidencias/F0_AUDITORIA.md; P23–P42 distribuídas
- [x] F0.8 Consolidar: cada pista de `02_PISTAS.md` fica confirmada (segue aberta) ou descartada com prova (➖); achado novo vira `P23`… com teste novo em `03_TESTES.md` e tarefa nova na fase certa — 6da6899 · seis auditorias deleg_4ebfcb98 + revisão em evidencias/F0_AUDITORIA.md; P23–P42 distribuídas
- [x] F0.9 Commitar a pasta `plano_producao/` (`docs: plano de produção e linha de base`) e atualizar o painel — 52c6e1e · git commit; backend 76 passed, painel 7 passed

## Portão de saída

- [x] Números de partida gravados no `00_PAINEL.md` (backend, painel, build do front, lint)
- [x] Toda pista com status definido; achados novos distribuídos nas fases — 6da6899 · 42 pistas / 120 testes, IDs únicos
- [x] Nenhum arquivo de código alterado — 6da6899 · git diff --stat: apenas o binário que já estava modificado; plano ainda untracked

## Evidências

| Item | Comando | Saída resumida |
|---|---|---|
| Backend | `env -u PYTHONPATH backend/.venv/Scripts/python -I -m pytest -q backend/tests` | 76 passed, 3 warnings; `evidencias/F0_backend.txt` |
| Painel | `env -u PYTHONPATH painel/.venv/Scripts/python -I -m pytest -q painel/tests` | 7 passed, 3 warnings; `evidencias/F0_painel.txt` |
| Build do front | `npm run build` | exit 0; `evidencias/F0_front.txt` (aviso chunk >500 kB) |
| Lint | `npx eslint .` | exit 0; `evidencias/F0_lint.txt` vazio = sem achados |
| Subagente | `delegate_task`, deleg_bdebea33 | Subagente operacional, Gemini high; 6 auditorias em deleg_4ebfcb98 |
