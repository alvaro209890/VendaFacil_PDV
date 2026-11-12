"""R08: diagnóstico autenticado, restrito e sem credenciais."""
import re

import backup
import fiscal_direto
from test_backup_robustez import armazenamento


def test_r08_diagnostico_exige_login(client):
    assert client.get('/api/diagnostico').status_code == 401


def test_r08_diagnostico_informa_saude_sem_segredos(client, auth, armazenamento, monkeypatch):
    local, _ = armazenamento
    agora = '2026-11-12T16:00:00+00:00'
    uid = local.create_user('operador', 'Operador', 'fixture', agora)['id']
    venda = local.create_venda(uid, None, 10, 0, 'dinheiro', '', [], agora)
    local.marcar_vendas_sincronizadas([venda['id']])
    local.salvar_config_fiscal({
        'habilitado': 1, 'ambiente': 'homologacao', 'csc': 'CSC_SENTINELA_FIXTURE',
        'gateway_token': 'TOKEN_SENTINELA_FIXTURE', 'certificado_a1_b64': 'QUJD',
        'certificado_senha': 'A1_SENTINELA_FIXTURE',
    }, agora)
    copia = backup._gerar_backup('auto')
    import diagnostico
    monkeypatch.setattr(diagnostico, 'db', local)
    monkeypatch.setattr(diagnostico, '_certificado', lambda _: (True, '2027-01-01T00:00:00+00:00'))
    monkeypatch.setattr(fiscal_direto, 'status_servico',
                        lambda *_: {'cstat': '107', 'mensagem': 'RETORNO_SENTINELA_FIXTURE'})

    r = client.get('/api/diagnostico', headers=auth)
    assert r.status_code == 200
    dados = r.json()
    assert re.fullmatch(r'\d+\.\d+\.\d+', dados['versao'])
    assert dados['banco']['caminho'] == local.caminho_db()
    assert dados['banco']['bytes'] > 0 and dados['banco']['livre_bytes'] > 0
    assert dados['banco']['integro'] is True
    assert dados['ultimo_backup']['nome'] == copia.name
    assert dados['ultimo_backup']['integro'] is True
    assert dados['fiscal']['ambiente'] == 'homologacao'
    assert dados['fiscal']['certificado_valido'] is True
    assert dados['fiscal']['certificado_vence_em']
    assert dados['fiscal']['sefaz'] == {'situacao': 'consultado', 'cstat': '107'}
    assert dados['fiscal']['pendentes'] == dados['fiscal']['contingencia'] == 0
    assert dados['ultima_sincronizacao']
    assert 'SENTINELA' not in r.text
