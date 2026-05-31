"""Configuração dos testes do PDV.

Aponta o banco para uma pasta temporária ANTES de importar o app (o módulo
database cria o banco no import). Cada execução de testes começa limpa.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ["VENDAFACIL_DATA_DIR"] = tempfile.mkdtemp(prefix="vf_test_")
os.environ["VENDAFACIL_NO_BROWSER"] = "1"
os.environ.pop("VENDAFACIL_PAINEL_URL", None)  # modo local (sem licença remota)

# backend/ no path para importar main, database, etc.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def auth(client):
    r = client.post("/api/auth/registro", json={
        "usuario": "teste", "nome": "Teste", "senha": "Loja@2026xy",
    })
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}
