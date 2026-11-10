"""C02: recebimento de fiado em dinheiro entra no caixa aberto."""
from fastapi.testclient import TestClient
from auth import _gerar_jwt, _token_user
from main import app
import caixa
import contas_receber
from test_transacoes import checkout_local, loja


def test_c02_recebimento_dinheiro_entra_no_caixa(checkout_local, monkeypatch):
    api, local, user, produto, cliente, _ = checkout_local
    monkeypatch.setattr(caixa, 'db', local)
    monkeypatch.setattr(contas_receber, 'db', local)
    headers = {'Authorization': 'Bearer ' + _gerar_jwt(_token_user(local.get_user_by_usuario('transacao')))}
    cliente_http = TestClient(app, raise_server_exceptions=False)
    assert cliente_http.post('/api/caixa/abrir', headers=headers, json={'valor_abertura': 10}).status_code == 200
    venda = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
        'forma_pagamento': 'fiado', 'cliente_id': cliente['id'],
    })
    assert venda.status_code == 201
    conta_id = local.list_contas_receber(user)[0]['id']
    dinheiro = cliente_http.post(
        f'/api/contas-receber/{conta_id}/pagar', headers=headers,
        json={'valor': 0.5, 'forma': 'dinheiro'},
    )
    assert dinheiro.status_code == 200
    esperado = local.resumo_caixa(local.get_caixa_aberto(user))['dinheiro_esperado']
    assert esperado == 10.5
    pix = cliente_http.post(
        f'/api/contas-receber/{conta_id}/pagar', headers=headers,
        json={'valor': 0.5, 'forma': 'pix'},
    )
    cliente_http.close()
    assert pix.status_code == 200
    assert local.resumo_caixa(local.get_caixa_aberto(user))['dinheiro_esperado'] == 10.5
