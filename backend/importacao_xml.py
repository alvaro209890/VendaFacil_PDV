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


def _gtin_secundario(texto: str) -> str:
    """cEANTrib serve só de código extra: inválido vira vazio, sem recusar a nota."""
    try:
        return _gtin(texto)
    except ValueError:
        return ""


def _valor_opcional(el, nome: str, campo: str) -> Decimal:
    texto = _ctext(el, nome) if el is not None else ""
    return Decimal(str(_numero(texto, campo))) if texto else Decimal(0)


def _soma_tag(raiz, nome: str, campo: str) -> Decimal:
    """Soma uma tag em qualquer grupo abaixo de `raiz` (ICMS00..ICMS90, ICMSSN*, IPITrib)."""
    if raiz is None:
        return Decimal(0)
    total = Decimal(0)
    for e in raiz.iter():
        if _local(e.tag) == nome and (e.text or "").strip():
            total += Decimal(str(_numero(e.text.strip(), campo)))
    return total


def _custo_item(prod, imposto, quantidade: float, valor_unitario: float) -> dict:
    """Custo de aquisição do item: o que a loja paga por ele, rateado na quantidade.

    vProd + frete + seguro + outras despesas + IPI + ICMS-ST (e FCP-ST) − desconto.
    O ICMS retido anteriormente (vICMSSTRet, CST 60) não entra: já está no preço.
    """
    v_prod_txt = _ctext(prod, "vProd")
    v_prod = Decimal(str(_numero(v_prod_txt, "valor do produto"))) if v_prod_txt else (
        Decimal(str(quantidade)) * Decimal(str(valor_unitario)))
    despesas = (_valor_opcional(prod, "vFrete", "frete") + _valor_opcional(prod, "vSeg", "seguro")
                + _valor_opcional(prod, "vOutro", "outras despesas")
                - _valor_opcional(prod, "vDesc", "desconto"))
    icms = _child(imposto, "ICMS") if imposto is not None else None
    ipi = _child(imposto, "IPI") if imposto is not None else None
    despesas += _soma_tag(icms, "vICMSST", "ICMS-ST") + _soma_tag(icms, "vFCPST", "FCP-ST")
    despesas += _soma_tag(ipi, "vIPI", "IPI")
    total = v_prod + despesas
    if total < 0:
        total = Decimal(0)
    qtd = Decimal(str(quantidade))
    efetivo = (total / qtd).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    rateio = (despesas / qtd).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return {"valor_unitario_efetivo": float(efetivo), "despesas_unitarias": float(rateio),
            "custo_total_item": float(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))}


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
        ean_trib = _gtin_secundario(_ctext(prod, "cEANTrib"))
        quantidade = _numero(_ctext(prod, "qCom"), "quantidade", positivo=True)
        valor_unitario = _numero(_ctext(prod, "vUnCom"), "custo")
        unidade = _ctext(prod, "uCom") or "UN"
        unidade_trib = (_ctext(prod, "uTrib") or unidade).strip().upper()
        qtd_trib_txt = _ctext(prod, "qTrib")
        try:
            qtd_trib = _numero(qtd_trib_txt, "quantidade tributável", positivo=True) if qtd_trib_txt else 0
        except ValueError:
            qtd_trib = 0
        # Ex.: 50 CX na unidade comercial e 600 UN na tributável = 12 por caixa.
        razao = qtd_trib / quantidade if qtd_trib else 0
        fator_sugerido = int(round(razao)) if (unidade_trib != unidade.strip().upper() and razao > 1
                                               and abs(razao - round(razao)) < 1e-6) else 0
        itens.append({
            "nome": nome,
            "codigo_barras": ean,
            "codigo_barras_trib": ean_trib if ean_trib != ean else "",
            "unidade": unidade,
            "unidade_trib": unidade_trib,
            "fator_sugerido": fator_sugerido,
            "quantidade": quantidade,
            "valor_unitario": valor_unitario,
            **_custo_item(prod, _child(det, "imposto"), quantidade, valor_unitario),
            "ncm": _ctext(prod, "NCM"),
            "cfop": _ctext(prod, "CFOP"),
        })

    if not itens:
        raise ValueError("Nenhum item encontrado na NF-e.")

    return {"emitente": emitente, "numero": numero, "chave": chave, "itens": itens}
