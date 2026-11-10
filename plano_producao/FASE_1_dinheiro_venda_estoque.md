# Fase 1 — Dinheiro, venda, estoque e cancelamento

**Status:** 🟨 em andamento · **Depende de:** Fase 0 · **Pistas:** P1, P2, P3, P7, P11 · **Testes:** D01–D05, V01–V13

## Objetivo

Nenhuma venda pode ficar pela metade, nenhum centavo pode sumir e toda venda pode ser cancelada com o estoque e o fiado voltando ao lugar.

## Ordem obrigatória

P3 → P7 → P1 → P2. Todas passam por `backend/database.py`, que é **serial**: um escritor por vez.

## Tarefas

- [x] F1.1 (P3) Criar o módulo único de dinheiro (`backend/dinheiro.py`): `Decimal`, `ROUND_HALF_UP`, funções para converter entrada, multiplicar quantidade × preço, somar e devolver valor de 2 casas. Testes D01 e D02 falhando primeiro — 3fe1aa4 · test_dinheiro.py: 7 passed; revisão deleg_de215589 aprovada; suíte backend 83/painel 7
- [x] F1.2 (P3) Trocar o cálculo do checkout (`vendas.py`) para o módulo de dinheiro. O schema continua `REAL`; o que muda é a conta — 52bb220 · test_checkout_dinheiro_half_up RED→GREEN; backend84/painel7; revisão deleg_6065d70c aprovada
- [~] F1.3 (P3) Trocar o cálculo do resumo de caixa, do fiado e dos relatórios para o módulo de dinheiro. Teste D05
- [ ] F1.4 (P3) Trocar os totais e o rateio de desconto do XML fiscal (`fiscal_direto.py`, `_ratear`) para o módulo de dinheiro. Testes D03 e D04. Os 49 testes fiscais existentes continuam verdes
- [ ] F1.5 (P7) Definir `busy_timeout`, `foreign_keys=ON` e `synchronous` na abertura da conexão (`database.py:15` e `:1339`). Conferir que `foreign_keys` não quebra dado existente (rodar contra uma cópia de banco com dados)
- [ ] F1.6 (P1) Criar em `database.py` a função única de checkout: valida estoque, baixa, grava venda, itens, movimentações e conta a receber **numa transação** (`BEGIN IMMEDIATE`). `vendas.py` passa a chamá-la. Testes V01, V02, V03
- [ ] F1.7 (P1) Concorrência e limites: testes V04, V05, V12, V13
- [ ] F1.8 (P1) Queda no meio: teste V06 com subprocesso morto durante o checkout
- [ ] F1.9 (P2) Backend do cancelamento: `POST /api/vendas/{id}/cancelar` com motivo; numa transação: status `cancelada`, devolve estoque com movimentação, estorna a conta a receber. Testes V07, V08, V10. Venda fiada com baixa já feita segue a decisão D8
- [ ] F1.10 (P2) Cancelamento × fiscal: recusar se houver NFC-e autorizada e não cancelada (V09); conferir o que `fiscal.cancelar_nfce` faz hoje com o estoque e alinhar (cancelar a nota não devolve estoque sozinho; quem devolve é o cancelamento da venda)
- [ ] F1.11 (P2) Venda cancelada fora do caixa, do dashboard e dos relatórios (V11). Tela: botão e confirmação em `src/pages/Vendas.tsx`, com atalho de teclado
- [ ] F1.12 (P11) Aplicar a decisão D3 (padrão: manter) e cobrir o comportamento atual com um teste, para não mudar sem querer
- [ ] F1.13 Revisor adversário: um subagente tenta quebrar checkout e cancelamento (valores limite, concorrência, reinício, usuário errado). Cada falha vira pista, teste e correção

## Complementos da auditoria

- [ ] F1.14 P23: validar referências de cliente/categoria e propriedade no checkout; V14

## Portão de saída

- [ ] D01–D05 e V01–V13 ✅ em `03_TESTES.md`
- [ ] Suíte do backend verde, com o número novo no painel
- [ ] `grep -n "round(" backend/vendas.py backend/caixa.py backend/contas_receber.py` não mostra conta de dinheiro fora do módulo
- [ ] Um commit por pista; `docs/CAIXA.md` e `docs/MANUAL.md` atualizados com o cancelamento de venda
- [ ] Pasta do plano commitada e `git push origin master`

## Evidências

| Item | Comando | Saída resumida |
|---|---|---|
| Suíte | | |
| Falha antes da correção (V01) | | |
| Concorrência (V04) | | |
| Queda no meio (V06) | | |
