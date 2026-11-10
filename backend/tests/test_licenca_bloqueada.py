"""L03/C07: licença vencida não prende caixa, leitura, backup nem XML."""
from pathlib import Path
import conta

RAIZ = Path(__file__).resolve().parents[2]


def test_l03_tela_nao_prende_caixa_backup_e_xml():
    tela = (RAIZ / 'src' / 'pages' / 'Ativacao.tsx').read_text(encoding='utf-8')
    inicio = tela.find('status.ativado && status.bloqueado')
    assert inicio >= 0
    trecho = tela[inicio:inicio + 700]
    assert '{children}' in trecho
    assert 'fechar o caixa' in trecho.lower()
    pdv = (RAIZ / 'src' / 'pages' / 'PDV.tsx').read_text(encoding='utf-8')
    assert 'licencaBloqueada' in pdv
    botao = pdv[pdv.find('disabled={'):pdv.find('disabled={') + 220]
    assert 'licencaBloqueada' in botao


def test_c07_api_nao_recusa_caixa_leitura_backup_xml(client, auth, monkeypatch):
    monkeypatch.setattr(conta, 'PAINEL_URL', 'http://painel.exemplo')
    monkeypatch.setattr(conta, 'status', lambda: {
        'obrigatoria': True, 'ativado': True, 'bloqueado': True,
        'motivo': 'Licença expirada. Renove para continuar.',
    })
    aberto = client.post('/api/caixa/abrir', headers=auth, json={'valor_abertura': 10})
    if aberto.status_code == 409:
        pass
    elif aberto.status_code != 200:
        raise AssertionError(aberto.text)
    fechado = client.post('/api/caixa/fechar', headers=auth, json={'valor_fechamento': 10, 'observacao': ''})
    assert fechado.status_code == 200, fechado.text
    assert client.get('/api/produtos', headers=auth).status_code == 200
    assert client.get('/api/backup/exportar', headers=auth).status_code == 200
    xml = client.get('/api/fiscal/nfce/export/xml', headers=auth)
    assert xml.status_code != 403
    venda = client.post('/api/vendas/checkout', headers=auth, json={
        'itens': [{'produto_id': 1, 'quantidade': 1}], 'forma_pagamento': 'dinheiro',
    })
    assert venda.status_code == 403
