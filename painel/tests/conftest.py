"""Configuração dos testes do Painel (SQLite local, sem Supabase)."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["PAINEL_DATA_DIR"] = tempfile.mkdtemp(prefix="vf_painel_test_")
os.environ["PAINEL_JWT_SECRET"] = "test-secret"
os.environ.pop("DATABASE_URL", None)
os.environ.pop("SUPABASE_DB_URL", None)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def admin(client):
    client.post("/api/admin/setup", json={"email": "admin@teste.com", "nome": "Admin", "senha": "admin123"})
    r = client.post("/api/admin/login", json={"email": "admin@teste.com", "senha": "admin123"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}
