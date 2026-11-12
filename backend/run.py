"""Ponto de entrada do VendaFácil PDV empacotado (.exe / binário).

Sobe o servidor FastAPI local e abre o navegador já no PDV. Roda 100%
offline na própria máquina — o banco fica em ./dados/vendafacil.db, ao lado
do executável. Variáveis de ambiente (opcionais):

  VENDAFACIL_HOST       (padrão 127.0.0.1)
  VENDAFACIL_PORT       (padrão 3020)
  VENDAFACIL_NO_BROWSER = 1  → não abre o navegador automaticamente
"""
import json
import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from http.client import HTTPConnection, HTTPException

import uvicorn

from main import app, heartbeat_expirou

HOST = os.environ.get("VENDAFACIL_HOST", "127.0.0.1")
PORT = int(os.environ.get("VENDAFACIL_PORT", "3020"))
_DEVNULL = None


def _preparar_saida_sem_console() -> None:
    """Evita erro do Uvicorn quando o PyInstaller roda sem console."""
    global _DEVNULL
    if sys.stdout is not None and sys.stderr is not None:
        return
    _DEVNULL = open(os.devnull, "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = _DEVNULL
    if sys.stderr is None:
        sys.stderr = _DEVNULL


def _instancia_ativa() -> bool:
    for _ in range(10):
        conn = HTTPConnection(HOST, PORT, timeout=0.5)
        try:
            conn.request("GET", "/health")
            resposta = conn.getresponse()
            if resposta.status != 200:
                return False
            dados = json.loads(resposta.read(4096))
            return (isinstance(dados, dict) and dados.get("app") == "vendafacil-pdv"
                    and dados.get("status") == "ok" and isinstance(dados.get("version"), str))
        except (ValueError, HTTPException):
            return False
        except OSError:
            time.sleep(0.15)
        finally:
            conn.close()
    return False


def _abrir_navegador() -> None:
    webbrowser.open(f"http://{HOST}:{PORT}/")


def _vigiar_heartbeat(servidor: uvicorn.Server, parar: threading.Event) -> None:
    while not parar.wait(5):
        if heartbeat_expirou():
            servidor.should_exit = True
            return


def main() -> int:
    _preparar_saida_sem_console()
    abrir = os.environ.get("VENDAFACIL_NO_BROWSER") != "1"
    empacotado = getattr(sys, "frozen", False)
    with socket.socket() as porta:
        if sys.platform == "win32":
            porta.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            porta.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            porta.bind((HOST, PORT))
        except OSError:
            if _instancia_ativa():
                if abrir:
                    _abrir_navegador()
                return 0
            mensagem = f"Não foi possível abrir a porta {PORT} para o VendaFácil PDV."
            logging.getLogger(__name__).error(mensagem)
            if empacotado and abrir and sys.platform == "win32":
                import ctypes
                ctypes.windll.user32.MessageBoxW(None, mensagem, "VendaFácil PDV", 0x10)
            return 1

        log_config = None if empacotado else uvicorn.config.LOGGING_CONFIG
        servidor = uvicorn.Server(uvicorn.Config(
            app, host=HOST, port=PORT, log_level="info", log_config=log_config,
        ))
        parar = threading.Event()
        navegador = threading.Timer(1.5, _abrir_navegador)
        if abrir:
            navegador.start()
        if empacotado and abrir:
            threading.Thread(target=_vigiar_heartbeat, args=(servidor, parar), daemon=True).start()
        try:
            servidor.run(sockets=[porta])
        finally:
            parar.set()
            navegador.cancel()
    return 0


if __name__ == "__main__":
    sys.exit(main())
