import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mercadopago import MercadoPagoPoint, _friendly_msg, _state, _payment_status_front


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


def test_criar_cobranca_pix_usa_orders_api_com_qr():
    cli = FakePoint()
    resp = cli.criar_cobranca("NEWLAND_TEST", Decimal("4.93"), "venda-teste", False, "pix")

    method, path, body, idempotency = cli.calls[0]
    assert method == "POST"
    assert path == "/v1/orders"
    assert idempotency is True
    assert body["type"] == "point"
    assert body["config"]["point"]["terminal_id"] == "NEWLAND_TEST"
    assert body["config"]["point"]["print_on_terminal"] == "no_ticket"
    assert body["config"]["payment_method"]["default_type"] == "qr"
    assert body["transactions"]["payments"][0]["amount"] == "4.93"
    assert resp["id"] == "ORD123"


def test_criar_cobranca_credito_usa_payload_oficial_sem_ticket():
    cli = FakePoint()
    cli.criar_cobranca("NEWLAND_TEST", Decimal("4.93"), "venda-teste", True, "credito")

    _, _, body, _ = cli.calls[0]
    assert body["config"]["point"]["print_on_terminal"] == "no_ticket"
    assert body["config"]["payment_method"]["default_type"] == "credit_card"


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
