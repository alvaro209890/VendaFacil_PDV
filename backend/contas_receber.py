"""Contas a Receber (Venda Fiada) — VendaFácil PDV"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Literal
from uuid import UUID, uuid4

from auth import _verificar_jwt, _agora
from database import db
from dinheiro import decimal
from mercadopago import MercadoPagoPoint, PointError, _state, _payment, _valor_decimal
from pix import _pix_config, gerar_payload, gerar_qrcode_base64

router = APIRouter()


def _get_user_id(request: Request) -> int:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não informado.")
    payload = _verificar_jwt(auth[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return int(payload["sub"])


class ContaReceberCreate(BaseModel):
    cliente_id: int | None = Field(default=None)
    venda_id: int | None = Field(default=None)
    valor_total: float = Field(gt=0)
    data_vencimento: str | None = Field(default=None, max_length=20)
    observacao: str = Field(default="", max_length=500)


class PagamentoConta(BaseModel):
    valor: float = Field(allow_inf_nan=False)
    forma: Literal['dinheiro', 'pix', 'debito', 'credito'] = 'dinheiro'
    referencia: UUID | None = None


class CobrancaFiado(BaseModel):
    valor: float = Field(gt=0, le=999999.99, allow_inf_nan=False, multiple_of=0.01)
    forma: Literal['pix', 'debito', 'credito']
    referencia: UUID


class PixFiadoInput(BaseModel):
    valor: float = Field(gt=0, le=999999.99, allow_inf_nan=False, multiple_of=0.01)


def _erro_valor(exc: ValueError) -> HTTPException:
    texto = str(exc)
    codigo = 409 if 'cancelada' in texto.lower() or 'cobrança pendente' in texto.lower() else 400
    return HTTPException(status_code=codigo, detail=texto)


def _cliente_point() -> MercadoPagoPoint:
    cfg = db.get_config_maquininha()
    if not cfg.get('habilitado'):
        raise HTTPException(status_code=503, detail='Maquininha não habilitada nas configurações.')
    return MercadoPagoPoint(cfg.get('access_token', ''))


def _obter_cobranca(conta_id: int, cobranca_id: str, user_id: int) -> dict:
    cobranca = db.get_cobranca_fiado(cobranca_id, conta_id, user_id)
    if not cobranca:
        raise HTTPException(status_code=404, detail='Cobrança não encontrada.')
    return cobranca


def _ordem(cobranca: dict, cli: MercadoPagoPoint) -> dict:
    if cobranca['order_id']:
        return cli.consultar_cobranca(cobranca['order_id'])
    # A reserva e a chave sobrevivem a timeout/reinício. Repetir não cria outra cobrança.
    try:
        ordem = cli.criar_cobranca(
            cobranca['device_id'], _valor_decimal(cobranca['valor']),
            f"fiado-{cobranca['id']}", False, cobranca['forma'], idempotency_key=cobranca['id'],
        )
    except PointError as exc:
        if exc.status in {400, 401, 403, 404, 422}:
            db.atualizar_cobranca_fiado(cobranca['id'], status='erro', agora=_agora())
        raise
    if not ordem.get('id'):
        raise HTTPException(status_code=502, detail='Point não retornou o identificador. Consulte a cobrança para recuperar.')
    db.atualizar_cobranca_fiado(cobranca['id'], order_id=str(ordem['id']), agora=_agora())
    return ordem


def _conciliar(cobranca: dict, ordem: dict) -> dict:
    estado = _state(ordem)
    if estado == 'FINISHED':
        pagamento = _payment(ordem)
        tipo = (pagamento.get('payment_method') or {}).get('type') or pagamento.get('type')
        forma = {'credit_card': 'credito', 'debit_card': 'debito', 'pix': 'pix', 'bank_transfer': 'pix'}.get(tipo)
        if (ordem.get('external_reference') != f"fiado-{cobranca['id']}"
                or str(ordem.get('id')) != str(cobranca['order_id'])
                or pagamento.get('status') not in {'approved', 'processed', 'accredited'}
                or not pagamento.get('id')
                or decimal(pagamento.get('amount', 0)) != decimal(cobranca['valor'])
                or forma != cobranca['forma']):
            raise HTTPException(status_code=409, detail='Pagamento divergente. Confira valor, forma e referência na Point antes de continuar.')
        try:
            db.pagar_conta_receber(
                cobranca['conta_id'], cobranca['user_id'], cobranca['valor'], _agora(), forma,
                referencia=f"point:{cobranca['id']}", cobranca_id=cobranca['id'], payment_id=str(pagamento['id']),
            )
        except ValueError as exc:
            raise _erro_valor(exc) from exc
    elif estado in {'CANCELED', 'ERROR'}:
        db.atualizar_cobranca_fiado(cobranca['id'], status='cancelado' if estado == 'CANCELED' else 'erro', agora=_agora())
    return {
        'cobranca': db.get_cobranca_fiado(cobranca['id'], cobranca['conta_id'], cobranca['user_id']),
        'state': estado, 'conta': db.get_conta_receber(cobranca['conta_id'], cobranca['user_id']),
    }


def _resultado_encerrado(cobranca: dict) -> dict:
    return {'cobranca': cobranca, 'state': 'FINISHED' if cobranca['status'] == 'pago' else 'CANCELED',
            'conta': db.get_conta_receber(cobranca['conta_id'], cobranca['user_id'])}


@router.get("")
async def listar(request: Request, status: str | None = None):
    user_id = _get_user_id(request)
    return {"contas": db.list_contas_receber(user_id, status)}


@router.get("/{conta_id}")
async def obter(conta_id: int, request: Request):
    user_id = _get_user_id(request)
    conta = db.get_conta_receber(conta_id, user_id)
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    venda = db.get_venda_completa(conta["venda_id"], user_id) if conta.get("venda_id") else None
    conta["venda"] = venda
    conta["itens"] = (venda or {}).get("itens", [])
    return {"conta": conta}


@router.post("", status_code=201)
async def criar(data: ContaReceberCreate, request: Request):
    user_id = _get_user_id(request)
    if data.cliente_id is not None and not db.get_cliente(data.cliente_id, user_id):
        raise HTTPException(status_code=400, detail="Cliente não encontrado.")
    if data.venda_id is not None and not db.get_venda(data.venda_id, user_id):
        raise HTTPException(status_code=400, detail="Venda não encontrada.")
    agora = _agora()
    conta = db.create_conta_receber(
        user_id, data.cliente_id, data.venda_id,
        data.valor_total, data.data_vencimento, data.observacao, agora,
    )
    return {"conta": conta}


@router.post("/{conta_id}/pagar")
async def pagar(conta_id: int, data: PagamentoConta, request: Request):
    user_id = _get_user_id(request)
    agora = _agora()
    if data.valor <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser maior que zero.")
    try:
        conta = db.pagar_conta_receber(conta_id, user_id, data.valor, agora, data.forma,
                                      referencia=f'manual:{data.referencia}' if data.referencia else None)
    except ValueError as exc:
        raise _erro_valor(exc) from exc
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    return {"conta": conta}


@router.post('/{conta_id}/cobrancas')
def criar_cobranca(conta_id: int, data: CobrancaFiado, request: Request):
    user_id = _get_user_id(request)
    if not db.get_conta_receber(conta_id, user_id):
        raise HTTPException(status_code=404, detail='Conta não encontrada.')
    cfg = db.get_config_maquininha()
    if data.forma == 'pix' and not cfg.get('pix_integrado'):
        raise HTTPException(status_code=400, detail='PIX na Point desligado. Ative em Maquininha ou use QR Code / copia e cola.')
    if not cfg.get('device_id'):
        raise HTTPException(status_code=400, detail='Configure o terminal em Maquininha antes de cobrar.')
    try:
        cli = _cliente_point()
        cli.configurar_modo_pdv(cfg['device_id'])
        cobranca = db.reservar_cobranca_fiado(str(data.referencia), conta_id, user_id, data.valor, data.forma, cfg['device_id'], _agora())
        if cobranca['status'] != 'pendente':
            return _resultado_encerrado(cobranca)
        ordem = _ordem(cobranca, cli)
        cobranca = _obter_cobranca(conta_id, cobranca['id'], user_id)
        return _conciliar(cobranca, ordem)
    except PointError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.mensagem) from exc
    except ValueError as exc:
        raise _erro_valor(exc) from exc


@router.post('/{conta_id}/pix')
def gerar_pix_fiado(conta_id: int, data: PixFiadoInput, request: Request):
    user_id = _get_user_id(request)
    if not db.get_conta_receber(conta_id, user_id):
        raise HTTPException(status_code=404, detail='Conta não encontrada.')
    chave, nome, cidade = _pix_config()
    if not chave:
        raise HTTPException(status_code=503, detail='Chave PIX não configurada. Configure em Configurações da Loja.')
    pix_id = uuid4()
    payload = gerar_payload(chave, data.valor, nome, cidade, txid=pix_id.hex[:25])
    try:
        return {'pix': db.salvar_pix_fiado(str(pix_id), conta_id, user_id, data.valor,
                                         payload, gerar_qrcode_base64(payload), _agora())}
    except ValueError as exc:
        raise _erro_valor(exc) from exc


@router.post('/{conta_id}/cobrancas/{cobranca_id}/consultar')
def consultar_cobranca(conta_id: int, cobranca_id: str, request: Request):
    cobranca = _obter_cobranca(conta_id, cobranca_id, _get_user_id(request))
    if cobranca['status'] != 'pendente':
        return _resultado_encerrado(cobranca)
    try:
        ordem = _ordem(cobranca, _cliente_point())
        return _conciliar(_obter_cobranca(conta_id, cobranca_id, cobranca['user_id']), ordem)
    except PointError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.mensagem) from exc


@router.delete('/{conta_id}/cobrancas/{cobranca_id}')
def cancelar_cobranca(conta_id: int, cobranca_id: str, request: Request):
    cobranca = _obter_cobranca(conta_id, cobranca_id, _get_user_id(request))
    if cobranca['status'] != 'pendente':
        return _resultado_encerrado(cobranca)
    try:
        cli = _cliente_point()
        ordem = _ordem(cobranca, cli)
        cobranca = _obter_cobranca(conta_id, cobranca_id, cobranca['user_id'])
        resultado = _conciliar(cobranca, ordem)
        if resultado['cobranca']['status'] != 'pendente':
            return resultado
        cli.cancelar_cobranca(cobranca['order_id'], at_terminal=_state(ordem) == 'ON_TERMINAL')
        # HTTP 202 significa solicitado, não cancelado. Só liberar após consultar o estado final.
        return _conciliar(cobranca, cli.consultar_cobranca(cobranca['order_id']))
    except PointError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.mensagem) from exc


@router.post("/{conta_id}/cancelar")
async def cancelar(conta_id: int, request: Request):
    user_id = _get_user_id(request)
    agora = _agora()
    try:
        ok = db.cancelar_conta_receber(conta_id, user_id, agora)
    except ValueError as exc:
        raise _erro_valor(exc) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    return {"ok": True}
