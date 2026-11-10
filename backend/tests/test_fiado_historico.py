"""P21: baixa de fiado deixa histórico."""
from fastapi.testclient import TestClient
from auth import _gerar_jwt, _token_user
from main import app
import contas_receber
from test_transacoes import checkout_local, loja


def test_c03_baixa_parcial_grava_historico(checkout_local, monkeypatch):
    api, local, user, produto, cliente, headers = checkout_local
    monkeypatch.setattr(contas_receber, 'db', local)
    cliente_http = TestClient(app, raise_server_exceptions=False)
    headers = {'Authorization': 'Bearer ' + _gerar_jwt(_token_user(local.get_user_by_usuario('transacao')))}
    venda = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
        'forma_pagamento': 'fiado', 'cliente_id': cliente['id'],
    })
    assert venda.status_code == 201
    conta_id = local.list_contas_receber(user)[0]['id']
    resposta = cliente_http.post(f'/api/contas-receber/{conta_id}/pagar', headers=headers, json={
        'valor': 0.5, 'forma': 'dinheiro',
    })
    cliente_http.close()
    assert resposta.status_code == 200, resposta.text
    atual = resposta.json()['conta']
    assert atual['status'] == 'parcial'
    assert atual['valor_pendente'] == 1.5
    pagamento = atual['pagamentos'][0]
    assert pagamento['valor'] == 0.5
    assert pagamento['forma'] == 'dinheiro'
    assert pagamento['user_id'] == user
    assert pagamento['criado_em']
