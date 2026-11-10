"""F3.4: senha curta ou óbvia não entra; o token fica em 30 dias de propósito."""
import database
from fastapi.testclient import TestClient
from main import app
import auth
import conta


def test_senha_curta_ou_obvia_recusada(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_DIR', tmp_path)
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'vendafacil.db')
    local = database.Database()
    monkeypatch.setattr(auth, 'db', local)
    monkeypatch.setattr(conta, 'licenca_obrigatoria', lambda: False)
    monkeypatch.setattr(conta, 'status', lambda: {'bloqueado': False})
    api = TestClient(app, raise_server_exceptions=False)
    for senha in ('abcd', '12345678'):
        resposta = api.post('/api/auth/registro', json={
            'usuario': 'lojista', 'nome': 'Loja', 'senha': senha,
        })
        assert resposta.status_code == 400, resposta.text
    boa = api.post('/api/auth/registro', json={
        'usuario': 'lojista', 'nome': 'Loja', 'senha': 'mercearia-1',
    })
    assert boa.status_code == 200, boa.text
    assert auth.TOKEN_EXPIRE_HOURS == 720
    api.close()
    local.close()
