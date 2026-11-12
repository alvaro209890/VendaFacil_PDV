"""H01–H09: reconferência real dos casos emitidos pelo PDV em homologação.

Opt-in: pytest -m homologacao tests/test_homologacao_real.py --tb=short.
Lê apenas o cofre padrão da loja. Não cria venda, não cobra a Point, não consome
numeração nem altera estoque. O operador/roteiro do PDV prepara os casos A–G
de docs/TESTE_FISCAL_WINDOWS.md; estes testes verificam o resultado na SEFAZ.
Nunca usar cópia de fixture ou certificado de outro contribuinte neste módulo.
"""
import json
import os
from pathlib import Path
import runpy
import sqlite3
from contextlib import closing
from datetime import datetime
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

import pytest
import fiscal_direto

pytestmark = pytest.mark.homologacao


@pytest.fixture(scope='module')
def cofre_homologacao():
    caminho = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'VendaFacilPDV' / 'dados' / 'vendafacil.db'
    precheck = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'scripts' / 'fiscal_precheck.py'))
    resultado = precheck['avaliar_banco'](caminho)
    if not resultado['apto_homologacao']:
        pytest.skip('Precheck da loja bloqueado: ' + ','.join(resultado['bloqueios']))
    with closing(sqlite3.connect(caminho.resolve().as_uri() + '?mode=ro', uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        config = dict(conn.execute('SELECT * FROM config_fiscal WHERE id=1').fetchone())
        notas = [dict(r) for r in conn.execute("""SELECT n.*,v.forma_pagamento,v.desconto,v.pagamento_detalhe
            FROM notas_fiscais n JOIN vendas v ON v.id=n.venda_id
            WHERE n.ambiente='homologacao' AND n.modelo='65' ORDER BY n.id DESC""")]
        tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        inutilizacoes = [dict(r) for r in conn.execute("SELECT * FROM inutilizacoes_fiscais WHERE ambiente='homologacao'")] if 'inutilizacoes_fiscais' in tabelas else []
    assert config['ambiente'] == 'homologacao'
    assert config['provedor_fiscal'] == 'sefaz_mt_direto'
    # Falha fechada se alguém alterar o mapa de serviços neste processo.
    for (modelo, ambiente, _), url in fiscal_direto.WS.items():
        if ambiente == 'homologacao':
            assert urlsplit(url).hostname == 'homologacao.sefaz.mt.gov.br'
    return config, notas, inutilizacoes


def _caso(cofre, predicado):
    for nota in cofre[1]:
        if predicado(nota):
            assert nota.get('xml_assinado') and nota.get('chave') and len(nota['chave']) == 44
            return nota
    pytest.fail('Caso real ausente no cofre: execute o cenário correspondente pelo PDV em homologação.', pytrace=False)


def _consultar(cofre, nota):
    try:
        r = fiscal_direto.consultar_chave('65', nota['chave'], cofre[0])
        assert r['status_code'] == 200
        raiz = ET.fromstring(r['texto'])
    except Exception:
        pytest.fail('Consulta real falhou; corpo e credenciais omitidos.', pytrace=False)
    return raiz


def _autorizada(cofre, nota):
    raiz = _consultar(cofre, nota)
    assert fiscal_direto._texto(raiz, 'cStat') in {'100', '150'}
    assert fiscal_direto._texto(raiz, 'nProt') == nota['protocolo']
    print(f"chave={nota['chave']} protocolo={nota['protocolo']} cStat={fiscal_direto._texto(raiz, 'cStat')}")


def test_h01_status_servico_real(cofre_homologacao):
    try:
        r = fiscal_direto.status_servico('65', cofre_homologacao[0])
    except Exception:
        pytest.fail('Status real indisponível; detalhes sensíveis omitidos.', pytrace=False)
    assert r['em_operacao'] and r['cstat'] == '107'


def test_h02_dinheiro_autorizado(cofre_homologacao):
    _autorizada(cofre_homologacao, _caso(cofre_homologacao, lambda n: n['status'] == 'autorizada' and n['forma_pagamento'] == 'dinheiro'))


def _integrada(cofre, formas):
    nota = _caso(cofre, lambda n: n['status'] == 'autorizada' and n['forma_pagamento'] in formas)
    detalhe = json.loads(nota['pagamento_detalhe'] or '{}')
    assert detalhe.get('tipo_integracao') == '1' and detalhe.get('autorizacao') and detalhe.get('adquirente_cnpj')
    xml = ET.fromstring(nota['xml_assinado'])
    assert xml.findtext('.//{*}card/{*}tpIntegra') == '1'
    assert xml.findtext('.//{*}card/{*}cAut') == detalhe['autorizacao']
    assert xml.findtext('.//{*}card/{*}CNPJReceb') == fiscal_direto.so_digitos(cofre[0]['cnpj'])
    _autorizada(cofre, nota)


def test_h03_cartao_com_vinculo(cofre_homologacao):
    _integrada(cofre_homologacao, {'credito', 'debito'})


def test_h04_pix_com_vinculo(cofre_homologacao):
    _integrada(cofre_homologacao, {'pix'})


def test_h05_desconto_autorizado(cofre_homologacao):
    _autorizada(cofre_homologacao, _caso(cofre_homologacao, lambda n: n['status'] == 'autorizada' and n['desconto'] > 0))


def test_h06_cancelamento_no_prazo(cofre_homologacao):
    nota = _caso(cofre_homologacao, lambda n: n['status'] == 'cancelada' and bool(n.get('autorizado_em')))
    assert 0 <= (datetime.fromisoformat(nota['atualizado_em']) - datetime.fromisoformat(nota['autorizado_em'])).total_seconds() <= 30 * 60
    assert fiscal_direto._texto(_consultar(cofre_homologacao, nota), 'cStat') == '101'


def test_h07_contingencia_transmitida(cofre_homologacao):
    nota = _caso(cofre_homologacao, lambda n: n['status'] == 'autorizada' and n['tipo_emissao'] == '9')
    assert ET.fromstring(nota['xml_assinado']).findtext('.//{*}tpEmis') == '9'
    _autorizada(cofre_homologacao, nota)


def test_h08_qr_abre_nota_no_portal(cofre_homologacao):
    import requests
    nota = _caso(cofre_homologacao, lambda n: n['status'] == 'autorizada' and bool(n.get('qrcode_url')))
    url = nota['qrcode_url']
    assert urlsplit(url).hostname == 'homologacao.sefaz.mt.gov.br'
    try:
        r = requests.get(url, timeout=30)
    except Exception:
        pytest.fail('Consulta QR real indisponível; URL e corpo omitidos.', pytrace=False)
    assert r.status_code == 200
    assert nota['chave'] in r.text and nota['protocolo'] in r.text


def test_h09_inutilizacao_homologada(cofre_homologacao):
    registros = [r for r in cofre_homologacao[2] if r['status'] == 'inutilizada']
    assert registros, 'Execute uma inutilização real permitida da loja, em homologação, pela tela Fiscal.'
    registro = registros[-1]
    raiz = ET.fromstring(registro['xml_retorno'])
    assert fiscal_direto._texto(raiz, 'cStat') == '102'
    assert fiscal_direto._texto(raiz, 'nProt') == registro['protocolo']
    print(f"protocolo={registro['protocolo']} cStat=102")
