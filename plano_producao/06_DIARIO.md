# Diário

Só acrescenta, nunca reescreve. Uma linha por item fechado, bloqueio, decisão aplicada ou descoberta. Mais recente **embaixo**.

Formato: `AAAA-MM-DD HH:MM | fase | ID | o que aconteceu | commit`

```
2026-11-10 --:-- | plano | — | Pasta plano_producao criada sobre 6da6899 (pré-análise: 22 pistas, backend 76 passed, painel sem venv) | —
```

2026-11-10 14:35 BRT | 0 | F0.1/F0.2 | Host PCQUE001IMAP; fila Windows vazia. Estado git idêntico ao esperado. Delegação ninerouter Gemini high comprovada (deleg_bdebea33). Nenhum binário ou rascunho será commitado. | 6da6899
2026-11-10 14:35 BRT | 0 | F0.3/F0.4 | PYTHONPATH herdado injeta libs Hermes nos venvs; Python -I e env -u PYTHONPATH isolam. Pip também exige -I, pois instalações anteriores resolviam dependências no ambiente externo. Backend: 76 passed / 3 avisos / 1.61s. | 6da6899
2026-11-10 14:35 BRT | 0 | F0.5 | npm install, build e eslint exit 0. npm audit: 21 vulnerabilidades, 2 runtime (react-router); investigar na Fase 3 sem audit fix --force. | 6da6899
2026-11-10 14:35 BRT | 0 | F0.7 | Seis auditorias somente leitura disparadas por domínio, sem escritores concorrentes nem acesso a segredos. | 6da6899
2026-11-10 14:38 BRT | 0 | F0.4/F0.6 | Painel: 7 passed / 3 avisos. Lidos os 11 documentos exigidos. Comandos corrigidos para Python -I em 01_REGRAS; saídas reais em evidencias/F0_*.txt. | 6da6899
2026-11-10 14:38 BRT | 0 | P1/P2/P3/P7 | Sondagem isolada do orquestrador reproduziu estoque perdido após falha INSERT (9→8), arredondamento 2,675→2,67 e ausência de cancelamento. P7 parcialmente incorreta: SQLite já aplica busy_timeout=5000 e synchronous=2; FK está desativada. Código do produto intocado. | 6da6899
2026-11-10 15:15 BRT | 0 | F0.7/F0.8 | Seis auditorias concluídas; 20 pistas novas agrupadas (P23–P42), 120 testes no total. Revisadas alegações; cobrança automática/fingerprint e mudanças de produto não foram adotados. PRAGMA synchronous continuará FULL. F0_AUDITORIA.md registra triagem e fundamentos. | 6da6899
2026-11-10 15:17 BRT | 0 | F0.9 | Linha de base commitada. Duas suítes novamente verdes: backend 76, painel 7. Logs brutos preservados (espaços de mensagens de terceiros não alterados). Fase 1 iniciada em F1.1. | 52c6e1e
