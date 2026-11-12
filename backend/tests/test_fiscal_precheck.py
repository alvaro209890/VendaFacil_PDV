"""Precheck não cria banco nem revela dados do cofre."""
import json
import runpy
import sqlite3
from pathlib import Path

precheck = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'scripts' / 'fiscal_precheck.py'))


def test_precheck_ausente_nao_cria_banco(tmp_path):
    caminho = tmp_path / 'nao-existe.db'
    resultado = precheck['avaliar_banco'](caminho)
    assert resultado['banco_presente'] is False
    assert resultado['apto_homologacao'] is False
    assert resultado['bloqueios'] == ['B1', 'B2', 'B3', 'B4', 'B5']
    assert not caminho.exists()


def test_precheck_cofre_invalido_somente_leitura_e_sem_segredo(tmp_path):
    caminho = tmp_path / 'cofre.db'
    sentinelas = ['PFX_INVALIDO_FIXTURE', 'SENHA_OPACA_FIXTURE', 'TOKEN_OPACO_FIXTURE', 'CSC_OPACO_FIXTURE']
    with sqlite3.connect(caminho) as conn:
        conn.executescript('''CREATE TABLE config_fiscal (id INTEGER, certificado_a1_b64 TEXT,
            certificado_senha TEXT, csc TEXT, ambiente TEXT);
            CREATE TABLE config_maquininha (id INTEGER, access_token TEXT);
            CREATE TABLE notas_fiscais (ambiente TEXT, status TEXT, protocolo TEXT, chave TEXT);''')
        conn.execute('INSERT INTO config_fiscal VALUES (1,?,?,?,?)',
                     (sentinelas[0], sentinelas[1], sentinelas[3], 'homologacao'))
        conn.execute('INSERT INTO config_maquininha VALUES (1,?)', (sentinelas[2],))
    antes = caminho.read_bytes()
    resultado = precheck['avaliar_banco'](caminho)
    assert resultado['banco_legivel'] is True
    assert resultado['certificado_presente'] is True
    assert resultado['certificado_valido'] is False
    assert resultado['apto_homologacao'] is False
    assert all(s not in json.dumps(resultado) for s in sentinelas)
    assert caminho.read_bytes() == antes
