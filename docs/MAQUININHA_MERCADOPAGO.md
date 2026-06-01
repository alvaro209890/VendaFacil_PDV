# Maquininha Mercado Pago Point no VendaFacil PDV

Integracao para cobrar na maquininha fisica Mercado Pago Point usando a API
atual de **Orders**. O caixa dispara o valor no PDV, a Point busca a order na
nuvem do Mercado Pago, o cliente paga no aparelho e o PDV acompanha o status.

O PDV nao armazena dados de cartao. Ele guarda apenas o Access Token da conta da
loja e o `device_id` da Point.

## Pre-requisitos

1. A Point precisa estar ativada na mesma conta Mercado Pago do Access Token.
2. Use o **Access Token de producao** da loja em:
   <https://www.mercadopago.com.br/developers> -> Suas integracoes -> aplicacao
   -> Credenciais de producao.
3. A Point precisa estar com internet e em modo **PDV**.

O sistema tenta colocar a terminal em modo PDV automaticamente antes de criar a
cobranca, usando `PATCH /terminals/v1/setup`. Mesmo assim, quando a Point nao
puxa a order, reinicie a maquininha e confirme no aparelho se ela saiu do modo
manual/standalone.

## API usada

Desde a versao 1.0.10, o VendaFacil usa:

- `GET /terminals/v1/list` para listar maquininhas e conferir `operating_mode`.
- `PATCH /terminals/v1/setup` para colocar o terminal em modo `PDV`.
- `POST /v1/orders` para criar a cobranca.
- `GET /v1/orders/{id}` para consultar o status.
- `POST /v1/orders/{id}/cancel` para cancelar.

A API antiga de `payment-intents` foi substituida. No teste real ela criava
intencao com `payment_mode: card` mesmo quando o PDV tentava PIX, deixando a
tela presa em "Enviando para a maquininha...".

Desde a versao 1.0.11, o PDV tambem:

- usa `print_on_terminal: "no_ticket"` para manter o payload igual ao exemplo
  minimo oficial durante o diagnostico;
- cancela automaticamente a order se ela ficar 45 segundos em `created`;
- mostra uma mensagem clara quando a nuvem do Mercado Pago cria a order, mas a
  Point nao puxa para a tela;
- registra no log o corpo sanitizado de erros Mercado Pago `400`, `409`, `412`
  e `5xx`;
- traduz `409` para: existe uma cobranca pendente na Point.

Referencia oficial: <https://www.mercadopago.com.br/developers/pt/docs/mp-point/migrate-payment-intent-to-orders>

## Configuracao no PDV

Tela **Maquininha**:

| Campo | O que preencher |
|---|---|
| Cobrança por maquininha habilitada | Ligado |
| Access Token | Token de producao da conta Mercado Pago da loja |
| Device ID | ID da Point encontrada na busca |
| POS ID / Store ID | Opcionais |
| Imprimir comprovante | Mantido por compatibilidade; no diagnostico atual o backend envia `no_ticket` |

Depois de salvar o token, clique em **Buscar maquininhas da conta** e selecione
a Point correta. O `device_id` tem formato parecido com:

```text
NEWLAND_N950__N950NCC904676430
PAX_A910__SMARTPOS1493550868
```

## Formas de pagamento

O PDV envia para `config.payment_method.default_type`:

| Forma no PDV | Valor enviado |
|---|---|
| PIX | `qr` |
| Debito | `debit_card` |
| Credito | `credit_card` |

O valor e enviado em reais como string decimal, por exemplo `"4.93"`.

## Estados

O backend traduz os estados da Orders API para o formato que o PDV ja usa:

| Orders API | PDV |
|---|---|
| `created` | `OPEN` |
| `at_terminal` / `on_terminal` | `ON_TERMINAL` |
| `processing` | `PROCESSING` |
| `processed` / pagamento aprovado | `FINISHED` |
| `expired` / `canceled` | `CANCELED` |
| `failed` | `ERROR` |

Considere pago somente quando o backend devolver:

```json
{
  "pago": true,
  "payment_status": "approved"
}
```

## Diagnostico rapido

Se a tela ficar presa em **Enviando para a maquininha...**:

1. Abra **Maquininha** e clique em **Buscar maquininhas da conta**.
2. Confirme se a Point fisica em uso e a mesma selecionada no `Device ID`.
3. Reinicie a Point.
4. Confirme se a Point esta em modo **PDV** e conectada a internet.
5. Gere uma cobranca pequena de teste.
6. Se a order ficar `created` ate expirar, a nuvem do Mercado Pago aceitou a
   cobranca, mas a Point nao puxou a order.

Com a versao nova instalada, os erros tambem ficam em:

```text
%LOCALAPPDATA%\VendaFacilPDV\dados\logs\vendafacil.log
```

Dados sensiveis como Access Token, CSC, senha e certificado sao mascarados.

## Endpoint interno de diagnostico

Use `GET /api/maquininha/diagnostico` com o token do PDV para ver, sem criar
cobranca:

- terminal configurado;
- `operating_mode` atual;
- ultimas orders encontradas no log;
- status bruto da ultima order.

Esse endpoint existe para suporte tecnico. Ele nao altera a conta Mercado Pago.
