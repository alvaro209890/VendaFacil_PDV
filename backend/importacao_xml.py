"""Leitura de XML de NF-e (modelo 55) para entrada de estoque.

O varejista recebe a mercadoria do fornecedor com a NF-e (arquivo .xml). Aqui
extraímos os itens (produto, código de barras, quantidade, custo) para dar
entrada no estoque. É tolerante a namespace e aceita tanto `nfeProc` quanto
`NFe` na raiz.
"""
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


def _float(s: str) -> float:
    try:
        return float((s or "0").replace(",", "."))
    except ValueError:
        return 0.0


def parse_nfe(xml_bytes: bytes) -> dict:
    """Devolve {emitente, numero, chave, itens:[...]} a partir do XML da NF-e."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise ValueError(f"XML inválido: {e}")

    inf = _first(root, "infNFe")
    if inf is None:
        raise ValueError("Arquivo não parece ser uma NF-e (infNFe não encontrado).")

    chave = (inf.get("Id") or "").replace("NFe", "").strip()
    emit = _first(inf, "emit")
    ide = _first(inf, "ide")
    emitente = _ctext(emit, "xNome") if emit is not None else ""
    numero = _ctext(ide, "nNF") if ide is not None else ""

    itens = []
    for det in inf.iter():
        if _local(det.tag) != "det":
            continue
        prod = _child(det, "prod")
        if prod is None:
            continue
        ean = _ctext(prod, "cEAN")
        if ean.upper().replace(" ", "") in ("SEMGTIN", ""):
            ean = ""
        itens.append({
            "nome": _ctext(prod, "xProd"),
            "codigo_barras": ean,
            "unidade": _ctext(prod, "uCom") or "UN",
            "quantidade": _float(_ctext(prod, "qCom")),
            "valor_unitario": round(_float(_ctext(prod, "vUnCom")), 4),
            "ncm": _ctext(prod, "NCM"),
            "cfop": _ctext(prod, "CFOP"),
        })

    if not itens:
        raise ValueError("Nenhum item encontrado na NF-e.")

    return {"emitente": emitente, "numero": numero, "chave": chave, "itens": itens}
