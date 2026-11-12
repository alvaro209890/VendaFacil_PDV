# Fase 6 — Build, instalador e ponta a ponta no `.exe`

**Status:** 🟨 pausada a pedido do Álvaro; 7/14 validados · **Depende de:** Fases 1 a 5 · **Pistas:** P12, P17 · **Testes:** E01–E09

## Objetivo

Provar que o que foi testado no código também funciona no executável que vai para a loja.

## Antes de começar

- [x] F6.1 Copiar `%LOCALAPPDATA%\VendaFacilPDV` para um backup datado (se existir) e anotar o caminho no diário — e41771e · F6_BACKUP_DATADO.txt; Robocopy 1, seis arquivos copiados, zero falhas
- [x] F6.2 Conferir que nada está ouvindo na porta 3020; os testes usam a 3021 — e41771e · F6_BACKUP_DATADO.txt; 3020 e 3021 livres, roteiro na 3021

## Tarefas

### Build

- [x] F6.3 Subir a versão para **1.0.13** em `installer/vendafacil.iss` e em todo lugar que a exiba (`grep -rn "1\.0\.12"` antes). A versão aparece na tela de diagnóstico — e41771e · F6_ROTEIRO_EXE.txt; /health informa 1.0.13
- [x] F6.4 `cmd.exe /c "build_exe.bat"` e `cmd.exe /c "installer\build_installer.bat"`. Registrar caminho, tamanho e sha256 dos dois artefatos. **Não commitar os binários** — e41771e · F6_BUILD_EXE/INSTALADOR/ARTEFATOS.txt; compilações saída 0, recompilar após 054e6d6

### Ponta a ponta no `.exe` (pasta de dados temporária, porta 3021)

- [x] F6.5 Smoke (E01) — e41771e · F6_ROTEIRO_EXE.txt; GET / 200, /health 200, /api/produtos 401
- [~] F6.6 Transformar `docs/TESTE_WINDOWS.md` em script (`scripts/roteiro_exe.py`) contra o `.exe`: primeiro acesso, produtos, importação de XML, venda em cada forma de pagamento, sangria, suprimento, fiado e baixa parcial, cancelamento, fechamento de caixa, relatórios, backup e restauração. Zero resposta 500 (E02) — e41771e · F6_ROTEIRO_EXE.txt; 34 requisições comerciais, zero 5xx; roteiro local, falta versionar
- [~] F6.7 Sem rede: repetir venda, cancelamento, fechamento e reimpressão com a SEFAZ inalcançável; religar (simulador) e conciliar (E03) — e41771e/054e6d6 · venda, cancelamento, fechamento e conciliação passaram no executável; botão validado no Chromium em dev, falta rodar --chromium no novo build
- [~] F6.8 Reinício: fechar o `.exe` com venda no carrinho e com nota pendente; reabrir e conferir — e41771e · F6_ROTEIRO_EXE.txt prova reinício com nota; carrinho preparado no script Chromium, aguarda execução

### Cupom (P12)

- [ ] F6.9 Gerar o cupom em PDF em 58 mm e 80 mm pela impressão do navegador: acentuação, QR legível por leitor, chave, protocolo, segunda via e marcação de contingência (E07, E08, E09). Teste em papel fica em B7

### Instalador (P17)

- [~] F6.10 Criar `scripts/teste_instalador.ps1`: instala a versão anterior, cria dados, instala a 1.0.13 por cima, desinstala; em cada etapa confere pasta do programa, atalhos e contagens do SQLite — script local com leitura sintática OK, aguarda versionar e executar
- [!] F6.11 Rodar o script. Sem elevação → `[!]` B8, com o script pronto para o Álvaro rodar como administrador (E04, E05, E06) — B8 · F6_INSTALADOR_B8.txt; saída 2, sessão sem elevação
- [x] F6.12 Sem elevação, provar o que dá sem instalar: o `.exe` 1.0.13 abre um banco criado pelo `.exe` anterior (migração aditiva) e nenhuma contagem muda — e41771e · F6_MIGRACAO.txt; contagens iguais com o executável local anterior

### Fechamento

- [ ] F6.13 Rodar as duas suítes uma última vez sobre o commit final e registrar os números

## Complementos da auditoria

- [x] F6.14 P33: impressão espera imagens e afterprint antes de remover iframe; E10 — eb55f20 · F6_E10_RED/GREEN.txt; espera imagem e afterprint

## Portão de saída

- [ ] E01–E03 e E07–E09 ✅; E04–E06 ✅ ou ⛔ B8
- [ ] Artefatos no disco com sha256 registrado; nenhum binário novo no git (`git status --porcelain` conferido)
- [ ] `docs/TESTE_WINDOWS.md`, `docs/INSTALACAO_WINDOWS.md` e `docs/BUILD_WINDOWS.md` atualizados
- [ ] Pasta do plano commitada e `git push origin master`

## Evidências

| Item | Comando | Saída resumida |
|---|---|---|
| Instalador (caminho, tamanho, sha256) | | |
| `.exe` (caminho, tamanho, sha256) | | |
| Roteiro (E02): requisições, respostas 500 | | |
| Offline (E03) | | |
| Instalador (E04–E06) | | |
