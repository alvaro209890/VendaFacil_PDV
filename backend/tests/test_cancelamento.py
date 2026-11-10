"""P2: cancelamento comercial seguro, não confundir com evento fiscal."""
from test_transacoes import loja, checkout_local
import pytest


@pytest.mark.parametrize('motivo', [None, '', '   '])
def test_cancelamento_exige_motivo(checkout_local, motivo):
    api, local, user, produto, _, headers = checkout_local
    venda = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
    }).json()['venda']
    resposta = api.post(f"/api/vendas/{venda['id']}/cancelar", headers=headers,
                        json={} if motivo is None else {'motivo': motivo})
    assert resposta.status_code in (409, 422)
    assert local.get_venda(venda['id'], user)['status'] == 'concluida'
    assert local.get_produto(produto['id'])['estoque'] == 4


def test_v13_cancelamento_alheio_404(checkout_local):
    from auth import _agora, _gerar_jwt, _token_user
    api, local, user, produto, _, headers = checkout_local
    venda = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
    }).json()['venda']
    outro = local.create_user('outro', 'Outro', 'hash_de_fixture', _agora())
    alheio = {'Authorization': 'Bearer ' + _gerar_jwt(_token_user(outro))}
    resposta = api.post(f"/api/vendas/{venda['id']}/cancelar", headers=alheio,
                        json={'motivo': 'Tentativa por outro usuário'})
    assert resposta.status_code == 404
    assert local.get_venda(venda['id'], user)['status'] == 'concluida'
    assert local.get_produto(produto['id'])['estoque'] == 4


def test_v10_cancelamento_concorrente_uma_devolucao(checkout_local):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    api, local, _, produto, _, headers = checkout_local
    venda = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
    }).json()['venda']
    barreira = Barrier(2)
    def cancelar(_):
        barreira.wait(timeout=10)
        return api.post(f"/api/vendas/{venda['id']}/cancelar", headers=headers,
                        json={'motivo': 'Cancelamento simultâneo'}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        respostas = list(pool.map(cancelar, range(2)))
    assert sorted(respostas) == [200, 409]
    assert local.get_produto(produto['id'])['estoque'] == 5
    assert local._conn.execute("SELECT COUNT(*) FROM movimentacoes_estoque WHERE origem = 'cancelamento_venda'").fetchone()[0] == 1


def test_v11_cancelada_sai_dos_totais(checkout_local):
    from auth import _agora
    api, local, user, produto, _, headers = checkout_local
    local.abrir_caixa(user, 0, _agora())
    venda = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
    }).json()['venda']
    antes = local.get_dashboard(user)
    assert antes['vendas_hoje_qtd'] == 1
    assert antes['vendas_total'] == 2
    assert api.post(f"/api/vendas/{venda['id']}/cancelar", headers=headers,
                    json={'motivo': 'Venda lançada por engano'}).status_code == 200
    caixa = local.resumo_caixa(local.get_caixa_aberto(user))
    assert caixa['vendas_qtd'] == 0
    assert caixa['vendas_total'] == 0
    assert caixa['dinheiro_esperado'] == 0
    painel = local.get_dashboard(user)
    assert painel['vendas_hoje_qtd'] == 0
    assert painel['vendas_hoje_total'] == 0
    assert painel['vendas_total'] == 0
    assert venda['id'] not in {v['id'] for v in painel['ultimas_vendas']}
    relatorio = local.relatorio_vendas(user, '2000-01-01', '2100-01-01')
    assert relatorio['qtd_vendas'] == 0
    assert relatorio['faturamento'] == 0


def test_v11_tela_confirma_cancelamento_com_atalho():
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[2]
    tela = (raiz / 'src/pages/Vendas.tsx').read_text(encoding='utf-8')
    api = (raiz / 'src/lib/api.ts').read_text(encoding='utf-8')
    assert 'function cancelarVenda' in api
    assert '/api/vendas/${id}/cancelar' in api
    assert 'cancelarVenda' in tela
    assert 'F9' in tela
    assert 'motivo' in tela
    assert "status !== 'concluida'" in tela or 'status === "cancelada"' in tela


@pytest.mark.parametrize('tabela,evento', [
    ('vendas', 'UPDATE'), ('contas_receber', 'UPDATE'), ('movimentacoes_estoque', 'INSERT'),
])
@pytest.mark.parametrize('sinal', ['ABORT', 'IGNORE'])
def test_cancelamento_rollback_sql(checkout_local, tabela, evento, sinal):
    api, local, user, produto, cliente, headers = checkout_local
    venda = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
        'forma_pagamento': 'fiado', 'cliente_id': cliente['id'],
    }).json()['venda']
    acao = "IGNORE" if sinal == 'IGNORE' else "ABORT, 'falha_estorno'"
    with local._conn:
        local._conn.execute(f'CREATE TEMP TRIGGER falhar_estorno BEFORE {evento} ON {tabela} BEGIN SELECT RAISE({acao}); END')
    resposta = api.post(f"/api/vendas/{venda['id']}/cancelar", headers=headers,
                        json={'motivo': 'Teste de falha na persistência'})
    assert resposta.status_code == (409 if sinal == 'IGNORE' else 500)
    assert local.get_venda(venda['id'], user)['status'] == 'concluida'
    assert local.get_produto(produto['id'])['estoque'] == 4
    conta = local.list_contas_receber(user)[0]
    assert conta['status'] == 'pendente' and conta['valor_pendente'] == 2
    assert local._conn.execute("SELECT COUNT(*) FROM movimentacoes_estoque WHERE origem = 'cancelamento_venda'").fetchone()[0] == 0


@pytest.mark.parametrize('recebido', [0, .5])
def test_v08_fiado_estorno_ou_recusa_recebido(checkout_local, recebido):
    api, local, user, produto, cliente, headers = checkout_local
    venda = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
        'forma_pagamento': 'fiado', 'cliente_id': cliente['id'],
    }).json()['venda']
    conta = local.list_contas_receber(user)[0]
    if recebido:
        from auth import _agora
        local.pagar_conta_receber(conta['id'], user, recebido, _agora())
    resposta = api.post(f"/api/vendas/{venda['id']}/cancelar", headers=headers,
                        json={'motivo': 'Cancelamento de venda fiada'})
    atual = local.get_conta_receber(conta['id'], user)
    if recebido:
        assert resposta.status_code == 409
        assert 'recebimento' in resposta.text.lower()
        assert atual['valor_pendente'] == 1.5
        assert local.get_venda(venda['id'], user)['status'] == 'concluida'
        assert local.get_produto(produto['id'])['estoque'] == 4
    else:
        assert resposta.status_code == 200
        assert atual['status'] == 'cancelado'
        assert atual['valor_pendente'] == 0
        assert local.get_produto(produto['id'])['estoque'] == 5


def test_v07_v10_cancelar_devolve_estoque_uma_vez(checkout_local):
    api, local, user, produto, _, headers = checkout_local
    venda = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
    }).json()['venda']
    resposta = api.post(f"/api/vendas/{venda['id']}/cancelar", headers=headers,
                        json={'motivo': 'Registro feito por engano'})
    assert resposta.status_code == 200, resposta.text
    atual = local.get_venda(venda['id'], user)
    assert atual['status'] == 'cancelada'
    assert atual['motivo_cancelamento'] == 'Registro feito por engano'
    assert atual['cancelada_em']
    assert local.get_produto(produto['id'])['estoque'] == 5
    movs = local._conn.execute("SELECT * FROM movimentacoes_estoque WHERE origem = 'cancelamento_venda'").fetchall()
    assert len(movs) == 1 and movs[0]['tipo'] == 'entrada' and movs[0]['quantidade'] == 1
    outra = api.post(f"/api/vendas/{venda['id']}/cancelar", headers=headers,
                     json={'motivo': 'Segunda tentativa indevida'})
    assert outra.status_code == 409
    assert local.get_produto(produto['id'])['estoque'] == 5
