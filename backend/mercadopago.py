"""Maquininha Mercado Pago (Point) — cobrança no cartão pela máquina física.

O caixa cria uma "intenção de pagamento" (payment intent) para um dispositivo
Point já pareado à conta Mercado Pago da loja. A maquininha exibe o valor, o
cliente passa o cartão (crédito/débito) e o PDV consulta o status até concluir.

NÃO guardamos dados de cartão. Falamos só com a API do Mercado Pago usando o
Access Token da conta da loja (cadastrado na config). Tudo exige internet —
pagamento em cartão é online por natureza.

Docs: https://www.mercadopago.com.br/developers/pt/docs/mp-point/integration-api
"""
import json
import urllib.error
import urllib.request
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth import _verificar_jwt, _agora
from database import db

router = APIRouter()

_BASE = "https://api.mercadopago.com"
_TIMEOUT = 30
# Campos sensíveis que não voltam por inteiro para o frontend.
_SENSIVEIS = {"access_token"}


def _auth(request: Request) -> int:
    a = request.headers.get("Authorization", "")
    payload = _verificar_jwt(a[7:]) if a.startswith("Bearer ") else None
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return int(payload["sub"])


def _mascarar(cfg: dict) -> dict:
    out = dict(cfg)
    for k in _SENSIVEIS:
        if out.get(k):
            out[k + "_preenchido"] = True
            out[k] = ""
    return out


# ─────────────────────────── Cliente Point ───────────────────────────
class PointError(Exception):
    def __init__(self, status: int, mensagem: str):
        self.status = status
        self.mensagem = mensagem
        super().__init__(mensagem)


class MercadoPagoPoint:
    """Cliente mínimo da Integration API do Mercado Pago Point."""

    def __init__(self, access_token: str):
        if not access_token:
            raise PointError(503, "Access Token do Mercado Pago não configurado.")
        self.token = access_token

    def _req(self, method: str, path: str, body: Optional[dict] = None) -> tuple[int, dict]:
        url = f"{_BASE}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
                txt = r.read().decode() or "{}"
                return r.status, json.loads(txt)
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read().decode() or "{}")
            except Exception:
                return e.code, {"message": str(e)}
        except urllib.error.URLError as e:
            raise PointError(503, f"Sem conexão com o Mercado Pago: {e.reason}")

    # Lista os dispositivos Point pareados à conta (para descobrir o device_id).
    def listar_dispositivos(self) -> list[dict]:
        status, resp = self._req("GET", "/point/integration-api/devices")
        if status >= 400:
            raise PointError(status, _msg(resp))
        return resp.get("devices", [])

    # Cria a intenção de pagamento (a maquininha acende e pede o cartão).
    def criar_cobranca(self, device_id: str, valor_centavos: int,
                       referencia: str, imprimir: bool) -> dict:
        body = {
            "amount": valor_centavos,
            "additional_info": {
                "external_reference": referencia,
                "print_on_terminal": imprimir,
            },
        }
        status, resp = self._req(
            "POST", f"/point/integration-api/devices/{device_id}/payment-intents", body
        )
        if status >= 400:
            raise PointError(status, _msg(resp))
        return resp

    def consultar_cobranca(self, payment_intent_id: str) -> dict:
        status, resp = self._req(
            "GET", f"/point/integration-api/payment-intents/{payment_intent_id}"
        )
        if status >= 400:
            raise PointError(status, _msg(resp))
        return resp

    def cancelar_cobranca(self, device_id: str, payment_intent_id: str) -> dict:
        status, resp = self._req(
            "DELETE",
            f"/point/integration-api/devices/{device_id}/payment-intents/{payment_intent_id}",
        )
        if status >= 400:
            raise PointError(status, _msg(resp))
        return resp


def _msg(resp: dict) -> str:
    return resp.get("message") or resp.get("error") or "Erro na API do Mercado Pago."


def _cliente() -> MercadoPagoPoint:
    cfg = db.get_config_maquininha()
    if not cfg.get("habilitado"):
        raise HTTPException(status_code=503, detail="Maquininha não habilitada nas configurações.")
    try:
        return MercadoPagoPoint(cfg.get("access_token", ""))
    except PointError as e:
        raise HTTPException(status_code=e.status, detail=e.mensagem)


# ─────────────────────────── Models ───────────────────────────
class ConfigMaquininhaInput(BaseModel):
    habilitado: bool | None = None
    access_token: str | None = None
    device_id: str | None = Field(default=None, max_length=120)
    store_id: str | None = Field(default=None, max_length=60)
    pos_id: str | None = Field(default=None, max_length=60)
    imprimir_comprovante: bool | None = None


class CobrancaInput(BaseModel):
    valor: float = Field(gt=0, le=999999.99)
    venda_uuid: str | None = Field(default=None, max_length=64)


# ─────────────────────────── Rotas: configuração ───────────────────────────
@router.get("/config")
async def obter_config(request: Request) -> dict:
    _auth(request)
    return {"config": _mascarar(db.get_config_maquininha())}


@router.put("/config")
async def salvar_config(data: ConfigMaquininhaInput, request: Request) -> dict:
    _auth(request)
    campos = data.model_dump(exclude_none=True)
    for b in ("habilitado", "imprimir_comprovante"):
        if b in campos:
            campos[b] = 1 if campos[b] else 0
    cfg = db.salvar_config_maquininha(campos, _agora())
    return {"config": _mascarar(cfg)}


@router.get("/dispositivos")
async def listar_dispositivos(request: Request) -> dict:
    """Lista as maquininhas pareadas à conta — use para descobrir o device_id."""
    _auth(request)
    cli = _cliente()
    try:
        return {"dispositivos": cli.listar_dispositivos()}
    except PointError as e:
        raise HTTPException(status_code=e.status, detail=e.mensagem)


# ─────────────────────────── Rotas: cobrança ───────────────────────────
@router.post("/cobranca")
async def criar_cobranca(data: CobrancaInput, request: Request) -> dict:
    """Dispara a cobrança na maquininha. Retorna o id da intenção para consultar."""
    _auth(request)
    cli = _cliente()  # valida habilitado + access_token
    cfg = db.get_config_maquininha()
    device_id = cfg.get("device_id") or ""
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id da maquininha não configurado.")
    referencia = data.venda_uuid or "venda"
    valor_centavos = int(round(data.valor * 100))
    try:
        resp = cli.criar_cobranca(
            device_id, valor_centavos, referencia,
            bool(cfg.get("imprimir_comprovante", 1)),
        )
    except PointError as e:
        raise HTTPException(status_code=e.status, detail=e.mensagem)
    return {
        "payment_intent_id": resp.get("id"),
        "state": resp.get("state"),
        "device_id": resp.get("device_id", device_id),
    }


@router.get("/cobranca/{payment_intent_id}")
async def consultar_cobranca(payment_intent_id: str, request: Request) -> dict:
    """Consulta o status da cobrança (poll a cada ~2s até finalizar)."""
    _auth(request)
    cli = _cliente()
    try:
        resp = cli.consultar_cobranca(payment_intent_id)
    except PointError as e:
        raise HTTPException(status_code=e.status, detail=e.mensagem)
    pgto = resp.get("payment") or {}
    return {
        "payment_intent_id": resp.get("id"),
        "state": resp.get("state"),          # OPEN, ON_TERMINAL, PROCESSING, FINISHED, CANCELED...
        "pago": resp.get("state") == "FINISHED",
        "payment_id": pgto.get("id"),
        "payment_status": pgto.get("status"),
        "payment_type": pgto.get("type"),     # credit_card | debit_card
    }


@router.delete("/cobranca/{payment_intent_id}")
async def cancelar_cobranca(payment_intent_id: str, request: Request) -> dict:
    """Cancela uma cobrança ainda não concluída na maquininha."""
    _auth(request)
    cfg = db.get_config_maquininha()
    device_id = cfg.get("device_id") or ""
    cli = _cliente()
    try:
        cli.cancelar_cobranca(device_id, payment_intent_id)
    except PointError as e:
        raise HTTPException(status_code=e.status, detail=e.mensagem)
    return {"cancelado": True}
