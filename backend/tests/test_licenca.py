"""Testa o throttle de revalidação da licença (sem rede)."""
from datetime import datetime, timedelta, timezone

import conta


def _iso(horas_atras: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=horas_atras)).isoformat()


def test_cache_saudavel():
    assert conta._cache_saudavel({"ativo": True, "licenca_expira_em": None})
    assert not conta._cache_saudavel({"ativo": False})
    assert not conta._cache_saudavel({"ativo": True, "licenca_expira_em": _iso(48)})  # vencida


def test_precisa_revalidar_throttle():
    # saudável e validado há pouco → NÃO revalida (login instantâneo)
    assert conta._precisa_revalidar({"ativo": True, "validado_em": _iso(1)}) is False
    # saudável mas validado há muito tempo → revalida
    assert conta._precisa_revalidar({"ativo": True, "validado_em": _iso(20)}) is True
    # bloqueada → revalida sempre (para o desbloqueio aplicar ao reconectar)
    assert conta._precisa_revalidar({"ativo": False, "validado_em": _iso(0.1)}) is True


def test_status_usa_cache_sem_chamar_rede(monkeypatch):
    # Liga o controle de licença e injeta um cache saudável e recente.
    monkeypatch.setattr(conta, "PAINEL_URL", "http://painel.exemplo")
    monkeypatch.setattr(conta, "_load", lambda: {
        "ativo": True, "licenca_expira_em": None, "validado_em": _iso(1),
        "nome_loja": "Loja", "token": "t",
    })
    chamadas = []
    def _spy():
        chamadas.append(1)
        return None
    monkeypatch.setattr(conta, "revalidar", _spy)
    st = conta.status()
    assert st["bloqueado"] is False
    assert chamadas == []  # cache saudável e recente → não tocou na rede


def _vender(client, headers):
    produto = client.post('/api/produtos', json={
        'nome': 'Item licenca', 'preco_venda': 2, 'preco_custo': 1, 'estoque': 5,
        'codigo_barras': '',
    }, headers=headers)
    assert produto.status_code == 201, produto.text
    venda = client.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto.json()['produto']['id'], 'quantidade': 1}],
        'forma_pagamento': 'dinheiro',
    })
    return venda


def test_l01_modo_local_vende_sem_rede(client, auth, monkeypatch):
    import urllib.error
    monkeypatch.setattr(conta, 'PAINEL_URL', '')
    def rede(*_a, **_k):
        raise urllib.error.URLError('sem rede')
    monkeypatch.setattr(conta, '_http', rede)
    assert conta.status()['bloqueado'] is False
    venda = _vender(client, auth)
    assert venda.status_code == 201, venda.text


def test_l02_painel_fora_vende_na_carencia(client, auth, monkeypatch):
    import urllib.error
    monkeypatch.setattr(conta, 'PAINEL_URL', 'http://painel.exemplo')
    monkeypatch.setattr(conta, '_load', lambda: {
        'ativo': True, 'licenca_expira_em': None, 'validado_em': _iso(48),
        'nome_loja': 'Loja', 'token': 't', 'login': 'teste',
    })
    def rede(*_a, **_k):
        raise urllib.error.URLError('painel fora')
    monkeypatch.setattr(conta, '_http', rede)
    assert conta.status()['bloqueado'] is False
    login = client.post('/api/auth/login', json={'usuario': 'teste', 'senha': 'Loja@2026xy'})
    assert login.status_code == 200, login.text
    venda = _vender(client, {'Authorization': 'Bearer ' + login.json()['token']})
    assert venda.status_code == 201, venda.text
