# Integrar Stone (e outras maquininhas) — análise e estimativa

> Como o VendaFácil poderia aceitar a **Stone** hoje, além do Mercado Pago Point,
> mantendo o **vínculo fiscal do pagamento** (NFC-e em MT). Inclui esforço e
> estimativa de valor. **Números são estimativas de mercado — confirmar.**

## Contexto

O Mercado Pago Point integra por **API REST na nuvem** (Orders API) — foi por isso
que saiu rápido. A **Stone não expõe** a maquininha física do mesmo jeito para um
PDV de desktop. Para integrar maquininha no varejo brasileiro, o caminho padrão é
**TEF**.

## Caminhos possíveis

### 1. TEF (recomendado) — CliSiTef ou PayGo Integrado
Um **agente TEF** roda na máquina (Windows) e conversa com o **pinpad/maquininha**.
O PDV chama o TEF, que devolve **bandeira, código de autorização (cAut) e CNPJ da
credenciadora** — exatamente o que a NFC-e precisa.

- **CliSiTef** (Software Express) ou **PayGo Integrado** (Setis): são
  **multi-adquirente** — funcionam com **Stone, Cielo, Rede, GetNet, etc.** com o
  mesmo código. Resolve Stone **e** dá flexibilidade futura.
- ✔️ Encaixa direto no que já construímos: o modelo `PagamentoEletronico` e o
  grupo `<card>` (tpIntegra/CNPJ/tBand/cAut) já existem — é só **alimentar** com o
  retorno do TEF em vez do Mercado Pago.

### 2. Stone via API/SDK próprio
- **Stone Connect / app no terminal Android** da Stone: o PDV teria que rodar
  **no terminal** (ou conversar com um app nele). Muda o modelo de implantação do
  VendaFácil (hoje é `.exe` no PC). Mais invasivo.
- **API de pagamentos online da Stone**: é para **e-commerce/link de pagamento**,
  não para a maquininha presencial do balcão. Não serve para o PDV físico.

### 3. Stone como "maquininha manual" (sem integração) — já funciona hoje
O lojista passa o cartão na Stone e registra a venda como **cartão manual** no
VendaFácil. Funciona **agora, sem desenvolvimento**, mas a NFC-e sai como
**`tpIntegra=2` (não integrado)** — **não atende** a exigência de MT para cartão.

## Recomendação

**TEF multi-adquirente (CliSiTef ou PayGo).** Resolve Stone, é o padrão do mercado,
roda no Windows e devolve os dados do vínculo fiscal. Como nossa arquitetura de
pagamento já é genérica, o esforço fica concentrado em **falar com o TEF**.

## O que muda no nosso código (pequeno)

1. **Novo módulo** `backend/tef.py`: inicia a transação no agente TEF, faz o
   *pinpad flow* (aprovação/desfazimento) e normaliza o retorno.
2. Reaproveitar o que já existe:
   - gravar o retorno em `vendas.pagamento_detalhe` (mesmo `PagamentoEletronico`);
   - `fiscal_direto._grupo_pagamento` **já monta** o `<card>` — zero mudança fiscal.
3. **Config**: provedor de pagamento (`mercadopago` | `tef`) e parâmetros do TEF.
4. **Frontend**: na finalização, rotear cartão para o fluxo TEF; tratar
   confirmação/desfazimento (TEF exige confirmar a venda após autorizar).
5. **Homologação** com o provedor TEF + adquirente (etapa obrigatória deles).

> O grosso do trabalho é o **fluxo TEF** (confirmação/desfazimento, timeouts,
> reimpressão, cancelamento) e a **homologação** — não a parte fiscal, que já está pronta.

## Esforço estimado (desenvolvimento)

| Item | Estimativa |
|------|-----------|
| Módulo TEF + fluxo de transação (aprovação, confirmação, desfazimento) | 40–70 h |
| Integração no PDV (rota cartão, telas de status, cancelamento) | 20–30 h |
| Config + provedor selecionável + testes automatizados | 10–20 h |
| Homologação com o provedor TEF/adquirente | 15–30 h |
| **Total** | **~85–150 h** (≈ **3–5 semanas** de 1 dev) |

## Custos recorrentes (não são seus — são do lojista/operação)

- **Licença do TEF** (CliSiTef/PayGo): tipicamente **mensalidade por PDV**
  (faixa comum **R$ 30–80/PDV/mês**, varia por contrato/volume). *Confirmar.*
- **Pinpad/maquininha** compatível com TEF (a Stone fornece o aparelho).
- Taxas de adquirência (MDR) da Stone — já são do contrato do lojista.

## Quanto cobrar (estimativa)

Premissas: dev sênior freel/PJ no Brasil, **R$ 90–160/h**.

- **Projeto fechado (escopo TEF acima)**: **~R$ 12.000 a R$ 28.000**, conforme a
  hora e quanto da homologação entra no escopo. Um **MVP** (só crédito/débito
  Stone via TEF, sem PIX/cancelamento avançado) cai para **~R$ 8.000–12.000**.
- **Alternativa por assinatura** (se virar produto): embutir como
  **"módulo maquininha integrada"** no plano do lojista — ex.: **+R$ 20–40/mês**
  por loja que usar TEF, para cobrir licença do TEF + suporte + amortizar o dev.

> ⚠️ Valores de mercado **mudam** e dependem de contrato (TEF/adquirente),
> volume e região. Use como ponto de partida e cote o TEF (Software Express /
> Setis) e a Stone antes de fechar preço.

## Resumo

- **Hoje, sem dev:** Stone só como **cartão manual** → NFC-e **não integrada**
  (não conforme em MT para cartão).
- **Caminho certo:** **TEF multi-adquirente** — resolve Stone + outras, reaproveita
  todo o vínculo fiscal já implementado, **~3–5 semanas** de dev,
  **~R$ 8k–28k** dependendo do escopo, + **licença TEF mensal** por PDV.
