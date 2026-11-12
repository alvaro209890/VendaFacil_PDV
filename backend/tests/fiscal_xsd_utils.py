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


def verificar_assinatura(xml: str | bytes, certificado_pem: bytes):
    """Valida Reference/digest e assinatura XMLDSig com o certificado da fixture."""
    from signxml import SignatureConfiguration, XMLVerifier
    from signxml.algorithms import DigestAlgorithm, SignatureMethod

    return XMLVerifier().verify(
        xml.encode("utf-8") if isinstance(xml, str) else xml,
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
