"""X21: inutilização rastreável sem concorrer com emissão."""
from datetime import datetime
import pytest
from test_sefaz_simulador import (fiscal_store, client, auth, simulador, emissor,
                                  loja, _vender, _emitir)
from sefaz_fake import retorno_inutilizacao


def _pedido():
    return {"modelo": "65", "ano": datetime.now().year, "serie": 1, "inicio": 4,
            "fim": 8, "justificativa": "Intervalo sem uso por falha local anterior"}


def test_x21_api_inutiliza_guarda_protocolo_e_nao_reenvia(client, auth, emissor, simulador, fiscal_store):
    store = fiscal_store["db"]
    store.salvar_config_fiscal({"proximo_numero_nfce": 10}, "fixture")
    simulador.push("inutilizacao", retorno_inutilizacao())
    r = client.post("/api/fiscal/servicos/inutilizacoes", headers=auth, json=_pedido())
    assert r.status_code == 200, r.text
    inutilizacao = r.json()["inutilizacao"]
    assert inutilizacao["status"] == "inutilizada"
    assert inutilizacao["protocolo"] == "151260000000010"
    repetida = client.post("/api/fiscal/servicos/inutilizacoes", headers=auth, json=_pedido())
    assert repetida.status_code == 200, repetida.text
    assert repetida.json()["inutilizacao"]["id"] == inutilizacao["id"]
    assert len(simulador.calls) == 1
    with store._lock:
        row = store._conn.execute("SELECT xml_pedido,xml_retorno FROM inutilizacoes_fiscais").fetchone()
    assert "Signature" in row["xml_pedido"] and "102" in row["xml_retorno"]
    historico = client.get("/api/fiscal/servicos/inutilizacoes", headers=auth)
    assert historico.status_code == 200
    assert historico.json()["inutilizacoes"][0]["id"] == inutilizacao["id"]


@pytest.mark.parametrize("situacao,tipo", [("autorizada", "1"), ("contingencia", "9"),
                                         ("processando", "1"), ("rejeitada", "9")])
def test_x21_faixa_com_nota_ativa_recusada(loja, fiscal_store, simulador, situacao, tipo):
    store = fiscal_store["db"]
    nota = _emitir(loja, _vender(loja)).json()["nota"]
    store.atualizar_nota(nota["id"], {"status": situacao, "tipo_emissao": tipo}, "fixture")
    pedido = {**_pedido(), "inicio": nota["numero"], "fim": nota["numero"]}
    antes = len(simulador.calls)
    r = loja["client"].post("/api/fiscal/servicos/inutilizacoes", headers=loja["auth"], json=pedido)
    assert r.status_code == 409, r.text
    assert len(simulador.calls) == antes


def test_x21_nao_inutiliza_faixa_futura(client, auth, emissor, simulador):
    r = client.post("/api/fiscal/servicos/inutilizacoes", headers=auth, json=_pedido())
    assert r.status_code == 409, r.text
    assert simulador.calls == []


def test_x21_sem_autenticacao_recusada(client):
    assert client.post("/api/fiscal/servicos/inutilizacoes", json=_pedido()).status_code == 401


def test_x21_pedido_concorrente_so_transmite_uma_vez(client, auth, emissor, simulador, fiscal_store):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    fiscal_store["db"].salvar_config_fiscal({"proximo_numero_nfce": 10}, "fixture")
    barreira = Barrier(2)
    def solicitar(_):
        barreira.wait(timeout=10)
        return client.post("/api/fiscal/servicos/inutilizacoes", headers=auth, json=_pedido())
    with ThreadPoolExecutor(max_workers=2) as pool:
        respostas = list(pool.map(solicitar, range(2)))
    assert all(r.status_code == 200 for r in respostas)
    assert len({r.json()["inutilizacao"]["id"] for r in respostas}) == 1
    assert len(simulador.calls) == 1


def test_x21_503_preserva_faixa_sem_reenvio(client, auth, emissor, simulador, fiscal_store):
    fiscal_store["db"].salvar_config_fiscal({"proximo_numero_nfce": 10}, "fixture")
    simulador.push("inutilizacao", "Serviço indisponível", status=503)
    for _ in range(2):
        r = client.post("/api/fiscal/servicos/inutilizacoes", headers=auth, json=_pedido())
        assert r.status_code == 200, r.text
        assert r.json()["inutilizacao"]["status"] == "processando"
    assert len(simulador.calls) == 1


def test_x21_inutilizado_nao_emite_apos_recuar_contador(loja, simulador, fiscal_store):
    store = fiscal_store["db"]
    store.salvar_config_fiscal({"proximo_numero_nfce": 10}, "fixture")
    r = loja["client"].post("/api/fiscal/servicos/inutilizacoes", headers=loja["auth"], json=_pedido())
    assert r.status_code == 200, r.text
    store.salvar_config_fiscal({"proximo_numero_nfce": 4}, "fixture")
    resposta = _emitir(loja, _vender(loja))
    assert resposta.status_code == 400, resposta.text
    assert "inutiliza" in resposta.text
    assert len(simulador.calls) == 1


def test_x21_outro_operador_nao_le_historico_nem_retorno(client, auth, emissor, simulador, fiscal_store):
    import auth as autenticacao
    store = fiscal_store["db"]
    store.salvar_config_fiscal({"proximo_numero_nfce": 10}, "fixture")
    assert client.post("/api/fiscal/servicos/inutilizacoes", headers=auth, json=_pedido()).status_code == 200
    user = store.create_user("outro-fiscal", "Outro operador", "hash-fixture", "fixture")
    headers = {"Authorization": "Bearer " + autenticacao._gerar_jwt(autenticacao._token_user(user))}
    assert client.get("/api/fiscal/servicos/inutilizacoes", headers=headers).json()["inutilizacoes"] == []
    repetida = client.post("/api/fiscal/servicos/inutilizacoes", headers=headers, json=_pedido())
    assert repetida.status_code == 409, repetida.text
    assert "151260000000010" not in repetida.text
    assert len(simulador.calls) == 1
