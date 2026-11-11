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
4. **Dinheiro esperado** = abertura + vendas em dinheiro + recebimentos de fiado em dinheiro + suprimentos − sangrias.
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

A conferência fiscal bloqueia o estorno enquanto existir nota autorizada, pendente,
em processamento ou em contingência. A reserva é gravada antes da transmissão.
Venda cancelada sai dos totais. Venda vinculada a caixa já fechado não pode ser
estornada comercialmente: retorna 409 sem reabrir o caixa nem alterar a gaveta.

## Sessões e validações

- Cada venda nova guarda a sessão aberta do próprio usuário na mesma transação.
  A sessão seguinte não soma as vendas da anterior; janela temporal é só fallback
  para vendas legadas sem vínculo.
- Sem caixa aberto, a venda continua permitida (D4), com aviso na tela. Ela não
  ganha vínculo retroativo ao abrir outra sessão.
- Segundo caixa aberto pelo mesmo usuário: 409.
- Sangria, suprimento e pagamento de fiado precisam ter valor maior que zero
  (400). Sangria acima do dinheiro esperado: 409, sem gravar movimento.
- Licença bloqueada não impede fechar caixa nem ler/exportar dados.

## Fiado

Baixas parciais/totais mantêm histórico de data, valor e forma. Excedente não é
engolido: retorna 400 sem baixar a conta. Valor exato quita. Conta cancelada não
aceita recebimento (409). Receber em dinheiro entra no caixa aberto do usuário;
PIX/cartão não alteram espécie. Cliente com fiado em aberto não pode ser ocultado
pelo DELETE (409).
