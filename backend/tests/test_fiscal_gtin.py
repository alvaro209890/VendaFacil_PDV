"""NFC-e: só GTIN válido em cEAN/cEANTrib; caixa e lata com o código certo.

Antes da 1.0.16 o código de barras do cadastro ia cru para o XML: código
interno ("AVULSO-PALHEIRO", "001") ou etiqueta de balança derrubava a nota no
schema/SEFAZ, e a lata vendida avulsa saía com o GTIN da caixa.
"""
from xml.etree import ElementTree as ET

import fiscal_direto
from test_embalagem import criar
from test_embalagem_kaiser import Caso, LATA, PACOTE, gtin
from test_embalagem_vendas import vender
from test_fiscal_xsd import cert_teste, cfg_xsd, _validar_nfce  # noqa: F401 (fixtures)

NS = {"n": "http://www.portalfiscal.inf.br/nfe"}


def test_gtin_fiscal_aceita_so_gtin_valido():
    assert fiscal_direto.gtin_fiscal(LATA) == LATA
    assert fiscal_direto.gtin_fiscal("12345670") == "12345670"
    for interno in ("AVULSO-PALHEIRO", "001", "7896045512318", gtin("200000000001"), "", None, "0000000000000"):
        assert fiscal_direto.gtin_fiscal(interno) == ""


def test_gtins_por_modo_de_venda():
    dupla = {"codigo_barras": PACOTE, "codigo_barras_unidade": LATA}
    assert fiscal_direto.gtins_item(dupla, "embalagem") == (PACOTE, LATA)
    assert fiscal_direto.gtins_item(dupla, "unidade") == (LATA, LATA)
    so_caixa = {"codigo_barras": PACOTE, "codigo_barras_unidade": "AVULSO-T11"}
    assert fiscal_direto.gtins_item(so_caixa, "embalagem") == (PACOTE, PACOTE)
    # Lata avulsa nunca sai com o GTIN da caixa.
    assert fiscal_direto.gtins_item(so_caixa, "unidade") == ("SEM GTIN", "SEM GTIN")
    assert fiscal_direto.gtins_item({"codigo_barras": "001"}, None) == ("SEM GTIN", "SEM GTIN")


def test_nfce_com_caixa_e_lata_valida_no_schema(client, auth, cfg_xsd, cert_teste):  # noqa: F811
    c = Caso()
    p = criar(client, auth, nome=c.nome, estoque=24, unidade_compra="CX", quantidade_por_embalagem=12,
              preco_embalagem=40, preco_unidade=3.8, codigo_barras=c.pacote, codigo_barras_unidade=c.lata,
              ncm="22030000", cest="0302100", cfop="5405", cst_csosn="500", cst_pis="07", cst_cofins="07")
    r = vender(client, auth, p, [{"quantidade": 1, "modo_venda": "embalagem"}, {"quantidade": 3}])
    assert r.status_code == 201, r.text
    venda = client.get(f"/api/vendas/{r.json()['venda']['id']}", headers=auth).json()["venda"]
    doc = fiscal_direto.montar_documento(venda, cfg_xsd, "65", serie=1, numero=1)
    _validar_nfce(doc, cfg_xsd, cert_teste)
    prods = ET.fromstring(doc.xml).findall(".//n:det/n:prod", NS)
    campo = lambda i, k: prods[i].findtext("n:" + k, namespaces=NS)  # noqa: E731
    assert (campo(0, "cEAN"), campo(0, "uCom"), campo(0, "qCom"), campo(0, "vUnCom")) == (c.pacote, "CX", "1.0000", "40.0000")
    assert (campo(0, "cEANTrib"), campo(0, "uTrib"), campo(0, "qTrib")) == (c.lata, "UN", "12.0000")
    assert (campo(1, "cEAN"), campo(1, "cEANTrib"), campo(1, "qCom"), campo(1, "vProd")) == (c.lata, c.lata, "3.0000", "11.40")


def test_nfce_com_codigo_interno_sai_sem_gtin(client, auth, cfg_xsd, cert_teste):  # noqa: F811
    p = criar(client, auth, nome="Palheiro interno", codigo_barras="CART-PALHEIRO-K", codigo_barras_unidade="AVULSO-K11",
              ncm="24031900", cfop="5102", cst_csosn="102", cst_pis="07", cst_cofins="07")
    r = vender(client, auth, p, [{"quantidade": 1, "modo_venda": "embalagem"}, {"quantidade": 1}])
    assert r.status_code == 201, r.text
    venda = client.get(f"/api/vendas/{r.json()['venda']['id']}", headers=auth).json()["venda"]
    doc = fiscal_direto.montar_documento(venda, cfg_xsd, "65", serie=1, numero=2)
    _validar_nfce(doc, cfg_xsd, cert_teste)
    for prod in ET.fromstring(doc.xml).findall(".//n:det/n:prod", NS):
        assert prod.findtext("n:cEAN", namespaces=NS) == "SEM GTIN"
        assert prod.findtext("n:cEANTrib", namespaces=NS) == "SEM GTIN"
