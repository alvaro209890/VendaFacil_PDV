"""PIX / QR Code — Geração de payload BR Code e QR Code imagem"""

import io
import os
import base64
import struct
from typing import Optional

import qrcode
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth import _verificar_jwt

router = APIRouter()

PIX_KEY = os.environ.get("VENDAFACIL_PIX_KEY", "")
MERCHANT_NAME = os.environ.get("VENDAFACIL_MERCHANT_NAME", "VendaFacil PDV")
MERCHANT_CITY = os.environ.get("VENDAFACIL_MERCHANT_CITY", "Querencia")


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


# ── Rotas ──


@router.post("/qrcode")
async def gerar_qr_pix(data: PixQrCodeRequest, request: Request) -> PixQrCodeResponse:
    """Gera um QR Code PIX com o valor informado."""
    _get_user_id(request)

    if not PIX_KEY:
        raise HTTPException(
            status_code=503,
            detail="Chave PIX não configurada. Configure VENDAFACIL_PIX_KEY no servidor.",
        )

    payload = gerar_payload(
        chave_pix=PIX_KEY,
        valor=data.valor,
        nome=MERCHANT_NAME,
        cidade=MERCHANT_CITY,
        txid="***",
    )
    qr = gerar_qrcode_base64(payload)
    return PixQrCodeResponse(payload=payload, qr_base64=qr)


@router.get("/chave")
async def obter_chave_pix(request: Request) -> dict:
    """Retorna se a chave PIX está configurada (sem expor o valor)."""
    _get_user_id(request)
    return {"configurada": bool(PIX_KEY)}
