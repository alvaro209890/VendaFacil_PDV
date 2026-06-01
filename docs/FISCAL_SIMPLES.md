# Fiscal no Simples Nacional

## Cadastro por produto

Cada produto pode ter sua própria classificação fiscal:

- `CSOSN 102`: tributação normal no Simples.
- `CSOSN 500`: ICMS já recolhido por Substituição Tributária.
- `CST PIS/COFINS 04`: monofásico.
- `CST PIS/COFINS 05`: substituição tributária.
- `CST PIS/COFINS 06`: alíquota zero.

Exemplos comuns precisam ser confirmados com o contador: bebidas frias, cigarros
e alguns produtos monofásicos podem exigir classificação diferente de arroz,
feijão e mercadorias tributadas normalmente.

## NFC-e / NF-e

Na emissão direta, o XML usa o grupo de ICMS correto para o CSOSN do produto.
Produtos com `CSOSN 500` saem em `ICMSSN500`, não em `ICMSSN102`.

PIS e COFINS também respeitam o CST do cadastro:

- `01` e `02`: grupo tributado por alíquota.
- `04`, `05`, `06`, `07`, `08` e `09`: grupo não tributado.
- demais códigos: grupo `Outr`.

## Relatório para PGDAS-D

A aba **Relatórios > Fiscal (Simples)** separa o faturamento do período em:

- receita com ICMS-ST;
- receita com PIS/COFINS monofásico, ST ou alíquota zero;
- receita tributada integral;
- detalhe por produto com NCM, CSOSN e CST PIS/COFINS.

Use esse relatório como apoio para o contador. A segregação depende do cadastro
fiscal atual dos produtos e não substitui a validação contábil.
