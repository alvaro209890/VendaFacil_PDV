"""Categorias de Produtos — VendaFácil PDV"""

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


class CategoriaCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    cor: str = Field(default="#6366f1", max_length=9)


class CategoriaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=60)
    cor: str | None = Field(default=None, max_length=9)


@router.get("")
async def listar(request: Request):
    user_id = _get_user_id(request)
    return {"categorias": db.list_categorias(user_id)}


@router.post("", status_code=201)
async def criar(data: CategoriaCreate, request: Request):
    user_id = _get_user_id(request)
    agora = _agora()
    cat = db.create_categoria(user_id, data.nome, data.cor, agora)
    return {"categoria": cat}


@router.put("/{categoria_id}")
async def atualizar(categoria_id: int, data: CategoriaUpdate, request: Request):
    user_id = _get_user_id(request)
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar.")
    cat = db.update_categoria(categoria_id, user_id, **updates)
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")
    return {"categoria": cat}


@router.delete("/{categoria_id}")
async def remover(categoria_id: int, request: Request):
    user_id = _get_user_id(request)
    ok = db.delete_categoria(categoria_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")
    return {"ok": True}
