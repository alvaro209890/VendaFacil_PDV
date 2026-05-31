import os
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from database import db
from paths import DATA_DIR

router = APIRouter()


def _resolver_jwt_secret() -> bytes:
    """Segredo do JWT estável entre reinícios.

    1. VENDAFACIL_JWT_SECRET (env) — preferível no Render/servidor.
    2. Arquivo persistido em DATA_DIR — gerado uma vez no primeiro boot.
    Sem isso, um segredo novo a cada reinício deslogaria todos os usuários.
    """
    env = os.environ.get("VENDAFACIL_JWT_SECRET")
    if env:
        return env.encode()
    key_file = DATA_DIR / "jwt_secret.key"
    if key_file.exists():
        return key_file.read_text().strip().encode()
    novo = secrets.token_hex(32)
    key_file.write_text(novo)
    try:
        os.chmod(key_file, 0o600)
    except OSError:
        pass
    return novo.encode()


JWT_SECRET = _resolver_jwt_secret()
TOKEN_EXPIRE_HOURS = 720  # 30 dias

# ── Models ──

class LoginRequest(BaseModel):
    usuario: str | None = Field(default=None, min_length=3, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=120)
    senha: str = Field(min_length=1, max_length=128)

class RegistroRequest(BaseModel):
    usuario: str | None = Field(default=None, min_length=3, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=120)
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


def _usuario(data: LoginRequest | RegistroRequest) -> str:
    valor = (data.usuario or data.email or "").strip().lower()
    if not valor:
        raise HTTPException(status_code=422, detail="Usuário não informado.")
    return valor


def _user_response(user: dict) -> dict:
    usuario = user.get("usuario") or user.get("email", "")
    return {"id": user["id"], "usuario": usuario, "email": usuario, "nome": user["nome"]}


def _token_user(user: dict) -> dict:
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    usuario = user.get("usuario") or user.get("email")
    return {
        "sub": str(user["id"]),
        "usuario": usuario,
        "email": usuario,
        "nome": user["nome"],
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(exp.timestamp()),
    }

# ── Rotas ──

@router.post("/login")
async def login(data: LoginRequest) -> dict:
    import conta as conta_mod
    usuario = _usuario(data)

    if conta_mod.licenca_obrigatoria():
        try:
            st = conta_mod.ativar(usuario, data.senha)
            if st.get("bloqueado"):
                raise HTTPException(status_code=403, detail=st.get("motivo", "Conta bloqueada."))
            user = db.upsert_user(usuario, st.get("nome_loja") or usuario, _hash_senha(data.senha), _agora())
        except ConnectionError as exc:
            st = conta_mod.status()
            if st.get("bloqueado"):
                raise HTTPException(status_code=403, detail=str(exc))
            user = db.get_user_by_usuario(usuario)
            if not user or not _verificar_senha(data.senha, user["senha_hash"]):
                raise HTTPException(status_code=503, detail="Sem internet. Faça o primeiro login online com a conta do painel.")
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc))
    else:
        user = db.get_user_by_usuario(usuario)
        if not user or not _verificar_senha(data.senha, user["senha_hash"]):
            raise HTTPException(status_code=401, detail="Usuário ou senha incorretos.")

    db.update_last_login(usuario, _agora())
    token = _gerar_jwt(_token_user(user))
    return {"token": token, "user": _user_response(user)}

@router.post("/registro")
async def registro(data: RegistroRequest) -> dict:
    import conta as conta_mod
    if conta_mod.licenca_obrigatoria():
        raise HTTPException(status_code=403, detail="Registro local desativado. Use o usuário criado no painel.")
    lic = conta_mod.status()
    if lic.get("bloqueado"):
        raise HTTPException(status_code=403, detail=lic.get("motivo", "Sistema não ativado."))

    usuario = _usuario(data)
    if data.senha.lower() in ("senha", "1234", "12345", "123456", "password", usuario):
        raise HTTPException(status_code=400, detail="Senha muito fraca.")

    hash_senha = _hash_senha(data.senha)
    user = db.create_user(usuario, data.nome, hash_senha, _agora())
    if not user:
        raise HTTPException(status_code=409, detail="Este usuário já está cadastrado.")

    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    token = _gerar_jwt({
        "sub": str(user["id"]),
        "usuario": user.get("usuario") or user.get("email"),
        "email": user.get("usuario") or user.get("email"),
        "nome": user["nome"],
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(exp.timestamp()),
    })
    return {"token": token, "user": _user_response(user)}

@router.get("/me")
async def me(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não informado.")
    payload = _verificar_jwt(auth[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    usuario = payload.get("usuario") or payload.get("email", "")
    return {"user": {"id": payload["sub"], "usuario": usuario, "email": usuario, "nome": payload["nome"]}}
