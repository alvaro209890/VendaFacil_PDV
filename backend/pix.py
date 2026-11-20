"""PIX — QR Code do PDV e PIX automático pelo Mercado Pago.

Dois caminhos:

1. **QR estático (sem confirmação automática)**: ``POST /qrcode`` monta um BR Code com
   a chave PIX da loja e ``txid`` aleatório. Quem marca "pago" é o operador
   (comportamento antigo, mantido quando a loja não usa o Mercado Pago).

2. **Mercado Pago (automático)**: ``POST /mp/cobranca`` cria um pagamento PIX no
   Mercado Pago com ``external_reference`` = ``venda-<hex>`` e devolve o QR. O PDV faz
   polling em ``GET /mp/cobranca/{id}``; quando o MP marca ``approved`` ele chama
   ``POST /mp/cobranca/{id}/confirmar`` e o backend **reconfere no MP e fecha a venda
   sozinho** (baixa estoque, registra no caixa) — sem clique. Valor pago é conferido
   contra o total ou a parcela PIX, e cada pagamento só pode vincular uma venda.
"""

import io
import os
import base64
import json
import logging
import re
import secrets
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any

import qrcode
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth import _verificar_jwt, _agora
from database import db

router = APIRouter()
logger = logging.getLogger("vendafacil.pix")

# Fallback por env (compatibilidade); a config da loja (banco) tem prioridade.
_PIX_KEY_ENV = os.environ.get("VENDAFACIL_PIX_KEY", "")
_MERCHANT_NAME_ENV = os.environ.get("VENDAFACIL_MERCHANT_NAME", "VendaFacil PDV")
_MERCHANT_CITY_ENV = os.environ.get("VENDAFACIL_MERCHANT_CITY", "Querencia")

_MP_BASE = "https://api.mercadopago.com"
_MP_TIMEOUT = 30


def _pix_config() -> tuple[str, str, str]:
    """Resolve chave/nome/cidade do PIX: banco (config da loja) → env."""
    cfg = db.get_config_loja()
    chave = (cfg.get("pix_chave") or _PIX_KEY_ENV).strip()
    nome = (cfg.get("pix_nome") or _MERCHANT_NAME_ENV).strip() or "VendaFacil PDV"
    cidade = (cfg.get("pix_cidade") or _MERCHANT_CITY_ENV).strip() or "Querencia"
    return chave, nome, cidade


def _mp_config() -> tuple[str, int]:
    """Token e id do usuário Mercado Pago (o mesmo token da maquininha)."""
    cfg = db.get_config_maquininha()
    token = (cfg.get("access_token") or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Mercado Pago nao configurado (access token vazio).")
    try:
        mp_user = int(cfg.get("mp_user_id") or 0)
    except (TypeError, ValueError):
        mp_user = 0
    return token, mp_user


def _get_user_id(request: Request) -> int:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não informado.")
    payload = _verificar_jwt(auth[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return int(payload["sub"])


# ── BR Code / PIX Payload ──


def _emv_texto(valor: str, limite: int, padrao: str) -> str:
    """Nome e cidade do BR Code são ASCII, sem acento."""
    sem_acento = unicodedata.normalize("NFD", valor or "")
    sem_acento = "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")
    limpo = re.sub(r"[^A-Za-z0-9 ]", " ", sem_acento).upper()
    limpo = re.sub(r" +", " ", limpo).strip()
    return (limpo or padrao)[:limite]


def _tlv(tag: str, value: str) -> str:
    """Codifica um campo TLV (Tag-Length-Value) no formato EMV."""
    length = len(value.encode("utf-8"))
    return f"{tag}{length:02d}{value}"


def _crc16(payload: str) -> str:
    """Calcula CRC16-CCITT (polynomial 0x1021) sobre o payload."""
    data = payload.encode("utf-8")
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return f"{crc:04X}"


def gerar_payload(
    chave_pix: str,
    valor: float,
    nome: str = "VendaFacil PDV",
    cidade: str = "Querencia",
    txid: str = "***",
    descricao: str = "",
    nome_recebedor: str = "",
) -> str:
    """Gera um payload BR Code para PIX no padrão EMV QR Code do BACEN.

    Com ``nome_recebedor`` preenchido, o nome exibido no app do banco é o dele e o
    nome fantasia vai no campo 62/tag 07 — mesmo formato que o Mercado Pago devolve.
    """
    # 00 — Payload Format Indicator
    payload = _tlv("00", "01")

    # 26 — Merchant Account Information
    conta = _tlv("00", "BR.GOV.BCB.PIX") + _tlv("01", chave_pix)
    if descricao:
        conta += _tlv("02", _emv_texto(descricao, 72, "VENDA"))
    payload += _tlv("26", conta)

    # 52 — Merchant Category Code
    payload += _tlv("52", "0000")

    # 53 — Transaction Currency (986 = BRL)
    payload += _tlv("53", "986")

    # 54 — Transaction Amount
    payload += _tlv("54", f"{valor:.2f}")

    # 58 — Country Code
    payload += _tlv("58", "BR")

    # 59 — Merchant Name (até 25 chars, ASCII)
    payload += _tlv("59", _emv_texto(nome_recebedor or nome, 25, "VENDAS"))

    # 60 — Merchant City
    payload += _tlv("60", _emv_texto(cidade, 15, "QUERENCIA"))

    # 62 — Additional Data Field Template (txid + nome fantasia)
    adicionais = _tlv("05", txid[:25])
    if nome_recebedor and nome:
        adicionais += _tlv("07", _emv_texto(nome, 25, "VENDAS"))
    payload += _tlv("62", adicionais)

    # EMV: o cálculo inclui ID e tamanho do CRC (6304), excluindo seu valor.
    payload += "6304"
    return payload + _crc16(payload)


def gerar_qrcode_base64(payload: str) -> str:
    """Gera imagem QR Code a partir do payload e retorna como base64 (PNG)."""
    img = qrcode.make(payload, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ── Mercado Pago (PIX automático) ──


class _MPErro(Exception):
    def __init__(self, status: int, mensagem: str, detalhe: dict[str, Any] | None = None):
        self.status = status
        self.mensagem = mensagem
        self.detalhe = detalhe or {}
        super().__init__(mensagem)


def _mp_req(token: str, method: str, path: str, body: dict[str, Any] | None = None,
            *, idempotencia: str | None = None) -> dict[str, Any]:
    url = f"{_MP_BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": idempotencia or secrets.token_hex(16),
    }
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=_MP_TIMEOUT) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            resp = json.loads(e.read().decode() or "{}")
        except Exception:
            resp = {"message": str(e)}
        msg = resp.get("message") or resp.get("error") or resp.get("status_detail") or "Erro na API do Mercado Pago."
        logger.warning("mp_pix_error path=%s status=%s resp=%s", path, e.code,
                       json.dumps(resp, ensure_ascii=False)[:1500])
        raise _MPErro(e.code, msg, resp)
    except urllib.error.URLError as e:
        raise _MPErro(503, f"Sem conexao com o Mercado Pago: {e.reason}")


def _garantir_mp_user(token: str) -> int:
    """Descobre o ``collector_id`` (dono do token) e guarda na config."""
    _, mp_user = _mp_config()
    if mp_user:
        return mp_user
    me = _mp_req(token, "GET", "/users/me")
    mp_user = int(me.get("id") or 0)
    if mp_user:
        db.salvar_config_maquininha({"mp_user_id": mp_user}, _agora())
    return mp_user


def _chave_pix_mp(token: str) -> str:
    """Chave PIX da conta do Mercado Pago (quando a API pública expõe).

    É para onde o dinheiro cai de verdade: o QR tem de apontar para ela, senão o
    cliente paga numa chave e o PDV consulta pagamento em outra. A API de Methods não
    devolve a chave na conta de pessoa física (medido em 19/11/2026), então cai para
    a chave cadastrada na loja — que tem de ser a mesma da conta do MP.
    """
    try:
        lista = _mp_req(token, "GET", "/v1/payment_methods")
        alvo = next((c for c in lista if (c.get("id") or "").lower() == "pix"), None)
        for item in ((alvo or {}).get("data") or {}).get("keys") or []:
            if (item.get("status") or "").lower() in {"", "enabled", "active"}:
                chave = (item.get("key") or "").strip()
                if chave:
                    return chave
    except _MPErro as e:
        logger.warning("mp_pix_chave_indisponivel status=%s msg=%s", e.status, e.mensagem)
    chave_loja, _, _ = _pix_config()
    return chave_loja


def _emv_campos(payload: str) -> dict[str, str]:
    """Lê os campos TLV de um BR Code (tag → valor). Devolve {} se o formato não fechar."""
    campos: dict[str, str] = {}
    i = 0
    while i < len(payload):
        if i + 4 > len(payload):
            return {}
        tag = payload[i:i + 2]
        try:
            tam = int(payload[i + 2:i + 4])
        except ValueError:
            return {}
        valor = payload[i + 4:i + 4 + tam]
        if len(valor) != tam:
            return {}
        campos[tag] = valor
        i += 4 + tam
    return campos


def _payload_do_mp(pagamento: dict[str, Any], chave_mp: str = "") -> str:
    """Extrai o copia-e-cola do MP, remontando no padrão BACEN só quando o QR vier quebrado.

    Banco recusa QR com CRC errado. O teste é o parsing TLV de verdade — procurar
    "5405" no texto errava para valores de 4 dígitos (0.01 → tag 54 com tamanho 04).
    """
    td = ((pagamento.get("point_of_interaction") or {}).get("transaction_data")) or {}
    qr = td.get("qr_code") or ""
    if not qr:
        return ""
    campos = _emv_campos(qr)
    valor = pagamento.get("transaction_amount")
    remontar = (
        not qr.startswith("000201")
        or not campos
        or "26" not in campos
        or "54" not in campos
        or qr[-4:] != _crc16(qr[:-4])
    )
    if remontar and valor:
        chave, nome, cidade = _pix_config()
        chave = chave_mp or chave
        if not chave:
            return ""
        # Preserva o txid do MP quando existir: é o que amarra o QR ao pagamento.
        txid = (campos.get("62") and _emv_campos(campos["62"]).get("05")) or td.get("transaction_id") or "***"
        return gerar_payload(chave, float(valor), nome=nome, cidade=cidade, txid=str(txid)[:25])
    return qr


def _cobranca_publica(pagamento: dict[str, Any], chave_mp: str = "") -> dict[str, Any]:
    """Resumo seguro da cobrança para o PDV (sem token nem dado sensível)."""
    td = ((pagamento.get("point_of_interaction") or {}).get("transaction_data")) or {}
    status = (pagamento.get("status") or "").lower()
    return {
        "id": str(pagamento.get("id") or ""),
        "status": status,
        "status_detail": pagamento.get("status_detail") or "",
        "valor": pagamento.get("transaction_amount"),
        "aprovado": status == "approved",
        "encerrado": status in {"approved", "cancelled", "rejected", "refunded", "charged_back"},
        "payload": _payload_do_mp(pagamento, chave_mp),
        "qr_base64": td.get("qr_code_base64") or "",
        "expira_em": pagamento.get("date_of_expiration") or "",
    }


# ── Models ──


class PixQrCodeRequest(BaseModel):
    valor: float = Field(gt=0, le=999999.99)


class PixQrCodeResponse(BaseModel):
    payload: str
    qr_base64: str


class PixConfigInput(BaseModel):
    pix_chave: str | None = Field(default=None, max_length=120)
    pix_nome: str | None = Field(default=None, max_length=60)
    pix_cidade: str | None = Field(default=None, max_length=60)


class PixMpCobrancaInput(BaseModel):
    valor: float = Field(gt=0, le=999999.99)
    descricao: str | None = Field(default=None, max_length=120)
    venda_uuid: str | None = Field(default=None, max_length=64)


class PixMpConfirmarInput(BaseModel):
    itens: list[dict] = Field(default_factory=list)
    desconto: float = Field(default=0, ge=0)
    observacao: str = Field(default="", max_length=200)
    cliente_id: int | None = None
    cpf_consumidor: str | None = Field(default=None, max_length=14)
    emitir_nota: bool = False
    valor: float = Field(gt=0)


# ── Rotas: QR estático ──


@router.post("/qrcode")
async def gerar_qr_pix(data: PixQrCodeRequest, request: Request) -> PixQrCodeResponse:
    """Gera um QR Code PIX com o valor informado."""
    _get_user_id(request)

    chave, nome, cidade = _pix_config()
    if not chave:
        raise HTTPException(
            status_code=503,
            detail="Chave PIX não configurada. Configure em Configurações da Loja.",
        )

    payload = gerar_payload(chave_pix=chave, valor=data.valor, nome=nome, cidade=cidade,
                            txid=secrets.token_hex(8))
    qr = gerar_qrcode_base64(payload)
    return PixQrCodeResponse(payload=payload, qr_base64=qr)


@router.get("/chave")
async def obter_chave_pix(request: Request) -> dict:
    """Retorna se a chave PIX está configurada (sem expor o valor)."""
    _get_user_id(request)
    chave, _, _ = _pix_config()
    return {"configurada": bool(chave)}


@router.get("/config")
async def obter_config_pix(request: Request) -> dict:
    """Config do PIX da loja (a chave é da própria loja, exibida para conferência)."""
    _get_user_id(request)
    chave, nome, cidade = _pix_config()
    return {"config": {"pix_chave": chave, "pix_nome": nome, "pix_cidade": cidade}}


@router.put("/config")
async def salvar_config_pix(data: PixConfigInput, request: Request) -> dict:
    _get_user_id(request)
    cfg = db.salvar_config_loja(data.model_dump(exclude_none=True), _agora())
    return {"config": {
        "pix_chave": cfg.get("pix_chave", ""),
        "pix_nome": cfg.get("pix_nome", ""),
        "pix_cidade": cfg.get("pix_cidade", ""),
    }}


# ── Rotas: Mercado Pago (confirmação automática) ──


@router.get("/mp/status")
async def mp_status(request: Request) -> dict:
    """Diz se o PIX automático está pronto (token do MP + chave PIX para receber)."""
    _get_user_id(request)
    cfg = db.get_config_maquininha()
    token = bool((cfg.get("access_token") or "").strip())
    chave_loja, _, _ = _pix_config()
    chave_mp = ""
    origem = ""
    if token:
        try:
            chave_mp = _chave_pix_mp(cfg.get("access_token", ""))
        except Exception:
            chave_mp = ""
        if chave_mp and chave_mp != chave_loja:
            origem = "mercado_pago"
    if not origem and chave_loja:
        origem = "loja"
    return {
        "configurado": bool(token and (chave_mp or chave_loja)),
        "token_mp": token,
        "chave_pix": bool(chave_mp or chave_loja),
        "chave_origem": origem,
    }


@router.post("/mp/cobranca")
async def criar_cobranca_mp(data: PixMpCobrancaInput, request: Request) -> dict:
    """Cria o pagamento PIX no Mercado Pago e devolve o QR para o cliente."""
    _get_user_id(request)
    token, _mp_user = _mp_config()
    _garantir_mp_user(token)
    chave_mp = _chave_pix_mp(token)
    if not chave_mp:
        raise HTTPException(status_code=503, detail="Nenhuma chave PIX para receber (loja e Mercado Pago vazias).")
    # O Mercado Pago exige o pagador; com PIX não há e-mail do cliente no balcão,
    # então usamos o e-mail da própria conta como identificação da cobrança.
    payer_email = ""
    try:
        payer_email = (_mp_req(token, "GET", "/users/me").get("email") or "").strip()
    except _MPErro:
        payer_email = ""
    referencia = data.venda_uuid or f"venda-{secrets.token_hex(8)}"
    # MP exige yyyy-MM-dd'T'HH:mm:ss.SSSZ com offset sem dois-pontos (-0400).
    expira = (datetime.now().astimezone() + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S.000%z")
    body: dict[str, Any] = {
        "transaction_amount": round(float(data.valor), 2),
        "description": (data.descricao or "Venda PDV")[:120],
        "payment_method_id": "pix",
        "external_reference": referencia,
        "date_of_expiration": expira,
    }
    if payer_email:
        body["payer"] = {"email": payer_email}
    try:
        pagamento = _mp_req(token, "POST", "/v1/payments", body, idempotencia=data.venda_uuid)
    except _MPErro as e:
        raise HTTPException(status_code=e.status, detail=e.mensagem)
    logger.info("pix_mp_cobranca_created payment_id=%s ref=%s valor=%s",
                pagamento.get("id"), referencia, data.valor)
    out = _cobranca_publica(pagamento, chave_mp)
    out["referencia"] = referencia
    return out


@router.get("/mp/cobranca/{payment_id}")
async def consultar_cobranca_mp(payment_id: str, request: Request) -> dict:
    _get_user_id(request)
    token, _mp_user = _mp_config()
    safe_id = urllib.parse.quote(payment_id, safe="")
    try:
        pagamento = _mp_req(token, "GET", f"/v1/payments/{safe_id}")
    except _MPErro as e:
        raise HTTPException(status_code=e.status, detail=e.mensagem)
    return _cobranca_publica(pagamento)


def verificar_pagamento_mp(payment_id: str) -> tuple[dict, dict]:
    """Confirma no Mercado Pago a forma, aprovação e valor a conciliar."""
    token, _mp_user = _mp_config()
    safe_id = urllib.parse.quote(payment_id, safe="")
    try:
        pagamento = _mp_req(token, "GET", f"/v1/payments/{safe_id}")
    except _MPErro as e:
        raise HTTPException(status_code=e.status, detail=e.mensagem)

    info = _cobranca_publica(pagamento)
    if not info["aprovado"]:
        raise HTTPException(
            status_code=409,
            detail=f"PIX ainda nao aprovado (status: {info['status'] or 'desconhecido'}).",
        )

    if pagamento.get("payment_method_id") != "pix" or str(pagamento.get("id")) != payment_id:
        raise HTTPException(status_code=409, detail="Pagamento PIX não confirmado.")
    cfg = db.get_config_maquininha()
    dados_transacao = (pagamento.get("point_of_interaction") or {}).get("transaction_data") or {}
    return {
        "id": payment_id,
        "valor": float(pagamento.get("transaction_amount") or 0),
        "referencia": pagamento.get("external_reference") or payment_id,
        "detalhe": {
            "tipo_integracao": "1",
            "adquirente_cnpj": cfg.get("adquirente_cnpj") or "",
            "bandeira": "pix",
            "autorizacao": dados_transacao.get("end_to_end_id") or dados_transacao.get("e2e_id") or payment_id,
            "payment_id": payment_id,
        },
    }, info


@router.post("/mp/cobranca/{payment_id}/confirmar")
async def confirmar_venda_mp(payment_id: str, data: PixMpConfirmarInput, request: Request) -> dict:
    """Fecha a venda de PIX único pelo mesmo checkout usado nas vendas divididas."""
    _get_user_id(request)
    from vendas import CheckoutRequest, ItemVenda, PagamentoEletronico, checkout

    pagamento, info = verificar_pagamento_mp(payment_id)
    req = CheckoutRequest(
        itens=[ItemVenda(**i) for i in data.itens],
        desconto=data.desconto,
        forma_pagamento="pix",
        observacao=data.observacao,
        cliente_id=data.cliente_id,
        cpf_consumidor=data.cpf_consumidor,
        emitir_nota=data.emitir_nota,
        pagamento=PagamentoEletronico(**pagamento["detalhe"]),
    )
    resp = await checkout(req, request, pix_mp=pagamento)
    return {**resp, "pix": info, "ja_confirmada": bool(resp.get("reusada"))}
