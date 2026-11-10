# F1.1/F1.2 — revisão adversária de dinheiro

Revisores independentes Gemini high:
- `deleg_de215589`: módulo dinheiro e testes, aprovado sem security_concerns ou logic_errors. Revisor executou suítes (relato); orquestrador também executou e guardou saídas próprias.
- `deleg_6065d70c`: cálculo do checkout, aprovado sem security_concerns ou logic_errors; contraprova 2,675×1−0,005 confirmada após quantizar subtotal e desconto.

Sugestões não bloqueantes:
- Parser monetário backend aceita vírgula simples, não milhar formatado. UI será tratada por P31; API tem campos JSON numéricos.
- Desconto negativo já é impedido por CheckoutRequest.desconto = Field(ge=0).
- Manter precisão Decimal internamente e float apenas na borda; integração futura seguirá isso. Nenhuma migração de schema REAL.

Evidência do orquestrador: F1_1_RED/GREEN.txt; F1_2_RED/GREEN/PAINEL.txt. RED de F1.2 teve a representação de fixture auth removida, para não versionar JWT sintético. Próximos pytest usam --tb=short. Nenhum token real foi utilizado.

Commits: `3fe1aa4` (módulo), `52bb220` (checkout). Backend 76→83→84; painel 7→7. P3 ainda em andamento: falta F1.3/F1.4.
