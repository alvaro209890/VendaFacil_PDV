"""F2.5: pagamento do fiado não passa do pendente nem aceita valor não positivo."""
import pytest
from fastapi.testclient import TestClient
from auth import _gerar_jwt, _token_user
from main import app
import contas_receber
from test_transacoes import checkout_local, loja


@pytest.fixture
def fiado(checkout_local, monkeypatch):
    api, local, user, produto, cliente, _ = checkout_local
    monkeypatch.setattr(contas_receber, 'db', local)
    headers = {'Authorization': 'Bearer ' + _gerar_jwt(_token_user(local.get_user_by_usuario('transacao')))}
    venda = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
        'forma_pagamento': 'fiado', 'cliente_id': cliente['id'],
    })
    assert venda.status_code == 201
    conta_id = local.list_contas_receber(user)[0]['id']
    cliente_http = TestClient(app, raise_server_exceptions=False)
    yield cliente_http, local, user, conta_id, headers
    cliente_http.close()


def test_c04_pagamento_maior_que_pendente_recusado(fiado):
    api, local, user, conta_id, headers = fiado
    resposta = api.post(f'/api/contas-receber/{conta_id}/pagar', headers=headers, json={'valor': 2.01})
    assert resposta.status_code == 400
    conta = local.get_conta_receber(conta_id, user)
    assert conta['valor_pendente'] == 2
    assert conta['status'] == 'pendente'
    assert conta['pagamentos'] == []


@pytest.mark.parametrize('valor', [0, -1])
def test_c05_pagamento_nao_positivo_400(fiado, valor):
    api, local, user, conta_id, headers = fiado
    resposta = api.post(f'/api/contas-receber/{conta_id}/pagar', headers=headers, json={'valor': valor})
    assert resposta.status_code == 400
    assert local.get_conta_receber(conta_id, user)['pagamentos'] == []
