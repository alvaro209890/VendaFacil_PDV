import sys
from pathlib import Path
import base64
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db
import fiscal_direto


def _cfg():
    return {
        "cnpj": "12345678000195",
        "inscricao_estadual": "00130000019",
        "regime_tributario": "1",
        "logradouro": "Rua Teste",
        "numero": "100",
        "bairro": "Centro",
        "municipio": "Cuiaba",
        "codigo_municipio": "5103403",
        "uf": "MT",
        "cep": "78000000",
        "ambiente": "homologacao",
        "csc": "CSCDEHOMOLOGACAO",
        "csc_id": "000001",
        "serie_nfce": 1,
        "proximo_numero_nfce": 1,
        "serie_nfe": 1,
        "proximo_numero_nfe": 1,
    }


def _venda(produto):
    return {
        "id": 1,
        "total": 10,
        "desconto": 0,
        "forma_pagamento": "dinheiro",
        "itens": [{
            "produto_id": produto["id"],
            "nome_produto": produto["nome"],
            "quantidade": 1,
            "preco_unitario": 10,
            "subtotal": 10,
        }],
    }


def test_monta_xml_nfce_65(client, auth):
    r = client.post("/api/produtos", headers=auth, json={
        "nome": "Refri Fiscal", "preco_venda": 10, "estoque": 5,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN",
    })
    produto = r.json()["produto"]
    doc = fiscal_direto.montar_documento(_venda(produto), _cfg(), "65", cpf_consumidor="12345678909", serie=1, numero=1)
    assert "<mod>65</mod>" in doc.xml
    assert doc.chave.startswith("51")
    assert doc.qrcode_url and "cHashQRCode" in doc.qrcode_url


def test_monta_xml_nfe_55_para_empresa(client, auth):
    produto = client.post("/api/produtos", headers=auth, json={
        "nome": "Arroz Fiscal", "preco_venda": 10, "estoque": 5,
        "ncm": "10063021", "cfop": "5102", "cst_csosn": "102", "unidade": "UN",
    }).json()["produto"]
    dest = {
        "nome": "Empresa Teste LTDA", "documento": "11222333000181",
        "logradouro": "Av Cliente", "numero": "10", "bairro": "Centro",
        "municipio": "Cuiaba", "codigo_municipio": "5103403", "uf": "MT",
        "cep": "78000000", "indicador_ie": "9", "inscricao_estadual": "",
    }
    doc = fiscal_direto.montar_documento(_venda(produto), _cfg(), "55", destinatario=dest, serie=1, numero=1)
    assert "<mod>55</mod>" in doc.xml
    assert "<CNPJ>11222333000181</CNPJ>" in doc.xml


def test_numeracao_separada_nfce_nfe():
    db.salvar_config_fiscal({"serie_nfce": 7, "proximo_numero_nfce": 11, "serie_nfe": 3, "proximo_numero_nfe": 21}, "agora")
    assert db.consumir_numero_fiscal("65") == (7, 11)
    assert db.consumir_numero_fiscal("55") == (3, 21)


def test_assina_xml_com_a1_pkcs12_sintetico():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "TESTE A1")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=30))
        .sign(key, hashes.SHA256())
    )
    pfx = pkcs12.serialize_key_and_certificates(
        b"teste",
        key,
        cert,
        None,
        serialization.BestAvailableEncryption(b"1234"),
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<NFe xmlns="http://www.portalfiscal.inf.br/nfe">'
        '<infNFe Id="NFe51000112345678000195650010000000011000000015" versao="4.00">'
        "<ide><cUF>51</cUF></ide>"
        "</infNFe></NFe>"
    )

    assinado = fiscal_direto.assinar_xml(xml, {
        "certificado_a1_b64": base64.b64encode(pfx).decode(),
        "certificado_senha": "1234",
    })

    assert "<ds:Signature" in assinado or "<Signature" in assinado
    assert "rsa-sha1" in assinado


def test_normaliza_retorno_sefaz_autorizado_com_xml_proc():
    xml_assinado = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe Id="NFe51000112345678000195650010000000011000000015" versao="4.00" /></NFe>'
    )
    retorno = (
        '<retEnviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
        "<cStat>104</cStat><xMotivo>Lote processado</xMotivo>"
        '<protNFe versao="4.00"><infProt>'
        "<chNFe>51000112345678000195650010000000011000000015</chNFe>"
        "<nProt>151000000000001</nProt><cStat>100</cStat>"
        "<xMotivo>Autorizado o uso da NF-e</xMotivo>"
        "</infProt></protNFe></retEnviNFe>"
    )

    dados = fiscal_direto.normalizar_retorno_sefaz(retorno, xml_assinado, 200)

    assert dados["status"] == "autorizada"
    assert dados["protocolo"] == "151000000000001"
    assert "nfeProc" in dados["xml_autorizado"]
    assert "protNFe" in dados["xml_autorizado"]


def test_normaliza_retorno_sefaz_rejeitado():
    retorno = (
        '<retEnviNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
        "<cStat>104</cStat><xMotivo>Lote processado</xMotivo>"
        '<protNFe versao="4.00"><infProt>'
        "<cStat>539</cStat><xMotivo>Duplicidade de NF-e</xMotivo>"
        "</infProt></protNFe></retEnviNFe>"
    )

    dados = fiscal_direto.normalizar_retorno_sefaz(retorno, None, 200)

    assert dados["status"] == "rejeitada"
    assert dados["motivo_rejeicao"] == "Duplicidade de NF-e"


def test_monta_xml_evento_cancelamento():
    nota = {"chave": "51000112345678000195650010000000011000000015", "protocolo": "151000000000001"}
    xml = fiscal_direto.montar_cancelamento_xml(nota, _cfg(), "Erro de emissao da venda teste")

    assert "<tpEvento>110111</tpEvento>" in xml
    assert "<nProt>151000000000001</nProt>" in xml
    assert "ID1101115100011234567800019565001000000001100000001501" in xml


def test_normaliza_retorno_evento_cancelado():
    retorno = (
        '<retEnvEvento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">'
        '<retEvento versao="1.00"><infEvento>'
        "<cStat>135</cStat><xMotivo>Evento registrado e vinculado a NF-e</xMotivo>"
        "<nProt>151000000000009</nProt>"
        "</infEvento></retEvento></retEnvEvento>"
    )

    dados = fiscal_direto.normalizar_retorno_evento(retorno, 200)

    assert dados["status"] == "cancelada"
    assert dados["protocolo"] == "151000000000009"
