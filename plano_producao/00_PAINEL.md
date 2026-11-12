# Painel

> Atualize este arquivo a cada item fechado. É a primeira coisa que qualquer agente lê.

| Campo | Valor |
|---|---|
| Estado geral | 🟨 EM ANDAMENTO |
| Fase atual | 4 — bloco A/B; 7/27 (F4.1–F4.5, F4.7, F4.17) |
| Próxima ação | Fechar F4.11 (simulador: 5 RED), F4.27 (P35: 4 RED) e F4.6 (X11); depois F4.8/F4.9 e bloco B |
| Última atualização | 2026-11-12 10:15 BRT — 08bbffc/9f28f02; XSD oficial e statusServico fechados; 347 backend verdes, 9 RED de itens em andamento no working tree |
| Commit de partida | `6da6899` |
| Versão de partida → de entrega | 1.0.12 → 1.0.13 |
| Testes backend (partida → agora) | 76→347 (`pytest -q`, 12/11 10:10 BRT; +9 RED não commitados de F4.11/F4.27) |
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
| Pistas (`02_PISTAS.md`) | 46 | 32 | 0 | 14 |
| Testes (`03_TESTES.md`) | 126 | 80 | 0 | 46 |
| Bloqueios (`04_BLOQUEIOS.md`) | 9 | — | 0 ativos | — |
| Decisões do Álvaro (`05_DECISOES_ALVARO.md`) | 9 | 0 respondidas | — | 9 |

## Bloqueios ativos agora

Nenhum registrado. (Quando um item virar `[!]`, liste aqui: `B<n> — o que falta — dono`.)
