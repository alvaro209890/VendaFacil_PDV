"""Maquininha Mercado Pago Point via Orders API.

O PDV cria uma order do tipo ``point`` para a terminal configurada. A Point
precisa estar em modo PDV para puxar a order da nuvem do Mercado Pago.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth import _verificar_jwt, _agora
from database import db
from paths import DATA_DIR

router = APIRouter()
logger = logging.getLogger("vendafacil.maquininha")

_BASE = "https://api.mercadopago.com"
_TIMEOUT = 30
_SENSIVEIS = {"access_token"}
_LOG_FILE = DATA_DIR / "logs" / "vendafacil.log"


class PointError(Exception):
    def __init__(self, status: int, mensagem: str, detalhe: dict[str, Any] | None = None):
        self.status = status
        self.mensagem = mensagem
        self.detalhe = detalhe or {}
        super().__init__(mensagem)


class MercadoPagoPoint:
    """Cliente minimo da Mercado Pago Point Orders API."""

    def __init__(self, access_token: str):
        if not access_token:
            raise PointError(503, "Access Token do Mercado Pago nao configurado.")
        self.token = access_token

    def _req(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        idempotency: bool = False,
    ) -> tuple[int, dict[str, Any]]:
        url = f"{_BASE}{path}"
        data = json.dumps(body).encode() if body is not None else None
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        if idempotency:
            headers["X-Idempotency-Key"] = str(uuid.uuid4())
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
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
            raise PointError(503, f"Sem conexao com o Mercado Pago: {e.reason}")

    def listar_dispositivos(self) -> list[dict[str, Any]]:
        """Lista as terminais Point da conta usando a API atual de terminals."""
        status, resp = self._req("GET", "/terminals/v1/list?limit=50&offset=0")
        if status >= 400:
            logger.warning("terminals_v1_list_failed status=%s resp=%s", status, _safe(resp))
            return self._listar_dispositivos_legado()
        return ((resp.get("data") or {}).get("terminals") or [])

    def _listar_dispositivos_legado(self) -> list[dict[str, Any]]:
        status, resp = self._req("GET", "/point/integration-api/devices")
        if status >= 400:
            _raise_point_error(status, resp, "point_devices_legacy_list")
        return resp.get("devices", [])

    def configurar_modo_pdv(self, device_id: str) -> None:
        body = {"terminals": [{"id": device_id, "operating_mode": "PDV"}]}
        status, resp = self._req("PATCH", "/terminals/v1/setup", body)
        if status >= 400:
            _raise_point_error(status, resp, "terminals_v1_setup")
        logger.info("point_operating_mode_pdv device_id=%s", device_id)

    def criar_cobranca(
        self,
        device_id: str,
        valor: Decimal,
        referencia: str,
        imprimir: bool,
        forma: str,
    ) -> dict[str, Any]:
        default_type = _forma_para_default_type(forma)
        body = {
            "type": "point",
            "external_reference": referencia,
            "description": "VendaFacil PDV",
            "expiration_time": "PT10M",
            "transactions": {
                "payments": [{"amount": _money(valor)}],
            },
            "config": {
                "point": {
                    "terminal_id": device_id,
                    # Mantem o payload igual ao exemplo oficial do Mercado Pago
                    # enquanto diagnosticamos terminals que ficam em "created".
                    "print_on_terminal": "no_ticket",
                },
                "payment_method": {"default_type": default_type},
            },
        }
        status, resp = self._req("POST", "/v1/orders", body, idempotency=True)
        logger.info(
            "point_order_create status=%s device_id=%s forma=%s order_id=%s order_status=%s",
            status,
            device_id,
            forma,
            resp.get("id"),
            resp.get("status"),
        )
        if status >= 400:
            _raise_point_error(status, resp, "orders_create")
        return resp

    def consultar_cobranca(self, order_id: str) -> dict[str, Any]:
        safe_id = urllib.parse.quote(order_id, safe="")
        status, resp = self._req("GET", f"/v1/orders/{safe_id}")
        if status >= 400:
            _raise_point_error(status, resp, "orders_get")
        return resp

    def cancelar_cobranca(self, order_id: str) -> dict[str, Any]:
        safe_id = urllib.parse.quote(order_id, safe="")
        status, resp = self._req("POST", f"/v1/orders/{safe_id}/cancel", idempotency=True)
        if status >= 400:
            _raise_point_error(status, resp, "orders_cancel")
        return resp

    def consultar_pagamento(self, payment_id: str) -> dict[str, Any]:
        """Detalhe do pagamento (Payments API) — traz authorization_code/bandeira
        que a Orders API nem sempre devolve. Melhor-esforço: não levanta erro."""
        safe_id = urllib.parse.quote(str(payment_id), safe="")
        status, resp = self._req("GET", f"/v1/payments/{safe_id}")
        if status >= 400:
            logger.info("payment_get_failed status=%s payment_id=%s", status, payment_id)
            return {}
        return resp


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
    forma: str | None = Field(default=None, max_length=12)  # credito | debito


def _auth(request: Request) -> int:
    a = request.headers.get("Authorization", "")
    payload = _verificar_jwt(a[7:]) if a.startswith("Bearer ") else None
    if not payload:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado.")
    return int(payload["sub"])


def _mascarar(cfg: dict) -> dict:
    out = dict(cfg)
    for k in _SENSIVEIS:
        if out.get(k):
            out[k + "_preenchido"] = True
            out[k] = ""
    return out


def _msg(resp: dict[str, Any]) -> str:
    return (
        resp.get("message")
        or resp.get("error")
        or resp.get("status_detail")
        or "Erro na API do Mercado Pago."
    )


def _friendly_msg(status: int, resp: dict[str, Any]) -> str:
    if status == 409:
        return "Ja existe uma cobranca pendente na Point. Cancele, aguarde expirar ou tente novamente em instantes."
    return _msg(resp)


def _raise_point_error(status: int, resp: dict[str, Any], context: str) -> None:
    if status in {400, 409, 412} or status >= 500:
        logger.warning(
            "mercadopago_error context=%s status=%s response=%s",
            context,
            status,
            _safe(resp, limit=6000),
        )
    raise PointError(status, _friendly_msg(status, resp), resp)


def _safe(resp: dict[str, Any], limit: int = 1000) -> str:
    try:
        return json.dumps(resp, ensure_ascii=False, default=str)[:limit]
    except Exception:
        return repr(resp)


def _cliente() -> MercadoPagoPoint:
    cfg = db.get_config_maquininha()
    if not cfg.get("habilitado"):
        raise HTTPException(status_code=503, detail="Maquininha nao habilitada nas configuracoes.")
    try:
        return MercadoPagoPoint(cfg.get("access_token", ""))
    except PointError as e:
        raise HTTPException(status_code=e.status, detail=e.mensagem)


def _forma_para_default_type(forma: str | None) -> str:
    f = (forma or "credito").lower()
    if f == "debito":
        return "debit_card"
    if f == "credito":
        return "credit_card"
    raise PointError(
        400,
        "Maquininha configurada apenas para cartao de credito/debito. Para PIX, use o QR Code do PDV.",
    )


def _money(valor: Decimal) -> str:
    return str(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _valor_decimal(valor: float) -> Decimal:
    return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _payment(order: dict[str, Any]) -> dict[str, Any]:
    payments = ((order.get("transactions") or {}).get("payments") or [])
    return payments[0] if payments else {}


def _state(order: dict[str, Any]) -> str:
    status = (order.get("status") or "").lower()
    status_detail = (order.get("status_detail") or "").lower()
    payment_status = (_payment(order).get("status") or "").lower()

    if status in {"processed", "paid"} or payment_status in {"approved", "processed", "accredited"}:
        return "FINISHED"
    if status in {"at_terminal", "on_terminal"} or status_detail in {"at_terminal", "on_terminal"}:
        return "ON_TERMINAL"
    if status in {"expired", "canceled", "cancelled"}:
        return "CANCELED"
    if status in {"failed", "error"}:
        return "ERROR"
    if status in {"processing", "action_required"}:
        return "PROCESSING"
    return "OPEN"


def _payment_status_front(order: dict[str, Any]) -> str | None:
    payment_status = (_payment(order).get("status") or "").lower()
    if _state(order) == "FINISHED":
        return "approved"
    return payment_status or order.get("status")


def _payment_type_front(order: dict[str, Any]) -> str | None:
    payment = _payment(order)
    method = (order.get("config") or {}).get("payment_method") or {}
    return payment.get("type") or method.get("default_type")


def _autorizacao(pay: dict[str, Any]) -> str | None:
    """Procura o código de autorização (cAut) em locais conhecidos do payload."""
    for caminho in (
        ("authorization_code",),
        ("payment_method", "authorization_code"),
        ("transaction_details", "authorization_code"),
        ("point_of_interaction", "transaction_data", "authorization_code"),
    ):
        cur: Any = pay
        for chave in caminho:
            cur = cur.get(chave) if isinstance(cur, dict) else None
            if cur is None:
                break
        if cur:
            return str(cur)
    return None


def _bandeira(pay: dict[str, Any]) -> str | None:
    """Bandeira do cartão (ex.: master, visa, elo). Normalizada no fiscal_direto."""
    return (
        (pay.get("payment_method") or {}).get("id")
        or pay.get("payment_method_id")
        or ((pay.get("payment_method") or {}).get("card") or {}).get("brand")
    )


def dados_fiscais_pagamento(order: dict[str, Any], cli: "MercadoPagoPoint | None" = None) -> dict[str, Any]:
    """Monta o vínculo do pagamento eletrônico (Portaria 262/2023-MT) a partir da
    order da Point: tipo_integracao, CNPJ da credenciadora, bandeira (tBand) e
    autorização (cAut). Best-effort — consulta a Payments API só p/ achar o cAut."""
    pay = _payment(order)
    cAut = _autorizacao(pay)
    bandeira = _bandeira(pay)
    payment_id = pay.get("id")
    if (not cAut or not bandeira) and payment_id and cli is not None:
        det = cli.consultar_pagamento(payment_id)
        if det:
            cAut = cAut or _autorizacao(det)
            bandeira = bandeira or _bandeira(det)
    cfg = db.get_config_maquininha()
    terminal = (order.get("config") or {}).get("point", {}).get("terminal_id")
    return {
        "tipo_integracao": "1",  # cobrança disparada e conciliada pelo PDV
        "adquirente_cnpj": cfg.get("adquirente_cnpj") or "",
        "bandeira": bandeira,
        "autorizacao": cAut,
        "payment_id": str(payment_id) if payment_id else None,
        "terminal": terminal,
    }


def _ultimas_orders_log(limit: int = 5) -> list[str]:
    if not _LOG_FILE.exists():
        return []
    try:
        text = _LOG_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    ids = re.findall(r"order_id=(ORD[A-Z0-9]+)", text)
    return list(dict.fromkeys(ids))[-limit:]


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
    _auth(request)
    cli = _cliente()
    try:
        return {"dispositivos": cli.listar_dispositivos()}
    except PointError as e:
        raise HTTPException(status_code=e.status, detail=e.mensagem)


@router.get("/diagnostico")
async def diagnostico(request: Request) -> dict:
    """Diagnostico operacional da Point configurada, sem criar cobranca."""
    _auth(request)
    cfg = db.get_config_maquininha()
    device_id = cfg.get("device_id") or ""
    cli = _cliente()
    try:
        dispositivos = cli.listar_dispositivos()
    except PointError as e:
        raise HTTPException(status_code=e.status, detail=e.mensagem)

    terminal = next((d for d in dispositivos if d.get("id") == device_id), None)
    ultimas_orders = _ultimas_orders_log()
    ultima_order_bruta = None
    if ultimas_orders:
        try:
            ultima_order_bruta = cli.consultar_cobranca(ultimas_orders[-1])
        except PointError as e:
            ultima_order_bruta = {"erro": e.mensagem, "status": e.status}

    return {
        "config": {
            "habilitado": bool(cfg.get("habilitado")),
            "device_id": device_id,
            "access_token_preenchido": bool(cfg.get("access_token")),
        },
        "terminal": terminal,
        "operating_mode": (terminal or {}).get("operating_mode"),
        "ultimas_orders": ultimas_orders,
        "ultima_order_bruta": ultima_order_bruta,
    }


@router.post("/cobranca")
async def criar_cobranca(data: CobrancaInput, request: Request) -> dict:
    _auth(request)
    referencia = data.venda_uuid or f"venda-{uuid.uuid4().hex[:8]}"
    forma = (data.forma or "credito").lower()
    if forma not in {"credito", "debito"}:
        raise HTTPException(
            status_code=400,
            detail="Maquininha configurada apenas para cartao de credito/debito. Para PIX, use o QR Code do PDV.",
        )

    cli = _cliente()
    cfg = db.get_config_maquininha()
    device_id = cfg.get("device_id") or ""
    if not device_id:
        raise HTTPException(status_code=400, detail="Device ID da maquininha nao configurado.")
    try:
        cli.configurar_modo_pdv(device_id)
        resp = cli.criar_cobranca(
            device_id,
            _valor_decimal(data.valor),
            referencia,
            bool(cfg.get("imprimir_comprovante", 1)),
            forma,
        )
    except PointError as e:
        raise HTTPException(status_code=e.status, detail=e.mensagem)

    return {
        "payment_intent_id": resp.get("id"),  # compatibilidade com o frontend
        "state": _state(resp),
        "device_id": (resp.get("config") or {}).get("point", {}).get("terminal_id", device_id),
    }


@router.get("/cobranca/{payment_intent_id}")
async def consultar_cobranca(payment_intent_id: str, request: Request) -> dict:
    _auth(request)
    cli = _cliente()
    try:
        resp = cli.consultar_cobranca(payment_intent_id)
    except PointError as e:
        raise HTTPException(status_code=e.status, detail=e.mensagem)
    pgto = _payment(resp)
    state = _state(resp)
    out = {
        "payment_intent_id": resp.get("id"),
        "state": state,
        "pago": state == "FINISHED",
        "payment_id": pgto.get("id"),
        "payment_status": _payment_status_front(resp),
        "payment_type": _payment_type_front(resp),
    }
    if state == "FINISHED":
        # Vínculo do pagamento eletrônico p/ a NFC-e (Portaria 262/2023-MT).
        out["pagamento_fiscal"] = dados_fiscais_pagamento(resp, cli)
    return out


@router.delete("/cobranca/{payment_intent_id}")
async def cancelar_cobranca(payment_intent_id: str, request: Request) -> dict:
    _auth(request)
    cli = _cliente()
    try:
        cli.cancelar_cobranca(payment_intent_id)
    except PointError as e:
        raise HTTPException(status_code=e.status, detail=e.mensagem)
    return {"cancelado": True}
