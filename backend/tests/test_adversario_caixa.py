"""F2.13: sequências estranhas de caixa e fiado não reescrevem o fechamento."""
from fastapi.testclient import TestClient
from auth import _agora, _gerar_jwt, _token_user
from main import app
import caixa
import contas_receber
from test_transacoes import checkout_local, loja


def test_pagar_conta_cancelada_recusado(checkout_local, monkeypatch):
    api, local, user, produto, cliente, _ = checkout_local
    monkeypatch.setattr(contas_receber, 'db', local)
    headers = {'Authorization': 'Bearer ' + _gerar_jwt(_token_user(local.get_user_by_usuario('transacao')))}
    cliente_http = TestClient(app, raise_server_exceptions=False)
    venda = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
        'forma_pagamento': 'fiado', 'cliente_id': cliente['id'],
    })
    assert venda.status_code == 201
    conta = local.list_contas_receber(user)[0]
    assert local.cancelar_conta_receber(conta['id'], user, _agora())
    resposta = cliente_http.post(f"/api/contas-receber/{conta['id']}/pagar", headers=headers, json={'valor': 1})
    cliente_http.close()
    assert resposta.status_code == 409
    atual = local.get_conta_receber(conta['id'], user)
    assert atual['status'] == 'cancelado'
    assert atual['pagamentos'] == []
    assert atual['valor_pendente'] == conta['valor_pendente'] or atual['valor_pendente'] == 0


def test_cancelar_venda_de_sessao_fechada_nao_reescreve_caixa(checkout_local, monkeypatch):
    api, local, user, produto, _, headers = checkout_local
    monkeypatch.setattr(caixa, 'db', local)
    cliente_http = TestClient(app, raise_server_exceptions=False)
    assert cliente_http.post('/api/caixa/abrir', headers=headers, json={'valor_abertura': 10}).status_code == 200
    venda = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
        'forma_pagamento': 'dinheiro',
    })
    assert venda.status_code == 201
    venda_id = venda.json()['venda']['id']
    fechado = cliente_http.post('/api/caixa/fechar', headers=headers, json={'valor_fechamento': 12, 'observacao': ''})
    cliente_http.close()
    assert fechado.status_code == 200, fechado.text
    esperado = fechado.json()['sessao']['valor_esperado']
    estoque = local.get_produto(produto['id'])['estoque']
    resposta = api.post(f'/api/vendas/{venda_id}/cancelar', headers=headers, json={'motivo': 'Caixa já fechado'})
    assert resposta.status_code == 409
    assert 'fechad' in resposta.text.lower()
    assert local.get_produto(produto['id'])['estoque'] == estoque
    sessao = local.list_caixa_historico(user)[0]
    assert sessao['valor_esperado'] == esperado
    assert local.get_venda(venda_id, user)['status'] == 'concluida'


def test_fechamento_nao_entra_no_meio_do_checkout():
    from pathlib import Path
    texto = (Path(__file__).resolve().parents[1] / 'database.py').read_text(encoding='utf-8')
    inicio = texto.find('def checkout_atomico')
    trecho = texto[inicio:texto.find('def cancelar_venda', inicio)]
    assert 'BEGIN IMMEDIATE' in trecho
    assert trecho.find('BEGIN IMMEDIATE') < trecho.find('caixa_sessoes') < trecho.find('INSERT INTO vendas')
