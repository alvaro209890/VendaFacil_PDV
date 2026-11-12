# Painel

> Atualize este arquivo a cada item fechado. É a primeira coisa que qualquer agente lê.

| Campo | Valor |
|---|---|
| Estado geral | 🟨 EM ANDAMENTO |
| Fase atual | 3 — 21/24; faltam F3.19 (U07), F3.21 (S13) e F3.22 (S14) |
| Próxima ação | F3.22 (owner fiscal) → F3.21 (bootstrap/revogação no painel) → F3.19 (total diário), depois portão da fase e push |
| Última atualização | 2026-11-12 10:00 BRT — b265950 publicado; F3.16/U06/P31 e Fase 2 fechados, E2E 81/81 em 4 lotes |
| Commit de partida | `6da6899` |
| Versão de partida → de entrega | 1.0.12 → 1.0.13 |
| Testes backend (partida → agora) | 76→315 (`pytest -q`, 12/11 09:12 BRT) |
| Testes painel (partida → agora) | 7→9; navegador: 81 E2E em 4 lotes (A28/B20/C19/XML14) + 29 Node; build/lint 0 |

Estados gerais possíveis: ⬜ NÃO INICIADO · 🟨 EM ANDAMENTO · ⏸ AGUARDANDO TERCEIRO · ✅ CONCLUÍDO.

## Fases

| Fase | Arquivo | Status | Itens fechados | Portão de saída | Commit do fechamento |
|---|---|---|---|---|---|
| 0 | `FASE_0_linha_de_base.md` | ✅ | 9/9 | ✅ | 52c6e1e |
| 1 | `FASE_1_dinheiro_venda_estoque.md` | ✅ | 15/15 | ✅ | 05c6323 |
| 2 | `FASE_2_caixa_fiado_importacao_licenca.md` | ✅ | 23/23 | ✅ | 41c9265 |
| 3 | `FASE_3_seguranca_e_front.md` | 🟨 | 21/24 | ⬜ | — |
| 4 | `FASE_4_fiscal_mt.md` | ⬜ | 0/27 | ⬜ | — |
| 5 | `FASE_5_robustez_e_suporte.md` | ⬜ | 0/12 | ⬜ | — |
| 6 | `FASE_6_build_instalador_e2e.md` | ⬜ | 0/14 | ⬜ | — |
| 7 | `FASE_7_documentacao_e_entrega.md` | ⬜ | 0/12 | ⬜ | — |

Status de fase: ⬜ não iniciada · 🟨 em andamento · ✅ concluída · ⏸ concluída com item bloqueado por terceiro.

## Placar

| Controle | Total | Fechados | Bloqueados | Abertos |
|---|---|---|---|---|
| Pistas (`02_PISTAS.md`) | 46 | 28 | 0 | 18 |
| Testes (`03_TESTES.md`) | 126 | 67 | 0 | 59 |
| Bloqueios (`04_BLOQUEIOS.md`) | 9 | — | 0 ativos | — |
| Decisões do Álvaro (`05_DECISOES_ALVARO.md`) | 9 | 0 respondidas | — | 9 |

## Bloqueios ativos agora

Nenhum registrado. (Quando um item virar `[!]`, liste aqui: `B<n> — o que falta — dono`.)
