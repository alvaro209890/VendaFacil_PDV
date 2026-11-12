# Plano de produção — VendaFácil PDV

Pasta de trabalho do agente. **Tudo o que falta para o PDV ficar pronto está aqui**, e o progresso é marcado nos próprios arquivos. Esta pasta é a única fonte de verdade do trabalho: se algo aqui estiver errado, corrija aqui e anote no diário.

Criado em 10/11/2026 sobre o commit `6da6899`, com pré-análise real do código.

## Mapa

| Arquivo | Para quê | Quem atualiza |
|---|---|---|
| `00_PAINEL.md` | Estado geral: fase atual, placar, próxima ação | agente, a cada item fechado |
| `01_REGRAS.md` | Regras duras, subagentes, comandos do ambiente | só se a regra mudar |
| `02_PISTAS.md` | Bugs e lacunas já vistos no código, com status | agente |
| `03_TESTES.md` | Matriz de todos os testes exigidos, com status | agente |
| `04_BLOQUEIOS.md` | O que depende de terceiro (lista fechada) | agente |
| `05_DECISOES_ALVARO.md` | O que é decisão de produto, com o padrão a seguir | agente registra; Álvaro decide |
| `06_DIARIO.md` | Registro corrido do que foi feito (só acrescenta) | agente |
| `FASE_0` … `FASE_7` | Tarefas, testes e portão de saída de cada fase | agente |
| `RELATORIO_FINAL.md` | Relatório de entrega | agente, na Fase 7 |
| `RETOMADA.md` | Onde parou em 12/11/2026, provas e próximos passos | atualizado a cada retomada |
| `GOAL_RETOMADA.md` | Texto de disparo para o próximo chat | ninguém |
| `GOAL.md` | O goal enviado ao agente (plano completo) | ninguém |

## Marcação

| Marca | Significa | Exigência |
|---|---|---|
| `[ ]` | pendente | — |
| `[~]` | em andamento | no máximo 1 por arquivo de fase (subagentes em paralelo: 1 por subagente) |
| `[x]` | concluído | no fim da linha: `— <commit> · <teste ou comando que prova>` |
| `[!]` | bloqueado por terceiro | só para item listado em `04_BLOQUEIOS.md`; no fim da linha: `— B<n>` |
| `[-]` | descartado | no fim da linha: `— motivo + prova` |

Nunca marcar `[x]` sem a evidência na linha. Nunca apagar item. Tarefa nova descoberta no caminho: acrescente com o próximo ID da fase (`F1.12`…) e anote no diário. Bug novo: nova linha em `02_PISTAS.md` (`P23`…) e teste novo em `03_TESTES.md`.

## Ciclo de trabalho

1. Ler `00_PAINEL.md` e `01_REGRAS.md`.
2. Abrir o arquivo da fase atual e pegar o primeiro `[ ]`.
3. Marcar `[~]`.
4. Escrever o teste que **falha** e guardar a saída da falha.
5. Corrigir com patch cirúrgico.
6. Rodar a suíte inteira. Verde → commit (1 assunto por commit, `git add` por caminho).
7. Marcar `[x]` com commit e teste. Atualizar `03_TESTES.md` e `02_PISTAS.md`.
8. Uma linha no `06_DIARIO.md`. Atualizar o placar do `00_PAINEL.md`.
9. Fim da fase: cumprir o **portão de saída**, commitar a pasta `plano_producao/` e fazer `git push origin master`.
10. Voltar ao passo 2 até a Fase 7 fechar.

## Retomada (perdeu contexto, sessão nova, goal reenviado)

Ler nesta ordem: `00_PAINEL.md` → `RETOMADA.md` → últimas 30 linhas de `06_DIARIO.md` → arquivo da fase atual → `git log --oneline -15` e `git status --porcelain`. Continue do primeiro `[~]` ou `[ ]`. Não refaça o que está `[x]`; se desconfiar de um `[x]`, rode o teste citado na linha.

## Quando o trabalho acaba

| Estado final | Condição |
|---|---|
| ✅ **CONCLUÍDO** | todo item de todas as fases `[x]` ou `[-]`; todo teste de `03_TESTES.md` ✅, inclusive o grupo H (SEFAZ-MT real em homologação) |
| ⏸ **AGUARDANDO TERCEIRO** | tudo `[x]`/`[-]`, exceto itens `[!]` da lista fechada de `04_BLOQUEIOS.md` |

Qualquer outro estado = o trabalho **não acabou**; continue.
