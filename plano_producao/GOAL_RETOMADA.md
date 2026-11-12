# GOAL — retomada em 12/11/2026

> Copie o bloco abaixo e envie no próximo chat. Ele é autossuficiente: aponta os arquivos que mandam e o ponto exato de retomada.

---

**Objetivo:** continuar o VendaFácil PDV (`C:\GIS\VendaFacil_PDV`, branch `master`, HEAD `a6a90d5`) do ponto em que parou e executar até o fim o plano de `C:\GIS\VendaFacil_PDV\plano_producao\`.

**Antes de escrever qualquer linha**

1. Leia, nesta ordem: `plano_producao/RETOMADA.md`, `00_PAINEL.md`, `01_REGRAS.md`, `README.md`.
2. Confira o estado real: `git log --oneline -5`, `git status --porcelain`, suítes backend/painel.
3. Não refaça o que já está fechado. Fases 0, 1 e 2 estão concluídas e publicadas; a Fase 3 está em **21/24**.

**Onde retomar (Fase 3, nesta ordem)**

| Item | Pista/Teste | O que fazer |
|---|---|---|
| F3.22 | P42 / S14 | Validar o dono da nota antes de ler, consultar ou cancelar (`fiscal_router.py`). Teste que falha primeiro, com dois usuários. |
| F3.21 | P41 / S13 | Bootstrap de admin atômico, senha mínima no painel e troca de senha que revoga tokens. |
| F3.19 | P34 / U07 | Total diário pelo backend, sem truncar nas 100 vendas, respeitando o fuso de MT. |

Feche cada item no ciclo do README: `[~]` → teste RED → correção → suíte → revisão independente → commit com caminho explícito → `[x]` com commit/teste → atualizar `03_TESTES.md`, `02_PISTAS.md`, `06_DIARIO.md` e `00_PAINEL.md`.

Depois dos três: portão da Fase 3 (suítes verdes, plano commitado, `git push origin master`) e siga para as fases 4 → 7, em ordem.

**Regras que não se negociam**

- Um bug = um commit, mensagem em português, `git add` sempre por caminho explícito. Nunca `git add -A`; nunca commitar `dist_exe/VendaFacilPDV.exe`.
- Segredo não entra em commit, log, diário nem vault. Evidência de falha é revisada e mascarada antes do stage.
- Fiscal: blocos A e B (offline, XSD/assinatura/QR e simulador local) são obrigatórios; o bloco C (SEFAZ-MT real) depende de B1–B5 e fica `[!]` se faltar. Nunca inventar dado fiscal, nunca usar certificado que não seja o da mercearia, nunca sair de `homologacao`.
- Autonomia primeiro: resolva sozinho build, teste, dependência, porta ocupada. Só marque `[!]` para os itens da lista fechada `04_BLOQUEIOS.md`. Decisão de produto: aplique o padrão de `05_DECISOES_ALVARO.md` e registre. Perguntas ao Álvaro só no fim, numa lista única.
- Subagentes: `delegate_task` em `ag/gemini-3.8-flash-high`, raciocínio `high`, quantos precisar. Você orquestra, confere a saída e é o único que commita. Relato de subagente é pista, não prova.

**Armadilhas medidas nesta máquina**

- A suíte E2E tem 81 testes com `workers: 1` e não cabe no limite de 350–600 s de uma ferramenta. Rode em 4 lotes e guarde a saída:
  1. `e2e/carrinho.spec.ts e2e/decimais.spec.ts` (28)
  2. `e2e/erros.spec.ts e2e/foco.spec.ts e2e/teclado.spec.ts` (20)
  3. `e2e/locale.spec.ts e2e/produtos-locale.spec.ts e2e/xml-idempotencia.spec.ts` (19)
  4. `e2e/xml-locale.spec.ts` (14)
- Antes de rodar, exporte `TEMP`/`TMP`/`TMPDIR` para uma pasta scratch. Memória de 16 GB: Browser/Chromium crashando com "Target crashed" é falta de RAM, não falha de teste — feche apps pesados e repita o lote.
- Python sempre com `-X utf8 -I` e sem `PYTHONPATH` herdado.
- Push: use o helper efêmero documentado em `RETOMADA.md` (`git -c credential.helper='!sh .../git-cred-sd.sh' push origin master`). Não grave, não imprima e não copie credencial.

**Só pare quando**

- não houver nenhum `[ ]` nem `[~]` em nenhuma fase, nenhum teste ⬜/🟥 em `03_TESTES.md`, as duas suítes verdes, o instalador 1.0.13 gerado e `RELATORIO_FINAL.md` preenchido com a saída real dos comandos; e
- o painel estiver em **✅ CONCLUÍDO** ou **⏸ AGUARDANDO TERCEIRO** (só itens `[!]` da lista fechada).

**Entrega final:** veredito em 1 linha, números de teste antes/depois, caminho e sha256 do instalador, e a lista "O que preciso de você". Responda em português, curto, com tabelas.
