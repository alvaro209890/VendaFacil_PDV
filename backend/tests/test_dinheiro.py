"""P3 / D01-D02: dinheiro comercial, com HALF_UP e entrada finita."""
from decimal import Decimal
import pytest


def test_d02_meio_centavo_comercial():
    from dinheiro import decimal, moeda, multiplicar, somar
    assert decimal('2,675') == Decimal('2.675')
    assert moeda('2.675') == 2.68
    assert moeda(2.675) == 2.68
    assert moeda('-2.675') == -2.68
    assert multiplicar('0.335', '12.99') == Decimal('4.35')
    assert somar(['3.33', '3.33', '3.33']) == Decimal('9.99')


def test_d01_soma_subtotais_e_desconto():
    from dinheiro import moeda, multiplicar, somar, decimal
    subtotais = [multiplicar('0.335', '12.99'), multiplicar(3, '3.33')]
    assert moeda(somar(subtotais) - decimal('0.01')) == 14.33


@pytest.mark.parametrize('valor', ['NaN', 'Infinity', '-Infinity', float('nan'), float('inf')])
def test_dinheiro_recusa_nao_finito(valor):
    from dinheiro import decimal
    with pytest.raises(ValueError, match='finito'):
        decimal(valor)

def test_checkout_dinheiro_half_up(client, auth):
    produto = client.post('/api/produtos', headers=auth, json={
        'nome': 'Meio centavo', 'preco_venda': 2.675, 'estoque': 10,
    }).json()['produto']
    resposta = client.post('/api/vendas/checkout', headers=auth, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
        'desconto': 0.005,
    })
    assert resposta.status_code == 201, resposta.text
    dados = resposta.json()
    assert dados['itens'][0]['subtotal'] == 2.68
    assert dados['venda']['desconto'] == 0.01
    assert dados['venda']['total'] == 2.67
