# 💳 Maquininha Mercado Pago (Point) no VendaFácil PDV

Integração para cobrar **no cartão pela maquininha física** (crédito/débito)
direto do PDV. O caixa dispara o valor, a máquina Point acende e pede o cartão,
e o PDV acompanha o status até concluir. **Não armazenamos dados de cartão** —
falamos apenas com a API do Mercado Pago usando o *Access Token* da loja.

> A maquininha **exige internet** (pagamento em cartão é online por natureza).
> O resto do PDV continua funcionando offline; só a cobrança no cartão depende
> de conexão no momento da venda.

## Pré-requisitos (no Mercado Pago)

1. Ter uma maquininha **Point** (Point Smart, Point Pro etc.) ativada na conta.
2. Pegar o **Access Token** da loja: <https://www.mercadopago.com.br/developers>
   → *Suas integrações* → aplicação → **Credenciais de produção** → `Access Token`.
3. Pôr a maquininha em **modo PDV/Integração** pelo app/menu do dispositivo
   (necessário para receber cobranças via API).

## Como configurar no PDV

A configuração fica salva no banco local do PDV (`config_maquininha`). Use os
endpoints abaixo (a tela de Configurações do PDV consome estes mesmos).

| Campo                  | Descrição                                                        |
|------------------------|------------------------------------------------------------------|
| `habilitado`           | Liga/desliga a cobrança por maquininha.                          |
| `access_token`         | Access Token da conta Mercado Pago da loja (sensível).           |
| `device_id`            | Id do dispositivo Point (ex.: `PAX_A910__SMARTPOS...`).          |
| `store_id` / `pos_id`  | Opcionais (loja/caixa no Mercado Pago).                          |
| `imprimir_comprovante` | Se a maquininha imprime o comprovante ao final (`true`/`false`). |

Descubra o `device_id` chamando `GET /api/maquininha/dispositivos` depois de
salvar o `access_token` — ele lista as maquininhas pareadas à conta.

## API (base `/api/maquininha`, exige JWT do PDV)

| Método  | Rota                         | Função                                                |
|---------|------------------------------|-------------------------------------------------------|
| `GET`   | `/config`                    | Lê a config (o `access_token` volta mascarado).       |
| `PUT`   | `/config`                    | Salva a config.                                       |
| `GET`   | `/dispositivos`              | Lista as maquininhas pareadas (para achar o `device_id`). |
| `POST`  | `/cobranca`                  | Dispara a cobrança. Body: `{"valor": 10.50, "venda_uuid": "..."}`. |
| `GET`   | `/cobranca/{id}`             | Consulta o status (faça *poll* a cada ~2s).           |
| `DELETE`| `/cobranca/{id}`             | Cancela uma cobrança ainda não concluída.             |

### Fluxo de uma venda no cartão

```
1. POST /api/maquininha/cobranca  { "valor": 49.90, "venda_uuid": "<uuid-da-venda>" }
   → { "payment_intent_id": "abc123", "state": "OPEN" }

2. (poll) GET /api/maquininha/cobranca/abc123
   → state: OPEN → ON_TERMINAL → PROCESSING → FINISHED
   → ao finalizar: { "pago": true, "payment_status": "approved", "payment_type": "credit_card" }

3. Se o cliente desistir: DELETE /api/maquininha/cobranca/abc123
```

Estados possíveis de `state`: `OPEN`, `ON_TERMINAL`, `PROCESSING`, `FINISHED`,
`CANCELED`, `ERROR`, `ABANDONED`. Considere pago somente quando
`state == "FINISHED"` **e** `payment_status == "approved"`.

## Valores

O `valor` é enviado em reais (ex.: `49.90`); internamente convertemos para
**centavos** (`4990`), como a API do Mercado Pago exige.

## Segurança

- O `access_token` nunca é devolvido pelo `GET /config` (vem em branco, com o
  flag `access_token_preenchido: true`). Trate-o como segredo.
- A cobrança roda na conta Mercado Pago da própria loja — o VendaFácil não
  intermedeia o dinheiro nem vê dados de cartão.

## Comportamento à prova de offline (no PDV)

A cobrança integrada é tratada como **conveniência só-online** — nunca como
dependência da venda. No checkout (`PDV.tsx`):

- O fluxo integrado só dispara quando **Débito/Crédito + maquininha habilitada +
  `device_id` configurado + `navigator.onLine`**. Caso contrário, a venda segue
  como **cartão manual** (o caixa passa no aparelho e o sistema só registra).
- Se a cobrança falhar ou cair a conexão durante o *poll*, o modal oferece
  **"Registrar cartão manual"** — a venda **nunca trava**.
- A venda é gravada **localmente primeiro** (SQLite) e sincroniza depois. Quando
  o pagamento é aprovado pela Point, o `payment_id` do Mercado Pago é anexado à
  observação da venda (`MP Point: <id>`) para conciliação.

> Importante: o PDV fala com a maquininha **pela nuvem do Mercado Pago**
> (`PDV → internet → MP → aparelho`), não por uma conexão direta de wifi local.
> Os dois precisam de internet. Pagamento em cartão é autorizado online por
> natureza — não existe cartão 100% offline; sem internet, venda no cartão é
> sempre **manual** (ou use dinheiro/PIX/fiado).

## Observações sobre o Painel SaaS / Supabase

A maquininha é **100% do lado do PDV**. As vendas no cartão chegam ao Painel SaaS
pela sincronização normal (como `forma_pagamento` = `credito`/`debito`), então
**o schema do Supabase não muda** por causa desta funcionalidade.
