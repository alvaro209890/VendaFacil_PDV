"""R05: servidor reinicia com o arquivo principal ilegível."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

import database
from auth import _hash_senha


@pytest.mark.parametrize('com_backup', [True, False])
def test_r05_sobe_em_consulta_e_bloqueia_vendas(tmp_path, com_backup):
    principal = tmp_path / 'vendafacil.db'
    pasta = tmp_path / 'backups'
    pasta.mkdir()
    copia = pasta / 'vendafacil-auto-bom.db'
    if com_backup:
        loja = database.Database(principal)
        try:
            agora = '2026-11-12T16:00:00+00:00'
            uid = loja.create_user('operador', 'Operador', _hash_senha('Fixture@2026'), agora)['id']
            loja.create_produto(uid, 'Produto recuperável', 3, 4, 5, 0, '', 'UN', agora)
            loja.backup_para(copia)
        finally:
            loja.close()
    corrompido = b'arquivo principal corrompido da fixture'
    principal.write_bytes(corrompido)
    (pasta / 'vendafacil-auto-ruim.db').write_bytes(b'copia mais nova corrompida')
    programa = r'''
import sys
sys.path.insert(0, sys.argv[1])
from fastapi.testclient import TestClient
from main import app
with TestClient(app) as api:
    assert api.get('/health').status_code == 200
    modo = api.get('/api/recuperacao').json()
    assert modo['somente_consulta'] is True
    login = api.post('/api/auth/login', json={'usuario': 'operador', 'senha': 'Fixture@2026'})
    if sys.argv[2] == 'True':
        assert modo['ultimo_backup'].endswith('vendafacil-auto-bom.db')
        assert login.status_code == 200
        auth = {'Authorization': 'Bearer ' + login.json()['token']}
        produtos = api.get('/api/produtos', headers=auth)
        assert produtos.status_code == 200
        assert 'Produto recuperável' in produtos.text
        assert api.get('/api/backup/exportar', headers=auth).status_code == 503
        assert api.post('/api/vendas/checkout', headers=auth, json={}).status_code == 503
    else:
        assert modo['ultimo_backup'] is None
        assert login.status_code == 503
'''
    ambiente = {**os.environ, 'VENDAFACIL_DATA_DIR': str(tmp_path)}
    ambiente.pop('PYTHONPATH', None)
    resultado = subprocess.run([sys.executable, '-X', 'utf8', '-I', '-c', programa,
                                str(Path(__file__).resolve().parents[1]), str(com_backup)],
                               env=ambiente, capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert resultado.returncode == 0, resultado.stderr
    assert principal.read_bytes() == corrompido
