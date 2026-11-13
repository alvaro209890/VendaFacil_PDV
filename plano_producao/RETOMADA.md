# Retomada — VendaFácil PDV

Entrega concluída em 12/11/2026: **⏸ aguardando terceiro**. Todas as fases fechadas; o que falta depende de B1–B5, B7, B8 e B9. Em 12/11 à noite o A1/CSC do James foram cadastrados, a transmissão real foi exercitada e quatro defeitos de NFC-e de MT foram corrigidos (`9d75ade`); o bloqueio restante do fiscal é cadastral (cStat 230, ver `04_BLOQUEIOS.md`).

| Campo | Situação |
|---|---|
| Fases 0–3 | Concluídas e publicadas |
| Fase 4 | Portão cc5deb3/3c388a3; H01–H09 bloqueados por B3 (cStat 230) e B5 |
| Fase 5 | Portão f97eb6a |
| Fase 6 | Portão 954dac8, com E04–E06 em B8 |
| Fase 7 | Concluída e publicada em 4f6b151; relatório em `RELATORIO_FINAL.md`; vault a40cdae |

Instalador: `C:\GIS\VendaFacil_PDV\dist_installer\VendaFacilPDV-Setup-1.0.13.exe` (39.979.931 bytes, SHA-256 `BD274911BB17EED2FA889EFCC9D328046E21385CB549FACDABD799AC5E935952`). Executável: `dist_exe\VendaFacilPDV.exe` (39.694.181 bytes, SHA-256 `7C8ED7F79BF3DD6658053AEEFE09BF1185432DD8CD3DC3CC05B1A0C8049E0F2F`). Rebuild de 12/11 20:55 sobre 9d75ade (correções de NFC-e de MT); o build anterior (808c5cb) tinha Setup C0B55A78… e exe E899D8FB…. Evidências F6_ARTEFATOS, F6_ROTEIRO_EXE_CHROMIUM, F6_MIGRACAO, F6_PORTAO_* e F7_E2E_FINAL.

## Próximo ponto

1. O A1, o CSC e os dados da empresa já estão no cofre de teste; o precheck acusa apenas B3 (cStat 230 — IE não cadastrada **no ambiente de homologação**) e B5 (Mercado Pago). Pedir ao contador a atualização do cadastro da IE na SEFAZ-MT; depois rodar `scripts/fiscal_precheck.py` e `pytest -m homologacao`. O passo a passo, a explicação e a mensagem pronta para o contador estão em `docs/IE_NFCE_AMBIENTES.md`.
2. Em máquina descartável, elevado: `scripts/teste_instalador.ps1` (E04–E06).
3. Se mudar algo no backend ou em `src/`, recompilar exe e Setup e refazer `roteiro_exe.py --chromium` + `verificar_cupons_pdf.py`.

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
