"""Rejeição ou falha de evento não desfaz autorização existente."""
import pytest
import fiscal


@pytest.mark.parametrize("codigo,corpo", [
    (200, '<retEnvEvento xmlns="http://www.portalfiscal.inf.br/nfe"><cStat>128</cStat>'
     '<retEvento><infEvento><cStat>573</cStat><xMotivo>Duplicidade de evento</xMotivo>'
     '</infEvento></retEvento></retEnvEvento>'),
    (503, ''), (200, '<resposta/>'),
    (503, '<retEvento xmlns="http://www.portalfiscal.inf.br/nfe"><infEvento>'
     '<cStat>135</cStat><nProt>151260000000009</nProt></infEvento></retEvento>'),
])
def test_cancelamento_sem_confirmacao_preserva_autorizacao(monkeypatch, codigo, corpo):
    nota = {"id": 7, "status": "autorizada", "protocolo": "151260000000100"}

    class Store:
        def get_nota(self, _id):
            return dict(nota)

        def get_config_fiscal(self):
            return {"provedor_fiscal": "sefaz_mt_direto"}

        def atualizar_nota(self, _id, dados, _agora):
            return {**nota, **dados}

    monkeypatch.setattr(fiscal, "db", Store())
    monkeypatch.setattr(fiscal, "_verificar_prazo_cancelamento", lambda *_: None)
    monkeypatch.setattr(fiscal.fiscal_direto, "cancelar_documento", lambda *_: {
        "retorno": {"texto": corpo, "status_code": codigo}})
    atualizada = fiscal.cancelar_nfce(7, "Cancelamento solicitado pelo operador")
    assert atualizada["status"] == "autorizada"
    assert atualizada["protocolo"] == nota["protocolo"]
