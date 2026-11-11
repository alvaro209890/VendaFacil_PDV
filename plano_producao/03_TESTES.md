# Matriz de testes

Todo teste abaixo precisa existir, rodar e passar. Automatizado = dentro do `pytest` (ou script versionado em `scripts/`). Nada de "testei na mão".

Status: ⬜ não escrito · 🟥 escrito e falhando (antes da correção) · ✅ passando · ⛔ bloqueado (código do bloqueio) · ➖ descartado (motivo)

Ao fechar: preencha **Onde** (`arquivo::função`) e **Commit**. Teste novo que você criar fora desta lista entra no fim do grupo, com o próximo número.

## Complementos descobertos na auditoria (fase indicada em 02_PISTAS)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| V14 | P23: Validar todas as referências e retornos por usuário | ✅ | `backend/tests/test_referencias.py` | c7e3991 |
| I06 | P24: Importação atômica/idempotente e validar GTIN/modelo/embalagem | ✅ | `test_importacao_atomica.py` + `test_importacao_parser.py` + `test_importacao_regras.py`; falhas/concorrência/schema e HTTP400 | 00e709d/5b8f0f2 |
| S09 | P25: Nunca registrar corpo bruto; sanitizar erros e exceções | ⬜ | | |
| S10 | P26: Preservar segredo omitido/vazio; remoção precisa ser explícita | ⬜ | | |
| L05 | P27: Persistir pagamento pendente e impedir segunda cobrança/venda | ✅ | `backend/tests/test_cobranca_pendente.py` | b633307 |
| L06 | P28: Normalização ASCII, comprimento em bytes, CRC provado | ✅ | `backend/tests/test_pix_emv.py` | 3227373 |
| L07 | P29: Conferir contrato de ACK e preservar pendências em resposta inválida | ✅ | `test_sync_ack.py` + `test_sync_ack_invalido.py`: parcial, inválidos/schema, retry e legado | 46244a9/40f49e7 |
| L08 | P30: Validar datas, recusar inválidas e usar fim do dia local de MT | ✅ | `painel/tests/test_licenca_data.py` | f1aeec4 |
| U06 | P31: Parser numérico pt-BR compartilhado, sem truncamento silencioso | ⬜ | | |
| S11 | P32: Escape completo de texto/atributos; QR Base64 validado | ⬜ | | |
| E10 | P33: Esperar imagens e afterprint, ciclo testável | ⬜ | | |
| U07 | P34: Total diário pelo backend, excluindo canceladas e fuso MT | ⬜ | | |
| X14 | P35: Reserva persistente/concorrente e tratamento de falhas antes da transmissão | ⬜ | | |
| X15 | P36: Basear prazo em dhRecbto; datas fiscais em MT | ⬜ | | |
| C09 | P37: Preservar fiado visível e validar referência/estado da conta | ✅ | `backend/tests/test_cliente_divida.py + test_adversario_caixa.py` | e1ad5e2/be78390 |
| I07 | P38: Cadastro do produto inteiro em uma transação | ✅ | `backend/tests/test_produto_atomico.py` | 7dee50a |
| R10 | P39: Encerrar com segurança e identificar serviço antes de reutilizar porta | ⬜ | | |
| S12 | P40: Atualizar dependências compatíveis e validar build/lint/audit | ⬜ | | |
| S13 | P41: Bootstrap atômico, validação de senha e versão de credencial | ⬜ | | |
| S14 | P42: Validar owner antes de qualquer leitura ou transmissão | ⬜ | | |

## D — Dinheiro (Fase 1)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| D01 | Σ itens − desconto = total, com casos quebrados (0,335 kg × 12,99 · 3 × 3,33 · desconto 0,01) | ✅ | `backend/tests/test_dinheiro.py::test_d01_soma_subtotais_e_desconto` e `test_checkout_dinheiro_half_up` | 52bb220 |
| D02 | Arredondamento de meio centavo é `ROUND_HALF_UP` (ex.: 2,675 → 2,68) em todo cálculo | ✅ | `backend/tests/test_dinheiro.py + test_dinheiro_db.py + test_dinheiro_fiscal.py (HALF_UP)` | 2a9b689 |
| D03 | Total da venda = Σ `vProd` − `vDesc` = `vNF` = Σ `vPag` no XML da NFC-e | ✅ | `backend/tests/test_dinheiro_fiscal.py::test_d03_xml_bate_com_checkout_no_meio_centavo` | 2a9b689 |
| D04 | Rateio de desconto fecha no centavo com 3, 7 e 13 itens | ✅ | `backend/tests/test_dinheiro_fiscal.py::test_d04_rateio_sem_residuo_negativo` | 2a9b689 |
| D05 | Resumo de caixa com 200 vendas de centavos quebrados bate com a soma exata | ✅ | `backend/tests/test_dinheiro_db.py::test_d05_resumo_200_vendas_exato` | d798762 |
| D06 | D3 caracterizada: preço de venda 0 cobra o custo; preço positivo não muda | ✅ | `backend/tests/test_cancelamento.py::test_d3_preco_zero_vende_pelo_custo` | 997dd69 |

## V — Venda, estoque e cancelamento (Fase 1)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| V01 | Exceção injetada ao gravar a venda → estoque intacto, nenhuma venda | ✅ | `backend/tests/test_transacoes.py::test_v01_v03_checkout_rollback_em_qualquer_etapa` | 68fcc88 |
| V02 | Exceção injetada ao gravar a movimentação → nada gravado | ✅ | `backend/tests/test_transacoes.py::test_v01_v03_checkout_rollback_em_qualquer_etapa` | 68fcc88 |
| V03 | Exceção injetada ao criar a conta a receber (fiado) → nada gravado | ✅ | `backend/tests/test_transacoes.py::test_v01_v03_checkout_rollback_em_qualquer_etapa` | 68fcc88 |
| V04 | Duas requisições simultâneas no último item: uma vende, a outra é recusada; estoque termina em 0 | ✅ | `backend/tests/test_transacoes.py::test_v04_api_concorrente_ultimo_item + test_v04_duas_conexoes_begin_immediate` | 79e5ccf |
| V05 | Estoque nunca fica negativo, inclusive com quantidade fracionada | ✅ | `backend/tests/test_transacoes.py::test_v05_fracionado_e_itens_duplicados_nao_negativam` | 79e5ccf |
| V06 | Processo morto no meio do checkout (subprocesso) → banco íntegro e sem venda pela metade | ✅ | `backend/tests/test_transacoes.py::test_v06_processo_morto_no_meio_do_checkout` | 15c7fb9 |
| V07 | Cancelar venda devolve o estoque e grava a movimentação | ✅ | `backend/tests/test_cancelamento.py::test_v07_v10_cancelar_devolve_estoque_uma_vez` | 4a7ff3e |
| V08 | Cancelar venda fiada estorna a conta a receber; com baixa já feita, comportamento definido e testado | ✅ | `backend/tests/test_cancelamento.py::test_v08_fiado_estorno_ou_recusa_recebido` | 4a7ff3e |
| V09 | Cancelar venda com NFC-e autorizada e não cancelada → recusado com orientação | ✅ | `backend/tests/test_cancelamento_fiscal.py` | 197dcee |
| V10 | Dois cancelamentos simultâneos da mesma venda → estoque devolvido só uma vez | ✅ | `backend/tests/test_cancelamento.py::test_v10_cancelamento_concorrente_uma_devolucao` | 4a7ff3e |
| V11 | Venda cancelada sai do resumo do caixa, do dashboard e dos relatórios | ✅ | `backend/tests/test_cancelamento.py::test_v11_cancelada_sai_dos_totais` | fd35f52 |
| V12 | Produto inativo, inexistente, quantidade 0 ou negativa → 400 | ✅ | `backend/tests/test_transacoes.py::test_v12_quantidade_invalida_retorna_400 + test_v12_produto_invalido_400` | 79e5ccf |
| V13 | Venda de um usuário não é visível nem cancelável por outro | ✅ | `backend/tests/test_cancelamento.py::test_v13_cancelamento_alheio_404 + test_transacoes.py::test_v13_venda_nao_visivel_a_outro_usuario` | 4a7ff3e |

| V15 | PRAGMAs explícitos init/reconexão, FK recusa referência inexistente, cópia legada válida preserva dados | ✅ | `backend/tests/test_transacoes.py` (3 testes P7) | a4f8e69 |

| V16 | Quantidade/desconto infinitos recusados antes de calcular, sem500 nem escrita | ✅ | `backend/tests/test_transacoes.py::test_v16_infinito_recusado_sem_erro_500` | 79e5ccf |

## C — Caixa e fiado (Fase 2)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| C01 | Abrir, vender em dinheiro, sangria, suprimento, fechar: dinheiro esperado exato | ✅ | `backend/tests/test_caixa_sessao.py::test_c01_esperado_bate_com_gaveta` | 320bc56 |
| C02 | Recebimento de fiado em dinheiro entra no dinheiro esperado do caixa | ✅ | `backend/tests/test_fiado_caixa.py` | 7c56670 |
| C03 | Baixa parcial: pendente e status corretos, histórico de pagamentos gravado | ✅ | `backend/tests/test_fiado_historico.py` | 2fbd5e1 |
| C04 | Pagamento maior que o pendente → recusado | ✅ | `backend/tests/test_fiado_limites.py` | 4033835 |
| C05 | Valor ≤ 0 em sangria, suprimento e pagamento → 400 | ✅ | `backend/tests/test_caixa_limites.py + test_fiado_limites.py` | 85a3abf/4033835 |
| C06 | Venda de uma sessão de caixa não entra no resumo da sessão seguinte | ✅ | `backend/tests/test_caixa_sessao.py::test_c06_venda_nao_entra_na_sessao_seguinte` | 320bc56 |
| C07 | Fechar caixa funciona com a licença bloqueada | ✅ | `backend/tests/test_licenca_bloqueada.py::test_c07_api_nao_recusa_caixa_leitura_backup_xml` | b247f2b |
| C08 | Segundo caixa aberto pelo mesmo usuário → recusado | ✅ | `backend/tests/test_caixa_limites.py::test_c08_segundo_caixa_recusado` | 85a3abf |

## I — Importação de XML e produtos (Fase 2)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| I01 | Mesma chave de NF-e importada duas vezes não duplica estoque | ✅ | `backend/tests/test_importacao_chave.py` | 781f6cd |
| I02 | Unidade e quantidade por embalagem convertidas corretamente | ✅ | `backend/tests/test_importacao_regras.py (3 casos de embalagem)` | 18c590d |
| I03 | XML malformado ou que não é NF-e → 400, nada gravado | ✅ | `backend/tests/test_importacao_regras.py::test_i03_xml_invalido_nao_grava` | 18c590d |
| I04 | Código de barras duplicado → recusado ou unificado, sem dois produtos iguais | ✅ | `backend/tests/test_importacao_regras.py::test_i04_codigo_repetido_nao_cria_outro_produto` | 18c590d |
| I05 | Item com `cEAN` "SEM GTIN" importa sem código de barras falso | ✅ | `backend/tests/test_importacao_regras.py::test_i05_sem_gtin_nao_grava_codigo_falso` | 18c590d |

## L — Licença e sincronização (Fase 2)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| L01 | Modo local, sem rede: todos os fluxos funcionam | ⬜ | Checkout offline em test_licenca.py; roteiro completo de todos os fluxos ainda pendente | be1efa7 (parcial) |
| L02 | Painel fora do ar dentro da carência: vende normalmente | ✅ | `backend/tests/test_licenca.py::test_l02_painel_fora_vende_na_carencia` | be1efa7 |
| L03 | Licença vencida ou carência estourada: ainda fecha caixa, lê dados, exporta backup e XML fiscal | ✅ | `backend/tests/test_licenca_bloqueada.py (UI + API)` | b247f2b |
| L04 | Painel fora do ar não atrasa o checkout (tempo medido) | ✅ | `backend/tests/test_licenca.py::test_l04_painel_fora_nao_atrasa_checkout` | 3e8f1a4 |

## S — Segurança (Fase 3)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| S01 | Senhas erradas seguidas → bloqueio temporário; depois da espera, a senha certa entra | ✅ | `backend/tests/test_login_limite.py` | 3544de8 |
| S02 | `/registro` sem token, depois do primeiro usuário → recusado | ✅ | `backend/tests/test_registro_fechado.py` | ac2f81e |
| S03 | Origem estranha não recebe `Access-Control-Allow-Origin` | ✅ | `backend/tests/test_cors.py` | 433ff7c |
| S04 | `/docs` e `/openapi.json` → 404 quando empacotado | ✅ | `backend/tests/test_docs_empacotado.py (flag empacotado; exe real na F6)` | 88a4ca2 |
| S05 | Leitura da configuração fiscal nunca devolve CSC, senha, `.pfx` nem token | ✅ | `backend/tests/test_segredos_config.py::test_s05_leitura_nao_devolve_segredo` | c7ff77c |
| S06 | Depois da suíte, o log não contém senha, token, CSC nem `.pfx` | ✅ | `backend/tests/test_segredos_config.py::test_s06_log_nao_grava_segredo (payload JSON fiscal; bytes em S09 ainda pendente)` | c7ff77c |
| S07 | Toda rota `/api/*` (fora login, registro, ativação e health) responde 401 sem token — teste percorre `app.routes` | ✅ | `backend/tests/test_rotas_sem_token.py (inclui heartbeat público)` | a7a398d |
| S08 | Token expirado ou adulterado → 401 | ✅ | `backend/tests/test_rotas_sem_token.py` | a7a398d |

## U — Front e teclado (Fase 3)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| U01 | Carrinho sobrevive ao F5 e é limpo ao finalizar | ✅ | `e2e/carrinho.spec.ts` (5 casos Chromium real, `F3_09_E2E.txt`) | 1a23906 |
| U02 | Venda inteira só com teclado: código + Enter (3 itens), F2, confirmar | ⬜ | | |
| U03 | Quantidade e desconto aceitam `1,5` e `1.5` | ⬜ | | |
| U04 | Foco volta ao campo de código depois de adicionar, finalizar e fechar janela | ⬜ | | |
| U05 | `npm run build` e `npx eslint .` sem erro | ⬜ | | |

## X — Fiscal offline, sem SEFAZ (Fase 4, bloco A)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| X01 | XML da NFC-e em dinheiro valida no XSD oficial 4.00 | ⬜ | | |
| X02 | Idem para cartão integrado, PIX, fiado, desconto, CPF na nota e item com ST/monofásico | ⬜ | | |
| X03 | XML da NF-e modelo 55 valida no XSD | ⬜ | | |
| X04 | Evento de cancelamento valida no XSD | ⬜ | | |
| X05 | Pedido de inutilização valida no XSD | ⬜ | | |
| X06 | Assinatura XMLDSig confere com a chave pública; 1 byte alterado invalida; algoritmos iguais aos do MOC | ⬜ | | |
| X07 | QR Code 2.00 online: hash do CSC recalculado e cada parâmetro conferido | ⬜ | | |
| X08 | QR Code de contingência: idem, com os campos do modo offline | ⬜ | | |
| X09 | `dhEmi` em −04:00; chave usa o AAMM do `dhEmi`; virada de mês às 23h30 locais | ⬜ | | |
| X10 | `tpAmb` vem só da configuração; em homologação o XML leva o texto obrigatório de "sem valor fiscal" exigido pelo MOC | ⬜ | | |
| X11 | Prazo de cancelamento (30 min NFC-e, 2 h NF-e) contado no fuso certo | ⬜ | | |
| X12 | Numeração sequencial sem buraco sob concorrência; rejeição não queima número sem tratamento | ⬜ | | |
| X13 | Com `sefaz_mt_direto` configurado, nenhum caminho cai em FocusNFe/PlugNotas | ⬜ | | |

## M — Fiscal com simulador local da SEFAZ (Fase 4, bloco B)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| M01 | Autorizada (cStat 100): nota autorizada, XML com protocolo guardado | ⬜ | | |
| M02 | Rejeição: venda preservada, nota rejeitada, mensagem clara, reemissão possível | ⬜ | | |
| M03 | Duplicidade: consulta e concilia sem criar segunda nota | ⬜ | | |
| M04 | Timeout: vira contingência (`tpEmis` 9), cupom marcado, loop transmite depois | ⬜ | | |
| M05 | HTTP 500/503: mesmo comportamento do timeout | ⬜ | | |
| M06 | Lote em processamento: reconsulta até autorizar | ⬜ | | |
| M07 | Autorização fora de prazo (cStat 150) tratada como autorizada | ⬜ | | |
| M08 | Cancelamento: evento homologado muda o status; evento rejeitado não muda | ⬜ | | |
| M09 | Inutilização homologada | ⬜ | | |
| M10 | `statusServico` em operação (cStat 107) e fora de operação | ⬜ | | |
| M11 | Reinício do processo com nota pendente: o loop retoma e não duplica | ⬜ | | |
| M12 | Três vendas seguidas sem rede → três contingências → três autorizadas ao voltar | ⬜ | | |

## H — SEFAZ-MT real, homologação (Fase 4, bloco C) — exige B1, B2, B3 e B4

Marker `homologacao`, fora da execução padrão. Sem os itens da loja: ⛔ com o código do bloqueio.

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| H01 | `statusServico` da SEFAZ-MT em homologação responde em operação | ⬜ | | |
| H02 | NFC-e em dinheiro autorizada | ⬜ | | |
| H03 | NFC-e em cartão com vínculo de pagamento autorizada | ⬜ | | |
| H04 | NFC-e em PIX autorizada | ⬜ | | |
| H05 | NFC-e com desconto autorizada | ⬜ | | |
| H06 | Cancelamento dentro do prazo homologado | ⬜ | | |
| H07 | Contingência real (rede cortada) e transmissão ao voltar | ⬜ | | |
| H08 | Consulta do QR Code no portal de homologação abre a nota | ⬜ | | |
| H09 | Inutilização homologada | ⬜ | | |

## R — Robustez (Fase 5)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| R01 | Backup automático gera arquivo que passa no `integrity_check` | ⬜ | | |
| R02 | Retenção mantém só os N mais recentes | ⬜ | | |
| R03 | Restauração em banco novo: contagens de produtos, vendas, clientes e notas iguais | ⬜ | | |
| R04 | Arquivo corrompido ou que não é do VendaFácil → recusado; banco atual intacto | ⬜ | | |
| R05 | Banco corrompido na abertura → sistema sobe em modo consulta e avisa | ⬜ | | |
| R06 | Backup durante vendas concorrentes não trava nem corrompe | ⬜ | | |
| R07 | Log rotaciona e fica em `logs/` dentro da pasta de dados | ⬜ | | |
| R08 | Diagnóstico devolve todos os campos e nenhum segredo | ⬜ | | |
| R09 | Segunda instância do `.exe` abre o navegador na que já está rodando | ⬜ | | |

## E — Ponta a ponta no `.exe` e instalador (Fase 6)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| E01 | Smoke no `.exe`: `/` 200 · `/health` 200 · `/api/produtos` 401 | ⬜ | | |
| E02 | Roteiro de `docs/TESTE_WINDOWS.md` em script contra o `.exe`: zero resposta 500 | ⬜ | | |
| E03 | Mesmo roteiro sem rede: vender, cancelar, fechar caixa, reimprimir; religar e conciliar | ⬜ | | |
| E04 | Instalação limpa: pasta do programa, atalhos, primeira execução, banco em `%LOCALAPPDATA%` | ⬜ | | |
| E05 | Instalar a 1.0.13 por cima da anterior preserva os dados (contagens iguais) | ⬜ | | |
| E06 | Desinstalar preserva os dados | ⬜ | | |
| E07 | Cupom em 58 mm (PDF): acentuação, QR legível, chave, protocolo | ⬜ | | |
| E08 | Cupom em 80 mm (PDF) e segunda via | ⬜ | | |
| E09 | Cupom de contingência com a marcação "emitida em contingência" | ⬜ | | |
