"""X05: contrato oficial de inutilização e validações antes da rede."""
import pytest
from test_fiscal_xsd import cert_teste, cfg_xsd
from fiscal_xsd_utils import validar_xml, verificar_assinatura
import fiscal_direto


def test_x05_inutilizacao_assinada_valida_no_xsd(cfg_xsd, cert_teste, monkeypatch):
    config = {**cfg_xsd, **cert_teste}
    envios = []

    def enviar(modelo, servico, xml, cfg):
        envios.append((modelo, servico, xml))
        return {"status_code": 200, "texto": '<retInutNFe xmlns="http://www.portalfiscal.inf.br/nfe">'
                '<infInut><cStat>102</cStat><xMotivo>Inutilização homologada</xMotivo>'
                '<nProt>151260000000010</nProt></infInut></retInutNFe>'}

    monkeypatch.setattr(fiscal_direto, "_post_soap", enviar)
    r = fiscal_direto.inutilizar_numeracao(config, "65", 2026, 1, 4, 8,
                                         "Falha local deixou intervalo sem emissao")
    assert r["status"] == "inutilizada" and r["cstat"] == "102"
    validar_xml(r["xml_pedido"], "inutilizacao")
    verificar_assinatura(r["xml_pedido"], cert_teste["cert_pem"])
    assert envios[0][:2] == ("65", "inutilizacao")


@pytest.mark.parametrize("modelo,ano,serie,inicio,fim,just", [
    ("66", 2026, 1, 1, 1, "Justificativa fiscal para teste"),
    ("65", 1999, 1, 1, 1, "Justificativa fiscal para teste"),
    ("65", 2026, -1, 1, 1, "Justificativa fiscal para teste"),
    ("65", 2026, 1, 0, 1, "Justificativa fiscal para teste"),
    ("65", 2026, 1, 2, 1, "Justificativa fiscal para teste"),
    ("65", 2026, 1, 1, 1000000000, "Justificativa fiscal para teste"),
    ("65", 2026, 1, 1, 1, "Curta"),
])
def test_inutilizacao_invalida_nao_transmite(cfg_xsd, monkeypatch, modelo, ano, serie, inicio, fim, just):
    def proibido(*_):
        pytest.fail("Pedido inválido não pode ir à rede")
    monkeypatch.setattr(fiscal_direto, "_post_soap", proibido)
    with pytest.raises(fiscal_direto.FiscalDiretoError):
        fiscal_direto.inutilizar_numeracao(cfg_xsd, modelo, ano, serie, inicio, fim, just)
