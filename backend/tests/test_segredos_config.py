"""S05/S06: configuração não devolve segredo e o log não grava o valor."""
import database
from fastapi.testclient import TestClient
from auth import _agora, _gerar_jwt
from errors import LOG_FILE
from main import app
import fiscal_config
import mercadopago

SEGREDOS = {
    'csc': 'CSC-SECRETO-7781',
    'certificado_senha': 'SENHA-CERT-7781',
    'certificado_a1_b64': 'PFX-BYTES-7781',
    'gateway_token': 'TOKEN-GATEWAY-7781',
    'access_token': 'TOKEN-MP-7781',
}


def _headers():
    token = _gerar_jwt({
        'sub': '1', 'usuario': 'loja', 'email': 'loja', 'nome': 'Loja',
        'iat': 1, 'exp': 9_999_999_999,
    })
    return {'Authorization': 'Bearer ' + token}


def test_s05_leitura_nao_devolve_segredo(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_DIR', tmp_path)
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'vendafacil.db')
    local = database.Database()
    monkeypatch.setattr(fiscal_config, 'db', local)
    monkeypatch.setattr(mercadopago, 'db', local)
    api = TestClient(app, raise_server_exceptions=False)
    headers = _headers()
    fiscal = api.put('/api/fiscal/config', headers=headers, json={
        'csc': SEGREDOS['csc'],
        'certificado_senha': SEGREDOS['certificado_senha'],
        'certificado_a1_b64': SEGREDOS['certificado_a1_b64'],
        'gateway_token': SEGREDOS['gateway_token'],
    })
    assert fiscal.status_code == 200, fiscal.text
    maq = api.put('/api/maquininha/config', headers=headers, json={'access_token': SEGREDOS['access_token']})
    assert maq.status_code == 200, maq.text
    for resposta in (
        api.get('/api/fiscal/config', headers=headers),
        api.get('/api/maquininha/config', headers=headers),
        fiscal,
        maq,
    ):
        texto = resposta.text
        for segredo in SEGREDOS.values():
            assert segredo not in texto
    api.close()
    local.close()


def test_s06_log_nao_grava_segredo():
    api = TestClient(app, raise_server_exceptions=False)
    resposta = api.put('/api/fiscal/config', headers=_headers(), json={
        'serie': 'nao-numero',
        'csc': SEGREDOS['csc'],
        'certificado_senha': SEGREDOS['certificado_senha'],
        'certificado_a1_b64': SEGREDOS['certificado_a1_b64'],
        'gateway_token': SEGREDOS['gateway_token'],
    })
    assert resposta.status_code == 422, resposta.text
    log = LOG_FILE.read_text(encoding='utf-8', errors='replace') if LOG_FILE.exists() else ''
    for segredo in SEGREDOS.values():
        assert segredo not in log
    api.close()
