"""S07/S08: rota de API sem token válido responde 401, salvo a lista pública."""
from fastapi.testclient import TestClient
from main import app
from auth import _gerar_jwt

PUBLICAS = {
    ('POST', '/api/auth/login'),
    ('POST', '/api/auth/registro'),
    ('GET', '/api/ativacao/status'),
    ('POST', '/api/ativacao'),
    ('POST', '/api/heartbeat'),
}


def _concreto(path: str) -> str:
    while '{' in path:
        inicio = path.index('{')
        fim = path.index('}', inicio)
        path = path[:inicio] + '1' + path[fim + 1:]
    return path


def _rotas_api():
    vistas = set()
    for rota in app.routes:
        grupos = []
        if type(rota).__name__ == '_IncludedRouter':
            prefixo = rota.include_context.prefix
            grupos = [(prefixo + sub.path, sub.methods) for sub in rota.original_router.routes]
        else:
            grupos = [(getattr(rota, 'path', '') or '', getattr(rota, 'methods', None))]
        for path, methods in grupos:
            if not path.startswith('/api/'):
                continue
            for method in methods or set():
                if method in {'HEAD', 'OPTIONS'}:
                    continue
                vistas.add((method, path, _concreto(path)))
    return vistas


def test_s07_api_sem_token_responde_401():
    api = TestClient(app, raise_server_exceptions=False)
    vazadas = []
    for method, path, concreto in sorted(_rotas_api()):
        if (method, path) in PUBLICAS:
            continue
        resposta = api.request(method, concreto, json={})
        if resposta.status_code != 401:
            vazadas.append(f'{method} {path} -> {resposta.status_code}')
    api.close()
    assert len(vistas := _rotas_api()) >= 40
    assert vazadas == []


def test_s08_token_expirado_ou_adulterado_401():
    api = TestClient(app, raise_server_exceptions=False)
    expirado = _gerar_jwt({
        'sub': '1', 'usuario': 'loja', 'email': 'loja', 'nome': 'Loja',
        'iat': 1, 'exp': 1,
    })
    adulterado = expirado[:-4] + 'xxxx'
    for token in (expirado, adulterado, 'nao-e-jwt'):
        resposta = api.get('/api/dashboard', headers={'Authorization': f'Bearer {token}'})
        assert resposta.status_code == 401, resposta.text
    api.close()
