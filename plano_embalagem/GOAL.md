# GOAL — embalagem e unidade

Cole o bloco abaixo no privado do Hermes no WhatsApp.

---

**Objetivo:** no VendaFácil PDV, vender a embalagem fechada e a unidade avulsa com preços independentes, testar até ficar verde e deixar o instalador 1.0.15 no `master` para a mercearia amanhã.

**Onde:** você é o Hermes da AWS. Este trabalho é do PC Windows `pcque001imap`, pasta `C:\GIS\VendaFacil_PDV`, branch `master`. Entre por SSH nesse PC e execute lá. Não compile o `.exe` na Lightsail. O plano já está no working tree, em `C:\GIS\VendaFacil_PDV\plano_embalagem\`. Ignore `plano_producao/`: é histórico e não faz parte deste goal.

**Como trabalhar**

1. Leia `plano_embalagem/README.md`, `00_PAINEL.md`, `01_REGRAS.md` e `02_ESPECIFICACAO.md`. A especificação está fechada. Não pergunte no meio.
2. Execute E1 a E8 de `04_TAREFAS.md` em ordem. Em cada item: marque `[~]`, escreva o teste que falha, corrija, rode a suíte, commite, marque `[x]` com commit e comando, atualize `03_TESTES.md`, `06_DIARIO.md` e o painel.
3. Critério que não se negocia: carteira de palheiro a R$ 20 com 20 unidades, palheiro a R$ 2. Uma carteira cobra R$ 20 e baixa 20. Um palheiro cobra R$ 2 e baixa 1. Uma carteira mais 3 palheiros cobra R$ 26 e baixa 23. Vinte avulsos cobram R$ 40. Com 15 no estoque a carteira é recusada. Nota em UN não multiplica pelo número escrito no nome (`CX 00050` com `qCom=600` continua 600).
4. Fiscal em homologação. Não chame a SEFAZ, não use certificado, não aponte o PDV para a VPS, não toque o banco em `%LOCALAPPDATA%\VendaFacilPDV\dados`.
5. `git add` por caminho. Nunca `git add -A`. Não commite `dados/`, binário, segredo nem `*.pfx`. Push de `origin/master` uma vez, no portão, sem pull request.

**Só pare quando**

- não houver `[ ]` nem `[~]`, T1–T14 estiverem ✅, o `master` estiver no GitHub e o workflow Build Windows EXE estiver verde; ou
- o SSH neste PC falhar, ou o Actions não puder ser consultado. Aí uma mensagem com a prova e pare.

Erro de teste, porta ocupada ou build quebrado não é parada: corrija e siga. Se perder o contexto, a seção Retomada do README.

**No WhatsApp, em português e curto:** uma linha ao começar; a entrega final com versão, commit, testes antes/depois e o link do Setup 1.0.15. Sem texto longo no meio.
