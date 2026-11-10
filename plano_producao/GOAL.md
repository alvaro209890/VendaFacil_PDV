# GOAL

Texto enviado ao Hermes-windows. A pasta `plano_producao/` é o plano; este arquivo é só o disparo.

---

**Objetivo:** deixar o VendaFácil PDV (`C:\GIS\VendaFacil_PDV`, branch `master`) pronto, testado, validado e documentado para ir a uma mercearia em Querência-MT, executando até o fim o plano em `C:\GIS\VendaFacil_PDV\plano_producao\`.

**Como trabalhar**

1. Leia `plano_producao/README.md`, `00_PAINEL.md` e `01_REGRAS.md`. Eles mandam; siga o ciclo de trabalho do README.
2. Execute as fases 0 a 7 em ordem. Em cada item: marque `[~]`, escreva o teste que falha, corrija, rode a suíte, commite, marque `[x]` com commit e teste, atualize `03_TESTES.md`, `02_PISTAS.md`, `06_DIARIO.md` e o painel.
3. Use subagentes à vontade, quantos e quantas vezes precisar: `delegate_task` em `ag/gemini-3.8-flash-high` com raciocínio `high`. Você orquestra, confere e commita.
4. **Autonomia primeiro:** faça sozinho tudo o que for possível, sem parar para perguntar. O que depender de terceiro (lista fechada em `04_BLOQUEIOS.md`) você marca `[!]` e segue adiante. Decisão de produto: aplique o padrão de `05_DECISOES_ALVARO.md` e siga. Só no fim, com todo o resto validado, entregue uma lista única do que precisa de mim.
5. Fiscal: os blocos A (offline, XSD/assinatura/QR) e B (simulador local da SEFAZ) são obrigatórios e não aceitam bloqueio. O bloco C (SEFAZ-MT real em homologação) roda se o precheck achar certificado A1, CSC e dados da loja no cofre local; senão fica `[!]`. Nunca invente dado fiscal, nunca use certificado que não seja o da mercearia, nunca saia de `homologacao`.

**Só pare quando**

- não houver nenhum `[ ]` nem `[~]` em nenhuma fase, nenhum teste ⬜ ou 🟥 em `03_TESTES.md`, as duas suítes estiverem verdes, o instalador 1.0.13 estiver gerado e `RELATORIO_FINAL.md` estiver preenchido com a saída dos comandos; e
- o painel estiver em **✅ CONCLUÍDO** (tudo validado, inclusive a SEFAZ-MT real) ou **⏸ AGUARDANDO TERCEIRO** (só restam itens `[!]` da lista fechada).

Erro de build, teste falhando, dependência faltando ou arquivo travado **não** são motivo para parar: diagnostique e continue. Se perder o contexto, siga a seção "Retomada" do README.

**Entrega final:** veredito em 1 linha, números de teste antes/depois, caminho e sha256 do instalador, e a lista "O que preciso de você" do relatório.
