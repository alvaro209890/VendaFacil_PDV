# Retomada — VendaFácil PDV

| Campo | Situação |
|---|---|
| Branch | master; retomada em e037473 |
| Fases 0–3 | Concluídas e publicadas |
| Fase 4 | 25/27 fechados, portão publicado em 3c388a3 |
| Homologação | F4.23/F4.24 e H01–H09 bloqueados por B1–B5; precheck saída 2 e 9 skips |
| Suítes registradas | Backend 459 verdes e 9 desmarcados, painel 23 verdes |

A Fase 5 passou com 459 backend e 23 painel. Retomar pela Fase 6 (backup datado, build e instalador 1.0.13).

O binário, o rascunho, os diretórios scratch e a alteração preexistente em F3_22_RED.txt ficam fora dos commits.
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
