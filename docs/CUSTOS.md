# 💰 Custos do sistema & controle financeiro

Quanto **você** (dono do SaaS) paga para manter o VendaFácil no ar, e a conta
de quanto sobra cobrando **R$ 180/loja/mês**. Os valores aqui são **referências
de mercado** — ajuste no painel (tela **💰 Financeiro**), que tem os números de
verdade e calcula receita/lucro automaticamente.

> ⚠️ Preços de terceiros mudam e variam com o dólar. Trate como estimativa e
> confirme no provedor. Em planos gratuitos, o custo é **R$ 0**.

## 📌 Situação atual (custo hoje ≈ R$ 0)

- **Render**: plano **gratuito** → R$ 0.
- **Supabase**: plano **gratuito** → R$ 0.
- **Vercel**: plano **gratuito** → R$ 0.
- **Domínio**: **não comprado por enquanto** (usando `.onrender.com`/`.vercel.app`).
- **NFC-e (Focus NFe)**: **adiado** — ainda precisa ser pago e vinculado; não
  está no custo. (No PDV a NFC-e já é opcional; ninguém é obrigado a usar.)
- **Code signing**: ainda não comprado.

Por isso os custos vêm **zerados** no painel. Conforme você for assinando algo
(plano pago, domínio, NFC-e), adicione/edite na tela **💰 Financeiro**.

## O que você paga (custos do SaaS)

| Serviço | Para quê | Plano free | Plano produção (estimado) |
|---|---|---|---|
| **Render** | hospeda a API do painel | R$ 0 (dorme) | ~US$ 7/mês (~R$ 38) sempre on |
| **Supabase** | banco de dados | R$ 0 (limites) | Pro ~US$ 25/mês (~R$ 135) |
| **Vercel** | painel admin (UI) | R$ 0 (Hobby) | Pro ~US$ 20/mês se uso comercial |
| **Domínio .com.br** | seu endereço | — | ~R$ 40/ano (~R$ 4/mês) |
| **Certificado Code Signing** | assinar o .exe | — | ~US$ 100–300/ano (~R$ 60/mês rateado) |
| **Focus NFe** | emitir NFC-e (por loja) | sandbox grátis | ~R$ 20–50/mês por loja (volume) |

> **Importante — o que NÃO é seu custo:**
> - **Certificado digital A1 (e-CNPJ)** da NFC-e → cada **varejista** paga (~R$120–250/ano).
> - **Taxas da maquininha/cartão (Mercado Pago)** → saem das vendas do **varejista**, não suas.

## A conta cobrando R$ 180/loja/mês

Usando as referências acima num cenário de produção:
- **Custo fixo** (independe do nº de lojas): Render + Supabase + Vercel + domínio +
  code signing ≈ **R$ 240/mês** (ou bem menos no free).
- **Custo por loja** (variável): Focus NFe ≈ **R$ 30/loja** (só se a loja usa NFC-e).
- **Margem por loja** = 180 − 30 = **R$ 150**.
- **Break-even** ≈ custo fixo ÷ margem = 240 ÷ 150 ≈ **2 lojas** já pagam a operação.

Exemplo com **10 lojas**:
- Receita: 10 × 180 = **R$ 1.800**
- Custo: 240 (fixo) + 10 × 30 = **R$ 540**
- **Lucro: R$ 1.260/mês**

> No começo, rodando tudo em **free** (custo fixo ≈ R$ 0) e sem NFC-e, quase tudo
> dos R$ 180 é lucro — mas o free não é recomendado para produção séria (Render
> dorme, Supabase tem limites). Suba para os pagos quando tiver clientes.

## Onde controlar no painel

Painel admin → botão **💰 Financeiro**. Lá você:
- Define o **preço por loja** (padrão R$ 180).
- Cadastra/edita os **custos** (fixos e por loja), ligando/desligando cada um.
- Vê em tempo real: **lojas ativas, receita, custo, lucro, margem por loja e o
  break-even** (quantas lojas pagam a operação).

Os custos vêm pré-preenchidos com as referências desta tabela — edite para a sua
realidade (ex.: zere o que estiver no plano gratuito).
