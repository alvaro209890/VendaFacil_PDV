"""O prazo não pode ser renovado pelo instante local da consulta."""
import pytest
import fiscal
import fiscal_direto


@pytest.mark.parametrize("cstat", ["100", "150"])
def test_p50_normaliza_instante_real_sefaz(cstat):
    xml = ('<retConsSitNFe xmlns="http://www.portalfiscal.inf.br/nfe"><protNFe><infProt>'
           f'<cStat>{cstat}</cStat><nProt>151260000000001</nProt>'
           '<dhRecbto>2026-10-31T23:55:00-04:00</dhRecbto></infProt></protNFe></retConsSitNFe>')
    retorno = fiscal_direto.normalizar_retorno_sefaz(xml, http_status=200)
    assert retorno["autorizado_em"] == "2026-10-31T23:55:00-04:00"


@pytest.mark.parametrize("fluxo", ["emissao", "consulta", "loop"])
def test_p50_fluxos_persistem_dhrecbto_sem_renovar_prazo(monkeypatch, fluxo):
    nota = {"id": 1, "status": "processando", "chave": "5" * 44, "modelo": "65"}
    config = {"provedor_fiscal": "sefaz_mt_direto", "certificado_a1_b64": "fixture", "certificado_senha": "fixture"}
    instante = "2026-10-31T23:55:00-04:00"
    class Store:
        def get_nota(self, _): return dict(nota)
        def get_config_fiscal(self): return config
        def notas_pendentes(self): return [dict(nota)]
        def atualizar_nota(self, _, dados, agora):
            nota.update(dados)
            return dict(nota)
    monkeypatch.setattr(fiscal, "db", Store())
    monkeypatch.setattr(fiscal_direto, "normalizar_retorno_sefaz", lambda *_: {
        "status": "autorizada", "protocolo": "151260000000001", "autorizado_em": instante})
    monkeypatch.setattr(fiscal_direto, "consultar_chave", lambda *_: {"texto": "fixture", "status_code": 200})
    if fluxo == "emissao":
        fiscal._concluir_reserva(1, {"numero": 1, "serie": 1, "chave": "5" * 44,
                                   "payload": "{}", "xml_assinado": "<NFe/>"}, config)
    elif fluxo == "consulta":
        fiscal.consultar_nfce(1)
    else:
        assert fiscal._processar_pendentes_direto(config) == 1
    assert nota["autorizado_em"] == instante
