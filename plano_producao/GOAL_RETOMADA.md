# GOAL — retomada em 12/11/2026 (Fase 4)

> Copie o bloco abaixo e envie no próximo chat.

---

**Objetivo:** continuar o VendaFácil PDV (`C:\GIS\VendaFacil_PDV`, branch `master`, HEAD `c9f6d1d` ou posterior) do ponto em que parou e executar até o fim o plano de `C:\GIS\VendaFacil_PDV\plano_producao\`.

**Antes de escrever qualquer linha**

1. Leia, nesta ordem: `plano_producao/RETOMADA.md`, `00_PAINEL.md`, `01_REGRAS.md`, `README.md`.
2. Confira o estado real: `git log --oneline -8`, `git status --porcelain`, e a suíte backend.
3. Não refaça o que está fechado. Fases 0, 1, 2 e 3 estão concluídas e publicadas. A Fase 4 está em **7/27**.

**Onde retomar (nesta ordem)**

| Item | O que falta | Onde |
|---|---|---|
| F4.27 (P35/P36) | 4 RED já escritos: config vazia não levanta, preflight certificado/itens grava nota, assinatura queima número | `backend/tests/test_fiscal_reserva_regras.py` + `fiscal_direto.py` |
| F4.11 | 5 RED no simulador: M05 (503 devolve rejeitada), M08 (evento 135 preso em processando), M09 (falta `inutilizar_numeracao`), M10×2 (fixture sem certificado) | `backend/tests/sefaz_fake.py`, `test_sefaz_simulador.py` |
| F4.6 | X11: prazo de cancelamento 30 min NFC-e / 2 h NF-e no fuso de MT (X09 já está verde) | `fiscal.py` / testes fiscais |
| F4.8 / F4.9 | X13 (nenhum caminho cai em FocusNFe/PlugNotas) e X12 (numeração sem buraco sob concorrência) | `fiscal.py`, `fiscal_direto.py` |
| F4.10 | Reconferir `docs/LEGISLACAO_FISCAL_MT.md` e `docs/VINCULO_PAGAMENTO_MT.md` contra o código; o que divergir vira pista | docs + código |
| F4.18 / F4.19 | Inutilização (X05/M09) e campos obrigatórios do cupom DANFE NFC-e | `fiscal_direto.py`, `recibo.ts` |
| Bloco B | M01–M04, M06, M07, M11, M12 ponta a ponta com o simulador | `test_sefaz_simulador.py` |
| F4.20–F4.26 | Precheck, `pytest.ini` com marker `homologacao`, H01–H09 (ou `[!]` B1–B5), revisor fiscal, docs | `scripts/`, `pytest.ini`, `backend/tests/` |

**Atenção:** `backend/tests/test_sefaz_simulador.py` e `test_fiscal_reserva_regras.py` estão no working tree **sem commit** e ainda falham. Não commitar antes do GREEN. Enquanto existirem, rode a suíte com `--ignore` nesses dois arquivos; o resto está em 347 verdes.

**Regras que não se negociam**

- Um bug = um commit, mensagem em português, `git add` sempre por caminho explícito. Nunca `git add -A`; nunca commitar `dist_exe/VendaFacilPDV.exe`.
- Item só fecha com a saída real do comando e a linha `— <commit> · <teste>`.
- Segredo não entra em commit, log, diário nem vault. Evidência de falha é revisada e mascarada antes do stage.
- Fiscal: blocos A e B (offline e simulador) são obrigatórios; o bloco C (SEFAZ-MT real) depende de B1–B5 e fica `[!]` com a prova do precheck. Nunca inventar dado fiscal, nunca usar certificado que não seja o da mercearia, nunca sair de `homologacao`.
- Autonomia primeiro: resolva sozinho build, teste, dependência, porta ocupada. Só marque `[!]` para itens de `04_BLOQUEIOS.md`. Decisão de produto: padrão de `05_DECISOES_ALVARO.md`, registrado. Perguntas ao Álvaro só no fim, numa lista única.
- Subagentes: `delegate_task` em `ag/gemini-3.8-flash-high`, raciocínio `high`. Você orquestra, confere e é o único que commita. Relato de subagente é pista, não prova.

**Armadilhas medidas nesta máquina**

- Suíte E2E: 81 testes com `workers: 1` não cabem em uma ferramenta. Rode em 4 lotes (A 28, B 20, C 19, XML 14) e guarde a saída.
- Antes de Playwright, exporte `TEMP`/`TMP`/`TMPDIR` para uma pasta scratch. Chromium com "Target crashed" é falta de RAM, não falha.
- Python sempre com `-X utf8 -I` e sem `PYTHONPATH` herdado.
- Push com o helper efêmero de `RETOMADA.md`; não grave nem imprima credencial.

**Só pare quando**

- não houver nenhum `[ ]` nem `[~]` em nenhuma fase, nenhum teste ⬜/🟥 em `03_TESTES.md`, as duas suítes verdes, o instalador 1.0.13 gerado e `RELATORIO_FINAL.md` preenchido com a saída real dos comandos; e
- o painel estiver em **✅ CONCLUÍDO** ou **⏸ AGUARDANDO TERCEIRO** (só itens `[!]` da lista fechada).

**Entrega final:** veredito em 1 linha, números de teste antes/depois, caminho e sha256 do instalador, e a lista "O que preciso de você". Responda em português, curto, com tabelas.
