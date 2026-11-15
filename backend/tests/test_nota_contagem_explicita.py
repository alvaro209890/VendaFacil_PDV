"""Reposição: a decisão de contagem independe da forma de venda cadastrada."""
import pytest


@pytest.mark.parametrize("duplo", [False, True])
@pytest.mark.parametrize("caixas", [False, True])
@pytest.mark.parametrize("un_nota", ["UN", "CX"])
def test_reposicao_contagem_explicita(client, auth, duplo, caixas, un_nota):
    produto = client.post('/api/produtos', headers=auth, json={
        'nome': 'Bebida de teste', 'estoque': 54, 'preco_custo': 1.59,
        'preco_venda': 2.07, 'unidade': 'UN', 'unidade_compra': 'CX',
        'quantidade_por_embalagem': 12, 'vende_por_unidade': duplo,
        'preco_embalagem': 23, 'preco_unidade': 2.07,
    }).json()['produto']
    r = client.post('/api/produtos/importar-xml/confirmar', headers=auth, json={
        'documento': 'Teste descartável', 'itens': [{
            'produto_id': produto['id'], 'nome': produto['nome'],
            'quantidade': 999, 'quantidade_xml': 2,
            'unidade_xml': un_nota, 'nota_em_embalagem': caixas,
            'quantidade_por_embalagem': 20 if duplo else 12,
            'valor_unitario_xml': 24, 'preco_venda': 999,
        }],
    })
    assert r.status_code == 200, r.text
    atual = client.get(f"/api/produtos/{produto['id']}", headers=auth).json()['produto']
    assert atual['estoque'] == 54 + (24 if caixas else 2)
    assert atual['preco_custo'] == (2 if caixas else 24)
    assert atual['preco_venda'] == 2.07
    assert atual['preco_embalagem'] == 23
    assert atual['preco_unidade'] == 2.07
    assert atual['vende_por_unidade'] == duplo
    assert atual['quantidade_por_embalagem'] == 12


def test_embalagem_fechada_nota_un_respeita_estoque_conferido(client, auth):
    r = client.post('/api/produtos/importar-xml/confirmar', headers=auth, json={
        'itens': [{'nome': 'Caixas fechadas', 'unidade': 'CX', 'unidade_xml': 'UN',
                   'modo_entrada': 'fechada', 'quantidade_xml': 24, 'quantidade': 2,
                   'preco_custo': 24, 'preco_venda': 30}],
    })
    assert r.status_code == 200, r.text
    p = next(p for p in client.get('/api/produtos', headers=auth).json()['produtos'] if p['nome'] == 'Caixas fechadas')
    assert p['unidade'] == 'CX' and p['estoque'] == 2


def test_troca_formato_preserva_estorno_de_venda_anterior(client, auth):
    p = client.post('/api/produtos', headers=auth, json={
        'nome': 'Estorno preservado', 'estoque': 24, 'preco_venda': 4,
    }).json()['produto']
    r = client.post('/api/vendas/checkout', headers=auth, json={
        'itens': [{'produto_id': p['id'], 'quantidade': 3}],
    })
    assert r.status_code == 201, r.text
    venda = r.json()['venda']['id']
    # Não permite reinterpretar os 3 UN vendidos como 3 CX no estorno.
    r = client.put(f"/api/produtos/{p['id']}", headers=auth, json={
        'unidade': 'CX', 'estoque': 2, 'preco_venda': 48,
    })
    assert r.status_code == 400 and 'estornos' in r.text
    # Os formatos caixa/unidade podem ser ativados mantendo a base em UN.
    r = client.put(f"/api/produtos/{p['id']}", headers=auth, json={
        'vende_por_unidade': True, 'unidade': 'UN', 'unidade_compra': 'CX',
        'quantidade_por_embalagem': 12, 'preco_embalagem': 48, 'preco_unidade': 5,
    })
    assert r.status_code == 200, r.text
    r = client.post(f'/api/vendas/{venda}/cancelar', headers=auth, json={'motivo': 'Teste de estorno'})
    assert r.status_code == 200, r.text
    p = client.get(f"/api/produtos/{p['id']}", headers=auth).json()['produto']
    assert p['estoque'] == 24 and p['preco_unidade'] == 5
