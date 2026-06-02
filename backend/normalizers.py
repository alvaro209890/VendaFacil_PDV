"""Normalizadores simples para dados de entrada."""
from __future__ import annotations

import re


def only_digits(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"\D", "", value)


def normalize_cep(value: str | None) -> str | None:
    """Aceita CEP com ponto, hífen ou só números e salva como 00000-000."""
    if value is None:
        return None
    raw = value.strip()
    digits = only_digits(raw) or ""
    if len(digits) == 8:
        return f"{digits[:5]}-{digits[5:]}"
    return raw


def normalize_upper_uf(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().upper()
