# Testes

⬜ não rodou · 🟥 falhou · ✅ passou, com a saída anotada na tarefa

| ID | Prova | Estado |
|---|---|---|
| T1 | Suíte backend antes de mexer, número de verdes anotado no diário | ⬜ |
| T2 | Carteira R$ 20, palheiro R$ 2, fator 20. Venda mista 1+3 cobra R$ 26 e baixa 23 | ⬜ |
| T3 | 20 avulsos cobram R$ 40 | ⬜ |
| T4 | Estoque 15 recusa a carteira e aceita até 15 avulsos | ⬜ |
| T5 | Checkout sem modo, com a opção ligada, vende unidade e não a carteira | ⬜ |
| T6 | Opção desligada: venda e XML iguais aos de hoje | ⬜ |
| T7 | XML em CX, opção ligada: 2 carteiras viram 40; preços de venda não mudam; custo unitário = custo da carteira ÷ 20 | ⬜ |
| T8 | XML em UN com "CX" e "50" no nome, sem confirmação do operador: quantidade não multiplica | ⬜ |
| T9 | Mudar o fator com estoque já lançado não altera a quantidade em estoque | ⬜ |
| T10 | Item de NFC-e/cupom: 1 carteira a R$ 20 numa linha, 1 UN a R$ 2 na outra | ⬜ |
| T11 | Playwright no PDV isolado: cadastra, compra 2 carteiras (estoque 40), vende 1 carteira e 3 avulsos (saldo 17, total R$ 26), recusa carteira com saldo baixo | ⬜ |
| T12 | `npm run build` e `npx eslint .` | ⬜ |
| T13 | Suíte backend inteira verde no commit final | ⬜ |
| T14 | Workflow Build Windows EXE verde no `master` e versão 1.0.15 no artefato ou no run | ⬜ |

T11 usa `VENDAFACIL_DATA_DIR` temporário, porta 3021, `VENDAFACIL_NO_BROWSER=1`, `VENDAFACIL_PAINEL_URL` vazio. `TEMP`/`TMP`/`TMPDIR` fora do repositório. Playwright com `--workers=1`.
