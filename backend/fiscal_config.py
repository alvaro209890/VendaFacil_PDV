"""Configuração fiscal do emitente (dados da loja + gateway NFC-e)."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth import _verificar_jwt, _agora
from database import db

router = APIRouter()

# Campos sensíveis que não devem voltar para o frontend por inteiro.
_SENSIVEIS = {"gateway_token", "csc", "certificado_a1_b64", "certificado_senha"}


def _auth(request: Request) -> int:
    a = request.headers.get("Authorization", "")
    if not a.startswith("Bearer ") or not _verificar_jwt(a[7:]):
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return int(_verificar_jwt(a[7:])["sub"])


class ConfigFiscalInput(BaseModel):
    habilitado: bool | None = None
    razao_social: str | None = Field(default=None, max_length=120)
    nome_fantasia: str | None = Field(default=None, max_length=120)
    cnpj: str | None = Field(default=None, max_length=18)
    inscricao_estadual: str | None = Field(default=None, max_length=20)
    regime_tributario: str | None = Field(default=None, max_length=1)  # 1=Simples
    logradouro: str | None = None
    numero: str | None = None
    bairro: str | None = None
    municipio: str | None = None
    codigo_municipio: str | None = Field(default=None, max_length=7)  # IBGE
    uf: str | None = Field(default=None, max_length=2)
    cep: str | None = Field(default=None, max_length=9)
    csc: str | None = None
    csc_id: str | None = None
    ambiente: str | None = None  # homologacao | producao
    gateway: str | None = None   # focusnfe | plugnotas
    provedor_fiscal: str | None = None  # sefaz_mt_direto | focusnfe legado
    gateway_token: str | None = None
    certificado_a1_b64: str | None = None
    certificado_senha: str | None = None
    certificado_nome: str | None = None
    certificado_validade: str | None = None
    serie: int | None = Field(default=None, ge=1)
    proximo_numero: int | None = Field(default=None, ge=1)
    serie_nfce: int | None = Field(default=None, ge=1)
    proximo_numero_nfce: int | None = Field(default=None, ge=1)
    serie_nfe: int | None = Field(default=None, ge=1)
    proximo_numero_nfe: int | None = Field(default=None, ge=1)


def _mascarar(cfg: dict) -> dict:
    out = dict(cfg)
    for k in _SENSIVEIS:
        if out.get(k):
            out[k + "_preenchido"] = True
            out[k] = ""
    out["provedor_fiscal"] = out.get("provedor_fiscal") or "sefaz_mt_direto"
    return out


@router.get("")
async def obter(request: Request) -> dict:
    _auth(request)
    return {"config": _mascarar(db.get_config_fiscal())}


@router.put("")
async def salvar(data: ConfigFiscalInput, request: Request) -> dict:
    _auth(request)
    campos = data.model_dump(exclude_none=True)
    if "habilitado" in campos:
        campos["habilitado"] = 1 if campos["habilitado"] else 0
    cfg = db.salvar_config_fiscal(campos, _agora())
    return {"config": _mascarar(cfg)}
