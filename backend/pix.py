"""PIX / QR Code — Geração de payload BR Code e QR Code imagem"""

import io
import os
import base64
import struct
from typing import Optional

import qrcode
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth import _verificar_jwt, _agora
from database import db

router = APIRouter()

# Fallback por env (compatibilidade); a config da loja (banco) tem prioridade.
_PIX_KEY_ENV = os.environ.get("VENDAFACIL_PIX_KEY", "")
_MERCHANT_NAME_ENV = os.environ.get("VENDAFACIL_MERCHANT_NAME", "VendaFacil PDV")
_MERCHANT_CITY_ENV = os.environ.get("VENDAFACIL_MERCHANT_CITY", "Querencia")


def _pix_config() -> tuple[str, str, str]:
    """Resolve chave/nome/cidade do PIX: banco (config da loja) → env."""
    cfg = db.get_config_loja()
    chave = (cfg.get("pix_chave") or _PIX_KEY_ENV).strip()
    nome = (cfg.get("pix_nome") or _MERCHANT_NAME_ENV).strip() or "VendaFacil PDV"
    cidade = (cfg.get("pix_cidade") or _MERCHANT_CITY_ENV).strip() or "Querencia"
    return chave, nome, cidade


def _get_user_id(request: Request) -> int:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não informado.")
    payload = _verificar_jwt(auth[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return int(payload["sub"])


# ── BR Code / PIX Payload ──


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
) -> str:
    """Gera um payload BR Code estático para PIX.

    O payload segue o padrão EMV QR Code definido pelo BACEN.
    """
    # 00 — Payload Format Indicator
    payload = _tlv("00", "01")

    # 26 — Merchant Account Information
    gui = _tlv("00", "BR.GOV.BCB.PIX")
    chave = _tlv("01", chave_pix)
    merchant_account = _tlv("26", gui + chave)
    payload += merchant_account

    # 52 — Merchant Category Code
    payload += _tlv("52", "0000")

    # 53 — Transaction Currency (986 = BRL)
    payload += _tlv("53", "986")

    # 54 — Transaction Amount (opcional)
    payload += _tlv("54", f"{valor:.2f}")

    # 58 — Country Code
    payload += _tlv("58", "BR")

    # 59 — Merchant Name (até 25 chars)
    payload += _tlv("59", nome[:25].upper())

    # 60 — Merchant City
    payload += _tlv("60", cidade[:15].upper())

    # 62 — Additional Data Field Template
    payload += _tlv("62", _tlv("05", txid))

    # 63 — CRC16 (preenchido com 0000 para cálculo)
    payload += "6304" + "0000"
    crc = _crc16(payload)

    return payload[:-4] + crc


def gerar_qrcode_base64(payload: str) -> str:
    """Gera imagem QR Code a partir do payload e retorna como base64 (PNG)."""
    img = qrcode.make(payload, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


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


# ── Rotas ──


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

    payload = gerar_payload(chave_pix=chave, valor=data.valor, nome=nome, cidade=cidade, txid="***")
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
