# 🖨️ Impressão de recibo (impressora térmica)

Ao finalizar uma venda, o PDV pode imprimir um **cupom não-fiscal** na impressora
térmica (rolo de **58mm** ou **80mm**).

## Como funciona

O sistema monta o cupom como um HTML estreito (largura do rolo, fonte
monoespaçada) e dispara a **impressão pelo diálogo do navegador**. Basta a
impressora térmica estar **instalada no Windows** (com o driver do fabricante) —
ela aparece como uma impressora normal. Não usamos comandos ESC/POS de baixo
nível, então funciona com a maioria das térmicas via driver.

> Dica: deixe a impressora térmica como **padrão** no Windows e, no diálogo de
> impressão, desative cabeçalho/rodapé do navegador e margens para um corte limpo.

## Na tela de venda (PDV)

- **Largura**: selecione **80mm** ou **58mm** (fica salvo no aparelho).
- **"Imprimir recibo ao finalizar"**: se marcado, imprime automaticamente ao
  concluir a venda.
- Após finalizar, aparece o botão **"🖨️ Imprimir recibo"** para reimprimir o
  último cupom quando quiser.

## O que sai no cupom

- Cabeçalho com **nome da loja, CNPJ e endereço** (puxados da configuração
  **Fiscal**, se preenchidos; senão, "VendaFácil PDV").
- Data/hora e número da venda.
- Itens (quantidade × preço = subtotal).
- Subtotal, desconto, **TOTAL** e a **forma de pagamento**.
- Rodapé "Obrigado pela preferência" + aviso de que **não é documento fiscal**.

## Quando a venda emite NFC-e

Se a venda for com **"emitir nota"** e a NFC-e for **autorizada**, o recibo
térmico inclui automaticamente um **bloco fiscal**: número/série, **chave de
acesso**, protocolo e o **QR Code** de consulta da NFC-e. Nesse caso o cupom
deixa de ter o aviso "não é fiscal" — ele é o comprovante da nota.

> Observação: o layout do cupom fiscal traz os elementos essenciais (emitente,
> itens, total, chave e QR). Valide com a SEFAZ do seu estado antes de usar em
> produção; em homologação dá para conferir tudo.

Para configurar a emissão de NFC-e, use a tela **Fiscal** (gateway Focus NFe).
