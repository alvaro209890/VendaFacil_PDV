# Regras

## Onde executar

O Hermes que recebe o WhatsApp é o da AWS. Este trabalho é do PC Windows `pcque001imap`, repositório `C:\GIS\VendaFacil_PDV`. Entrar por SSH nesse PC e editar aqui. Não compilar o `.exe` na Lightsail (2 GB, sem Inno Setup). O instalador de amanhã sai do GitHub Actions no `master`.

Se o SSH neste PC não conectar: uma mensagem no WhatsApp e pare. Não porte o build para Linux.

## Ambiente

| Item | Valor |
|---|---|
| Repo | `C:\GIS\VendaFacil_PDV`, GitHub `alvaro209890/VendaFacil_PDV`, branch `master` |
| Versão hoje | `1.0.14` em `backend/version.py`, `installer/vendafacil.iss`, `scripts/roteiro_exe.py` |
| Versão desta entrega | `1.0.15` |
| Backend | `backend\.venv\Scripts\python.exe -X utf8 -I -m pytest -q --tb=short` a partir de `backend/`, sem `PYTHONPATH` |
| Front | `npm run build` e `npx eslint .` na raiz |
| PDV isolado | `VENDAFACIL_DATA_DIR` numa pasta temporária, `VENDAFACIL_PORT=3021`, `VENDAFACIL_NO_BROWSER=1`, `VENDAFACIL_PAINEL_URL` vazio |
| Instalador | workflow `.github/workflows/build-exe.yml` no push do `master`. Artefato em Actions. Não commitar `dist_exe/` nem `dist_installer/` |

No git-bash o pytest é `cd backend && env -u PYTHONPATH .venv/Scripts/python -X utf8 -I -m pytest -q --tb=short`.

## Duras

1. Português, curto, tabela em vez de textão. Resposta de WhatsApp em poucas linhas.
2. Um assunto = um commit no `master`, mensagem em português, teste de regressão no mesmo commit. O teste falha antes da correção.
3. `git add` por caminho. Nunca `git add -A` nem `git add .`. Não commitar binário, `dados/`, `dist_exe/`, `dist_installer/`, `build/`, segredo, `*.pfx`, `Dados_James/`.
4. Push de `origin/master` uma vez, no portão final, com a suíte verde. Sem pull request.
5. Fiscal permanece em `homologacao`. Não inventar CNPJ, IE, CSC nem certificado. Não usar certificado da Pamera nem o do James. Esta entrega não chama a SEFAZ.
6. Não apontar o PDV para a VPS. Não mudar `VENDAFACIL_PAINEL_URL` nem `backend/painel_config.py`.
7. Não tocar o banco real `%LOCALAPPDATA%\VendaFacilPDV\dados`.
8. Não migrar `REAL` para centavos. Patch cirúrgico. `backend/database.py` é serial: um editor por vez.
9. Produto sem a opção nova permanece com o comportamento de hoje, inclusive KG, G, LT e ML.
10. Decisão de produto desta entrega já está em `02_ESPECIFICACAO.md`. Não perguntar no meio. Dúvida que não mexe em dinheiro nem estoque: escolha a opção que preserva o comportamento atual, anote no diário e siga.
11. Subagente é pista. Quem commita é você, depois de rodar o teste.
12. Fora de escopo: `painel/` (salvo prova de que não quebrou, se for alterado), SIMCAR, outros repos em `C:\GIS\`, certificado e download de XML na SEFAZ.

## Autonomia

Erro de teste, porta ocupada, dependência e arquivo travado não param o goal. Diagnostique e continue. Pergunta ao Álvaro só no fim, numa lista, e só se o portão não fechar sem ele.
