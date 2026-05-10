"""Contas a Receber (Venda Fiada) — VendaFácil PDV"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth import _verificar_jwt, _agora
from database import db

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
    valor: float = Field(gt=0)


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
    return {"conta": conta}


@router.post("", status_code=201)
async def criar(data: ContaReceberCreate, request: Request):
    user_id = _get_user_id(request)
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
    conta = db.pagar_conta_receber(conta_id, user_id, data.valor, agora)
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    return {"conta": conta}


@router.post("/{conta_id}/cancelar")
async def cancelar(conta_id: int, request: Request):
    user_id = _get_user_id(request)
    agora = _agora()
    ok = db.cancelar_conta_receber(conta_id, user_id, agora)
    if not ok:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    return {"ok": True}
