"""F5.9: um encerramento abrupto durante SOAP permite conciliar a reserva."""
import os
import subprocess
import sys
import time
from pathlib import Path

import fiscal
import requests
from urllib3.exceptions import MaxRetryError, NewConnectionError, ProtocolError, ProxyError
from sefaz_fake import retorno_consulta
from test_sefaz_simulador import fiscal_store, client, auth, simulador, emissor, loja, _vender, _emitir


def test_transmissao_interrompida_persiste_xml_antes_da_rede(loja, simulador, fiscal_store, tmp_path):
    venda = _vender(loja)
    banco = Path(fiscal_store['db'].caminho_db())
    entrou = tmp_path / 'entrou-no-soap'
    programa = r'''
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import database
import fiscal
import fiscal_direto
local = database.Database(Path(sys.argv[2]))
fiscal.db = fiscal_direto.db = local
def aguardar_resposta(modelo, xml_assinado, config):
    Path(sys.argv[5]).touch()
    time.sleep(30)
fiscal_direto.transmitir_autorizacao = aguardar_resposta
fiscal.emitir_nfce(int(sys.argv[3]), int(sys.argv[4]))
'''
    ambiente = {**os.environ, 'VENDAFACIL_DATA_DIR': str(tmp_path)}
    ambiente.pop('PYTHONPATH', None)
    proc = subprocess.Popen([sys.executable, '-X', 'utf8', '-I', '-c', programa,
                             str(Path(__file__).resolve().parents[1]), str(banco), str(venda['id']),
                             str(loja['user_id']), str(entrou)], env=ambiente)
    try:
        limite = time.monotonic() + 10
        while not entrou.exists() and proc.poll() is None and time.monotonic() < limite:
            time.sleep(0.025)
        assert entrou.exists()
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)

    nota = fiscal_store['db'].get_nota_por_venda(venda['id'], '65')
    assert nota['status'] == 'processando'
    assert bool(nota['chave']) and bool(nota['xml_assinado'])
    simulador.push('consulta', retorno_consulta(chave=nota['chave']))
    assert fiscal._processar_pendentes_direto(loja['config']) == 1
    final = fiscal_store['db'].get_nota(nota['id'])
    assert final['status'] == 'autorizada'
    assert [c['service'] for c in simulador.calls] == ['consulta']
    assert fiscal_store['db']._conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'


def test_conexao_interrompida_sem_resposta_preserva_chave_normal(loja, simulador, monkeypatch):
    def falhar(*args, **kwargs):
        raise requests.exceptions.ConnectionError(ProtocolError('Resposta interrompida'))

    monkeypatch.setattr(requests.Session, 'post', falhar)
    r = _emitir(loja, _vender(loja))
    assert r.status_code == 200
    nota = r.json()['nota']
    assert nota['status'] == 'processando'
    assert nota['tipo_emissao'] == '1'


def test_proxy_sem_conexao_permite_contingencia(loja, simulador, monkeypatch):
    def falhar(*args, **kwargs):
        motivo = ProxyError('Proxy local inacessível', NewConnectionError(None, 'Conexão recusada'))
        raise requests.exceptions.ProxyError(MaxRetryError(None, '/', motivo))

    monkeypatch.setattr(requests.Session, 'post', falhar)
    r = _emitir(loja, _vender(loja))
    assert r.status_code == 200
    nota = r.json()['nota']
    assert nota['status'] == 'contingencia'
    assert nota['tipo_emissao'] == '9'
