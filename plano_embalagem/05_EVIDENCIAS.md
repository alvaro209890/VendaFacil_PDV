# Evidências de implementação — 1.0.15

Autor: Codex, 13/11/2026. Execução local no Windows PCQUE001IMAP autorizada
pelo Álvaro. Todos os bancos usados são descartáveis; fonte fiscal real não
foi copiada para o repositório. Não houve uso de certificado nem SEFAZ.

| Etapa | Saída antes da correção | Saída depois |
|---|---|---|
| E1 | `.venv/Scripts/python -X utf8 -I -m pytest -q --tb=short` | `466 passed, 9 deselected` |
| E2, `tests/test_embalagem.py` | `9 failed`: `KeyError: vende_por_unidade`, preços ausentes, configuração inválida aceita com 201 | Backend completo `475 passed, 9 deselected`; depois da proteção do fator, 476 |
| E3, `tests/test_embalagem_vendas.py` | `10 failed, 1 passed`: carteira cobrou 9 em vez de 20; 20 avulsos cobraram 180 em vez de 40; faltavam snapshots | Backend completo 487, depois 488; lucro 26 − 23 × 0,50 = 14,50; estorno preserva fator original |
| E4, `tests/test_embalagem_xml.py` | `4 failed`: faltavam fator/mensagem/pergunta e conversão confirmada | Backend completo `492 passed, 9 deselected`; navegador XML/embalagem `18 passed` |
| E5, `tests/test_embalagem_fiscal.py` | `uCom=UN`, esperado CART; o mesmo erro foi reproduzido no payload | Teste XML direto + payload passou; backend 493 |
| E6, revisão | Entrada manual de duas carteiras somava 2 em vez de 40; código avulso duplicado aceito com 201 | Entrada 40 a custo 0,50; duplicação recusa com 409; backend 495 e migração idempotente 496 |
| E6, navegador | Correção visual de cards, mensagem de sucesso invisível e separação de modos; falhas de teclado/XML foram repetidas | Suíte integral estável: `95 passed (2.3m)`; aceite isolado 3021 `4 passed`; Node 38 |
| E8, `tests/test_embalagem_versao.py` | `3 failed`: backend, Inno Setup e roteiro ainda 1.0.14 | Todos em 1.0.15; backend `499 passed, 9 deselected` |

## Arquivo real baixado

`%TEMP%/vf-nota.xml`, NF-e **446817**, SHA-256
`ea3051184f0bd3802b2cf716f2c295cff42ab97d017183e33188c10208fe4dfb`.
O teste `T8 real` fez upload, conferiu a pergunta desligada, confirmou a entrada
e consultou a API do banco temporário: `CX 00050 KAISER LT 350ML`, **600 UN**,
custo **2,74**, venda sugerida **3,56**. Nenhum “50” foi convertido em estoque.

## Comandos de reprodução

- Backend, dentro de `backend/`, sem PYTHONPATH:
  `.venv/Scripts/python -X utf8 -I -m pytest -q --tb=short`.
- Raiz: `npm run build`, `npx eslint .`, `node --test frontend-tests/*.test.mjs`.
- Navegador integral: `npx playwright test --workers=1` (TEMP/TMP/TMPDIR fora
  do repo; `VF_XML_REAL` aponta para a fonte baixada para incluir o caso real).
- Aceite em 3021: definir `VF_E2E_API_PORT=3021` e
  `VF_EMBALAGEM_API=http://127.0.0.1:3021`; rodar
  `npx playwright test e2e/embalagem.spec.ts --workers=1`.
- Aceite do artefato: `VF_TEST_EXE` aponta para o executável extraído e
  `npx playwright test --config playwright.exe.config.ts --workers=1`.
  O harness exige health 1.0.15 e usa banco temporário, porta 3021 e painel vazio.

Logs completos e capturas ficam em `output/` (fora do git). A matriz T1–T14 e
o diário recebem o commit, run e artefato efetivamente observados no portão.
