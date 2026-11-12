"""R09/R10: porta ocupada e encerramento cooperativo."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import run


@pytest.mark.parametrize('app', ['vendafacil-pdv', 'outro-servico'])
def test_instancia_so_reutiliza_porta_do_pdv(monkeypatch, app):
    class Health(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({'app': app, 'status': 'ok', 'version': 'fixture'}).encode())

    server = ThreadingHTTPServer(('127.0.0.1', 0), Health)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    abertas = []
    monkeypatch.setattr(run, 'PORT', server.server_port)
    monkeypatch.setattr(run, '_abrir_navegador', lambda: abertas.append('PDV'))
    monkeypatch.delenv('VENDAFACIL_NO_BROWSER', raising=False)
    try:
        resultado = run.main()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    assert resultado == (0 if app == 'vendafacil-pdv' else 1)
    assert abertas == (['PDV'] if app == 'vendafacil-pdv' else [])


def test_watchdog_pede_saida_do_servidor_sem_forcar_processo(monkeypatch):
    servidor = SimpleNamespace(should_exit=False)
    parar = SimpleNamespace(wait=lambda _: False)
    monkeypatch.setattr(run, 'heartbeat_expirou', lambda: True)
    run._vigiar_heartbeat(servidor, parar)
    assert servidor.should_exit is True


def test_r10_encerramento_aguarda_tarefa_em_andamento(monkeypatch):
    import backup
    import fiscal
    import sync_client
    from main import app

    iniciou, concluiu = Event(), Event()

    def iniciar(parar):
        def trabalho():
            iniciou.set()
            if parar.wait(3):
                concluiu.set()
        thread = Thread(target=trabalho, daemon=True)
        thread.start()
        return thread

    monkeypatch.setattr(backup, 'iniciar_em_background', iniciar)
    monkeypatch.setattr(fiscal, 'iniciar_em_background', lambda _: None)
    monkeypatch.setattr(sync_client, 'iniciar_em_background', lambda _: None)
    with TestClient(app):
        assert iniciou.wait(2)
        assert not concluiu.is_set()
    assert concluiu.is_set()
