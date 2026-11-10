"""S01: senhas erradas seguidas esperam, e a senha certa entra depois da espera."""
import pytest
import database
from fastapi.testclient import TestClient
from auth import _agora, _hash_senha
from main import app
import auth
import conta


@pytest.fixture
def loja_s01(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_DIR', tmp_path)
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'vendafacil.db')
    local = database.Database()
    agora = _agora()
    local.create_user('lojista', 'Loja', _hash_senha('senha-certa'), agora)
    monkeypatch.setattr(auth, 'db', local)
    monkeypatch.setattr(conta, 'licenca_obrigatoria', lambda: False)
    auth._falhas_login.clear()
    relogio = {'t': 1_000.0}
    monkeypatch.setattr(auth, '_relogio', lambda: relogio['t'], raising=False)
    api = TestClient(app, raise_server_exceptions=False)
    yield api, relogio
    api.close()
    local.close()


def test_s01_espera_crescente_nao_trava_para_sempre(loja_s01):
    api, relogio = loja_s01
    for _ in range(5):
        errada = api.post('/api/auth/login', json={'usuario': 'lojista', 'senha': 'errada'})
        assert errada.status_code == 401, errada.text
    bloqueio = api.post('/api/auth/login', json={'usuario': 'lojista', 'senha': 'senha-certa'})
    assert bloqueio.status_code == 429, bloqueio.text
    relogio['t'] += 31
    certa = api.post('/api/auth/login', json={'usuario': 'lojista', 'senha': 'senha-certa'})
    assert certa.status_code == 200, certa.text
    assert 'token' in certa.json()
