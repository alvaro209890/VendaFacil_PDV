"""Emissor fiscal direto SEFAZ-MT (base local, sem gateway).

Este módulo monta XML NF-e/NFC-e 4.00, assina com A1 quando configurado e
prepara/transmite SOAP para homologação/produção da SEFAZ-MT. A emissão real
depende de certificado A1 da loja, CSC/idCSC e credenciamento estadual.
"""
from __future__ import annotations

import base64
import hashlib
import json
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from database import db

NFE_NS = "http://www.portalfiscal.inf.br/nfe"
ET.register_namespace("", NFE_NS)

C_UF_MT = "51"
VERSAO = "4.00"
URL_QR_NFCE = {
    "homologacao": "https://homologacao.sefaz.mt.gov.br/nfce/consultanfce",
    "producao": "https://www.sefaz.mt.gov.br/nfce/consultanfce",
}
WS = {
    ("65", "homologacao", "autorizacao"): "https://homologacao.sefaz.mt.gov.br/nfcews/services/NFeAutorizacao4",
    ("65", "producao", "autorizacao"): "https://nfce.sefaz.mt.gov.br/nfcews/services/NFeAutorizacao4",
    ("65", "homologacao", "consulta"): "https://homologacao.sefaz.mt.gov.br/nfcews/services/NFeConsultaProtocolo4",
    ("65", "producao", "consulta"): "https://nfce.sefaz.mt.gov.br/nfcews/services/NFeConsultaProtocolo4",
    ("55", "homologacao", "autorizacao"): "https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NFeAutorizacao4",
    ("55", "producao", "autorizacao"): "https://nfe.sefaz.mt.gov.br/nfews/v2/services/NFeAutorizacao4",
    ("55", "homologacao", "consulta"): "https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NFeConsultaProtocolo4",
    ("55", "producao", "consulta"): "https://nfe.sefaz.mt.gov.br/nfews/v2/services/NFeConsultaProtocolo4",
}


class FiscalDiretoError(Exception):
    pass


@dataclass
class DocumentoMontado:
    chave: str
    xml: str
    payload: dict
    qrcode_url: str | None = None


def so_digitos(s: str | None) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


def agora_mt() -> str:
    return datetime.now(timezone(timedelta(hours=-4))).replace(microsecond=0).isoformat()


def dv_chave(chave43: str) -> str:
    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    soma = sum(int(n) * pesos[i % len(pesos)] for i, n in enumerate(reversed(chave43)))
    resto = soma % 11
    dv = 11 - resto
    return "0" if dv >= 10 else str(dv)


def chave_acesso(config: dict, modelo: str, serie: int, numero: int, tp_emis: str = "1") -> str:
    dt = datetime.now(timezone(timedelta(hours=-4)))
    cnpj = so_digitos(config.get("cnpj")).zfill(14)
    ano_mes = dt.strftime("%y%m")
    cod = str(numero).zfill(8)[-8:]
    base = f"{C_UF_MT}{ano_mes}{cnpj}{modelo}{serie:03d}{numero:09d}{tp_emis}{cod}"
    return base + dv_chave(base)


def _tag(parent, name: str, text=None):
    el = ET.SubElement(parent, f"{{{NFE_NS}}}{name}")
    if text is not None:
        el.text = str(text)
    return el


def _validar_emitente(config: dict) -> None:
    obrig = ("cnpj", "inscricao_estadual", "regime_tributario", "codigo_municipio",
             "municipio", "uf", "logradouro", "numero", "bairro", "cep")
    faltando = [c for c in obrig if not str(config.get(c) or "").strip()]
    if faltando:
        raise FiscalDiretoError(f"Configuração fiscal incompleta: {', '.join(faltando)}.")
    if (config.get("uf") or "").upper() != "MT":
        raise FiscalDiretoError("Emissão direta configurada para Mato Grosso: UF do emitente deve ser MT.")


def _validar_certificado(config: dict, modelo: str) -> None:
    if not config.get("certificado_a1_b64") or not config.get("certificado_senha"):
        raise FiscalDiretoError("Informe o certificado A1 da loja e a senha em Configurações Fiscais.")
    if modelo == "65" and (not config.get("csc") or not config.get("csc_id")):
        raise FiscalDiretoError("Informe CSC e ID do CSC para emitir NFC-e.")


def validar_itens(venda: dict) -> None:
    faltas = []
    for item in venda.get("itens", []):
        prod = db.get_produto(item["produto_id"]) or {}
        for campo in ("ncm", "cfop", "cst_csosn", "unidade"):
            if not prod.get(campo):
                faltas.append(f"{item['nome_produto']}: {campo}")
    if faltas:
        raise FiscalDiretoError("Produtos com dados fiscais incompletos: " + "; ".join(faltas[:8]))


def montar_documento(venda: dict, config: dict, modelo: str = "65",
                     cpf_consumidor: str | None = None,
                     destinatario: dict | None = None,
                     serie: int | None = None, numero: int | None = None) -> DocumentoMontado:
    modelo = str(modelo)
    _validar_emitente(config)
    validar_itens(venda)
    if modelo == "55" and not destinatario:
        raise FiscalDiretoError("NF-e modelo 55 exige destinatário.")

    serie = int(serie or (config.get("serie_nfe") if modelo == "55" else config.get("serie_nfce")) or 1)
    numero = int(numero or (config.get("proximo_numero_nfe") if modelo == "55" else config.get("proximo_numero_nfce")) or 1)
    ambiente = config.get("ambiente") or "homologacao"
    tp_amb = "1" if ambiente == "producao" else "2"
    chave = chave_acesso(config, modelo, serie, numero)
    inf_id = "NFe" + chave

    nfe = ET.Element(f"{{{NFE_NS}}}NFe")
    inf = _tag(nfe, "infNFe")
    inf.set("Id", inf_id)
    inf.set("versao", VERSAO)
    ide = _tag(inf, "ide")
    _tag(ide, "cUF", C_UF_MT)
    _tag(ide, "cNF", chave[35:43])
    _tag(ide, "natOp", "VENDA AO CONSUMIDOR" if modelo == "65" else "VENDA DE MERCADORIA")
    _tag(ide, "mod", modelo)
    _tag(ide, "serie", serie)
    _tag(ide, "nNF", numero)
    _tag(ide, "dhEmi", agora_mt())
    _tag(ide, "tpNF", "1")
    _tag(ide, "idDest", "1")
    _tag(ide, "cMunFG", so_digitos(config.get("codigo_municipio")))
    _tag(ide, "tpImp", "4" if modelo == "65" else "1")
    _tag(ide, "tpEmis", "1")
    _tag(ide, "cDV", chave[-1])
    _tag(ide, "tpAmb", tp_amb)
    _tag(ide, "finNFe", "1")
    _tag(ide, "indFinal", "1" if modelo == "65" else "0")
    _tag(ide, "indPres", "1")
    _tag(ide, "procEmi", "0")
    _tag(ide, "verProc", "VendaFacilPDV")

    emit = _tag(inf, "emit")
    _tag(emit, "CNPJ", so_digitos(config.get("cnpj")))
    _tag(emit, "xNome", config.get("razao_social") or config.get("nome_fantasia"))
    _tag(emit, "xFant", config.get("nome_fantasia") or config.get("razao_social"))
    end = _tag(emit, "enderEmit")
    _tag(end, "xLgr", config.get("logradouro"))
    _tag(end, "nro", config.get("numero"))
    _tag(end, "xBairro", config.get("bairro"))
    _tag(end, "cMun", so_digitos(config.get("codigo_municipio")))
    _tag(end, "xMun", config.get("municipio"))
    _tag(end, "UF", (config.get("uf") or "MT").upper())
    _tag(end, "CEP", so_digitos(config.get("cep")))
    _tag(end, "cPais", "1058")
    _tag(end, "xPais", "BRASIL")
    _tag(emit, "IE", so_digitos(config.get("inscricao_estadual")))
    _tag(emit, "CRT", config.get("regime_tributario") or "1")

    dest_doc = so_digitos(cpf_consumidor)
    if modelo == "55":
        dest_doc = so_digitos(destinatario.get("documento"))
    if modelo == "55" or dest_doc:
        dest = _tag(inf, "dest")
        _tag(dest, "CNPJ" if len(dest_doc) == 14 else "CPF", dest_doc)
        _tag(dest, "xNome", (destinatario or {}).get("nome") or "CONSUMIDOR")
        if modelo == "55":
            de = _tag(dest, "enderDest")
            _tag(de, "xLgr", destinatario.get("logradouro"))
            _tag(de, "nro", destinatario.get("numero"))
            _tag(de, "xBairro", destinatario.get("bairro"))
            _tag(de, "cMun", so_digitos(destinatario.get("codigo_municipio")))
            _tag(de, "xMun", destinatario.get("municipio"))
            _tag(de, "UF", destinatario.get("uf"))
            _tag(de, "CEP", so_digitos(destinatario.get("cep")))
            _tag(de, "cPais", "1058")
            _tag(de, "xPais", "BRASIL")
        _tag(dest, "indIEDest", (destinatario or {}).get("indicador_ie") or "9")
        if modelo == "55" and (destinatario or {}).get("inscricao_estadual"):
            _tag(dest, "IE", so_digitos(destinatario.get("inscricao_estadual")))

    total_prod = 0.0
    for idx, item in enumerate(venda.get("itens", []), 1):
        prod = db.get_produto(item["produto_id"]) or {}
        qtd = float(item["quantidade"])
        val = float(item["preco_unitario"])
        bruto = round(qtd * val, 2)
        total_prod += bruto
        det = _tag(inf, "det")
        det.set("nItem", str(idx))
        p = _tag(det, "prod")
        _tag(p, "cProd", item["produto_id"])
        _tag(p, "cEAN", prod.get("codigo_barras") or "SEM GTIN")
        _tag(p, "xProd", item["nome_produto"])
        _tag(p, "NCM", prod.get("ncm"))
        if prod.get("cest"):
            _tag(p, "CEST", prod.get("cest"))
        _tag(p, "CFOP", prod.get("cfop"))
        _tag(p, "uCom", (prod.get("unidade") or "UN").upper())
        _tag(p, "qCom", f"{qtd:.4f}")
        _tag(p, "vUnCom", f"{val:.4f}")
        _tag(p, "vProd", f"{bruto:.2f}")
        _tag(p, "cEANTrib", prod.get("codigo_barras") or "SEM GTIN")
        _tag(p, "uTrib", (prod.get("unidade_tributavel") or prod.get("unidade") or "UN").upper())
        _tag(p, "qTrib", f"{qtd:.4f}")
        _tag(p, "vUnTrib", f"{val:.4f}")
        _tag(p, "indTot", "1")
        imp = _tag(det, "imposto")
        icms = _tag(imp, "ICMS")
        sn = _tag(icms, "ICMSSN102")
        _tag(sn, "orig", prod.get("origem") or "0")
        _tag(sn, "CSOSN", prod.get("cst_csosn") or "102")
        pis = _tag(imp, "PIS")
        pisnt = _tag(pis, "PISNT")
        _tag(pisnt, "CST", prod.get("cst_pis") or "07")
        cof = _tag(imp, "COFINS")
        cofnt = _tag(cof, "COFINSNT")
        _tag(cofnt, "CST", prod.get("cst_cofins") or "07")

    total = _tag(inf, "total")
    icmst = _tag(total, "ICMSTot")
    for tag in ("vBC", "vICMS", "vICMSDeson", "vFCP", "vBCST", "vST", "vFCPST", "vFCPSTRet"):
        _tag(icmst, tag, "0.00")
    _tag(icmst, "vProd", f"{total_prod:.2f}")
    for tag in ("vFrete", "vSeg", "vDesc", "vII", "vIPI", "vIPIDevol", "vPIS", "vCOFINS", "vOutro"):
        _tag(icmst, tag, "0.00")
    _tag(icmst, "vNF", f"{float(venda.get('total') or total_prod):.2f}")
    transp = _tag(inf, "transp")
    _tag(transp, "modFrete", "9")
    pag = _tag(inf, "pag")
    detp = _tag(pag, "detPag")
    _tag(detp, "tPag", {"dinheiro": "01", "credito": "03", "debito": "04", "pix": "17"}.get(venda.get("forma_pagamento"), "99"))
    _tag(detp, "vPag", f"{float(venda.get('total') or total_prod):.2f}")

    qrcode_url = None
    if modelo == "65":
        infsupl = _tag(nfe, "infNFeSupl")
        qrcode_url = gerar_qrcode_url(chave, config, ambiente)
        _tag(infsupl, "qrCode", qrcode_url)
        _tag(infsupl, "urlChave", URL_QR_NFCE[ambiente])

    xml = ET.tostring(nfe, encoding="utf-8", xml_declaration=True).decode("utf-8")
    payload = {"modelo": modelo, "chave": chave, "ambiente": ambiente, "serie": serie, "numero": numero}
    return DocumentoMontado(chave=chave, xml=xml, payload=payload, qrcode_url=qrcode_url)


def gerar_qrcode_url(chave: str, config: dict, ambiente: str) -> str:
    id_csc = str(config.get("csc_id") or "").strip()
    csc = str(config.get("csc") or "").strip()
    tp_amb = "1" if ambiente == "producao" else "2"
    params = f"chNFe={chave}&nVersao=100&tpAmb={tp_amb}&cDest=&dhEmi=&vNF=&vICMS=&digVal=&cIdToken={id_csc}"
    h = hashlib.sha1((params + csc).encode("utf-8")).hexdigest().upper()
    return f"{URL_QR_NFCE[ambiente]}?p={params}&cHashQRCode={h}"


def assinar_xml(xml: str, config: dict) -> str:
    try:
        from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, pkcs12
        from lxml import etree
        from signxml import XMLSigner, methods
    except Exception as e:
        raise FiscalDiretoError(f"Dependências de assinatura fiscal não instaladas: {e}")
    pfx = base64.b64decode(config.get("certificado_a1_b64") or "")
    senha = (config.get("certificado_senha") or "").encode()
    key, cert, _cas = pkcs12.load_key_and_certificates(pfx, senha or None)
    if not key or not cert:
        raise FiscalDiretoError("Certificado A1 inválido ou senha incorreta.")
    key_pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    cert_pem = cert.public_bytes(Encoding.PEM)
    root = etree.fromstring(xml.encode("utf-8"))
    inf = root.find(f".//{{{NFE_NS}}}infNFe")
    ref = "#" + inf.get("Id")
    signed = XMLSigner(method=methods.enveloped, digest_algorithm="sha1", signature_algorithm="rsa-sha1").sign(
        root, key=key_pem, cert=cert_pem, reference_uri=ref
    )
    return etree.tostring(signed, encoding="utf-8", xml_declaration=True).decode("utf-8")


def transmitir_autorizacao(modelo: str, xml_assinado: str, config: dict) -> dict:
    try:
        import requests
        from requests_pkcs12 import Pkcs12Adapter
    except Exception as e:
        raise FiscalDiretoError(f"Dependências de transmissão fiscal não instaladas: {e}")
    ambiente = config.get("ambiente") or "homologacao"
    url = WS.get((str(modelo), ambiente, "autorizacao"))
    if not url:
        raise FiscalDiretoError(f"Webservice SEFAZ-MT não configurado para modelo {modelo}/{ambiente}.")
    pfx = base64.b64decode(config.get("certificado_a1_b64") or "")
    senha = config.get("certificado_senha") or ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pfx") as fp:
        fp.write(pfx)
        pfx_path = fp.name
    try:
        sess = requests.Session()
        sess.mount("https://", Pkcs12Adapter(pkcs12_filename=pfx_path, pkcs12_password=senha))
        body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDadosMsg xmlns="{NFE_NS}"><enviNFe versao="{VERSAO}"><idLote>1</idLote><indSinc>1</indSinc>{xml_assinado}</enviNFe></nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>"""
        resp = sess.post(url, data=body.encode("utf-8"), headers={"Content-Type": "application/soap+xml; charset=utf-8"}, timeout=30)
        return {"status_code": resp.status_code, "texto": resp.text}
    finally:
        try:
            Path(pfx_path).unlink(missing_ok=True)
        except Exception:
            pass


def preparar_e_tentar_transmitir(venda: dict, config: dict, modelo: str = "65",
                                 cpf_consumidor: str | None = None,
                                 destinatario: dict | None = None) -> dict:
    _validar_certificado(config, modelo)
    serie, numero = db.consumir_numero_fiscal(modelo)
    doc = montar_documento(venda, config, modelo, cpf_consumidor, destinatario, serie, numero)
    xml_assinado = assinar_xml(doc.xml, config)
    retorno = transmitir_autorizacao(modelo, xml_assinado, config)
    return {
        "serie": serie, "numero": numero, "chave": doc.chave, "xml_assinado": xml_assinado,
        "payload": json.dumps(doc.payload, ensure_ascii=False), "qrcode_url": doc.qrcode_url,
        "retorno": retorno,
    }
