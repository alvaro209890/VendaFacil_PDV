# Treinamento do operador de caixa (20 minutos)

Faça cada passo junto com o operador, no PDV da loja. Use um produto barato e
cancele as vendas de treino no fim.

## 1. Abrir o caixa (2 min)

1. Menu **Caixa** → informe o **fundo de troco** (dinheiro que já está na gaveta) → **Abrir caixa**.
2. Se esquecer de abrir, o PDV avisa "Caixa fechado", mas deixa vender. Abra o caixa assim que perceber.

## 2. Vender com o leitor (5 min)

| Ação | Como |
|---|---|
| Colocar produto | Bipe o código de barras (ou digite o nome na busca, **F4**) |
| Mudar quantidade | **F3** e digite (vírgula para peso: `0,350`) |
| Desconto | **F6** |
| Forma de pagamento | **F7** (Dinheiro, PIX, Crédito, Débito, Fiado) |
| Dinheiro | Digite o valor recebido; o troco aparece na tela |
| Nota fiscal | Marque **Emitir NFC-e** se a loja emite nota |
| Finalizar | **F2** ou o botão **FINALIZAR VENDA** |
| Fechar janela | **Esc** |

O cupom pode sair sozinho ("Imprimir recibo ao finalizar") ou pelo botão
**🖨️ Imprimir recibo**, que também serve para reimprimir.

Se fechar o programa sem querer com itens no carrinho, ao abrir de novo o
carrinho volta.

## 3. Sangria e suprimento (2 min)

**Caixa** → **Sangria** (tirar dinheiro da gaveta) ou **Suprimento** (colocar
troco). Digite o valor. O "dinheiro esperado" já desconta/soma.

## 4. Fiado e recebimento (4 min)

1. Venda em **Fiado**: escolha o cliente (cadastre em **Clientes** se não existir).
2. Para receber: **Contas a receber** → conta do cliente → registre o valor pago
   (pode ser parcial; quita ao zerar).
3. Venda fiada que já teve pagamento **não pode ser cancelada** antes de estornar
   o recebimento — o sistema avisa.

## 5. Cancelar uma venda (2 min)

**Vendas** → abra a venda → **Cancelar venda (F9)** → escreva o motivo. O estoque
volta. Se a venda teve NFC-e, o cancelamento da nota segue o prazo da SEFAZ
(30 minutos para NFC-e); depois disso, procure o contador.

## 6. Fechar o caixa (3 min)

**Caixa** → conte o dinheiro da gaveta → digite o valor contado → **Fechar**.
O sistema mostra a diferença (sobra ou falta). Só o dinheiro entra na conta da
gaveta; cartão e PIX aparecem separados.

## 7. Se a nota não autorizar (2 min)

| O que aparece | O que fazer |
|---|---|
| **EMITIDA EM CONTINGÊNCIA** (sem internet) | Normal. Entregue a **via do consumidor**, guarde a **via do estabelecimento**. Deixe o programa aberto: quando a internet voltar, a nota é autorizada sozinha |
| **Pendente** | Não refaça a venda. Em **Vendas**, abra a venda e use o botão de atualizar status |
| **Rejeitada** | A venda está gravada. Anote a mensagem e mande o diagnóstico ao suporte (`SUPORTE_LOJA.md`) |

Nunca refaça uma venda só porque a nota não saiu: isso duplica o estoque e o caixa.

## Conferência final

O operador faz sozinho, sem ajuda: abrir caixa → vender 2 itens no dinheiro →
sangria → fechar caixa. Se acertar, o treinamento terminou.
