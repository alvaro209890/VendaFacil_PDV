"""Helpers de validação local dos esquemas oficiais NF-e/NFC-e."""
from functools import lru_cache
from pathlib import Path

from lxml import etree


XSD_DIR = Path(__file__).resolve().parent / "xsd"
_NF_NS = "http://www.portalfiscal.inf.br/nfe"


@lru_cache(maxsize=None)
def schema(nome: str) -> etree.XMLSchema:
    arquivos = {
        "nfe": XSD_DIR / "NFe" / "nfe_v4.00.xsd",
        "cancelamento": XSD_DIR / "Cancelamento" / "envEventoCancNFe_v1.00.xsd",
        "inutilizacao": XSD_DIR / "Inutilizacao" / "inutNFe_v4.00.xsd",
    }
    try:
        caminho = arquivos[nome]
    except KeyError as exc:
        raise ValueError(f"Schema fiscal desconhecido: {nome}") from exc
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    return etree.XMLSchema(etree.parse(str(caminho), parser))


def validar_xml(xml: str | bytes, nome: str = "nfe") -> None:
    """Lança AssertionError com o erro XSD completo para facilitar o diagnóstico."""
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    raiz = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml, parser)
    contrato = schema(nome)
    if not contrato.validate(raiz):
        erros = "; ".join(str(e) for e in contrato.error_log)
        raise AssertionError(f"XML inválido no schema {nome}: {erros}")


def _verificar_assinatura_sem_prefixo(raiz, sig, certificado_pem: bytes):
    """Verificação manual (digest SHA-1 + RSA-SHA1) para a Signature com o
    namespace xmldsig DEFAULT, que o signxml 5.2 não localiza por prefixo."""
    import base64
    import hashlib

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    ds = "http://www.w3.org/2000/09/xmldsig#"

    def c14n(elemento):
        bruto = etree.tostring(elemento, encoding="utf-8", xml_declaration=False)
        return etree.tostring(etree.fromstring(bruto), method="c14n",
                              exclusive=False, with_comments=False)

    signed_info = sig.find(f"{{{ds}}}SignedInfo")
    referencia = signed_info.find(f"{{{ds}}}Reference")
    uri = (referencia.get("URI") or "").lstrip("#")
    alvo = raiz.find(f".//*[@Id='{uri}']")
    assert alvo is not None, "Reference sem elemento correspondente"
    canonico = c14n(alvo)
    digest = base64.b64encode(hashlib.sha1(canonico).digest()).decode("ascii")
    assert digest == referencia.findtext(f"{{{ds}}}DigestValue"), "DigestValue não confere"
    si_canonico = c14n(signed_info)
    valor = base64.b64decode(sig.findtext(f"{{{ds}}}SignatureValue"))
    cert = x509.load_pem_x509_certificate(certificado_pem)
    cert.public_key().verify(valor, si_canonico, padding.PKCS1v15(), hashes.SHA1())
    return {"signed_xml": raiz}


def verificar_assinatura(xml: str | bytes, certificado_pem: bytes):
    """Valida Reference/digest e assinatura XMLDSig com o certificado da fixture."""
    bruto = xml.encode("utf-8") if isinstance(xml, str) else xml
    raiz = etree.fromstring(bruto)
    sig = raiz.find(".//{http://www.w3.org/2000/09/xmldsig#}Signature")
    if sig is not None and sig.prefix is None:
        return _verificar_assinatura_sem_prefixo(raiz, sig, certificado_pem)

    from signxml import SignatureConfiguration, XMLVerifier
    from signxml.algorithms import DigestAlgorithm, SignatureMethod

    return XMLVerifier().verify(
        bruto,
        x509_cert=certificado_pem,
        expect_config=SignatureConfiguration(
            require_x509=True,
            signature_methods=frozenset({SignatureMethod.RSA_SHA1}),
            digest_algorithms=frozenset({DigestAlgorithm.SHA1}),
        ),
    )


def texto_no(xml: str | bytes, nome: str) -> str | None:
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    raiz = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml, parser)
    return raiz.findtext(f".//{{{_NF_NS}}}{nome}")
