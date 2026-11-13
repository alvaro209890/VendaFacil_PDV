"""O PDV se identifica ao painel: o Cloudflare barra "Python-urllib" (erro 1010)."""
import json
import urllib.request

import conta
import sync_client
from version import APP_VERSION


class _Resposta:
    status = 200

    def __init__(self, corpo):
        self._corpo = json.dumps(corpo).encode()

    def read(self):
        return self._corpo

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_ativacao_e_sync_enviam_user_agent_proprio(monkeypatch, tmp_path):
    vistos = []

    def urlopen(req, timeout=None):
        vistos.append(req.get_header("User-agent"))
        if req.full_url.endswith("/api/sync/vendas"):
            return _Resposta({"aceitas": [], "recebidas": 0})
        return _Resposta({"ok": True, "motivo": "ok", "token": "t",
                          "conta": {"login": "x", "nome_loja": "Loja", "ativo": True}})

    monkeypatch.setattr(conta, "PAINEL_URL", "https://painel.exemplo")
    monkeypatch.setattr(conta, "CONTA_FILE", tmp_path / "conta.json")
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    conta.ativar("x", "senha-qualquer")
    sync_client._enviar("tok", [])

    assert vistos == [f"VendaFacilPDV/{APP_VERSION}"] * 2
    assert "urllib" not in vistos[0].lower()
