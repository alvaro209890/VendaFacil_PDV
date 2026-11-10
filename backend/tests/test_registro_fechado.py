"""S02: o primeiro registro é aberto; o seguinte exige quem já entrou."""
import pytest
import database
from fastapi.testclient import TestClient
from main import app
import auth
import conta


@pytest.fixture
def loja_s02(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_DIR', tmp_path)
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'vendafacil.db')
    local = database.Database()
    monkeypatch.setattr(auth, 'db', local)
    monkeypatch.setattr(conta, 'licenca_obrigatoria', lambda: False)
    monkeypatch.setattr(conta, 'status', lambda: {'bloqueado': False})
    api = TestClient(app, raise_server_exceptions=False)
    yield api
    api.close()
    local.close()


def test_s02_registro_fecha_depois_do_primeiro(loja_s02):
    api = loja_s02
    primeiro = api.post('/api/auth/registro', json={
        'usuario': 'lojista', 'nome': 'Loja', 'senha': 'senha-forte',
    })
    assert primeiro.status_code == 200, primeiro.text
    aberto = api.post('/api/auth/registro', json={
        'usuario': 'caixa', 'nome': 'Caixa', 'senha': 'outra-forte',
    })
    assert aberto.status_code == 401, aberto.text
    token = primeiro.json()['token']
    fechado = api.post('/api/auth/registro', headers={'Authorization': f'Bearer {token}'}, json={
        'usuario': 'caixa', 'nome': 'Caixa', 'senha': 'outra-forte',
    })
    assert fechado.status_code == 200, fechado.text
