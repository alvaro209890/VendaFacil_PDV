# ✅ Testes automatizados

Há uma suíte de testes (pytest) cobrindo a lógica crítica do **PDV** e do
**Painel**. Eles usam um banco temporário (não tocam nos seus dados) e o
`TestClient` do FastAPI.

## O que é coberto

**PDV** (`backend/tests/`): saúde da API, checkout baixando estoque, bloqueio por
estoque insuficiente, entrada manual de estoque, importação de XML (criar/repor),
fluxo de caixa (abertura → venda → sangria → fechamento com diferença),
relatório de vendas e exportação de backup.

**Painel** (`painel/tests/`): setup/login do admin, login incorreto, CRUD de
contas, validação de conta do PDV, contas da matemática financeira, troca de
senha e proteção contra força-bruta (rate limit).

## Como rodar

Instale as dependências de teste (arquivo `requirements-dev.txt` na raiz) em
cada venv e rode o pytest na respectiva pasta. No Windows, sem `PYTHONPATH`
herdado e com `-X utf8 -I`:

```bat
:: PDV
backend\.venv\Scripts\python.exe -X utf8 -I -m pip install -r requirements-dev.txt
cd backend && .venv\Scripts\python.exe -X utf8 -I -m pytest -q --tb=short && cd ..

:: Painel
painel\.venv\Scripts\python.exe -X utf8 -I -m pip install -r requirements-dev.txt
cd painel && .venv\Scripts\python.exe -X utf8 -I -m pytest -q --tb=short && cd ..

:: Front
npm run build && npx eslint .
node --test frontend-tests/*.test.mjs
npx playwright test --workers=1
```

`backend/pytest.ini` desmarca os testes `homologacao` (SEFAZ-MT real): eles só
rodam com `-m homologacao` e com o certificado, o CSC e os dados da própria loja
no cofre. Em 12/11/2026: backend 460 verdes e 9 desmarcados, painel 23, Node 36,
E2E 90 (Chromium, 1 worker). O `.exe` é validado por `scripts/roteiro_exe.py`
(ver `TESTE_WINDOWS.md`).

> Rode em cada pasta separadamente (PDV e Painel têm, cada um, seu próprio
> `main.py`).
