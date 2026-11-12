"""Timeout pode ocorrer antes de a SEFAZ registrar a chave (cStat217)."""
import requests
from test_sefaz_simulador import fiscal_store, client, auth, simulador, emissor, loja, _vender, _emitir
from sefaz_fake import retorno_consulta, retorno_autorizacao
import fiscal


def test_timeout_com_chave_nao_encontrada_reenvia_mesmo_xml_sem_nova_numeracao(loja, simulador, monkeypatch, fiscal_store):
    original = requests.Session.post
    def timeout_uma_vez(session, *args, **kwargs):
        if not getattr(timeout_uma_vez, 'fez', False):
            timeout_uma_vez.fez = True
            raise requests.exceptions.ReadTimeout('Falha sintética antes do registro SEFAZ')
        return original(session, *args, **kwargs)
    monkeypatch.setattr(requests.Session, 'post', timeout_uma_vez)
    nota = _emitir(loja, _vender(loja)).json()['nota']
    assert nota['status'] == 'processando'
    original_xml = nota['xml_assinado']
    simulador.push('consulta', retorno_consulta('217', 'NF-e não consta na base', ''))
    simulador.push('autorizacao', retorno_autorizacao())
    assert fiscal._processar_pendentes_direto(loja['config']) == 1
    final = fiscal_store['db'].get_nota(nota['id'])
    assert final['status'] == 'autorizada'
    assert final['numero'] == nota['numero'] and final['chave'] == nota['chave']
    assert final['xml_assinado'] == original_xml
    assert [c['service'] for c in simulador.calls] == ['consulta', 'autorizacao']
    assert original_xml.split('?>', 1)[-1].strip() in simulador.calls[-1]['body']


def test_conflito_com_outra_chave_nao_retransmite_apos_217(loja, simulador, fiscal_store):
    simulador.push('autorizacao', retorno_autorizacao('539', 'Duplicidade com diferença na chave', ''))
    nota = _emitir(loja, _vender(loja)).json()['nota']

    for _ in range(2):
        simulador.push('consulta', retorno_consulta('217', 'NF-e não consta na base', chave=nota['chave']))
        assert fiscal._processar_pendentes_direto(loja['config']) == 1

    final = fiscal_store['db'].get_nota(nota['id'])
    assert final['status'] == 'processando'
    assert 'diferença na chave' in final['mensagem']
    assert final['chave'] == nota['chave']
    assert [c['service'] for c in simulador.calls] == ['autorizacao', 'consulta', 'consulta']
