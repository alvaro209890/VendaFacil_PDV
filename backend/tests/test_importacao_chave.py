"""I01: a mesma chave de NF-e não entra no estoque duas vezes."""
CHAVE = '35200114200166000187650010000000991123456780'
EAN = '7891000999110'
XML = f'''<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00"><NFe>
<infNFe Id="NFe{CHAVE}" versao="4.00">
<ide><mod>55</mod><nNF>99</nNF></ide>
<emit><xNome>Distribuidora Isolada</xNome></emit>
<det nItem="1"><prod><cEAN>{EAN}</cEAN><xProd>BOLACHA</xProd>
<uCom>UN</uCom><qCom>12.0000</qCom><vUnCom>2.5000</vUnCom></prod></det>
</infNFe></NFe></nfeProc>'''.encode()


def _confirmar(client, auth):
    return client.post('/api/produtos/importar-xml/confirmar', json={
        'documento': '99',
        'chave': CHAVE,
        'itens': [{
            'produto_id': None, 'nome': 'BOLACHA', 'codigo_barras': EAN,
            'unidade': 'UN', 'quantidade': 12, 'preco_custo': 2.5, 'preco_venda': 4.0,
            'atualizar_custo': True,
        }],
    }, headers=auth)


def test_i01_chave_repetida_nao_duplica_estoque(client, auth):
    primeira = _confirmar(client, auth)
    assert primeira.status_code == 200, primeira.text
    produto = next(p for p in client.get('/api/produtos', headers=auth).json()['produtos']
                   if p['codigo_barras'] == EAN)
    assert produto['estoque'] == 12
    segunda = _confirmar(client, auth)
    assert segunda.status_code == 409
    assert 'importad' in segunda.text.lower()
    de_novo = client.get(f"/api/produtos/{produto['id']}", headers=auth).json()['produto']
    assert de_novo['estoque'] == 12
    previa = client.post('/api/produtos/importar-xml/preview', content=XML, headers=auth)
    assert previa.status_code == 200
    assert previa.json()['ja_importada'] is True
