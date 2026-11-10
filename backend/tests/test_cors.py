"""S03: origem estranha não recebe CORS; o Vite local continua."""
from fastapi.testclient import TestClient
from main import app


def test_s03_origem_estranha_sem_cors():
    api = TestClient(app)
    resposta = api.get('/health', headers={'Origin': 'https://evil.example'})
    origem = resposta.headers.get('access-control-allow-origin')
    assert origem != 'https://evil.example'
    assert origem != '*'
    api.close()


def test_s03_vite_local_permitido():
    api = TestClient(app)
    for origem in ('http://127.0.0.1:5173', 'http://localhost:5173'):
        resposta = api.get('/health', headers={'Origin': origem})
        assert resposta.headers.get('access-control-allow-origin') == origem
    api.close()
