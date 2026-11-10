# Regras

## 1. Ambiente

| Item | Valor |
|---|---|
| Repositório | `C:\GIS\VendaFacil_PDV` (GitHub `alvaro209890/VendaFacil_PDV`, público), branch `master` |
| Toolchain | Node 22 · npm 10 · Python 3.11 (`py -3.11`) · Inno Setup 6 (`C:\Program Files (x86)\Inno Setup 6\ISCC.exe`) |
| Shell do agente | bash (git-bash). `.bat` roda com `cmd.exe /c "arquivo.bat"` |
| Testes backend | `cd backend && env -u PYTHONPATH .venv/Scripts/python -I -m pytest -q` |
| Testes painel | `cd painel && env -u PYTHONPATH .venv/Scripts/python -I -m pytest -q` (o venv é criado na Fase 0) |
| Front | `npm run build` · `npx eslint .` |
| Build do `.exe` | `cmd.exe /c "build_exe.bat"` → `dist_exe\VendaFacilPDV.exe` |
| Build do instalador | `cmd.exe /c "installer\build_installer.bat"` → `dist_installer\VendaFacilPDV-Setup-<versão>.exe` |
| Rodar isolado | `VENDAFACIL_DATA_DIR=<pasta temporária>` · `VENDAFACIL_PORT=3021` · `VENDAFACIL_NO_BROWSER=1` |
| Dados reais do `.exe` | `%LOCALAPPDATA%\VendaFacilPDV\dados` (banco, backups, `jwt_secret.key`) |

Arquitetura em uma linha: `.exe` único (FastAPI em `127.0.0.1:3020` servindo o React embutido) + SQLite local. `backend/database.py` concentra todo o acesso ao banco. `painel/` é o SaaS de licença e **não entra no `.exe`**.

**Isolamento medido na Fase 0:** o processo do Hermes herda `PYTHONPATH` com bibliotecas de outro Python. Execute também as instalações com `env -u PYTHONPATH .venv/Scripts/python -I -m pip ...`; não use o `pip` global. `-I` evita carregar extensões de ABI incompatível.

## 2. Regras duras

1. Português, curto, tabela em vez de textão.
2. **Um bug = um commit** no `master`, mensagem em português, com o teste de regressão junto. O teste precisa **falhar antes** da correção.
3. `git add` **sempre por caminho explícito**. Nunca `git add -A` nem `git add .`: o build altera `dist_exe/VendaFacilPDV.exe`, que está trackeado. **Não commitar binário novo.**
4. `git push origin master` só no fim de cada fase, com as duas suítes verdes.
5. **Nunca inventar dado fiscal** (CNPJ, IE, CSC, certificado) fora de fixture de teste. Nunca desligar validação para o teste passar.
6. **Certificado:** só o A1 da própria mercearia, já gravado no cofre local do PDV. Qualquer outro certificado que exista neste PC (inclusive o da RT Pamera) é **proibido**. Certificado autoassinado só dentro de `backend/tests/`.
7. `ambiente` fica em **`homologacao`**. Produção só por ordem explícita do Álvaro.
8. **Offline-first é requisito fiscal.** Nada no caminho da venda pode depender de rede.
9. Segredo não entra em commit, log, relatório, diário nem vault (o vault é público). Para provar que existe, mostre presença (`sim/não`), tamanho ou validade — nunca o valor.
10. Testes nunca tocam os dados reais (use as variáveis da tabela acima). Antes da Fase 6, copie `%LOCALAPPDATA%\VendaFacilPDV` para um backup datado.
11. Não migrar o schema de `REAL` para centavos inteiros nesta entrega. Não reescrever módulo inteiro: patch cirúrgico.
12. Fora de escopo: outros projetos em `C:\GIS\`, serviços do Hermes, SIMCAR, Trello, e-mail, APK (não existe app Android). Vault só na Fase 7.
13. `PROMPT_CLAUDE_CODE_PRODUCAO.md` na raiz é rascunho antigo: não seguir, não commitar.
14. "Pronto" só com a saída do comando registrada. Relato sem saída não fecha item.
15. Na dúvida entre corrigir e perguntar: **corrija** bug, perda de dado, dinheiro errado e nota rejeitada; **siga o padrão** de `05_DECISOES_ALVARO.md` no que é decisão de produto, e registre.

## 3. Subagentes — quantos quiser, quantas vezes precisar

| Item | Valor |
|---|---|
| Ferramenta | `delegate_task` |
| Modelo | `ag/gemini-3.8-flash-high` (provider `ninerouter`) |
| Raciocínio | `reasoning_effort: high` |
| Limite | nenhum |

Antes do primeiro disparo: confira a seção de delegação do seu `config.yaml` e faça um `delegate_task` de 1 linha para provar que o modelo responde. Se não responder, **pare e avise**; não troque de modelo por conta própria.

- **Você orquestra e é o único que commita e que edita esta pasta.** Subagente devolve: arquivos tocados, diff, comando rodado e saída.
- **Leitura e auditoria:** em paralelo, um subagente por módulo ou por pergunta.
- **Escrita:** um subagente por conjunto de arquivos; dois nunca escrevem no mesmo arquivo. `backend/database.py` é **serial**.
- **Relato de subagente é pista, não prova.** Rode o teste você mesmo antes de commitar.
- **Revisor adversário:** depois de cada correção de dinheiro, estoque ou fiscal, um subagente só para tentar quebrá-la (concorrência, valor limite, reinício no meio, fuso).
- Cada tarefa delegada leva: objetivo em 1 frase, arquivos, o que **não** tocar, critério de pronto e formato de retorno.

## 4. Autonomia primeiro (ordem do Álvaro, 10/11/2026)

**Faça sozinho tudo o que for possível, sem parar para perguntar. Só no fim, com todo o resto validado, peça o que precisar — numa lista única.**

| Situação | O que fazer |
|---|---|
| Erro de build, teste falhando, dependência faltando, arquivo travado, porta ocupada | **Não pare.** Diagnostique e siga |
| Item depende de terceiro e está em `04_BLOQUEIOS.md` | Marque `[!]`, registre a prova e **siga para o próximo item** |
| Item parece depender de terceiro e **não** está na lista | Não é bloqueio: resolva por outro caminho |
| Decisão de produto | Aplique o padrão de `05_DECISOES_ALVARO.md`, registre e siga |
| Dúvida que não é decisão de produto | Escolha a opção mais conservadora (a que não muda o comportamento atual), registre no diário e siga |
| Modelo dos subagentes não responde | Registre no diário, faça o trabalho você mesmo e tente de novo na fase seguinte. Não troque de modelo |
| Um teste só passaria mudando regra fiscal ou inventando dado | **Não faça.** Deixe o item aberto com o motivo, siga com os outros e leve a dúvida para a lista final |
| Tudo `[x]`/`[-]`/`[!]` e relatório entregue | Fim (ver "Quando o trabalho acaba" no `README.md`) |

Pedidos ao Álvaro vão **todos juntos** para a seção "O que preciso de você" do `RELATORIO_FINAL.md`: o que fazer, onde, quanto tempo leva e o que destrava. Nada de pergunta no meio do caminho.

O que a autonomia **não** cobre, nem com pressa: sair de `homologacao`, usar certificado que não seja o da loja, inventar dado fiscal, commitar binário ou segredo, mexer fora deste repositório.
