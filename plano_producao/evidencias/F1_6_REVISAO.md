# F1.5/F1.6 — revisões de integridade e atomicidade

- **F1.5/P7** — Gemini high `deleg_a0b41841`: aprovado, sem security_concerns/logic_errors. PRAGMAs aplicados antes de transação; FULL preserva durabilidade. Sugestão de diagnóstico de órfãos legados fica para Fase5. Provas: F1_5_RED.txt e F1_5_GREEN/PAINEL.txt (104/7). Commit `a4f8e69`.
- **F1.6/P1 (parte transacional)** — Gemini high `deleg_97847eb4`: aprovado, sem security_concerns/logic_errors. BEGIN IMMEDIATE, SQL direto sem contexto conn aninhado, estoque agregado por produto e rollback automático. Sugestão não bloqueante de defesa SQL adicional anotada. Provas: F1_6_RED.txt, F1_6_RED_update_ignorado.txt, F1_6_GREEN/PAINEL.txt (107/7). Commit `68fcc88`.

O teste legado que mockava `baixar_estoque` foi adaptado para falha SQL verdadeira via trigger `RAISE(IGNORE)` no segundo produto: preservou os asserts HTTP409 e estoque original. As novas injeções de falha ao inserir venda, movimento e conta fiada garantem que o estoque e todas as tabelas voltem ao estado anterior.

Nenhum teste tocou banco real, certificado ou rede SEFAZ. A parte de concorrência, queda do processo e cancelamento segue em itens específicos; não é declarada concluída por estes commits.
