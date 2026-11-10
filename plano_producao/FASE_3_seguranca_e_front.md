# Fase 3 — Segurança mínima e front de caixa

**Status:** ⬜ não iniciada · **Depende de:** Fase 2 · **Pistas:** P5, P6, P10, P14 · **Testes:** S01–S08, U01–U05

## Objetivo

Um PDV de balcão seguro o bastante para ficar ligado o dia todo num PC de loja, e operável só com teclado e leitor de código de barras.

## Tarefas

### Segurança (backend)

- [ ] F3.1 (P5) Limite de tentativas no login local com espera crescente, sem travar o lojista para sempre. Teste S01
- [ ] F3.2 (P5) `/registro` fechado depois do primeiro usuário: novo usuário só por quem está autenticado. Teste S02. Conferir que o primeiro acesso da loja continua simples
- [ ] F3.3 (P5) CORS restrito à origem do próprio PDV (`127.0.0.1` e `localhost` na porta em uso). Teste S03. O modo de desenvolvimento do Vite continua funcionando
- [ ] F3.4 (P5) Senha: mínimo e lista de senhas fracas revisados; registrar a escolha em `docs/SEGURANCA.md`. Validade do token (30 dias) avaliada e justificada
- [ ] F3.5 (P6) `/docs` e `/openapi.json` desligados quando empacotado. Teste S04
- [ ] F3.6 Teste S07: percorre `app.routes` e exige 401 sem token em toda rota `/api/*`, com lista explícita das exceções. Teste S08
- [ ] F3.7 (P14) Teste S05 (configuração fiscal e da maquininha nunca devolvem segredo) e S06 (log sem segredo depois da suíte)
- [ ] F3.8 Escrever `docs/SEGURANCA.md`: o que o sistema protege, o que é aceito num PDV offline e por quê (cofre fiscal em claro no SQLite — decisão D6), onde ficam os segredos, o que fazer se o PC da loja for trocado ou roubado

### Front (caixa usa teclado e leitor, não mouse)

- [ ] F3.9 (P10) Carrinho persistido em `localStorage`, restaurado ao abrir e limpo ao finalizar ou cancelar. Teste U01
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
