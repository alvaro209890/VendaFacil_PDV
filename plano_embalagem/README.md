# Plano — vender embalagem e unidade

Pasta deste goal. O progresso é marcado aqui. Não retomar `plano_producao/`: aquele plano é histórico e não faz parte deste trabalho.

Criado em 13/11/2026. A especificação já está fechada pelo Álvaro em `02_ESPECIFICACAO.md`. Não reabrir.

## Mapa

| Arquivo | Para quê | Quem atualiza |
|---|---|---|
| `GOAL.md` | Texto que o Álvaro cola no WhatsApp | ninguém |
| `00_PAINEL.md` | Estado, placar, próxima ação | agente, a cada item |
| `01_REGRAS.md` | Regras duras e ambiente | só se a regra mudar |
| `02_ESPECIFICACAO.md` | Regra de negócio fechada | ninguém, salvo correção de fato errado |
| `03_TESTES.md` | Matriz do que tem de passar | agente |
| `04_TAREFAS.md` | Itens em ordem | agente |
| `05_EVIDENCIAS.md` | Saídas de vermelho/verde e comandos de reprodução | agente |
| `06_DIARIO.md` | Registro corrido (só acrescenta) | agente |

## Marcação

| Marca | Significa | Exigência |
|---|---|---|
| `[ ]` | pendente | — |
| `[~]` | em andamento | no máximo 1 |
| `[x]` | concluído | no fim da linha: `— <commit> · <comando que prova>` |
| `[!]` | bloqueado | só SSH no Windows impossível, ou Actions sem permissão; escrever a prova |
| `[-]` | descartado | motivo + prova |

Nunca marcar `[x]` sem a saída do comando. Nunca apagar item. Tarefa nova: próximo ID (`E9`…) e uma linha no diário.

## Ciclo

1. Ler `00_PAINEL.md`, `01_REGRAS.md` e `02_ESPECIFICACAO.md`.
2. Pegar o primeiro `[ ]` de `04_TAREFAS.md`.
3. Marcar `[~]`.
4. Escrever o teste que falha e guardar a saída.
5. Corrigir com patch cirúrgico.
6. Suíte backend verde. Commit de um assunto, `git add` por caminho.
7. Marcar `[x]` com commit e teste. Atualizar `03_TESTES.md` e o painel.
8. Uma linha no diário.
9. No fim: portão de `04_TAREFAS.md`, push de `origin/master`, workflow verde.

## Retomada

`00_PAINEL.md` → últimas 30 linhas de `06_DIARIO.md` → `04_TAREFAS.md` → `git log --oneline -15` e `git status --porcelain`. Continue do primeiro `[~]` ou `[ ]`. Não refaça `[x]`.

## Quando acaba

| Estado | Condição |
|---|---|
| ✅ **CONCLUÍDO** | todo item `[x]` ou `[-]`; testes de `03_TESTES.md` ✅; `master` atualizado; workflow Build Windows EXE verde |
| ⏸ **PARADO** | só se o SSH neste PC falhar, ou o Actions não puder ser visto. Uma mensagem no WhatsApp com a prova |

Qualquer outro estado = não acabou.
