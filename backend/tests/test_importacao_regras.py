"""I02–I05: embalagem, XML inválido, código repetido e SEM GTIN."""

def _xml(chave, ean, unidade, qtd, valor, nome='ITEM'):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe>
<infNFe Id="NFe{chave}"><ide><nNF>1</nNF></ide><emit><xNome>Fornecedor</xNome></emit>
<det nItem="1"><prod><cEAN>{ean}</cEAN><xProd>{nome}</xProd>
<uCom>{unidade}</uCom><qCom>{qtd}</qCom><vUnCom>{valor}</vUnCom></prod></det>
</infNFe></NFe></nfeProc>'''.encode()


def test_i02_converte_so_quando_a_unidade_do_xml_e_a_de_compra(client, auth):
    criado = client.post('/api/produtos', json={
        'nome': 'Arroz fardo', 'preco_venda': 5, 'preco_custo': 2, 'estoque': 0,
        'codigo_barras': '7891000888001', 'unidade': 'UN', 'unidade_compra': 'CX',
        'quantidade_por_embalagem': 12,
    }, headers=auth)
    assert criado.status_code == 201, criado.text
    caixa = client.post('/api/produtos/importar-xml/preview', headers=auth, content=_xml(
        '35200114200166000187650010000000881123456781', '7891000888001', 'CX', '2.0000', '24.0000'))
    assert caixa.status_code == 200, caixa.text
    item = caixa.json()['itens'][0]
    assert item['quantidade'] == 24
    assert item['valor_unitario'] == 2
    unidade = client.post('/api/produtos/importar-xml/preview', headers=auth, content=_xml(
        '35200114200166000187650010000000881123456782', '7891000888001', 'UN', '3.0000', '1.5000'))
    assert unidade.json()['itens'][0]['quantidade'] == 3
    assert unidade.json()['itens'][0]['valor_unitario'] == 1.5


def test_i02_nota_em_unidade_nao_apaga_o_fator(client, auth):
    criado = client.post('/api/produtos', json={
        'nome': 'Feijao fardo', 'preco_venda': 6, 'preco_custo': 3, 'estoque': 0,
        'codigo_barras': '7891000888011', 'unidade': 'UN', 'unidade_compra': 'CX',
        'quantidade_por_embalagem': 12,
    }, headers=auth)
    assert criado.status_code == 201, criado.text
    produto_id = criado.json()['produto']['id']
    previa_un = client.post('/api/produtos/importar-xml/preview', headers=auth, content=_xml(
        '35200114200166000187650010000000881123456791', '7891000888011', 'UN', '3.0000', '1.5000'))
    item = previa_un.json()['itens'][0]
    conf = client.post('/api/produtos/importar-xml/confirmar', json={
        'chave': '35200114200166000187650010000000881123456791',
        'itens': [{
            'produto_id': produto_id, 'nome': 'Feijao fardo', 'codigo_barras': '7891000888011',
            'unidade': item['unidade'], 'unidade_compra': item['unidade_compra'],
            'quantidade_por_embalagem': item['quantidade_por_embalagem'],
            'quantidade': item['quantidade'], 'preco_custo': item['valor_unitario'], 'preco_venda': 6,
        }],
    }, headers=auth)
    assert conf.status_code == 200, conf.text
    depois = client.get(f'/api/produtos/{produto_id}', headers=auth).json()['produto']
    assert depois['quantidade_por_embalagem'] == 12
    assert depois['unidade_compra'] == 'CX'
    caixa = client.post('/api/produtos/importar-xml/preview', headers=auth, content=_xml(
        '35200114200166000187650010000000881123456792', '7891000888011', 'CX', '2.0000', '24.0000'))
    assert caixa.json()['itens'][0]['quantidade'] == 24


def test_i02_fator_sem_unidade_de_compra_ainda_converte_caixa(client, auth):
    criado = client.post('/api/produtos', json={
        'nome': 'Acucar fardo', 'preco_venda': 5, 'preco_custo': 2, 'estoque': 0,
        'codigo_barras': '7891000888012', 'unidade': 'UN', 'quantidade_por_embalagem': 12,
    }, headers=auth)
    assert criado.status_code == 201, criado.text
    caixa = client.post('/api/produtos/importar-xml/preview', headers=auth, content=_xml(
        '35200114200166000187650010000000881123456793', '7891000888012', 'CX', '2.0000', '24.0000'))
    assert caixa.json()['itens'][0]['quantidade'] == 24
    assert caixa.json()['itens'][0]['valor_unitario'] == 2


def test_i03_xml_invalido_nao_grava(client, auth):
    antes = len(client.get('/api/produtos', headers=auth).json()['produtos'])
    ruim = client.post('/api/produtos/importar-xml/preview', headers=auth, content=b'<nfe>')
    outro = client.post('/api/produtos/importar-xml/preview', headers=auth,
                        content=b'<?xml version="1.0"?><pedido><item>1</item></pedido>')
    assert ruim.status_code == 400
    assert outro.status_code == 400
    assert len(client.get('/api/produtos', headers=auth).json()['produtos']) == antes


def test_i04_codigo_repetido_nao_cria_outro_produto(client, auth):
    primeiro = client.post('/api/produtos', json={
        'nome': 'Sabao', 'preco_venda': 4, 'preco_custo': 2, 'estoque': 1,
        'codigo_barras': '7891000888002',
    }, headers=auth)
    assert primeiro.status_code == 201, primeiro.text
    repetido = client.post('/api/produtos', json={
        'nome': 'Sabao copia', 'preco_venda': 4, 'preco_custo': 2, 'estoque': 9,
        'codigo_barras': '7891000888002',
    }, headers=auth)
    assert repetido.status_code == 409
    conf = client.post('/api/produtos/importar-xml/confirmar', json={
        'chave': '35200114200166000187650010000000881123456783',
        'itens': [{
            'produto_id': None, 'nome': 'Sabao novo', 'codigo_barras': '7891000888002',
            'unidade': 'UN', 'quantidade': 2, 'preco_custo': 2, 'preco_venda': 4,
        }],
    }, headers=auth)
    assert conf.status_code == 200, conf.text
    iguais = [p for p in client.get('/api/produtos', headers=auth).json()['produtos']
              if p['codigo_barras'] == '7891000888002']
    assert len(iguais) == 1
    assert iguais[0]['estoque'] == 3


def test_i05_sem_gtin_nao_grava_codigo_falso(client, auth):
    previa = client.post('/api/produtos/importar-xml/preview', headers=auth, content=_xml(
        '35200114200166000187650010000000881123456784', 'SEM GTIN', 'UN', '1.0000', '3.0000', 'Farinha'))
    assert previa.status_code == 200, previa.text
    assert previa.json()['itens'][0]['codigo_barras'] == ''
    conf = client.post('/api/produtos/importar-xml/confirmar', json={
        'chave': '35200114200166000187650010000000881123456784',
        'itens': [{
            'produto_id': None, 'nome': 'Farinha', 'codigo_barras': 'SEM GTIN',
            'unidade': 'UN', 'quantidade': 1, 'preco_custo': 3, 'preco_venda': 5,
        }],
    }, headers=auth)
    assert conf.status_code == 200, conf.text
    farinha = next(p for p in client.get('/api/produtos', headers=auth).json()['produtos'] if p['nome'] == 'Farinha')
    assert farinha['codigo_barras'] == ''
