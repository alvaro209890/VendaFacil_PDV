"""Falha HTTP não é rejeição fiscal nem prova de autorização."""
import pytest
import fiscal_direto


@pytest.mark.parametrize("codigo", [500, 502, 503, 504])
@pytest.mark.parametrize("corpo", ["", "Servidor indisponível", """
<retEnviNFe xmlns="http://www.portalfiscal.inf.br/nfe"><protNFe><infProt>
<cStat>100</cStat><nProt>151260000000001</nProt>
<xMotivo>Corpo não confiável em erro HTTP</xMotivo></infProt></protNFe></retEnviNFe>
"""])
def test_http_5xx_preserva_pendente_para_consultar(codigo, corpo):
    retorno = fiscal_direto.normalizar_retorno_sefaz(corpo, http_status=codigo)
    assert retorno["status"] == "processando"
    assert not retorno.get("protocolo")
    assert not retorno.get("motivo_rejeicao")
