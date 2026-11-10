"""C09: cliente com dívida não some e referência de conta é validada."""
import pytest
import database
from fastapi.testclient import TestClient
from auth import _agora, _gerar_jwt, _token_user
from main import app
import clientes
import contas_receber
import vendas


@pytest.fixture
def loja_c09(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_DIR', tmp_path)
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'vendafacil.db')
    local = database.Database()
    agora = _agora()
    user = local.create_user('transacao', 'Transação', 'hash_de_fixture', agora)
    monkeypatch.setattr(vendas, 'db', local)
    monkeypatch.setattr(clientes, 'db', local)
    monkeypatch.setattr(contas_receber, 'db', local)
    produto = local.create_produto(user['id'], 'Transação', 1, 2, 5, 0, '', 'UN', agora)
    cliente = local.create_cliente(user['id'], 'Cliente', '', '', '', '', agora)
    headers = {'Authorization': 'Bearer ' + _gerar_jwt(_token_user(local.get_user_by_usuario('transacao')))}
    api = TestClient(app, raise_server_exceptions=False)
    yield api, local, user['id'], produto, cliente, headers
    api.close()
    local.close()


def test_c09_cliente_com_divida_nao_some(loja_c09):
    api, local, user, produto, cliente, headers = loja_c09
    venda = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
        'forma_pagamento': 'fiado', 'cliente_id': cliente['id'],
    })
    assert venda.status_code == 201, venda.text
    resposta = api.delete(f"/api/clientes/{cliente['id']}", headers=headers)
    assert resposta.status_code == 409
    nomes = [c['nome'] for c in api.get('/api/clientes', headers=headers).json()['clientes']]
    assert cliente['nome'] in nomes
    assert local.list_contas_receber(user)[0]['valor_pendente'] == 2


def test_c09_referencia_alheia_nao_abre_fiado(loja_c09):
    api, local, user, produto, cliente, headers = loja_c09
    antes = len(local.list_contas_receber(user))
    for corpo in ({'cliente_id': 999999, 'valor_total': 10}, {'venda_id': 999999, 'valor_total': 10}):
        resposta = api.post('/api/contas-receber', headers=headers, json=corpo)
        assert resposta.status_code == 400, resposta.text
    assert len(local.list_contas_receber(user)) == antes
