# Testes

⬜ não rodou · 🟥 falhou · ✅ passou, com a saída anotada na tarefa

| ID | Prova | Estado |
|---|---|---|
| T1 | Suíte backend antes de mexer, número de verdes anotado no diário | ✅ |
| T2 | Carteira R$ 20, palheiro R$ 2, fator 20. Venda mista 1+3 cobra R$ 26 e baixa 23 | ✅ |
| T3 | 20 avulsos cobram R$ 40 | ✅ |
| T4 | Estoque 15 recusa a carteira e aceita até 15 avulsos | ✅ |
| T5 | Checkout sem modo, com a opção ligada, vende unidade e não a carteira | ✅ |
| T6 | Opção desligada: venda e XML iguais aos de hoje | ✅ |
| T7 | XML em CX, opção ligada: 2 carteiras viram 40; preços de venda não mudam; custo unitário = custo da carteira ÷ 20 | ✅ |
| T8 | XML em UN com "CX" e "50" no nome, sem confirmação do operador: quantidade não multiplica | ✅ |
| T9 | Mudar o fator com estoque já lançado não altera a quantidade em estoque | ✅ |
| T10 | Item de NFC-e/cupom: 1 carteira a R$ 20 numa linha, 1 UN a R$ 2 na outra | ✅ |
| T11 | Playwright no PDV isolado: cadastra, compra 2 carteiras (estoque 40), vende 1 carteira e 3 avulsos (saldo 17, total R$ 26), recusa carteira com saldo baixo | ✅ |
| T12 | `npm run build` e `npx eslint .` | ⬜ |
| T13 | Suíte backend inteira verde no commit final | ⬜ |
| T14 | Workflow Build Windows EXE verde no `master` e versão 1.0.15 no artefato ou no run | ⬜ |

T11 usa `VENDAFACIL_DATA_DIR` temporário, porta 3021, `VENDAFACIL_NO_BROWSER=1`, `VENDAFACIL_PAINEL_URL` vazio. `TEMP`/`TMP`/`TMPDIR` fora do repositório. Playwright com `--workers=1`.

Provas E1–E4: backend 466 antes, 492 após XML; testes novos de cadastro 9 falhas antes, vendas 10 falhas antes, XML 4 falhas antes. Playwright XML e embalagem: 18 passed, incluindo o arquivo real local vf-nota.xml (NF-e 446817), estoque 600, custo 2,74, venda 3,56. SHA-256: ea3051184f0bd3802b2cf716f2c295cff42ab97d017183e33188c10208fe4dfb. Fonte real fora do git; testes em banco temporário.

T10: test_embalagem_fiscal.py cobre XML direto e payload, quantidades comerciais 1 CART/1 UN e tributação 20 UN; sem SEFAZ. T11: VF_E2E_API_PORT=3021 VF_EMBALAGEM_API=http://127.0.0.1:3021 npx playwright test e2e/embalagem.spec.ts --workers=1: 4 passed, com XML real, entrada manual e fator preservado.
