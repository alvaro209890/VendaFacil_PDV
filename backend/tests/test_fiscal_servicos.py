"""M10: status de serviço usa SOAP oficial e não expõe configuração."""
import pytest
from xml.etree import ElementTree as ET
import fiscal_direto as direto


@pytest.mark.parametrize('modelo', ['55', '65'])
@pytest.mark.parametrize('cstat', ['107', '108', '109'])
def test_m10_status_servico(modelo, cstat, monkeypatch):
    chamadas = []
    def enviar(mod, servico, xml, config):
        chamadas.append((mod, servico, ET.fromstring(xml)))
        return {'status_code': 200, 'texto': f'<retConsStatServ xmlns="{direto.NFE_NS}" versao="4.00"><tpAmb>2</tpAmb><cStat>{cstat}</cStat><xMotivo>Retorno de teste</xMotivo></retConsStatServ>'}
    monkeypatch.setattr(direto, '_post_soap', enviar)
    resultado = direto.status_servico(modelo, {'ambiente': 'homologacao'})
    assert resultado['cstat'] == cstat
    assert resultado['em_operacao'] is (cstat == '107')
    assert chamadas[0][:2] == (modelo, 'status')
    xml = chamadas[0][2]
    ns = {'n': direto.NFE_NS}
    assert xml.tag == '{' + direto.NFE_NS + '}consStatServ'
    assert xml.findtext('n:tpAmb', namespaces=ns) == '2'
    assert xml.findtext('n:cUF', namespaces=ns) == '51'
    assert xml.findtext('n:xServ', namespaces=ns) == 'STATUS'
    assert direto.WS[(modelo, 'homologacao', 'status')].endswith('/NfeStatusServico4')
    corpo, headers = direto.montar_soap('status', ET.tostring(xml).decode())
    assert b'NFeStatusServico4' in corpo
    assert 'nfeStatusServicoNF' in headers['Content-Type']


def test_m10_rota_status_autenticada(client, auth, monkeypatch):
    monkeypatch.setattr(direto, 'status_servico', lambda modelo, config: {
        'cstat': '107', 'em_operacao': True, 'mensagem': 'Servico em operacao'}, raising=False)
    resposta = client.get('/api/fiscal/servicos/status?modelo=65', headers=auth)
    assert resposta.status_code == 200
    assert resposta.json()['cstat'] == '107'
    assert client.get('/api/fiscal/servicos/status?modelo=65').status_code == 401


def test_m10_config_a1_invalida_nao_vira_500(monkeypatch):
    def invalido(*args):
        raise ValueError('detalhe opaco da fixture')
    monkeypatch.setattr(direto, '_post_soap', invalido)
    with pytest.raises(direto.FiscalDiretoError, match='Não foi possível consultar'):
        direto.status_servico('65', {'ambiente': 'homologacao'})
