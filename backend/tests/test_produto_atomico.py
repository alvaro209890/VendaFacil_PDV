"""I07: cadastro do produto e dos campos fiscais cabe numa transação."""
import pytest
import database
from fastapi.testclient import TestClient
from auth import _agora, _gerar_jwt, _token_user
from main import app
import produtos


@pytest.fixture
def loja_i07(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_DIR', tmp_path)
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'vendafacil.db')
    local = database.Database()
    agora = _agora()
    user = local.create_user('transacao', 'Transação', 'hash_de_fixture', agora)
    monkeypatch.setattr(produtos, 'db', local)
    headers = {'Authorization': 'Bearer ' + _gerar_jwt(_token_user(local.get_user_by_usuario('transacao')))}
    api = TestClient(app, raise_server_exceptions=False)
    writes = []
    class Conexao:
        def __init__(self, inner):
            self._inner = inner
        def execute(self, sql, params=()):
            texto = sql if isinstance(sql, str) else ''
            cabeca = texto.lstrip().upper()
            if 'PRODUTOS' in cabeca and cabeca.startswith(('INSERT', 'UPDATE')):
                writes.append(cabeca.split()[0])
            return self._inner.execute(sql, params)
        def __enter__(self):
            return self._inner.__enter__()
        def __exit__(self, *args):
            return self._inner.__exit__(*args)
        def __getattr__(self, name):
            return getattr(self._inner, name)
    local._conn = Conexao(local._conn)
    yield api, local, user['id'], headers, writes
    api.close()
    local.close()


def test_i07_produto_e_fiscal_na_mesma_transacao(loja_i07):
    api, local, user, headers, writes = loja_i07
    resposta = api.post('/api/produtos', headers=headers, json={
        'nome': 'Cerveja', 'preco_venda': 5, 'preco_custo': 3, 'ncm': '22030000',
    })
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()['produto']['ncm'] == '22030000'
    assert writes == ['INSERT']
    assert local.list_produtos(user)[0]['ncm'] == '22030000'
