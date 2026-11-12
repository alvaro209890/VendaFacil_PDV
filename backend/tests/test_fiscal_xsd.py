"""X01-X10: contratos offline de XML, assinatura e QR Code fiscal."""
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from lxml import etree

import fiscal_direto
from fiscal_xsd_utils import validar_xml, verificar_assinatura


NS = "http://www.portalfiscal.inf.br/nfe"
CSC_TESTE = "CSC-SINTETICO-DE-TESTE-ONLY"


@pytest.fixture(scope="module")
def cert_teste():
    """Certificado autoassinado sintético, confinado à fixture de teste."""
    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Fixture fiscal local")])
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
def cfg_xsd():
    return {
        "cnpj": "12345678000195", "inscricao_estadual": "00130000019",
        "regime_tributario": "1", "logradouro": "Rua Sintetica",
        "numero": "100", "bairro": "Centro", "municipio": "Cuiaba",
        "codigo_municipio": "5103403", "uf": "MT", "cep": "78000000",
        "razao_social": "Emitente de teste", "ambiente": "homologacao",
        "csc": CSC_TESTE, "csc_id": "000007", "serie_nfce": 1,
        "serie_nfe": 2, "proximo_numero_nfce": 1, "proximo_numero_nfe": 1,
    }


def _produto(client, auth, sufixo, *, csosn="102", cfop="5102", cest=None):
    resposta = client.post("/api/produtos", headers=auth, json={
        "nome": f"Item fiscal sintético {sufixo}", "preco_venda": 10,
        "estoque": 10, "ncm": "22021000", "cfop": cfop,
        "cst_csosn": csosn, "unidade": "UN", "cest": cest,
        "cst_pis": "07", "cst_cofins": "07",
    })
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["produto"]


def _venda(produto, *, forma="dinheiro", detalhe=None, desconto=0):
    return {
        "id": 876543, "total": 10 - desconto, "desconto": desconto,
        "forma_pagamento": forma, "pagamento_detalhe": detalhe,
        "itens": [{"produto_id": produto["id"], "nome_produto": produto["nome"],
                   "quantidade": 1, "preco_unitario": 10, "subtotal": 10}],
    }


def _assinar(doc, cfg, cert_teste):
    assinatura_cfg = {**cfg, **cert_teste}
    return fiscal_direto.assinar_xml(doc.xml, assinatura_cfg)


def _validar_nfce(doc, cfg, cert_teste):
    assinado = _assinar(doc, cfg, cert_teste)
    validar_xml(assinado, "nfe")
    return assinado


def test_x01_schema_nfce_dinheiro_e_cartao(client, auth, cfg_xsd, cert_teste):
    produto = _produto(client, auth, "dinheiro")
    doc = fiscal_direto.montar_documento(_venda(produto), cfg_xsd, "65", serie=1, numero=101)
    validar_xml(_validar_nfce(doc, cfg_xsd, cert_teste), "nfe")
    assert "<tPag>01</tPag>" in doc.xml

    cartao = _produto(client, auth, "cartao")
    detalhe = {"tipo_integracao": "1", "adquirente_cnpj": "10573521000191",
               "bandeira": "master", "autorizacao": "AUT-TESTE-01"}
    doc_card = fiscal_direto.montar_documento(
        _venda(cartao, forma="credito", detalhe=detalhe), cfg_xsd, "65", serie=1, numero=102)
    validar_xml(_validar_nfce(doc_card, cfg_xsd, cert_teste), "nfe")
    assert "<tpIntegra>1</tpIntegra>" in doc_card.xml


def test_x02_schema_nfce_pix_integrado_e_fiado(client, auth, cfg_xsd, cert_teste):
    pix = _produto(client, auth, "pix")
    doc_pix = fiscal_direto.montar_documento(
        _venda(pix, forma="pix", detalhe={"tipo_integracao": "1",
                                            "adquirente_cnpj": "10573521000191",
                                            "autorizacao": "E2E-TESTE-0001"}),
        cfg_xsd, "65", serie=1, numero=103)
    validar_xml(_validar_nfce(doc_pix, cfg_xsd, cert_teste), "nfe")
    assert "<tPag>17</tPag>" in doc_pix.xml

    fiado = _produto(client, auth, "fiado")
    doc_fiado = fiscal_direto.montar_documento(
        _venda(fiado, forma="fiado"), cfg_xsd, "65", cpf_consumidor="12345678909",
        serie=1, numero=104)
    validar_xml(_validar_nfce(doc_fiado, cfg_xsd, cert_teste), "nfe")
    assert "<tPag>05</tPag>" in doc_fiado.xml and "<indPag>1</indPag>" in doc_fiado.xml
    assert "<xPag>" not in doc_fiado.xml


def test_x03_schema_nfce_desconto_cpf_e_st(client, auth, cfg_xsd, cert_teste):
    produto = _produto(client, auth, "st", csosn="500", cfop="5405", cest="0300700")
    doc = fiscal_direto.montar_documento(
        _venda(produto, desconto=1.25), cfg_xsd, "65", cpf_consumidor="12345678909",
        serie=1, numero=105)
    validar_xml(_validar_nfce(doc, cfg_xsd, cert_teste), "nfe")
    assert "<vDesc>1.25</vDesc>" in doc.xml
    assert "<CSOSN>500</CSOSN>" in doc.xml and "<CEST>0300700</CEST>" in doc.xml
    assert "<CPF>12345678909</CPF>" in doc.xml


def test_x03_schema_nfe55_destinatario(client, auth, cfg_xsd, cert_teste):
    produto = _produto(client, auth, "nfe55")
    destinatario = {
        "nome": "Destinatario sintético", "documento": "11222333000181",
        "logradouro": "Av Teste", "numero": "2", "bairro": "Centro",
        "municipio": "Cuiaba", "codigo_municipio": "5103403", "uf": "MT",
        "cep": "78000000", "indicador_ie": "9", "inscricao_estadual": "",
    }
    doc = fiscal_direto.montar_documento(
        _venda(produto), cfg_xsd, "55", destinatario=destinatario, serie=2, numero=106)
    assinado = _assinar(doc, cfg_xsd, cert_teste)
    validar_xml(assinado, "nfe")
    assert "<mod>55</mod>" in doc.xml
    assert "<indIEDest>9</indIEDest>" in doc.xml
    assert "<indFinal>1</indFinal>" in doc.xml

    destinatario.update(indicador_ie="1", inscricao_estadual="130000019")
    contribuinte = fiscal_direto.montar_documento(
        _venda(produto), cfg_xsd, "55", destinatario=destinatario, serie=2, numero=107)
    assert "<indIEDest>1</indIEDest>" in contribuinte.xml
    assert "<indFinal>0</indFinal>" in contribuinte.xml


@pytest.mark.parametrize("modelo", ["55", "65"])
def test_indica_operacao_presencial_sem_intermediario(client, auth, cfg_xsd, cert_teste, modelo):
    produto = _produto(client, auth, "presencial")
    destino = {
        "nome": "Cliente sintético", "documento": "11222333000181",
        "logradouro": "Av Teste", "numero": "2", "bairro": "Centro",
        "municipio": "Cuiaba", "codigo_municipio": "5103403", "uf": "MT",
        "cep": "78000000", "indicador_ie": "9",
    }
    doc = fiscal_direto.montar_documento(_venda(produto), cfg_xsd, modelo, destinatario=destino)
    assinado = (_validar_nfce(doc, cfg_xsd, cert_teste) if modelo == "65"
                else _assinar(doc, cfg_xsd, cert_teste))
    validar_xml(assinado, "nfe")
    assert "<indPres>1</indPres><indIntermed>0</indIntermed>" in doc.xml
    assert "<infIntermed>" not in doc.xml


def test_x04_schema_cancelamento_assinado(cfg_xsd, cert_teste):
    nota = {"chave": "51261112345678000195650010000001011000000107",
            "protocolo": "151000000000107", "modelo": "65"}
    xml_evento = fiscal_direto.montar_cancelamento_xml(
        nota, cfg_xsd, "Cancelamento de teste sintético por erro de emissão")
    xml_assinado = fiscal_direto.assinar_xml(xml_evento, {**cfg_xsd, **cert_teste})
    verificar_assinatura(xml_assinado, cert_teste["cert_pem"])
    pacote = (f'<envEvento xmlns="{NS}" versao="1.00"><idLote>1</idLote>'
              f'{xml_assinado.split("?>", 1)[-1]}</envEvento>')
    validar_xml(pacote, "cancelamento")
    assert "<tpEvento>110111</tpEvento>" in pacote


def test_x06_assinatura_sha1_c14n_public_key_e_byte_adulterado(
        client, auth, cfg_xsd, cert_teste):
    produto = _produto(client, auth, "assinatura")
    doc = fiscal_direto.montar_documento(_venda(produto), cfg_xsd, "65", serie=1, numero=108)
    assinado = _assinar(doc, cfg_xsd, cert_teste)
    validar_xml(assinado, "nfe")
    verificar_assinatura(assinado, cert_teste["cert_pem"])

    raiz = etree.fromstring(assinado.encode("utf-8"))
    ns = {"n": NS, "ds": "http://www.w3.org/2000/09/xmldsig#"}
    assert raiz.xpath("string(.//ds:SignatureMethod/@Algorithm)", namespaces=ns).endswith("rsa-sha1")
    assert raiz.xpath("string(.//ds:DigestMethod/@Algorithm)", namespaces=ns).endswith("sha1")
    assert raiz.xpath("string(.//ds:CanonicalizationMethod/@Algorithm)", namespaces=ns) == (
        "http://www.w3.org/TR/2001/REC-xml-c14n-20010315")

    original = "<vNF>10.00</vNF>"
    assert original in assinado
    adulterado = assinado.replace(original, "<vNF>10.01</vNF>", 1)
    with pytest.raises(Exception):
        verificar_assinatura(adulterado, cert_teste["cert_pem"])


def test_x07_qr2_online_hash_independente(cfg_xsd):
    chave = "51261112345678000195650010000001011000000107"
    url = fiscal_direto.gerar_qrcode_url(chave, cfg_xsd, "homologacao")
    partes = unquote(url.split("?p=", 1)[1]).split("|")
    conteudo = "|".join(partes[:-1])
    esperado = hashlib.sha1((conteudo + CSC_TESTE).encode("utf-8")).hexdigest().upper()
    assert partes[:4] == [chave, "2", "2", "7"]
    assert partes[-1] == esperado


def test_x08_qr2_contingencia_hash_independente(cfg_xsd):
    chave = "51261112345678000195650010000001011000000107"
    dt = "2026-11-12T13:14:15-04:00"
    digest = "QUJDREVGR0g="
    url = fiscal_direto.gerar_qrcode_url(
        chave, cfg_xsd, "homologacao", tp_emis="9", dh_emi=dt,
        v_nf=8.75, dig_val=digest)
    partes = unquote(url.split("?p=", 1)[1]).split("|")
    conteudo = "|".join(partes[:-1])
    esperado = hashlib.sha1((conteudo + CSC_TESTE).encode("utf-8")).hexdigest().upper()
    # O exemplo oficial da seção 4.3.6.2 apresenta o digVal em hexadecimal
    # minúsculo; a caixa não altera o digest nem é normalizada na URL.
    assert partes[:7] == [chave, "2", "2", "12", "8.75", digest.encode().hex(), "7"]
    assert partes[-1] == esperado


def test_x09_fuso_mt_dh_emi_e_chave_coerentes(client, auth, cfg_xsd, monkeypatch):
    produto = _produto(client, auth, "fuso")
    instante = datetime(2026, 12, 31, 23, 30, tzinfo=fiscal_direto.TZ_MT)

    class RelogioFixo(datetime):
        @classmethod
        def now(cls, tz=None):
            return instante.astimezone(tz) if tz else instante.replace(tzinfo=None)

    monkeypatch.setattr(fiscal_direto, "datetime", RelogioFixo)
    doc = fiscal_direto.montar_documento(_venda(produto), cfg_xsd, "65", serie=1, numero=109)
    raiz = etree.fromstring(doc.xml.encode("utf-8"))
    dh = raiz.findtext(f".//{{{NS}}}dhEmi")
    assert dh == "2026-12-31T23:30:00-04:00"
    assert doc.chave[2:6] == "2612"
    assert doc.chave[-1] == fiscal_direto.dv_chave(doc.chave[:-1])


def test_x10_ambiente_somente_da_configuracao(client, auth, cfg_xsd):
    produto = _produto(client, auth, "ambiente")
    homolog = fiscal_direto.montar_documento(
        _venda(produto), cfg_xsd, "65", cpf_consumidor="12345678909", serie=1, numero=110)
    prod = fiscal_direto.montar_documento(
        _venda(produto), {**cfg_xsd, "ambiente": "producao"}, "65",
        cpf_consumidor="12345678909", serie=1, numero=111)
    assert f"<tpAmb>2</tpAmb>" in homolog.xml
    assert f"<tpAmb>1</tpAmb>" in prod.xml
    assert "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL" in homolog.xml
