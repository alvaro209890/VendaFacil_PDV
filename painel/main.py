"""Painel SaaS VendaFácil — roda na VPS (domínio próprio).

Você (admin) gerencia as contas das lojas (login/senha de cada mercado),
ativa/bloqueia e define validade de licença. Os PDVs (.exe) validam a conta
aqui e sincronizam as vendas.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from database import db
import security

app = FastAPI(title="VendaFácil — Painel SaaS", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


# ── Helpers ──
def _admin_atual(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não informado.")
    payload = security.verificar_jwt(auth[7:])
    if not payload or payload.get("tipo") != "admin":
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return payload


def _conta_atual(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não informado.")
    payload = security.verificar_jwt(auth[7:])
    if not payload or payload.get("tipo") != "conta":
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return payload


def _licenca_valida(conta: dict) -> tuple[bool, str]:
    if not conta.get("ativo"):
        return False, "Conta bloqueada. Entre em contato com o suporte."
    exp = conta.get("licenca_expira_em")
    if exp:
        try:
            venc = datetime.fromisoformat(exp)
            if venc.tzinfo is None:
                venc = venc.replace(tzinfo=timezone.utc)
            if venc < datetime.now(timezone.utc):
                return False, "Licença expirada. Renove para continuar."
        except ValueError:
            pass
    return True, "ok"


# ── Models ──
class AdminSetup(BaseModel):
    email: str = Field(min_length=3, max_length=120)
    nome: str = Field(min_length=1, max_length=80)
    senha: str = Field(min_length=6, max_length=128)


class AdminLogin(BaseModel):
    email: str
    senha: str


class ContaInput(BaseModel):
    nome_loja: str = Field(min_length=1, max_length=120)
    login: str = Field(min_length=3, max_length=60)
    senha: str = Field(min_length=4, max_length=128)
    plano: str = "mensal"
    licenca_expira_em: Optional[str] = None
    observacao: Optional[str] = None


class ContaUpdate(BaseModel):
    nome_loja: Optional[str] = None
    ativo: Optional[bool] = None
    plano: Optional[str] = None
    licenca_expira_em: Optional[str] = None
    observacao: Optional[str] = None
    nova_senha: Optional[str] = None


class ContaValidar(BaseModel):
    login: str
    senha: str


class VendaSync(BaseModel):
    uuid: str
    total: float
    desconto: float = 0
    forma_pagamento: Optional[str] = None
    criado_em: Optional[str] = None
    itens: Optional[list] = None


class SyncPayload(BaseModel):
    vendas: list[VendaSync] = []


# ── Health ──
@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "app": "vendafacil-painel", "version": app.version}


# ── Admin ──
@app.get("/api/admin/precisa-setup")
async def precisa_setup() -> dict:
    return {"precisa_setup": db.count_admins() == 0}


@app.post("/api/admin/setup")
async def admin_setup(data: AdminSetup) -> dict:
    if db.count_admins() > 0:
        raise HTTPException(status_code=403, detail="Admin já configurado.")
    admin = db.create_admin(data.email, data.nome, security.hash_senha(data.senha))
    if not admin:
        raise HTTPException(status_code=409, detail="E-mail já cadastrado.")
    token = security.gerar_jwt({"sub": str(admin["id"]), "tipo": "admin", "nome": admin["nome"]})
    return {"token": token, "admin": admin}


@app.post("/api/admin/login")
async def admin_login(data: AdminLogin) -> dict:
    admin = db.get_admin_by_email(data.email)
    if not admin or not security.verificar_senha(data.senha, admin["senha_hash"]):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")
    token = security.gerar_jwt({"sub": str(admin["id"]), "tipo": "admin", "nome": admin["nome"]})
    return {"token": token, "admin": {"id": admin["id"], "email": admin["email"], "nome": admin["nome"]}}


@app.get("/api/admin/contas")
async def listar_contas(request: Request) -> dict:
    _admin_atual(request)
    contas = db.listar_contas()
    for c in contas:
        c["resumo"] = db.resumo_vendas(c["id"])
        c["licenca_ok"], _ = _licenca_valida(c)
    return {"contas": contas}


@app.post("/api/admin/contas")
async def criar_conta(data: ContaInput, request: Request) -> dict:
    _admin_atual(request)
    conta = db.criar_conta(
        data.nome_loja, data.login, security.hash_senha(data.senha),
        data.plano, data.licenca_expira_em, data.observacao,
    )
    if not conta:
        raise HTTPException(status_code=409, detail="Esse login já existe.")
    conta.pop("senha_hash", None)
    return {"conta": conta}


@app.put("/api/admin/contas/{conta_id}")
async def atualizar_conta(conta_id: int, data: ContaUpdate, request: Request) -> dict:
    _admin_atual(request)
    if not db.get_conta(conta_id):
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    campos: dict = {}
    if data.nome_loja is not None:
        campos["nome_loja"] = data.nome_loja
    if data.ativo is not None:
        campos["ativo"] = 1 if data.ativo else 0
    if data.plano is not None:
        campos["plano"] = data.plano
    if data.licenca_expira_em is not None:
        campos["licenca_expira_em"] = data.licenca_expira_em or None
    if data.observacao is not None:
        campos["observacao"] = data.observacao
    if data.nova_senha:
        campos["senha_hash"] = security.hash_senha(data.nova_senha)
    db.atualizar_conta(conta_id, campos)
    return {"ok": True}


# ── PDV: validação de conta (login controlado centralmente) ──
@app.post("/api/conta/validar")
async def validar_conta(data: ContaValidar) -> dict:
    conta = db.get_conta_by_login(data.login)
    if not conta or not security.verificar_senha(data.senha, conta["senha_hash"]):
        raise HTTPException(status_code=401, detail="Login ou senha incorretos.")
    ok, motivo = _licenca_valida(conta)
    db.marcar_acesso(conta["id"])
    # Token de conta com validade longa = período de carência offline (30 dias)
    token = security.gerar_jwt(
        {"sub": str(conta["id"]), "tipo": "conta", "loja": conta["nome_loja"]},
        horas=24 * 30,
    )
    return {
        "ok": ok,
        "motivo": motivo,
        "conta": {
            "id": conta["id"],
            "nome_loja": conta["nome_loja"],
            "login": conta["login"],
            "ativo": bool(conta["ativo"]),
            "plano": conta["plano"],
            "licenca_expira_em": conta["licenca_expira_em"],
        },
        "token": token,
    }


# ── PDV: revalidação de licença por token (sem repetir senha) ──
@app.get("/api/conta/status")
async def conta_status(request: Request) -> dict:
    conta = _conta_atual(request)
    atual = db.get_conta(int(conta["sub"]))
    if not atual:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    ok, motivo = _licenca_valida(atual)
    db.marcar_acesso(atual["id"])
    return {
        "ok": ok,
        "motivo": motivo,
        "nome_loja": atual["nome_loja"],
        "ativo": bool(atual["ativo"]),
        "licenca_expira_em": atual["licenca_expira_em"],
    }


# ── PDV: sincronização de vendas ──
@app.post("/api/sync/vendas")
async def sync_vendas(data: SyncPayload, request: Request) -> dict:
    conta = _conta_atual(request)
    conta_id = int(conta["sub"])
    atual = db.get_conta(conta_id)
    if not atual:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    ok_lic, motivo = _licenca_valida(atual)
    recebidas = 0
    for v in data.vendas:
        if db.registrar_venda_sync(conta_id, v.model_dump()):
            recebidas += 1
    db.marcar_acesso(conta_id)
    return {"recebidas": recebidas, "licenca_ok": ok_lic, "motivo": motivo}


# ── UI Admin (estática) ──
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="assets")

    @app.get("/", include_in_schema=False)
    async def _admin_ui() -> FileResponse:
        return FileResponse(str(STATIC_DIR / "index.html"))
