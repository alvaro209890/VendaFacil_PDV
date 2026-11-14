# Diário

- **2026-11-13** — Plano criado. Nada executado. Spec fechada pelo Álvaro: carteira R$ 20 com 20 palheiros a R$ 2 cada; XML em UN não multiplica pelo número do nome. (autor: Cursor | 2026-11-13)

- **2026-11-13 — Codex — E1.1 fim**: Leitura integral da especificação e regras; execução local autorizada. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E1.2 inicio**: Suíte backend de partida. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E1.2 fim**: backend: .venv/Scripts/python -X utf8 -I -m pytest -q --tb=short: 466 passed, 9 deselected. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E2.1 inicio**: Regressões de cadastro e migração. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E2.1 fim**: 9 regressões falharam antes; pytest backend inteiro: 475 passed, 9 deselected. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E2.2 inicio**: Tela de cadastro, dois preços e estoque de balcão; teste Node falhou por módulo ausente. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E2.2 fim**: npm run build; npx eslint .; node --test frontend-tests/embalagem.test.mjs: 1 passed; backend 475 passed. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E2.3 inicio**: T9: fator 20 para 30 preserva 65 unidades e dois preços; já verde após E2.1, sem defeito adicional. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E2.3 fim**: T9: pytest backend 476 passed, 9 deselected; fator e ativação preservam estoque. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E3.1 inicio**: Checkout: 10 falhas e 1 verde antes; T2-T6 e snapshots. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E3.1 fim**: pytest backend: 487 passed, 9 deselected; antes 10 failed e 1 passed em vendas. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E3.2 inicio**: Verificar lucro, movimentos, cancelamento e concorrência. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E3.2 fim**: pytest backend: 488 passed, 9 deselected; lucro 14,50 e estorno por snapshot. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E3.3 inicio**: Dois botões, códigos principal e avulso, rascunho separado por modo; navegador em validação. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E3.3 fim**: Playwright embalagem e cadastro: 9 passed; Node 2 passed; build e lint verdes; backend 488 passed. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E4.1 inicio**: XML: 4 regressões falharam antes; prévia deve explicar fator e preservar preços. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E4.1 fim**: pytest backend 492 passed, 9 deselected; Playwright XML/embalagem 18 passed. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E4.2 inicio**: Teste real da NF-e 446817: vf-nota.xml, 600 UN e custo 2,74 sem conversão pelo nome. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E4.2 fim**: Playwright e2e/embalagem.spec.ts com VF_XML_REAL: T8 real passou, 18 testes verdes; hash no 03_TESTES. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E5.1 inicio**: T10 falhou: uCom UN em vez de CART; corrigir snapshots fiscais sem transmitir. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E5.1 fim**: T10 falhou antes com UN; pytest backend 493 passed e teste fiscal payload atualizado 1 passed; sem transmissão. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E6.1 inicio**: Navegador integral, inspeção visual, T11 na porta 3021 e correções encontradas. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E6.1 fim**: Backend 496 passed, 9 deselected; Playwright integral 95 passed; aceite porta 3021 4 passed; build/lint/Node 38 verdes. Correções de revisão: entrada por embalagem, códigos, migração e campos derivados da prévia. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E7.1 inicio**: Atualizar manual dentro do app, documentação da loja, treinamento e Segundo Cérebro. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E7.1 fim**: Manual do app e 3 documentos atualizados; npm run build e npx eslint . verdes; backend 496; vault receberá versão, commit e artefato comprovados ao fechar. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E8.1 inicio**: Verificar sincronismo da versão 1.0.15 em backend, instalador e roteiro. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E8.1 fim**: 3 testes de versão falharam antes; pytest backend 499 passed, 9 deselected depois. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E8.2 inicio**: Portão final: build, lint, Node, backend e navegador; preparar validação do artefato. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E8.2 fim**: npm run build e npx eslint . exit 0; backend 499, Node 38 e navegador integral 95 passed. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-13 — Codex — E8.3 inicio**: Auditoria do commit final e push único origin/master. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-14 — Codex — E8.3 fim**: Push efetivo único: 9a47c2b..b3477e2 master -> master no mesmo origin via SSH já autorizado do server; HTTPS local recusava credencial. HEAD exato validado: 499 passed, 9 deselected. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-14 — Codex — E8.4 inicio**: Aguardar Build Windows EXE do commit b3477e2 e conferir Setup 1.0.15. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-14 — Codex — E8.4 fim**: gh run view 43549468463: success, HEAD b3477e2; artefato 14094704053 Setup ProductVersion 1.0.15; ZIP SHA256 igual ao digest GitHub; Playwright no exe publicado 4 passed, com XML real. Execução local no PCQUE001IMAP autorizada pelo Álvaro; sem SSH.

- **2026-11-14 — Cursor — reteste independente**: PDV 1.0.15 na porta 3021, banco temporário e painel vazio. Cadastro da carteira, compra de 2 carteiras, venda mista R$ 26, saldo 17, recusa da carteira seguinte e NF-e 446817 com 600 UN. Instalador local conferido, SHA-256 igual ao do vault. (autor: Cursor | 2026-11-14)

- **2026-11-14 — Codex — auditoria final**: 17 itens concluídos e T1–T14 verdes. HEAD e master público b3477e24d53cd9344c800fddaa4e5441d0aea8a8; backend no HEAD 499 passed, 9 deselected; Node 38; navegador 95; executável publicado 4. Build Windows EXE 43549468463 success. Setup 1.0.15 copiado para dist_installer, SHA-256 BB0A9823B90204B571777F2CB7438ACEA14BA68256430CC4FA47C7B0E5573B97. Segundo Cérebro atualizado e commitado: cd27c61 (ficha §11 e changelog). Nenhum segundo push: as evidências posteriores à publicação ficam no plano local e vault, sem mudar o código/manuais do master publicado. Download público do ZIP via nightly.link com digest idêntico ao GitHub; fonte real de XML e binários fora do git. Fiscal em homologação; não houve acesso ao banco real, certificado ou SEFAZ.
