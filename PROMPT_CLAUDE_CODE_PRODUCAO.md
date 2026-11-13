# BRIEFING — VendaFácil PDV: auditar, corrigir, deixar pronto para produção e implantar numa mercearia (Querência-MT)

> **Você é o Claude Code operando neste PC Windows (`pcque001imap`).**
> Este documento é a sua única fonte de contexto: ele foi escrito por quem já mediu o ambiente,
> buildou o instalador e conhece as regras da casa. Não improvise por cima dele — se algo aqui
> estiver errado, **corrija o documento no fim do trabalho** e relate.
>
> **Missão:** pegar o PDV no estado em que está hoje, **encontrar e corrigir todo bug real**,
> **validar fiscalmente o que é validável sem certificado da loja**, empacotar, testar o instalador
> de ponta a ponta e **deixar o sistema implantado e operante numa mercearia em Querência-MT** —
> com o que depende de terceiro (certificado A1, CSC, credenciamento SEFAZ) explicitamente
> bloqueado e documentado, nunca inventado.

---

## 1. Onde você trabalha

| Item | Valor |
|---|---|
| Repositório | `C:\GIS\VendaFacil_PDV` — clone de `https://github.com/alvaro209890/VendaFacil_PDV` (público) |
| Branch | `master`, HEAD `6da6899` ("fix: corrige regras do eslint na api…") |
| Outras cópias | `server:/home/server/VendaFacil_PDV` e `acer:~/Documentos/VendaFacil_PDV` — **mesmo commit, git limpo**. GitHub `master` também em `6da6899`: ninguém está à frente de ninguém |
| Dono | Álvaro (IMAP Engenharia, Querência-MT). Fala português; quer resposta curta, tabela, sem enrolação |
| Toolchain medida (10/11/2026) | Node **v22.22.0** · npm 10.9.4 · Python **3.11.15** (`py -3.11`) · Inno Setup 6 (`C:\Program Files (x86)\Inno Setup 6\ISCC.exe`) · git 2.x (MSYS) |
| Shell | O agente do Hermes aqui roda em **bash (git-bash/MSYS)**. Você, Claude Code, tem shell nativo — mas se rodar `.bat`, use `cmd.exe /c "build_exe.bat"` (com **aspas duplas** em caminho com barra) |

## 2. O produto, em uma tela

**VendaFácil PDV** — PDV desktop **offline-first** para pequeno comércio, com **NFC-e (modelo 65) e
NF-e (55)** para **Mato Grosso**, mais um painel SaaS de licenciamento (Render + Supabase) que **não
faz parte do `.exe`**.

| Peça | Onde | Roda em |
|---|---|---|
| PDV (backend FastAPI + front React embutido) | `backend/`, `src/` | `.exe` único na máquina da loja |
| Instalador | `installer/vendafacil.iss` (Inno Setup) | Windows da loja |
| Painel admin | `painel/` | Render (API) + Vercel (front) |
| Banco local | SQLite em `%LOCALAPPDATA%\VendaFacilPDV\dados\vendafacil.db` | máquina da loja — **sobrevive a reinstalação e a desinstalação** |

- O `.exe` sobe o FastAPI em `127.0.0.1:3020` e abre o navegador. `VENDAFACIL_NO_BROWSER=1` e
  `VENDAFACIL_PORT` são respeitados por `backend/run.py`.
- **Offline-first é requisito fiscal, não conveniência:** a loja precisa vender com a internet
  caída e transmitir depois (contingência). Qualquer mudança que crie dependência de rede no fluxo
  de venda é **bug de projeto**, não melhoria.

### Módulos reais do backend (âncoras para você)

`main.py` (rotas) · `vendas.py` · `produtos.py` · `clientes.py` · `caixa.py` · `conta.py` ·
`contas_receber.py` (fiado) · `categorias.py` · `auth.py` · `backup.py` · `importacao_xml.py` ·
`mercadopago.py` (maquininha Point) · `pix.py` · `fiscal.py` · `fiscal_direto.py` (SOAP/assinatura/QR
SFaz-MT) · `fiscal_config.py` (cofre de configuração fiscal) · `fiscal_router.py` · `sync_client.py`
(sincroniza com o painel) · `painel_config.py` · `paths.py` · `normalizers.py` · `errors.py`.

## 3. Linha de base já medida hoje (não é chute — foi executado)

| Verificação | Resultado real |
|---|---|
| `backend` testes | **76 passed** (`backend/.venv` + `pip install -r requirements-dev.txt` da **raiz**) |
| Painel | 7 testes existem (`painel/tests/test_painel.py`) — **não medidos hoje**: `painel/` **não tem venv**; criar um e medir |
| Build do `.exe` | ✅ `cmd.exe /c build_exe.bat` → `dist_exe\VendaFacilPDV.exe` (39,6 MB) |
| Build do instalador | ✅ `cmd.exe /c "installer\build_installer.bat"` → `dist_installer\VendaFacilPDV-Setup-1.0.12.exe` (39,9 MB) |
| Smoke test | ✅ `GET /` 200 · `/docs` 200 · `/api/produtos` 401 (auth funcionando) |
| Binário do repo | 🔴 o commitado é o **`Setup-1.0.11` de 01/06/2026** — anterior às correções fiscais de 13/07 e ao ESLint de 03/11 |

`requirements-dev.txt` está na **raiz** e serve aos dois venvs (`backend/` e `painel/`); dentro de
`backend/` o caminho é `../requirements-dev.txt`.

## 4. O que conta como "pronto para produção" — gates com prova

Nenhum item abaixo vale por "eu revisei". Vale por **saída de comando colada no relatório**.

| # | Gate | Prova exigida |
|---|---|---|
| G1 | Zero bug conhecido nos fluxos de venda | Suíte pytest **verde** (backend + painel), com o número antes/depois; cada bug corrigido tem **teste de regressão** que falha no commit anterior |
| G2 | Nenhuma exceção 500 nos caminhos do dia a dia | Roteiro manual de `docs/TESTE_WINDOWS.md` executado no `.exe` real, com o log colado (venda, sangria, fechamento de caixa, fiado, cancelamento, importação XML, backup, restauração) |
| G3 | Fiscal MT consistente | XML gerado **validado contra o XSD oficial** (NFC-e 4.00), assinatura XMLDSig verificada, QR Code 2.00 conferido campo a campo, `tPag`/`<card>`/CEST-ST/Lei 12.741 presentes. Tudo isso é offline e **você consegue provar sem certificado da loja** |
| G4 | Transmissão real em homologação SEFAZ-MT | 🔴 **Só com certificado A1 da mercearia + CSC + credenciamento.** Se não houver, **NÃO simule sucesso**: entregue o harness pronto (`pytest -m homologacao`, script de ping no webservice com `statusServico`) e marque como **BLOQUEADO POR TERCEIRO** |
| G5 | Instalador aprovado | Instalar via `Setup-1.0.12.exe` **neste PC** numa conta limpa: Programa Files criado, atalhos, primeira execução, banco em `%LOCALAPPDATA%`, upgrade por cima preservando dados, desinstalação preservando dados. Evidência: caminhos + `sqlite3` mostrando o banco antes/depois |
| G6 | Offline real | Desligar a rede (ou apontar DNS inválido) e vender, cancelar, fechar caixa e reimprimir. Reconectar e transmitir/conciliar. Log das duas fases |
| G7 | Backup que restaura | Backup automático + manual, e **restauração testada** num banco novo — backup que nunca foi restaurado não é backup |
| G8 | Licença não quebra a loja | Modo local (`PAINEL_URL=""`) e modo painel; carência offline; bloqueio por validade **não** pode impedir fechamento de caixa nem leitura dos dados |
| G9 | Documentação | `docs/` atualizado (o que mudou, como operar, o que ficou bloqueado), `06-changelog`/ficha no vault (ver §8) |
| G10 | Instalado na mercearia | Ver §7 — roteiro de implantação cumprido com evidência de cada item |

## 5. Fila de trabalho (nesta ordem; não pule para o fim)

### P0 — Auditoria e correção (fazer primeiro, com ou sem hardware)
1. **Ler antes de mexer:** `CLAUDE.md`, `docs/CHECKLIST_COMERCIALIZACAO.md`, `docs/TESTES.md`,
   `docs/LEGISLACAO_FISCAL_MT.md`, `docs/VINCULO_PAGAMENTO_MT.md`, `docs/CONTINGENCIA_OFFLINE.md`.
2. **Auditar de verdade** (não é leitura passiva): concorrência em SQLite (duas abas do PDV, dois
   caixas), arredondamento de dinheiro (**centavos em float é bug**), transações não atômicas em
   venda+estoque+caixa, cancelamento de venda que deixa estoque errado, fiado/contas a receber
   (juros, vencimento, baixa parcial), estoque negativo, importação de XML (duplicidade de chave,
   unidade de medida, CST/CSOSN), backups concorrentes, caminho de erro do fiscal que **perde a
   venda** por causa da SEFAZ, reinício do `.exe` no meio de uma venda.
3. **Segurança mínima de produto:** `auth.py` (hash, sessão, rate limit), o que acontece no primeiro
   acesso (senha padrão!), `/docs` exposto em produção (decidir e justificar), CORS, o cofre
   `fiscal_config.py` (os campos `csc`, `certificado_senha`, `certificado_a1_b64`, `gateway_token`
   estão mascarados em leitura? estão em claro no SQLite local? **isso é aceitável num PDV offline,
   mas tem de estar decidido e escrito**), e nenhum segredo em log.
4. **Front (`src/`):** teclado-first (o caixa usa teclado e leitor de código de barras, **não
   mouse**), foco automático no campo de código, Enter como "adicionar/confirmar", nenhuma tela que
   perca o carrinho ao atualizar, `desconto` e `quantidade` sem "travar" em vírgula/ponto.
5. **Cada correção = 1 commit** em português, direto no `master`, com o teste de regressão junto.
   Nunca um commit gigante "corrige vários bugs".

### P1 — Fiscal MT até onde é provável
6. Validar o XML contra o XSD oficial (NFC-e 4.00) em teste automatizado.
7. Verificar assinatura (XMLDSig, SHA-1/RSA conforme MOC), QR 2.00 (hash CSC + parâmetros),
   `tpAmb` homologação/produção sem risco de trocar sozinho, prazos de cancelamento (30 min / 2 h),
   `tPag` (20/17/99), `CRT` (1/4), CEST-ST, Lei 12.741.
8. `statusServico` do webservice de MT em homologação — **só** se houver certificado válido
   disponível; senão deixar script pronto e documentar como bloqueado.
9. Conferir que **falha da SEFAZ não perde venda**: contingência grava, marca para transmitir,
   retenta, e o cupom sai com a marcação correta.

### P2 — Robustez de produção (o que faz a loja não te ligar às 18h de sábado)
10. **Auto-backup** com retenção e verificação de integridade (`PRAGMA integrity_check`).
11. **Log rotativo** em `%LOCALAPPDATA%\VendaFacilPDV\logs`, sem dado sensível.
12. **Recuperação**: banco corrompido → o sistema precisa abrir em modo consulta e avisar, não morrer.
13. **Atualização por cima** (reinstalar Setup) preservando dados — já previsto no `.iss`, **provar**.
14. **Impressão térmica 58/80mm** com o hardware real (ou emulador RAW): corte, acentuação,
    QR no cupom, segunda via.
15. Versão: subir `AppVersion` no `installer/vendafacil.iss` a cada entrega (hoje `1.0.12`).

### P3 — Sinais de vida e operação
16. Tela/arquivo de diagnóstico acessível ao suporte: versão, caminho do banco, espaço livre,
    status fiscal (certificado válido até, ambiente, pendências de transmissão), último backup.

## 6. 🔴 Dependências do mundo real — você NÃO pode resolver sozinho

Isto **não é código**, é do lojista/contador/Álvaro. Sua função é **verificar, listar e cobrar** —
e **parar** em vez de inventar dado fiscal. Dado fiscal inventado = nota rejeitada ou, pior,
irregularidade na loja.

| Dependência | De quem | Onde entra no sistema | Se faltar |
|---|---|---|---|
| **Certificado digital A1 (`.pfx`) da mercearia** + senha | Lojista (e-CNPJ) | Fiscal → Certificado | Não transmite. **Nunca** usar certificado de terceiro, de teste ou autoassinado como se fosse da loja |
| **CSC + ID do CSC** (token NFC-e) | Portal SEFAZ-MT da loja | Fiscal → CSC | QR Code não vale |
| **Credenciamento NFC-e da loja na SEFAZ-MT** | Lojista/contador | fora do sistema | Rejeição 778 etc. |
| **CNPJ da credenciadora** (Mercado Pago) no vínculo de pagamento | Conta Mercado Pago da loja | Maquininha → Vínculo fiscal | `<card>` incompleto → rejeição (obrigatório p/ CNAE 4712-1 desde 01/07/2024) |
| **Maquininha Point física + conta de produção** | Lojista | Maquininha | Fluxo PIX/cartão não se prova sem aparelho |
| **Dados da empresa** (CNPJ, IE, CNAE, endereço, regime/CRT, CSC, certificado) | Lojista | Fiscal → Empresa | Cupom sai sem validade fiscal |
| **Decisão sobre ambiente** | Álvaro | `ambiente`: `homologacao` \| `producao` | **Começar SEMPRE em homologação.** Ir a produção é decisão explícita dele, nunca sua |

Regra dura: **nunca** preencher CNPJ/IE/CSC/certificado com valor fictício para "ver funcionar",
nem desativar validação fiscal para o teste passar. Se faltar dado, o caminho é:
`BLOQUEADO: falta <item> (dono: <quem>). Impacto: <o que a loja não consegue fazer>`.

## 7. Implantação na mercearia (Querência-MT)

O que "implantar" significa concretamente. Faça o que é possível neste PC e entregue o resto como
roteiro executável **com evidência por item**:

| # | Item | Evidência |
|---|---|---|
| 1 | Instalador 1.0.x instalado na máquina da loja | print/console do Setup + atalho + versão mostrada no app |
| 2 | PDV abre e vende com a internet **desligada** | log da venda offline + cupom |
| 3 | Cadastro mínimo carregado: produtos com código de barras, preço, estoque, unidade | contagem real de linhas no SQLite |
| 4 | Formas de pagamento e maquininha configuradas | tela + venda teste em cada forma |
| 5 | Fiscal configurado (cert A1, CSC, empresa, ambiente=**homologacao**) | `statusServico` OK e 1 NFC-e autorizada em homologação, ou BLOQUEADO com dono |
| 6 | Impressora térmica + gaveta + leitor testados | cupom físico/RAW gerado |
| 7 | Backup automático ligado + **restauração testada** | arquivo de backup + banco restaurado consultado |
| 8 | Senhas trocadas (admin do PDV, painel), licença com validade | captura do login novo |
| 9 | Treinamento de 20 min com quem vai operar (abrir caixa, vender, sangria, fechar caixa, fiado, cancelar) | roteiro em `docs/` + quem foi treinado |
| 10 | Contato de suporte e o que fazer se cair a luz/a internet | 1 página impressa deixada na loja |

**Não** instale em `producao` sem ordem explícita do Álvaro. A primeira NFC-e real da loja é um
evento fiscal: precisa dele e do contador presentes.

## 8. Rito da casa (regras do Álvaro — desrespeitar é retrabalho)

1. **Português**, direto, tabela em vez de textão. Sem floreio.
2. **Commit direto no `master`, sem PR**, mensagem em português. Um assunto por commit.
3. **Testado antes de dizer pronto.** "Está pronto" só com a saída do comando no relatório.
4. **Doc antes do commit**: o que mudou em `docs/` quando muda comportamento de operação.
5. **Não commitar**: `dados/`, `.db`, `build/`, `.venv/`, `node_modules/`, segredo, certificado,
   senha, token. ⚠️ Exceção herdada: `dist_exe/VendaFacilPDV.exe` e `dist_installer/*.exe` **estão
   trackeados** no git (contradiz o `CLAUDE.md`, que manda não commitar). **Decisão pendente do
   Álvaro** — até ele decidir, **não commite binário novo**; deixe os artefatos no disco e relate.
6. **Não** gerar APK (não existe app Android neste projeto), **não** mexer em outros projetos em
   `C:\GIS\`, **não** parar/reiniciar serviço do Hermes, **não** tocar em SIMCAR/Trello/vault sem
   pedido, **não** abrir e-mail.
7. **Nunca** segredo em texto: nem em commit, nem em log, nem no vault (o Segundo Cérebro é git **e
   site público**). Onde fica o valor: cofre local, fora do repo.
8. Ao terminar, atualizar a ficha do projeto no Segundo Cérebro (`02-projetos/vendafacil.md`) e o
   `.md` correspondente em `docs/` do repo. Se não tiver acesso ao vault por SSH, entregue o texto
   pronto para colar e avise.

## 9. Formato do relatório final (é o que ele vai ler)

```
## VendaFácil PDV — <data>

### Veredito
<pronto para homologação | pronto para produção | bloqueado: X>

### Bugs encontrados e corrigidos
| # | Gravidade | Onde | Sintoma | Correção | Teste que prova | Commit |
|---|---|---|---|---|---|---|

### Bugs encontrados NÃO corrigidos (com motivo)
| # | Gravidade | Por que não corrigi | Impacto na loja |

### Provas
| Gate | Resultado | Comando/saída |
|---|---|---|

### Bloqueado por terceiro
| Item | Dono | Impacto | O que preciso dele |

### Artefatos
- installer: `dist_installer\VendaFacilPDV-Setup-X.Y.Z.exe` — sha256, tamanho
- exe: `dist_exe\VendaFacilPDV.exe` — sha256, tamanho
- testes: <N> passed

### Riscos que ficam
<lista curta: o que pode dar errado na loja e o que fazer>
```

## 10. Primeiros 15 minutos (faça exatamente isto, nesta ordem)

```bash
cd C:/GIS/VendaFacil_PDV
git log --oneline -1                      # tem de ser 6da6899
git status --porcelain                    # esperado: só "M dist_exe/VendaFacilPDV.exe" (build de hoje)
cd backend && .venv/Scripts/pip install -q -r ../requirements-dev.txt
.venv/Scripts/python -m pytest -q         # esperado: 76 passed
```

Depois, antes de tocar em código:
1. `painel/` → criar venv, instalar `../requirements-dev.txt`, rodar os 7 testes.
2. Ler os 5 docs listados no P0 §1.
3. Escrever **seu próprio** plano de auditoria (módulo por módulo, com o que vai testar) e só então
   começar a corrigir. Plano curto e verificável — não um romance.

Se em qualquer ponto você ficar entre **corrigir** e **pedir decisão**: corrija o que é
inequívoco (bug, perda de dado, dinheiro errado, nota rejeitada) e **peça decisão** no que é
produto/negócio (assinatura de código, preço, ir a produção, mudar fluxo que o lojista já usa).
