# F1.10 — cancelamento comercial × fiscal

A primeira revisão, `deleg_3103557a`, reprovou a corrida: `emitir_nfce` e `emitir_nfe` só gravavam a nota depois da rede. Nesse intervalo o cancelamento devolvia o estoque e a autorização posterior deixava nota ativa em venda cancelada.

RED: `F1_10_RED_corrida.txt` (modelos 65 e 55, nota ausente durante a transmissão) e `F1_10_RED_falha_local.txt` (falha local deixava a reserva em `processando`).

Correção: `reservar_nota_fiscal` valida a venda, consome a numeração e grava `processando` na mesma transação, antes de `preparar_e_tentar_transmitir`. O retorno atualiza a mesma linha. Falha sem chave/XML marca `rejeitada` e libera o cancelamento.

Segunda revisão, `deleg_39942334`: aprovada, sem security_concerns/logic_errors. Sugestão não bloqueante: tratar exceção inesperada antes da chave. GREEN: `F1_10_GREEN.txt` 147 passed; painel 7. Commit `197dcee`.

Nenhum certificado real, dado de loja ou chamada à SEFAZ foi usado.
