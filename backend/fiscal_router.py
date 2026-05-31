"""Rotas de emissão de NFC-e."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

import fiscal
from auth import _verificar_jwt
from database import db

router = APIRouter()
nfe_router = APIRouter()


def _user(request: Request) -> int:
    a = request.headers.get("Authorization", "")
    payload = _verificar_jwt(a[7:]) if a.startswith("Bearer ") else None
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return int(payload["sub"])


class CancelarInput(BaseModel):
    justificativa: str = Field(min_length=15, max_length=255)


class EmitirInput(BaseModel):
    cpf_consumidor: str | None = Field(default=None, max_length=14)


@router.get("/venda/{venda_id}")
async def nota_da_venda(venda_id: int, request: Request) -> dict:
    _user(request)
    return {"nota": fiscal.anexar_qrcode(db.get_nota_por_venda(venda_id, "65"))}


@router.post("/venda/{venda_id}/emitir")
async def emitir(venda_id: int, data: EmitirInput, request: Request) -> dict:
    user_id = _user(request)
    try:
        return {"nota": fiscal.anexar_qrcode(fiscal.emitir_nfce(venda_id, user_id, cpf=data.cpf_consumidor))}
    except fiscal.FiscalError as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/{nota_id}/consultar")
async def consultar(nota_id: int, request: Request) -> dict:
    _user(request)
    try:
        return {"nota": fiscal.anexar_qrcode(fiscal.consultar_nfce(nota_id))}
    except fiscal.FiscalError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{nota_id}/cancelar")
async def cancelar(nota_id: int, data: CancelarInput, request: Request) -> dict:
    _user(request)
    try:
        return {"nota": fiscal.cancelar_nfce(nota_id, data.justificativa)}
    except fiscal.FiscalError as e:
        raise HTTPException(status_code=400, detail=str(e))


class EmitirNfeInput(BaseModel):
    cliente_id: int


@nfe_router.get("/venda/{venda_id}")
async def nfe_da_venda(venda_id: int, request: Request) -> dict:
    _user(request)
    return {"nota": db.get_nota_por_venda(venda_id, "55")}


@nfe_router.post("/venda/{venda_id}/emitir")
async def emitir_nfe(venda_id: int, data: EmitirNfeInput, request: Request) -> dict:
    user_id = _user(request)
    try:
        return {"nota": fiscal.emitir_nfe(venda_id, user_id, data.cliente_id)}
    except fiscal.FiscalError as e:
        raise HTTPException(status_code=400, detail=str(e))


@nfe_router.post("/{nota_id}/consultar")
async def consultar_nfe(nota_id: int, request: Request) -> dict:
    _user(request)
    try:
        return {"nota": fiscal.consultar_nfce(nota_id)}
    except fiscal.FiscalError as e:
        raise HTTPException(status_code=400, detail=str(e))
