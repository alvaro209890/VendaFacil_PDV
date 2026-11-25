"""Rotas de cadastro fiscal — pendências do catálogo para a NFC-e.

`GET /pendencias` lista os produtos que impedem a emissão (NCM/CSOSN/CEST) com
a sugestão de NCM de um irmão do catálogo e quantas vendas dos últimos 30 dias
passaram por eles (para priorizar).

`POST /pendencias/corrigir` aplica **apenas as sugestões** (nunca inventa NCM) e
devolve quantos ficaram pendentes.

`PATCH /produtos/{id}` grava o que o lojista/contador informar.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

import fiscal_cadastro
from auth import _verificar_jwt
from database import db

router = APIRouter()


def _user(request: Request) -> int:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não informado.")
    payload = _verificar_jwt(auth[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return int(payload["sub"])


class CorrecaoInput(BaseModel):
    aplicar_sugestoes: bool = True


class ProdutoFiscalInput(BaseModel):
    ncm: str | None = Field(default=None, max_length=8)
    cest: str | None = Field(default=None, max_length=9)
    cst_csosn: str | None = Field(default=None, max_length=4)
    cfop: str | None = Field(default=None, max_length=4)


def _pendencias(user_id: int) -> list[dict]:
    produtos = db.listar_produtos(user_id)
    vendas = db.vendas_por_produto(user_id, dias=30)
    return fiscal_cadastro.analisar(produtos, vendas)


@router.get("/pendencias")
async def pendencias(request: Request) -> dict:
    user_id = _user(request)
    itens = _pendencias(user_id)
    return {
        "total": len(itens),
        "com_sugestao": sum(1 for i in itens if i["sugestao_ncm"]),
        "itens": itens,
    }


@router.post("/pendencias/corrigir")
async def corrigir(data: CorrecaoInput, request: Request) -> dict:
    user_id = _user(request)
    if not data.aplicar_sugestoes:
        raise HTTPException(status_code=400, detail="Nada para aplicar: confirme aplicar_sugestoes.")
    aplicados = 0
    for item in _pendencias(user_id):
        if not item["sugestao_ncm"]:
            continue
        campos = {"ncm": item["sugestao_ncm"]}
        if "cst_csosn" in item["faltando"]:
            campos["cst_csosn"] = "102"
        if db.atualizar_fiscal_produto(user_id, item["id"], campos):
            aplicados += 1
    restantes = _pendencias(user_id)
    return {
        "corrigidos": aplicados,
        "restantes": len(restantes),
        "itens": restantes,
    }


@router.patch("/produtos/{produto_id}")
async def corrigir_produto(produto_id: int, data: ProdutoFiscalInput, request: Request) -> dict:
    user_id = _user(request)
    campos = {k: v.strip() if isinstance(v, str) else v
              for k, v in data.model_dump(exclude_none=True).items()}
    if not campos:
        raise HTTPException(status_code=400, detail="Informe ao menos um campo fiscal.")
    produto = db.atualizar_fiscal_produto(user_id, produto_id, campos)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return {"produto": produto}
