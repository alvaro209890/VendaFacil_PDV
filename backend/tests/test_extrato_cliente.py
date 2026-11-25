"""P22: extrato do cliente — o que comprou, que dia, quanto e o fiado.

Cobre o relatório que o lojista consulta no PDV (e exporta em PDF/CSV):
histórico de compras por cliente, com itens, filtro por período e isolamento
entre contas. Também garante que o detalhe da conta fiada traz a venda.
"""
from datetime import datetime, timedelta, timezone

import pytest
import database
from fastapi.testclient import TestClient
from auth import _agora, _gerar_jwt, _token_user
from main import app
import clientes
import contas_receber
import vendas


def _hoje_mt() -> str:
    return datetime.now(timezone(timedelta(hours=-4))).date().isoformat()


@pytest.fixture
def loja_p22(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_DIR", tmp_path)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "vendafacil.db")
    local = database.Database()
    agora = _agora()
    user = local.create_user("transacao", "Transação", "hash_de_fixture", agora)
    monkeypatch.setattr(vendas, "db", local)
    monkeypatch.setattr(clientes, "db", local)
    monkeypatch.setattr(contas_receber, "db", local)
    produto = local.create_produto(user["id"], "COCA COLA 2L", 1, 10, 20, 0, "", "UN", agora)
    cliente = local.create_cliente(user["id"], "Warli Rafael", "", "", "", "", agora)
    headers = {"Authorization": "Bearer " + _gerar_jwt(_token_user(local.get_user_by_usuario("transacao")))}
    api = TestClient(app, raise_server_exceptions=False)
    yield api, local, user["id"], produto, cliente, headers
    api.close()
    local.close()


def _vender(api, headers, produto, quantidade, forma="fiado", cliente=None):
    corpo = {"itens": [{"produto_id": produto["id"], "quantidade": quantidade}], "forma_pagamento": forma}
    if cliente is not None:
        corpo["cliente_id"] = cliente["id"]
    resposta = api.post("/api/vendas/checkout", headers=headers, json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["venda"]


def test_extrato_traz_compras_itens_e_resumo(loja_p22):
    api, local, user, produto, cliente, headers = loja_p22
    _vender(api, headers, produto, 3, "fiado", cliente)
    _vender(api, headers, produto, 1, "dinheiro", cliente)

    resposta = api.get(f"/api/clientes/{cliente['id']}/extrato", headers=headers)
    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()

    assert dados["cliente"]["id"] == cliente["id"]
    assert dados["resumo"]["compras"] == 2
    assert dados["resumo"]["total"] == 40  # 3 x 10 (fiado) + 1 x 10 (dinheiro)
    assert dados["resumo"]["fiado_total"] == 30
    assert dados["resumo"]["fiado_pendente"] == 30
    assert len(dados["compras"]) == 2
    # A mais recente vem primeiro.
    fiado = next(c for c in dados["compras"] if c["forma_pagamento"] == "fiado")
    assert fiado["itens"][0]["nome_produto"] == "COCA COLA 2L"
    assert fiado["itens"][0]["quantidade"] == 3
    assert fiado["itens"][0]["subtotal"] == 30
    assert fiado["conta"]["valor_pendente"] == 30
    assert fiado["conta"]["status"] == "pendente"
    dinheiro = next(c for c in dados["compras"] if c["forma_pagamento"] == "dinheiro")
    assert dinheiro["conta"] is None


def test_extrato_filtra_pelo_dia_comercial_de_mt(loja_p22):
    api, local, user, produto, cliente, headers = loja_p22
    _vender(api, headers, produto, 2, "fiado", cliente)
    hoje = _hoje_mt()

    dentro = api.get(f"/api/clientes/{cliente['id']}/extrato?inicio={hoje}&fim={hoje}", headers=headers)
    assert dentro.status_code == 200, dentro.text
    assert dentro.json()["resumo"]["compras"] == 1

    amanha = (datetime.fromisoformat(hoje) + timedelta(days=1)).date().isoformat()
    fora = api.get(f"/api/clientes/{cliente['id']}/extrato?inicio={amanha}", headers=headers)
    assert fora.status_code == 200, fora.text
    assert fora.json()["resumo"]["compras"] == 0
    assert fora.json()["compras"] == []


def test_extrato_valida_datas(loja_p22):
    api, local, user, produto, cliente, headers = loja_p22
    ruim = api.get(f"/api/clientes/{cliente['id']}/extrato?inicio=25/11/2026", headers=headers)
    assert ruim.status_code == 400, ruim.text
    invertido = api.get(
        f"/api/clientes/{cliente['id']}/extrato?inicio=2026-11-25&fim=2026-11-01", headers=headers
    )
    assert invertido.status_code == 400, invertido.text


def test_extrato_de_cliente_de_outra_conta_nao_vaza(loja_p22):
    api, local, user, produto, cliente, headers = loja_p22
    outro = local.create_user("outro", "Outro", "hash_de_fixture", _agora())
    alheio = local.create_cliente(outro["id"], "Cliente do Outro", "", "", "", "", _agora())
    resposta = api.get(f"/api/clientes/{alheio['id']}/extrato", headers=headers)
    assert resposta.status_code == 404, resposta.text


def test_detalhe_da_conta_traz_o_que_foi_comprado(loja_p22):
    api, local, user, produto, cliente, headers = loja_p22
    _vender(api, headers, produto, 4, "fiado", cliente)
    conta_id = local.list_contas_receber(user)[0]["id"]

    resposta = api.get(f"/api/contas-receber/{conta_id}", headers=headers)
    assert resposta.status_code == 200, resposta.text
    conta = resposta.json()["conta"]
    assert conta["venda_id"]
    assert conta["itens"][0]["nome_produto"] == "COCA COLA 2L"
    assert conta["itens"][0]["quantidade"] == 4
    assert conta["venda"]["id"] == conta["venda_id"]
