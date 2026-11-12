# VendaFácil PDV — relatório de entrega

> Preenchido pelo agente na Fase 7. Toda prova leva a saída do comando, não a opinião.

**Data:** 2026-11-12 · **Commit final:** `701c5bc` · **Versão:** 1.0.13

## Veredito

⏸ **Pronto para homologação na loja, aguardando terceiro: B1–B5 (dados fiscais reais), B7 (papel), B8 (instalador elevado) e B9 (implantação).**
Tudo o que dependia só do código e desta máquina está validado, incluindo o `.exe` e o instalador.

"Pronto para produção" só o Álvaro declara, depois da 1ª NFC-e autorizada com o certificado da mercearia.

## O que preciso de você

Lista única, em ordem de prioridade. É a única coisa que o Álvaro precisa ler para destravar o que falta.

| # | O que fazer | Onde | Tempo | Destrava |
|---|---|---|---|---|
| 1 | Cadastrar o **certificado A1 da própria mercearia** e a senha (B1) | PDV → **Fiscal**, ambiente **homologação** | 10 min | H01–H09 (1ª NFC-e real) |
| 2 | Gerar e cadastrar **CSC + ID do CSC de homologação** (B2) | Portal da SEFAZ-MT → PDV → Fiscal | 15 min | QR Code válido, H02–H08 |
| 3 | Preencher os **dados da empresa** (CNPJ igual ao do A1, IE, CNAE, endereço, CRT) com o contador (B4) | PDV → Fiscal | 15 min | H02–H09 |
| 4 | Pedir ao contador a confirmação do **credenciamento NFC-e** da loja na SEFAZ-MT (B3) | Contador / SEFAZ-MT | depende do contador | H01–H09 |
| 5 | Depois de 1–4: rodar `scripts\fiscal_precheck.py` ou reenviar o goal; o agente roda H01–H09 em homologação | Este PC | 5 min | Bloco C fiscal |
| 6 | Rodar o teste do instalador como administrador numa máquina/VM descartável sem o PDV: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\teste_instalador.ps1` (B8) | PowerShell elevado | 10 min | E04–E06 |
| 7 | Informar o **CNPJ da credenciadora** e ligar a conta Mercado Pago de produção; parear a Point física (B5/B6) | PDV → Maquininha → Vínculo fiscal | 20 min | H03/H04, cartão real |
| 8 | Testar em **papel**: impressora térmica, leitor e gaveta reais (B7) | Loja | 20 min | Teste físico do cupom |
| 9 | Preencher o contato de suporte em `docs/SUPORTE_LOJA.md` e imprimir | Repositório | 5 min | Folha do balcão |
| 10 | Implantação presencial seguindo `docs/IMPLANTACAO_MERCEARIA.md` + treinamento (B9) | Loja | 2–3 h | Operação real |

## Números

| Medida | Partida (`6da6899`) | Entrega (`701c5bc`) |
|---|---|---|
| Testes backend | 76 | 460 verdes, 9 desmarcados (`homologacao`, B1–B5) |
| Testes painel | 7 | 23 |
| Testes Node do front | 0 | 36 |
| Testes E2E (Chromium, 1 worker) | 0 | 91/91 numa rodada |
| Roteiro do `.exe` | — | 49 requisições, 0 respostas 5xx; 4/4 cupons PDF; migração com contagens iguais |
| Pistas fechadas | 0/22 | 53/53 com status final (0 abertas) |
| Testes da matriz ✅ | 0/100 | 122/134 |
| Testes da matriz ⛔ | — | 12 (H01–H09 por B1–B5; E04–E06 por B8) |
| Build / lint | — | 0 erros |

## Bugs corrigidos

| # | Gravidade | Onde | Sintoma | Correção | Teste que prova | Commit |
|---|---|---|---|---|---|---|
| P1 | 🔴 | `vendas.py:109-161` | Checkout em 4+ transações separadas (`baixar_estoque` por item → `create_venda` → `registrar_movimentacao` → `create_conta_receber`). Queda no meio deixa estoque baixado sem venda ou fiado sem conta | Uma função única em `database.py`, numa transação (`BEGIN IMMEDIATE`) | V01–V06 (rollback, concorrência, queda) | 68fcc88 / 79e5ccf / 15c7fb9 |
| P2 | 🔴 | backend inteiro | Não existe cancelamento/estorno de venda (só cancelar conta a receber e cancelar NFC-e) | `POST /api/vendas/{id}/cancelar` + tela em `src/pages/Vendas.tsx` | V07–V11 | 4a7ff3e / 197dcee / fd35f52 |
| P3 | 🔴 | schema em `database.py`; `vendas.py:63-103` | Dinheiro em `REAL`, soma em `float` com `round()` (55 ocorrências; `Decimal` só em `mercadopago.py`) | Módulo único de dinheiro com `Decimal` + `ROUND_HALF_UP` usado por venda, caixa, fiado e XML | D01–D05 e101 testes | 3fe1aa4/52bb220/d798762/2a9b689 |
| P4 | 🟠 | `database.py:824-866` | Caixa soma vendas por janela de tempo, sem `sessao_id`; venda é aceita sem caixa aberto | Garantir que sessões não se misturam; aviso de caixa fechado (ver D4) | C01/C06/D4; suíte274 e cobertura realF3.13 | 320bc56/2629af3 |
| P5 | 🟠 | `auth.py:123-179`, `main.py:54` | Login local sem limite de tentativas; `/registro` aberto em modo local com CORS `*`; senha mínima 4; token de 30 dias | Limite de tentativas; fechar `/registro` após o 1º usuário; CORS restrito | S01–S03 e test_senha; política/token em SEGURANCA.md | 3544de8/ac2f81e/433ff7c/ebc8390 |
| P6 | 🟠 | `main.py` | `/docs` e `/openapi.json` expostos no `.exe` | Desligar quando empacotado (`sys.frozen`) | S04 flag empacotado; confirmação no exe real fica na F6 | 88a4ca2 |
| P7 | 🟠 | `database.py:15-18` | Conexão única + `RLock`, WAL; `foreign_keys=0`; `busy_timeout=5000` e `synchronous=2` já existem por padrão (medido na Fase 0) | Definir os PRAGMAs e provar com teste de concorrência | V15 / PRAGMAs e cópia legada válidos | a4f8e69 |
| P8 | 🟠 | `backup.py:44-58`, `:114-121`; `database.py:1353` | Loop de backup engole exceção sem log; sem `integrity_check`; restauração aceita qualquer `.db` que abra | `integrity_check`, validação de schema, log, modo consulta com banco corrompido | R01–R06, cópia íntegra e recuperação | 73ae8f2/1979b2e/1ee3df3/15696f5 |
| P9 | 🟠 | `backend/tests/` | Sem XSD, sem validação de schema, sem marker `homologacao`, sem `pytest.ini` | Fase 4, bloco A e C | X01–X10 verdes no XSD oficial e marker homologacao separa 9 cenários | 08bbffc/e037473 |
| P10 | 🟠 | `src/pages/PDV.tsx` | Carrinho só em memória (F5 perde a venda); atalhos só F2/F4 | Persistir carrinho; revisar teclado | persistência e atalhos; três SKUs só no teclado | 1a23906/dc0858d |
| P11 | 🟡 | `vendas.py:81` | Produto com preço de venda 0 é vendido pelo custo, em silêncio | ✅ mantida por D3 | 997dd69 · caracterização, sem mudança de código | — |
| P12 | 🟡 | `src/lib/recibo.ts` | Impressão é pelo navegador; não há ESC/POS, RAW nem gaveta | 🟦 D5 aplicada | ee491d5/b41e946 · E07–E09/E11 em PDF; impressão segue pelo navegador; papel em B7 | — |
| P13 | 🟡 | `main.py:102` | Só existe `/health`; não há diagnóstico para o suporte | Endpoint autenticado + tela | R08 API protegida e clipboard Chromium | f25d05f/aa2ea37 |
| P14 | 🟡 | `fiscal_config.py:12` | `_SENSIVEIS` mascarados na leitura, em claro no SQLite | ✅ máscara comprovada; D6 documentada | c7ff77c/f9d8ad1 · S05/S06 JSON; caso bytes/log bruto continua aberto em P25 | — |
| P15 | 🟡 | `auth.py:93`, `fiscal.py:352-376`, `fiscal_direto.py:83` | Timestamps de venda em UTC; fiscal usa `agora_mt()`. MT é UTC−4 | ✅ conferida | 08bbffc/4e52786/fb9f5b9 · X09/X11 e U07, viradas de dia/mês em MT | — |
| P16 | 🟡 | git | 4 binários trackeados apesar do `.gitignore`; `CLAUDE.md` diz o contrário | Só relatar (decisão D2) | D2 respondida: binários removidos do índice (git ls-files sem .exe); CLAUDE.md atualizado | 808c5cb |
| P17 | 🟡 | `installer/vendafacil.iss:44` | `PrivilegesRequired=admin`: instalar exige UAC | ✅ teste pronto; execução ⛔ B8 | b41e946 · `scripts/teste_instalador.ps1`; F6_INSTALADOR_B8.txt saída 2 | — |
| P19 | 🟠 | `fiscal_direto.py` (comentário na linha 1085) | Não há inutilização de numeração (serviço `NfeInutilizacao4` ausente do dicionário de webservices, linhas 37-42) | Conferir no MOC/SEFAZ-MT a exigência atual para NFC-e e implementar; provar que rejeição não deixa buraco | X05/M09/X12, API e 4 testes Chromium | 5980fe4/8c83d0f/31a4e5c/60a99ad |
| P20 | 🟡 | `fiscal_direto.py:37-42` | Não há `statusServico` (`NfeStatusServico4`) | Implementar; usar no diagnóstico e no harness de homologação | `statusServico` 65/55 homologação e produção, rota + tela Fiscal; M10 | 9f28f02 |
| P21 | 🟠 | `database.py:1096-1115` | Baixa de fiado: valor maior que o pendente é engolido sem aviso; não há histórico dos pagamentos; não lança no caixa | Tabela de pagamentos, recusa de excedente, lançamento no caixa quando em dinheiro | C02–C05, histórico e recusa de excedente | 2fbd5e1/4033835/7c56670/12f1994 |
| P22 | 🟡 | `fiscal.py:42`, `:134` | Três caminhos de emissão: SEFAZ-MT direto, FocusNFe e PlugNotas (legados) | ✅ conferida | 4e52786 · X13:55/65, emissão/consulta/loop/cancelamento sem gateway | — |
| P23 | 🟠 | `vendas.py:55; database.py:969` | Cliente de outro usuário aceito no checkout não fiado; update_categoria retorna registro sem filtro de proprietário | Validar todas as referências e retornos por usuário | V14; checkout já recusava, retorno da categoria vazava | c7e3991 |
| P24 | 🟠 | `produtos.py:221; importacao_xml.py:49` | XML sem deduplicação persistente por chave; barcode sem unicidade; modelo de entrada sem validação | Importação atômica/idempotente e validar GTIN/modelo/embalagem | atomicidade+GTIN/modelo/números+embalagens comprovados | 00e709d/5b8f0f2 |
| P25 | 🟠 | `errors.py:106,234` | Payload inválido em bytes pode registrar segredo no log | Nunca registrar corpo bruto; sanitizar erros e exceções | 6RED→10GREEN,315backend/9painel;review deleg_0911d189 aprovada | 5da31fa |
| P26 | 🟠 | `fiscal_config.py:95; mercadopago.py:370` | Reenviar config mascarada com campo sensível vazio apaga credencial | Preservar segredo omitido/vazio; remoção precisa ser explícita | 31novoscasos,máscaras/literal/clearwhitelist,revisãoaprovada | 6535b18 |
| P27 | 🟠 | `PDV.tsx:384; mercadopago.py` | Cobrança aprovada perde comprovante se checkout falhar; falta conciliação idempotente | Persistir pagamento pendente e impedir segunda cobrança/venda | L05, cobrança aprovada persistida e idempotente | b633307 |
| P28 | 🟠 | `pix.py:97` | Nome/cidade com acentos produz TLV EMV incompatível | Normalização ASCII, comprimento em bytes, CRC provado | L06, PIX ASCII e CRC | 3227373 |
| P29 | 🟠 | `sync_client.py:30,57` | HTTP 200 marca todas vendas sincronizadas sem confirmar aceitação | Conferir contrato de ACK e preservar pendências em resposta inválida | ACK parcial/legado/inválido preserva fila; 17 casos novos | 46244a9/40f49e7 |
| P30 | 🟠 | `painel/main.py:54; painel/static/index.html:348` | Data inválida torna licença perpétua e data UTC expira antes do fim do dia MT | Validar datas, recusar inválidas e usar fim do dia local de MT | L08, datas válidas e fim do dia MT | f1aeec4 |
| P31 | 🟠 | `PDV.tsx; ContasReceber.tsx:87; Caixa.tsx:33; Produtos.tsx:182` | Vírgula rejeitada/truncada em fiado, caixa, quantidade, desconto e embalagem | Parser numérico pt-BR compartilhado, sem truncamento silencioso | `src/lib/numeros.ts` em caixa/fiado/produtos/PDV/XML; U06 e 81 E2E em 4 lotes | a6a90d5 |
| P32 | 🟠 | `recibo.ts:83,91,108,115` | Interpolação de forma/id/numero/serie/QR sem escape permite HTML/script | Escape completo de texto/atributos; QR Base64 validado | escapeforma/id/numero/serie,allowlistQR,7DOMgreen;review aprovado | 95e2322 |
| P33 | 🟠 | `recibo.ts:168–171` | Iframe removido por timer antes de terminar impressão | Esperar imagens e afterprint, ciclo testável | E10 (F6_E10_RED/GREEN) | eb55f20 |
| P34 | 🟠 | `Vendas.tsx:89–96` | Total do dia truncado nos primeiros 100 registros | Total diário pelo backend, excluindo canceladas e fuso MT | U07:4 backend + 1 UI; total integral/MT/mês/ano, revisão Luna | fb9f5b9 |
| P35 | 🟠 | `database.py:506; fiscal_direto.py:1095` | Config vazia repete número 1; falha de assinatura depois de reservar deixa buraco | Reserva persistente/concorrente e tratamento de falhas antes da transmissão | preflight antes de reservar, erro local libera o número e retomada reusa a mesma reserva; 4 casos | 990408c |
| P36 | 🟠 | `fiscal.py:38,360` | Prazo de cancelamento usa criação em vez de autorização; offset legado UTC−3 | Basear prazo em dhRecbto; datas fiscais em MT | prazo conta de `autorizado_em` (fallback criação); 4 casos X15 | c62400c |
| P37 | 🟠 | `clientes.py:120; contas_receber.py:49` | Cliente com dívida pode ser ocultado; referências de conta sem validação; conta cancelada aceita pagamento | Preservar fiado visível e validar referência/estado da conta | C09, dívida/referência/estado de conta | e1ad5e2 |
| P38 | 🟠 | `produtos.py:135–154` | Criação do produto e campos fiscais usa duas transações | Cadastro do produto inteiro em uma transação | I07, INSERT único incluindo fiscal | 7dee50a |
| P39 | 🟠 | `main.py:39; run.py:37` | Watchdog encerra com os._exit durante operações; porta ocupada é assumida como PDV | Encerrar com segurança e identificar serviço antes de reutilizar porta | R09/R10, porta validada e saída cooperativa | e6885ba/f1bdf6a |
| P40 | 🟠 | `package-lock.json` | npm audit: 21 vulnerabilidades (2 runtime, react-router) | Atualizar dependências compatíveis e validar build/lint/audit | npm audit0 e revisão independente aprovada; override minimatch documentado | fa736aa |
| P41 | 🟠 | `painel/main.py:168; auth painel` | Setup inicial concorrente permite dois admins; senha trocada não revoga tokens; atualização aceita senha fraca | Bootstrap atômico, validação de senha e versão de credencial |  | 31541bd/1f52324/f54b125; RED1/8/3, GREEN23 painel; revisão Luna |
| P42 | 🟠 | `fiscal_router.py:33–64,110–131` | Leitura, consulta e cancelamento de nota de outro usuário | Validar owner antes de qualquer leitura ou transmissão | S14/8 casos; RED4 → backend323 verde; revisão Luna aprovada | 342f3d6 |
| P43 | 🟠 | `vendas.py:18,36` | Infinity em quantidade/desconto passava pelo modelo e gerava500 no cálculo Decimal | Recusar números não finitos na validação; V16 | V16 guardas finitas, suíte117 | 79e5ccf |
| P44 | 🟠 | `e2e/servidor.cjs` | Vite ficava disponível antes da API; testes iniciavam com ECONNREFUSED3121 | Esperar health da API antes de iniciar Vite; provar atraso4s; U08 | health API antes Vite; atraso4s rechecado após deps | ba47db4 |
| P45 | 🟠 | `PDV.tsx:confirmarVenda` | Checkout201 com erro_nota/rejeitada/pendente era exibido como Nota emitida e escondia o motivo | Separar venda jágravada de resultado fiscal; não repetir cobrança; U09/F3.13 | erro_nota real local e statusUI;U09,semalegarSEFAZ | bd6013e |
| P47 | 🟠 | `fiscal_direto.normalizar_retorno_sefaz` | HTTP 5xx tratado como rejeição, podendo liberar nova emissão indevida | Preservar reserva e consultar chave | 12 RED→GREEN; suíte 367 | 8d8cc1b |
| P48 | 🟠 | `fiscal.cancelar_nfce` | Evento rejeitado/indisponível retira autorização da nota | Preservar status e protocolo até confirmação | 3 RED→GREEN; suíte 370 | a9dc752 |
| P49 | 🟠 | `docs/LEGISLACAO_FISCAL_MT.md` / `fiscal_direto.py` | Limites estaduais inclusivos diferentes dos nacionais usados | Identificação desde R$1 mil; vedação desde R$200 mil, Portaria177/2021 arts.3/8 | 3 RED→7 GREEN; suíte412 | 2e43441 |
| P50 | 🟠 | `fiscal.py` / `fiscal_direto.py` | Carimbo local sobrescreve dhRecbto da SEFAZ e renova prazo ao consultar | Normalizar e persistir instante do protocolo nos três fluxos | 5 RED→GREEN; suíte405 | 2945663 |
| P51 | 🟠 | `fiscal_direto._grupo_pagamento` | Não envia CNPJReceb/idTermPag disponíveis, exigidos no vínculo de MT | Copiar emitente e terminal real da transação, sem inventar identificador | X19, 3 RED→3 verdes focados; suíte 415 | 188ad56 |
| P52 | 🟡 | `src/lib/recibo.ts:122` | No rolo de 80 mm, `word-break:break-all` partia um bloco de 4 dígitos da chave de acesso do DANFE | `overflow-wrap:anywhere`, quebra só entre blocos | E11 (`e2e/cupom.spec.ts`, F6_CHAVE_RED/GREEN) | ee491d5 |
| P53 | 🟠 | `src/pages/Vendas.tsx` | Venda com NFC-e autorizada só cancela depois da nota, mas nenhuma tela cancelava a NFC-e (só a API): operador travado | Botão "Cancelar NFC-e" com justificativa de 15+ caracteres | U10 (`e2e/cancelar-nfce.spec.ts`, F7_CANCELAR_NFCE_RED/GREEN) | 074a43a |
| D3 | 🟡 | `backend/vendas.py`, `src/pages/PDV.tsx` | Produto com preço de venda 0 era vendido pelo custo, sem aviso | Bloquear no checkout (400) e no carrinho (decisão do Álvaro) | V17 | 49dbecc |
| P46 | 🟠 | `src/lib/api.ts` + `Produtos.tsx` | UI de XML descartava a chave da prévia ao confirmar; reimportação duplicava estoque | Enviar a chave e tratar 409 na tela | I08 | 41c9265 |
| F6 | 🟠 | `fiscal_direto.py` (proxy) | Proxy recusando conexão não levava a venda à contingência | Tratar recusa do proxy como rede indisponível | F6_PROXY_RED/GREEN | 0d0193e |
| F6 | 🟠 | `src/pages/PDV.tsx` | Após venda em contingência o botão de imprimir/reimprimir não aparecia | Oferecer a reimpressão também em contingência | F6_REIMPRESSAO_RED/GREEN (7 Chromium) | 054e6d6 |
| F6 | 🟡 | `scripts/roteiro_exe.py` | Limpeza da pasta temporária falhava com o `-shm` ainda preso (só no teste) | `ignore_cleanup_errors` | F6_MIGRACAO.txt saída 0 | 2d062b2 |

## Pistas descartadas (com prova)

| # | Por que não é bug | Comando/saída |
|---|---|---|
| P18 | Cita build pelo GitHub Actions — a60aa89 · `gh run list --workflow build-exe.yml`: execuções "Build Windows EXE" verdes em 12/11; CLAUDE.md registra a conferência e que o entregável validado é o local | `gh run list --workflow build-exe.yml` |

## Não corrigido (com motivo)

| # | Gravidade | Motivo | Impacto na loja |
|---|---|---|---|
| P12 | 🟡 | D5: sem ESC/POS nem gaveta | Impressão pelo navegador (58/80 mm validados em PDF); gaveta abre manualmente |
| D6 | 🟡 | Cofre fiscal em claro no SQLite (risco aceito, `docs/SEGURANCA.md`) | Proteger o PC da loja (usuário Windows com senha, backup fora do PC) |
| — | 🟡 | Auto-update do `.exe` | Atualização é reinstalar o Setup por cima (dados preservados) |

## Provas por fase

| Fase | Portão de saída | Comando | Saída resumida |
|---|---|---|---|
| 0 | ✅ 52c6e1e | `pytest -q` (backend/painel), build, lint | Linha de base 76 backend; auditoria F0_AUDITORIA.md com 22 pistas |
| 1 | ✅ 05c6323 | `pytest -q` | Dinheiro em Decimal, checkout transacional, cancelamento; suíte 158/7 |
| 2 | ✅ 41c9265 | `pytest -q` + E2E | Caixa por sessão, fiado, importação atômica, licença/ACK; F2_PORTAO_* |
| 3 | ✅ d9038dc | `pytest -q`, 4 lotes E2E, Node, build/lint | Backend 327, painel 23, E2E A28/B20/C19/XML14, Node 29 |
| 4 A (offline) | ✅ 3c388a3 | `pytest -q` (X01–X19) | XSD, assinatura, QR, contingência, inutilização; 438 backend |
| 4 B (simulador) | ✅ 3c388a3 | `pytest -q` (M01–M12) | Simulador local da SEFAZ verde |
| 4 C (SEFAZ-MT real) | ⛔ B1–B5 | `scripts/fiscal_precheck.py` | Saída 2: certificado, CSC, empresa e credenciamento ausentes (F4_PRECHECK_REAL.txt) |
| 5 | ✅ f97eb6a | `pytest -q` | Backup/integrity_check, modo consulta, log rotativo, instância única, diagnóstico; 459/9 e 23 |
| 6 | ✅ com B8, 954dac8 | `roteiro_exe.py --chromium`, `verificar_cupons_pdf.py`, suítes | 49 req/0 5xx; 4/4 PDFs e 6 QR decodificados; E04–E06 ⛔ B8 (saída 2) |
| 7 | ✅ `701c5bc` | suítes finais, `git status --porcelain`, `git ls-remote` | Backend 460/9, painel 23, Node 36, E2E 91/91 numa rodada; build/lint 0 |

## Bloqueado por terceiro

| # | Item | Dono | Impacto | O que preciso dele |
|---|---|---|---|---|
| B1 | Certificado A1 da mercearia + senha | Lojista | Sem transmissão de NFC-e | Cadastrar na tela Fiscal |
| B2 | CSC + ID de homologação | Lojista | Sem QR válido | Gerar no portal da SEFAZ-MT |
| B3 | Credenciamento NFC-e | Lojista/contador | Sem autorização | Confirmar com o contador |
| B4 | Dados da empresa | Lojista | Cupom sem validade | Preencher com o contador |
| B5 | CNPJ da credenciadora + conta MP produção | Lojista | Rejeição em cartão/PIX | Configurar na Maquininha |
| B6 | Point física | Lojista | Cartão não testado no aparelho | Parear o aparelho |
| B7 | Térmica, leitor, gaveta | Lojista | Cupom não testado em papel | Teste na loja |
| B8 | Elevação (UAC) | Álvaro | E04–E06 não executados | Rodar `scripts\teste_instalador.ps1` elevado |
| B9 | Implantação e 1ª NFC-e | Álvaro + contador | Loja não opera | Seguir `docs/IMPLANTACAO_MERCEARIA.md` |

## Decisões do Álvaro (respondidas em 12/11/2026)

| # | Decisão | Padrão adotado | O que muda se ele decidir o contrário |
|---|---|---|---|
| D1 | Ir para produção | Homologação | Trocar o ambiente na tela Fiscal após a 1ª NFC-e de homologação |
| D5 | ESC/POS e gaveta | Não construir | Projeto novo de impressão direta |
| D6 | Criptografar cofre | Não | Chave por máquina e migração do cofre |
| D7 | Assinar o `.exe` | Não assinar | Comprar certificado de code signing e assinar no build |
| D9 | Mudar fluxo do lojista | Não mudar | — |

**Todas as 9 decisões foram respondidas pelo Álvaro em 12/11/2026** (`05_DECISOES_ALVARO.md`): D2 (binários fora do git, 808c5cb) e D3 (bloqueio de venda sem preço, 49dbecc) foram implementadas; as demais mantêm o padrão da tabela acima.

## Artefatos

| Artefato | Caminho | Tamanho | sha256 |
|---|---|---|---|
| Instalador | `C:\GIS\VendaFacil_PDV\dist_installer\VendaFacilPDV-Setup-1.0.13.exe` | 39.974.387 bytes | `C0B55A78D17C221074F4AE68373B0A283C89A33AE8E923A3A575A05EF86109F9` |
| Executável | `C:\GIS\VendaFacil_PDV\dist_exe\VendaFacilPDV.exe` | 39.688.485 bytes | `E899D8FBD0CD060FA5B2C68010C658B953F413A7CCBD2708A16FA091F1F77683` |

Gerados sobre `808c5cb` (inclui D3; depois só o verificador de testes, docs e plano). Nenhum binário no git (D2).

## Riscos que ficam

- **NFC-e real nunca transmitida**: tudo fiscal foi provado offline e com simulador. A 1ª nota em homologação com o A1 da loja (B1–B4) é o teste que falta.
- **Contingência depende do programa aberto**: se o PC ficar desligado até depois do prazo (1º dia útil seguinte em MT), a nota não é transmitida. Está escrito em `SUPORTE_LOJA.md`.
- **Cofre em claro no SQLite** (D6): se o PC for roubado, o certificado pode vazar. Revogar o A1 e trocar o CSC (`SEGURANCA.md`).
- **Instalador não testado elevado** (B8) e **sem assinatura** (SmartScreen esperado).
- **E2E sob carga**: rodando tudo de uma vez, testes podem falhar na preparação por falta de memória; repetir o arquivo isolado.

## Erros encontrados neste plano

- O painel indicava 16/27 na Fase 4 quando o código já estava em 20/27 (corrigido na retomada).
- O modelo de subagente do plano (`ag/gemini-3.8-flash-high`) foi substituído por ordem do Álvaro: nesta retomada os subagentes usaram Claude Haiku 5.5 com esforço alto (auditoria de docs, relato conferido no código antes de cada correção).
- `node --test frontend-tests/` (diretório) falha no Node 22; o comando certo é `node --test frontend-tests/*.test.mjs`.
- No bash do Git, `cmd.exe /c "build_exe.bat"` não acha o arquivo; use o caminho absoluto entre aspas simples.
- F7.11 pedia autor `Hermes-windows` no vault; a ficha foi escrita por Claude e assinada como Claude, para não atribuir a outro agente.
- A pasta `Dados_James/` com o A1, o CSC e o credenciamento reais da loja apareceu na raiz do repositório; foi colocada no `.gitignore` (505ddcb) junto com `*.pfx`/`*.p12`, sem nunca ter sido commitada.
- A auditoria de docs achou um defeito de produto, não só de texto: o cancelamento da NFC-e não existia na tela (P53, 074a43a).
