"""Cópias locais só entram no histórico depois de validadas."""
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import backup
import database


@pytest.fixture
def armazenamento(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_DIR', tmp_path)
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'vendafacil.db')
    local = database.Database()
    pasta = tmp_path / 'backups'
    pasta.mkdir()
    monkeypatch.setattr(backup, 'db', local)
    monkeypatch.setattr(backup, 'BACKUP_DIR', pasta)
    try:
        yield local, pasta
    finally:
        local.close()


def test_r01_backup_publicado_tem_integridade(armazenamento):
    local, pasta = armazenamento
    local.create_user('operador', 'Operador', 'fixture', '2026-11-12')
    destino = backup._gerar_backup('auto')
    assert list(pasta.iterdir()) == [destino]
    with closing(sqlite3.connect(destino)) as copia:
        assert copia.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
        assert copia.execute('SELECT COUNT(*) FROM users').fetchone() == (1,)


def test_r01_backup_corrompido_nao_entra_no_historico(armazenamento, monkeypatch, caplog):
    local, pasta = armazenamento
    bom = backup._gerar_backup('auto')
    original = bom.read_bytes()

    def copia_corrompida(destino):
        assert list(pasta.glob('*.db')) == [bom]
        destino.write_bytes(b'fixture de copia interrompida')

    monkeypatch.setattr(local, 'backup_para', copia_corrompida)
    with pytest.raises(ValueError, match='integridade'):
        backup._gerar_backup('manual')

    assert list(pasta.iterdir()) == [bom]
    assert bom.read_bytes() == original
    assert 'integridade' in caplog.text


def test_r02_retem_automaticos_mais_recentes_e_preserva_manual(armazenamento, monkeypatch):
    _, pasta = armazenamento
    monkeypatch.setattr(backup, 'MANTER', 2)
    for i in range(4):
        arquivo = pasta / f'vendafacil-auto-{i}.db'
        arquivo.touch()
        os.utime(arquivo, (i + 1, i + 1))
    manual = pasta / 'vendafacil-manual.db'
    manual.touch()
    backup._limpar_antigos()
    assert sorted(p.name for p in pasta.glob('*.db')) == [
        'vendafacil-auto-2.db', 'vendafacil-auto-3.db', manual.name,
    ]


def test_r02_loop_registra_falha_sem_detalhe_sensivel(monkeypatch, caplog):
    def falhar(*args):
        raise OSError('sentinela que não deve ir para o log')

    def parar(*args):
        raise StopIteration

    monkeypatch.setattr(backup, '_gerar_backup', falhar)
    monkeypatch.setattr(backup, 'time', SimpleNamespace(sleep=parar))
    with pytest.raises(StopIteration):
        backup._loop()
    assert 'Backup automático falhou (OSError)' in caplog.text
    assert 'sentinela' not in caplog.text


def test_r02_nome_do_backup_usa_hora_local_e_microssegundos(monkeypatch):
    local = datetime(2026, 11, 12, 12, 15, 59, 241032, tzinfo=timezone(timedelta(hours=-4)))
    monkeypatch.setattr(backup, 'datetime', SimpleNamespace(now=lambda fuso=None: local.astimezone(fuso) if fuso else local))
    assert backup._stamp() == '20261112-121559-241032'


@pytest.mark.parametrize('tipo', ['corrompido', 'outro_aplicativo'])
def test_r04_restaura_apenas_banco_integro_do_vendafacil(armazenamento, tipo):
    local, pasta = armazenamento
    local.create_user('operador', 'Operador', 'fixture', '2026-11-12')
    caminho = pasta / 'arquivo.db'
    if tipo == 'corrompido':
        caminho.write_bytes(b'fixture corrompida')
    else:
        with closing(sqlite3.connect(caminho)) as outro:
            outro.execute('CREATE TABLE users (id INTEGER PRIMARY KEY)')

    with pytest.raises(ValueError):
        local.restaurar_de(caminho)

    assert local.get_user_by_usuario('operador')['nome'] == 'Operador'
    assert local._conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'


def test_r03_restauracao_em_banco_novo_preserva_contagens(armazenamento, tmp_path):
    local, _ = armazenamento
    agora = '2026-11-12T16:00:00+00:00'
    usuario = local.create_user('operador', 'Operador', 'fixture', agora)['id']
    cliente = local.create_cliente(usuario, 'Cliente', '', '', '', '', agora)
    produto = local.create_produto(usuario, 'Produto', 3, 4, 5, 0, '', 'UN', agora)
    venda = local.create_venda(usuario, cliente['id'], 4, 0, 'dinheiro', '', [{
        'produto_id': produto['id'], 'nome_produto': produto['nome'],
        'quantidade': 1, 'preco_unitario': 4, 'subtotal': 4,
    }], agora)
    local.criar_nota({'venda_id': venda['id'], 'user_id': usuario, 'ref': 'fixture',
                     'modelo': '65', 'numero': 1, 'serie': 1, 'ambiente': 'homologacao',
                     'status': 'pendente', 'criado_em': agora, 'atualizado_em': agora})
    copia = backup._gerar_backup('manual')
    conteudo = copia.read_bytes()
    tabelas = ('clientes', 'produtos', 'vendas', 'itens_venda', 'notas_fiscais')
    novo = database.Database(tmp_path / 'restaurado.db')
    try:
        novo.restaurar_de(copia)
        for tabela in tabelas:
            esperado = local._conn.execute(f'SELECT COUNT(*) FROM {tabela}').fetchone()[0]
            assert novo._conn.execute(f'SELECT COUNT(*) FROM {tabela}').fetchone()[0] == esperado == 1
        assert novo.get_user_by_usuario('operador')['nome'] == 'Operador'
        assert novo._conn.execute('PRAGMA journal_mode').fetchone()[0] == 'wal'
        assert novo._conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    finally:
        novo.close()
    assert copia.read_bytes() == conteudo
