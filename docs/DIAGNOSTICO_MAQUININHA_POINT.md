# Diagnostico da Point neste PC

Data: 2026-06-01

Contexto: o PDV instalado ficava em **"Enviando para a maquininha..."** ao tentar
cobrar R$ 4,93 via PIX na Point.

## O que foi encontrado

- O sistema instalado estava rodando em `http://127.0.0.1:3020`.
- Havia duas instancias de `VendaFacilPDV.exe` abertas. Apenas uma estava
  escutando a porta 3020.
- O banco local ativo estava em:

```text
%LOCALAPPDATA%\VendaFacilPDV\dados\vendafacil.db
```

- A configuracao da maquininha estava habilitada.
- O Access Token salvo era valido.
- A conta Mercado Pago retornou duas Points:

```text
PAX_A910__SMARTPOS1493550868
NEWLAND_N950__N950NCC904676430
```

- A Point configurada no PDV era:

```text
NEWLAND_N950__N950NCC904676430
```

## Problema principal

A versao instalada usava a API antiga de `payment-intents`:

```text
POST /point/integration-api/devices/{device_id}/payment-intents
```

No teste real, uma cobranca PIX de R$ 4,93 criou a intencao, mas a resposta do
Mercado Pago veio como:

```text
payment_mode: card
state: OPEN
```

Ou seja: a cobranca foi aceita na nuvem, mas nao estava usando PIX de verdade
para a Point e nao saiu do estado `OPEN`.

## Modo da terminal

As Points apareceram inicialmente como `STANDALONE`. Foi enviado:

```text
PATCH /terminals/v1/setup
operating_mode: PDV
```

A API nova confirmou a NEWLAND em modo `PDV`:

```text
NEWLAND_N950__N950NCC904676430 -> PDV
PAX_A910__SMARTPOS1493550868 -> STANDALONE
```

## Teste com Orders API

Foi criada uma order PIX de R$ 4,93 com expiração curta de 30 segundos:

```text
POST /v1/orders
type: point
terminal_id: NEWLAND_N950__N950NCC904676430
default_type: qr
```

Resultado:

```text
status: created
payment status: created
depois: expired
```

Interpretacao: a nuvem do Mercado Pago criou a order corretamente, mas a Point
fisica nao puxou a cobranca antes de expirar.

## Teste definitivo com payload minimo oficial

Depois da versao 1.0.11, foi executado um teste direto na API do Mercado Pago
com o payload minimo para cartao:

```text
POST /v1/orders
type: point
terminal_id: NEWLAND_N950__N950NCC904676430
default_type: credit_card
print_on_terminal: no_ticket
amount: 4.93
expiration_time: PT30S
```

Antes do teste, qualquer order `created` conhecida no log foi cancelada e a
terminal foi colocada novamente em modo `PDV`.

Resultado bruto:

```text
setup_pdv: 200
terminal_atual: NEWLAND_N950__N950NCC904676430 -> PDV
create: 201
order: ORD01KT2161R2XRPDBYWQ3YJCDAMM
payment: PAY01KT2161RGFZJ1ES8SDE45VH8D
status inicial: created
poll 2s ate 22s: created
poll 24s: expired
```

Conclusao: mesmo com o payload minimo oficial, token valido, device correto e
terminal em modo `PDV`, a Point nao puxou a order. O problema esta no trecho
Mercado Pago -> terminal fisica/provisionamento, nao no PDV.

## O que foi alterado no sistema

- Backend migrado para Orders API.
- Antes de cobrar, o backend tenta colocar a terminal em modo `PDV`.
- Credito envia `credit_card`.
- Debito envia `debit_card`.
- Desde a versao 1.0.12, PIX nao e enviado para a Point; fica no fluxo proprio
  de QR Code do PDV.
- A listagem de dispositivos usa `GET /terminals/v1/list`, que mostra o modo
  real da terminal.
- Na versao 1.0.11, o backend envia `print_on_terminal: no_ticket` no payload da
  order para igualar o exemplo minimo oficial.
- Na versao 1.0.11, o frontend cancela automaticamente a order se ela ficar 45
  segundos em `created` e mostra mensagem orientando reiniciar/atualizar a
  Point.
- Na versao 1.0.11, erros Mercado Pago `400`, `409`, `412` e `5xx` sao logados
  com corpo sanitizado.
- Na versao 1.0.11, `409` ganhou mensagem clara de cobranca pendente.
- Foi adicionado `GET /api/maquininha/diagnostico` para suporte tecnico.
- Logs novos ficam em:

```text
%LOCALAPPDATA%\VendaFacilPDV\dados\logs\vendafacil.log
```

## Banco fiscal

A pedido, a configuracao fiscal do banco instalado foi limpa/desabilitada para
testar somente a maquininha.

Backup criado antes da limpeza:

```text
%LOCALAPPDATA%\VendaFacilPDV\dados\backups\vendafacil-pre-limpa-fiscal-20260601-130244.db
```

## Proximo teste fisico

1. Instalar a versao nova.
2. Fechar qualquer `VendaFacilPDV.exe` duplicado.
3. Reiniciar a Point NEWLAND.
4. Abrir o PDV.
5. Ir em **Maquininha** e buscar as maquininhas da conta.
6. Selecionar a NEWLAND e salvar.
7. Testar PIX pequeno.

Se a order continuar `created` ate expirar, o problema ja nao esta no PDV. Isso
ja foi reproduzido com o payload minimo oficial: o Mercado Pago aceitou a order,
mas a terminal fisica nao buscou a cobranca.
