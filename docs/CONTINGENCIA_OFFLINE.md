# Contingência offline + correções fiscais (NFC-e SEFAZ-MT)

Este documento descreve a **contingência offline da NFC-e** e o pacote de
**correções fiscais** aplicado à emissão direta SEFAZ-MT (`backend/fiscal_direto.py`).
Tudo isso vale para o fluxo padrão **SEFAZ-MT direto** (Simples Nacional).

> ⚠️ **Validação obrigatória em homologação.** As mudanças seguem o MOC da NF-e
> 4.00 e o "Manual de Padrões Técnicos do DANFE-NFC-e e QR Code" (QR Code 2.00),
> mas **a palavra final é da SEFAZ**. Rode o roteiro de
> [`TESTE_FISCAL_WINDOWS.md`](TESTE_FISCAL_WINDOWS.md) em **homologação** com o A1
> e o CSC reais antes de produção.

---

## 1. Contingência offline (tpEmis=9)

O PDV é **offline-first** — o caixa não pode parar quando a internet cai. Antes,
ao emitir NFC-e sem conexão, o número fiscal era **consumido e perdido** (a nota
não era gravada) e o operador via um erro. Agora:

1. Tenta a emissão **normal** (tpEmis=1) direto na SEFAZ-MT.
2. **Sem conexão** (erro de conexão/timeout de conexão) → a NFC-e é reemitida em
   **contingência offline (tpEmis=9)**: chave com `tpEmis=9`, grupos `dhCont` +
   `xJust`, assinada e com **QR Code offline** no formato oficial do QR 2.0
   (`chave|2|tpAmb|DIA|vNF|digValHex|idCSC|hash` — só o **dia** da emissão, sem
   vICMS; `digValHex` é o texto Base64 do `DigestValue` em hexadecimal). A nota
   é gravada com status **`contingencia`** e o **DANFE NFC-e é impresso na hora,
   em DUAS vias e com o QR Code** (via do consumidor + via do estabelecimento),
   com o texto "EMITIDA EM CONTINGÊNCIA — Pendente de autorização".
3. Quando a internet volta, o **loop em segundo plano** (`fiscal._loop`,
   a cada 45 s) **transmite** o XML já assinado e atualiza para `autorizada`.
4. **Enviou mas não obteve resposta** (ex.: timeout de leitura): a nota fica
   `processando` e o loop **consulta pela chave** (não retransmite, para não
   duplicar) — pode já estar autorizada na SEFAZ.

Pontos importantes:

- O **número fiscal nunca se perde**: é reservado uma vez e reaproveitado entre a
  tentativa online e a contingência (muda só o `tpEmis`, logo a chave/`cDV`).
- **Reemitir a venda não duplica a nota**: `contingencia` conta como nota viva
  na deduplicação de `emitir_nfce`/`emitir_nfe`.
- **Duplicidade no reenvio (cStat 539)**: se a transmissão anterior tinha
  chegado à SEFAZ, o loop **consulta pela chave** e grava a situação real (antes
  marcava `rejeitada` uma nota que na verdade estava autorizada).
- A venda **nunca quebra** por causa da nota (o checkout já trata erro de nota).
- **NF-e modelo 55** não usa contingência offline deste tipo: sem conexão ela
  fica `processando` para reenvio/consulta.
- Prazo legal: o DANFE de contingência é entregue ao consumidor na hora e a nota
  deve ser **transmitida em até 24 h** — o que o loop faz automaticamente assim
  que houver internet (autorização após o prazo volta cStat 150, também tratada
  como autorizada).

Arquivos: `montar_documento(tp_emis=...)`, `inserir_qrcode_offline()`,
`preparar_e_tentar_transmitir()` (em `fiscal_direto.py`), tratamento de
`contingencia`/`pendente` em `fiscal.emitir_nfce()` e transmissão no
`_processar_pendentes_direto()`.

---

## 2. Correções fiscais aplicadas

| # | O que era | O que ficou |
|---|-----------|-------------|
| 1 | **QR Code** misturava o layout antigo (v1.00: `cDest/dhEmi/vNF/vICMS/digVal`) dentro do wrapper `p=`, com `&` e `nVersao=100`. | **QR Code 2.00** correto: `p=chave\|2\|tpAmb\|idCSC\|hash` (online) e `chave\|2\|tpAmb\|DIA\|vNF\|digValHex\|idCSC\|hash` (offline — revisado em 2026-07: só o dia da emissão, sem vICMS, digVal = texto Base64 em hex, idCSC sem zeros). `hash = SHA-1(conteúdo + CSC)`. QR 3.0 (NT 2025.001) disponível como opção — ver [`LEGISLACAO_FISCAL_MT.md`](LEGISLACAO_FISCAL_MT.md). |
| 2 | **Assinatura** com C14N **exclusiva** (padrão do `signxml`). | C14N **não-exclusiva** (`REC-xml-c14n-20010315`) no `CanonicalizationMethod` e no `Transform` — exigência da NF-e (evita Rejeição 297). |
| 3 | **Desconto** ignorado: `vDesc=0` com `vNF=total` → total não fechava (Rejeição 528/610). | Desconto **rateado por item** (`prod/vDesc`) + `ICMSTot/vDesc`; `vNF = vProd − vDesc`. |
| 4 | Sem internet: número queimado, sem nota, com erro. | **Contingência offline** (seção 1). |
| 5 | `cNF` = `nNF` (código numérico = número da nota). | `cNF` **aleatório** de 8 dígitos, **diferente do `nNF`** (regra do MOC). |
| 6 | Em homologação o destinatário ia com nome real. | Em homologação o `xNome` do destinatário vai como **"NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"** (evita Rejeição 706). |
| 7 | Sem **Lei 12.741/2012** no XML direto. | `infAdic/infCpl` com o texto dos tributos aproximados (IBPT) + Simples Nacional. |
| 8 | Cupom dizia **"CUPOM NÃO FISCAL"** mesmo com nota. | Vira **DANFE NFC-e**: título correto, **consumidor**, chave, protocolo, QR, URL de consulta MT e Lei 12.741; rótulo de **contingência** quando aplicável. |

> Ainda **só Simples Nacional** (grupos `ICMSSN*`). Regime normal (CRT 3, com
> CST 00/10/20/40/60/90) não é coberto — é o público-alvo (mercearia no Simples).

---

## 3. Checklist de validação em homologação

Além de A–E de [`TESTE_FISCAL_WINDOWS.md`](TESTE_FISCAL_WINDOWS.md):

- [ ] **QR Code**: escanear o QR do DANFE e abrir a consulta no portal NFC-e MT.
- [ ] **Assinatura**: nota **autorizada** (cStat 100) — confirma que o C14N está aceito.
- [ ] **Desconto**: emitir venda **com desconto** e conferir `vProd`, `vDesc` e
      `vNF` fechando (sem Rejeição 528/610).
- [ ] **Contingência**: **desligar a internet**, vender com "Emitir nota" →
      o DANFE imprime "EMITIDA EM CONTINGENCIA OFFLINE" → **religar** → a nota
      vira `autorizada` sozinha em ~1 min.
- [ ] **cNF ≠ nNF**: abrir o XML e conferir que `cNF` não é igual ao `nNF`.

## 4. Pendências conhecidas (futuro)

- **Inutilização** de numeração (evento) para justificar quebras de sequência.
- **Reforma tributária (IBS/CBS)** — acompanhar a NT 2025.002 para a NFC-e
  (obrigatoriedade plena em 2027; 2026 é fase de transição).
- **Valor exato** dos tributos (Lei 12.741) via tabela IBPT por NCM (hoje só o texto).
- **Pagamento dividido** (mais de uma forma na mesma venda) no grupo `pag`.
