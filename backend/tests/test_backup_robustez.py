"""Cópias locais só entram no histórico depois de validadas."""
import sqlite3
from contextlib import closing

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
