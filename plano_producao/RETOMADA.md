# Retomada — VendaFácil PDV

Pausado a pedido do Álvaro em 12/11/2026. Retomar na Fase 6 somente quando solicitado.

| Campo | Situação |
|---|---|
| Fases 0–3 | Concluídas e publicadas |
| Fase 4 | Portão publicado em cc5deb3; H01–H09 bloqueados por B1–B5 |
| Fase 5 | Portão publicado em f97eb6a; 459 backend verdes, 9 desmarcados, 23 painel verdes |
| Fase 6 | Build 1.0.13 em e41771e. 054e6d6 corrigiu a reimpressão após contingência e passou 7 testes Chromium |
| Fase 7 | Pendente |

O instalador 1.0.13 gerado em e41771e está em `C:\GIS\VendaFacil_PDV\dist_installer\VendaFacilPDV-Setup-1.0.13.exe` (40.136.851 bytes, SHA-256 `408C9EED6303547E83F685C1EC8B183D35BA6C1B24B46B3681878379ED44C6F5`). Essa compilação antecede a correção de reimpressão de 054e6d6. O roteiro HTTP do executável passou com 46 requisições e zero respostas 5xx, incluindo conciliação da nota após reinício. O banco do executável local anterior abriu na 1.0.13 com contagens iguais. Consulte F6_ARTEFATOS, F6_ROTEIRO_EXE e F6_MIGRACAO em `evidencias/`.

## Próximo ponto

1. Recompilar os dois artefatos após 054e6d6 e atualizar os hashes.
2. Validar `scripts/roteiro_exe.py --chromium --cupons output/fase6/notas-simuladas.json` contra a compilação nova, com TEMP/TMP/TMPDIR fora da árvore do Vite. A opção --chromium e `scripts/roteiro_exe_chromium.mjs` foram preparadas localmente. A validação HTTP e a migração já rodaram sem essa opção.
3. Gerar e verificar PDFs 58/80 mm e contingência, rodar as suítes finais e fechar a Fase 6. O teste de instalação exige B8. `scripts/teste_instalador.ps1` passou pela leitura sintática e retornou saída 2 em sessão sem elevação.
4. Executar a Fase 7 e publicar somente após os portões.

Arquivos locais novos do roteiro e do instalador estão preservados para revisão e commit após validação. Os binários, rascunhos, diretórios scratch e a alteração preexistente em F3_22_RED.txt ficam fora dos commits.

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
