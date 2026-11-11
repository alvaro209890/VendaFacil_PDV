# Fase 3 — Segurança mínima e front de caixa

**Status:** 🟨 em andamento (F3.1–F3.9 commitados; retorno à Fase 2 para lacunas do portão) · **Depende de:** Fase 2 · **Pistas:** P5, P6, P10, P14 · **Testes:** S01–S08, U01–U05

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
- [ ] F3.10 Teclado: leitor de código de barras (digitação rápida + Enter) adiciona o item; Enter confirma; Esc fecha janela; F2 finaliza; atalho para quantidade, desconto e forma de pagamento. Teste U02
- [ ] F3.11 Foco sempre volta ao campo de código depois de adicionar, finalizar e fechar janela. Teste U04
- [ ] F3.12 Campos de quantidade e desconto aceitam vírgula e ponto, sem travar a digitação. Teste U03
- [ ] F3.13 Erros do backend aparecem como mensagem clara na tela (estoque insuficiente, caixa fechado, nota rejeitada), nunca como tela branca
- [ ] F3.14 Automatizar U01–U04 com teste de navegador contra o PDV rodando (Playwright como dependência só de desenvolvimento). Se for inviável neste PC, script de roteiro com captura de tela e o motivo no diário
- [ ] F3.15 `npm run build` e `npx eslint .` limpos (U05)

## Complementos da auditoria

- [ ] F3.16 P31: parser pt-BR em caixa, fiado, produtos e PDV; U06
- [ ] F3.17 P26: salvar configurações mascaradas preserva segredos; S10
- [ ] F3.18 P32: fechar XSS na impressão; S11
- [ ] F3.19 P34: total diário sem truncamento nas 100 vendas; U07
- [ ] F3.20 P40: dependências sem vulnerabilidades conhecidas corrigíveis; S12
- [ ] F3.21 P41: bootstrap admin concorrente, senha e revogação de token no painel; S13
- [ ] F3.22 P42: owner fiscal verificado antes de consultar/cancelar/ler nota; S14

## Portão de saída

- [ ] S01–S08 e U01–U05 ✅ em `03_TESTES.md`
- [ ] `docs/SEGURANCA.md` existe; `docs/MANUAL.md` lista os atalhos de teclado
- [ ] Suítes verdes; pasta do plano commitada e `git push origin master`

## Evidências

| Item | Comando | Saída resumida |
|---|---|---|
| Suíte | | |
| Rotas sem token (S07) | | |
| Log sem segredo (S06) | | |
| Venda só com teclado (U02) | | |
