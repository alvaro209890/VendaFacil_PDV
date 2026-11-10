# Fase 2 — Caixa, fiado, importação de XML e licença

**Status:** ⬜ não iniciada · **Depende de:** Fase 1 · **Pistas:** P4, P21 · **Testes:** C01–C08, I01–I05, L01–L04

## Objetivo

O fechamento do caixa bate com a gaveta, o fiado tem histórico, a importação de nota de compra não duplica nada e a licença nunca prende os dados do lojista.

## Tarefas

### Caixa

- [ ] F2.1 (P4) Ligar a venda à sessão de caixa aberta (coluna nova por migração aditiva, no padrão das outras em `database.py`); o resumo passa a somar pela sessão, com a janela de tempo só como reserva para vendas antigas. Testes C01 e C06
- [ ] F2.2 (P4) Venda sem caixa aberto: aplicar a decisão D4 (padrão: permitir e avisar no PDV)
- [ ] F2.3 Validações: valor ≤ 0 em sangria/suprimento (C05); segundo caixa aberto recusado (C08); sangria maior que o dinheiro em caixa tem comportamento definido e testado

### Fiado

- [ ] F2.4 (P21) Tabela de pagamentos do fiado (data, valor, forma, usuário). Baixa parcial grava histórico. Teste C03
- [ ] F2.5 (P21) Recusar pagamento maior que o pendente e valor ≤ 0. Testes C04 e C05
- [ ] F2.6 (P21) Recebimento em dinheiro lança no caixa aberto e entra no esperado. Teste C02
- [ ] F2.7 Tela `src/pages/ContasReceber.tsx`: mostrar o histórico de pagamentos e o erro de excedente

### Importação de XML e produtos

- [ ] F2.8 Chave de NF-e já importada não entra de novo (guardar a chave e conferir antes). Teste I01
- [ ] F2.9 Unidade e quantidade por embalagem (I02); XML malformado ou que não é NF-e (I03); código de barras duplicado (I04); `cEAN` "SEM GTIN" (I05)

### Licença e sincronização

- [ ] F2.10 Modo local e carência offline (L01, L02)
- [ ] F2.11 Licença vencida ou carência estourada **não** impede fechar caixa, ler dados, exportar backup nem exportar XML fiscal (L03, C07). Ajustar onde bloquear demais
- [ ] F2.12 `sync_client.py` fora do caminho da venda: painel fora do ar não atrasa o checkout (L04, com tempo medido)

### Fechamento

- [ ] F2.13 Revisor adversário em caixa e fiado (sequências estranhas: fechar com venda em andamento, pagar conta cancelada, cancelar venda de sessão já fechada)

## Complementos da auditoria

- [ ] F2.14 P27: persistir e conciliar cobrança aprovada que ainda não gerou venda; L05
- [ ] F2.15 P28: normalização do PIX EMV com nomes acentuados; L06
- [ ] F2.16 P29: ACK de sincronização só marca vendas efetivamente aceitas; L07
- [ ] F2.17 P30: validar datas de licença no painel e fim do dia em MT; L08
- [ ] F2.18 P37: cliente com dívida, referências e estado de conta; C09
- [ ] F2.19 P38: cadastro de produto e campos fiscais atômicos; I07

## Portão de saída

- [ ] C01–C08, I01–I05 e L01–L04 ✅ em `03_TESTES.md`
- [ ] Suítes do backend e do painel verdes
- [ ] `docs/CAIXA.md`, `docs/ESTOQUE_E_XML.md`, `docs/LICENCA.md` e `docs/MANUAL.md` atualizados no que mudou
- [ ] Pasta do plano commitada e `git push origin master`

## Evidências

| Item | Comando | Saída resumida |
|---|---|---|
| Suíte | | |
| Caixa com fiado em dinheiro (C02) | | |
| Importação duplicada (I01) | | |
| Checkout com painel fora (L04) | | |
