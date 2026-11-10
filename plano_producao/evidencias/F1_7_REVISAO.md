# F1.7 — concorrência e limites

Revisor Gemini high `deleg_8bd64d0d`: aprovado, sem security_concerns/logic_errors. Testes exercitam threads e conexões reais, sem mocks. Sugestão de agregar quantidades também na pré-validação da rota é não bloqueante: a transação já agrega e rejeita sem gravar.

RED: F1_7_RED.txt (0/−1 retornavam422 em vez do400 previsto) e F1_7_RED_infinitos.txt (Infinity causava500). GREEN: F1_7_GREEN.txt:117 passed; painel7. Provas específicas em F1_7_TRANSACOES.txt.

Commit `79e5ccf`. API concorrente repetida5vezes, SQLite com2conexões independentes, estoque fracionado e itens duplicados, produtos inválidos e leitura de venda de outro usuário. V13 cancelamento segue na F1.9; não foi declarado pronto aqui.
