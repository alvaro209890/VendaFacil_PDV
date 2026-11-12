# Retomada — estado real em 12/11/2026 14:15 BRT

> Leia junto com `00_PAINEL.md` (placar), `01_REGRAS.md` (regras duras) e `06_DIARIO.md` (histórico).

## Onde parou

| Campo | Valor |
|---|---|
| HEAD local | `c62400c` ou posterior (os commits seguintes são só docs) — confira com `git log -1` |
| Remoto | `origin/master` sincronizado em 12/11 |
| Fases 0–3 | ✅ concluídas e publicadas |
| Fase 4 | 🟨 **7/27** — F4.1–F4.5, F4.7 e F4.17 fechados; F4.27 quase fechado |
| Placar | Pistas 34/46 · Testes 81/126 |
| Suíte | backend **355** verde (sem `test_sefaz_simulador.py`), painel 23, E2E 82, Node 29, build/lint 0 |

## Fechado recentemente

| Item | Prova | Commit |
|---|---|---|
| P35 / F4.27 (parte) | preflight antes de reservar, erro local libera o número e a retomada reusa a mesma reserva; 4 casos | `990408c` |
| P36 / X15 | prazo de cancelamento conta de `autorizado_em` (fallback `criado_em`); 4 casos | `c62400c` |
| F4.1–F4.5/F4.7 | XSD oficial + X01–X10 | `08bbffc` |
| F4.17 | `statusServico` 65/55, rota e tela | `9f28f02` |

## Aberto agora

| Item | Estado |
|---|---|
| F4.27 | falta só **cancelamento após contingência** (X14); persistência/retomada já provadas |
| X14 (matriz) | falta o caso **concorrente explícito** de reserva |
| F4.11 simulador | 12 testes, **5 RED**: M05 (503 devolve rejeitada), M08 (evento 135 preso em `processando`), M09 (`inutilizar_numeracao` inexistente), M10×2 (fixture sem certificado) |
| F4.20 | `scripts/fiscal_precheck.py` + 2 testes verdes, ainda não fechado (fechar junto do F4.22) |

**Untracked de propósito** (não commitar antes do GREEN): `backend/tests/sefaz_fake.py`, `backend/tests/test_sefaz_simulador.py`, `backend/tests/test_fiscal_precheck.py`, `scripts/`.

## Ordem sugerida

1. **F4.11** — completar o simulador: status na rota, evento 135, resposta 503, fixture com certificado e contrato de inutilização. Fechar os 12 M.
2. **F4.27** — teste de cancelamento após contingência (e o caso concorrente do X14); fechar o item.
3. **F4.6** — X11 (prazo no fuso) já está coberto por X15; conferir e fechar.
4. **F4.8/F4.9** — X13 (nenhum caminho cai em legado) e X12 (numeração sem buraco sob concorrência).
5. **F4.10** — reconferir `docs/LEGISLACAO_FISCAL_MT.md` e `docs/VINCULO_PAGAMENTO_MT.md`.
6. **F4.18/F4.19** — inutilização (X05/M09) e cupom DANFE NFC-e.
7. **Bloco B** — M01–M04, M06, M07, M11, M12.
8. **F4.20–F4.26** — precheck, `pytest.ini` com marker `homologacao`, H01–H09 (ou `[!]` B1–B5), revisor e docs.

## Comandos

```powershell
cd C:\GIS\VendaFacil_PDV\backend
.venv\Scripts\python.exe -X utf8 -I -m pytest -q --tb=short --ignore=tests/test_sefaz_simulador.py

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

- Um bug = um commit; `git add` por caminho explícito; nunca commitar `dist_exe/VendaFacilPDV.exe`.
- Item só fecha com saída real de comando e a linha `— <commit> · <teste>`.
- Fiscal: blocos A/B obrigatórios; bloco C (SEFAZ real) depende de B1–B5 e fica `[!]` com prova do precheck. Nunca inventar dado fiscal, nunca sair de `homologacao`.
- Segredo não entra em commit, log, diário nem vault.
