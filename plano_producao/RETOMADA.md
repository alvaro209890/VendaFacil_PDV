# Retomada — VendaFácil PDV

Entrega concluída em 12/11/2026: **⏸ aguardando terceiro**. Todas as fases fechadas; o que falta depende de B1–B5, B7, B8 e B9.

| Campo | Situação |
|---|---|
| Fases 0–3 | Concluídas e publicadas |
| Fase 4 | Portão cc5deb3/3c388a3; H01–H09 bloqueados por B1–B5 |
| Fase 5 | Portão f97eb6a |
| Fase 6 | Portão 954dac8, com E04–E06 em B8 |
| Fase 7 | Concluída e publicada em 4f6b151; relatório em `RELATORIO_FINAL.md`; vault a40cdae |

Instalador: `C:\GIS\VendaFacil_PDV\dist_installer\VendaFacilPDV-Setup-1.0.13.exe` (39.974.387 bytes, SHA-256 `C0B55A78D17C221074F4AE68373B0A283C89A33AE8E923A3A575A05EF86109F9`). Executável: `dist_exe\VendaFacilPDV.exe` (39.688.485 bytes, SHA-256 `E899D8FBD0CD060FA5B2C68010C658B953F413A7CCBD2708A16FA091F1F77683`). Ambos gerados sobre 808c5cb (inclui D3). Evidências F6_ARTEFATOS, F6_ROTEIRO_EXE_CHROMIUM, F6_MIGRACAO, F6_PORTAO_* e F7_E2E_FINAL.

## Próximo ponto

1. Quando o Álvaro cadastrar A1, CSC e dados da empresa (homologação): rodar `scripts/fiscal_precheck.py` e executar H01–H09 (`pytest -m homologacao`).
2. Em máquina descartável, elevado: `scripts/teste_instalador.ps1` (E04–E06).
3. Se mudar algo em `src/`, recompilar exe e Setup e refazer `roteiro_exe.py --chromium` + `verificar_cupons_pdf.py`.

## Comandos

```powershell
cd C:\GIS\VendaFacil_PDV\backend
.venv\Scripts\python.exe -X utf8 -I -m pytest -q --tb=short

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
