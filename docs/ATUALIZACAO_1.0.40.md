# Atualização 1.0.40 — venda com item "bom" e item "ruim" não perde mais a NFC-e

Álvaro, 25/11/2026. Pedido: *"Se tiver produtos bons e ruins na mesma nota, o dos bons deve sair
normalmente — estruture algo e deixe funcionando e documentado no main do GitHub."*

## O problema, em uma frase

A NFC-e é **uma nota por venda**. A SEFAZ valida **cada item** e rejeita a nota inteira quando um
item está fora da regra — então um único produto com cadastro fiscal errado derrubava a nota dos
itens bons daquela venda. Não existe "emitir só os itens bons": cortar item da nota é emitir
documento com valor menor que a venda.

A saída correta é **não deixar o cadastro derrubar a nota**: o que é derivável, o sistema deriva;
o que não é (NCM), o sistema lista e sugere.

## O que mudou

### 1. CFOP da NFC-e derivado do CSOSN (na emissão)

A SEFAZ-MT valida o par **CSOSN × CFOP** pela NT 2023.003 e rejeita com a **rejeição 725**
("NFC-e com CFOP inválido"). Para o Simples:

- CSOSN 500 (ICMS já recolhido por substituição tributária) → **5405**, com CEST obrigatório;
- demais CSOSN (101/102/103/104/300/400/900) → **5102**, preservando 5101/5103/5104/5115 quando o
  cadastro já usa um deles.

Agora o CFOP do XML é **calculado a partir do CSOSN** na hora de montar a nota
(`backend/fiscal_cadastro.py`), e não mais copiado do cadastro. Um produto importado com 5401,
5403 ou 5405 num CSOSN 102 emite normalmente como 5102 — **sem perder o item nem a venda**.

O lojista continua mandando na tributação pelo **CSOSN**; o CFOP deixou de ser uma fonte de erro.

### 2. Cadastro existente corrigido na atualização (com auditoria)

Na subida do app, `database._corrigir_cfop_nfce()` alinha o CFOP de todos os produtos ao CSOSN.
É idempotente (roda uma vez e não mexe mais) e grava o que mudou em
`dados/logs/correcao-cfop-AAAA-MM-DD.csv` (id, produto, CFOP antigo, CFOP novo) — o contador pode
revisar e reverter o que for de substituição tributária de verdade.

No catálogo do James (medido em 25/11): **257 produtos** corrigidos — 29 de `5401`, 25 de `5403` e
203 de `5405`, todos com CSOSN 102 e sem CEST.

### 3. Tela "Cadastro fiscal pendente" (o que a SEFAZ não deixa derivar)

NCM não se deriva: sem NCM a SEFAZ rejeita (rejeição 778) e não há substituto legal. A tela
**Fiscal** ganhou a seção **Cadastro fiscal pendente**, que:

- lista os produtos que impedem a emissão, **os mais vendidos primeiro** (vendas dos últimos 30 dias);
- mostra o que falta em cada um (`ncm`, `cst_csosn`, `cest`);
- sugere o **NCM de um produto irmão** do próprio catálogo — só quando não há ambiguidade (mesmo
  termo do nome e um único NCM entre os irmãos). "Papel alumínio" não herda o NCM de "papel
  higiênico", e "51 ICE" com NCMs divergentes não recebe sugestão;
- botão **Aplicar N sugestões** grava todas de uma vez e um campo por produto para o NCM informado
  à mão.

A sugestão é um atalho, **nunca aplicação silenciosa**: quem confirma é o lojista e o contador.

### 4. Rotas novas

- `GET /api/fiscal/cadastro/pendencias` — total, quantos têm sugestão e a lista priorizada.
- `POST /api/fiscal/cadastro/pendencias/corrigir` — aplica as sugestões e devolve o que sobrou.
- `PATCH /api/fiscal/cadastro/produtos/{id}` — grava NCM/CEST/CSOSN/CFOP de um produto.

## Números do catálogo do James (25/11/2026)

| | |
|---|---|
| Produtos ativos | 478 |
| Com CFOP de NF-e/ST em CSOSN 102 (corrigidos) | 257 |
| Sem NCM (pendentes) | 148 |
| Com sugestão segura de NCM | 49 |

Vendas concluídas de 19 a 25/11 (533):

| Situação | Vendas |
|---|---|
| Travadas por `5405` sem CEST / CSOSN ≠ 500 | 364 |
| Travadas por NCM ausente | 223 |
| Rejeitadas por `5401`/`5403` | 17 |
| **Emitíveis depois da correção de CFOP** | **310 (58%)** |
| Emitíveis com as 49 sugestões de NCM aplicadas | 370 (69%) |

As 163 restantes dependem de NCM informado (produtos sem irmão claro no catálogo).

## Testes

- `backend/tests/test_fiscal_cadastro.py` (7): derivação do CFOP por CSOSN, preservação das
  variações válidas, CSOSN 500 → 5405, pendências por campo, sugestão de NCM sem ambiguidade e
  **venda mista** — monta o XML de uma venda com um item `5102` e um item `5401` e confere que os
  dois saem com `<CFOP>5102</CFOP>`.
- Rodados no Linux e no Windows (Python 3.12): 7 passed.
- `npm run build` (Vite) sem erro de TypeScript; bundle novo gerado.

## Arquivos

- `backend/fiscal_cadastro.py` (novo) — regra do CFOP e análise das pendências.
- `backend/fiscal_cadastro_router.py` (novo) — rotas de pendências.
- `backend/database.py` — migração do CFOP com CSV de auditoria; `listar_produtos`,
  `vendas_por_produto`, `atualizar_fiscal_produto`.
- `backend/fiscal_direto.py` — CFOP efetivo no XML e na validação do CEST.
- `backend/fiscal.py` — CFOP efetivo no payload do gateway legado.
- `backend/main.py` — registro do router `/api/fiscal/cadastro`.
- `src/lib/api.ts` e `src/pages/Fiscal.tsx` — seção de pendências e chamadas.
- `backend/tests/test_fiscal_cadastro.py` (novo).

## Instalação

| Artefato | Bytes | SHA-256 |
|---|---|---|
| `dist_exe/VendaFacilPDV.exe` | 59.517.598 | `52B1DC9C5FCCF5E29A4B586861CA0B4A46339A9D9662124522C6E86416ED75C7` |
| `dist_installer/VendaFacilPDV-Setup-1.0.40.exe` | 59.364.951 | `B5E3A71E46707ECE92F93F536F382C03B580AAA2D1A5337A3F04D3378F4645BC` |

Setup `1.0.40` instalado sobre a 1.0.39 no caixa do James. Na primeira subida o app corrige o
cadastro (257 produtos) e grava o CSV; a seção de pendências aparece em **Fiscal**.

Resultado no caixa: `/health` 1.0.40, 2 processos, 1 janela kiosk, 257 CFOPs corrigidos e 49
sugestões de NCM aplicadas pela tela (148 → 99 pendentes). Vendas emitíveis de 19 a 25/11: 58% só
com a correção de CFOP e **71%** com as sugestões aplicadas.

🔴 **Ao instalar:** pare o `VendaFacilPDV` antes de rodar o setup. Com o app aberto o Inno Setup não
troca o `.exe` e deixa a troca agendada em `PendingFileRenameOperations` — a versão registrada sobe,
mas o processo antigo continua servindo (foi o que aconteceu na primeira tentativa).

🔴 **Ao buildar:** o executável é gerado com **Python 3.11** (`py -3.11 -m PyInstaller`), o único com
PyInstaller instalado. As dependências precisam estar nesse interpretador — faltava `qrcode` e o exe
subia morto com `ModuleNotFoundError: No module named 'qrcode'` (o `pix.py` importa na subida).
