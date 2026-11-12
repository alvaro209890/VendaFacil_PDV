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
    produto = local.create_produto(
        user, 'Transação', 1, 2, 5, 0, '', 'UN', agora,
        fiscais={'ncm': '22021000', 'cfop': '5102', 'cst_csosn': '102'},
    )
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


@pytest.mark.parametrize('quantidade', [0, -1])
def test_v12_quantidade_invalida_retorna_400(checkout_local, quantidade):
    api, local, user, produto, _, headers = checkout_local
    resposta = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': quantidade}],
    })
    assert resposta.status_code == 400
    assert local.get_produto(produto['id'])['estoque'] == 5
    assert not local.list_vendas(user)


@pytest.mark.parametrize('campo', ['quantidade', 'desconto'])
def test_v16_infinito_recusado_sem_erro_500(checkout_local, campo):
    import json
    api, local, user, produto, _, headers = checkout_local
    corpo = {'itens': [{'produto_id': produto['id'], 'quantidade': 1}], 'desconto': 0}
    if campo == 'quantidade':
        corpo['itens'][0]['quantidade'] = float('inf')
    else:
        corpo['desconto'] = float('inf')
    resposta = api.post('/api/vendas/checkout', headers={**headers, 'Content-Type': 'application/json'}, content=json.dumps(corpo))
    assert resposta.status_code == 422
    assert local.get_produto(produto['id'])['estoque'] == 5
    assert not local.list_vendas(user)


@pytest.mark.parametrize('tipo', ['inativo', 'inexistente'])
def test_v12_produto_invalido_400(checkout_local, tipo):
    api, local, user, produto, _, headers = checkout_local
    pid = produto['id']
    if tipo == 'inativo':
        local.update_produto(pid, user, ativo=0)
    else:
        pid = 999999
    resposta = api.post('/api/vendas/checkout', headers=headers, json={'itens': [{'produto_id': pid, 'quantidade': 1}]})
    assert resposta.status_code == 400
    assert not local.list_vendas(user)


def test_v05_fracionado_e_itens_duplicados_nao_negativam(checkout_local):
    api, local, user, produto, _, headers = checkout_local
    local.update_produto(produto['id'], user, estoque=.3)
    invalida = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': .2}] * 2,
    })
    assert invalida.status_code == 409
    assert local.get_produto(produto['id'])['estoque'] == .3
    for quantidade in [.1, .2]:
        resposta = api.post('/api/vendas/checkout', headers=headers, json={
            'itens': [{'produto_id': produto['id'], 'quantidade': quantidade}],
        })
        assert resposta.status_code == 201, resposta.text
    assert local.get_produto(produto['id'])['estoque'] == 0


def test_v04_api_concorrente_ultimo_item(checkout_local):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    api, local, user, produto, _, headers = checkout_local
    for _ in range(5):
        local.update_produto(produto['id'], user, estoque=1)
        antes = len(local.list_vendas(user))
        barreira = Barrier(2)
        def vender():
            barreira.wait(timeout=10)
            return api.post('/api/vendas/checkout', headers=headers, json={
                'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
            }).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            respostas = list(pool.map(lambda _: vender(), range(2)))
        assert sorted(respostas) in ([201, 400], [201, 409])
        assert local.get_produto(produto['id'])['estoque'] == 0
        assert len(local.list_vendas(user)) == antes + 1


def test_v04_duas_conexoes_begin_immediate(checkout_local):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    _, local, user, produto, _, _ = checkout_local
    local.update_produto(produto['id'], user, estoque=1)
    outra = database.Database()
    barreira = Barrier(2)
    def vender(conn):
        barreira.wait(timeout=10)
        try:
            conn.checkout_atomico(user, None, 2, 0, 'dinheiro', '', [{
                'produto_id': produto['id'], 'nome_produto': produto['nome'],
                'quantidade': 1, 'preco_unitario': 2, 'subtotal': 2,
            }], _agora())
            return True
        except database.EstoqueConcorrente:
            return False
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            respostas = list(pool.map(vender, [local, outra]))
        assert sorted(respostas) == [False, True]
        assert local.get_produto(produto['id'])['estoque'] == 0
        assert len(local.list_vendas(user)) == 1
    finally:
        outra.close()


def test_v13_venda_nao_visivel_a_outro_usuario(checkout_local):
    from auth import _gerar_jwt, _token_user
    api, local, user, produto, _, headers = checkout_local
    venda = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
    }).json()['venda']
    outro = local.create_user('outro', 'Outro', 'hash_de_fixture', _agora())
    alheio = {'Authorization': 'Bearer ' + _gerar_jwt(_token_user(outro))}
    assert api.get(f"/api/vendas/{venda['id']}", headers=alheio).status_code == 404
    assert api.get('/api/vendas', headers=alheio).json()['vendas'] == []


def test_v06_processo_morto_no_meio_do_checkout(checkout_local, tmp_path):
    import os
    from pathlib import Path
    import queue
    import subprocess
    import sys
    import threading
    _, local, _, produto, _, _ = checkout_local
    raiz = Path(__file__).resolve().parents[2]
    origem_legada = ''
    if os.environ.get('VENDAFACIL_TEST_CHECKOUT_LEGADO') == '1':
        # Controle RED executa a rota real anterior à correção, extraída do git.
        pasta = tmp_path / 'rota_legada'
        pasta.mkdir()
        codigo = subprocess.check_output(['git', 'show', 'a4f8e69:backend/vendas.py'], cwd=raiz)
        (pasta / 'vendas.py').write_bytes(codigo)
        origem_legada = str(pasta)
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env['VENDAFACIL_DATA_DIR'] = str(tmp_path)
    env['VENDAFACIL_PAINEL_URL'] = ''
    proc = subprocess.Popen([
        sys.executable, '-I', '-u', str(Path(__file__).with_name('checkout_queda_worker.py')),
        str(tmp_path), str(produto['id']), origem_legada,
    ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
       text=True, env=env, cwd=raiz)
    linhas = queue.Queue()
    def ler_saida():
        for linha in proc.stdout:
            linhas.put(linha)
        linhas.put(None)
    leitor = threading.Thread(target=ler_saida, daemon=True)
    leitor.start()
    try:
        while True:
            linha = linhas.get(timeout=20)
            assert linha is not None, 'Worker encerrou antes do ponto de corte.'
            if 'PONTO_DE_CORTE_SQL' in linha:
                break
        proc.kill()
        proc.wait(timeout=10)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=10)
        leitor.join(timeout=5)
        for pipe in (proc.stdin, proc.stdout):
            pipe.close()
    assert local.get_produto(produto['id'])['estoque'] == 5
    for tabela in ('vendas', 'itens_venda', 'movimentacoes_estoque', 'contas_receber'):
        assert local._conn.execute(f'SELECT COUNT(*) FROM {tabela}').fetchone()[0] == 0
    assert local._conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert list(local._conn.execute('PRAGMA foreign_key_check')) == []
