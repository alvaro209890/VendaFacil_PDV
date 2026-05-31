# 🧪 Roteiro de teste no Windows (antes de vender)

Checklist para validar o `.exe` numa máquina Windows real, função por função.
Marque cada item. "✅ Esperado" descreve o resultado correto.

> Pré-requisito: já ter gerado o `.exe`/instalador (veja `BUILD_WINDOWS.md`).
> Dica: deixe o **Console** do app aberto — erros aparecem nele.

## 0. Instalação
- [ ] Rodar `VendaFacilPDV-Setup-*.exe`. ✅ Instala, cria atalho no Menu Iniciar e Área de Trabalho.
- [ ] (SmartScreen) "Editor desconhecido". ✅ "Mais informações → Executar assim mesmo" abre normal.
- [ ] Abrir pelo atalho. ✅ O navegador abre em `http://127.0.0.1:3020/`.

## 1. Login / primeiro acesso
- [ ] Criar conta (registro) com e-mail e senha forte. ✅ Entra no sistema.
- [ ] Sair e logar de novo. ✅ Login funciona.
- [ ] (Se usar painel) informar login/senha da loja. ✅ Ativa; bloqueada no painel = trava na revalidação.

## 2. Produtos
- [ ] Cadastrar produto (nome, custo, venda, estoque, código de barras, unidade). ✅ Aparece na lista.
- [ ] Editar e desativar. ✅ Refletem na lista.
- [ ] Cadastrar produto com estoque ≤ mínimo. ✅ Dashboard mostra alerta de estoque baixo.
- [ ] Botão **+ Estoque** (entrada rápida) somando quantidade. ✅ Estoque aumenta.

## 3. Importar XML (NF-e)
- [ ] **📄 Importar XML** com um `.xml` de NF-e real do fornecedor. ✅ Mostra a prévia com os itens.
- [ ] Item com código já cadastrado aparece como **repor**; novo como **criar**. ✅ Correto.
- [ ] Confirmar. ✅ Estoque dos existentes sobe; novos são criados; custo atualiza.

## 4. Venda (PDV)
- [ ] Buscar por nome e por **código de barras** (use o leitor se tiver). ✅ Bipou → entra no carrinho.
- [ ] Ajustar quantidade (+/−), aplicar desconto. ✅ Total recalcula.
- [ ] Finalizar com **Dinheiro** (ou tecla **F2**). ✅ "Venda finalizada"; estoque baixa.
- [ ] Tentar vender mais que o estoque. ✅ Bloqueia com mensagem de estoque insuficiente.

## 5. Formas de pagamento
- [ ] **PIX**: gera QR Code (precisa de chave PIX configurada). ✅ QR aparece; confirmar conclui a venda.
- [ ] **Maquininha (se configurada + internet)**: dispara cobrança na Point e aguarda. ✅ Aprovou → venda concluída.
- [ ] **Maquininha sem internet / falha**: ✅ Oferece "cartão manual"; a venda **não trava**.
- [ ] **Fiado**: escolher cliente. ✅ Cria conta a receber.

## 6. Recibo térmico
- [ ] Selecionar largura (80mm/58mm) conforme a impressora. ✅ Salva a escolha.
- [ ] Marcar "Imprimir recibo ao finalizar" e vender. ✅ Imprime automático na térmica.
- [ ] Usar **🖨️ Imprimir recibo** para reimprimir. ✅ Sai o cupom com loja, itens, total e forma de pagamento.

## 7. Caixa
- [ ] **Abrir caixa** com fundo de troco. ✅ Mostra "dinheiro esperado" = abertura.
- [ ] Fazer vendas em dinheiro e em cartão/PIX. ✅ Só o dinheiro soma ao esperado da gaveta.
- [ ] **Suprimento** e **Sangria**. ✅ Ajustam o esperado.
- [ ] **Fechar** contando um valor diferente. ✅ Mostra a **diferença** (sobra/falta) e some do "atual".

## 8. Contas a receber (fiado)
- [ ] Registrar **pagamento parcial** e depois o restante. ✅ Pendente diminui; quita ao zerar.

## 9. Relatórios
- [ ] Abrir **Relatórios**, usar atalhos (Hoje / 7 / 30 / Mês). ✅ Faturamento, nº de vendas e ticket batem com o que você vendeu.
- [ ] Conferir **por forma de pagamento** e **top produtos**. ✅ Consistentes.

## 10. Backup
- [ ] **Baixar backup agora**. ✅ Baixa um `.db` (guarde fora do PC).
- [ ] Criar um produto "TESTE", depois **Restaurar** o backup baixado antes dele. ✅ "TESTE" some (voltou ao estado do backup); página recarrega.
- [ ] Conferir backups automáticos em `%LOCALAPPDATA%\VendaFacilPDV\dados\backups`.

## 11. Nota fiscal (NFC-e) — só se for usar
- [ ] Preencher a tela **Fiscal** (emitente + gateway Focus NFe, ambiente **homologação**).
- [ ] Emitir NFC-e de uma venda. ✅ Autoriza em homologação (status "autorizada"); links de XML/DANFE aparecem.
- [ ] Só então mudar para **produção** (exige certificado A1, CSC e credenciamento na SEFAZ).

## 12. Persistência e offline
- [ ] Fechar o app e abrir de novo. ✅ Produtos/vendas/caixa continuam lá (banco em `%LOCALAPPDATA%`).
- [ ] **Desligar a internet** e vender em dinheiro/PIX/fiado. ✅ Funciona normal.
- [ ] Com internet de volta (se usar painel): as vendas sincronizam sozinhas em segundo plano.

## 13. Sinais de problema (o que observar)
- App não abre / porta ocupada → ver o Console; outra instância na porta 3020?
- "Editor desconhecido" → normal (sem assinatura).
- Cartão não cobra → internet + Point em modo PDV + Access Token/Device certos.
- Recibo sai cortado → ajustar a **largura** (58/80mm) e, no diálogo de impressão, desativar cabeçalho/rodapé e margens.

---

Passou em tudo? O sistema está pronto para uso no balcão. Guarde este checklist
para repetir a cada nova versão do `.exe`.
