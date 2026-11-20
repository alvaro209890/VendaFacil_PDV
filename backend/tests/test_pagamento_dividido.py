from uuid import uuid4
from xml.etree import ElementTree as ET

import pytest

import fiscal
import fiscal_direto
import pix
from test_fiscal_direto import _cfg, _produto_simples
from test_transacoes import checkout_local, loja


def _checkout(fixture, partes, **extras):
    api, _, _, produto, _, headers = fixture
    return api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
        'pagamentos': [{'forma': forma, 'valor': valor} for forma, valor in partes],
        **extras,
    })


@pytest.mark.parametrize('partes', [
    [], [('dinheiro', 1), ('pix', .98)], [('dinheiro', 1), ('pix', 1.02)],
    [('dinheiro', 0), ('pix', 2)], [('dinheiro', -1), ('pix', 3)],
    [('dinheiro', .995), ('pix', 1.005)], [('vale', 1), ('pix', 1)],
    [('fiado', 1), ('pix', 1)],
])
def test_pagamentos_invalidos_nao_baixam_estoque(checkout_local, partes):
    _, local, user, produto, _, _ = checkout_local
    assert _checkout(checkout_local, partes).status_code == 400
    assert local.get_produto(produto['id'], user)['estoque'] == produto['estoque']
    assert not local.list_vendas(user)


@pytest.mark.parametrize('valor', [.99, 1.01])
def test_aceita_um_centavo_de_tolerancia(checkout_local, valor):
    resp = _checkout(checkout_local, [('dinheiro', 1), ('pix', valor)])
    assert resp.status_code == 201, resp.text


def test_caixa_misto_com_troco_fiado_e_dados_legados(checkout_local):
    _, local, user, _, cliente, _ = checkout_local
    sessao = local.abrir_caixa(user, 10, '2020-01-01')
    local.create_venda(user, None, 2, 0, 'dinheiro', '', [], '2020-01-02')
    partes = [('dinheiro', .50), ('debito', .25), ('fiado', 1.25)]
    referencia = str(uuid4())
    resp = _checkout(checkout_local, partes, dinheiro_recebido=5, cliente_id=cliente['id'],
                     referencia_checkout=referencia)
    assert resp.status_code == 201, resp.text
    venda = resp.json()['venda']
    assert venda['forma_pagamento'] == 'misto'
    assert [(p['forma'], p['valor']) for p in venda['pagamentos']] == partes
    assert _checkout(checkout_local, partes, dinheiro_recebido=5, cliente_id=cliente['id'],
                     referencia_checkout=referencia).status_code == 200
    conta, = local.list_contas_receber(user)
    assert conta['valor_pendente'] == 1.25
    resumo = local.resumo_caixa(sessao)
    assert resumo['vendas_qtd'] == 2
    assert resumo['vendas_dinheiro'] == 2.50
    assert resumo['dinheiro_esperado'] == 12.50


def test_nota_com_duas_formas_e_troco(client, auth):
    produto = _produto_simples(client, auth, 'Produto para pagamento misto')
    from database import db
    total = produto['preco_venda']
    resp = client.post('/api/vendas/checkout', headers=auth, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
        'pagamentos': [{'forma': 'dinheiro', 'valor': 2}, {'forma': 'pix', 'valor': total - 2}],
        'dinheiro_recebido': 5,
    })
    assert resp.status_code == 201, resp.text
    venda = db.get_venda_completa(resp.json()['venda']['id'])
    payload = fiscal.montar_payload(venda, _cfg())
    assert payload['formas_pagamento'] == [
        {'forma_pagamento': '01', 'valor_pagamento': 5},
        {'forma_pagamento': '17', 'valor_pagamento': total - 2},
    ]
    assert payload['valor_troco'] == 3
    xml = ET.fromstring(fiscal_direto.montar_documento(venda, _cfg()).xml)
    pag = xml.find('.//n:pag', {'n': fiscal_direto.NFE_NS})
    assert [el.text for el in pag.findall('{*}detPag/{*}tPag')] == ['01', '17']
    assert [el.text for el in pag.findall('{*}detPag/{*}vPag')] == ['5.00', f'{total - 2:.2f}']
    assert pag.findtext('{*}vTroco') == '3.00'


def test_pix_e_multiplas_cobrancas_point_no_mesmo_checkout(checkout_local, monkeypatch):
    _, local, user, _, _, _ = checkout_local
    for pid, valor, forma in [('p1', .70, 'credit_card'), ('p2', .30, 'debit_card')]:
        local.salvar_cobranca_aprovada(user, 'ord-' + pid, pid, valor, forma, '{}', '2020-01-01')
    assert local.cobranca_aprovada_sem_venda(user, ['p1', 'p2']) is None
    monkeypatch.setattr(pix, '_mp_config', lambda: ('fixture', ''))
    monkeypatch.setattr(pix, '_mp_req', lambda *_: {
        'id': 'pix1', 'status': 'approved', 'payment_method_id': 'pix', 'transaction_amount': 1,
    })
    parcelas = [
        {'forma': 'credito', 'valor': .60, 'pagamento': {'payment_id': 'p1'}},
        {'forma': 'debito', 'valor': .30, 'pagamento': {'payment_id': 'p2'}},
        {'forma': 'pix', 'valor': 1.10, 'pix_mp_id': 'pix1'},
    ]
    invalida = _checkout(checkout_local, [], pagamentos=parcelas)
    assert invalida.status_code == 409
    parcelas[0]['valor'] = .70
    parcelas[2]['valor'] = 1
    resp = _checkout(checkout_local, [], pagamentos=parcelas)
    assert resp.status_code == 201, resp.text
    assert local.cobranca_aprovada_sem_venda(user) is None
    venda_id = resp.json()['venda']['id']
    assert all(local.venda_da_cobranca(user, pid) == venda_id for pid in ('p1', 'p2', 'pix1'))
    assert _checkout(checkout_local, [], pagamentos=parcelas).status_code == 200
