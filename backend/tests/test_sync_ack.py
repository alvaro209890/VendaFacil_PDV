"""L07: o ACK só marca a venda que o painel aceitou."""
import json
import urllib.request
import conta
import sync_client
from database import db


def test_l07_ack_parcial_nao_marca_rejeitada(monkeypatch):
    pendentes = [
        {'id': 9001, 'uuid': 'u-aceita', 'total': 1, 'desconto': 0,
         'forma_pagamento': 'dinheiro', 'criado_em': '2026-01-01T00:00:00'},
        {'id': 9002, 'uuid': 'u-recusada', 'total': 2, 'desconto': 0,
         'forma_pagamento': 'dinheiro', 'criado_em': '2026-01-01T00:00:01'},
    ]
    marcadas = []
    monkeypatch.setattr(db, 'vendas_pendentes_sync', lambda limite=100: pendentes)
    monkeypatch.setattr(db, 'set_venda_uuid', lambda *args: None)
    monkeypatch.setattr(db, 'marcar_vendas_sincronizadas', lambda ids: marcadas.extend(ids))
    monkeypatch.setattr(conta, 'PAINEL_URL', 'http://painel.exemplo')
    monkeypatch.setattr(conta, 'token_sync', lambda: 'tok')
    monkeypatch.setattr(conta, 'licenca_obrigatoria', lambda: True)

    class Resposta:
        status = 200
        def __init__(self, aceitas):
            self._corpo = json.dumps({'aceitas': aceitas, 'recebidas': len(aceitas)}).encode()
        def read(self):
            return self._corpo
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    def urlopen(req, timeout=None):
        corpo = json.loads(req.data.decode())
        return Resposta([corpo['vendas'][0]['uuid']])

    monkeypatch.setattr(urllib.request, 'urlopen', urlopen)
    assert sync_client.enviar_pendentes() == 1
    assert marcadas == [9001]
