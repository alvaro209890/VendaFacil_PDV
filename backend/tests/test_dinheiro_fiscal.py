"""D03-D04: XML e rateio fecham no centavo sem desconto negativo."""
from decimal import Decimal
import pytest
import fiscal_direto


@pytest.mark.parametrize('n,total', [(3, '.02'), (7, '.04'), (13, '.07')])
def test_d04_rateio_sem_residuo_negativo(n, total):
    bases = [.01] * n
    partes = fiscal_direto._ratear(float(total), bases)
    assert len(partes) == n
    assert all(0 <= Decimal(str(p)) <= Decimal('.01') for p in partes)
    assert sum(Decimal(str(p)) for p in partes) == Decimal(total)


def test_d03_xml_bate_com_checkout_no_meio_centavo(client, auth):
    from xml.etree import ElementTree as ET
    from test_fiscal_direto import _cfg
    from database import db
    produto = client.post('/api/produtos', headers=auth, json={
        'nome': 'Fracionado fiscal', 'preco_venda': 2.675, 'estoque': 10,
        'ncm': '19059090', 'cfop': '5102', 'cst_csosn': '102',
    }).json()['produto']
    resposta = client.post('/api/vendas/checkout', headers=auth, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
        'desconto': .005,
    })
    assert resposta.status_code == 201, resposta.text
    venda = db.get_venda_completa(resposta.json()['venda']['id'])
    doc = fiscal_direto.montar_documento(venda, _cfg())
    ns = {'n': fiscal_direto.NFE_NS}
    raiz = ET.fromstring(doc.xml)
    valor = lambda p: Decimal(raiz.findtext(p, namespaces=ns))
    produtos = sum(Decimal(e.text) for e in raiz.findall('.//n:det/n:prod/n:vProd', ns))
    descontos = sum(Decimal(e.text) for e in raiz.findall('.//n:det/n:prod/n:vDesc', ns))
    vnf = valor('.//n:ICMSTot/n:vNF')
    assert produtos == valor('.//n:ICMSTot/n:vProd')
    assert descontos == valor('.//n:ICMSTot/n:vDesc')
    assert produtos - descontos == vnf == Decimal(str(venda['total']))
    assert vnf == sum(Decimal(e.text) for e in raiz.findall('.//n:detPag/n:vPag', ns))


@pytest.mark.parametrize('grupo,campo,cst', [
    ('_grupo_pis', 'pis', '01'), ('_grupo_pis', 'pis', '49'),
    ('_grupo_cofins', 'cofins', '01'), ('_grupo_cofins', 'cofins', '49'),
])
def test_imposto_half_up(grupo, campo, cst):
    from xml.etree import ElementTree as ET
    raiz = ET.Element('imposto')
    valor = getattr(fiscal_direto, grupo)(raiz, {f'cst_{campo}': cst, f'aliquota_{campo}': 50}, 5.35)
    assert Decimal(str(valor)) == Decimal('2.68')


def test_ibpt_half_up_na_montagem(client, auth):
    from test_fiscal_direto import _cfg, _venda
    produto = client.post('/api/produtos', headers=auth, json={
        'nome': 'IBPT meio centavo', 'preco_venda': 5.35, 'estoque': 10,
        'ncm': '19059090', 'cfop': '5102', 'cst_csosn': '102',
    }).json()['produto']
    venda = _venda(produto)
    venda['total'] = 5.35
    venda['itens'][0].update(preco_unitario=5.35, subtotal=5.35)
    doc = fiscal_direto.montar_documento(venda, {**_cfg(), 'ibpt_percentual': 50})
    assert '<vTotTrib>2.68</vTotTrib>' in doc.xml
