# Fase 3 — Segurança mínima e front de caixa

**Status:** ✅ 24/24 — concluída · **Depende de:** Fase 2

## Objetivo

Um PDV de balcão seguro o bastante para ficar ligado o dia todo num PC de loja, e operável só com teclado e leitor de código de barras.

## Tarefas

### Segurança (backend)

- [x] F3.1 (P5) Limite de tentativas no login local com espera crescente, sem travar o lojista para sempre. Teste S01 — 3544de8 · RED a sexta ainda entrava; suíte196; revisão deleg_6eb90d8f aprovada
- [x] F3.2 (P5) `/registro` fechado depois do primeiro usuário: novo usuário só por quem está autenticado. Teste S02. Conferir que o primeiro acesso da loja continua simples — ac2f81e · RED segundo registro era 200; suíte197; revisão deleg_cbdb6c83 aprovada
- [x] F3.3 (P5) CORS restrito à origem do próprio PDV (`127.0.0.1` e `localhost` na porta em uso). Teste S03. O modo de desenvolvimento do Vite continua funcionando — 433ff7c · RED cabeçalho era *; suíte199; revisão deleg_2268a7a3 aprovada
- [x] F3.4 (P5) Senha: mínimo e lista de senhas fracas revisados; registrar a escolha em `docs/SEGURANCA.md`. Validade do token (30 dias) avaliada e justificada — ebc8390 · RED 12345678 cadastrava; suíte200; revisão deleg_0b710f4c aprovada
- [x] F3.5 (P6) `/docs` e `/openapi.json` desligados quando empacotado. Teste S04 — 88a4ca2 · RED urls_doc não existia; suíte202; revisão deleg_d2c28f21 aprovada
- [x] F3.6 Teste S07: percorre `app.routes` e exige 401 sem token em toda rota `/api/*`, com lista explícita das exceções. Teste S08 — a7a398d · RED POST sem token era 422; suíte204; revisão deleg_b7e4672e aprovada
- [x] F3.7 (P14) Teste S05 (configuração fiscal e da maquininha nunca devolvem segredo) e S06 (log sem segredo depois da suíte) — c7ff77c · testes travam a máscara; suíte206; revisão deleg_8cac5cf5 aprovada
- [x] F3.8 Escrever `docs/SEGURANCA.md`: o que o sistema protege, o que é aceito num PDV offline e por quê (cofre fiscal em claro no SQLite — decisão D6), onde ficam os segredos, o que fazer se o PC da loja for trocado ou roubado — f9d8ad1 · doc conferida contra paths.py; revisão deleg_ff063fa7 aprovada

### Front (caixa usa teclado e leitor, não mouse)

- [x] F3.9 (P10) Carrinho persistido em `localStorage`, restaurado ao abrir e limpo ao finalizar ou cancelar. Teste U01 — 1a23906 · 5 testes Chromium reais; backend206/painel9; revisão deleg_385d098d aprovada
- [x] F3.10 Teclado: leitor de código de barras (digitação rápida + Enter) adiciona o item; Enter confirma; Esc fecha janela; F2 finaliza; atalho para quantidade, desconto e forma de pagamento. Teste U02 — dc0858d · 13 Chromium (8 U02+5 U01),24repetiçõesU02; revisão deleg_4a10f998 aprovada, recheck pós-deps no parent.
- [x] F3.11 Foco sempre volta ao campo de código depois de adicionar, finalizar e fechar janela. Teste U04 — b480a4a · 5 casos U04,15repetições;18Chromium/274backend/9painel; revisão deleg_c563ac96 aprovada, recheck parent.
- [x] F3.12 Campos de quantidade e desconto aceitam vírgula e ponto, sem travar a digitação. Teste U03 — bb36365 · 19casos/38repetições,37Chromium/274backend/9painel/build/lint0; revisão deleg_1b00f290 completa aprovada e recheck parent.
- [x] F3.13 Erros do backend aparecem como mensagem clara na tela (estoque insuficiente, caixa fechado, nota rejeitada), nunca como tela branca — bd6013e · 7casos/21repetições;44Chromium/274backend/9painel/build/eslint0;revisão deleg_30bc8fc6 JSONcompletoaprovado,recheck7verde.
- [x] F3.14 Automatizar U01–U04 com teste de navegador contra o PDV rodando (Playwright como dependência só de desenvolvimento). Se for inviável neste PC, script de roteiro com captura de tela e o motivo no diário — c3cc1a3 ·41U01–U04/48Chromium,274backend/9painel,build/eslint0;revisão deleg_9d101eb8 JSONcompletoaprovado,recheck23verde.
- [x] F3.15 `npm run build` e `npx eslint .` limpos (U05) — c3cc1a3 · npm run build e npx eslint . ambos0 em F3_15_BUILD.txt/F3_15_LINT.txt.

## Complementos da auditoria

- [x] F3.16 P31: parser pt-BR em caixa, fiado, produtos e PDV; U06 — a6a90d5 · `src/lib/numeros.ts` lendo texto editável em Caixa/ContasReceber/PDV/Produtos/XML; 22 unitários + 14 casos XML/locale + 8 Produtos + 10 fiado/caixa; E2E 81 em 4 lotes verdes (28+20+19+14) e recheck lote A 28/28 em F3_16_LOTE_A_GREEN.txt; backend315/painel9/build/lint0.
- [x] F3.17 P26: salvar configurações mascaradas preserva segredos; S10 — 6535b18 ·31novoscasos/305backend/9painel;revisão deleg_cb9b8f05 aprovada,recheck31verde.
- [x] F3.18 P32: fechar XSS na impressão; S11 — 95e2322 ·7ChromiumDOM/controlePNGverdes,recheckpai;review deleg_ab6c44fc aprovado,semhardware/SEFAZ.
- [x] F3.19 P34: total diário sem truncamento nas 100 vendas; U07 — fb9f5b9 · RED2 backend/1 UI; GREEN327 backend/23 painel, 4 casos MT/mês/ano e 1 UI; revisão Luna aprovada.
- [x] F3.20 P40: dependências sem vulnerabilidades conhecidas corrigíveis; S12 — fa736aa · audit21→0, npm_ls/build/lint/13Chromium pós-deps no parent; revisão deleg_bb3cb8d7 aprovada; audit rechecado0 antes do commit.
- [x] F3.21 P41: bootstrap admin concorrente, senha e revogação de token no painel; S13 — 31541bd/1f52324/f54b125 · RED1/8/3; painel23 verdes, migração concorrente e revisão Luna aprovadas.
- [x] F3.22 P42: owner fiscal verificado antes de consultar/cancelar/ler nota; S14 — 342f3d6 · RED 4 falhas; GREEN 323 backend/9 painel; 8 casos S14 e revisão Luna aprovada.

- [x] F3.23 P44/U08: barreira de health da API antes de disponibilizar o Vite no harness E2E; provar com atraso de backend de4s. Corrida ECONNREFUSED reproduzida e correção em revisão deleg_63f791d8. — ba47db4 · atrasoAPI4s RED/GREEN e recheckU01F5; revisão deleg_63f791d8 aprovada, pós-deps validado no parent.

- [x] F3.24 P25/S09: provar sanitização de bytes inválidos/corpo bruto no log; complementar S06 sem alegar que só JSON prova ausência de segredo. Item faltava no plano da fase apesar da pista/matriz. — 5da31fa ·10novoscasos,315backend/9painel;review deleg_0911d189 aprovada,recheck10verde.

## Portão de saída

- [x] S01–S08 e U01–U05 ✅ em `03_TESTES.md` — U01–U05 em 1a23906/dc0858d/b480a4a/bb36365/c3cc1a3; U06 em a6a90d5.
- [x] `docs/SEGURANCA.md` existe; `docs/MANUAL.md` lista os atalhos de teclado — SEGURANCA.md desde f9d8ad1 (atualizado em 95e2322); MANUAL.md, seção "Atalhos do caixa".
- [x] Suítes verdes; pasta do plano commitada e `git push origin master` — d9038dc · backend327/painel23/E2E82/Node29/build/lint0; push conferido por ls-remote: d9038dcfa5a478412a1497aa9e9b89acc4903444.

## Evidências

| Item | Comando | Saída resumida |
|---|---|---|
| Suíte backend | `backend: .venv/Scripts/python -X utf8 -I -m pytest -q --tb=short` | `315 passed, 3 warnings in 35.65s` (12/11 09:12 BRT) |
| Suíte painel | `painel: .venv/Scripts/python -X utf8 -I -m pytest -q --tb=short` | `9 passed, 3 warnings in 1.37s` |
| Rotas sem token (S07) | `backend/tests/test_rotas.py` via suíte | verde desde a7a398d |
| Log sem segredo (S06) | `test_log_segredo.py` + F3.24 | 10 casos, verdes em 5da31fa |
| Venda só com teclado (U02) | `npx playwright test e2e/teclado.spec.ts` | lote B: 20 passed (50.5s), F3_16_LOTE_B.txt |
| E2E completo | 4 lotes A/B/C/XML | 81/81 passed; lote A recheck 28/28 (F3_16_LOTE_A_GREEN.txt) |
