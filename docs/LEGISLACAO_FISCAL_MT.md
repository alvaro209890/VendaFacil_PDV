# Legislação fiscal MT aplicada ao PDV — revisão 2026-11-12

Este documento registra a **revisão de conformidade com a legislação de Mato
Grosso** (e as normas nacionais da NFC-e/NF-e) feita em julho/2026, os **bugs
corrigidos** com base nela e o fundamento legal de cada decisão. Vale para o
fluxo padrão **SEFAZ-MT direto** (`backend/fiscal_direto.py` + `backend/fiscal.py`).

> ⚠️ Como sempre: a palavra final é da SEFAZ. Antes de usar em produção, rode o
> roteiro de [`TESTE_FISCAL_WINDOWS.md`](TESTE_FISCAL_WINDOWS.md) em
> **homologação** com o A1/CSC reais da loja.

---

## 1. Endereços dos webservices SEFAZ-MT (bug crítico corrigido)

Os endpoints usados até então **não existiam** no autorizador de MT (o caminho é
case-sensitive e alguns nomes eram outros). Nenhuma transmissão real teria
funcionado — a SEFAZ devolveria 404 e a nota ficava "rejeitada" sem motivo real.

Endereços corretos (cadastro nacional de webservices por UF, autorizador MT):

| Serviço | NFC-e (65) produção | NF-e (55) produção |
| --- | --- | --- |
| Autorização | `https://nfce.sefaz.mt.gov.br/nfcews/services/NfeAutorizacao4` | `https://nfe.sefaz.mt.gov.br/nfews/v2/services/NfeAutorizacao4` |
| Consulta protocolo | `https://nfce.sefaz.mt.gov.br/nfcews/services/NfeConsulta4` | `https://nfe.sefaz.mt.gov.br/nfews/v2/services/NfeConsulta4` |
| Eventos (cancelamento) | `https://nfce.sefaz.mt.gov.br/nfcews/services/RecepcaoEvento4` | `https://nfe.sefaz.mt.gov.br/nfews/v2/services/RecepcaoEvento4` |

(Homologação: mesmos caminhos em `homologacao.sefaz.mt.gov.br`.)

Erros que existiam: `NFeAutorizacao4` (maiúscula errada), `NFeConsultaProtocolo4`
e `NFeRecepcaoEvento4` (nomes que MT não usa nos caminhos).

## 2. Envelope SOAP (bug crítico corrigido)

O elemento `<nfeDadosMsg>` ia com o namespace do **leiaute** da NF-e
(`http://www.portalfiscal.inf.br/nfe`), mas o padrão de comunicação exige o
namespace do **WSDL da operação** (`http://www.portalfiscal.inf.br/nfe/wsdl/
NFeAutorizacao4`, `.../NFeConsultaProtocolo4`, `.../NFeRecepcaoEvento4`), com o
`action="<namespace>/<método>"` no Content-Type do SOAP 1.2. Sem isso o servidor
não roteia a operação. Corrigido em `montar_soap()`/`_post_soap()`; o conteúdo
interno (`enviNFe`, `consSitNFe`, `envEvento`) continua no namespace do leiaute.

## 3. QR Code da NFC-e (bug crítico corrigido + QR 3.0)

Base: *Manual de Especificações Técnicas do DANFE NFC-e e QR Code* e, para o QR
3.0, a **NT 2025.001** (em produção desde 09/2025; adoção opcional para PJ,
obrigatória só para produtor rural PF — o 2.0 segue aceito, inclusive em MT).

- **URL de consulta oficial de MT** (a SEFAZ valida o conteúdo do
  qrCode/urlChave contra o cadastro — Rejeição 591): produção
  `http://www.sefaz.mt.gov.br/nfce/consultanfce` e homologação
  `http://homologacao.sefaz.mt.gov.br/nfce/consultanfce`. Antes o código usava
  `https` e produção sem `www` — divergente do cadastro.
- **idCSC sem zeros à esquerda** no parâmetro do QR (antes ia `000001`).
- **QR 2.0 offline no formato certo**: `chave|2|tpAmb|DIA|vNF|digValHex|idCSC|hash`,
  onde `DIA` é só o dia da emissão (2 dígitos) e `digValHex` é o **texto Base64**
  do DigestValue convertido a hexadecimal. O formato anterior misturava campos
  do QR 1.0 (dhEmi completo em hex + vICMS + bytes decodificados) — toda NFC-e
  de contingência seria rejeitada na transmissão e o QR não validaria no app.
- **QR 3.0 opcional** (`Configurações Fiscais → Versão do QR Code`): online
  `chave|3|tpAmb` (dispensa CSC); offline
  `chave|3|tpAmb|DIA|vNF|tpIdDest|cDest|assinatura`, com assinatura RSA-SHA1 do
  conteúdo feita com o próprio A1 (Base64). Padrão continua **2.0** (é o aceito
  em produção na SEFAZ-MT).

## 4. Prazo de cancelamento em MT (novo bloqueio com orientação)

- **NFC-e: até 30 minutos** após a autorização — Ajuste SINIEF 07/18, vigente na
  SEFAZ-MT desde 03/06/2019.
- **NF-e: até 2 horas** em MT.
- Fora do prazo o sistema agora **explica o caminho**: pedido de cancelamento
  extemporâneo no portal da SEFAZ-MT (até o 5º dia útil do mês seguinte —
  Portarias 160/2021 e 177/2021) ou cancelamento por substituição (168h, evento
  110112, não suportado pelo PDV). Antes o PDV mandava o evento mesmo assim e o
  usuário recebia só o cStat 501 seco da SEFAZ. Tolerância de 5 min para
  diferença de relógio.

## 5. Contingência offline (bugs corrigidos)

Padrões Técnicos de Contingência Offline da NFC-e (ENCAT):

- **Reemitir a venda não duplica mais a nota**: uma nota com status
  `contingencia` agora conta como "nota viva" na deduplicação (antes um clique
  em "emitir" de novo gerava um **segundo documento fiscal** para a mesma venda,
  e a nota offline ainda seria transmitida pelo loop → duas notas autorizadas).
- **QR no cupom de contingência**: o `qrcode_base64` agora é gerado também para
  notas `contingencia` — o DANFE offline **tem** que sair impresso com o QR (era
  impresso sem).
- **Duas vias**: o cupom de contingência sai em 2 vias ("via do consumidor" e
  "via do estabelecimento — guardar"), como mandam os padrões técnicos, com o
  texto "EMITIDA EM CONTINGÊNCIA — Pendente de autorização".
- Transmitir assim que a falha cessar; em MT, limite até o primeiro dia útil
  seguinte à emissão (Portaria177/2021 art.18 §1 II). O loop tenta a cada45s
  enquanto o programa estiver aberto; isso não garante autorização no prazo.
- **cStat 204** mantém a nota pendente até a consulta pela chave. **cStat 539**
  indica conflito com outra chave. Se a consulta da chave local ficar inconclusiva,
  o PDV conserva o retorno original para o contador conferir no portal.
- Após timeout ou HTTP 5xx, a consulta precede nova transmissão. O retorno 217
  permite reenviar o mesmo XML assinado, salvo quando há conflito 539 registrado.

## 6. Formas de pagamento (IT 2024.002, produção desde 01/07/2024)

Tabela de Meios de Pagamento atualizada + regras do grupo `detPag`:

| Situação no PDV | Antes | Agora |
| --- | --- | --- |
| PIX pela maquininha Point (dinâmico, com endToEndId) | `tPag 17` + `card` | igual (correto) |
| PIX manual pelo QR fixo da loja (estático) | `tPag 17` (errado) | **`tPag 20`** |
| Fiado (caderneta/crediário) | `tPag 99` com descrição | **`tPag 05` + `indPag 1` (a prazo)** |
| Demais formas | sem `indPag` | `indPag 0` (à vista) |

`xPag` acompanha `tPag=99`. O IT 2024.002 inclui o crediário no código 05.
O grupo `card` inclui o CNPJ do beneficiário e o terminal quando disponíveis
no pagamento integrado. Consulte [`VINCULO_PAGAMENTO_MT.md`](VINCULO_PAGAMENTO_MT.md).

## 7. Limites da NFC-e em Mato Grosso

- NFC-e **a partir de R$ 200.000,00 é vedada**; emitir NF-e 55.
- Desde **R$ 1.000,00**, informar CPF/CNPJ do consumidor em MT. A validação usa
  o total após desconto, antes da transmissão.
- Base: [Portaria 177/2021-SEFAZ, arts.3 §4 II e 8 II a](https://app1.sefaz.mt.gov.br/Sistema/Legislacao/legislacaotribut.nsf/07fa81bed2760c6b84256710004d3940/14a777e454d23f9f0425874b006641f7),
  texto consolidado oficial consultado em 12/11/2026. O limite nacional de
  R$10 mil usado na revisão anterior não atendia à regra estadual.

## 8. Reforma Tributária (IBS/CBS — NT 2025.002) e CRT

- Em 2026, o escopo do emissor é Simples Nacional (CRT1) e MEI (CRT4).
  Não usar a data de abril/2027 da revisão anterior como calendário de migração:
  conferir NT2025.002 e NT2026.005 no [Portal Nacional, notas técnicas vigentes](https://www.nfe.fazenda.gov.br/portal/listaConteudo.aspx?AspxAutoDetectCookieSupport=1&tipoConteudo=04BIflQt1aY%3D)
  antes de operar em2027. O programa não monta IBS/CBS.
- **Regime normal (CRT 3): DF-e sem IBS/CBS será rejeitado a partir de
  03/08/2026** (regra UB12-10). O PDV **não** monta esses grupos, então agora
  valida o CRT e recusa 2 e 3 com mensagem explicando o motivo (CRT 2 usa CST
  comum; CRT 3 exigirá IBS/CBS). Antes, um CRT 3 configurado geraria XML
  inconsistente (CRT 3 + CSOSN) rejeitado pela SEFAZ sem explicação local.
- CRT 4 (MEI) é aceito — usa os mesmos grupos CSOSN.

## 9. Outras validações que evitam rejeição na SEFAZ (novas)

| Validação | Rejeição evitada |
| --- | --- |
| CNPJ do emitente com dígitos verificadores | 207/504 |
| CPF/CNPJ do consumidor com DV (antes de transmitir) | 237/207 |
| Código IBGE de município com 7 dígitos iniciando em 51 (MT) | 270/272 |
| NCM com 8 dígitos | 778 |
| **CEST obrigatório** quando CSOSN 500/CFOP 5405 (ICMS-ST — Conv. ICMS 92/15) | 806 |
| IE do destinatário só com `indIEDest=1` (e exigida nesse caso) | 490/695 |
| Venda nacional a não contribuinte em NF-e 55 informa `indFinal=1` | 696 |
| `idDest` derivado da UF do destinatário; interestadual exige CFOP 6xxx | 694 |
| Textos normalizados (sem espaços nas pontas, tamanhos máximos: xProd 120, xNome/xLgr/... 60) | 215/588 |
| AAMM da chave casando com o dhEmi (mesmo instante na virada de mês) | 615 |
| Justificativa de cancelamento 15–255 caracteres (normalizada) | 501 |

Além disso, **as validações rodam antes de reservar o número fiscal** — erro de
cadastro/config não queima mais numeração (buraco de numeração exigiria
inutilização junto à SEFAZ).

## 10. Lei 12.741/2012 (tributos no cupom)

O cupom citava a tabela IBPT mas não informava **valor**. Agora existe o campo
**"% tributos aprox. (IBPT)"** em Configurações Fiscais: preenchido (peça o
percentual do CNAE ao contador), o XML sai com `vTotTrib` por item e no total e
o `infCpl`/cupom mostram "Trib aprox R$ X (Y%) Fonte: IBPT". Com 0 (padrão), o
comportamento anterior é mantido.

## 11. Bugs gerais (não-legislação) corrigidos na mesma revisão

- **Checkout com falha no meio da baixa de estoque** (corrida entre caixas):
  agora devolve o estoque já baixado antes de retornar 409 — antes o estoque
  ficava menor sem venda criada.
- **Desconto maior que o subtotal** é recusado no checkout (400) — antes criava
  venda de total 0 e a NFC-e correspondente seria rejeitada.
- **Export de XML com só a data final** (`?fim=`) era ignorado — agora filtra.
- **Certificado A1 corrompido/senha errada** virava erro 500 genérico — agora é
  mensagem amigável ("Certificado A1 inválido ou senha incorreta").

## 12. O que NÃO foi alterado (e por quê)

- **QR Code 2.0 continua o padrão** — é o aceito em produção na SEFAZ-MT; o 3.0
  fica opcional até a SEFAZ-MT exigir.
- **Grupos IBS/CBS** não são montados; para2027 é necessária nova revisão normativa
  e atualização do emissor (item8).
- **infRespTec** segue opcional/desligado (MT não exige) — ver
  [`RESPONSAVEL_TECNICO.md`](RESPONSAVEL_TECNICO.md).
- **Cancelamento por substituição (evento110112)** permanece fora do emissor;
  tratar com o contador.

## 13. Serviços e homologação

- A tela Fiscal consulta a disponibilidade da SEFAZ-MT para NFC-e e NF-e.
  O retorno 107 informa operação do serviço. O credenciamento depende da loja.
- A inutilização usa pedido assinado e valida a faixa no SQLite antes do envio.
  A tela Fiscal preserva a faixa, a situação e o protocolo no histórico.
- Execute o [roteiro de homologação](TESTE_FISCAL_WINDOWS.md) com o cofre da
  loja. O precheck registra presença e validade dos requisitos locais.

## Fontes consultadas (2026-07-13)

- SEFAZ-MT — notícias oficiais de prazo de cancelamento (NF-e 2h; NFC-e 30 min):
  <https://www5.sefaz.mt.gov.br/-/prazo-para-cancelar-a-nf-e-continuara-de-ate-duas-horas-em-mato-grosso>
  e <https://www5.sefaz.mt.gov.br/en/-/11787178-sefaz-altera-regras-para-cancelamento-da-nota-fiscal-do-consumidor>
- Espião NFe — NFC-e MT 30 minutos (Ajuste SINIEF 07/18, vigência 03/06/2019):
  <https://espiaonfe.com.br/blog/nfc-e-mt-prazo-cancelamento-reduzido-para-ate-30-minutos>
- TOTVS — cancelamento extemporâneo MT (Portarias 160/2021 e 177/2021):
  <https://www.totvs.com/blog/fiscal-clientes/mt-cancelamento-extemporaneo-de-nf-e-e-nfc-e/>
- TecnoSpeed — NT 2025.001 (QR Code 3.0, resposta síncrona, prazos):
  <https://blog.tecnospeed.com.br/nota-tecnica-2025-001-nfc-e-qr-code/>
- Datacaixa — QR Code 3.00 (2.00 continua válido; obrigatório só p/ produtor rural PF):
  <https://www.datacaixa.com.br/versao-3-00-novo-leiaute-do-qr-code-da-nfc-e/>
- TecnoSpeed — NT 2025.002 (IBS/CBS; Simples/MEI em 01/04/2027):
  <https://blog.tecnospeed.com.br/nota-tecnica-reforma-tributaria-nfe-nfce/>
- MRS Advogados — NT 2025.002 v1.40 (rejeição de DF-e sem IBS/CBS a partir de 03/08/2026):
  <https://mrsadvogados.com/nota-tecnica-2025-002-v-1-40-df-e-sem-cbs-e-ibs-serao-rejeitados-a-partir-de-03-08-2026/>
- TecnoSpeed — IT 2024.002 (tabela de meios de pagamento: PIX 17/20, xPag c/ 99):
  <https://blog.tecnospeed.com.br/informe-tecnico-2024-002/>
- Focus NFe — tabela tPag de referência:
  <https://campos.focusnfe.com.br/nfe/FormaPagamentoXML.html>
- Padrões Técnicos de Contingência Offline NFC-e (ENCAT, portal nacional):
  <https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=fMhAfsQfE+M%3D>
- Cadastro de webservices por UF (mod. 55/65) do projeto sped-nfe (nfephp-org),
  usado em produção por milhares de emissores:
  <https://github.com/nfephp-org/sped-nfe/blob/master/storage/wsnfe_4.00_mod65.xml>
