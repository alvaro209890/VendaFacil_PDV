# Especificação fechada (Álvaro, 13/11/2026)

Não reabrir. O exemplo numérico é o critério de aceite.

## Exemplo

Carteira de palheiro com 20 unidades.

| Ação | Cobra | Estoque |
|---|---|---|
| Compra ou lança 2 carteiras | custo da carteira ÷ 20 = custo de cada palheiro | +40 palheiros |
| Vende 1 carteira | R$ 20 | −20 |
| Vende 1 palheiro | R$ 2 | −1 |
| Vende 1 carteira e 3 palheiros | R$ 26 | −23 |
| 20 palheiros avulsos | R$ 40, não R$ 20 | −20 |
| Estoque 15, tenta vender 1 carteira | recusa | permanece 15; avulso segue até 15 |

Carteira de 30 é a mesma regra com 30 no lugar de 20. Vale para caixa, fardo, pacote, display e carteira **quando o operador ligar** “também vende por unidade”. Desligada, o produto é o de hoje.

O preço da unidade é digitado. Não é a carteira dividida pela quantidade, embora a tela possa sugerir essa conta já preenchida e editável. R$ 20 a carteira e R$ 2 o palheiro é o caso que tem de passar.

## Estoque

Um produto só. Estoque sempre na unidade menor (o palheiro). Vender a carteira desconta as unidades. Não existe etapa de “abrir a caixa”.

Trocar a quantidade por embalagem com estoque já lançado não multiplica nem divide o que já está contado. A tela avisa e o número de unidades permanece.

## Cadastro (`src/pages/Produtos.tsx`)

Opção desligada por padrão: **Também vende por unidade**.

Ligada, obrigatórios e maiores que zero:

- nome da embalagem (carteira, caixa, fardo…), gravado na unidade de compra já existente
- quantas unidades vêm dentro (`quantidade_por_embalagem`)
- preço da embalagem fechada
- preço da unidade

Na lista, linguagem de balcão: `3 carteiras e 5 avulsos (65 palheiros)`.

Produto antigo, ao ligar a opção, pede os dois preços. Não reinterpreta sozinho o `preco_venda` que já estava gravado e não mexe no estoque.

## Caixa (`src/pages/PDV.tsx`, `backend/vendas.py`)

Dois lançamentos visíveis, grandes: **Carteira — R$ 20** e **Unidade — R$ 2**.

- Código de barras da embalagem lança a embalagem, não vinte cliques.
- Avulso entra pelo botão, pela busca ou por um segundo código, se cadastrado.
- As duas linhas podem estar no mesmo carrinho.
- Checkout sem modo, em produto com a opção ligada, vende **unidade** pelo preço da unidade. Embalagem só com o modo explícito. Assim um cliente antigo não cobra R$ 2 numa carteira de R$ 20 nem o contrário.
- Produto com a opção desligada: o checkout de hoje, `produto_id` + `quantidade`, preço `preco_venda`, baixa 1 para 1.
- Histórico, caixa e relatório mostram o que foi vendido (1 carteira ou 3 avulsos) e baixam unidades.
- Custo da unidade = custo da embalagem ÷ quantidade de dentro. Lucro usa esse custo vezes as unidades baixadas, na carteira e no avulso.

## Cupom e NFC-e

A linha é o que o cliente levou, não a unidade interna.

| Venda | Quantidade na nota | Unidade | Preço |
|---|---|---|---|
| Carteira | 1 | carteira / unidade de compra | R$ 20 |
| Palheiro | 1 | UN | R$ 2 |

Fiscal continua em homologação. Não chamar a SEFAZ nesta entrega. Cobrir com o teste que já monta o item (`backend/fiscal_direto.py` e a suíte fiscal existente).

## XML de compra

Prévia em português, antes de confirmar, dizendo o que entra.

| Situação | O que fazer |
|---|---|
| Opção ligada e a nota vem na unidade da embalagem | `2 carteiras viram 40 palheiros; custo de cada um = custo da carteira ÷ 20`. Não alterar os dois preços de venda |
| Opção ligada e a nota vem em UN | fator 1, entra unidade a unidade |
| Opção desligada | lógica atual de `backend/produtos.py` (fator 1 se a unidade da nota é a do estoque; fator do cadastro se a nota vem na unidade de compra) |
| Produto novo, nome parece caixa/fardo/pacote/display/carteira, nota em UN | não converter. Perguntar: “Isto é embalagem fechada que também vende por unidade?”. Só converter se o operador informar quantas unidades vêm dentro e os dois preços |
| Produto novo sem essa confirmação | gravar quantidade e unidade da nota, fator 1, venda sugerida = custo + 30% |

Proibido ler número no nome e multiplicar. A NF-e 446817 (`CX 00050 KAISER LT 350ML`, `uCom=UN`, `qCom=600`) continua 600 UN a R$ 2,74 se ninguém confirmar a abertura.

## Fora desta regra

KG, G, LT e ML. Produto que só se vende inteiro. Dois cadastros separados para a mesma mercadoria. Abrir caixa como movimento próprio.
