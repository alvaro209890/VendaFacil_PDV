"""S13: troca de credencial invalida todas as sessões anteriores."""
import pytest
from fastapi.testclient import TestClient
import database
import main
import security


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'tokens.db')
    local = database.Database()
    monkeypatch.setattr(main, 'db', local)
    with TestClient(main.app) as client:
        yield client, local
    local._conn.close()


def cabecalho(resposta):
    assert resposta.status_code == 200
    return {'Authorization': 'Bearer ' + resposta.json()['token']}


def test_s13_troca_admin_revoga_todas_sessoes(api):
    client, _ = api
    login = {'login': 'admin', 'senha': 'Loja@2026xy'}
    a = cabecalho(client.post('/api/admin/setup', json={**login, 'nome': 'Admin'}))
    b = cabecalho(client.post('/api/admin/login', json=login))
    assert client.put('/api/admin/senha', headers=a, json={
        'senha_atual': login['senha'], 'nova_senha': 'Nova@2026xy'}).status_code == 200
    assert [client.get('/api/admin/contas', headers=h).status_code for h in (a, b)] == [401, 401]
    novo = cabecalho(client.post('/api/admin/login', json={'login': 'admin', 'senha': 'Nova@2026xy'}))
    assert client.get('/api/admin/contas', headers=novo).status_code == 200
    assert client.post('/api/admin/login', json=login).status_code == 401


def test_s13_troca_conta_revoga_sync_e_validacao(api):
    client, _ = api
    admin = cabecalho(client.post('/api/admin/setup', json={
        'login': 'admin', 'nome': 'Admin', 'senha': 'Loja@2026xy'}))
    r = client.post('/api/admin/contas', headers=admin, json={
        'login': 'loja', 'nome_loja': 'Loja', 'senha': 'Loja@2026xy'})
    assert r.status_code == 200
    cid = r.json()['conta']['id']
    antigo = cabecalho(client.post('/api/conta/validar', json={'login': 'loja', 'senha': 'Loja@2026xy'}))
    assert client.put(f'/api/admin/contas/{cid}', headers=admin,
                      json={'nova_senha': 'Nova@2026xy'}).status_code == 200
    assert client.post('/api/sync/vendas', headers=antigo, json={'vendas': []}).status_code == 401
    novo = cabecalho(client.post('/api/conta/validar', json={'login': 'loja', 'senha': 'Nova@2026xy'}))
    assert client.post('/api/sync/vendas', headers=novo, json={'vendas': []}).status_code == 200


def test_s13_conta_excluida_nao_usa_token(api):
    client, _ = api
    admin = cabecalho(client.post('/api/admin/setup', json={
        'login': 'admin', 'nome': 'Admin', 'senha': 'Loja@2026xy'}))
    r = client.post('/api/admin/contas', headers=admin, json={
        'login': 'loja', 'nome_loja': 'Loja', 'senha': 'Loja@2026xy'})
    assert r.status_code == 200
    token = cabecalho(client.post('/api/conta/validar', json={'login': 'loja', 'senha': 'Loja@2026xy'}))
    assert client.delete(f"/api/admin/contas/{r.json()['conta']['id']}", headers=admin).status_code == 200
    assert client.post('/api/sync/vendas', headers=token, json={'vendas': []}).status_code == 401


def test_s13_token_legado_exige_novo_login(api):
    client, local = api
    conta = local.create_admin('legado', 'Legado', security.hash_senha('1234'))
    # A credencial antiga ainda permite login; token sem versão não dá acesso.
    login = client.post('/api/admin/login', json={'login': 'legado', 'senha': '1234'})
    atual = cabecalho(login)
    assert client.get('/api/admin/contas', headers=atual).status_code == 200
    antigo = security.gerar_jwt({'sub': str(conta['id']), 'tipo': 'admin'})
    resposta = client.get('/api/admin/contas', headers={'Authorization': 'Bearer ' + antigo})
    assert resposta.status_code == 401


def test_s13_migracao_concorrente_preserva_credenciais(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'legado.db')
    legado = database.Database()
    legado.create_admin('legado', 'Legado', 'hash_fixture')
    with legado._conn:
        legado._conn.execute('ALTER TABLE admins DROP COLUMN token_version')
        legado._conn.execute('ALTER TABLE contas DROP COLUMN token_version')
    legado._conn.close()
    barreira = Barrier(2)
    def abrir(_):
        barreira.wait(timeout=5)
        local = database.Database()
        try:
            row = local.get_admin_by_login('legado')
            return row['token_version'], row['senha_hash']
        finally:
            local._conn.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(abrir, range(2))) == [(0, 'hash_fixture')] * 2
