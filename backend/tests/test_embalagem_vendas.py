import pytest
from test_embalagem import criar


def vender(client,auth,p,itens):
    return client.post('/api/vendas/checkout',headers=auth,json={
        'itens':[{'produto_id':p['id'],**it} for it in itens]})


@pytest.mark.parametrize('itens,total,baixa',[
    ([{'quantidade':1,'modo_venda':'embalagem'}],20,20),
    ([{'quantidade':1,'modo_venda':'unidade'}],2,1),
    ([{'quantidade':1,'modo_venda':'embalagem'},{'quantidade':3,'modo_venda':'unidade'}],26,23),
    ([{'quantidade':20,'modo_venda':'unidade'}],40,20),
    ([{'quantidade':1}],2,1),
])
def test_t2_t3_t5_vendas(client,auth,itens,total,baixa):
    p=criar(client,auth)
    r=vender(client,auth,p,itens)
    assert r.status_code==201,r.text
    assert r.json()['venda']['total']==total
    assert client.get(f"/api/produtos/{p['id']}",headers=auth).json()['produto']['estoque']==65-baixa


def test_t4_recusa_embalagem_e_aceita_15_avulsos(client,auth):
    p=criar(client,auth,estoque=15)
    r=vender(client,auth,p,[{'quantidade':1,'modo_venda':'embalagem'}])
    assert r.status_code==400,r.text
    assert client.get(f"/api/produtos/{p['id']}",headers=auth).json()['produto']['estoque']==15
    r=vender(client,auth,p,[{'quantidade':15}])
    assert r.status_code==201 and r.json()['venda']['total']==30


def test_t6_legado_um_para_um(client,auth):
    p=criar(client,auth,vende_por_unidade=False)
    r=vender(client,auth,p,[{'quantidade':2}])
    assert r.status_code==201 and r.json()['venda']['total']==18
    assert client.get(f"/api/produtos/{p['id']}",headers=auth).json()['produto']['estoque']==63


def test_linhas_duplicadas_nao_ultrapassam_estoque(client,auth):
    p=criar(client,auth,estoque=20)
    r=vender(client,auth,p,[{'quantidade':1,'modo_venda':'embalagem'},{'quantidade':1}])
    assert r.status_code in (400,409)
    assert client.get(f"/api/produtos/{p['id']}",headers=auth).json()['produto']['estoque']==20


def test_historico_movimentos_e_estorno_snapshot(client,auth):
    p=criar(client,auth)
    r=vender(client,auth,p,[{'quantidade':1,'modo_venda':'embalagem'},{'quantidade':3}])
    assert r.status_code==201,r.text
    v=r.json()['venda']['id']
    itens=client.get(f'/api/vendas/{v}',headers=auth).json()['venda']['itens']
    assert [(i['quantidade'],i['quantidade_estoque'],i['unidade_venda']) for i in itens]==[(1,20,'CARTEIRA'),(3,3,'UN')]
    assert 'CARTEIRA' in itens[0]['nome_produto']
    client.put(f"/api/produtos/{p['id']}",headers=auth,json={'quantidade_por_embalagem':30})
    r=client.post(f'/api/vendas/{v}/cancelar',headers=auth,json={'motivo':'Cliente desistiu'})
    assert r.status_code==200,r.text
    assert client.get(f"/api/produtos/{p['id']}",headers=auth).json()['produto']['estoque']==65


@pytest.mark.parametrize('qtd',[0.5,1.2])
def test_embalagem_ou_avulso_inteiros(client,auth,qtd):
    p=criar(client,auth)
    assert vender(client,auth,p,[{'quantidade':qtd,'modo_venda':'embalagem'}]).status_code==400
