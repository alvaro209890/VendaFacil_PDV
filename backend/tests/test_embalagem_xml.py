from test_embalagem import criar
from test_importacao_regras import _xml


def preview(client,auth,ean,un,qtd,custo,nome='Palheiros'):
    r=client.post('/api/produtos/importar-xml/preview',headers=auth,content=_xml('',ean,un,str(qtd),str(custo),nome))
    assert r.status_code==200,r.text
    return r.json()['itens'][0]


def confirmar(client,auth,it,**extra):
    data=dict(produto_id=it['produto_id'],nome=it['nome'],codigo_barras=it['codigo_barras'],
        unidade=it['unidade'],unidade_compra=it['unidade_compra'],quantidade_por_embalagem=it['quantidade_por_embalagem'],
        quantidade_xml=it['quantidade_xml'],quantidade=it['quantidade'],preco_custo=it['valor_unitario'],preco_venda=3.56)
    data.update(extra)
    return client.post('/api/produtos/importar-xml/confirmar',headers=auth,json={'itens':[data]})


def test_t7_embalagem_configurada_preserva_precos(client,auth):
    p=criar(client,auth,estoque=0,codigo_barras='7899987654329')
    it=preview(client,auth,p['codigo_barras'],'CARTEIRA',2,10)
    assert it['quantidade']==40 and it['valor_unitario']==0.5
    assert it['fator_entrada']==20
    assert '40' in it['mensagem_entrada'] and 'CARTEIRA' in it['mensagem_entrada']
    r=confirmar(client,auth,it)
    assert r.status_code==200,r.text
    p=client.get(f"/api/produtos/{p['id']}",headers=auth).json()['produto']
    assert p['estoque']==40 and p['preco_custo']==0.5
    assert p['preco_unidade']==2 and p['preco_embalagem']==20
    it=preview(client,auth,p['codigo_barras'],'UN',3,0.75)
    assert it['fator_entrada']==1 and it['quantidade']==3


def test_t8_kaiser_sem_confirmacao_nao_multiplica(client,auth):
    it=preview(client,auth,'','UN',600,2.74,'CX 00050 KAISER LT 350ML')
    assert it['quantidade']==600 and it['valor_unitario']==2.74
    assert it['perguntar_embalagem'] is True
    r=confirmar(client,auth,it)
    assert r.status_code==200,r.text
    ps=client.get('/api/produtos',headers=auth).json()['produtos']
    p=next(p for p in ps if p['nome']=='CX 00050 KAISER LT 350ML')
    assert p['estoque']==600 and p['preco_custo']==2.74 and p['preco_venda']==3.56
    assert p['vende_por_unidade']==0


def test_novo_confirmado_explicitamente_vira_unidades(client,auth):
    it=preview(client,auth,'','UN',2,10,'Carteira Nova')
    # Cada UN desta nota é uma carteira (R$ 10 cada): o operador diz isso
    # explicitamente. Sem dizer, nota em UN entra 1 para 1 (caso Kaiser).
    r=confirmar(client,auth,it,vende_por_unidade=True,unidade_compra='CARTEIRA',
                quantidade_por_embalagem=20,preco_embalagem=20,preco_unidade=2,
                confirmar_abertura=True,nota_em_embalagem=True,unidade_xml='UN',valor_unitario_xml=10)
    assert r.status_code==200,r.text
    p=next(p for p in client.get('/api/produtos',headers=auth).json()['produtos'] if p['nome']=='Carteira Nova')
    assert p['estoque']==40 and p['preco_custo']==0.5 and p['vende_por_unidade']==1


def test_novo_duplo_sem_confirmacao_recusa(client,auth):
    it=preview(client,auth,'','UN',2,10,'Carteira Incompleta')
    r=confirmar(client,auth,it,vende_por_unidade=True,preco_embalagem=20,preco_unidade=2,unidade_compra='CARTEIRA',quantidade_por_embalagem=20)
    assert r.status_code==400,r.text
