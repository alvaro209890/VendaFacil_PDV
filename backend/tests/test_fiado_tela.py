"""F2.7: a tela mostra o histórico e o erro de pagamento acima do pendente."""
from pathlib import Path
from fastapi.testclient import TestClient
from auth import _agora, _gerar_jwt, _token_user
from main import app
import contas_receber
from test_transacoes import checkout_local, loja

RAIZ = Path(__file__).resolve().parents[2]
TELA = RAIZ / 'src' / 'pages' / 'ContasReceber.tsx'


def test_f27_tela_mostra_historico_e_erro_de_excedente():
    texto = TELA.read_text(encoding='utf-8')
    assert 'Pagamento maior que o pendente.' in texto
    assert 'pagamentos.map' in texto
    assert 'Histórico' in texto


def test_lista_devolve_historico_da_baixa(checkout_local, monkeypatch):
    api, local, user, produto, cliente, _ = checkout_local
    monkeypatch.setattr(contas_receber, 'db', local)
    headers = {'Authorization': 'Bearer ' + _gerar_jwt(_token_user(local.get_user_by_usuario('transacao')))}
    cliente_http = TestClient(app, raise_server_exceptions=False)
    venda = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
        'forma_pagamento': 'fiado', 'cliente_id': cliente['id'],
    })
    assert venda.status_code == 201
    conta_id = local.list_contas_receber(user)[0]['id']
    pago = cliente_http.post(
        f'/api/contas-receber/{conta_id}/pagar', headers=headers,
        json={'valor': 0.5, 'forma': 'dinheiro'},
    )
    cliente_http.close()
    assert pago.status_code == 200
    lista = local.list_contas_receber(user)
    assert lista[0]['pagamentos'][0]['valor'] == 0.5
    assert lista[0]['pagamentos'][0]['forma'] == 'dinheiro'
