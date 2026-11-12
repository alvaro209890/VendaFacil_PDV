"""F1.13: ataques reproduzidos pelo orquestrador, não pelo relato do subagente."""
from test_transacoes import checkout_local, loja


def test_desconto_no_limite_e_um_centavo_acima(checkout_local):
    api, _, _, produto, _, headers = checkout_local
    igual = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}], 'desconto': 2,
    })
    assert igual.status_code == 201
    assert igual.json()['venda']['total'] == 0
    acima = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}], 'desconto': 2.01,
    })
    assert acima.status_code == 400


def test_fracionado_exato_e_excesso_de_um_milesimo(checkout_local):
    api, local, user, produto, _, headers = checkout_local
    local.update_produto(produto['id'], user, estoque=2.5)
    exato = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 2.5}],
    })
    assert exato.status_code == 201
    assert local.get_produto(produto['id'])['estoque'] == 0
    local.update_produto(produto['id'], user, estoque=2.5)
    excesso = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 2.501}],
    })
    assert excesso.status_code == 400
    assert local.get_produto(produto['id'])['estoque'] == 2.5


def test_itens_repetidos_somados_nao_furam_estoque(checkout_local):
    api, local, user, produto, _, headers = checkout_local
    local.update_produto(produto['id'], user, estoque=5)
    resposta = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 3}] * 2,
    })
    assert resposta.status_code in (400, 409)
    assert local.get_produto(produto['id'])['estoque'] == 5
    assert not local.list_vendas(user)


def test_motivo_curto_recusado_e_limite_aceito(checkout_local):
    api, local, user, produto, _, headers = checkout_local
    venda = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
    }).json()['venda']
    curto = api.post(f"/api/vendas/{venda['id']}/cancelar", headers=headers, json={'motivo': 'ab'})
    assert curto.status_code == 422
    assert local.get_venda(venda['id'], user)['status'] == 'concluida'
    longo = api.post(f"/api/vendas/{venda['id']}/cancelar", headers=headers, json={'motivo': 'x' * 255})
    assert longo.status_code == 200
    assert local.get_produto(produto['id'])['estoque'] == 5


def test_preco_e_custo_zero_nao_baixa_estoque(checkout_local):
    """D3: produto sem preço de venda é recusado sem mexer no estoque."""
    api, local, user, produto, _, headers = checkout_local
    local.update_produto(produto['id'], user, preco_venda=0, preco_custo=0, estoque=10)
    resposta = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
    })
    assert resposta.status_code == 400
    assert local.get_produto(produto['id'])['estoque'] == 10


def test_d4_checkout_sem_caixa_aberto_continua_permitido(checkout_local):
    api, local, user, produto, _, headers = checkout_local
    assert local.get_caixa_aberto(user) is None
    resposta = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
    })
    assert resposta.status_code == 201
