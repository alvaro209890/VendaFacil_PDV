"""P4: a venda pertence a uma sessão de caixa, não só a uma janela de tempo."""
from auth import _agora
from test_transacoes import checkout_local, loja


def test_c06_venda_nao_entra_na_sessao_seguinte(checkout_local):
    api, local, user, produto, _, headers = checkout_local
    primeira = local.abrir_caixa(user, 10, '2026-11-10T10:00:00')
    venda = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
    })
    assert venda.status_code == 201
    segunda = local.abrir_caixa(user, 0, '2026-11-10T10:00:00')
    assert local.resumo_caixa(primeira)['vendas_qtd'] == 1
    assert local.resumo_caixa(primeira)['vendas_total'] == 2
    assert local.resumo_caixa(segunda)['vendas_qtd'] == 0
    assert local.resumo_caixa(segunda)['vendas_total'] == 0


def test_c01_esperado_bate_com_gaveta(checkout_local):
    api, local, user, produto, _, headers = checkout_local
    sessao = local.abrir_caixa(user, 10, _agora())
    assert api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
    }).status_code == 201
    local.registrar_movimento_caixa(sessao['id'], user, 'sangria', 1, 'retirada', _agora())
    local.registrar_movimento_caixa(sessao['id'], user, 'suprimento', .5, 'reforço', _agora())
    resumo = local.resumo_caixa(local.get_caixa_aberto(user))
    assert resumo['vendas_dinheiro'] == 2
    assert resumo['dinheiro_esperado'] == 11.5
    fechado = local.fechar_caixa(sessao['id'], 11.5, resumo['dinheiro_esperado'], _agora(), '')
    assert fechado['diferenca'] == 0


def test_d4_pdv_vende_sem_caixa_aberto_e_sem_aviso():
    # Álvaro, 14/11/2026: abrir caixa não é obrigatório para vender e o PDV
    # não mostra aviso de caixa fechado (antes: faixa amarela "Caixa fechado").
    from pathlib import Path
    tela = (Path(__file__).resolve().parents[2] / 'src/pages/PDV.tsx').read_text(encoding='utf-8')
    assert 'Caixa fechado' not in tela
    assert 'caixaAberto' not in tela
    assert 'caixaAtual' not in tela
    inicio = tela.index('onClick={finalizarVenda}')
    botao = tela[inicio:tela.index('className=', inicio)]
    assert 'caixaAberto' not in botao
    assert 'licencaBloqueada' in botao
