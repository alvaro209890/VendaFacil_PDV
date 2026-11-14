"""Aceitação da embalagem/avulso. Sempre banco temporário do conftest."""
import pytest


def criar(client, auth, **kwargs):
    data = dict(nome='Palheiro', preco_custo=0.5, preco_venda=9, estoque=65,
                unidade='UN', unidade_compra='CARTEIRA', quantidade_por_embalagem=20,
                vende_por_unidade=True, preco_embalagem=20, preco_unidade=2)
    data.update(kwargs)
    r = client.post('/api/produtos', headers=auth, json=data)
    assert r.status_code == 201, r.text
    return r.json()['produto']


def test_cadastro_precos_independentes(client, auth):
    p = criar(client, auth)
    assert p['vende_por_unidade'] == 1
    assert p['preco_embalagem'] == 20
    assert p['preco_unidade'] == 2
    assert p['preco_venda'] == 9  # não reinterpretar o preço legado
    assert p['estoque'] == 65


def test_legado_desligado(client, auth):
    r = client.post('/api/produtos', headers=auth, json={'nome':'Legado', 'preco_venda':7, 'estoque':15})
    p=r.json()['produto']
    assert p['vende_por_unidade'] == 0
    assert p['preco_venda'] == 7 and p['estoque'] == 15


@pytest.mark.parametrize('campo,valor', [('preco_embalagem',0),('preco_unidade',0),
    ('unidade_compra',''),('unidade','KG'),('quantidade_por_embalagem',1.5)])
def test_configuracao_invalida(client,auth,campo,valor):
    data=dict(nome='Inválido', vende_por_unidade=True, unidade='UN',unidade_compra='CX',
              quantidade_por_embalagem=20,preco_embalagem=20,preco_unidade=2)
    data[campo]=valor
    r=client.post('/api/produtos',headers=auth,json=data)
    assert r.status_code in (400,422),r.text


def test_ativar_legado_exige_dois_precos(client,auth):
    p=criar(client,auth,vende_por_unidade=False,preco_embalagem=0,preco_unidade=0)
    r=client.put(f"/api/produtos/{p['id']}",headers=auth,json={'vende_por_unidade':True})
    assert r.status_code == 400,r.text


def test_t9_trocar_fator_preserva_estoque(client,auth):
    p=criar(client,auth)
    r=client.put(f"/api/produtos/{p['id']}",headers=auth,json={'quantidade_por_embalagem':30})
    assert r.status_code == 200,r.text
    p=r.json()['produto']
    assert p['quantidade_por_embalagem']==30 and p['estoque']==65
    assert p['preco_embalagem']==20 and p['preco_unidade']==2
