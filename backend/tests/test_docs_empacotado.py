"""S04: o executável não publica /docs nem /openapi.json."""
from fastapi.testclient import TestClient
from main import app, urls_doc


def test_s04_empacotado_esconde_docs():
    from fastapi import FastAPI
    fechado = FastAPI(title="teste", **urls_doc(True))
    api = TestClient(fechado)
    assert api.get("/docs").status_code == 404
    assert api.get("/openapi.json").status_code == 404
    api.close()


def test_s04_dev_mantem_docs():
    assert urls_doc(False)["docs_url"] == "/docs"
    assert urls_doc(False)["openapi_url"] == "/openapi.json"
    assert app.docs_url == urls_doc(False)["docs_url"]
