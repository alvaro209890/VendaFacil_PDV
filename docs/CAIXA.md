# 💵 Fechamento de caixa

Controle de abertura e fechamento do caixa do dia, com sangria/suprimento e
conferência do dinheiro na gaveta. Roda no **.exe local** (offline-first).

## Como funciona

1. **Abrir caixa** (menu **Caixa**): informe o **fundo de troco** inicial
   (dinheiro na gaveta ao abrir). Só pode haver **um caixa aberto** por vez.
2. Durante o expediente, as **vendas** entram automaticamente na sessão, somadas
   por **forma de pagamento** (dinheiro, PIX, débito, crédito, fiado).
3. **Suprimento** (reforço de troco) e **Sangria** (retirada de dinheiro) ajustam
   o esperado na gaveta.
4. **Dinheiro esperado** = abertura + vendas em dinheiro + suprimentos − sangrias.
5. **Fechar caixa**: conte o dinheiro e informe o valor. O sistema mostra a
   **diferença** (sobra/falta) em relação ao esperado e guarda no histórico.

> Só o **dinheiro** entra no cálculo da gaveta. PIX/cartão aparecem no resumo de
> vendas, mas não afetam o esperado em espécie.

## API (backend, exige JWT)

| Método | Rota | Função |
|---|---|---|
| `GET`  | `/api/caixa/atual` | sessão aberta + resumo (ou `{aberto:false}`) |
| `POST` | `/api/caixa/abrir` | abre o caixa (`valor_abertura`) |
| `POST` | `/api/caixa/movimento` | sangria/suprimento (`tipo`, `valor`, `motivo`) |
| `POST` | `/api/caixa/fechar` | fecha (`valor_fechamento`) e calcula a diferença |
| `GET`  | `/api/caixa/historico` | sessões fechadas |

Tabelas: `caixa_sessoes` e `caixa_movimentos` (banco local do PDV).

## Cancelamento comercial (backend)

`POST /api/vendas/{id}/cancelar` exige JWT do dono da venda e JSON
`{"motivo":"Registro incorreto"}` (3–255 caracteres não vazios). O backend guarda
motivo/data, muda o status, devolve o estoque com movimento de entrada e zera a
conta de fiado em uma única transação. Repetição ou corrida não duplica a devolução.
Se houve recebimento parcial/total, recusa e orienta estornar o recebimento antes
(decisão D8); não devolve dinheiro silenciosamente. Falha SQL desfaz todo o estorno.

A conferência fiscal e a exclusão dos totais de caixa/relatórios são portões
separados do plano (F1.10/F1.11). Esta API isolada não constitui aprovação de produção.
