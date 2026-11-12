# Fase 4 — Fiscal de Mato Grosso (NFC-e 65 e NF-e 55)

**Status:** ⏸ blocos A/B concluídos — 25/27, H01–H09 aguardam B1–B5 · **Depende de:** Fase 1 (dinheiro) · **Pistas:** P9, P15, P19, P20, P22, P49 · **Testes:** X01–X18, M01–M12, H01–H09

## Objetivo

Provar a parte fiscal inteira. São três blocos, do que não depende de ninguém ao que depende da loja:

| Bloco | O que prova | Depende de terceiro? | Pode ficar `[!]`? |
|---|---|---|---|
| A — offline | O XML, a assinatura e o QR Code estão certos | Não | **Não** |
| B — simulador | O PDV reage certo a cada resposta possível da SEFAZ | Não | **Não** |
| C — SEFAZ-MT real | A SEFAZ-MT de homologação aceita a nota da loja | Sim (B1–B6) | Sim |

Caminho de emissão da mercearia: **`sefaz_mt_direto`** (`fiscal_direto.py`). FocusNFe e PlugNotas são legados: não remover, não usar.

Já existe: 49 testes fiscais (`test_fiscal_direto.py`, `test_fiscal_fluxo.py`) cobrindo montagem, pagamento, ST, QR, contingência e prazos. **Não reescreva; complete.**

## Bloco A — offline (obrigatório)

- [x] F4.1 (P9) Baixar o pacote oficial de schemas da NF-e/NFC-e 4.00 no Portal Nacional da NF-e, guardar em `backend/tests/xsd/` e registrar no diário a versão do pacote, a URL e a data. Só fonte oficial — 08bbffc · PL_010g v1.03 de 26/10/2026 + cancelamento v1.01, 16 XSDs, SHA-256 dos dois ZIPs conferido em F4_XSD_ORIGEM.txt
- [x] F4.2 (P9) Auxiliar de teste que valida qualquer XML gerado contra o XSD (`lxml`). Testes X01, X02, X03 — 08bbffc · `test_fiscal_xsd.py` X01–X03 (dinheiro, cartão, PIX, fiado, desconto, CPF, ST e NF-e 55); 347 backend verdes
- [x] F4.3 Validar no XSD o evento de cancelamento (X04) — 08bbffc · `test_x04_schema_cancelamento_assinado`, assinado e validado no schema de evento
- [x] F4.4 Assinatura: verificação com a chave pública, adulteração de 1 byte e algoritmos conforme o Manual de Orientação do Contribuinte (X06). Citar no diário a seção do manual usada — 08bbffc · MOC NF-e 7.0 §4.2.4 (RSA-SHA1, SHA-1, C14N não exclusiva); 1 byte alterado invalida
- [x] F4.5 QR Code 2.00 online e de contingência: recalcular o hash do CSC e conferir cada parâmetro com a especificação (X07, X08) — 08bbffc · hash recalculado de forma independente nos dois modos; ordem e parâmetros conferidos
- [x] F4.6 (P15) Fuso de MT: `dhEmi`, chave de acesso, virada de mês e prazos de cancelamento (X09, X11) — 4e52786 · X09 em 08bbffc; `test_prazo_cancelamento.py`:8 passes, equivalência UTC/MT na virada do mês; suíte398 em F4_SIMULADOR_FINAL_SUITE.txt
- [x] F4.7 Ambiente: `tpAmb` só da configuração; texto obrigatório de homologação conforme o manual (X10). Conferir que nada troca o ambiente sozinho — 08bbffc · X10 com `tpAmb` 1/2 e o texto "SEM VALOR FISCAL"
- [x] F4.8 (P22) Com `sefaz_mt_direto` configurado, nenhum caminho cai em gateway legado (X13) — 4e52786 · `test_x13_direto_nao_cai_em_gateway_emissao_consulta_loop_cancelamento`: modelos55/65, 2 passes em F4_X13_GREEN.txt
- [x] F4.9 Numeração sequencial concorrente e tratamento de rejeição normal via inutilização, sem reutilizar número usado/contingente — 4e52786/8c83d0f/60a99ad · X12/X14 em duas conexões; `test_x12_rejeicao_normal_tem_faixa_inutilizavel_sem_reusar_numero`, 1 pass em F4_X12_REJEICAO_GREEN.txt
- [x] F4.10 Conferência normativa/documental: pagamentos, CRT, CEST/ST, tributos e limites estaduais — 2e43441/188ad56/1139a1a · F4_AUDITORIA_NORMATIVA.md; limites de MT e campos do pagamento integrado

## Bloco B — simulador local da SEFAZ (obrigatório)

- [x] F4.11 Simulador HTTP SOAP local de autorização, consulta, evento, inutilização e status, sem URL de teste no produto — 4e52786 · 5 RED/8 passes reproduzidos → M01–M12 verdes; suíte391 e depois398 em F4_SIMULADOR_SUITE/FINAL_SUITE.txt
- [x] F4.12 Autorização e rejeição ponta a ponta pela API do PDV (M01, M02, M03) — 4e52786 · simulador M01/M02/M03, XML/protocolo persistidos, consulta de duplicidade sem segunda nota
- [x] F4.13 Falha da SEFAZ não perde venda: conexão recusada permite contingência; timeout/5xx preservam chave normal e consultam, sem reutilização vedada pelo art.18 §2 I da Portaria177/2021 — 8d8cc1b/4e52786 · M04/M05/M12 verdes; F4_SIMULADOR_FINAL_SUITE.txt
- [x] F4.14 Lote em processamento e autorização fora de prazo (M06, M07) — 4e52786 · M06/M07 verdes em F4_SIMULADOR_FINAL_SUITE.txt
- [x] F4.15 Cancelamento: evento homologado e evento rejeitado (M08) — a9dc752/4e52786 · M08, 135 cancela e 573 preserva autorização; X17 prova 503/malformado
- [x] F4.16 Reinício do processo com nota pendente (M11) — 4e52786 · M11 usa subprocesso Python isolado e SQLite reaberto; consulta, sem retransmissão; suíte398
- [x] F4.17 (P20) Implementar `statusServico` (`NfeStatusServico4`) com as URLs oficiais de MT para 65 e 55, homologação e produção. Testes M10 — 9f28f02 · RED 7 falhas → GREEN 7; rota autenticada; A1 inválida não vira 500; suíte 335 no commit
- [x] F4.18 (P19) Inutilização exigida pela Portaria177/2021 art.33: SOAP assinado/XSD, API autenticada, histórico e tela, faixa reservada antes da rede — 5980fe4/8c83d0f/60a99ad · X05/M09, API11 casos e X12 adicional, suíte428; UI4, build/lint0, F4_INUTILIZACAO_API_GREEN.txt e F4_INUTILIZACAO_UI.txt
- [x] F4.19 DANFE: campos do XML, IE, tributos reais quando informados, homologação, avisos por via de contingência, identificação do consumidor e pagamento — 1139a1a/92d589b · 3 RED e complemento4 RED→13 Chromium verdes; build/lint0; F4_DANFE_QA.md, imagens58/80 inspecionadas. Leitura do QR/PDF físico permanece na Fase6

## Bloco C — SEFAZ-MT real em homologação

- [x] F4.20 Precheck lê o cofre e registra presença e validade dos requisitos, com conferência do CNPJ do certificado — e037473 · test_fiscal_precheck.py, dois casos de leitura segura; F4_PRECHECK_REAL.txt
- [x] F4.21 Marker homologacao exclui H01–H09 da suíte padrão; testes leem o cofre local — e037473 · backend/pytest.ini e test_homologacao_real.py; F4_HOMOLOGACAO_BLOQUEADA.txt, 9 skips
- [x] F4.22 Executar precheck, registrar B1–B5 e bloquear H01–H09 — e037473 · F4_PRECHECK_REAL.txt, saída 2; F4_HOMOLOGACAO_BLOQUEADA.txt, 9 skips
- [!] F4.23 Com o precheck verde: rodar H01–H09 em **homologação**, seguindo `docs/TESTE_FISCAL_WINDOWS.md` (testes A–G), e guardar chave, protocolo e `cStat` de cada nota no diário — e037473 · F4_HOMOLOGACAO_BLOQUEADA.txt, B1–B5
- [!] F4.24 Rejeição real da SEFAZ vira pista, teste no simulador (bloco B) e correção, e roda de novo — e037473 · F4_PRECHECK_REAL.txt, B1–B5

## Fechamento

- [x] F4.25 Revisão independente do XML, com rechecagem das correções — 3c388a3 · F4_AUDITORIA_NORMATIVA.md; F4_REVISAO_XML_RED.txt (5 falhas) e evidências GREEN de fiado, consumidor final e intermediador
- [x] F4.26 Atualizar LEGISLACAO_FISCAL_MT, CONTINGENCIA_OFFLINE, TESTE_FISCAL_WINDOWS e CONTADOR — 3c388a3 · git diff --check dos documentos e F4_PORTAO_BACKEND.txt

## Complementos da auditoria

- [x] F4.27 P35/P36: configuração vazia, assinatura falha e cancelamento após contingência; X14/X15 — 990408c/c62400c/4e52786 · persistência/retomada, concorrência em duas conexões, cancelamento após criação antiga em contingência; suíte398 e X13 adicional2 verdes

## Portão de saída

- [x] X01–X13 e M01–M12 ✅ — b92e3aa · F4_PORTAO_BACKEND.txt, 438 verdes; matriz atualizada
- [x] H01–H09 ⛔ B1–B5 — e037473/3c388a3 · F4_HOMOLOGACAO_BLOQUEADA.txt (9 skips) e F4_PRECHECK_REVALIDADO.txt (saída 2)
- [x] Dados da loja em homologação, XMLs sintéticos restritos às fixtures — b92e3aa/3c388a3 · X10 e F4_PRECHECK_REVALIDADO.txt; nenhuma transmissão real executada
- [x] Suítes verdes, plano commitado e push confirmado — 3c388a3 · F4_PORTAO_BACKEND.txt (438), F4_PORTAO_PAINEL.txt (23); git ls-remote: 3c388a3cbef1932d3f71694835814f1c4c7e2330

## Evidências

| Item | Comando | Saída resumida |
|---|---|---|
| Pacote XSD (versão, URL) | Conferência SHA-256 | F4_XSD_ORIGEM.txt |
| Validação XSD (X01–X05) | pytest tests/test_fiscal_xsd.py tests/test_fiscal_inutilizacao.py | Verdes na suíte registrada em F4_PORTAO_BACKEND.txt |
| Simulador (M01–M12) | pytest tests/test_sefaz_simulador.py | Verdes em F4_TIMEOUT_217_GREEN.txt e no portão |
| Precheck | python -X utf8 -I scripts/fiscal_precheck.py | Saída 2, B1–B5 em F4_PRECHECK_REAL.txt |
| Homologação real (H01–H09) | pytest -m homologacao -rs | 9 skips em F4_HOMOLOGACAO_BLOQUEADA.txt |
