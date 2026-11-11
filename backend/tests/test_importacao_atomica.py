"""I06: importação inteira atômica, inclusive chave e movimentos."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
import database
import produtos
from auth import _gerar_jwt, _token_user
from fastapi.testclient import TestClient
from main import app
from test_transacoes import loja

CHAVE = '35200114200166000187550010000000011123456780'


@pytest.fixture
def entrada(loja, monkeypatch):
    local, user, agora = loja
    produto = local.create_produto(user, 'Existente', 1, 2, 5, 0, 'EAN-EXISTENTE', 'UN', agora)
    monkeypatch.setattr(produtos, 'db', local)
    headers = {'Authorization': 'Bearer ' + _gerar_jwt(_token_user(local.get_user_by_usuario('transacao')))}
    corpo = {'chave': CHAVE, 'documento': 'NF-e fixture', 'itens': [
        {'produto_id': produto['id'], 'nome': 'Existente', 'quantidade': 2, 'preco_custo': 3},
        {'nome': 'Novo', 'codigo_barras': 'EAN-NOVO', 'quantidade': 4,
         'preco_custo': 2, 'preco_venda': 5, 'ncm': '10063021', 'cfop': '5102'},
    ]}
    api = TestClient(app, raise_server_exceptions=False)
    yield api, local, user, produto, headers, corpo
    api.close()


@pytest.mark.parametrize('tabela,evento', [
    ('produtos', 'UPDATE'), ('produtos', 'INSERT'),
    ('movimentacoes_estoque', 'INSERT'), ('notas_entrada', 'INSERT'),
])
@pytest.mark.parametrize('falha', ['ABORT', 'IGNORE'])
def test_i06_falha_desfaz_toda_entrada(entrada, tabela, evento, falha):
    api, local, user, produto, headers, corpo = entrada
    sinal = "ABORT, 'falha_fixture'" if falha == 'ABORT' else "IGNORE"
    with local._conn:
        local._conn.execute(f'CREATE TRIGGER falha BEFORE {evento} ON {tabela} BEGIN SELECT RAISE({sinal}); END')
    resposta = api.post('/api/produtos/importar-xml/confirmar', headers=headers, json=corpo)
    assert resposta.status_code == 500
    assert local.get_produto(produto['id'], user)['estoque'] == 5
    assert local.get_produto(produto['id'], user)['preco_custo'] == 1
    assert len(local.list_produtos(user)) == 1
    assert local._conn.execute('SELECT COUNT(*) FROM movimentacoes_estoque').fetchone()[0] == 0
    assert not local.nota_entrada_importada(user, CHAVE)
    with local._conn:
        local._conn.execute('DROP TRIGGER falha')
    repetida = api.post('/api/produtos/importar-xml/confirmar', headers=headers, json=corpo)
    assert repetida.status_code == 200
    assert local.get_produto(produto['id'], user)['estoque'] == 7
    assert local.nota_entrada_importada(user, CHAVE)


def test_i06_referencia_invalida_nao_importa_primeiro_item(entrada):
    api, local, user, produto, headers, corpo = entrada
    corpo['itens'][1]['produto_id'] = 999999
    resposta = api.post('/api/produtos/importar-xml/confirmar', headers=headers, json=corpo)
    assert resposta.status_code == 400
    assert local.get_produto(produto['id'], user)['estoque'] == 5
    assert not local.nota_entrada_importada(user, CHAVE)


def test_i06_duas_conexoes_mesma_chave_uma_entrada(entrada):
    _, local, user, produto, _, corpo = entrada
    segunda = database.Database()
    barreira = Barrier(2)
    itens = [produtos.ItemImportar(**it).model_dump() for it in corpo['itens']]

    def confirmar(banco):
        barreira.wait(timeout=5)
        try:
            banco.importar_entrada_atomica(user, CHAVE, 'fixture concorrente', itens, '2026-11-11T10:00:00Z')
            return 'aceita'
        except database.NotaEntradaDuplicada:
            return 'duplicada'

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futuros = [pool.submit(confirmar, banco) for banco in (local, segunda)]
            resultados = [f.result(timeout=10) for f in futuros]
        assert sorted(resultados) == ['aceita', 'duplicada']
        assert local.get_produto(produto['id'], user)['estoque'] == 7
        assert len(local.list_produtos(user)) == 2
        assert local._conn.execute('SELECT COUNT(*) FROM notas_entrada').fetchone()[0] == 1
        assert local._conn.execute('SELECT COUNT(*) FROM movimentacoes_estoque').fetchone()[0] == 2
        novo = next(p for p in local.list_produtos(user) if p['nome'] == 'Novo')
        assert novo['ncm'] == '10063021'
        assert novo['cfop'] == '5102'
        assert local._conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    finally:
        segunda.close()


@pytest.mark.parametrize('campo', ['quantidade', 'preco_custo', 'preco_venda', 'quantidade_por_embalagem'])
def test_i06_recusa_infinito_antes_de_gravar(entrada, campo):
    import json
    api, local, user, produto, headers, corpo = entrada
    corpo['itens'][0][campo] = float('inf')
    resposta = api.post('/api/produtos/importar-xml/confirmar',
                       headers={**headers, 'Content-Type': 'application/json'}, content=json.dumps(corpo))
    assert resposta.status_code == 422
    assert local.get_produto(produto['id'], user)['estoque'] == 5
    assert not local.nota_entrada_importada(user, CHAVE)


def test_i06_lote_vazio_nao_reserva_chave(entrada):
    api, local, user, _, headers, corpo = entrada
    corpo['itens'] = []
    resposta = api.post('/api/produtos/importar-xml/confirmar', headers=headers, json=corpo)
    assert resposta.status_code == 422
    assert not local.nota_entrada_importada(user, CHAVE)


def test_i06_produto_alheio_nao_altera_nenhum_estoque(entrada):
    api, local, user, produto, headers, corpo = entrada
    outro = local.create_user('outro', 'Outra loja', 'hash_fixture', '2026-11-11T10:00:00Z')
    alheio = local.create_produto(outro['id'], 'Alheio', 1, 2, 9, 0, '', 'UN', '2026-11-11T10:00:00Z')
    corpo['itens'][1]['produto_id'] = alheio['id']
    resposta = api.post('/api/produtos/importar-xml/confirmar', headers=headers, json=corpo)
    assert resposta.status_code == 400
    assert local.get_produto(produto['id'], user)['estoque'] == 5
    assert local.get_produto(alheio['id'], outro['id'])['estoque'] == 9
    assert not local.nota_entrada_importada(user, CHAVE)
