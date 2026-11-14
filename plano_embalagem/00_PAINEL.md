# Painel

| | |
|---|---|
| Estado | 🔄 EM EXECUÇÃO |
| Versão alvo | 1.0.15 |
| Branch | `master` |
| Próxima ação | E8.1 |

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
| E8 | [~] |

## O que já é fato (13/11/2026)

- O PDV tem um estoque e um `preco_venda`. O caixa manda `produto_id` e `quantidade`.
- Já existem `unidade`, `unidade_compra` e `quantidade_por_embalagem`. O XML só multiplica quando a unidade da nota é a de compra e é diferente da de estoque. Nota em UN fica com fator 1.
- Prova real: NF-e 446817, item `CX 00050 KAISER LT 350ML`, `uCom=UN`, `qCom=600`, `vUnCom=2.74`. Entrou como 600 UN a R$ 2,74, venda R$ 3,56. O 50 do nome não virou estoque. Isso tem de continuar.
- O banco da loja em `%LOCALAPPDATA%\VendaFacilPDV\dados` não entra neste trabalho. O `dados\vendafacil.db` do repositório é teste e pode ter esse Kaiser. Não commitar `dados/`.
