# Pistas — bugs e lacunas vistos no código

Lidas em 10/11/2026 no commit `6da6899`. **Cada linha é pista, não bug provado.** Fluxo: escrever o teste que falha → corrigir → commit → fechar a linha.

Status: ⬜ aberta · 🟨 em andamento · ✅ corrigida (commit + teste) · ➖ descartada (com prova) · 🟦 decisão do Álvaro (padrão aplicado)

| # | Grav. | Onde | O que foi visto | O que fazer | Fase | Status | Commit · teste |
|---|---|---|---|---|---|---|---|
| P1 | 🔴 | `vendas.py:109-161` | Checkout em 4+ transações separadas (`baixar_estoque` por item → `create_venda` → `registrar_movimentacao` → `create_conta_receber`). Queda no meio deixa estoque baixado sem venda ou fiado sem conta | Uma função única em `database.py`, numa transação (`BEGIN IMMEDIATE`) | 1 | ✅ corrigida | 68fcc88 / 79e5ccf / 15c7fb9 · V01–V06 (rollback, concorrência, queda) |
| P2 | 🔴 | backend inteiro | **Não existe cancelamento/estorno de venda** (só cancelar conta a receber e cancelar NFC-e) | `POST /api/vendas/{id}/cancelar` + tela em `src/pages/Vendas.tsx` | 1 | ✅ corrigida | 4a7ff3e / 197dcee / fd35f52 · V07–V11 |
| P3 | 🔴 | schema em `database.py`; `vendas.py:63-103` | Dinheiro em `REAL`, soma em `float` com `round()` (55 ocorrências; `Decimal` só em `mercadopago.py`) | Módulo único de dinheiro com `Decimal` + `ROUND_HALF_UP` usado por venda, caixa, fiado e XML | 1 | ✅ corrigida | 3fe1aa4/52bb220/d798762/2a9b689 · D01–D05 e101 testes |
| P4 | 🟠 | `database.py:824-866` | Caixa soma vendas por janela de tempo, sem `sessao_id`; venda é aceita sem caixa aberto | Garantir que sessões não se misturam; aviso de caixa fechado (ver D4) | 2 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P5 | 🟠 | `auth.py:123-179`, `main.py:54` | Login local sem limite de tentativas; `/registro` aberto em modo local com CORS `*`; senha mínima 4; token de 30 dias | Limite de tentativas; fechar `/registro` após o 1º usuário; CORS restrito | 3 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P6 | 🟠 | `main.py` | `/docs` e `/openapi.json` expostos no `.exe` | Desligar quando empacotado (`sys.frozen`) | 3 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P7 | 🟠 | `database.py:15-18` | Conexão única + `RLock`, WAL; `foreign_keys=0`; `busy_timeout=5000` e `synchronous=2` já existem por padrão (medido na Fase 0) | Definir os PRAGMAs e provar com teste de concorrência | 1 | ✅ corrigida | a4f8e69 · V15 / PRAGMAs e cópia legada válidos |
| P8 | 🟠 | `backup.py:44-58`, `:114-121`; `database.py:1353` | Loop de backup engole exceção sem log; sem `integrity_check`; restauração aceita qualquer `.db` que abra | `integrity_check`, validação de schema, log, modo consulta com banco corrompido | 5 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P9 | 🟠 | `backend/tests/` | Sem XSD, sem validação de schema, sem marker `homologacao`, sem `pytest.ini` | Fase 4, bloco A e C | 4 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P10 | 🟠 | `src/pages/PDV.tsx` | Carrinho só em memória (F5 perde a venda); atalhos só F2/F4 | Persistir carrinho; revisar teclado | 3 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P11 | 🟡 | `vendas.py:81` | Produto com preço de venda 0 é vendido pelo custo, em silêncio | Decisão D3 | 1 | ✅ mantida por D3 | 997dd69 · caracterização, sem mudança de código |
| P12 | 🟡 | `src/lib/recibo.ts` | Impressão é pelo navegador; não há ESC/POS, RAW nem gaveta | Validar cupom 58/80 mm em PDF; decisão D5 | 6 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P13 | 🟡 | `main.py:102` | Só existe `/health`; não há diagnóstico para o suporte | Endpoint autenticado + tela | 5 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P14 | 🟡 | `fiscal_config.py:12` | `_SENSIVEIS` mascarados na leitura, em claro no SQLite | Teste de não vazamento + decisão D6 escrita | 3 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P15 | 🟡 | `auth.py:93`, `fiscal.py:352-376`, `fiscal_direto.py:83` | Timestamps de venda em UTC; fiscal usa `agora_mt()`. MT é UTC−4 | Testar `dhEmi`, prazo de cancelamento e "vendas de hoje" entre 20h e 24h locais | 4 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P16 | 🟡 | git | 4 binários trackeados apesar do `.gitignore`; `CLAUDE.md` diz o contrário | Só relatar (decisão D2) | 7 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P17 | 🟡 | `installer/vendafacil.iss:44` | `PrivilegesRequired=admin`: instalar exige UAC | Fase 6; sem elevação → B8 | 6 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P18 | 🟡 | `CLAUDE.md` | Cita build pelo GitHub Actions | Não depender do CI; corrigir o doc se o Actions estiver fora | 7 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P19 | 🟠 | `fiscal_direto.py` (comentário na linha 1085) | **Não há inutilização de numeração** (serviço `NfeInutilizacao4` ausente do dicionário de webservices, linhas 37-42) | Conferir no MOC/SEFAZ-MT a exigência atual para NFC-e e implementar; provar que rejeição não deixa buraco | 4 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P20 | 🟡 | `fiscal_direto.py:37-42` | **Não há `statusServico`** (`NfeStatusServico4`) | Implementar; usar no diagnóstico e no harness de homologação | 4 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P21 | 🟠 | `database.py:1096-1115` | Baixa de fiado: valor maior que o pendente é engolido sem aviso; não há histórico dos pagamentos; não lança no caixa | Tabela de pagamentos, recusa de excedente, lançamento no caixa quando em dinheiro | 2 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |
| P22 | 🟡 | `fiscal.py:42`, `:134` | Três caminhos de emissão: SEFAZ-MT direto, FocusNFe e PlugNotas (legados) | O caminho da mercearia é `sefaz_mt_direto`. Não remover os legados; garantir que nenhum é escolhido por engano | 4 | ⬜ confirmada no código | `evidencias/F0_AUDITORIA.md` (não corrigida) |

| P23 | 🟠 | `vendas.py:55; database.py:969` | Cliente de outro usuário aceito no checkout não fiado; update_categoria retorna registro sem filtro de proprietário | Validar todas as referências e retornos por usuário | 1 | ✅ corrigida | c7e3991 · V14; checkout já recusava, retorno da categoria vazava |
| P24 | 🟠 | `produtos.py:221; importacao_xml.py:49` | XML sem deduplicação persistente por chave; barcode sem unicidade; modelo de entrada sem validação | Importação atômica/idempotente e validar GTIN/modelo/embalagem | 2 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em I06 |
| P25 | 🟠 | `errors.py:106,234` | Payload inválido em bytes pode registrar segredo no log | Nunca registrar corpo bruto; sanitizar erros e exceções | 3 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em S09 |
| P26 | 🟠 | `fiscal_config.py:95; mercadopago.py:370` | Reenviar config mascarada com campo sensível vazio apaga credencial | Preservar segredo omitido/vazio; remoção precisa ser explícita | 3 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em S10 |
| P27 | 🟠 | `PDV.tsx:384; mercadopago.py` | Cobrança aprovada perde comprovante se checkout falhar; falta conciliação idempotente | Persistir pagamento pendente e impedir segunda cobrança/venda | 2 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em L05 |
| P28 | 🟠 | `pix.py:97` | Nome/cidade com acentos produz TLV EMV incompatível | Normalização ASCII, comprimento em bytes, CRC provado | 2 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em L06 |
| P29 | 🟠 | `sync_client.py:30,57` | HTTP 200 marca todas vendas sincronizadas sem confirmar aceitação | Conferir contrato de ACK e preservar pendências em resposta inválida | 2 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em L07 |
| P30 | 🟠 | `painel/main.py:54; painel/static/index.html:348` | Data inválida torna licença perpétua e data UTC expira antes do fim do dia MT | Validar datas, recusar inválidas e usar fim do dia local de MT | 2 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em L08 |
| P31 | 🟠 | `PDV.tsx; ContasReceber.tsx:87; Caixa.tsx:33; Produtos.tsx:182` | Vírgula rejeitada/truncada em fiado, caixa, quantidade, desconto e embalagem | Parser numérico pt-BR compartilhado, sem truncamento silencioso | 3 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em U06 |
| P32 | 🟠 | `recibo.ts:83,91,108,115` | Interpolação de forma/id/numero/serie/QR sem escape permite HTML/script | Escape completo de texto/atributos; QR Base64 validado | 3 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em S11 |
| P33 | 🟠 | `recibo.ts:168–171` | Iframe removido por timer antes de terminar impressão | Esperar imagens e afterprint, ciclo testável | 6 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em E10 |
| P34 | 🟠 | `Vendas.tsx:89–96` | Total do dia truncado nos primeiros 100 registros | Total diário pelo backend, excluindo canceladas e fuso MT | 3 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em U07 |
| P35 | 🟠 | `database.py:506; fiscal_direto.py:1095` | Config vazia repete número 1; falha de assinatura depois de reservar deixa buraco | Reserva persistente/concorrente e tratamento de falhas antes da transmissão | 4 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em X14 |
| P36 | 🟠 | `fiscal.py:38,360` | Prazo de cancelamento usa criação em vez de autorização; offset legado UTC−3 | Basear prazo em dhRecbto; datas fiscais em MT | 4 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em X15 |
| P37 | 🟠 | `clientes.py:120; contas_receber.py:49` | Cliente com dívida pode ser ocultado; referências de conta sem validação; conta cancelada aceita pagamento | Preservar fiado visível e validar referência/estado da conta | 2 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em C09 |
| P38 | 🟠 | `produtos.py:135–154` | Criação do produto e campos fiscais usa duas transações | Cadastro do produto inteiro em uma transação | 2 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em I07 |
| P39 | 🟠 | `main.py:39; run.py:37` | Watchdog encerra com os._exit durante operações; porta ocupada é assumida como PDV | Encerrar com segurança e identificar serviço antes de reutilizar porta | 5 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em R10 |
| P40 | 🟠 | `package-lock.json` | npm audit: 21 vulnerabilidades (2 runtime, react-router) | Atualizar dependências compatíveis e validar build/lint/audit | 3 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em S12 |
| P41 | 🟠 | `painel/main.py:168; auth painel` | Setup inicial concorrente permite dois admins; senha trocada não revoga tokens; atualização aceita senha fraca | Bootstrap atômico, validação de senha e versão de credencial | 3 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em S13 |
| P42 | 🟠 | `fiscal_router.py:33–64,110–131` | Leitura, consulta e cancelamento de nota de outro usuário | Validar owner antes de qualquer leitura ou transmissão | 3 | ⬜ confirmada na auditoria | `evidencias/F0_AUDITORIA.md`; prova automatizada em S14 |

| P43 | 🟠 | `vendas.py:18,36` | Infinity em quantidade/desconto passava pelo modelo e gerava500 no cálculo Decimal | Recusar números não finitos na validação; V16 | 1 | ✅ corrigida | 79e5ccf · V16 guardas finitas, suíte117 |

## Auditoria por conta própria (além das pistas)

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
