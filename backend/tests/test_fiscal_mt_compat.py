"""Compatibilidade SEFAZ-MT: ASCII 7-bit (cStat 402), assinatura sem prefixo
(cStat 587), bundle TLS com as raízes ICP-Brasil e rejeição de lote com HTTP 200."""
import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

import fiscal_direto
from fiscal_xsd_utils import validar_xml, verificar_assinatura

NS = "http://www.portalfiscal.inf.br/nfe"


@pytest.fixture(scope="module")
def cert_teste():
    """Certificado autoassinado sintético, confinado à fixture de teste."""
    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Fixture MT local")])
    agora = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(nome).issuer_name(nome).public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - timedelta(minutes=1))
        .not_valid_after(agora + timedelta(days=2))
        .sign(chave, hashes.SHA256())
    )
    pfx = pkcs12.serialize_key_and_certificates(
        b"fixture-fiscal", chave, cert, None,
        serialization.BestAvailableEncryption(b"senha-teste"),
    )
    return {
        "certificado_a1_b64": base64.b64encode(pfx).decode("ascii"),
        "certificado_senha": "senha-teste",
        "cert_pem": cert.public_bytes(serialization.Encoding.PEM),
    }


@pytest.fixture
def cfg_mt():
    return {
        "cnpj": "12345678000195", "inscricao_estadual": "00130000019",
        "regime_tributario": "1", "logradouro": "Rua Sintética",
        "numero": "100", "bairro": "Centro", "municipio": "Querência",
        "codigo_municipio": "5107065", "uf": "MT", "cep": "78643000",
        "razao_social": "Mercearia São João", "ambiente": "homologacao",
        "csc": "CSC-SINTETICO-DE-TESTE-ONLY", "csc_id": "000007",
        "serie_nfce": 1, "serie_nfe": 2, "proximo_numero_nfce": 1,
        "proximo_numero_nfe": 1,
    }


def _produto(client, auth):
    resposta = client.post("/api/produtos", headers=auth, json={
        "nome": "PÃO DE QUEIJO CONGELADO 500G", "preco_venda": 12.5, "estoque": 10,
        "ncm": "19059090", "cfop": "5102", "cst_csosn": "102",
        "unidade": "UN", "cst_pis": "07", "cst_cofins": "07",
    })
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["produto"]


def _venda(produto):
    return {
        "id": 765432, "total": 12.5, "desconto": 0,
        "forma_pagamento": "dinheiro", "pagamento_detalhe": None,
        "itens": [{"produto_id": produto["id"], "nome_produto": produto["nome"],
                   "quantidade": 1, "preco_unitario": 12.5, "subtotal": 12.5}],
    }


def test_mt_nfce_sai_em_ascii_7bit(client, auth, cfg_mt, cert_teste):
    produto = _produto(client, auth)
    doc = fiscal_direto.montar_documento(_venda(produto), cfg_mt, "65", serie=1, numero=201)
    nao_ascii = [c for c in doc.xml if ord(c) > 127]
    assert not nao_ascii, f"sobrou caractere fora do ASCII: {nao_ascii[:5]}"
    assert "<xMun>Querencia</xMun>" in doc.xml
    assert "PAO DE QUEIJO" in doc.xml
    assinado = fiscal_direto.assinar_xml(doc.xml, {**cfg_mt, **cert_teste})
    validar_xml(assinado, "nfe")
    verificar_assinatura(assinado, cert_teste["cert_pem"])


def test_mt_assinatura_sem_prefixo_ds(client, auth, cfg_mt, cert_teste):
    produto = _produto(client, auth)
    doc = fiscal_direto.montar_documento(_venda(produto), cfg_mt, "65", serie=1, numero=202)
    assinado = fiscal_direto.assinar_xml(doc.xml, {**cfg_mt, **cert_teste})
    assert "<ds:Signature" not in assinado
    assert '<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">' in assinado
    validar_xml(assinado, "nfe")
    verificar_assinatura(assinado, cert_teste["cert_pem"])


def test_mt_justificativa_de_cancelamento_em_ascii(cfg_mt):
    nota = {"chave": "51261112345678000195650010000002011000000201",
            "protocolo": "123456789012345", "modelo": "65"}
    xml = fiscal_direto.montar_cancelamento_xml(
        nota, cfg_mt, "Cancelamento por erro de digitação do operador — café")
    assert all(ord(c) < 128 for c in xml)
    assert "digitacao" in xml and "cafe" in xml


def test_rejeicao_de_lote_sem_infprot_nao_fica_processando():
    retorno = ('<retEnviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
               '<tpAmb>2</tpAmb><verAplic>MT_A2_NFCe-4.100</verAplic><cStat>402</cStat>'
               '<xMotivo>Rejeicao: XML utiliza codificacao diferente de UTF-8</xMotivo>'
               '</retEnviNFe>')
    dados = fiscal_direto.normalizar_retorno_sefaz(retorno, "<NFe/>", 200)
    assert dados["status"] == "rejeitada"
    assert dados["cstat"] == "402"


def test_ca_bundle_inclui_raizes_icpbrasil():
    caminho = fiscal_direto._ca_bundle()
    assert caminho, "bundle TLS não foi montado"
    with open(caminho, encoding="utf-8") as arquivo:
        conteudo = arquivo.read()
    assert conteudo.count("BEGIN CERTIFICATE") >= 3  # certifi + v10 + v5
