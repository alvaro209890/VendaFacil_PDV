# Painel

> Atualize este arquivo a cada item fechado. É a primeira coisa que qualquer agente lê.

| Campo | Valor |
|---|---|
| Estado geral | 🟨 EM ANDAMENTO |
| Fase atual | 4 — 23/27, com 2 itens de homologação bloqueados |
| Próxima ação | Validar duplicidade 204/539 e retomada 217, revisão fiscal F4.25 e documentação F4.26 |
| Última atualização | 2026-11-12 — reconciliados 20 itens prévios e os 3 do precheck de e037473 |
| Commit de partida | `6da6899` |
| Versão de partida → de entrega | 1.0.12 → 1.0.13 |
| Testes backend (partida → agora) | 76→432 no último registro antes da retomada; F4_RECONCILIACAO_CANCEL_GREEN.txt |
| Testes painel (partida → agora) | 7→23; navegador: 82 E2E (A28/B20/C19/XML14/U07:1) + 29 Node; build/lint 0 |

Estados gerais possíveis: ⬜ NÃO INICIADO · 🟨 EM ANDAMENTO · ⏸ AGUARDANDO TERCEIRO · ✅ CONCLUÍDO.

## Fases

| Fase | Arquivo | Status | Itens fechados | Portão de saída | Commit do fechamento |
|---|---|---|---|---|---|
| 0 | `FASE_0_linha_de_base.md` | ✅ | 9/9 | ✅ | 52c6e1e |
| 1 | `FASE_1_dinheiro_venda_estoque.md` | ✅ | 15/15 | ✅ | 05c6323 |
| 2 | `FASE_2_caixa_fiado_importacao_licenca.md` | ✅ | 23/23 | ✅ | 41c9265 |
| 3 | `FASE_3_seguranca_e_front.md` | ✅ | 24/24 | ✅ | d9038dc |
| 4 | `FASE_4_fiscal_mt.md` | 🟨 | 23/27 | ⬜ | — |
| 5 | `FASE_5_robustez_e_suporte.md` | ⬜ | 0/12 | ⬜ | — |
| 6 | `FASE_6_build_instalador_e2e.md` | ⬜ | 0/14 | ⬜ | — |
| 7 | `FASE_7_documentacao_e_entrega.md` | ⬜ | 0/12 | ⬜ | — |

Status de fase: ⬜ não iniciada · 🟨 em andamento · ✅ concluída · ⏸ concluída com item bloqueado por terceiro.

## Placar

| Controle | Total | Fechados | Bloqueados | Abertos |
|---|---|---|---|---|
| Pistas (`02_PISTAS.md`) | 51 | 43 | 0 | 8 |
| Testes (`03_TESTES.md`) | 131 | 102 | 9 | 20 |
| Bloqueios (`04_BLOQUEIOS.md`) | 9 | — | 5 ativos | — |
| Decisões do Álvaro (`05_DECISOES_ALVARO.md`) | 9 | 0 respondidas | — | 9 |

## Bloqueios ativos agora

B1–B5 bloqueiam H01–H09. Ver F4_PRECHECK_REAL.txt, F4_HOMOLOGACAO_BLOQUEADA.txt e 04_BLOQUEIOS.md.
