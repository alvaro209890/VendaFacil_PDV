# F1.14 — isolamento de categoria e cliente

RED: `F1_14_RED.txt` — PUT da categoria de outro usuário retornava 200 e o nome alheio. O UPDATE já filtrava `user_id`, mas o SELECT seguinte lia só pelo id.

Correção: `rowcount == 1` e SELECT com `user_id`. Checkout não fiado com cliente alheio já era recusado pela transação; o teste agora impede regressão.

Revisão `deleg_27af025a`: aprovada, sem security_concerns/logic_errors. Sugestão aplicada antes do commit: o teste usa `monkeypatch` em vez de gravar `categorias.db` global.

GREEN: `F1_14_GREEN.txt` 158 passed; painel 7. Commit `c7e3991`.
