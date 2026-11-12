# Fase 2 — Caixa, fiado, importação de XML e licença

**Status:** ✅ concluída (reaberta em 11/11 para F2.23/P46/I08 e refechada em 12/11) · **Depende de:** Fase 1

## Objetivo

O fechamento do caixa bate com a gaveta, o fiado tem histórico, a importação de nota de compra não duplica nada e a licença nunca prende os dados do lojista.

## Tarefas

### Caixa

- [x] F2.1 (P4) Ligar a venda à sessão de caixa aberta (coluna nova por migração aditiva, no padrão das outras em `database.py`); o resumo passa a somar pela sessão, com a janela de tempo só como reserva para vendas antigas. Testes C01 e C06 — 320bc56 · C06 RED qtd 1→0; suíte160/7; revisão deleg_bb75ffaf aprovada
- [x] F2.2 (P4) Venda sem caixa aberto: aplicar a decisão D4 (padrão: permitir e avisar no PDV) — 2629af3 · aviso no PDV sem desabilitar finalização; revisão deleg_eb733afb aprovada
- [x] F2.3 Validações: valor ≤ 0 em sangria/suprimento (C05); segundo caixa aberto recusado (C08); sangria maior que o dinheiro em caixa tem comportamento definido e testado — 85a3abf · C05 422→400 e sangria 10,01 recusada 409; suíte167/7; revisão deleg_c63b6825 aprovada

### Fiado

- [x] F2.4 (P21) Tabela de pagamentos do fiado (data, valor, forma, usuário). Baixa parcial grava histórico. Teste C03 — 2fbd5e1 · RED sem chave pagamentos; suíte168/7; revisão deleg_81dba485 aprovada
- [x] F2.5 (P21) Recusar pagamento maior que o pendente e valor ≤ 0. Testes C04 e C05 — 4033835 · excedente 200→400 sem baixa; suíte171/7; revisão deleg_39f6556a aprovada
- [x] F2.6 (P21) Recebimento em dinheiro lança no caixa aberto e entra no esperado. Teste C02 — 7c56670 · RED esperado 10,00≠10,50; suíte172/7; revisão deleg_001dd4e6 aprovada
- [x] F2.7 Tela `src/pages/ContasReceber.tsx`: mostrar o histórico de pagamentos e o erro de excedente — 12f1994 · RED sem histórico na lista; suíte174/7; revisão deleg_ca8479d7 aprovada

### Importação de XML e produtos

- [x] F2.8 Chave de NF-e já importada não entra de novo (guardar a chave e conferir antes). Teste I01 — 781f6cd · RED segunda importação 200; suíte175/7; revisão deleg_cf309b35 aprovada
- [x] F2.9 Unidade e quantidade por embalagem (I02); XML malformado ou que não é NF-e (I03); código de barras duplicado (I04); `cEAN` "SEM GTIN" (I05) — 18c590d · RED fator 1,0 e código 201; suíte181/7; revisão deleg_6246e8ff aprovada

### Licença e sincronização

- [x] F2.10 Modo local e carência offline (L01, L02) — be1efa7 · prova de venda sem rede; suíte183/7; revisão deleg_b81adb43 aprovada
- [x] F2.11 Licença vencida ou carência estourada **não** impede fechar caixa, ler dados, exportar backup nem exportar XML fiscal (L03, C07). Ajustar onde bloquear demais — b247f2b · RED a tela substituía o app; suíte185/7; revisão deleg_1462163e aprovada
- [x] F2.12 `sync_client.py` fora do caminho da venda: painel fora do ar não atrasa o checkout (L04, com tempo medido) — 3e8f1a4 · RED 2,02s; suíte186/7; revisão deleg_4345c797 aprovada

### Fechamento

- [x] F2.13 Revisor adversário em caixa e fiado (sequências estranhas: fechar com venda em andamento, pagar conta cancelada, cancelar venda de sessão já fechada) — be78390 · RED 200 nos dois ataques; suíte189/7; revisão deleg_a1ec1fef aprovada

## Complementos da auditoria

- [x] F2.14 P27: persistir e conciliar cobrança aprovada que ainda não gerou venda; L05 — b633307 · RED segunda cobrança ia à maquininha; suíte190/7; revisão deleg_ee30d8a2 aprovada
- [x] F2.15 P28: normalização do PIX EMV com nomes acentuados; L06 — 3227373 · RED ainda levava JOSÉ; suíte191/7; revisão deleg_74364e3d aprovada
- [x] F2.16 P29: ACK de sincronização só marca vendas efetivamente aceitas; L07 — 46244a9 · RED marcava as duas; suíte192/7; revisão deleg_b5967088 aprovada
- [x] F2.17 P30: validar datas de licença no painel e fim do dia em MT; L08 — f1aeec4 · RED data inválida liberava; painel9/backend192; revisão deleg_7c21b78d aprovada
- [x] F2.18 P37: cliente com dívida, referências e estado de conta; C09 — e1ad5e2 · RED DELETE 200; suíte194; revisão deleg_be115551 aprovada
- [x] F2.19 P38: cadastro de produto e campos fiscais atômicos; I07 — 7dee50a · RED INSERT+UPDATE; suíte195; revisão deleg_b6024c9a aprovada

- [x] F2.20 P24/I06: completar atomicidade da importação (estoque + produto fiscal + movimentos + chave); provar rollback ABORT/IGNORE e concorrência da mesma NF-e. Lacuna detectada na reconciliação do portão em 11/11. — 00e709d · 16 casos atômicos/retry/concorrência verdes; revisão deleg_1de7f6d4 completa aprovada; recheck no parent.

- [x] F2.21 P24/I06: completar validação do modelo 55/GTIN e números do XML na prévia; não alegar validação completa só com SEM GTIN e XML malformado. — 5b8f0f2 · 34 casos do parser e HTTP400; suíte256/9; build/lint verdes; revisão deleg_177521b8 aprovada, recheck no parent.
- [x] F2.22 P29/L07: respostas não-JSON/tipos inválidos do ACK devem preservar fila sem exceção; complementar teste parcial existente. — 40f49e7 · 17 novos casos + ACK parcial; suítes273/9 (gate posterior274/9), revisão deleg_754105c0 aprovada e recheck no parent.

- [x] F2.23 P46/I08: encaminhar a chave recebida da prévia na confirmação pela UI; repetir XML na tela deve retornar 409 e preservar estoque/produtos. RED real: segunda importação retornou200. — 41c9265;67Chromium/315backend/9painel;revisão deleg_d6e39f23 aprovada,recheckUIverde.

## Portão de saída

- [x] I08 em Chromium com leitura do estoque persistido; revisão independente e recheck. — 41c9265;primeira200,segunda409,umprodutoestoque2;mensagem+IDvisíveis.

- [x] C01–C08, I01–I05 e L01–L04 ✅ em `03_TESTES.md` — 8a05019 · roteiro offline revisto deleg_f6a9cdcd; demais casos na suíte274.
- [x] Suítes do backend e do painel verdes — 8a05019 · F2_PORTAO_BACKEND.txt 274 passed; F2_PORTAO_PAINEL.txt 9 passed; código idêntico e recheck L01 no parent.
- [x] `docs/CAIXA.md`, `docs/ESTOQUE_E_XML.md`, `docs/LICENCA.md` e `docs/MANUAL.md` atualizados no que mudou — 978c6d4/5b8f0f2/40f49e7 · contratos reconciliados.
- [x] Pasta do plano commitada e `git push origin master` — 05c6323 · primeiro push real com readback; F2.23 publicada em 11/12 e novo push em 12/12 (ver diário), restando o push final da Fase 3.

## Evidências

| Item | Comando | Saída resumida |
|---|---|---|
| Suíte | `pytest backend/tests` e `pytest painel/tests` isolados conforme regras | `F2_PORTAO_BACKEND.txt`: 274 passed; `F2_PORTAO_PAINEL.txt`: 9 passed; três avisos herdados por suíte |
| Caixa com fiado em dinheiro (C02) | Suíte inclui `test_fiado_caixa.py` e `test_offline_roteiro.py` | Dinheiro recebido entra na gaveta; histórico e fechamento conferidos; sem rede no roteiro |
| Importação duplicada (I01) | Suíte inclui `test_importacao_chave.py` e `test_importacao_atomica.py` | 409 na repetição; uma entrada na concorrência em duas conexões; rollback em ABORT/IGNORE |
| Checkout com painel fora (L04) | `test_licenca.py::test_l04_painel_fora_nao_atrasa_checkout` na suíte completa | Checkout passa no limite <1s com rede simulada lenta de 2s; não depende de sync |
