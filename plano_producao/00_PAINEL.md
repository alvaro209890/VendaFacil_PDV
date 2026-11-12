# Painel

> Atualize este arquivo a cada item fechado. É a primeira coisa que qualquer agente lê.

| Campo | Valor |
|---|---|
| Estado geral | 🟨 EM ANDAMENTO |
| Fase atual | 4 — bloco A/B; 7/27 (F4.1–F4.5, F4.7, F4.17) |
| Próxima ação | F4.11 (5 RED do simulador) e o cenário de cancelamento após contingência do F4.27; depois F4.6 (X11), F4.8/F4.9 |
| Última atualização | 2026-11-12 14:10 BRT — 990408c/c62400c; P35/P36 fechados (reserva e prazo); 355 backend verdes, 5 RED de F4.11 no working tree |
| Commit de partida | `6da6899` |
| Versão de partida → de entrega | 1.0.12 → 1.0.13 |
| Testes backend (partida → agora) | 76→355 (`pytest -q`, 12/11 14:05 BRT; +5 RED não commitados de F4.11) |
| Testes painel (partida → agora) | 7→23; navegador: 82 E2E (A28/B20/C19/XML14/U07:1) + 29 Node; build/lint 0 |

Estados gerais possíveis: ⬜ NÃO INICIADO · 🟨 EM ANDAMENTO · ⏸ AGUARDANDO TERCEIRO · ✅ CONCLUÍDO.

## Fases

| Fase | Arquivo | Status | Itens fechados | Portão de saída | Commit do fechamento |
|---|---|---|---|---|---|
| 0 | `FASE_0_linha_de_base.md` | ✅ | 9/9 | ✅ | 52c6e1e |
| 1 | `FASE_1_dinheiro_venda_estoque.md` | ✅ | 15/15 | ✅ | 05c6323 |
| 2 | `FASE_2_caixa_fiado_importacao_licenca.md` | ✅ | 23/23 | ✅ | 41c9265 |
| 3 | `FASE_3_seguranca_e_front.md` | ✅ | 24/24 | ✅ | d9038dc |
| 4 | `FASE_4_fiscal_mt.md` | 🟨 | 7/27 | ⬜ | — |
| 5 | `FASE_5_robustez_e_suporte.md` | ⬜ | 0/12 | ⬜ | — |
| 6 | `FASE_6_build_instalador_e2e.md` | ⬜ | 0/14 | ⬜ | — |
| 7 | `FASE_7_documentacao_e_entrega.md` | ⬜ | 0/12 | ⬜ | — |

Status de fase: ⬜ não iniciada · 🟨 em andamento · ✅ concluída · ⏸ concluída com item bloqueado por terceiro.

## Placar

| Controle | Total | Fechados | Bloqueados | Abertos |
|---|---|---|---|---|
| Pistas (`02_PISTAS.md`) | 46 | 34 | 0 | 12 |
| Testes (`03_TESTES.md`) | 126 | 81 | 0 | 45 |
| Bloqueios (`04_BLOQUEIOS.md`) | 9 | — | 0 ativos | — |
| Decisões do Álvaro (`05_DECISOES_ALVARO.md`) | 9 | 0 respondidas | — | 9 |

## Bloqueios ativos agora

Nenhum registrado. (Quando um item virar `[!]`, liste aqui: `B<n> — o que falta — dono`.)
