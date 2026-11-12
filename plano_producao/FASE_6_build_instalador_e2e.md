# Fase 6 — Build, instalador e ponta a ponta no `.exe`

**Status:** ⏸ concluída com E04–E06 bloqueados por B8; 14/15 fechados e 1 `[!]` · **Depende de:** Fases 1 a 5 · **Pistas:** P12, P17 · **Testes:** E01–E09

## Objetivo

Provar que o que foi testado no código também funciona no executável que vai para a loja.

## Antes de começar

- [x] F6.1 Copiar `%LOCALAPPDATA%\VendaFacilPDV` para um backup datado (se existir) e anotar o caminho no diário — e41771e · F6_BACKUP_DATADO.txt; Robocopy 1, seis arquivos copiados, zero falhas
- [x] F6.2 Conferir que nada está ouvindo na porta 3020; os testes usam a 3021 — e41771e · F6_BACKUP_DATADO.txt; 3020 e 3021 livres, roteiro na 3021

## Tarefas

### Build

- [x] F6.3 Subir a versão para **1.0.13** em `installer/vendafacil.iss` e em todo lugar que a exiba (`grep -rn "1\.0\.12"` antes). A versão aparece na tela de diagnóstico — e41771e · F6_ROTEIRO_EXE.txt; /health informa 1.0.13
- [x] F6.4 `cmd.exe /c "build_exe.bat"` e `cmd.exe /c "installer\build_installer.bat"`. Registrar caminho, tamanho e sha256 dos dois artefatos. **Não commitar os binários** — e41771e · F6_BUILD_EXE/INSTALADOR/ARTEFATOS.txt; compilações saída 0. Recompilado sobre ee491d5 (inclui 054e6d6): exe 39.687.711 bytes SHA-256 E9C13FFEA6845200ED720943C4ABF23D663A273BE1E357E780A2C8F53E27EC01; Setup 39.973.691 bytes SHA-256 4529904B25C61F55981C5D5C2476B048C6F16A686AA355083E5F99C126293A11

### Ponta a ponta no `.exe` (pasta de dados temporária, porta 3021)

- [x] F6.5 Smoke (E01) — e41771e · F6_ROTEIRO_EXE.txt; GET / 200, /health 200, /api/produtos 401
- [x] F6.6 Transformar `docs/TESTE_WINDOWS.md` em script (`scripts/roteiro_exe.py`) contra o `.exe`: primeiro acesso, produtos, importação de XML, venda em cada forma de pagamento, sangria, suprimento, fiado e baixa parcial, cancelamento, fechamento de caixa, relatórios, backup e restauração. Zero resposta 500 (E02) — e41771e · F6_ROTEIRO_EXE.txt; 34 requisições comerciais, zero 5xx. b41e946 · F6_ROTEIRO_EXE_CHROMIUM.txt; roteiro versionado, 49 requisições no executável final, zero 5xx
- [x] F6.7 Sem rede: repetir venda, cancelamento, fechamento e reimpressão com a SEFAZ inalcançável; religar (simulador) e conciliar (E03) — e41771e/054e6d6 · venda, cancelamento, fechamento e conciliação passaram no executável; b41e946 · F6_ROTEIRO_EXE_CHROMIUM.txt; no executável final, 2 vendas em contingência pela tela, impressão e reimpressão, cancelamento, fechamento, reinício e conciliação das 2 notas com o mesmo número, chave e XML
- [x] F6.8 Reinício: fechar o `.exe` com venda no carrinho e com nota pendente; reabrir e conferir — e41771e · F6_ROTEIRO_EXE.txt prova reinício com nota; b41e946 · F6_ROTEIRO_EXE_CHROMIUM.txt; "o carrinho reapareceu no executável reiniciado" e notas conciliadas após reinício

### Cupom (P12)

- [x] F6.9 Gerar o cupom em PDF em 58 mm e 80 mm pela impressão do navegador: acentuação, QR legível por leitor, chave, protocolo, segunda via e marcação de contingência (E07, E08, E09). Teste em papel fica em B7 — ee491d5/b41e946 · F6_ROTEIRO_EXE_CHROMIUM.txt; 4/4 PDFs (contingência e autorizada × 58/80 mm), 6 QR decodificados iguais ao qrcode_url da nota; o 80 mm partia um bloco da chave, corrigido em ee491d5 (F6_CHAVE_RED/GREEN)

### Instalador (P17)

- [x] F6.10 Criar `scripts/teste_instalador.ps1`: instala a versão anterior, cria dados, instala a 1.0.13 por cima, desinstala; em cada etapa confere pasta do programa, atalhos e contagens do SQLite — b41e946 · F6_INSTALADOR_B8.txt; versionado, Parser.ParseFile com 0 erros, Setups 1.0.12 e 1.0.13 presentes com SHA-256
- [!] F6.11 Rodar o script. Sem elevação → `[!]` B8, com o script pronto para o Álvaro rodar como administrador (E04, E05, E06) — B8 · F6_INSTALADOR_B8.txt; revalidado em b41e946: IsInRole(Administrator)=False, saída 2, nenhum Setup executado; comando para o Álvaro registrado na evidência
- [x] F6.12 Sem elevação, provar o que dá sem instalar: o `.exe` 1.0.13 abre um banco criado pelo `.exe` anterior (migração aditiva) e nenhuma contagem muda — e41771e · F6_MIGRACAO.txt; contagens iguais com o executável local anterior

### Fechamento

- [x] F6.13 Rodar as duas suítes uma última vez sobre o commit final e registrar os números — b41e946 · F6_PORTAO_BACKEND/PAINEL/FRONT/NODE/E2E(_RERUN).txt; backend 460 verdes e 9 desmarcados, painel 23, Node 36, build/lint 0, E2E 87 verdes na rodada única + as 2 falhas de preparação sob carga verdes ao repetir os arquivos (15/15)

## Complementos da auditoria

- [x] F6.14 P33: impressão espera imagens e afterprint antes de remover iframe; E10 — eb55f20 · F6_E10_RED/GREEN.txt; espera imagem e afterprint
- [x] F6.15 E11: chave de acesso do DANFE sem bloco de 4 dígitos partido em 58 e 80 mm — ee491d5 · F6_CHAVE_RED.txt (80 mm partia "4249") → F6_CHAVE_GREEN.txt (9 Chromium verdes)

## Portão de saída

- [x] E01–E03 e E07–E09 ✅; E04–E06 ⛔ B8
- [x] Artefatos no disco com sha256 registrado; nenhum binário novo no git (`git status --porcelain` conferido: só ` M dist_exe/VendaFacilPDV.exe`, já trackeado, fora dos commits)
- [x] `docs/TESTE_WINDOWS.md`, `docs/INSTALACAO_WINDOWS.md` e `docs/BUILD_WINDOWS.md` atualizados
- [x] Pasta do plano commitada e `git push origin master`

## Evidências

| Item | Comando | Saída resumida |
|---|---|---|
| Instalador (caminho, tamanho, sha256) | `Get-FileHash -Algorithm SHA256` | `dist_installer\VendaFacilPDV-Setup-1.0.13.exe`, 39.973.691 bytes, 4529904B25C61F55981C5D5C2476B048C6F16A686AA355083E5F99C126293A11 |
| `.exe` (caminho, tamanho, sha256) | `Get-FileHash -Algorithm SHA256` | `dist_exe\VendaFacilPDV.exe`, 39.687.711 bytes, E9C13FFEA6845200ED720943C4ABF23D663A273BE1E357E780A2C8F53E27EC01 |
| Roteiro (E02): requisições, respostas 500 | `scripts/roteiro_exe.py --chromium --cupons ...` | 49 requisições, 0 respostas 5xx, saída 0 |
| Offline (E03) | mesmo comando, SEFAZ sintética desligada → religada | 2 notas em contingência conciliadas após reinício, mesmo número/chave/XML |
| Instalador (E04–E06) | `scripts/teste_instalador.ps1` | B8: sessão sem elevação, saída 2 |
