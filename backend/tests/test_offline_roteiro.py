"""L01: caracterização integrada dos fluxos locais, sem dados da loja.

Não substitui UI/instalador nem homologação fiscal: não há credenciadora,
certificado ou SEFAZ neste roteiro. O XML de entrada é fixture mínima.
"""
import importlib
import io
import urllib.error
import urllib.request
import zipfile
from decimal import Decimal

import pytest
import requests
from fastapi.testclient import TestClient

import database
import conta
from main import app
from test_importacao_parser import xml_nota


@pytest.fixture
def roteiro_local(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_DIR', tmp_path)
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'offline.db')
    local = database.Database()
    modulos = ('auth', 'backup', 'caixa', 'categorias', 'clientes',
               'contas_receber', 'fiscal', 'fiscal_config', 'fiscal_direto',
               'fiscal_router', 'main', 'mercadopago', 'pix', 'produtos',
               'sync_client', 'vendas')
    for nome in modulos:
        monkeypatch.setattr(importlib.import_module(nome), 'db', local)
    import backup
    destino = tmp_path / 'backups'
    destino.mkdir()
    monkeypatch.setattr(backup, 'BACKUP_DIR', destino)
    monkeypatch.setattr(conta, 'PAINEL_URL', '')
    chamadas = []

    def rede_proibida(*args, **kwargs):
        chamadas.append('tentativa de rede')
        raise urllib.error.URLError('rede indisponivel na fixture L01')
    monkeypatch.setattr(urllib.request, 'urlopen', rede_proibida)
    monkeypatch.setattr(requests.Session, 'request', rede_proibida)
    api = TestClient(app, raise_server_exceptions=False)
    try:
        yield api, local, chamadas
    finally:
        api.close()
        local.close()


def test_l01_roteiro_comercial_local_sem_tentativa_de_rede(roteiro_local):
    api, local, chamadas = roteiro_local
    headers = {}

    def req(metodo, caminho, esperado=200, **kwargs):
        resposta = api.request(metodo, caminho, headers=headers, **kwargs)
        # Não imprimir token, senha, backup ou corpo inteiro em caso de falha.
        detalhe = ''
        if resposta.status_code != esperado and 'application/json' in resposta.headers.get('content-type', ''):
            detalhe = str(resposta.json().get('detail', ''))
        assert resposta.status_code == esperado, f'{metodo} {caminho}: {resposta.status_code} {detalhe}'
        return resposta

    credenciais = {'usuario': 'operador-offline', 'senha': 'Fixture-offline@26'}
    req('POST', '/api/auth/registro', json={**credenciais, 'nome': 'Operador fixture'})
    login = req('POST', '/api/auth/login', json=credenciais).json()
    headers['Authorization'] = 'Bearer ' + login['token']
    assert conta.status()['bloqueado'] is False
    req('POST', '/api/caixa/abrir', json={'valor_abertura': 100})
    produto = req('POST', '/api/produtos', 201, json={
        'nome': 'Mercadoria fixture', 'preco_venda': 10, 'preco_custo': 6,
        'estoque': 10, 'codigo_barras': '12345670',
    }).json()['produto']
    pid = produto['id']
    req('POST', f'/api/produtos/{pid}/entrada', json={'quantidade': 1})
    req('POST', f'/api/produtos/{pid}/ajuste', json={'tipo': 'perda', 'quantidade': 1})
    cliente = req('POST', '/api/clientes', 201, json={'nome': 'Cliente fixture'}).json()['cliente']
    assert req('GET', '/api/clientes').json()['clientes']

    xml = xml_nota()
    previa = req('POST', '/api/produtos/importar-xml/preview', content=xml).json()
    item = previa['itens'][0]
    entrada = req('POST', '/api/produtos/importar-xml/confirmar', json={
        'chave': previa['chave'], 'documento': 'fixture L01',
        'itens': [{'produto_id': None, 'nome': item['nome'],
                   'codigo_barras': item['codigo_barras'], 'unidade': item['unidade'],
                   'quantidade': item['quantidade'], 'preco_custo': item['valor_unitario'],
                   'preco_venda': 2}],
    }).json()
    assert entrada['criados'] == 1

    itens = [{'produto_id': pid, 'quantidade': 2}]
    venda = req('POST', '/api/vendas/checkout', 201, json={
        'itens': itens, 'forma_pagamento': 'dinheiro',
    }).json()['venda']
    req('GET', f"/api/vendas/{venda['id']}")
    req('POST', '/api/vendas/checkout', 201, json={
        'itens': [{'produto_id': pid, 'quantidade': 1}],
        'forma_pagamento': 'fiado', 'cliente_id': cliente['id'],
    })
    contas = req('GET', '/api/contas-receber').json()['contas']
    assert len(contas) == 1
    cid = contas[0]['id']
    req('POST', f'/api/contas-receber/{cid}/pagar', json={'valor': 3, 'forma': 'dinheiro'})
    req('POST', f'/api/contas-receber/{cid}/pagar', json={'valor': 7, 'forma': 'dinheiro'})
    quitada = req('GET', '/api/contas-receber').json()['contas'][0]
    assert quitada['status'] == 'pago'
    assert len(quitada['pagamentos']) == 2

    descartada = req('POST', '/api/vendas/checkout', 201, json={
        'itens': [{'produto_id': pid, 'quantidade': 1}], 'forma_pagamento': 'dinheiro',
    }).json()['venda']
    req('POST', f"/api/vendas/{descartada['id']}/cancelar", json={'motivo': 'Fixture cancelamento offline'})
    assert req('GET', f'/api/produtos/{pid}').json()['produto']['estoque'] == 10 - 2 - 1
    req('POST', '/api/caixa/movimento', json={'tipo': 'suprimento', 'valor': 5})
    req('POST', '/api/caixa/movimento', json={'tipo': 'sangria', 'valor': 2})
    esperado = Decimal('100') + Decimal('10') * 2 + Decimal('3') + Decimal('7') + Decimal('5') - Decimal('2')
    assert req('GET', '/api/caixa/atual').json()['resumo']['dinheiro_esperado'] == float(esperado)
    assert req('GET', '/api/relatorios/vendas').json()['qtd_vendas'] == 2
    req('GET', '/api/relatorios/fiscal')
    # Sem documento, 404 é contrato correto, não defeito de offline.
    req('GET', '/api/fiscal/nfce/export/xml', 404)
    # Documento deliberadamente sintético: testa só armazenamento/download,
    # não autorização, assinatura, XSD nem integração SEFAZ.
    xml_fixture = '<fixture>ARQUIVO-DE-TESTE-L01</fixture>'
    local.criar_nota({
        'venda_id': venda['id'], 'user_id': local.get_user_by_usuario(credenciais['usuario'])['id'],
        'ref': 'fixture-export-l01', 'modelo': '65', 'numero': 1, 'serie': 1,
        'ambiente': 'homologacao', 'status': 'autorizada',
        'xml_autorizado': xml_fixture, 'criado_em': venda['criado_em'],
        'atualizado_em': venda['criado_em'],
    })
    xmls = req('GET', '/api/fiscal/nfce/export/xml')
    with zipfile.ZipFile(io.BytesIO(xmls.content)) as arquivo:
        assert len(arquivo.namelist()) == 1
        assert arquivo.read(arquivo.namelist()[0]).decode() == xml_fixture
    req('POST', '/api/caixa/fechar', json={'valor_fechamento': float(esperado)})
    assert req('GET', '/api/caixa/atual').json()['aberto'] is False

    copia = req('GET', '/api/backup/exportar').content
    assert copia.startswith(b'SQLite format 3\x00')
    req('PUT', f'/api/produtos/{pid}', json={'preco_venda': 99})
    req('POST', '/api/backup/restaurar', content=copia)
    assert req('GET', f'/api/produtos/{pid}').json()['produto']['preco_venda'] == 10
    assert local._conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert chamadas == []
