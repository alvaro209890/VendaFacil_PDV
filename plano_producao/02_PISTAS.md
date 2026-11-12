# Pistas — bugs e lacunas vistos no código

Lidas em 10/11/2026 no commit `6da6899`. **Cada linha é pista, não bug provado.** Fluxo: escrever o teste que falha → corrigir → commit → fechar a linha.

Status: ⬜ aberta · 🟨 em andamento · ✅ corrigida (commit + teste) · ➖ descartada (com prova) · 🟦 decisão do Álvaro (padrão aplicado)

| # | Grav. | Onde | O que foi visto | O que fazer | Fase | Status | Commit · teste |
|---|---|---|---|---|---|---|---|
| P1 | 🔴 | `vendas.py:109-161` | Checkout em 4+ transações separadas (`baixar_estoque` por item → `create_venda` → `registrar_movimentacao` → `create_conta_receber`). Queda no meio deixa estoque baixado sem venda ou fiado sem conta | Uma função única em `database.py`, numa transação (`BEGIN IMMEDIATE`) | 1 | ✅ corrigida | 68fcc88 / 79e5ccf / 15c7fb9 · V01–V06 (rollback, concorrência, queda) |
| P2 | 🔴 | backend inteiro | **Não existe cancelamento/estorno de venda** (só cancelar conta a receber e cancelar NFC-e) | `POST /api/vendas/{id}/cancelar` + tela em `src/pages/Vendas.tsx` | 1 | ✅ corrigida | 4a7ff3e / 197dcee / fd35f52 · V07–V11 |
| P3 | 🔴 | schema em `database.py`; `vendas.py:63-103` | Dinheiro em `REAL`, soma em `float` com `round()` (55 ocorrências; `Decimal` só em `mercadopago.py`) | Módulo único de dinheiro com `Decimal` + `ROUND_HALF_UP` usado por venda, caixa, fiado e XML | 1 | ✅ corrigida | 3fe1aa4/52bb220/d798762/2a9b689 · D01–D05 e101 testes |
| P4 | 🟠 | `database.py:824-866` | Caixa soma vendas por janela de tempo, sem `sessao_id`; venda é aceita sem caixa aberto | Garantir que sessões não se misturam; aviso de caixa fechado (ver D4) | 2 | ✅ corrigida | 320bc56/2629af3 · C01/C06/D4; suíte274 e cobertura realF3.13 |
| P5 | 🟠 | `auth.py:123-179`, `main.py:54` | Login local sem limite de tentativas; `/registro` aberto em modo local com CORS `*`; senha mínima 4; token de 30 dias | Limite de tentativas; fechar `/registro` após o 1º usuário; CORS restrito | 3 | ✅ corrigida | 3544de8/ac2f81e/433ff7c/ebc8390 · S01–S03 e test_senha; política/token em SEGURANCA.md |
| P6 | 🟠 | `main.py` | `/docs` e `/openapi.json` expostos no `.exe` | Desligar quando empacotado (`sys.frozen`) | 3 | ✅ corrigida | 88a4ca2 · S04 flag empacotado; confirmação no exe real fica na F6 |
| P7 | 🟠 | `database.py:15-18` | Conexão única + `RLock`, WAL; `foreign_keys=0`; `busy_timeout=5000` e `synchronous=2` já existem por padrão (medido na Fase 0) | Definir os PRAGMAs e provar com teste de concorrência | 1 | ✅ corrigida | a4f8e69 · V15 / PRAGMAs e cópia legada válidos |
| P8 | 🟠 | `backup.py:44-58`, `:114-121`; `database.py:1353` | Loop de backup engole exceção sem log; sem `integrity_check`; restauração aceita qualquer `.db` que abra | `integrity_check`, validação de schema, log, modo consulta com banco corrompido | 5 | ✅ corrigida | 73ae8f2/1979b2e/1ee3df3/15696f5 · R01–R06, cópia íntegra e recuperação |
| P9 | 🟠 | `backend/tests/` | Sem XSD, sem validação de schema, sem marker `homologacao`, sem `pytest.ini` | Fase 4, bloco A e C | 4 | ✅ corrigida | 08bbffc/e037473 · X01–X10 verdes no XSD oficial e marker homologacao separa 9 cenários |
| P10 | 🟠 | `src/pages/PDV.tsx` | Carrinho só em memória (F5 perde a venda); atalhos só F2/F4 | Persistir carrinho; revisar teclado | 3 | ✅ corrigida | 1a23906/dc0858d · persistência e atalhos; três SKUs só no teclado |
| P11 | 🟡 | `vendas.py:81` | Produto com preço de venda 0 é vendido pelo custo, em silêncio | Decisão D3 | 1 | ✅ mantida por D3 | 997dd69 · caracterização, sem mudança de código |
| P12 | 🟡 | `src/lib/recibo.ts` | Impressão é pelo navegador; não há ESC/POS, RAW nem gaveta | Validar cupom 58/80 mm em PDF; decisão D5 | 6 | 🟦 D5 aplicada | ee491d5/b41e946 · E07–E09/E11 em PDF; impressão segue pelo navegador; papel em B7 |
| P13 | 🟡 | `main.py:102` | Só existe `/health`; não há diagnóstico para o suporte | Endpoint autenticado + tela | 5 | ✅ corrigida | f25d05f/aa2ea37 · R08 API protegida e clipboard Chromium |
| P14 | 🟡 | `fiscal_config.py:12` | `_SENSIVEIS` mascarados na leitura, em claro no SQLite | Teste de não vazamento + decisão D6 escrita | 3 | ✅ máscara comprovada; D6 documentada | c7ff77c/f9d8ad1 · S05/S06 JSON; caso bytes/log bruto continua aberto em P25 |
| P15 | 🟡 | `auth.py:93`, `fiscal.py:352-376`, `fiscal_direto.py:83` | Timestamps de venda em UTC; fiscal usa `agora_mt()`. MT é UTC−4 | Testar `dhEmi`, prazo de cancelamento e "vendas de hoje" entre 20h e 24h locais | 4 | ✅ conferida | 08bbffc/4e52786/fb9f5b9 · X09/X11 e U07, viradas de dia/mês em MT |
| P16 | 🟡 | git | 4 binários trackeados apesar do `.gitignore`; `CLAUDE.md` diz o contrário | Só relatar (decisão D2) | 7 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P17 | 🟡 | `installer/vendafacil.iss:44` | `PrivilegesRequired=admin`: instalar exige UAC | Fase 6; sem elevação → B8 | 6 | ✅ teste pronto; execução ⛔ B8 | b41e946 · `scripts/teste_instalador.ps1`; F6_INSTALADOR_B8.txt saída 2 |
| P18 | 🟡 | `CLAUDE.md` | Cita build pelo GitHub Actions | Não depender do CI; corrigir o doc se o Actions estiver fora | 7 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P19 | 🟠 | `fiscal_direto.py` (comentário na linha 1085) | **Não há inutilização de numeração** (serviço `NfeInutilizacao4` ausente do dicionário de webservices, linhas 37-42) | Conferir no MOC/SEFAZ-MT a exigência atual para NFC-e e implementar; provar que rejeição não deixa buraco | 4 | ✅ corrigida | 5980fe4/8c83d0f/31a4e5c/60a99ad · X05/M09/X12, API e 4 testes Chromium |
| P20 | 🟡 | `fiscal_direto.py:37-42` | **Não há `statusServico`** (`NfeStatusServico4`) | Implementar; usar no diagnóstico e no harness de homologação | 4 | ✅ corrigida | 9f28f02 · `statusServico` 65/55 homologação e produção, rota + tela Fiscal; M10 |
| P21 | 🟠 | `database.py:1096-1115` | Baixa de fiado: valor maior que o pendente é engolido sem aviso; não há histórico dos pagamentos; não lança no caixa | Tabela de pagamentos, recusa de excedente, lançamento no caixa quando em dinheiro | 2 | ✅ corrigida | 2fbd5e1/4033835/7c56670/12f1994 · C02–C05, histórico e recusa de excedente |
| P22 | 🟡 | `fiscal.py:42`, `:134` | Três caminhos de emissão: SEFAZ-MT direto, FocusNFe e PlugNotas (legados) | O caminho da mercearia é `sefaz_mt_direto`. Não remover os legados; garantir que nenhum é escolhido por engano | 4 | ✅ conferida | 4e52786 · X13:55/65, emissão/consulta/loop/cancelamento sem gateway |

| P23 | 🟠 | `vendas.py:55; database.py:969` | Cliente de outro usuário aceito no checkout não fiado; update_categoria retorna registro sem filtro de proprietário | Validar todas as referências e retornos por usuário | 1 | ✅ corrigida | c7e3991 · V14; checkout já recusava, retorno da categoria vazava |
| P24 | 🟠 | `produtos.py:221; importacao_xml.py:49` | XML sem deduplicação persistente por chave; barcode sem unicidade; modelo de entrada sem validação | Importação atômica/idempotente e validar GTIN/modelo/embalagem | 2 | ✅ | 00e709d/5b8f0f2 · atomicidade+GTIN/modelo/números+embalagens comprovados |
| P25 | 🟠 | `errors.py:106,234` | Payload inválido em bytes pode registrar segredo no log | Nunca registrar corpo bruto; sanitizar erros e exceções | 3 | ✅ corrigida | 5da31fa ·6RED→10GREEN,315backend/9painel;review deleg_0911d189 aprovada |
| P26 | 🟠 | `fiscal_config.py:95; mercadopago.py:370` | Reenviar config mascarada com campo sensível vazio apaga credencial | Preservar segredo omitido/vazio; remoção precisa ser explícita | 3 | ✅ corrigida | 6535b18 ·31novoscasos,máscaras/literal/clearwhitelist,revisãoaprovada |
| P27 | 🟠 | `PDV.tsx:384; mercadopago.py` | Cobrança aprovada perde comprovante se checkout falhar; falta conciliação idempotente | Persistir pagamento pendente e impedir segunda cobrança/venda | 2 | ✅ corrigida | b633307 · L05, cobrança aprovada persistida e idempotente |
| P28 | 🟠 | `pix.py:97` | Nome/cidade com acentos produz TLV EMV incompatível | Normalização ASCII, comprimento em bytes, CRC provado | 2 | ✅ corrigida | 3227373 · L06, PIX ASCII e CRC |
| P29 | 🟠 | `sync_client.py:30,57` | HTTP 200 marca todas vendas sincronizadas sem confirmar aceitação | Conferir contrato de ACK e preservar pendências em resposta inválida | 2 | ✅ | 46244a9/40f49e7 · ACK parcial/legado/inválido preserva fila; 17 casos novos |
| P30 | 🟠 | `painel/main.py:54; painel/static/index.html:348` | Data inválida torna licença perpétua e data UTC expira antes do fim do dia MT | Validar datas, recusar inválidas e usar fim do dia local de MT | 2 | ✅ corrigida | f1aeec4 · L08, datas válidas e fim do dia MT |
| P31 | 🟠 | `PDV.tsx; ContasReceber.tsx:87; Caixa.tsx:33; Produtos.tsx:182` | Vírgula rejeitada/truncada em fiado, caixa, quantidade, desconto e embalagem | Parser numérico pt-BR compartilhado, sem truncamento silencioso | 3 | ✅ corrigida | a6a90d5 · `src/lib/numeros.ts` em caixa/fiado/produtos/PDV/XML; U06 e 81 E2E em 4 lotes |
| P32 | 🟠 | `recibo.ts:83,91,108,115` | Interpolação de forma/id/numero/serie/QR sem escape permite HTML/script | Escape completo de texto/atributos; QR Base64 validado | 3 | ✅ corrigida | 95e2322 ·escapeforma/id/numero/serie,allowlistQR,7DOMgreen;review aprovado |
| P33 | 🟠 | `recibo.ts:168–171` | Iframe removido por timer antes de terminar impressão | Esperar imagens e afterprint, ciclo testável | 6 | ✅ corrigida | eb55f20 · E10 (F6_E10_RED/GREEN) |
| P34 | 🟠 | `Vendas.tsx:89–96` | Total do dia truncado nos primeiros 100 registros | Total diário pelo backend, excluindo canceladas e fuso MT | 3 | ✅ corrigida | fb9f5b9 · U07:4 backend + 1 UI; total integral/MT/mês/ano, revisão Luna |
| P35 | 🟠 | `database.py:506; fiscal_direto.py:1095` | Config vazia repete número 1; falha de assinatura depois de reservar deixa buraco | Reserva persistente/concorrente e tratamento de falhas antes da transmissão | 4 | ✅ corrigida | 990408c · preflight antes de reservar, erro local libera o número e retomada reusa a mesma reserva; 4 casos |
| P36 | 🟠 | `fiscal.py:38,360` | Prazo de cancelamento usa criação em vez de autorização; offset legado UTC−3 | Basear prazo em dhRecbto; datas fiscais em MT | 4 | ✅ corrigida | c62400c · prazo conta de `autorizado_em` (fallback criação); 4 casos X15 |
| P37 | 🟠 | `clientes.py:120; contas_receber.py:49` | Cliente com dívida pode ser ocultado; referências de conta sem validação; conta cancelada aceita pagamento | Preservar fiado visível e validar referência/estado da conta | 2 | ✅ corrigida | e1ad5e2 · C09, dívida/referência/estado de conta |
| P38 | 🟠 | `produtos.py:135–154` | Criação do produto e campos fiscais usa duas transações | Cadastro do produto inteiro em uma transação | 2 | ✅ corrigida | 7dee50a · I07, INSERT único incluindo fiscal |
| P39 | 🟠 | `main.py:39; run.py:37` | Watchdog encerra com os._exit durante operações; porta ocupada é assumida como PDV | Encerrar com segurança e identificar serviço antes de reutilizar porta | 5 | ✅ corrigida | e6885ba/f1bdf6a · R09/R10, porta validada e saída cooperativa |
| P40 | 🟠 | `package-lock.json` | npm audit: 21 vulnerabilidades (2 runtime, react-router) | Atualizar dependências compatíveis e validar build/lint/audit | 3 | ✅ corrigida | fa736aa · npm audit0 e revisão independente aprovada; override minimatch documentado |
| P41 | 🟠 | `painel/main.py:168; auth painel` | Setup inicial concorrente permite dois admins; senha trocada não revoga tokens; atualização aceita senha fraca | Bootstrap atômico, validação de senha e versão de credencial | 3 | ✅ corrigida | 31541bd/1f52324/f54b125; RED1/8/3, GREEN23 painel; revisão Luna |
| P42 | 🟠 | `fiscal_router.py:33–64,110–131` | Leitura, consulta e cancelamento de nota de outro usuário | Validar owner antes de qualquer leitura ou transmissão | 3 | ✅ corrigida | 342f3d6 · S14/8 casos; RED4 → backend323 verde; revisão Luna aprovada |

| P43 | 🟠 | `vendas.py:18,36` | Infinity em quantidade/desconto passava pelo modelo e gerava500 no cálculo Decimal | Recusar números não finitos na validação; V16 | 1 | ✅ corrigida | 79e5ccf · V16 guardas finitas, suíte117 |
| P44 | 🟠 | `e2e/servidor.cjs` | Vite ficava disponível antes da API; testes iniciavam com ECONNREFUSED3121 | Esperar health da API antes de iniciar Vite; provar atraso4s; U08 | 3 | ✅ corrigida | ba47db4 · health API antes Vite; atraso4s rechecado após deps |
| P45 | 🟠 | `PDV.tsx:confirmarVenda` | Checkout201 com erro_nota/rejeitada/pendente era exibido como Nota emitida e escondia o motivo | Separar venda jágravada de resultado fiscal; não repetir cobrança; U09/F3.13 | 3 | ✅ corrigida | bd6013e ·erro_nota real local e statusUI;U09,semalegarSEFAZ |
| P46 | UI XML descarta chave da prévia ao confirmar; reimportação duplica | 2 | src/lib/api.ts + Produtos.tsx | ✅ corrigida | 41c9265 ·chaveforward/modal409/estoquepreservado;reviewaprovado,recheckverde |

## Auditoria por conta própria (além das pistas)

| P47 | 🟠 | `fiscal_direto.normalizar_retorno_sefaz` | HTTP 5xx tratado como rejeição, podendo liberar nova emissão indevida | Preservar reserva e consultar chave | 4 | ✅ corrigida | 8d8cc1b · 12 RED→GREEN; suíte 367 |
| P48 | 🟠 | `fiscal.cancelar_nfce` | Evento rejeitado/indisponível retira autorização da nota | Preservar status e protocolo até confirmação | 4 | ✅ corrigida | a9dc752 · 3 RED→GREEN; suíte 370 |
| P49 | 🟠 | `docs/LEGISLACAO_FISCAL_MT.md` / `fiscal_direto.py` | Limites estaduais inclusivos diferentes dos nacionais usados | Identificação desde R$1 mil; vedação desde R$200 mil, Portaria177/2021 arts.3/8 | 4 | ✅ corrigida | 2e43441 · 3 RED→7 GREEN; suíte412 |
| P50 | 🟠 | `fiscal.py` / `fiscal_direto.py` | Carimbo local sobrescreve dhRecbto da SEFAZ e renova prazo ao consultar | Normalizar e persistir instante do protocolo nos três fluxos | 4 | ✅ corrigida | 2945663 · 5 RED→GREEN; suíte405 |
| P51 | 🟠 | `fiscal_direto._grupo_pagamento` | Não envia CNPJReceb/idTermPag disponíveis, exigidos no vínculo de MT | Copiar emitente e terminal real da transação, sem inventar identificador | 4 | ✅ corrigida | 188ad56 · X19, 3 RED→3 verdes focados; suíte 415 |

Na Fase 0, um subagente por módulo procura mais. Tudo o que achar vira linha nova aqui (`P23`…).

| Área | O que procurar |
|---|---|
| `produtos.py`, `importacao_xml.py` | chave de NF-e importada duas vezes, conversão de unidade/embalagem, código de barras duplicado, `cEAN` "SEM GTIN", XML que não é NF-e |
| `clientes.py`, `contas_receber.py` | cliente excluído com fiado em aberto, limite de crédito, vencimento sempre nulo |
| `conta.py`, `sync_client.py` | licença bloqueada impedindo fechar caixa ou ler dados; sincronização travando o checkout sem rede |
| `pix.py`, `mercadopago.py` | cobrança paga sem venda registrada; venda registrada sem pagamento confirmado; timeout da maquininha |
| `errors.py` | segredo em log; exceção que vira 500 sem mensagem útil |
| `main.py` | rota `/api/*` sem autenticação; dado de um `user_id` visível para outro |
| `src/` | tela que perde dado ao atualizar; campo numérico que trava com vírgula; fluxo que exige mouse |
