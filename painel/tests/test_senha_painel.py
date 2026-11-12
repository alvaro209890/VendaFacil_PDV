"""S13: política de senha aplicada em criação e troca, inclusive contas."""
import pytest
from fastapi.testclient import TestClient
import database
import main


@pytest.fixture
def isolado(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'senhas.db')
    local = database.Database()
    monkeypatch.setattr(main, 'db', local)
    with TestClient(main.app) as client:
        yield client
    local._conn.close()


@pytest.mark.parametrize('senha', ['abc123', '12345678', 'admin123', '        '])
def test_s13_setup_recusa_senha_fraca(isolado, senha):
    r = isolado.post('/api/admin/setup', json={'login': 'admin', 'nome': 'Admin', 'senha': senha})
    assert r.status_code == 422
    assert isolado.get('/api/admin/precisa-setup').json()['precisa_setup']


@pytest.mark.parametrize('senha', ['abc123', '12345678', 'admin123', '        '])
def test_s13_trocas_e_contas_recusam_senha_fraca(isolado, senha):
    setup = isolado.post('/api/admin/setup', json={
        'login': 'admin', 'nome': 'Admin', 'senha': 'Loja@2026xy'})
    assert setup.status_code == 200
    headers = {'Authorization': 'Bearer ' + setup.json()['token']}
    conta = isolado.post('/api/admin/contas', headers=headers, json={
        'login': 'loja', 'nome_loja': 'Loja', 'senha': 'Loja@2026xy'})
    assert conta.status_code == 200
    cid = conta.json()['conta']['id']
    respostas = [
        isolado.put('/api/admin/senha', headers=headers, json={
            'senha_atual': 'Loja@2026xy', 'nova_senha': senha}),
        isolado.post('/api/admin/contas', headers=headers, json={
            'login': 'nova', 'nome_loja': 'Nova', 'senha': senha}),
        isolado.put(f'/api/admin/contas/{cid}', headers=headers, json={'nova_senha': senha}),
    ]
    assert [r.status_code for r in respostas] == [422, 422, 422]
