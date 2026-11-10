# Auditoria consolidada da Fase 0

Data: 2026-11-10. Fonte: seis subagentes Gemini `ag/gemini-3.8-flash-high`, esforço high, unidade `deleg_4ebfcb98`; revisão do orquestrador. Alguns auditores atingiram 30 iterações: os relatos não são prova de correção nem de cobertura exaustiva. Nenhuma alteração no produto na auditoria.

## Validação independente

- `F0_backend.txt`: 76 passed; `F0_painel.txt`: 7 passed; build e lint exit 0.
- `F0_sondagem.txt`: falha SQL ao inserir venda deixa estoque 9→8; checkout arredonda 2,675 para 2,67; FK desativada; não existe cancelamento de venda.
- P7 parcialmente refutada: busy_timeout=5000 e synchronous=2 (FULL) já são os padrões observados. Manter FULL explicitamente; NORMAL não é correção obrigatória e reduz durabilidade.
- Inspeção direta do orquestrador: `fiscal_router.py:33–64,110–131` não valida proprietário em leitura/consulta/cancelamento; `fiscal_config.py:95–99` persiste strings vazias sensíveis; `recibo.ts:83,91,108,115` interpola conteúdo sem escape; `auth.py:123–179` confirma login sem limite e registro aberto.

## Encaminhamento

As 22 pistas originais foram confirmadas no código, com as ressalvas P7 e as decisões P11/P12/P14/P16. Não são correções concluídas. Novos problemas acionáveis: P23–P42 em 02_PISTAS, com testes e tarefas distribuídos nas fases. Achados sobre o mesmo mecanismo foram agrupados, não multiplicados artificialmente.

## Alegações não adotadas como defeito

| Alegação do auditor | Decisão e prova |
|---|---|
| Falta cobrança automática no SaaS | Descartada: docs/CHECKLIST_COMERCIALIZACAO.md:9–11 define cobrança MANUAL por decisão do projeto. |
| Sync deve recusar loja bloqueada | Descartada: main.py:360–366 devolve licenca_ok e ainda recebe dados; preservar dados e sincronização é compatível com L03. O cliente deve interpretar a resposta sem perder registros. |
| Implementar fingerprint/limite de dispositivos | Não implementar: produto atual não define limite. É mudança de negócio, não bug desta entrega. |
| Trocar synchronous FULL por NORMAL | Descartada: FULL favorece integridade na queda de energia. Explicitar FULL. |
| Cancelamento de categoria faz query desnecessária | Não é falha funcional: queries filtram user_id e a transação é única; a leitura de retorno sem owner é tratada em P23. |
| Token no localStorage e A1 em estado React | Riscos locais aceitos/documentados, não defeitos por si. Tratar XSS, logs e mascaramento; não reescrever autenticação/cofre. |
| Novo fluxo de gerente para cancelar fiado | Não alterar o fluxo sem decisão; recusar cancelamento de conta paga/parcial e auditar, conforme D8. |
| crypto.randomUUID em IP LAN HTTP | Runner local escuta em 127.0.0.1; LAN não é requisito desta entrega. Não abrir bind de rede para contornar. |
| Depreciação on_event/httpx | Avisos registrados, não falhas. Não silenciar nem reduzir testes para verde. |
| Margem usa custo atual | Relatório já se intitula lucro estimado; documentar sem alterar schema histórico nesta entrega (D9). |
| cEANTrib deve substituir cEAN automaticamente | Não aceitar cegamente: embalagem e GTIN unitário podem ter unidades diferentes; validar conversão explícita em I02/I05. |

## Notas de fonte

Os relatos sobre protocolos fiscais serão confrontados com schemas/manuais oficiais na Fase 4; hipótese de auditor não vira regra fiscal. Esta auditoria não realizou requisição SEFAZ, não leu cofre real e não utilizou certificado.
