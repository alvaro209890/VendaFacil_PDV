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

Instale as dependências de teste em cada venv e rode o pytest na respectiva pasta:

```bash
# PDV
backend/.venv/bin/pip install -r requirements-dev.txt
cd backend && .venv/bin/python -m pytest -q

# Painel
painel/.venv/bin/pip install -r requirements-dev.txt
cd painel && .venv/bin/python -m pytest -q
```

> Rode em cada pasta separadamente (PDV e Painel têm, cada um, seu próprio
> `main.py`).
