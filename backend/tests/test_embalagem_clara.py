"""Importação de XML: caixa x unidade bem especificada (1.0.22).

Cobre a normalização de `uCom` (UN1 → UN), a sugestão de embalagem quando a
própria nota declara a contagem e o modo "comprei em caixa, vendo só unidade",
que antes obrigava o lojista a marcar "vende caixa e unidade" com dois preços.
"""
import pytest


def _xml(nome, ucom, qcom, vuncom, utrib='', qtrib='', ean='', chave=''):
    trib = f'<uTrib>{utrib}</uTrib><qTrib>{qtrib}</qTrib>' if utrib and qtrib else ''
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe>
<infNFe Id="NFe{chave}"><ide><mod>55</mod><nNF>1</nNF></ide><emit><xNome>Fornecedor</xNome></emit>
<det nItem="1"><prod><cEAN>{ean}</cEAN><xProd>{nome}</xProd>
<uCom>{ucom}</uCom><qCom>{qcom}</qCom><vUnCom>{vuncom}</vUnCom>{trib}</prod></det>
</infNFe></NFe></nfeProc>'''.encode()


def _preview(client, auth, xml):
    r = client.post('/api/produtos/importar-xml/preview', headers=auth, content=xml)
    assert r.status_code == 200, r.text
    return r.json()['itens'][0]


def _confirmar(client, auth, it, **extra):
    data = dict(
        produto_id=it['produto_id'], nome=it['nome'], codigo_barras=it['codigo_barras'],
        unidade=it['unidade'], unidade_compra=it['unidade_compra'],
        quantidade_por_embalagem=it['quantidade_por_embalagem'],
        quantidade_xml=it['quantidade_xml'], quantidade=it['quantidade'],
        preco_custo=it['valor_unitario'], preco_venda=5.0,
        unidade_xml=it['unidade_xml'], valor_unitario_xml=it['valor_unitario_xml'],
    )
    data.update(extra)
    return client.post('/api/produtos/importar-xml/confirmar', headers=auth,
                       json={'itens': [data]})


def _produto(client, auth, nome):
    produtos = client.get('/api/produtos', headers=auth).json()['produtos']
    return next(p for p in produtos if p['nome'] == nome)


def test_un1_da_nota_vira_un_e_nao_vira_embalagem(client, auth):
    it = _preview(client, auth, _xml('Refrigerante Lata 350', 'UN1', 5, 2.5))
    assert it['unidade_xml'] == 'UN'
    assert it['unidade_original'] == 'UN1'
    assert it['aviso_unidade']
    assert it['fator_entrada'] == 1
    assert it['quantidade'] == 5
    assert it['perguntar_embalagem'] is False
    assert it['sugestao'] == 'unidades'


def test_nota_declara_a_contagem_e_a_previa_avisa(client, auth):
    it = _preview(client, auth, _xml('Refrigerante Cola 2L', 'CX', 2, 40, utrib='UN', qtrib='12'))
    assert it['fator_sugerido'] == 6  # 2 CX = 12 UN
    assert it['perguntar_embalagem'] is True
    assert it['sugestao'] == 'embalagem'
    assert any('6 por CX' in s for s in it['sinais_embalagem'])


def test_nome_com_caixa_avisa_mesmo_com_nota_em_un_solta(client, auth):
    it = _preview(client, auth, _xml('CX 00050 KAISER LT 350ML', 'UN', 600, 2.74))
    assert it['fator_sugerido'] == 0
    assert it['perguntar_embalagem'] is True
    assert it['sugestao'] == 'revisar'
    assert it['embalagem_sugerida'] == 'CX'


def test_nota_em_peso_nunca_sugere_embalagem(client, auth):
    it = _preview(client, auth, _xml('BANANA PRATA', 'KG', 2, 5, utrib='KG', qtrib='2'))
    assert it['fator_sugerido'] == 0


def test_mesma_unidade_com_contagem_tributavel_maior_sugere(client, auth):
    it = _preview(client, auth, _xml('CERVEJA LATA 350', 'UN', 50, 32.88, utrib='UN', qtrib='600'))
    assert it['fator_sugerido'] == 12


def test_modo_unidade_cria_estoque_em_un_sem_preco_de_embalagem(client, auth):
    it = _preview(client, auth, _xml('REFRIGERANTE COLA 2L CX 6', 'CX', 2, 40))
    assert it['perguntar_embalagem'] is True
    # A tela manda a quantidade e o custo já convertidos para a unidade.
    r = _confirmar(client, auth, it, modo_entrada='unidade', unidade='UN',
                   quantidade_por_embalagem=6, nota_em_embalagem=True,
                   quantidade=12, preco_custo=round(40 / 6, 4))
    assert r.status_code == 200, r.text
    p = _produto(client, auth, 'REFRIGERANTE COLA 2L CX 6')
    assert p['estoque'] == 12
    assert p['unidade'] == 'UN'
    assert p['preco_custo'] == pytest.approx(40 / 6, abs=1e-4)
    assert p['vende_por_unidade'] == 0
    assert p['preco_embalagem'] == 0 and p['preco_unidade'] == 0


def test_modo_unidade_com_nota_em_unidades_soltas_nao_multiplica(client, auth):
    it = _preview(client, auth, _xml('AGUA MINERAL 500ML CX 12', 'UN', 600, 1.2))
    r = _confirmar(client, auth, it, modo_entrada='unidade',
                   quantidade_por_embalagem=12, nota_em_embalagem=False,
                   quantidade=600, preco_custo=1.2)
    assert r.status_code == 200, r.text
    p = _produto(client, auth, 'AGUA MINERAL 500ML CX 12')
    assert p['estoque'] == 600
    assert p['preco_custo'] == pytest.approx(1.2, abs=1e-4)


def test_modo_embalagem_exige_os_dois_precos(client, auth):
    it = _preview(client, auth, _xml('Carteira Palheiro CX', 'UN', 2, 10))
    r = _confirmar(client, auth, it, modo_entrada='embalagem', vende_por_unidade=True,
                   confirmar_abertura=True, unidade_compra='CARTEIRA',
                   quantidade_por_embalagem=20)
    assert r.status_code == 400
    assert 'dois preços' in r.json()['detail']