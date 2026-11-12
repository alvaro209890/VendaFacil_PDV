"""Serviços fiscais solicitados explicitamente na tela de suporte fiscal."""
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from database import db
from fiscal_router import _user
import fiscal_direto

router = APIRouter()


@router.get('/status')
def status(request: Request, modelo: Literal['55', '65'] = '65') -> dict:
    _user(request)
    try:
        return fiscal_direto.status_servico(modelo, db.get_config_fiscal())
    except fiscal_direto.FiscalDiretoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
