"""Hashing de senha (PBKDF2) e tokens JWT HS256 — compartilhado pelo painel."""
import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

from database import DATA_DIR


def _resolver_jwt_secret() -> bytes:
    env = os.environ.get("PAINEL_JWT_SECRET")
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


def hash_senha(senha: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt.encode(), 200_000)
    return f"{salt}${h.hex()}"


def verificar_senha(senha: str, hash_str: str) -> bool:
    try:
        salt, stored = hash_str.split("$", 1)
    except ValueError:
        return False
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt.encode(), 200_000)
    return hmac.compare_digest(h.hex(), stored)


def gerar_jwt(payload: dict, horas: int = 24) -> str:
    dados = dict(payload)
    agora = datetime.now(timezone.utc)
    dados.setdefault("iat", int(agora.timestamp()))
    dados.setdefault("exp", int((agora + timedelta(hours=horas)).timestamp()))
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(dados).encode()).rstrip(b"=").decode()
    sig = base64.urlsafe_b64encode(
        hmac.new(JWT_SECRET, f"{header}.{body}".encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{header}.{body}.{sig}"


def verificar_jwt(token: str) -> dict | None:
    try:
        header, body, sig = token.split(".")
        esperado = base64.urlsafe_b64encode(
            hmac.new(JWT_SECRET, f"{header}.{body}".encode(), hashlib.sha256).digest()
        ).rstrip(b"=").decode()
        if not hmac.compare_digest(sig, esperado):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
            return None
        return payload
    except Exception:
        return None
