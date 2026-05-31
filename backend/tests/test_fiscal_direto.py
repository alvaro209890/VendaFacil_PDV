import sys
from pathlib import Path

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
