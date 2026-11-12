# Retomada — VendaFácil PDV

| Campo | Situação |
|---|---|
| Branch | master; retomada em e037473 |
| Fases 0–3 | Concluídas e publicadas |
| Fase 4 | 23/27 fechados, incluindo F4.20–F4.22 |
| Homologação | F4.23/F4.24 e H01–H09 bloqueados por B1–B5; precheck saída 2 e 9 skips |
| Suítes registradas | Backend 432 verdes e 9 desmarcados, painel 23 verdes |

1. Validar as regressões de duplicidade 204/539 e retomada após 217 com consulta e XML assinado.
2. Concluir a revisão independente F4.25, a documentação F4.26 e o portão fiscal.
3. Executar em ordem as Fases 5–7.

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
