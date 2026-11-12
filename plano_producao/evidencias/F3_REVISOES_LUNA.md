# Revisões independentes — 12/11/2026

Modelo autorizado pelo usuário: GPT-6 Luna, raciocínio high; revisor somente leitura.
Execuções e resultados abaixo foram conferidos pelo agente principal.

| Item | Parecer | Achados e resolução |
|---|---|---|
| F3.22 | Aprovado | Venda e nota pertencem ao usuário antes do serviço fiscal; positivos/ausência de nota/modelo55 acrescentados. Pai: RED4, GREEN323 backend. |
| F3.21 bootstrap | Aprovado | BEGIN IMMEDIATE SQLite; LOCK TABLE na transação PG. Teste disputa duas conexões SQLite. PG avaliado por código, sem servidor PG de teste nesta máquina. RED1, GREEN10 painel. |
| F3.21 senha | Aprovado com ajuste visual | Mínimo8/comuns no servidor, login legado preservado. Rótulos mínimos corrigidos e campos limitados a128; senha de conta mascarada na tela. RED8, GREEN18 painel. |
| F3.21 revogação | Aprovado após correção | Revisor identificou corrida PRAGMA/ALTER SQLite. BEGIN IMMEDIATE cobre os dois, teste de migração concorrente e token legado adicionados. RED3, GREEN23 painel. |
| F3.19 | Aprovado | Soma decimal integral por usuário e dia UTC−4, independente da página, canceladas fora. Revisor pediu virada mês/ano explícita; dois casos adicionados. RED2 backend/1 UI; GREEN327 backend (inclui mês/ano) e1 UI. |

Nenhuma execução de homologação real é alegada nesta fase.
