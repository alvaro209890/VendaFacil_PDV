"""I06 / F2.21: modelo, GTIN e números da prévia de NF-e."""
import pytest
from importacao_xml import parse_nfe


def xml_nota(modelo='55', gtin='7891000888001', quantidade='2', custo='1.25', raiz='NFe'):
    ide = f'<ide><mod>{modelo}</mod><nNF>1</nNF></ide>' if modelo is not None else '<ide><nNF>1</nNF></ide>'
    nfe = f'<NFe><infNFe Id="NFe35200114200166000187550010000000011123456780">{ide}<emit><xNome>Fixture</xNome></emit><det nItem="1"><prod><xProd>Arroz fixture</xProd><cEAN>{gtin}</cEAN><uCom>UN</uCom><qCom>{quantidade}</qCom><vUnCom>{custo}</vUnCom></prod></det></infNFe></NFe>'
    return (nfe if raiz == 'NFe' else f'<{raiz}>{nfe}</{raiz}>').encode()


@pytest.mark.parametrize('modelo', ['65', '57', '', None])
def test_i06_modelo_diferente_ou_ausente_recusado(modelo):
    with pytest.raises(ValueError, match='modelo 55'):
        parse_nfe(xml_nota(modelo=modelo))


@pytest.mark.parametrize('gtin', ['123', '7891000888002', 'ABC1000888001', '00000000', '７８９１０００８８８００１'])
def test_i06_gtin_invalido_recusado(gtin):
    with pytest.raises(ValueError, match='GTIN'):
        parse_nfe(xml_nota(gtin=gtin))


@pytest.mark.parametrize('gtin', ['12345670', '123456789012', '7891000888001', '17891000888008', 'SEM GTIN', ''])
def test_i06_gtin_valido_ou_sem_gtin(gtin):
    nota = parse_nfe(xml_nota(gtin=gtin))
    assert nota['itens'][0]['codigo_barras'] == ('' if gtin in ('SEM GTIN', '') else gtin)


@pytest.mark.parametrize('quantidade', ['0', '-1', 'NaN', 'Infinity', 'texto', ''])
def test_i06_quantidade_invalida_recusada(quantidade):
    with pytest.raises(ValueError, match='quantidade'):
        parse_nfe(xml_nota(quantidade=quantidade))


@pytest.mark.parametrize('custo', ['-1', 'NaN', 'Infinity', 'texto', ''])
def test_i06_custo_invalido_recusado(custo):
    with pytest.raises(ValueError, match='custo'):
        parse_nfe(xml_nota(custo=custo))


def test_i06_outro_documento_com_nfe_aninhada_recusado():
    with pytest.raises(ValueError, match='NF-e'):
        parse_nfe(xml_nota(raiz='pedido'))


def test_i06_nfeproc_e_zero_no_custo_continuam_aceitos():
    nota = parse_nfe(xml_nota(raiz='nfeProc', custo='0', quantidade='0.335'))
    assert nota['itens'][0]['quantidade'] == 0.335
    assert nota['itens'][0]['valor_unitario'] == 0


@pytest.mark.parametrize('alteracao', ['item_sem_produto', 'nome_vazio'])
def test_i06_item_malformado_nao_e_ignorado(alteracao):
    xml = xml_nota()
    if alteracao == 'item_sem_produto':
        xml = xml.replace(b'</infNFe>', b'<det nItem="2"><imposto/></det></infNFe>')
    else:
        xml = xml.replace(b'<xProd>Arroz fixture</xProd>', b'<xProd> </xProd>')
    with pytest.raises(ValueError, match='item'):
        parse_nfe(xml)


@pytest.mark.parametrize('campos', [
    {'modelo': '65'}, {'gtin': '7891000888002'},
    {'quantidade': '0'}, {'custo': 'NaN'},
])
def test_i06_preview_invalido_400_sem_escrever(client, auth, campos):
    antes = client.get('/api/produtos', headers=auth).json()['produtos']
    resposta = client.post('/api/produtos/importar-xml/preview', headers=auth,
                           content=xml_nota(**campos))
    assert resposta.status_code == 400
    assert client.get('/api/produtos', headers=auth).json()['produtos'] == antes
