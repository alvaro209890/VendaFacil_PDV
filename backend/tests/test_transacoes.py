"""P7/P1: persistência, integridade e fronteiras de transação."""
import sqlite3
import pytest
import database
from auth import _agora


@pytest.fixture
def loja(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_DIR', tmp_path)
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'vendafacil.db')
    local = database.Database()
    agora = _agora()
    user = local.create_user('transacao', 'Transação', 'hash_de_fixture', agora)
    yield local, user['id'], agora
    local.close()


def test_p7_pragmas_iniciais_e_reconexao(loja):
    local, _, _ = loja
    for _ in range(2):
        assert local._conn.execute('PRAGMA foreign_keys').fetchone()[0] == 1
        assert local._conn.execute('PRAGMA busy_timeout').fetchone()[0] == 5000
        assert local._conn.execute('PRAGMA synchronous').fetchone()[0] == 2
        assert local._conn.execute('PRAGMA journal_mode').fetchone()[0] == 'wal'
        local.close()
        local.reconectar()


def test_p7_referencia_inexistente_recusada(loja):
    local, user, agora = loja
    with pytest.raises(sqlite3.IntegrityError):
        local.create_venda(user, 999999, 1, 0, 'dinheiro', '', [], agora)
    assert not local.list_vendas(user)


def test_p7_abre_copia_legada_sem_perder_dados(loja, tmp_path, monkeypatch):
    local, user, agora = loja
    local._conn.execute('PRAGMA foreign_keys = OFF')
    produto = local.create_produto(user, 'Legado', 1, 2, 5, 0, '', 'UN', agora)
    local.create_venda(user, None, 2, 0, 'dinheiro', '', [{
        'produto_id': produto['id'], 'nome_produto': 'Legado',
        'quantidade': 1, 'preco_unitario': 2, 'subtotal': 2,
    }], agora)
    tabelas = ('users', 'produtos', 'vendas', 'itens_venda')
    contagens = lambda conn: {t: conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in tabelas}
    antes = contagens(local._conn)
    copia = tmp_path / 'legado.db'
    local.backup_para(copia)
    monkeypatch.setattr(database, 'DB_PATH', copia)
    outra = database.Database()
    try:
        assert contagens(outra._conn) == antes
        assert outra._conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert list(outra._conn.execute('PRAGMA foreign_key_check')) == []
        assert outra._conn.execute('PRAGMA foreign_keys').fetchone()[0] == 1
    finally:
        outra.close()


@pytest.fixture
def checkout_local(loja, monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    from auth import _gerar_jwt, _token_user
    import vendas
    local, user, agora = loja
    monkeypatch.setattr(vendas, 'db', local)
    produto = local.create_produto(user, 'Transação', 1, 2, 5, 0, '', 'UN', agora)
    cliente = local.create_cliente(user, 'Cliente', '', '', '', '', agora)
    usuario = local.get_user_by_usuario('transacao')
    headers = {'Authorization': 'Bearer ' + _gerar_jwt(_token_user(usuario))}
    api = TestClient(app, raise_server_exceptions=False)
    yield api, local, user, produto, cliente, headers
    api.close()


@pytest.mark.parametrize('tabela', ['vendas', 'movimentacoes_estoque', 'contas_receber'])
def test_v01_v03_checkout_rollback_em_qualquer_etapa(checkout_local, tabela):
    api, local, user, produto, cliente, headers = checkout_local
    with local._conn:
        local._conn.execute(f"CREATE TRIGGER falha BEFORE INSERT ON {tabela} BEGIN SELECT RAISE(ABORT, 'falha_injetada'); END")
    resposta = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
        'forma_pagamento': 'fiado', 'cliente_id': cliente['id'],
    })
    assert resposta.status_code == 500
    assert local.get_produto(produto['id'])['estoque'] == 5
    assert not local.list_vendas(user)
    assert not local.list_contas_receber(user)
    assert local._conn.execute('SELECT COUNT(*) FROM movimentacoes_estoque').fetchone()[0] == 0
