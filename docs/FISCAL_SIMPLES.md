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

## Regras da revisão de legislação (2026-07)

Detalhes e fundamentos em [`LEGISLACAO_FISCAL_MT.md`](LEGISLACAO_FISCAL_MT.md).
Resumo do que a emissão passou a exigir/fazer:

- **CRT**: o emissor atende **Simples Nacional (CRT 1)** e **MEI (CRT 4)**.
  CRT 2 (sublimite, usa CST comum) e CRT 3 (regime normal, que exigirá IBS/CBS
  a partir de 03/08/2026) são recusados com mensagem clara.
- **Reforma Tributária**: para o Simples/MEI os grupos IBS/CBS da NT 2025.002
  só passam a valer em **01/04/2027** — nada muda em 2026.
- **CEST obrigatório** em produto com ICMS-ST (CSOSN 500 / CFOP 5405) — ex.:
  bebidas frias e cigarros. Sem CEST a emissão é recusada localmente (evita a
  Rejeição 806 da SEFAZ). Cadastre o CEST na aba fiscal do produto.
- **NCM com 8 dígitos** (evita a Rejeição 778).
- **Formas de pagamento** na NFC-e: PIX estático (QR fixo da loja) = `tPag 20`;
  PIX pela Point = `tPag 17` com grupo `card`; fiado = `tPag 99` com descrição
  `xPag` e `indPag 1` (a prazo).
- **Lei 12.741/2012**: configure o "% tributos aprox. (IBPT)" em Configurações
  Fiscais (peça ao contador o percentual do CNAE) para o cupom informar o valor
  aproximado dos tributos (`vTotTrib`).
