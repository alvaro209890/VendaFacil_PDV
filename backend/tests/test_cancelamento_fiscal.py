"""Interação entre cancelamento comercial e fiscal, somente dados de teste."""
import pytest
from test_transacoes import loja, checkout_local
from auth import _agora


def _vender(checkout_local):
    api, _, _, produto, _, headers = checkout_local
    resposta = api.post('/api/vendas/checkout', headers=headers, json={
        'itens': [{'produto_id': produto['id'], 'quantidade': 1}],
    })
    assert resposta.status_code == 201
    return resposta.json()['venda']


def _nota(local, user, venda, status, modelo='65'):
    return local.criar_nota({
        'user_id': user, 'venda_id': venda['id'],
        'ref': f"teste-{modelo}-{venda['id']}-{status}", 'modelo': modelo,
        'ambiente': 'homologacao', 'status': status,
        'criado_em': _agora(), 'atualizado_em': _agora(),
    })


@pytest.mark.parametrize('modelo', ['65', '55'])
@pytest.mark.parametrize('status', ['autorizada', 'pendente', 'processando', 'contingencia'])
def test_v09_nota_ativa_impede_cancelar_venda(checkout_local, modelo, status):
    api, local, user, produto, _, headers = checkout_local
    venda = _vender(checkout_local)
    _nota(local, user, venda, status, modelo)
    resposta = api.post(f"/api/vendas/{venda['id']}/cancelar", headers=headers,
                        json={'motivo': 'Cancelamento de venda com nota'})
    assert resposta.status_code == 409
    assert 'fiscal' in resposta.text.lower() and 'antes' in resposta.text.lower()
    assert local.get_produto(produto['id'])['estoque'] == 4
    assert local.get_venda(venda['id'], user)['status'] == 'concluida'


def test_nota_cancelada_nao_devolve_estoque_sozinha(checkout_local, monkeypatch):
    import fiscal
    api, local, user, produto, _, headers = checkout_local
    monkeypatch.setattr(fiscal, 'db', local)
    venda = _vender(checkout_local)
    nota = _nota(local, user, venda, 'autorizada')
    # Só a fronteira externa é substituída; normalizador e persistência são reais.
    xml = ('<retEnvEvento xmlns="http://www.portalfiscal.inf.br/nfe">'
           '<retEvento><infEvento><cStat>135</cStat><xMotivo>Evento registrado</xMotivo>'
           '<nProt>151000000000001</nProt></infEvento></retEvento></retEnvEvento>')
    def transporte_teste(nota_enviada, config, justificativa):
        assert config['ambiente'] == 'homologacao'
        assert nota_enviada['id'] == nota['id']
        return {'retorno': {'status_code': 200, 'texto': xml}}
    monkeypatch.setattr(fiscal.fiscal_direto, 'cancelar_documento', transporte_teste)
    local.salvar_config_fiscal({'ambiente': 'homologacao', 'provedor_fiscal': 'sefaz_mt_direto'}, _agora())
    resultado = fiscal.cancelar_nfce(nota['id'], 'Cancelamento dentro do teste local')
    assert resultado['status'] == 'cancelada'
    assert local.get_produto(produto['id'])['estoque'] == 4
    assert local.get_venda(venda['id'], user)['status'] == 'concluida'
    resposta = api.post(f"/api/vendas/{venda['id']}/cancelar", headers=headers,
                        json={'motivo': 'Nota já cancelada; estorno comercial'})
    assert resposta.status_code == 200
    assert local.get_produto(produto['id'])['estoque'] == 5


@pytest.mark.parametrize('modelo', ['65', '55'])
def test_venda_cancelada_nao_pode_emitir_nota(checkout_local, monkeypatch, modelo):
    import fiscal
    api, local, user, _, cliente, headers = checkout_local
    monkeypatch.setattr(fiscal, 'db', local)
    venda = _vender(checkout_local)
    assert api.post(f"/api/vendas/{venda['id']}/cancelar", headers=headers,
                    json={'motivo': 'Cancelamento antes da emissão'}).status_code == 200
    with pytest.raises(fiscal.FiscalError, match='Venda cancelada'):
        if modelo == '65':
            fiscal.emitir_nfce(venda['id'], user)
        else:
            fiscal.emitir_nfe(venda['id'], user, cliente['id'])
    assert local.get_nota_por_venda(venda['id']) is None


def test_v09_nao_olha_apenas_ultima_nota(checkout_local):
    api, local, user, produto, _, headers = checkout_local
    venda = _vender(checkout_local)
    _nota(local, user, venda, 'autorizada')
    _nota(local, user, venda, 'cancelada')
    resposta = api.post(f"/api/vendas/{venda['id']}/cancelar", headers=headers,
                        json={'motivo': 'Última nota não é prova suficiente'})
    assert resposta.status_code == 409
    assert local.get_produto(produto['id'])['estoque'] == 4


_CFG_TESTE = {
    'habilitado': 1, 'cnpj': '12345678000195', 'inscricao_estadual': '00130000019',
    'regime_tributario': '1', 'logradouro': 'Rua Teste', 'numero': '100', 'bairro': 'Centro',
    'municipio': 'Cuiaba', 'codigo_municipio': '5103403', 'uf': 'MT', 'cep': '78000000',
    'ambiente': 'homologacao', 'provedor_fiscal': 'sefaz_mt_direto',
    'csc': 'CSCDEHOMOLOGACAO', 'csc_id': '000001',
}


@pytest.mark.parametrize('modelo', ['65', '55'])
def test_v09_reserva_antes_da_rede_impede_estorno(checkout_local, monkeypatch, modelo):
    """A transmissão ainda não voltou: cancelar não pode devolver estoque."""
    import fiscal
    api, local, user, produto, cliente, headers = checkout_local
    monkeypatch.setattr(fiscal, 'db', local)
    local.salvar_config_fiscal(_CFG_TESTE, _agora())
    if modelo == '55':
        local.update_cliente(cliente['id'], user, documento='12345678909', logradouro='Rua Teste',
                             numero='100', bairro='Centro', municipio='Cuiaba',
                             codigo_municipio='5103403', uf='MT', cep='78000000')
    venda = _vender(checkout_local)
    captura = {}

    def rede(venda_enviada, config, modelo_arg='65', **_kwargs):
        assert config.get('ambiente') == 'homologacao'
        assert str(modelo_arg) == modelo
        nota = local.get_nota_por_venda(venda['id'], modelo)
        assert nota and nota['status'] in ('processando', 'pendente')
        captura['id'] = nota['id']
        cancelamento = api.post(f"/api/vendas/{venda['id']}/cancelar", headers=headers,
                                json={'motivo': 'Cancelamento durante a transmissão'})
        assert cancelamento.status_code == 409
        assert local.get_produto(produto['id'])['estoque'] == 4
        assert local.get_venda(venda['id'], user)['status'] == 'concluida'
        return {
            'serie': nota['serie'], 'numero': nota['numero'], 'chave': '5' * 44,
            'xml_assinado': '<NFe/>', 'payload': '{}', 'qrcode_url': 'http://teste.local/qr',
            'retorno': {'status_code': 200, 'texto': '<ret><cStat>100</cStat><xMotivo>Autorizado o uso</xMotivo></ret>'},
        }

    monkeypatch.setattr(fiscal.fiscal_direto, 'preparar_e_tentar_transmitir', rede)
    if modelo == '65':
        resultado = fiscal.emitir_nfce(venda['id'], user)
    else:
        resultado = fiscal.emitir_nfe(venda['id'], user, cliente['id'])
    assert resultado['id'] == captura['id']
    assert resultado['status'] == 'autorizada'
    assert local.get_venda(venda['id'], user)['status'] == 'concluida'
    assert local.get_produto(produto['id'])['estoque'] == 4
    total = local._conn.execute('SELECT COUNT(*) FROM notas_fiscais WHERE venda_id = ?', (venda['id'],)).fetchone()[0]
    assert total == 1


def test_falha_antes_da_rede_nao_prende_cancelamento(checkout_local, monkeypatch):
    import fiscal
    import fiscal_direto
    api, local, user, produto, _, headers = checkout_local
    monkeypatch.setattr(fiscal, 'db', local)
    local.salvar_config_fiscal(_CFG_TESTE, _agora())
    venda = _vender(checkout_local)

    def falha(*_args, **_kwargs):
        raise fiscal_direto.FiscalDiretoError('Falha local antes de transmitir.')

    monkeypatch.setattr(fiscal_direto, 'preparar_e_tentar_transmitir', falha)
    with pytest.raises(fiscal.FiscalError, match='antes de transmitir'):
        fiscal.emitir_nfce(venda['id'], user)
    nota = local.get_nota_por_venda(venda['id'], '65')
    assert nota and nota['status'] == 'rejeitada'
    resposta = api.post(f"/api/vendas/{venda['id']}/cancelar", headers=headers,
                        json={'motivo': 'Emissão nem começou'})
    assert resposta.status_code == 200
    assert local.get_produto(produto['id'])['estoque'] == 5
