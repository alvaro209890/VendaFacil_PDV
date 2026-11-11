"""Leitura de XML de NF-e (modelo 55) para entrada de estoque.

O varejista recebe a mercadoria do fornecedor com a NF-e (arquivo .xml). Aqui
extraímos os itens (produto, código de barras, quantidade, custo) para dar
entrada no estoque. É tolerante a namespace e aceita tanto `nfeProc` quanto
`NFe` na raiz.
"""
import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import xml.etree.ElementTree as ET


def _local(tag: str) -> str:
    """Remove o namespace do nome da tag (ex.: '{...}prod' -> 'prod')."""
    return tag.rsplit("}", 1)[-1]


def _child(el, name: str):
    for c in list(el):
        if _local(c.tag) == name:
            return c
    return None


def _ctext(el, name: str, default: str = "") -> str:
    c = _child(el, name) if el is not None else None
    return (c.text or "").strip() if c is not None and c.text else default


def _first(root, name: str):
    for e in root.iter():
        if _local(e.tag) == name:
            return e
    return None


def _numero(texto: str, campo: str, positivo: bool = False) -> float:
    try:
        valor = Decimal(texto.replace(",", "."))
        if not valor.is_finite() or valor < 0 or (positivo and valor == 0):
            raise ValueError
        if not positivo:
            valor = valor.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        numero = float(valor)
        if not math.isfinite(numero) or (positivo and numero <= 0):
            raise ValueError
        return numero
    except (InvalidOperation, ValueError, OverflowError):
        raise ValueError(f"Valor de {campo} inválido na NF-e.") from None


def _gtin(texto: str) -> str:
    if texto.upper().replace(" ", "") in ("SEMGTIN", ""):
        return ""
    if len(texto) not in (8, 12, 13, 14) or not texto.isascii() or not texto.isdigit() or set(texto) == {"0"}:
        raise ValueError("GTIN inválido na NF-e.")
    soma = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(reversed(texto[:-1])))
    if (-soma) % 10 != int(texto[-1]):
        raise ValueError("Dígito verificador do GTIN inválido na NF-e.")
    return texto


def parse_nfe(xml_bytes: bytes) -> dict:
    """Devolve {emitente, numero, chave, itens:[...]} a partir do XML da NF-e."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise ValueError(f"XML inválido: {e}")

    if _local(root.tag) == "NFe":
        nfe = root
    elif _local(root.tag) == "nfeProc":
        nfes = [e for e in root if _local(e.tag) == "NFe"]
        nfe = nfes[0] if len(nfes) == 1 else None
    else:
        nfe = None
    inf = _child(nfe, "infNFe") if nfe is not None else None
    if inf is None:
        raise ValueError("Arquivo não parece ser uma NF-e (raiz NFe/nfeProc e infNFe obrigatórios).")

    ide = _child(inf, "ide")
    if _ctext(ide, "mod") != "55":
        raise ValueError("Importação exige NF-e de modelo 55.")
    chave = (inf.get("Id") or "").replace("NFe", "").strip()
    emit = _child(inf, "emit")
    emitente = _ctext(emit, "xNome") if emit is not None else ""
    numero = _ctext(ide, "nNF") if ide is not None else ""

    itens = []
    for det in inf.iter():
        if _local(det.tag) != "det":
            continue
        prod = _child(det, "prod")
        if prod is None:
            raise ValueError("Estrutura de item inválida na NF-e (prod ausente).")
        nome = _ctext(prod, "xProd")
        if not nome:
            raise ValueError("Nome do item ausente na NF-e.")
        ean = _gtin(_ctext(prod, "cEAN"))
        itens.append({
            "nome": nome,
            "codigo_barras": ean,
            "unidade": _ctext(prod, "uCom") or "UN",
            "quantidade": _numero(_ctext(prod, "qCom"), "quantidade", positivo=True),
            "valor_unitario": _numero(_ctext(prod, "vUnCom"), "custo"),
            "ncm": _ctext(prod, "NCM"),
            "cfop": _ctext(prod, "CFOP"),
        })

    if not itens:
        raise ValueError("Nenhum item encontrado na NF-e.")

    return {"emitente": emitente, "numero": numero, "chave": chave, "itens": itens}
