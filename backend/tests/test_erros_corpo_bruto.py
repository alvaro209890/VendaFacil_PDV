"""S09/P25: corpo bruto não pode ir ao log; marcadores são canários não secretos."""
import logging

import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel

from errors import register_error_handlers, _safe_json


class Entrada(BaseModel):
    numero: int
    senha: str = ""


@pytest.fixture
def api_log(tmp_path):
    app = FastAPI()
    register_error_handlers(app)

    @app.post("/modelo")
    async def modelo(dados: Entrada):
        return {"numero": dados.numero}

    @app.post("/bytes")
    async def bytes_invalidos(request: Request):
        corpo = await request.body()
        raise RequestValidationError(
            [{"type": "int_parsing", "loc": ("body", "numero"), "msg": "Inteiro esperado"}],
            body=corpo,
        )

    caminho = tmp_path / "fixture.log"
    handler = logging.FileHandler(caminho, encoding="utf-8")
    logger = logging.getLogger("vendafacil.api")
    propagacao, nivel = logger.propagate, logger.level
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    cliente = TestClient(app, raise_server_exceptions=False)
    try:
        yield cliente, caminho, handler
    finally:
        cliente.close()
        logger.removeHandler(handler)
        handler.close()
        logger.propagate = propagacao
        logger.setLevel(nivel)


@pytest.mark.parametrize("rota,corpo", [
    ("/modelo", b'{"senha":"CANARIO_P25_NAO_SECRETO","numero":}'),
    ("/bytes", b'{"senha":"CANARIO_P25_NAO_SECRETO","numero":"x"}'),
    ("/modelo", b'{"numero":"x","observacao":"CANARIO_P25_NAO_SECRETO"}'),
], ids=["json-malformado", "erro-com-body-bytes", "json-invalido-sem-corpo-no-log"])
def test_s09_nao_registra_corpo_bruto(api_log, rota, corpo):
    cliente, caminho, handler = api_log
    resposta = cliente.post(rota, content=corpo, headers={"Content-Type": "application/json"})
    assert resposta.status_code == 422
    handler.flush()
    texto = caminho.read_text(encoding="utf-8")
    vazou = "CANARIO_P25_NAO_SECRETO" in texto
    assert vazou is False, "Corpo bruto de entrada foi registrado"
    assert "validation_error" in texto
    assert resposta.json()["request_id"] in texto


@pytest.mark.parametrize("construtor", [bytes, bytearray, memoryview], ids=["bytes", "bytearray", "memoryview"])
def test_s09_bytes_utf8_nao_viram_texto_bruto(construtor):
    vazou = "CANARIO_P25_NAO_SECRETO" in _safe_json(construtor(b'{"senha":"CANARIO_P25_NAO_SECRETO"}'))
    assert vazou is False, "Formatter decodificou bytes sem sanitizar"


def test_s09_falha_de_sanitizacao_nao_recorre_a_repr_bruto():
    circular = {"senha": "CANARIO_P25_NAO_SECRETO"}
    circular["ciclo"] = circular
    vazou = "CANARIO_P25_NAO_SECRETO" in _safe_json(circular)
    assert vazou is False, "Fallback do formatter expôs o objeto bruto"


def test_s09_bytes_nao_utf8_ja_sao_opacos():
    vazou = "CANARIO_P25_NAO_SECRETO" in _safe_json(b'\xffCANARIO_P25_NAO_SECRETO')
    assert vazou is False


def test_s09_requisicao_nao_utf8_e_recusada_sem_corpo(api_log):
    cliente, caminho, handler = api_log
    resposta = cliente.post("/modelo", content=b'\xffCANARIO_P25_NAO_SECRETO', headers={"Content-Type": "application/json"})
    assert resposta.status_code in (400, 422)
    handler.flush()
    vazou = "CANARIO_P25_NAO_SECRETO" in caminho.read_text(encoding="utf-8")
    assert vazou is False


def test_s09_detalhe_estruturado_mantem_motivo_e_mascara():
    texto = _safe_json({"mensagem": "Estoque insuficiente", "access_token": "CANARIO_P25_NAO_SECRETO"})
    assert "Estoque insuficiente" in texto
    vazou = "CANARIO_P25_NAO_SECRETO" in texto
    assert vazou is False
