"""Caixa — abertura, sangria/suprimento e fechamento do dia."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth import _verificar_jwt, _agora
from database import db

router = APIRouter()


def _get_user_id(request: Request) -> int:
    auth = request.headers.get("Authorization", "")
    payload = _verificar_jwt(auth[7:]) if auth.startswith("Bearer ") else None
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return int(payload["sub"])


class AbrirInput(BaseModel):
    valor_abertura: float = Field(default=0, ge=0)


class MovimentoInput(BaseModel):
    tipo: str  # sangria | suprimento
    valor: float = Field(gt=0)
    motivo: str = Field(default="", max_length=200)


class FecharInput(BaseModel):
    valor_fechamento: float = Field(ge=0)
    observacao: str = Field(default="", max_length=200)


@router.get("/atual")
async def atual(request: Request) -> dict:
    user_id = _get_user_id(request)
    sessao = db.get_caixa_aberto(user_id)
    if not sessao:
        return {"aberto": False}
    return {"aberto": True, "sessao": sessao, "resumo": db.resumo_caixa(sessao)}


@router.post("/abrir")
async def abrir(data: AbrirInput, request: Request) -> dict:
    user_id = _get_user_id(request)
    if db.get_caixa_aberto(user_id):
        raise HTTPException(status_code=409, detail="Já existe um caixa aberto. Feche-o antes de abrir outro.")
    sessao = db.abrir_caixa(user_id, data.valor_abertura, _agora())
    return {"aberto": True, "sessao": sessao, "resumo": db.resumo_caixa(sessao)}


@router.post("/movimento")
async def movimento(data: MovimentoInput, request: Request) -> dict:
    user_id = _get_user_id(request)
    if data.tipo not in ("sangria", "suprimento"):
        raise HTTPException(status_code=400, detail="Tipo deve ser 'sangria' ou 'suprimento'.")
    sessao = db.get_caixa_aberto(user_id)
    if not sessao:
        raise HTTPException(status_code=409, detail="Nenhum caixa aberto.")
    db.registrar_movimento_caixa(sessao["id"], user_id, data.tipo, data.valor, data.motivo, _agora())
    return {"resumo": db.resumo_caixa(sessao)}


@router.post("/fechar")
async def fechar(data: FecharInput, request: Request) -> dict:
    user_id = _get_user_id(request)
    sessao = db.get_caixa_aberto(user_id)
    if not sessao:
        raise HTTPException(status_code=409, detail="Nenhum caixa aberto.")
    resumo = db.resumo_caixa(sessao)
    esperado = resumo["dinheiro_esperado"]
    fechada = db.fechar_caixa(sessao["id"], data.valor_fechamento, esperado, _agora(), data.observacao)
    return {"sessao": fechada, "resumo": resumo}


@router.get("/historico")
async def historico(request: Request) -> dict:
    user_id = _get_user_id(request)
    return {"sessoes": db.list_caixa_historico(user_id)}
