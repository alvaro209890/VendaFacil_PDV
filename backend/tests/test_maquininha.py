import sys
from pathlib import Path
from decimal import Decimal

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mercadopago import (
    MercadoPagoPoint, PointError, _friendly_msg, _state, _payment_status_front,
    dados_fiscais_pagamento,
)
from database import db


class FakePoint(MercadoPagoPoint):
    def __init__(self):
        self.token = "TEST"
        self.calls = []

    def _req(self, method, path, body=None, *, idempotency=False):
        self.calls.append((method, path, body, idempotency))
        if path == "/v1/orders":
            return 201, {
                "id": "ORD123",
                "status": "created",
                "config": body["config"],
                "transactions": body["transactions"],
            }
        return 200, {}


def test_criar_cobranca_pix_usa_default_type_pix():
    cli = FakePoint()
    cli.criar_cobranca("NEWLAND_TEST", Decimal("4.93"), "venda-teste", False, "pix")

    _, _, body, _ = cli.calls[0]
    assert body["config"]["payment_method"]["default_type"] == "pix"


def test_rota_maquininha_recusa_pix_quando_desligado(client, auth):
    # PIX integrado desligado (padrão) → rota recusa e manda usar o QR do PDV.
    db.salvar_config_maquininha({"habilitado": 1, "pix_integrado": 0}, "agora")
    resp = client.post(
        "/api/maquininha/cobranca",
        headers=auth,
        json={"valor": 4.93, "forma": "pix"},
    )
    assert resp.status_code == 400
    assert "PIX pela maquininha" in resp.json()["detail"]


def test_criar_cobranca_credito_usa_payload_oficial_sem_ticket():
    cli = FakePoint()
    cli.criar_cobranca("NEWLAND_TEST", Decimal("4.93"), "venda-teste", True, "credito")

    _, _, body, _ = cli.calls[0]
    assert body["config"]["point"]["print_on_terminal"] == "no_ticket"
    assert body["config"]["payment_method"]["default_type"] == "credit_card"


def test_criar_cobranca_debito_usa_debit_card():
    cli = FakePoint()
    cli.criar_cobranca("NEWLAND_TEST", Decimal("4.93"), "venda-teste", True, "debito")

    method, path, body, idempotency = cli.calls[0]
    assert method == "POST"
    assert path == "/v1/orders"
    assert idempotency is True
    assert body["type"] == "point"
    assert body["config"]["point"]["terminal_id"] == "NEWLAND_TEST"
    assert body["config"]["point"]["print_on_terminal"] == "no_ticket"
    assert body["config"]["payment_method"]["default_type"] == "debit_card"
    assert body["transactions"]["payments"][0]["amount"] == "4.93"


def test_erro_409_tem_mensagem_clara():
    msg = _friendly_msg(409, {"message": "Conflict"})
    assert "cobranca pendente" in msg.lower()
    assert "point" in msg.lower()


def test_state_orders_mapeia_para_frontend_legado():
    assert _state({"status": "created"}) == "OPEN"
    assert _state({"status": "at_terminal"}) == "ON_TERMINAL"
    assert _state({"status": "processing"}) == "PROCESSING"
    assert _state({"status": "expired"}) == "CANCELED"
    assert _state({"status": "failed"}) == "ERROR"

    order = {"status": "processed", "transactions": {"payments": [{"status": "processed"}]}}
    assert _state(order) == "FINISHED"
    assert _payment_status_front(order) == "approved"


def test_dados_fiscais_extrai_autorizacao_e_bandeira():
    db.salvar_config_maquininha({"adquirente_cnpj": "10573521000191"}, "agora")
    order = {
        "config": {"point": {"terminal_id": "PAX_A910"}},
        "transactions": {"payments": [{
            "id": 99887766,
            "payment_method": {"id": "master", "authorization_code": "654321"},
        }]},
    }
    dados = dados_fiscais_pagamento(order)  # cli=None: usa só o payload da order
    assert dados["tipo_integracao"] == "1"
    assert dados["adquirente_cnpj"] == "10573521000191"
    assert dados["bandeira"] == "master"
    assert dados["autorizacao"] == "654321"
    assert dados["payment_id"] == "99887766"
    assert dados["terminal"] == "PAX_A910"


def test_dados_fiscais_pix_usa_endtoend_id_como_cAut():
    db.salvar_config_maquininha({"adquirente_cnpj": "10573521000191"}, "agora")
    order = {
        "transactions": {"payments": [{
            "id": 111222,
            "payment_method": {"type": "pix"},
            "point_of_interaction": {"transaction_data": {"e2e_id": "E105735212024X"}},
        }]},
    }
    dados = dados_fiscais_pagamento(order)
    assert dados["autorizacao"] == "E105735212024X"
    assert dados["bandeira"] in (None, "pix")  # PIX não tem bandeira de cartão


def test_checkout_grava_vinculo_pagamento_na_venda(client, auth):
    prod = client.post("/api/produtos", headers=auth, json={
        "nome": "Item Vinculo", "preco_venda": 10, "estoque": 5,
        "ncm": "22021000", "cfop": "5102", "cst_csosn": "102", "unidade": "UN",
    }).json()["produto"]
    r = client.post("/api/vendas/checkout", headers=auth, json={
        "itens": [{"produto_id": prod["id"], "quantidade": 1}],
        "forma_pagamento": "credito",
        "pagamento": {
            "tipo_integracao": "1", "adquirente_cnpj": "10573521000191",
            "bandeira": "visa", "autorizacao": "ABC123",
        },
    })
    assert r.status_code == 201
    venda_id = r.json()["venda"]["id"]
    venda = db.get_venda(venda_id)
    assert venda["pagamento_detalhe"]
    import json as _json
    pd = _json.loads(venda["pagamento_detalhe"])
    assert pd["autorizacao"] == "ABC123"
    assert pd["adquirente_cnpj"] == "10573521000191"
