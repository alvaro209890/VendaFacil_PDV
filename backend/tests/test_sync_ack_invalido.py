"""F2.22/L07: falha de protocolo não dá baixa na fila offline."""
import json
import urllib.request

import pytest
import conta
import sync_client
from database import db


@pytest.fixture
def fila_ack(monkeypatch):
    pendentes = [
        {'id': 98001, 'uuid': 'ack-valida-1', 'total': 1, 'desconto': 0,
         'forma_pagamento': 'dinheiro', 'criado_em': '2026-01-01T00:00:00'},
        {'id': 98002, 'uuid': 'ack-valida-2', 'total': 2, 'desconto': 0,
         'forma_pagamento': 'dinheiro', 'criado_em': '2026-01-01T00:00:01'},
    ]
    marcadas = []
    monkeypatch.setattr(db, 'vendas_pendentes_sync', lambda limite=100: pendentes)
    monkeypatch.setattr(db, 'marcar_vendas_sincronizadas', lambda ids: marcadas.extend(ids))
    monkeypatch.setattr(conta, 'PAINEL_URL', 'http://painel.exemplo')
    monkeypatch.setattr(conta, 'token_sync', lambda: 'fixture-nao-credencial')
    monkeypatch.setattr(conta, 'licenca_obrigatoria', lambda: True)

    def responder(corpo):
        class Resposta:
            status = 200
            def read(self):
                return corpo
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
        monkeypatch.setattr(urllib.request, 'urlopen', lambda *args, **kwargs: Resposta())
    return marcadas, responder


@pytest.mark.parametrize('corpo', [
    b'<html>indisponivel</html>', b'{incompleto', b'\xff',
    b'null', b'[]', b'0', b'"texto"',
])
def test_l07_corpo_invalido_preserva_fila_sem_excecao(fila_ack, corpo):
    marcadas, responder = fila_ack
    responder(corpo)
    assert sync_client.enviar_pendentes() == 0
    assert marcadas == []
    # Um próximo ciclo válido ainda consegue entregar a venda; não houve baixa indevida.
    responder(json.dumps({'aceitas': ['ack-valida-1']}).encode())
    assert sync_client.enviar_pendentes() == 1
    assert marcadas == [98001]


@pytest.mark.parametrize('ack', [
    {'aceitas': None, 'recebidas': 2},
    {'aceitas': 'ack-valida-1', 'recebidas': 2},
    {'aceitas': {'ack-valida-1': True}, 'recebidas': 2},
    {'aceitas': ['ack-valida-1', 42], 'recebidas': 2},
    {'recebidas': 2.0},
])
def test_l07_tipo_invalido_nao_cai_no_ack_legado(fila_ack, ack):
    marcadas, responder = fila_ack
    responder(json.dumps(ack).encode())
    assert sync_client.enviar_pendentes() == 0
    assert marcadas == []


@pytest.mark.parametrize('ack, esperadas', [
    ({'recebidas': 2}, [98001, 98002]),
    ({'recebidas': 1}, []),
    ({'aceitas': [], 'recebidas': 2}, []),
    ({'aceitas': ['ack-valida-2', 'externa', 'ack-valida-2']}, [98002]),
])
def test_l07_ack_valido_mantem_contrato(fila_ack, ack, esperadas):
    marcadas, responder = fila_ack
    responder(json.dumps(ack).encode())
    assert sync_client.enviar_pendentes() == len(esperadas)
    assert marcadas == esperadas


def test_l07_booleano_nao_e_contagem_legacy(fila_ack, monkeypatch):
    marcadas, responder = fila_ack
    pendentes = db.vendas_pendentes_sync()[:1]
    monkeypatch.setattr(db, 'vendas_pendentes_sync', lambda limite=100: pendentes)
    responder(b'{"recebidas": true}')
    assert sync_client.enviar_pendentes() == 0
    assert marcadas == []
