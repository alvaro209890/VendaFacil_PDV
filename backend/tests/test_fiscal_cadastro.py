"""CFOP da NFC-e derivado do CSOSN e pendências do cadastro (1.0.40).

Cobre o caso que derrubava vendas com itens bons: produto importado com CFOP de
NF-e (5401/5403) ou com 5405 num produto CSOSN 102. O CFOP da NFC-e passa a ser
derivado do CSOSN, e a venda inteira emite — sem perder item.
"""
import fiscal_cadastro as fc


CONFIG = {
    "cnpj": "42115849000150",
    "inscricao_estadual": "138761892",
    "regime_tributario": "1",
    "codigo_municipio": "5107065",
    "municipio": "QUERENCIA",
    "uf": "MT",
    "logradouro": "R LOCAL 04",
    "numero": "750",
    "bairro": "GREENVILLE II",
    "cep": "78643000",
    "ambiente": "homologacao",
    "serie_nfce": 1,
    "proximo_numero_nfce": 1,
    "qrcode_versao": "3",
}


def test_cfop_deriva_do_csosn():
    # Cadastro importado errado não manda mais na NFC-e: CSOSN 102 → 5102.
    assert fc.cfop_nfce({"cfop": "5401", "cst_csosn": "102"}) == "5102"
    assert fc.cfop_nfce({"cfop": "5403", "cst_csosn": "102"}) == "5102"
    assert fc.cfop_nfce({"cfop": "5405", "cst_csosn": "102"}) == "5102"
    assert fc.cfop_nfce({"cfop": "", "cst_csosn": "102"}) == "5102"
    assert fc.cfop_nfce({"cfop": "5102", "cst_csosn": "102"}) == "5102"


def test_cfop_preserva_variacoes_validas():
    for cfop in ("5101", "5103", "5104", "5115"):
        assert fc.cfop_nfce({"cfop": cfop, "cst_csosn": "102"}) == cfop


def test_csosn_500_usa_5405():
    assert fc.cfop_nfce({"cfop": "5102", "cst_csosn": "500"}) == "5405"
    assert fc.cfop_nfce({"cfop": "5405", "cst_csosn": "500"}) == "5405"


def test_pendencias_marcam_o_que_falta():
    assert fc.pendencias_produto({"ncm": "12345678", "cst_csosn": "102"}) == []
    assert fc.pendencias_produto({"ncm": "", "cst_csosn": "102"}) == ["ncm"]
    assert fc.pendencias_produto({"ncm": "123456", "cst_csosn": "102"}) == ["ncm"]
    assert "cest" in fc.pendencias_produto({"ncm": "12345678", "cst_csosn": "500", "cest": ""})
    assert fc.pendencias_produto({"ncm": "12345678", "cst_csosn": "500", "cest": "1234567"}) == []


def test_sugestao_de_ncm_usa_irmao_sem_ambiguidade():
    catalogo = [
        {"id": 1, "nome": "Cigarro DUNHILL", "ncm": "24022000"},
        {"id": 2, "nome": "Cigarro LUCKY STRIKE", "ncm": ""},
        {"id": 3, "nome": "PAPEL HIGIENICO", "ncm": "48181000"},
        {"id": 4, "nome": "PAPEL ALUMINIO", "ncm": ""},
    ]
    assert fc.sugestao_ncm(catalogo[1], catalogo) == "24022000"
    # "papel" é genérico (higiênico x alumínio têm NCM diferente): não sugere.
    assert fc.sugestao_ncm(catalogo[3], catalogo) == ""


def test_sugestao_nao_chuta_quando_irmaos_divergem():
    catalogo = [
        {"id": 1, "nome": "51 ICE limao", "ncm": "22029000"},
        {"id": 2, "nome": "51 ICE uva", "ncm": "22089000"},
        {"id": 3, "nome": "51 ICE melancia", "ncm": ""},
    ]
    assert fc.sugestao_ncm(catalogo[2], catalogo) == ""


def test_venda_mista_sai_com_cfop_valido_nos_dois_itens(monkeypatch):
    import fiscal_direto

    produtos = {
        1: {"id": 1, "nome": "SAL", "ncm": "25010020", "cfop": "5102",
            "cst_csosn": "102", "unidade": "UN", "origem": "0",
            "cst_pis": "07", "cst_cofins": "07"},
        2: {"id": 2, "nome": "POTE SORVETE", "ncm": "21050010", "cfop": "5401",
            "cst_csosn": "102", "unidade": "UN", "origem": "0",
            "cst_pis": "07", "cst_cofins": "07"},
    }
    monkeypatch.setattr(fiscal_direto.db, "get_produto",
                        lambda pid, user_id=None: produtos.get(pid))
    venda = {
        "id": 1,
        "itens": [
            {"produto_id": 1, "nome_produto": "SAL", "quantidade": 1,
             "preco_unitario": 5.0, "subtotal": 5.0},
            {"produto_id": 2, "nome_produto": "POTE SORVETE", "quantidade": 1,
             "preco_unitario": 28.0, "subtotal": 28.0},
        ],
        "desconto": 0,
    }
    doc = fiscal_direto.montar_documento(venda, CONFIG, modelo="65")
    xml = doc.xml if isinstance(doc.xml, str) else doc.xml.decode()
    assert xml.count("<CFOP>5102</CFOP>") == 2
    assert "5401" not in xml
