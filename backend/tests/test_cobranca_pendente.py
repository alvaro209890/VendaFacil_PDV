"""L05: cobrança aprovada sobrevive a falha de checkout e não cobra de novo."""
import mercadopago
from database import db


class _PointAprovada:
    def __init__(self):
        self.criacoes = 0

    def configurar_modo_pdv(self, device_id):
        return None

    def consultar_cobranca(self, order_id):
        return {
            'id': order_id,
            'status': 'processed',
            'transactions': {'payments': [{'id': 'PAY-L05', 'status': 'approved', 'amount': '2.00'}]},
        }

    def consultar_pagamento(self, payment_id):
        return {'id': payment_id, 'status': 'approved'}

    def criar_cobranca(self, *args, **kwargs):
        self.criacoes += 1
        return {'id': 'ORD-NOVA'}


def test_l05_cobranca_aprovada_nao_gera_segunda_venda(client, auth, monkeypatch):
    ponto = _PointAprovada()
    monkeypatch.setattr(mercadopago, '_cliente', lambda: ponto)
    db.salvar_config_maquininha({'habilitado': 1, 'device_id': 'POINT-L05', 'pix_integrado': 0}, 'agora')
    produto = client.post('/api/produtos', headers=auth, json={
        'nome': 'Item cobranca', 'preco_venda': 2, 'preco_custo': 1, 'estoque': 1,
        'codigo_barras': '7891000777001',
    })
    assert produto.status_code == 201, produto.text
    produto_id = produto.json()['produto']['id']
    consulta = client.get('/api/maquininha/cobranca/ORD-L05', headers=auth)
    assert consulta.status_code == 200, consulta.text
    assert consulta.json()['payment_id'] == 'PAY-L05'
    sem_estoque = client.post('/api/vendas/checkout', headers=auth, json={
        'itens': [{'produto_id': produto_id, 'quantidade': 2}],
        'forma_pagamento': 'credito',
        'pagamento': {'payment_id': 'PAY-L05'},
    })
    assert sem_estoque.status_code in (400, 409)
    outra = client.post('/api/maquininha/cobranca', headers=auth, json={'valor': 2, 'forma': 'credito'})
    assert outra.status_code == 409
    assert ponto.criacoes == 0
    primeira = client.post('/api/vendas/checkout', headers=auth, json={
        'itens': [{'produto_id': produto_id, 'quantidade': 1}],
        'forma_pagamento': 'credito',
        'pagamento': {'payment_id': 'PAY-L05'},
    })
    assert primeira.status_code == 201, primeira.text
    venda_id = primeira.json()['venda']['id']
    segunda = client.post('/api/vendas/checkout', headers=auth, json={
        'itens': [{'produto_id': produto_id, 'quantidade': 1}],
        'forma_pagamento': 'credito',
        'pagamento': {'payment_id': 'PAY-L05'},
    })
    assert segunda.status_code == 200
    assert segunda.json()['venda']['id'] == venda_id
    assert client.get(f'/api/produtos/{produto_id}', headers=auth).json()['produto']['estoque'] == 0
