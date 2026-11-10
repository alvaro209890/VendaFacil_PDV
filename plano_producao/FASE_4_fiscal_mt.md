# Fase 4 — Fiscal de Mato Grosso (NFC-e 65 e NF-e 55)

**Status:** ⬜ não iniciada · **Depende de:** Fase 1 (dinheiro) · **Pistas:** P9, P15, P19, P20, P22 · **Testes:** X01–X13, M01–M12, H01–H09

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

- [ ] F4.1 (P9) Baixar o pacote oficial de schemas da NF-e/NFC-e 4.00 no Portal Nacional da NF-e, guardar em `backend/tests/xsd/` e registrar no diário a versão do pacote, a URL e a data. Só fonte oficial
- [ ] F4.2 (P9) Auxiliar de teste que valida qualquer XML gerado contra o XSD (`lxml`). Testes X01, X02, X03
- [ ] F4.3 Validar no XSD o evento de cancelamento (X04)
- [ ] F4.4 Assinatura: verificação com a chave pública, adulteração de 1 byte e algoritmos conforme o Manual de Orientação do Contribuinte (X06). Citar no diário a seção do manual usada
- [ ] F4.5 QR Code 2.00 online e de contingência: recalcular o hash do CSC e conferir cada parâmetro com a especificação (X07, X08)
- [ ] F4.6 (P15) Fuso de MT: `dhEmi`, chave de acesso, virada de mês e prazos de cancelamento (X09, X11). Conferir que venda (UTC) e nota (`agora_mt`) não divergem de dia
- [ ] F4.7 Ambiente: `tpAmb` só da configuração; texto obrigatório de homologação conforme o manual (X10). Conferir que nada troca o ambiente sozinho
- [ ] F4.8 (P22) Com `sefaz_mt_direto` configurado, nenhum caminho cai em gateway legado (X13)
- [ ] F4.9 Numeração: sequencial sem buraco sob concorrência; número de nota rejeitada tem tratamento definido (X12)
- [ ] F4.10 Reconferir contra `docs/LEGISLACAO_FISCAL_MT.md` e `docs/VINCULO_PAGAMENTO_MT.md`: `tPag`, grupo `<card>`, `CRT`, CEST/ST, Lei 12.741, limite de R$ 10 mil sem consumidor identificado. O que o doc afirma e o código não faz vira pista

## Bloco B — simulador local da SEFAZ (obrigatório)

- [ ] F4.11 Criar o simulador (`backend/tests/sefaz_fake.py`): servidor HTTP local que responde os serviços SOAP com respostas no formato real (autorização, consulta, evento, inutilização, status). Os testes apontam o dicionário de webservices de `fiscal_direto.py` para ele; **nenhuma opção de "URL de teste" entra na tela nem na configuração do produto**
- [ ] F4.12 Autorização e rejeição ponta a ponta pela API do PDV (M01, M02, M03)
- [ ] F4.13 Falha da SEFAZ não perde venda: timeout e HTTP 5xx viram contingência; o loop transmite depois; sem nota duplicada (M04, M05, M12)
- [ ] F4.14 Lote em processamento e autorização fora de prazo (M06, M07)
- [ ] F4.15 Cancelamento: evento homologado e evento rejeitado (M08)
- [ ] F4.16 Reinício do processo com nota pendente (M11)
- [ ] F4.17 (P20) Implementar `statusServico` (`NfeStatusServico4`) com as URLs oficiais de MT para 65 e 55, homologação e produção. Testes M10
- [ ] F4.18 (P19) Inutilização de numeração: conferir no manual e na SEFAZ-MT a exigência atual para NFC-e; implementar o pedido (`NfeInutilizacao4`), a rota e o ponto na tela Fiscal. Testes X05 e M09. Se a regra vigente dispensar, descartar com a citação da norma
- [ ] F4.19 Cupom fiscal (`src/lib/recibo.ts`): conferir os campos obrigatórios do DANFE NFC-e (emitente, itens, totais, forma de pagamento, chave, protocolo, QR, consumidor, tributos, marcação de contingência e de homologação) contra a especificação

## Bloco C — SEFAZ-MT real em homologação

- [ ] F4.20 Criar `scripts/fiscal_precheck.py`: lê o cofre local e imprime **só** presença e validade — certificado (titular, CNPJ, vencimento), CSC e ID, dados da empresa, ambiente, CNPJ do certificado igual ao do emitente. Nunca imprime segredo
- [ ] F4.21 Criar `pytest.ini` com o marker `homologacao` (fora da execução padrão) e os testes H01–H09 lendo tudo do cofre local
- [ ] F4.22 Rodar o precheck. Faltou item da loja → marcar H01–H09 ⛔ com o código (B1–B5), registrar em `04_BLOQUEIOS.md` e **seguir para a Fase 5**
- [ ] F4.23 Com o precheck verde: rodar H01–H09 em **homologação**, seguindo `docs/TESTE_FISCAL_WINDOWS.md` (testes A–G), e guardar chave, protocolo e `cStat` de cada nota no diário
- [ ] F4.24 Rejeição real da SEFAZ vira pista, teste no simulador (bloco B) e correção, e roda de novo

## Fechamento

- [ ] F4.25 Revisor adversário fiscal: um subagente lê o XML gerado contra o manual, campo a campo, atrás de rejeições conhecidas
- [ ] F4.26 Atualizar `docs/LEGISLACAO_FISCAL_MT.md`, `docs/CONTINGENCIA_OFFLINE.md`, `docs/TESTE_FISCAL_WINDOWS.md` e `docs/CONTADOR.md` com o que mudou (inutilização, status do serviço, precheck)

## Complementos da auditoria

- [ ] F4.27 P35/P36: configuração vazia, assinatura falha e cancelamento após contingência; X14/X15

## Portão de saída

- [ ] X01–X13 e M01–M12 ✅ — **sem exceção**
- [ ] H01–H09 ✅, ou ⛔ com bloqueio registrado e prova do precheck
- [ ] Nenhum dado fiscal fictício fora de `backend/tests/`; `ambiente` segue `homologacao`
- [ ] Suítes verdes; pasta do plano commitada e `git push origin master`

## Evidências

| Item | Comando | Saída resumida |
|---|---|---|
| Pacote XSD (versão, URL) | | |
| Validação XSD (X01–X05) | | |
| Simulador (M01–M12) | | |
| Precheck | | |
| Homologação real (H01–H09) | | |
