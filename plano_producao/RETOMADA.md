# Retomada — VendaFácil PDV

Retomado em 12/11/2026. Fase 6 fechada com E04–E06 em B8; Fase 7 em andamento.

| Campo | Situação |
|---|---|
| Fases 0–3 | Concluídas e publicadas |
| Fase 4 | Portão publicado em cc5deb3; H01–H09 bloqueados por B1–B5 |
| Fase 5 | Portão publicado em f97eb6a |
| Fase 6 | Portão com B8. Build 1.0.13 sobre ee491d5 (inclui 054e6d6). Roteiro do exe e PDFs verdes em b41e946 |
| Fase 7 | Em andamento |

Instalador: `C:\GIS\VendaFacil_PDV\dist_installer\VendaFacilPDV-Setup-1.0.13.exe` (39.973.691 bytes, SHA-256 `4529904B25C61F55981C5D5C2476B048C6F16A686AA355083E5F99C126293A11`). Executável: `dist_exe\VendaFacilPDV.exe` (39.687.711 bytes, SHA-256 `E9C13FFEA6845200ED720943C4ABF23D663A273BE1E357E780A2C8F53E27EC01`). Evidências F6_ARTEFATOS, F6_ROTEIRO_EXE_CHROMIUM e F6_PORTAO_*.

## Próximo ponto

1. Fase 7 inteira (docs da loja, revisão, checklist, CLAUDE.md, relatório final, painel, vault) e push.
2. Pendências de terceiros: B1–B5 (H01–H09), B7 (papel), B8 (`scripts/teste_instalador.ps1` elevado), B9 (implantação).

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
