"""Produtos CRUD — VendaFácil PDV"""

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


# ── Models ──

class ProdutoCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    categoria_id: int | None = Field(default=None)
    preco_custo: float = Field(default=0, ge=0)
    preco_venda: float = Field(default=0, ge=0)
    estoque: int = Field(default=0, ge=0)
    estoque_minimo: int = Field(default=5, ge=0)
    codigo_barras: str = Field(default="", max_length=60)
    unidade: str = Field(default="UN", max_length=10)


class ProdutoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    categoria_id: int | None = Field(default=None)
    preco_custo: float | None = Field(default=None, ge=0)
    preco_venda: float | None = Field(default=None, ge=0)
    estoque: int | None = Field(default=None, ge=0)
    estoque_minimo: int | None = Field(default=None, ge=0)
    codigo_barras: str | None = Field(default=None, max_length=60)
    unidade: str | None = Field(default=None, max_length=10)
    ativo: int | None = Field(default=None, ge=0, le=1)


# ── Rotas ──

@router.get("")
async def listar(request: Request, ativos: bool = True):
    user_id = _get_user_id(request)
    return {"produtos": db.list_produtos(user_id, ativos_only=ativos)}


@router.get("/{produto_id}")
async def obter(produto_id: int, request: Request):
    user_id = _get_user_id(request)
    p = db.get_produto(produto_id, user_id)
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return {"produto": p}


@router.post("", status_code=201)
async def criar(data: ProdutoCreate, request: Request):
    user_id = _get_user_id(request)
    agora = _agora()
    p = db.create_produto(
        user_id=user_id,
        nome=data.nome,
        categoria_id=data.categoria_id,
        preco_custo=data.preco_custo,
        preco_venda=data.preco_venda,
        estoque=data.estoque,
        estoque_minimo=data.estoque_minimo,
        codigo_barras=data.codigo_barras,
        unidade=data.unidade,
        agora=agora,
    )
    return {"produto": p}


@router.put("/{produto_id}")
async def atualizar(produto_id: int, data: ProdutoUpdate, request: Request):
    user_id = _get_user_id(request)
    p = db.get_produto(produto_id, user_id)
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    updates["atualizado_em"] = _agora()
    p = db.update_produto(produto_id, user_id, **updates)
    return {"produto": p}


@router.delete("/{produto_id}")
async def desativar(produto_id: int, request: Request):
    """Desativa um produto (soft delete)."""
    user_id = _get_user_id(request)
    p = db.get_produto(produto_id, user_id)
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    db.update_produto(produto_id, user_id, ativo=0, atualizado_em=_agora())
    return {"ok": True}
