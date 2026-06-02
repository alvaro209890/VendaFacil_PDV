# Vínculo do pagamento eletrônico na NFC-e (Mato Grosso)

> Em Mato Grosso, a NFC-e/NF-e de **cartão ou PIX** precisa carregar os dados da
> transação de pagamento **dentro do XML** — é o "vínculo do pagamento
> eletrônico". Base legal: **Decreto 599/2023** e **Portaria SEFAZ 262/2023**
> (alterada pela 43/2025).

## Quem é obrigado

A obrigatoriedade é por CNAE, em fases. **Mercearia / minimercado / armazém
(CNAE 4712-1)** e **super/hipermercado (4711-3)** estão no **Anexo II — obrigados
desde 01/07/2024**.

**Dispensados** (não precisam do vínculo, mesmo no CNAE):
- **MEI** optante (LC 123/2006);
- regime especial **NFF** (Nota Fiscal Fácil);
- vendas não presenciais por plataforma de terceiros;
- entrega com pagamento em domicílio.

> Venda em **dinheiro** não tem pagamento eletrônico a vincular — sai normal.

## O que o sistema faz agora

Quando a venda é cobrada pela **maquininha Mercado Pago Point** (cartão de
crédito/débito) e há emissão de NFC-e, o VendaFácil:

1. ao aprovar a cobrança, lê da Order do Mercado Pago a **bandeira** e o **código
   de autorização (cAut)** — consultando a Payments API quando necessário;
2. junta o **CNPJ da credenciadora** configurado (ver abaixo);
3. grava esse vínculo na venda (`pagamento_detalhe`);
4. na emissão, monta o grupo `<card>` do XML:

```xml
<detPag>
  <tPag>03</tPag>          <!-- 03 crédito | 04 débito | 17 PIX -->
  <vPag>10.00</vPag>
  <card>
    <tpIntegra>1</tpIntegra>   <!-- 1 = integrado ao PDV -->
    <CNPJ>10573521000191</CNPJ> <!-- credenciadora (Mercado Pago) -->
    <tBand>02</tBand>           <!-- bandeira (02 = Master) -->
    <cAut>654321</cAut>         <!-- autorização da transação -->
  </card>
</detPag>
```

### Regra de segurança (evita rejeição)

- **`tpIntegra=1`** só é emitido quando há **CNPJ da credenciadora E cAut**. O
  layout exige os dois nesse caso — sem eles a SEFAZ rejeita (**rejeição 392**).
- Faltando algum dado (ex.: **cartão manual**, ou a Point não retornou a
  autorização), o sistema declara **`tpIntegra=2` (não integrado)** — XML válido,
  mas **não atende** a exigência de MT. Nesses casos, prefira **dinheiro** para a
  NFC-e ou complete a integração.

## Configuração (uma vez)

Tela **Maquininha → Vínculo fiscal do pagamento**:

- **CNPJ da credenciadora (Mercado Pago)**: informe o CNPJ da credenciadora dos
  recebíveis. **Confirme com seu contador** ou na sua fatura/extrato de
  recebíveis do Mercado Pago. Sem esse CNPJ, as notas de cartão saem como
  **não integrado** (`tpIntegra=2`).

Bandeira e autorização são preenchidas **automaticamente** pela maquininha.

## PIX

- **PIX pela Point (integrado)**: ligue **Maquininha → "Cobrar PIX pela
  maquininha"**. O PIX é cobrado na telinha da Point e o sistema usa o
  **endToEndId** como `cAut` no grupo `<card>` (`tpIntegra=1`). Depende de a
  Point suportar PIX — **valide em homologação**.
- **PIX via QR estático no PDV** (sem maquininha, chave configurada em PIX): não
  é transação integrada → sai como `tpIntegra=2`.

## Limitações conhecidas

- O caminho legado **Focus NFe** não monta o grupo `<card>` (use o emissor
  **SEFAZ-MT direto**, que é o padrão).
- O **CNPJ da credenciadora** é configurado uma vez (não vem da API do Mercado
  Pago); confirme o número correto com o contador / fatura de recebíveis.

> Não substitui orientação contábil. Confirme CNAE, regime e o CNPJ da
> credenciadora com o contador da loja.
