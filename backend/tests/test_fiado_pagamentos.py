"""Recebimento: conciliação Point, recuperação e caixa isolados de dinheiro real."""
from copy import deepcopy
from uuid import uuid4

import pytest
import contas_receber
import pix
import caixa
from mercadopago import PointError
from test_transacoes import checkout_local, loja


@pytest.fixture
def fiado(checkout_local, monkeypatch):
    api, local, user, produto, cliente, headers = checkout_local
    for modulo in (contas_receber, pix, caixa):
        monkeypatch.setattr(modulo, 'db', local)
    local.salvar_config_maquininha({'habilitado': 1, 'access_token': 'fixture', 'device_id': 'TEST', 'pix_integrado': 1}, 'agora')
    conta = local.create_conta_receber(user, cliente['id'], None, 100, None, 'Fiado teste', 'agora')

    class Point:
        orders = {}
        chamadas = []
        timeout = False
        cancelamento_pendente = False

        def __init__(self, token):
            assert token == 'fixture'

        def configurar_modo_pdv(self, device_id):
            assert device_id == 'TEST'

        def criar_cobranca(self, device_id, valor, referencia, imprimir, forma, *, idempotency_key):
            self.chamadas.append(idempotency_key)
            if idempotency_key not in self.orders:
                self.orders[idempotency_key] = {
                    'id': f'ORD{idempotency_key}', 'status': 'created', 'external_reference': referencia,
                    'transactions': {'payments': [{'id': f'PAY{idempotency_key}', 'amount': str(valor), 'status': 'created',
                                                  'payment_method': {'type': {'credito': 'credit_card', 'debito': 'debit_card', 'pix': 'bank_transfer'}[forma]}}]},
                }
            if self.timeout:
                type(self).timeout = False
                raise PointError(503, 'Sem conexão após criar')
            return deepcopy(self.orders[idempotency_key])

        def consultar_cobranca(self, order_id):
            return deepcopy(next(o for o in self.orders.values() if o['id'] == order_id))

        def cancelar_cobranca(self, order_id, *, at_terminal=False):
            order = next(o for o in self.orders.values() if o['id'] == order_id)
            if order['status'] == 'at_terminal':
                assert at_terminal
            if not self.cancelamento_pendente:
                order['status'] = 'canceled'
            return deepcopy(order)

    monkeypatch.setattr(contas_receber, 'MercadoPagoPoint', Point)
    return api, local, user, conta['id'], headers, Point


def criar(fiado, forma='debito', valor=30, referencia=None):
    api, _, _, conta, headers, _ = fiado
    return api.post(f'/api/contas-receber/{conta}/cobrancas', headers=headers,
                    json={'valor': valor, 'forma': forma, 'referencia': referencia or str(uuid4())})


def consultar(fiado, cobranca):
    api, _, _, conta, headers, _ = fiado
    return api.post(f'/api/contas-receber/{conta}/cobrancas/{cobranca}/consultar', headers=headers)


def aprovar(point):
    order = next(iter(point.orders.values()))
    order['status'] = 'processed'
    order['transactions']['payments'][0]['status'] = 'processed'
    return order


@pytest.mark.parametrize('forma', ['dinheiro', 'pix', 'debito', 'credito'])
def test_manual_respeita_forma_e_so_dinheiro_entra_na_gaveta(fiado, forma):
    api, local, user, conta, headers, _ = fiado
    assert api.post('/api/caixa/abrir', headers=headers, json={'valor_abertura': 10}).status_code == 200
    dados = {'valor': 20.50, 'forma': forma, 'referencia': str(uuid4())}
    for _ in range(2):
        r = api.post(f'/api/contas-receber/{conta}/pagar', headers=headers, json=dados)
        assert r.status_code == 200, r.text
    salva = local.get_conta_receber(conta, user)
    assert salva['valor_pendente'] == 79.50
    assert len(salva['pagamentos']) == 1
    assert salva['pagamentos'][0]['forma'] == forma
    assert local.resumo_caixa(local.get_caixa_aberto(user))['dinheiro_esperado'] == (30.50 if forma == 'dinheiro' else 10)


@pytest.mark.parametrize('forma', ['fiado', 'qualquer', 'PIX'])
def test_forma_invalida_recusada(fiado, forma):
    api, local, user, conta, headers, _ = fiado
    r = api.post(f'/api/contas-receber/{conta}/pagar', headers=headers, json={'valor': 10, 'forma': forma})
    assert r.status_code == 422
    assert local.get_conta_receber(conta, user)['valor_pendente'] == 100


@pytest.mark.parametrize('forma', ['debito', 'credito', 'pix'])
def test_point_so_baixa_apos_aprovar_e_nao_duplica(fiado, forma):
    api, local, user, conta, headers, point = fiado
    api.post('/api/caixa/abrir', headers=headers, json={'valor_abertura': 10})
    ref = str(uuid4())
    criada = criar(fiado, forma, referencia=ref)
    assert criada.status_code == 200, criada.text
    cobranca = criada.json()['cobranca']['id']
    assert local.get_conta_receber(conta, user)['valor_pendente'] == 100
    assert consultar(fiado, cobranca).json()['state'] == 'OPEN'
    aprovar(point)
    for _ in range(2):
        paga = consultar(fiado, cobranca)
        assert paga.status_code == 200, paga.text
        assert paga.json()['cobranca']['status'] == 'pago'
    # Repetir inclusive a criação após perder a resposta não cobra o restante de novo.
    assert criar(fiado, forma, referencia=ref).json()['state'] == 'FINISHED'
    salva = local.get_conta_receber(conta, user)
    assert salva['valor_pendente'] == 70
    assert len(salva['pagamentos']) == 1
    assert salva['pagamentos'][0]['forma'] == forma
    assert salva['pagamentos'][0]['payment_id']
    assert local.resumo_caixa(local.get_caixa_aberto(user))['dinheiro_esperado'] == 10
    assert local.cobranca_aprovada_sem_venda(user) is None


def test_timeout_recupera_mesma_order_com_mesma_chave(fiado):
    _, local, user, conta, _, point = fiado
    point.timeout = True
    ref = str(uuid4())
    assert criar(fiado, referencia=ref).status_code == 503
    salva = local.get_conta_receber(conta, user)
    assert salva['cobranca_pendente']['id'] == ref
    # Também sobrevive à reconexão com o banco.
    local.reconectar()
    assert consultar(fiado, ref).status_code == 200
    assert len(point.orders) == 1
    assert point.chamadas == [ref, ref]


def test_pendente_bloqueia_baixa_manual_cancelamento_e_nova_forma(fiado):
    api, local, user, conta, headers, _ = fiado
    assert criar(fiado).status_code == 200
    for caminho, dados in [('pagar', {'valor': 20, 'forma': 'dinheiro'}), ('cancelar', {})]:
        r = api.post(f'/api/contas-receber/{conta}/{caminho}', headers=headers, json=dados)
        assert r.status_code == 409, r.text
    assert criar(fiado, forma='credito').status_code == 409
    assert local.get_conta_receber(conta, user)['valor_pendente'] == 100


def test_cancelamento_assincrono_so_libera_apos_estado_final(fiado):
    api, local, user, conta, headers, point = fiado
    cob = criar(fiado).json()['cobranca']['id']
    next(iter(point.orders.values()))['status'] = 'at_terminal'
    point.cancelamento_pendente = True
    url = f'/api/contas-receber/{conta}/cobrancas/{cob}'
    assert api.delete(url, headers=headers).json()['cobranca']['status'] == 'pendente'
    point.cancelamento_pendente = False
    assert api.delete(url, headers=headers).json()['cobranca']['status'] == 'cancelado'
    assert local.get_conta_receber(conta, user)['valor_pendente'] == 100
    assert local.get_conta_receber(conta, user)['pagamentos'] == []


def test_aprovado_durante_cancelamento_concilia_em_vez_de_descartar(fiado):
    api, local, user, conta, headers, point = fiado
    cob = criar(fiado).json()['cobranca']['id']
    aprovar(point)
    r = api.delete(f'/api/contas-receber/{conta}/cobrancas/{cob}', headers=headers)
    assert r.json()['cobranca']['status'] == 'pago'
    assert local.get_conta_receber(conta, user)['valor_pendente'] == 70


@pytest.mark.parametrize('campo', ['amount', 'referencia', 'forma', 'status'])
def test_divergencia_na_point_nao_baixa_divida(fiado, campo):
    _, local, user, conta, _, point = fiado
    cob = criar(fiado).json()['cobranca']['id']
    ordem = aprovar(point)
    pay = ordem['transactions']['payments'][0]
    if campo == 'amount': pay['amount'] = '100'
    if campo == 'referencia': ordem['external_reference'] = 'outra-conta'
    if campo == 'forma': pay['payment_method']['type'] = 'credit_card'
    if campo == 'status': pay['status'] = 'rejected'
    assert consultar(fiado, cob).status_code == 409
    assert local.get_conta_receber(conta, user)['valor_pendente'] == 100
    assert local.get_conta_receber(conta, user)['cobranca_pendente']


def test_pix_qr_gera_payload_sem_dar_baixa(fiado):
    api, local, user, conta, headers, _ = fiado
    local.salvar_config_loja({'pix_chave': 'teste@example.com', 'pix_nome': 'LOJA TESTE', 'pix_cidade': 'QUERENCIA'}, 'agora')
    qr = api.post('/api/pix/qrcode', headers=headers, json={'valor': 30.25})
    assert qr.status_code == 200
    assert 'teste@example.com' in qr.json()['payload']
    assert '540530.25' in qr.json()['payload']
    assert qr.json()['qr_base64'].startswith('iVBOR')
    assert local.get_conta_receber(conta, user)['valor_pendente'] == 100


def test_pix_copia_cola_persiste_e_libera_point_e_outros_recebimentos(fiado):
    api, local, user, conta, headers, point = fiado
    local.salvar_config_loja({'pix_chave': 'teste@example.com'}, 'agora')
    # Não pode usar nenhuma operação na Point ao gerar o copia e cola.
    resposta = api.post(f'/api/contas-receber/{conta}/pix', headers=headers, json={'valor': 30})
    assert resposta.status_code == 200, resposta.text
    salvo = resposta.json()['pix']
    assert not point.orders
    assert local.cobranca_fiado_pendente(conta, user) is None
    assert local.cobranca_aprovada_sem_venda(user) is None
    # Reabrir o sistema conserva exatamente o código enviado ao cliente.
    local.reconectar()
    lista = api.get('/api/contas-receber', headers=headers).json()['contas']
    assert lista[0]['pix_pendentes'][0]['payload'] == salvo['payload']
    assert lista[0]['valor_pendente'] == 100
    # Uma nova geração do mesmo valor recupera o código já salvo.
    repetido = api.post(f'/api/contas-receber/{conta}/pix', headers=headers, json={'valor': 30})
    assert repetido.json()['pix']['id'] == salvo['id']
    # O terminal continua disponível, inclusive para outro acerto da mesma conta.
    cartao = criar(fiado, valor=20)
    assert cartao.status_code == 200
    aprovar(point)
    assert consultar(fiado, cartao.json()['cobranca']['id']).status_code == 200
    # O PIX pode chegar depois, sem precisar deixar janela aberta.
    dados = {'valor': 30, 'forma': 'pix', 'referencia': salvo['id']}
    for _ in range(2):
        assert api.post(f'/api/contas-receber/{conta}/pagar', headers=headers, json=dados).status_code == 200
    atual = local.get_conta_receber(conta, user)
    assert atual['valor_pendente'] == 50
    assert len(atual['pagamentos']) == 2
    assert atual['pix_pendentes'] == []


def test_falha_sql_na_baixa_point_nao_perde_conciliacao(fiado):
    _, local, user, conta, _, point = fiado
    cob = criar(fiado).json()['cobranca']['id']
    aprovar(point)
    with local._conn:
        local._conn.execute("CREATE TRIGGER falhar BEFORE INSERT ON pagamentos_fiado BEGIN SELECT RAISE(ABORT, 'falha'); END")
    assert consultar(fiado, cob).status_code == 500
    atual = local.get_conta_receber(conta, user)
    assert atual['valor_pendente'] == 100
    assert atual['cobranca_pendente']['status'] == 'pendente'
    with local._conn:
        local._conn.execute('DROP TRIGGER falhar')
    assert consultar(fiado, cob).status_code == 200
    assert local.get_conta_receber(conta, user)['valor_pendente'] == 70


def test_point_lenta_nao_ocupa_o_servidor(fiado, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    api, _, _, _, _, point = fiado
    entrou, liberar = Event(), Event()
    original = point.criar_cobranca

    def lento(self, *args, **kwargs):
        entrou.set()
        liberar.wait(5)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(point, 'criar_cobranca', lento)
    with ThreadPoolExecutor(max_workers=2) as pool:
        cobrando = pool.submit(criar, fiado)
        try:
            assert entrou.wait(3)
            # Uma Point sem resposta não pode impedir outro caixa de usar o PDV.
            saude = pool.submit(api.get, '/health')
            assert saude.result(timeout=2).status_code == 200
        finally:
            liberar.set()
        assert cobrando.result(timeout=3).status_code == 200


def test_conta_de_outro_usuario_nao_consulta_nem_cancela_cobranca(fiado):
    api, local, user, conta, headers, _ = fiado
    from auth import _gerar_jwt, _token_user
    cob = criar(fiado).json()['cobranca']['id']
    outro = local.create_user('outro', 'Outro', 'fixture', 'agora')
    h = {'Authorization': 'Bearer ' + _gerar_jwt(_token_user(outro))}
    base = f'/api/contas-receber/{conta}/cobrancas/{cob}'
    assert api.post(base + '/consultar', headers=h).status_code == 404
    assert api.delete(base, headers=h).status_code == 404
    assert api.post(f'/api/contas-receber/{conta}/cobrancas', headers=h,
                    json={'valor': 30, 'forma': 'debito', 'referencia': str(uuid4())}).status_code == 404
