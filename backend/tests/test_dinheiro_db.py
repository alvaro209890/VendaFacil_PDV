"""F1.3: dinheiro exato no SQLite, sem acessar o banco do lojista."""
from decimal import Decimal, ROUND_HALF_UP
import pytest
import database
from auth import _agora


@pytest.fixture
def loja(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_DIR', tmp_path)
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'vendafacil.db')
    local = database.Database()
    agora = _agora()
    user = local.create_user('decimal', 'Decimal', 'hash_de_fixture', agora)
    yield local, user['id'], agora
    local.close()


def test_d05_resumo_200_vendas_exato(loja):
    local, user, agora = loja
    sessao = local.abrir_caixa(user, 0, agora)
    for _ in range(200):
        local.create_venda(user, None, 2.675, 0, 'dinheiro', '', [], agora)
    esperado = float(Decimal('2.675').quantize(Decimal('.01'), rounding=ROUND_HALF_UP) * 200)
    resumo = local.resumo_caixa(sessao)
    assert resumo['dinheiro_esperado'] == esperado
    assert resumo['por_forma']['dinheiro']['total'] == esperado


def test_caixa_abertura_movimento_fechamento_half_up(loja):
    local, user, agora = loja
    sessao = local.abrir_caixa(user, 2.675, agora)
    assert sessao['valor_abertura'] == 2.68
    local.registrar_movimento_caixa(sessao['id'], user, 'suprimento', .005, '', agora)
    assert local.resumo_caixa(sessao)['dinheiro_esperado'] == 2.69
    fechada = local.fechar_caixa(sessao['id'], 5.365, 2.69, agora, '')
    assert fechada['valor_fechamento'] == 5.37
    assert fechada['diferenca'] == 2.68


def test_fiado_valor_e_pagamento_half_up(loja):
    local, user, agora = loja
    conta = local.create_conta_receber(user, None, None, 10.005, None, '', agora)
    assert conta['valor_total'] == 10.01
    paga = local.pagar_conta_receber(conta['id'], user, 7.325, agora)
    assert paga['valor_pendente'] == 2.68


def test_dashboard_soma_decimal_sem_drift(loja):
    local, user, agora = loja
    for total in [.1, .2]:
        local.create_venda(user, None, total, 0, 'dinheiro', '', [], agora)
    painel = local.get_dashboard(user)
    assert painel['vendas_total'] == .3
    assert painel['vendas_hoje_total'] == .3


def test_relatorio_margem_preserva_precisao_decimal(loja):
    local, user, agora = loja
    produto = local.create_produto(user, 'Fração', 0, 5.35, 10, 0, '', 'KG', agora)
    local.create_venda(user, None, 2.68, 0, 'dinheiro', '', [{
        'produto_id': produto['id'], 'nome_produto': produto['nome'],
        'quantidade': .5, 'preco_unitario': 5.35, 'subtotal': 2.68,
    }], agora)
    resultado = local.relatorio_vendas(user, '2000-01-01', '2100-01-01')
    assert resultado['lucro_estimado'] == 2.68


@pytest.mark.parametrize('totais', [[.05, .04], [.1, .2]])
def test_relatorio_ticket_e_grupos_exatos(loja, totais):
    local, user, agora = loja
    for total in totais:
        local.create_venda(user, None, total, 0, 'dinheiro', '', [], agora)
    esperado = sum(Decimal(str(t)) for t in totais)
    resultado = local.relatorio_vendas(user, '2000-01-01', '2100-01-01')
    assert resultado['faturamento'] == float(esperado)
    assert resultado['por_forma'][0]['total'] == float(esperado)
    assert resultado['por_dia'][0]['total'] == float(esperado)
    assert resultado['ticket_medio'] == float((esperado / len(totais)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))

def test_agregado_decimal_reconecta_e_segrega(loja):
    local, user, agora = loja
    produto = local.create_produto(user, 'Fiscal Decimal', 0, .1, 10, 0, '', 'UN', agora)
    for total in [.1, .2]:
        local.create_venda(user, None, total, 0, 'dinheiro', '', [{
            'produto_id': produto['id'], 'nome_produto': produto['nome'],
            'quantidade': 1, 'preco_unitario': total, 'subtotal': total,
        }], agora)
    local.close()
    local.reconectar()
    segregado = local.relatorio_fiscal_segregado(user, '2000-01-01', '2100-01-01')
    assert segregado['total_geral'] == .3
    assert segregado['icms']['tributado_normal'] == .3
    assert segregado['itens'][0]['total'] == .3
