# Tarefas

Ordem fixa. Um `[~]` por vez.

## E1 — Linha de base

- [x] **E1.1** Ler `02_ESPECIFICACAO.md` e `01_REGRAS.md`. Não editar código ainda. — 9a47c2b · Leitura integral da especificação e regras; execução local autorizada
- [x] **E1.2** Rodar a suíte backend e anotar verdes/falhas em `06_DIARIO.md` e T1. — 532a9aa · backend: .venv/Scripts/python -X utf8 -I -m pytest -q --tb=short: 466 passed, 9 deselected

## E2 — Cadastro e estoque

- [x] **E2.1** Testes T2–T6 e T9 falhando. Colunas novas no produto, default da opção desligado, produtos antigos intactos. — 051e969 · 9 regressões falharam antes; pytest backend inteiro: 475 passed, 9 deselected
- [x] **E2.2** API de cadastro e a tela Produtos com a opção, os dois preços e o texto “3 carteiras e 5 avulsos”. — b1a6075 · npm run build; npx eslint .; node --test frontend-tests/embalagem.test.mjs: 1 passed; backend 475 passed
- [x] **E2.3** Troca de fator com estoque não recontagem (T9). — 5fa54df · T9: pytest backend 476 passed, 9 deselected; fator e ativação preservam estoque

## E3 — Caixa

- [x] **E3.1** Checkout aceita o modo. Sem modo = unidade (T5). Carteira só no modo embalagem. — 3acf694 · pytest backend: 487 passed, 9 deselected; antes 10 failed e 1 passed em vendas
- [x] **E3.2** Baixa, recusa por falta de unidade, histórico e lucro (T2, T3, T4). — 6bfad27 · pytest backend: 488 passed, 9 deselected; lucro 14,50 e estorno por snapshot
- [x] **E3.3** PDV com os dois botões e o código de barras da embalagem lançando a carteira. — d41e91d · Playwright embalagem e cadastro: 9 passed; Node 2 passed; build e lint verdes; backend 488 passed

## E4 — XML

- [x] **E4.1** Prévia converte embalagem já configurada e não mexe no preço de venda (T7). — 29d718c · pytest backend 492 passed, 9 deselected; Playwright XML/embalagem 18 passed
- [x] **E4.2** Nota em UN não multiplica pelo número do nome. A pergunta aparece; sem resposta, fator 1 (T8). O caso Kaiser da especificação entra no teste. — f7fe918 · Playwright e2e/embalagem.spec.ts com VF_XML_REAL: T8 real passou, 18 testes verdes; hash no 03_TESTES

## E5 — Cupom

- [x] **E5.1** Linha fiscal e cupom com a unidade e o preço vendidos (T10). Homologação. Sem chamada à SEFAZ. — d04c3ec · T10 falhou antes com UN; pytest backend 493 passed e teste fiscal payload atualizado 1 passed; sem transmissão

## E6 — Navegador

- [x] **E6.1** Playwright do T11 no PDV isolado. Corrigir o que a tela mostrar errado e repetir. — 1544c43 · Backend 496 passed, 9 deselected; Playwright integral 95 passed; aceite porta 3021 4 passed; build/lint/Node 38 verdes. Correções de revisão: entrada por embalagem, códigos, migração e campos derivados da prévia

## E7 — Documento

- [x] **E7.1** `docs/ESTOQUE_E_XML.md`, manual do operador e treinamento do caixa: exemplo da carteira com R$ 20 e R$ 2, a pergunta na prévia do XML, e que o número no nome não vira estoque. — 69a2ade · Manual do app e 3 documentos atualizados; npm run build e npx eslint . verdes; backend 496; vault receberá versão, commit e artefato comprovados ao fechar

## E8 — Versão e entrega

- [x] **E8.1** Subir para 1.0.15 em `backend/version.py`, `installer/vendafacil.iss` e `scripts/roteiro_exe.py`. Não reescrever docs históricos que citam 1.0.14 como entrega passada. — 781718b · 3 testes de versão falharam antes; pytest backend 499 passed, 9 deselected depois
- [x] **E8.2** T12 e T13 verdes. — de9fd08 · npm run build e npx eslint . exit 0; backend 499, Node 38 e navegador integral 95 passed
- [~] **E8.3** Commit dos caminhos desta entrega, `git push origin master`.
- [ ] **E8.4** T14: workflow Build Windows EXE verde. Anotar o número do run e onde baixar o Setup.

## Portão

Só fecha com T1–T14 ✅, nenhum `[ ]` ou `[~]`, `master` no GitHub e o workflow verde. Aí o painel vai para ✅ CONCLUÍDO e a mensagem final do WhatsApp leva: versão, commit, testes antes/depois, link do artefato.
