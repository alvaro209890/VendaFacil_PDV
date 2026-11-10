"""P23: referência e retorno não podem vazar outro usuário."""
from auth import _agora, _gerar_jwt, _token_user
from test_transacoes import checkout_local, loja


def test_v14_cliente_alheio_nao_entra_no_checkout(checkout_local):
    api, local, user, produto, _, headers = checkout_local
    outro = local.create_user('vizinho', 'Vizinho', 'hash_de_fixture', _agora())
    alheio = local.create_cliente(outro['id'], 'Cliente alheio', '', '', '', '', _agora())
    resposta = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
        'cliente_id': alheio['id'],
    })
    assert resposta.status_code in (400, 404)
    assert local.get_produto(produto['id'])['estoque'] == 5
    assert not local.list_vendas(user)


def test_v14_categoria_alheia_nao_vaza_no_retorno(checkout_local, monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    import categorias
    api, local, user, _, _, headers = checkout_local
    api = TestClient(app, raise_server_exceptions=False)
    outro = local.create_user('vizinho', 'Vizinho', 'hash_de_fixture', _agora())
    cat = local.create_categoria(outro['id'], 'Alheia', '#111111', _agora())
    monkeypatch.setattr(categorias, 'db', local)
    alheio = {'Authorization': 'Bearer ' + _gerar_jwt(_token_user(local.get_user_by_usuario('transacao')))}
    resposta = api.put(f"/api/categorias/{cat['id']}", headers=alheio, json={'nome': 'Invadida'})
    api.close()
    assert resposta.status_code == 404
    assert 'Alheia' not in resposta.text
    assert local._conn.execute('SELECT nome FROM categorias WHERE id = ?', (cat['id'],)).fetchone()[0] == 'Alheia'
