import os
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from database import db

router = APIRouter()

JWT_SECRET = os.environ.get("VENDAFACIL_JWT_SECRET", secrets.token_hex(32)).encode()
TOKEN_EXPIRE_HOURS = 720  # 30 dias

# ── Models ──

class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=120)
    senha: str = Field(min_length=1, max_length=128)

class RegistroRequest(BaseModel):
    email: str = Field(min_length=3, max_length=120)
    nome: str = Field(min_length=1, max_length=80)
    senha: str = Field(min_length=4, max_length=128)

# ── Helpers ──

def _hash_senha(senha: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt.encode(), 200_000)
    return f"{salt}${h.hex()}"

def _verificar_senha(senha: str, hash_str: str) -> bool:
    salt, stored = hash_str.split("$", 1)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt.encode(), 200_000)
    return hmac.compare_digest(h.hex(), stored)

def _gerar_jwt(payload: dict) -> str:
    import base64, json
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    sig_raw = hmac.new(JWT_SECRET, f"{header}.{body}".encode(), hashlib.sha256).digest()
    sig = base64.urlsafe_b64encode(sig_raw).rstrip(b"=").decode()
    return f"{header}.{body}.{sig}"

def _verificar_jwt(token: str) -> dict | None:
    import base64, json
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, body, sig = parts
        expected = base64.urlsafe_b64encode(
            hmac.new(JWT_SECRET, f"{parts[0]}.{parts[1]}".encode(), hashlib.sha256).digest()
        ).rstrip(b"=").decode()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
            return None
        return payload
    except Exception:
        return None

def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()

# ── Rotas ──

@router.post("/login")
async def login(data: LoginRequest) -> dict:
    user = db.get_user_by_email(data.email)
    if not user or not _verificar_senha(data.senha, user["senha_hash"]):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")

    db.update_last_login(data.email, _agora())
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    token = _gerar_jwt({
        "sub": str(user["id"]),
        "email": user["email"],
        "nome": user["nome"],
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(exp.timestamp()),
    })
    return {"token": token, "user": {"id": user["id"], "email": user["email"], "nome": user["nome"]}}

@router.post("/registro")
async def registro(data: RegistroRequest) -> dict:
    if data.senha.lower() in ("senha", "1234", "12345", "123456", "password", data.email.split("@")[0].lower()):
        raise HTTPException(status_code=400, detail="Senha muito fraca.")

    hash_senha = _hash_senha(data.senha)
    user = db.create_user(data.email, data.nome, hash_senha, _agora())
    if not user:
        raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado.")

    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    token = _gerar_jwt({
        "sub": str(user["id"]),
        "email": user["email"],
        "nome": user["nome"],
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(exp.timestamp()),
    })
    return {"token": token, "user": {"id": user["id"], "email": user["email"], "nome": user["nome"]}}

@router.get("/me")
async def me(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não informado.")
    payload = _verificar_jwt(auth[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return {"user": {"id": payload["sub"], "email": payload["email"], "nome": payload["nome"]}}
