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


def test_t9_desligar_e_religar_nao_reconta(client,auth):
    p=criar(client,auth)
    url=f"/api/produtos/{p['id']}"
    for data in ({'vende_por_unidade':False}, {'vende_por_unidade':True,'preco_embalagem':30,'preco_unidade':3}):
        r=client.put(url,headers=auth,json=data)
        assert r.status_code==200,r.text
        assert r.json()['produto']['estoque']==65


def test_entrada_manual_de_duas_carteiras(client,auth):
    p=criar(client,auth,estoque=0)
    r=client.post(f"/api/produtos/{p['id']}/entrada",headers=auth,json={
        'quantidade':2,'modo_entrada':'embalagem','custo_unitario':10})
    assert r.status_code==200,r.text
    assert r.json()['produto']['estoque']==40
    assert r.json()['produto']['preco_custo']==0.5


def test_codigos_de_unidade_nao_colidem(client,auth):
    p=criar(client,auth,codigo_barras_unidade='AVULSO-UNICO')
    r=client.post('/api/produtos',headers=auth,json={'nome':'Outro','codigo_barras':'AVULSO-UNICO'})
    assert r.status_code==409,r.text
    r=client.post('/api/produtos',headers=auth,json={'nome':'Outro 2','codigo_barras_unidade':'AVULSO-UNICO'})
    assert r.status_code==409,r.text
    outro=criar(client,auth)
    r=client.put(f"/api/produtos/{outro['id']}",headers=auth,json={'codigo_barras_unidade':'AVULSO-UNICO'})
    assert r.status_code==409,r.text
    assert p['codigo_barras_unidade']=='AVULSO-UNICO'


def test_migracao_idempotente_preserva_produto_antigo(tmp_path):
    from database import Database
    path=tmp_path/'legado.db'
    local=Database(path)
    uid=local.create_user('legado@fixture','Legado','hash_fixture','2026-11-13T00:00:00Z')['id']
    p=local.create_produto(uid,'Palheiros antigos',0.5,7,65,5,'','UN','2026-11-13T00:00:00Z')
    with local._conn:
        for col in ('vende_por_unidade','preco_embalagem','preco_unidade','codigo_barras_unidade'):
            local._conn.execute(f'ALTER TABLE produtos DROP COLUMN {col}')
        for col in ('modo_venda','unidade_venda','quantidade_estoque','custo_unitario_estoque'):
            local._conn.execute(f'ALTER TABLE itens_venda DROP COLUMN {col}')
    local.close()
    for _ in range(2):
        local=Database(path)
        produto=local.get_produto(p['id'])
        assert produto['estoque']==65 and produto['preco_venda']==7
        assert produto['vende_por_unidade']==0 and produto['preco_embalagem']==0 and produto['preco_unidade']==0
        local.close()
