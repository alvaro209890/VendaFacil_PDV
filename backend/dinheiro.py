"""Dinheiro comercial: Decimal na conta, REAL apenas na borda SQLite/API.

Converta floats pela representação decimal, nunca pelo valor binário interno.
Quantidade × preço arredonda por item; somas não arredondam prematuramente.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable

CENTAVO = Decimal('0.01')


def decimal(valor) -> Decimal:
    """Entrada decimal finita, aceitando vírgula simples como separador."""
    try:
        resultado = Decimal(str(valor).strip().replace(',', '.'))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError('Informe um número decimal finito.') from exc
    if not resultado.is_finite():
        raise ValueError('Informe um número decimal finito.')
    return resultado


def arredondar(valor) -> Decimal:
    """Valor monetário com duas casas e arredondamento comercial."""
    try:
        return decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError('Valor monetário fora do limite suportado.') from exc


def moeda(valor) -> float:
    """Borda de armazenamento/API, preservando schema REAL nesta entrega."""
    return float(arredondar(valor))


def multiplicar(quantidade, preco) -> Decimal:
    return arredondar(decimal(quantidade) * decimal(preco))


def somar(valores: Iterable) -> Decimal:
    return sum((decimal(valor) for valor in valores), Decimal('0'))
