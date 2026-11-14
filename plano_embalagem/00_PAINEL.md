# Painel

| | |
|---|---|
| Estado | ✅ CONCLUÍDO |
| Versão alvo | 1.0.15 |
| Branch | `master` |
| Próxima ação | Entrega do Setup 1.0.15 — run 43549468463 verde |

## Placar

| ID | Estado |
|---|---|
| E1 | [x] |
| E2 | [x] |
| E3 | [x] |
| E4 | [x] |
| E5 | [x] |
| E6 | [x] |
| E7 | [x] |
| E8 | [x] |

## O que já é fato (13/11/2026)

- O PDV tem um estoque e um `preco_venda`. O caixa manda `produto_id` e `quantidade`.
- Já existem `unidade`, `unidade_compra` e `quantidade_por_embalagem`. O XML só multiplica quando a unidade da nota é a de compra e é diferente da de estoque. Nota em UN fica com fator 1.
- Prova real: NF-e 446817, item `CX 00050 KAISER LT 350ML`, `uCom=UN`, `qCom=600`, `vUnCom=2.74`. Entrou como 600 UN a R$ 2,74, venda R$ 3,56. O 50 do nome não virou estoque. Isso tem de continuar.
- **1.0.16 (14/11/2026, Claude):** continua 600 UN; o custo passou a ser o de aquisição, R$ 2,7606 (soma vOutro R$ 12,36), venda sugerida R$ 3,59. Marcar caixa + unidade nessa nota não multiplica mais (a 1.0.15 gravava 7.200). Ver `docs/CAIXA_E_UNIDADE.md`.
- O banco da loja em `%LOCALAPPDATA%\VendaFacilPDV\dados` não entra neste trabalho. O `dados\vendafacil.db` do repositório é teste e pode ter esse Kaiser. Não commitar `dados/`.
