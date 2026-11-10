# Matriz de testes

Todo teste abaixo precisa existir, rodar e passar. Automatizado = dentro do `pytest` (ou script versionado em `scripts/`). Nada de "testei na mão".

Status: ⬜ não escrito · 🟥 escrito e falhando (antes da correção) · ✅ passando · ⛔ bloqueado (código do bloqueio) · ➖ descartado (motivo)

Ao fechar: preencha **Onde** (`arquivo::função`) e **Commit**. Teste novo que você criar fora desta lista entra no fim do grupo, com o próximo número.

## Complementos descobertos na auditoria (fase indicada em 02_PISTAS)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| V14 | P23: Validar todas as referências e retornos por usuário | ⬜ | | |
| I06 | P24: Importação atômica/idempotente e validar GTIN/modelo/embalagem | ⬜ | | |
| S09 | P25: Nunca registrar corpo bruto; sanitizar erros e exceções | ⬜ | | |
| S10 | P26: Preservar segredo omitido/vazio; remoção precisa ser explícita | ⬜ | | |
| L05 | P27: Persistir pagamento pendente e impedir segunda cobrança/venda | ⬜ | | |
| L06 | P28: Normalização ASCII, comprimento em bytes, CRC provado | ⬜ | | |
| L07 | P29: Conferir contrato de ACK e preservar pendências em resposta inválida | ⬜ | | |
| L08 | P30: Validar datas, recusar inválidas e usar fim do dia local de MT | ⬜ | | |
| U06 | P31: Parser numérico pt-BR compartilhado, sem truncamento silencioso | ⬜ | | |
| S11 | P32: Escape completo de texto/atributos; QR Base64 validado | ⬜ | | |
| E10 | P33: Esperar imagens e afterprint, ciclo testável | ⬜ | | |
| U07 | P34: Total diário pelo backend, excluindo canceladas e fuso MT | ⬜ | | |
| X14 | P35: Reserva persistente/concorrente e tratamento de falhas antes da transmissão | ⬜ | | |
| X15 | P36: Basear prazo em dhRecbto; datas fiscais em MT | ⬜ | | |
| C09 | P37: Preservar fiado visível e validar referência/estado da conta | ⬜ | | |
| I07 | P38: Cadastro do produto inteiro em uma transação | ⬜ | | |
| R10 | P39: Encerrar com segurança e identificar serviço antes de reutilizar porta | ⬜ | | |
| S12 | P40: Atualizar dependências compatíveis e validar build/lint/audit | ⬜ | | |
| S13 | P41: Bootstrap atômico, validação de senha e versão de credencial | ⬜ | | |
| S14 | P42: Validar owner antes de qualquer leitura ou transmissão | ⬜ | | |

## D — Dinheiro (Fase 1)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| D01 | Σ itens − desconto = total, com casos quebrados (0,335 kg × 12,99 · 3 × 3,33 · desconto 0,01) | ⬜ | | |
| D02 | Arredondamento de meio centavo é `ROUND_HALF_UP` (ex.: 2,675 → 2,68) em todo cálculo | ⬜ | | |
| D03 | Total da venda = Σ `vProd` − `vDesc` = `vNF` = Σ `vPag` no XML da NFC-e | ⬜ | | |
| D04 | Rateio de desconto fecha no centavo com 3, 7 e 13 itens | ⬜ | | |
| D05 | Resumo de caixa com 200 vendas de centavos quebrados bate com a soma exata | ⬜ | | |

## V — Venda, estoque e cancelamento (Fase 1)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| V01 | Exceção injetada ao gravar a venda → estoque intacto, nenhuma venda | ⬜ | | |
| V02 | Exceção injetada ao gravar a movimentação → nada gravado | ⬜ | | |
| V03 | Exceção injetada ao criar a conta a receber (fiado) → nada gravado | ⬜ | | |
| V04 | Duas requisições simultâneas no último item: uma vende, a outra é recusada; estoque termina em 0 | ⬜ | | |
| V05 | Estoque nunca fica negativo, inclusive com quantidade fracionada | ⬜ | | |
| V06 | Processo morto no meio do checkout (subprocesso) → banco íntegro e sem venda pela metade | ⬜ | | |
| V07 | Cancelar venda devolve o estoque e grava a movimentação | ⬜ | | |
| V08 | Cancelar venda fiada estorna a conta a receber; com baixa já feita, comportamento definido e testado | ⬜ | | |
| V09 | Cancelar venda com NFC-e autorizada e não cancelada → recusado com orientação | ⬜ | | |
| V10 | Cancelar duas vezes → segunda recusada; estoque não duplica | ⬜ | | |
| V11 | Venda cancelada sai do resumo do caixa, do dashboard e dos relatórios | ⬜ | | |
| V12 | Produto inativo, inexistente, quantidade 0 ou negativa → 400 | ⬜ | | |
| V13 | Venda de um usuário não é visível nem cancelável por outro | ⬜ | | |

## C — Caixa e fiado (Fase 2)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| C01 | Abrir, vender em dinheiro, sangria, suprimento, fechar: dinheiro esperado exato | ⬜ | | |
| C02 | Recebimento de fiado em dinheiro entra no dinheiro esperado do caixa | ⬜ | | |
| C03 | Baixa parcial: pendente e status corretos, histórico de pagamentos gravado | ⬜ | | |
| C04 | Pagamento maior que o pendente → recusado | ⬜ | | |
| C05 | Valor ≤ 0 em sangria, suprimento e pagamento → 400 | ⬜ | | |
| C06 | Venda de uma sessão de caixa não entra no resumo da sessão seguinte | ⬜ | | |
| C07 | Fechar caixa funciona com a licença bloqueada | ⬜ | | |
| C08 | Segundo caixa aberto pelo mesmo usuário → recusado | ⬜ | | |

## I — Importação de XML e produtos (Fase 2)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| I01 | Mesma chave de NF-e importada duas vezes não duplica estoque | ⬜ | | |
| I02 | Unidade e quantidade por embalagem convertidas corretamente | ⬜ | | |
| I03 | XML malformado ou que não é NF-e → 400, nada gravado | ⬜ | | |
| I04 | Código de barras duplicado → recusado ou unificado, sem dois produtos iguais | ⬜ | | |
| I05 | Item com `cEAN` "SEM GTIN" importa sem código de barras falso | ⬜ | | |

## L — Licença e sincronização (Fase 2)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| L01 | Modo local, sem rede: todos os fluxos funcionam | ⬜ | | |
| L02 | Painel fora do ar dentro da carência: vende normalmente | ⬜ | | |
| L03 | Licença vencida ou carência estourada: ainda fecha caixa, lê dados, exporta backup e XML fiscal | ⬜ | | |
| L04 | Painel fora do ar não atrasa o checkout (tempo medido) | ⬜ | | |

## S — Segurança (Fase 3)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| S01 | Senhas erradas seguidas → bloqueio temporário; depois da espera, a senha certa entra | ⬜ | | |
| S02 | `/registro` sem token, depois do primeiro usuário → recusado | ⬜ | | |
| S03 | Origem estranha não recebe `Access-Control-Allow-Origin` | ⬜ | | |
| S04 | `/docs` e `/openapi.json` → 404 quando empacotado | ⬜ | | |
| S05 | Leitura da configuração fiscal nunca devolve CSC, senha, `.pfx` nem token | ⬜ | | |
| S06 | Depois da suíte, o log não contém senha, token, CSC nem `.pfx` | ⬜ | | |
| S07 | Toda rota `/api/*` (fora login, registro, ativação e health) responde 401 sem token — teste percorre `app.routes` | ⬜ | | |
| S08 | Token expirado ou adulterado → 401 | ⬜ | | |

## U — Front e teclado (Fase 3)

| ID | O que prova | Status | Onde | Commit |
|---|---|---|---|---|
| U01 | Carrinho sobrevive ao F5 e é limpo ao finalizar | ⬜ | | |
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
