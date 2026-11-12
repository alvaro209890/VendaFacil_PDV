# Retomada — estado real em 12/11/2026 10:20 BRT

> Leia junto com `00_PAINEL.md` (placar), `01_REGRAS.md` (regras duras) e `06_DIARIO.md` (histórico).

## Onde parou

| Campo | Valor |
|---|---|
| HEAD local | `c9f6d1d` ou posterior (só docs) — confira com `git log -1` |
| Remoto | `origin/master` sincronizado em 12/11 |
| Fases 0–3 | ✅ concluídas e publicadas |
| Fase 4 | 🟨 **7/27** — F4.1–F4.5, F4.7 e F4.17 fechados |
| Placar | Pistas 32/46 · Testes 80/126 |
| Suíte | backend **347** verde (sem os 2 arquivos RED de F4.11/F4.27), painel 23, E2E 82, Node 29, build/lint 0 |

## O que já está fechado na Fase 4

| Item | Prova | Commit |
|---|---|---|
| F4.1 schemas oficiais | PL_010g v1.03 (26/10/2026) + cancelamento v1.01, 16 XSDs, SHA-256 conferido | `08bbffc` |
| F4.2 X01–X03 | dinheiro, cartão, PIX, fiado, desconto, CPF, ST e NF-e 55 no XSD | `08bbffc` |
| F4.3 X04 | evento de cancelamento assinado valida no schema | `08bbffc` |
| F4.4 X06 | RSA-SHA1/SHA-1/C14N (MOC 7.0 §4.2.4), 1 byte invalida | `08bbffc` |
| F4.5 X07/X08 | QR 2.00 online e contingência com hash recalculado | `08bbffc` |
| F4.7 X10 | `tpAmb` só da configuração + texto de homologação | `08bbffc` |
| F4.17 M10/P20 | `statusServico` 65/55, rota + tela Fiscal; RED 7→GREEN | `9f28f02` |

## O que está aberto AGORA (working tree, sem commit)

| Item | Estado | Arquivos |
|---|---|---|
| F4.11 simulador | 12 testes, **7 verdes / 5 RED**: M05 (503 devolve rejeitada), M08 (evento 135 preso em `processando`), M09 (`inutilizar_numeracao` inexistente), M10×2 (fixture sem certificado) | `backend/tests/sefaz_fake.py`, `backend/tests/test_sefaz_simulador.py` |
| F4.27 P35/P36 | **4 RED**: config vazia não levanta, preflight certificado/itens grava nota, assinatura queima número | `backend/tests/test_fiscal_reserva_regras.py` |
| F4.20 antecipado | `scripts/fiscal_precheck.py` + 2 testes verdes (cofre ausente/inválido); não fechar antes de F4.22 | `scripts/fiscal_precheck.py`, `backend/tests/test_fiscal_precheck.py` |

Esses arquivos estão **untracked de propósito**: a suíte completa fica vermelha com eles. Não commitar antes do GREEN.

## Ordem sugerida

1. **F4.27** — consertar a reserva/numeração (P35/P36) em `fiscal_direto.py`; os 4 testes já descrevem o comportamento. Depois X14/X15 e fechar.
2. **F4.11** — completar o simulador: status na rota, evento 135, resposta 503, fixture com certificado, contrato de inutilização (depende de F4.18). Fechar os 12 M.
3. **F4.6** — escrever X11 (prazo 30 min NFC-e / 2 h NF-e no fuso de MT), que é o único pedaço que falta do item.
4. **F4.8/F4.9** — X13 (nenhum caminho cai em legado) e X12 (numeração sem buraco sob concorrência).
5. **F4.10** — reconferência contra `docs/LEGISLACAO_FISCAL_MT.md` e `docs/VINCULO_PAGAMENTO_MT.md`.
6. **F4.18/F4.19** — inutilização (X05/M09) e cupom DANFE NFC-e.
7. **Bloco B** — M01–M04, M06, M07, M11, M12 com o simulador.
8. **F4.20–F4.26** — precheck, `pytest.ini` com marker `homologacao`, H01–H09 (ou `[!]` B1–B5), revisor fiscal e docs.

## Comandos

```powershell
cd C:\GIS\VendaFacil_PDV\backend
.venv\Scripts\python.exe -X utf8 -I -m pytest -q --tb=short
# enquanto os RED de F4.11/F4.27 existirem, rode a suíte sem eles:
.venv\Scripts\python.exe -X utf8 -I -m pytest -q --tb=short --ignore=tests/test_sefaz_simulador.py --ignore=tests/test_fiscal_reserva_regras.py

cd C:\GIS\VendaFacil_PDV\painel
.venv\Scripts\python.exe -X utf8 -I -m pytest -q --tb=short

cd C:\GIS\VendaFacil_PDV
npm run build
npx eslint .
```

Push (helper efêmero, não grava segredo):

```powershell
git -c credential.helper='!sh "C:/Users/Usuario/AppData/Local/Temp/opencode/git-cred-sd.sh"' push origin master
```

## Regras que continuam valendo

- Um bug = um commit, `git add` por caminho explícito, nunca commitar `dist_exe/VendaFacilPDV.exe`.
- Item só fecha com saída real de comando. Nada de `[x]` por relato.
- Fiscal: bloco A/B obrigatórios; bloco C (SEFAZ real) depende de B1–B5 e fica `[!]` com prova do precheck. Nunca inventar dado fiscal, nunca sair de `homologacao`.
- Segredo não entra em commit, log, diário nem vault.
