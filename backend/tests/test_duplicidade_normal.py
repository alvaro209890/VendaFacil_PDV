"""Duplicidade não libera uma segunda emissão para a mesma venda."""
import pytest
from test_sefaz_simulador import fiscal_store, client, auth, simulador, emissor, loja, _vender, _emitir
from sefaz_fake import retorno_autorizacao, retorno_consulta
import fiscal


@pytest.mark.parametrize('cstat', ['204', '539'])
def test_duplicidade_normal_preserva_reserva_para_consultar(loja, simulador, fiscal_store, cstat):
    venda = _vender(loja)
    simulador.push('autorizacao', retorno_autorizacao(cstat, 'Duplicidade de NF-e', ''))
    primeira = _emitir(loja, venda).json()['nota']
    assert primeira['status'] == 'processando'
    segunda = _emitir(loja, venda).json()['nota']
    assert segunda['id'] == primeira['id'] and segunda['numero'] == primeira['numero']
    assert [c['service'] for c in simulador.calls] == ['autorizacao']
    simulador.push('consulta', retorno_consulta())
    assert fiscal._processar_pendentes_direto(loja['config']) == 1
    assert fiscal_store['db'].get_nota(primeira['id'])['status'] == 'autorizada'
    assert [c['service'] for c in simulador.calls] == ['autorizacao', 'consulta']
