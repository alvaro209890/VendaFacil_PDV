"""Tratamento central de erros e logs do VendaFacil PDV."""
from __future__ import annotations

import json
import logging
import sys
import uuid
from logging.handlers import RotatingFileHandler
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status

from paths import DATA_DIR

LOG_DIR = DATA_DIR / "logs"
LOG_FILE = LOG_DIR / "vendafacil.log"

SENSITIVE_KEYS = {
    "authorization",
    "senha",
    "password",
    "token",
    "gateway_token",
    "csc",
    "certificado_a1_b64",
    "certificado_senha",
    "resp_tec_csrt",
    "access_token",
}

FIELD_LABELS = {
    "body": "Dados enviados",
    "query": "Parâmetros",
    "path": "Rota",
    "nome": "Nome",
    "telefone": "Telefone",
    "email": "E-mail",
    "endereco": "Endereço",
    "documento": "CPF/CNPJ",
    "inscricao_estadual": "Inscrição Estadual",
    "indicador_ie": "Indicador IE",
    "logradouro": "Logradouro",
    "numero": "Número",
    "bairro": "Bairro",
    "municipio": "Município",
    "codigo_municipio": "Código IBGE do município",
    "uf": "UF",
    "cep": "CEP",
    "cnpj": "CNPJ",
    "razao_social": "Razão social",
    "nome_fantasia": "Nome fantasia",
    "regime_tributario": "Regime tributário",
    "serie": "Série",
    "serie_nfce": "Série NFC-e",
    "proximo_numero_nfce": "Próx. NFC-e",
    "serie_nfe": "Série NF-e",
    "proximo_numero_nfe": "Próx. NF-e",
    "valor": "Valor",
    "valor_total": "Valor total",
    "quantidade": "Quantidade",
    "preco_venda": "Preço de venda",
    "preco_custo": "Preço de custo",
    "estoque": "Estoque",
    "estoque_minimo": "Estoque mínimo",
    "cpf_consumidor": "CPF do consumidor",
    "justificativa": "Justificativa",
}


def configure_error_logging() -> None:
    """Configura log em arquivo rotativo e console quando houver console."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if not any(getattr(h, "baseFilename", None) == str(LOG_FILE) for h in root.handlers):
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=1_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        ))
        root.addHandler(file_handler)

    if sys.stderr is not None and not any(getattr(h, "_vf_console", False) for h in root.handlers):
        console_handler = logging.StreamHandler()
        console_handler._vf_console = True  # type: ignore[attr-defined]
        console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        root.addHandler(console_handler)


def register_error_handlers(app: FastAPI) -> None:
    logger = logging.getLogger("vendafacil.api")

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = _request_id(request)
        campos = [_format_validation_error(err) for err in exc.errors()]
        erros = [c["mensagem"] for c in campos]
        logger.warning(
            "validation_error request_id=%s method=%s path=%s errors=%s body=%s",
            request_id,
            request.method,
            request.url.path,
            json.dumps(campos, ensure_ascii=False),
            _safe_json(getattr(exc, "body", None)),
        )
        return _json_error(
            422,
            {
                "codigo": "validacao",
                "mensagem": "Revise os campos destacados.",
                "erros": erros,
                "campos": campos,
                "request_id": request_id,
            },
            request_id,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = _request_id(request)
        level = logging.ERROR if exc.status_code >= 500 else logging.INFO
        logger.log(
            level,
            "http_error request_id=%s status=%s method=%s path=%s detail=%s",
            request_id,
            exc.status_code,
            request.method,
            request.url.path,
            _safe_json(exc.detail),
        )
        return _json_error(exc.status_code, exc.detail, request_id)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = _request_id(request)
        logger.exception(
            "unhandled_error request_id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
        )
        return _json_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {
                "codigo": "erro_interno",
                "mensagem": "Erro interno do sistema. Tente novamente ou envie o código do erro ao suporte.",
                "erros": [f"Erro interno. Código: {request_id}"],
                "request_id": request_id,
            },
            request_id,
        )


def _request_id(request: Request) -> str:
    incoming = request.headers.get("X-Request-ID")
    return incoming.strip() if incoming else uuid.uuid4().hex[:12]


def _json_error(status_code: int, detail: Any, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


def _field_name(loc: Any) -> str:
    if not isinstance(loc, (list, tuple)):
        return str(loc)
    parts = [str(p) for p in loc if p not in ("body", "query", "path")]
    return ".".join(parts) if parts else "body"


def _label(field: str) -> str:
    last = field.split(".")[-1]
    return FIELD_LABELS.get(last, last.replace("_", " ").capitalize())


def _format_validation_error(error: dict[str, Any]) -> dict[str, str]:
    field = _field_name(error.get("loc", "body"))
    label = _label(field)
    err_type = str(error.get("type", ""))
    ctx = error.get("ctx") or {}

    if err_type == "missing":
        msg = f"{label} é obrigatório."
    elif err_type == "string_too_long":
        max_len = ctx.get("max_length")
        msg = f"{label} deve ter no máximo {max_len} caracteres."
        if field.endswith("cep"):
            msg += " Use 78643-000 ou apenas os 8 números."
    elif err_type == "string_too_short":
        min_len = ctx.get("min_length")
        msg = f"{label} deve ter no mínimo {min_len} caracteres."
    elif err_type == "greater_than":
        msg = f"{label} deve ser maior que {ctx.get('gt')}."
    elif err_type == "greater_than_equal":
        msg = f"{label} deve ser maior ou igual a {ctx.get('ge')}."
    elif err_type == "less_than_equal":
        msg = f"{label} deve ser menor ou igual a {ctx.get('le')}."
    elif err_type in {"int_parsing", "int_type"}:
        msg = f"{label} deve ser um número inteiro."
    elif err_type in {"float_parsing", "float_type"}:
        msg = f"{label} deve ser um número válido."
    elif err_type in {"bool_parsing", "bool_type"}:
        msg = f"{label} deve ser sim ou não."
    elif err_type == "string_pattern_mismatch":
        msg = f"{label} está em formato inválido."
    else:
        msg = str(error.get("msg") or f"{label} está inválido.")

    return {"campo": field, "mensagem": msg, "tipo": err_type}


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_KEYS:
                clean[key] = "***"
            else:
                clean[key] = _sanitize(item)
        return clean
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")[:2000]
        except UnicodeDecodeError:
            return "<bytes>"
    if isinstance(value, str) and len(value) > 2000:
        return value[:2000] + "...<truncado>"
    return value


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(_sanitize(value), ensure_ascii=False, default=str)
    except Exception:
        return repr(value)
