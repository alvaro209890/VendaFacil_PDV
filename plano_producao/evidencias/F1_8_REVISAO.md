# F1.8 — prova de queda real

Gemini high `deleg_1a1b940a`: aprovado, sem security_concerns/logic_errors. O revisor confirmou processo realmente morto entre a baixa e o INSERT de venda, teste sensível à rota legada e isolamento completo em tmp_path. Sugestões não bloqueantes: mensagem mais detalhada de timeout/saída prematura do worker.

Controle histórico RED usa a rota real `a4f8e69:backend/vendas.py` extraída do git para a pasta temporária, sem alterar o produto. Falhou estoque4≠5. GREEN atual conserva5, sem linhas parciais em vendas/itens/movimentações/fiado, integrity_checkok e foreign_key_checkvazio. Suítes118/7. Logs F1_8_RED_legado.txt, F1_8_GREEN_queda.txt, F1_8_GREEN.txt e F1_8_PAINEL.txt. Commit `15c7fb9`.
