"""Portaria MT 262/2023: beneficiário e terminal no pagamento integrado."""
import pytest
from lxml import etree
from test_fiscal_direto import _cfg, _venda
from test_fiscal_xsd import cert_teste
from fiscal_xsd_utils import validar_xml
import fiscal_direto


@pytest.mark.parametrize("forma", ["credito", "debito", "pix"])
def test_x19_pagamento_integrado_leva_beneficiario_e_terminal(client, auth, cert_teste, forma):
    p = client.post("/api/produtos", headers=auth, json={
        "nome": "Vinculo de teste", "preco_venda": 10, "estoque": 3,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN"}).json()["produto"]
    venda = _venda(p)
    venda.update(forma_pagamento=forma, pagamento_detalhe={
        "tipo_integracao": "1", "adquirente_cnpj": "10573521000191",
        "bandeira": "mastercard", "autorizacao": "AutorizacaoFixture", "terminal": "TERMINAL-FIXTURE-123"})
    cfg = {**_cfg(), **cert_teste, "razao_social": "Loja de teste", "nome_fantasia": "Loja de teste"}
    doc = fiscal_direto.montar_documento(venda, cfg, serie=1, numero=1)
    root = etree.fromstring(doc.xml.encode())
    card = root.find('.//{*}card')
    assert card.findtext('{*}CNPJReceb') == cfg['cnpj']
    assert card.findtext('{*}idTermPag') == 'TERMINAL-FIXTURE-123'
    validar_xml(fiscal_direto.assinar_xml(doc.xml, cfg))
