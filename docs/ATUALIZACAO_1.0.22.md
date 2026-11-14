# Importação de XML: caixa x unidade bem especificada — 1.0.22

Hermes-aws, 14/11/2026. Pedido do Álvaro depois de tentar importar a nota do
fornecedor e achar a tela confusa: *"a questão do que é caixa e é vendido por
unidade não está bem especificado e muitas vezes a caixa vem só e já aparece
para vender o produto por unidade"*.

## O que mudou

- **Três decisões claras por produto novo** na prévia do XML:
  **Só por unidade** (comprei em caixa, vendo a unidade), **Caixa fechada e
  unidade** (dois preços) e **Só a embalagem fechada**. Antes só existia o
  checkbox "Vende a embalagem fechada e também a unidade, com preços
  diferentes?", que obrigava a preencher dois preços mesmo quando o lojista só
  queria estoque em unidades.
- **Novo modo de entrada `unidade`** no
  `POST /api/produtos/importar-xml/confirmar`: estoque em UN,
  `vende_por_unidade = 0` e custo dividido pelo fator da nota. Era o caso mais
  comum do mercadinho e não tinha caminho.
- **Aviso de embalagem**: a prévia lista os sinais que encontrou (`qTrib ÷ qCom`,
  nome com CX/FARDO/PCT/CARTEIRA, `uCom` de contagem) e mostra *"Esta nota tem
  cara de caixa fechada"*. Nada multiplica sem o operador confirmar — a regra
  do "o número no nome não vira estoque" continua valendo.
- **Unidade normalizada**: `UN1`, `UND`, `UNID`, `PC`, `PÇ`, `PCS`, `PECA` são
  lidas como **UN**, com aviso na tela. Antes `UN1` virava uma unidade própria e
  a nota inteira era tratada como embalagem fechada. Nome de embalagem
  (`CARTEIRA`, `CAIXA`) **não** é abreviado: fica como o lojista escreveu.
- **Sugestão de fator pela própria nota**: `qTrib ÷ qCom` inteiro vira
  `fator_sugerido` também quando as unidades são iguais (ex.: 50 UN = 600 UN) e
  nunca quando há peso/volume (KG, G, LT, ML).
- **Validação só do campo editável**: campo travado pela própria tela (ex.:
  *Entra* e *Custo R$* com caixa+unidade ligada) não reprova mais a importação
  inteira. A mensagem diz o item, o campo e o valor recusado.
- **Resumo em destaque** por item: o que a nota traz, o que entra no estoque,
  quanto custa cada unidade e como o produto vai aparecer no caixa.
- **Manual** (`docs/MANUAL.md`, `docs/ESTOQUE_E_XML.md` e a tela **Manual**)
  reescrito com os três caminhos e a conferência pelo preço da nota.

## Provas

- `pytest backend/tests/test_embalagem_clara.py` — 8 testes novos: UN1 → UN,
  sinais de embalagem, nota em peso sem sugestão, mesma unidade com contagem
  maior, modo unidade com nota em caixa e em unidades soltas, e exigência dos
  dois preços no modo embalagem.
- Suíte backend completa e `tsc --noEmit` — resultado na ficha de entrega.
