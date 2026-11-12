"""Cópias locais só entram no histórico depois de validadas."""
import os
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier, Event
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
    parar = Event()

    def falhar(*args):
        parar.set()
        raise OSError('sentinela que não deve ir para o log')

    monkeypatch.setattr(backup, '_gerar_backup', falhar)
    backup._loop(parar)
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


def test_r06_backup_durante_checkouts_preserva_estoque_e_itens(armazenamento):
    local, _ = armazenamento
    agora = '2026-11-12T16:00:00+00:00'
    usuario = local.create_user('operador', 'Operador', 'fixture', agora)['id']
    produto = local.create_produto(usuario, 'Produto', 3, 4, 20, 0, '', 'UN', agora)
    inicio = Barrier(3, timeout=5)

    def vender():
        inicio.wait()
        for _ in range(5):
            local.checkout_atomico(usuario, None, 4, 0, 'dinheiro', '', [{
                'produto_id': produto['id'], 'nome_produto': produto['nome'],
                'quantidade': 1, 'preco_unitario': 4, 'subtotal': 4,
            }], agora)

    with ThreadPoolExecutor(max_workers=2) as pool:
        vendas = [pool.submit(vender) for _ in range(2)]
        inicio.wait()
        copia = backup._gerar_backup('auto')
        for tarefa in vendas:
            tarefa.result(timeout=5)

    with closing(sqlite3.connect(copia)) as conn:
        total = conn.execute('SELECT COUNT(*) FROM vendas').fetchone()[0]
        assert 0 <= total <= 10
        assert conn.execute('SELECT COUNT(*) FROM itens_venda').fetchone()[0] == total
        assert conn.execute('SELECT estoque FROM produtos').fetchone()[0] == 20 - total
        assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert local.get_produto(produto['id'])['estoque'] == 10


def test_backup_interrompido_nao_publica_copia_parcial(armazenamento, tmp_path):
    local, pasta = armazenamento
    bom = backup._gerar_backup('auto')
    antes = bom.read_bytes()
    marcador = tmp_path / 'copia-iniciada'
    programa = r'''
import sqlite3, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import backup
db = sqlite3.connect(backup.db.caminho_db())
db.execute('BEGIN IMMEDIATE')
db.execute("INSERT INTO users(email,nome,senha_hash,criado_em) VALUES ('fixture','Nome','hash','2026-11-12')")
def copia_interrompida(destino):
    destino.write_bytes(b'paginas parciais')
    Path(sys.argv[2]).touch()
    time.sleep(30)
backup.db.backup_para = copia_interrompida
backup._gerar_backup('auto')
'''
    ambiente = {**os.environ, 'VENDAFACIL_DATA_DIR': str(tmp_path)}
    ambiente.pop('PYTHONPATH', None)
    proc = subprocess.Popen([sys.executable, '-X', 'utf8', '-I', '-c', programa,
                             str(Path(__file__).resolve().parents[1]), str(marcador)],
                            env=ambiente)
    try:
        limite = time.monotonic() + 10
        while not marcador.exists() and proc.poll() is None and time.monotonic() < limite:
            time.sleep(0.025)
        assert marcador.exists()
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)
    assert list(pasta.glob('*.db')) == [bom]
    assert bom.read_bytes() == antes
    assert local._conn.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0
    assert local._conn.execute('PRAGMA journal_mode').fetchone()[0] == 'wal'
    database.verificar_integridade(Path(local.caminho_db()))
