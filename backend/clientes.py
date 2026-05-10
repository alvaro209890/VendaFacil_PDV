"""Clientes — VendaFácil PDV"""

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


class ClienteCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    telefone: str = Field(default="", max_length=20)
    email: str = Field(default="", max_length=120)
    endereco: str = Field(default="", max_length=255)
    observacao: str = Field(default="", max_length=500)


class ClienteUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    telefone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=120)
    endereco: str | None = Field(default=None, max_length=255)
    observacao: str | None = Field(default=None, max_length=500)


@router.get("")
async def listar(request: Request):
    user_id = _get_user_id(request)
    return {"clientes": db.list_clientes(user_id)}


@router.get("/{cliente_id}")
async def obter(cliente_id: int, request: Request):
    user_id = _get_user_id(request)
    c = db.get_cliente(cliente_id, user_id)
    if not c:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    return {"cliente": c}


@router.post("", status_code=201)
async def criar(data: ClienteCreate, request: Request):
    user_id = _get_user_id(request)
    agora = _agora()
    c = db.create_cliente(
        user_id, data.nome, data.telefone, data.email,
        data.endereco, data.observacao, agora,
    )
    return {"cliente": c}


@router.put("/{cliente_id}")
async def atualizar(cliente_id: int, data: ClienteUpdate, request: Request):
    user_id = _get_user_id(request)
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    updates["atualizado_em"] = _agora()
    c = db.update_cliente(cliente_id, user_id, **updates)
    if not c:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    return {"cliente": c}


@router.delete("/{cliente_id}")
async def remover(cliente_id: int, request: Request):
    user_id = _get_user_id(request)
    c = db.update_cliente(cliente_id, user_id, ativo=0, atualizado_em=_agora())
    if not c:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    return {"ok": True}
