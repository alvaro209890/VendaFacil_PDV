"""F2.3: limites do caixa, sem dados reais."""
import pytest
from fastapi.testclient import TestClient
from auth import _agora, _gerar_jwt, _token_user
from main import app
import caixa
from test_transacoes import checkout_local, loja


@pytest.fixture
def caixa_api(checkout_local, monkeypatch):
    api, local, user, produto, _, _ = checkout_local
    monkeypatch.setattr(caixa, 'db', local)
    headers = {'Authorization': 'Bearer ' + _gerar_jwt(_token_user(local.get_user_by_usuario('transacao')))}
    cliente = TestClient(app, raise_server_exceptions=False)
    yield cliente, local, user, produto, headers
    cliente.close()


def test_c08_segundo_caixa_recusado(caixa_api):
    api, _, _, _, headers = caixa_api
    assert api.post('/api/caixa/abrir', headers=headers, json={'valor_abertura': 10}).status_code == 200
    outro = api.post('/api/caixa/abrir', headers=headers, json={'valor_abertura': 5})
    assert outro.status_code == 409
    assert api.get('/api/caixa/atual', headers=headers).json()['sessao']['valor_abertura'] == 10


@pytest.mark.parametrize('tipo', ['sangria', 'suprimento'])
@pytest.mark.parametrize('valor', [0, -1])
def test_c05_movimento_nao_positivo_400(caixa_api, tipo, valor):
    api, local, user, _, headers = caixa_api
    api.post('/api/caixa/abrir', headers=headers, json={'valor_abertura': 10})
    resposta = api.post('/api/caixa/movimento', headers=headers, json={'tipo': tipo, 'valor': valor})
    assert resposta.status_code == 400
    assert local.resumo_caixa(local.get_caixa_aberto(user))['sangrias'] == 0
    assert local.resumo_caixa(local.get_caixa_aberto(user))['suprimentos'] == 0


def test_sangria_acima_da_gaveta_recusada(caixa_api):
    api, local, user, _, headers = caixa_api
    api.post('/api/caixa/abrir', headers=headers, json={'valor_abertura': 10})
    resposta = api.post('/api/caixa/movimento', headers=headers, json={
        'tipo': 'sangria', 'valor': 10.01, 'motivo': 'acima da gaveta',
    })
    assert resposta.status_code == 409
    assert 'gaveta' in resposta.text.lower() or 'caixa' in resposta.text.lower()
    assert local.resumo_caixa(local.get_caixa_aberto(user))['dinheiro_esperado'] == 10
