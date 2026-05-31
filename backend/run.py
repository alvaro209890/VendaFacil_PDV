"""Ponto de entrada do VendaFácil PDV empacotado (.exe / binário).

Sobe o servidor FastAPI local e abre o navegador já no PDV. Roda 100%
offline na própria máquina — o banco fica em ./dados/vendafacil.db, ao lado
do executável. Variáveis de ambiente (opcionais):

  VENDAFACIL_HOST       (padrão 127.0.0.1)
  VENDAFACIL_PORT       (padrão 3020)
  VENDAFACIL_NO_BROWSER = 1  → não abre o navegador automaticamente
"""
import os
import sys
import threading
import webbrowser

import uvicorn

from main import app

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


def _abrir_navegador() -> None:
    webbrowser.open(f"http://{HOST}:{PORT}/")


def main() -> None:
    _preparar_saida_sem_console()
    if os.environ.get("VENDAFACIL_NO_BROWSER") != "1":
        threading.Timer(1.5, _abrir_navegador).start()
    print(f"VendaFácil PDV rodando em http://{HOST}:{PORT}/  (Ctrl+C para sair)")
    log_config = None if getattr(sys, "frozen", False) else uvicorn.config.LOGGING_CONFIG
    uvicorn.run(app, host=HOST, port=PORT, log_level="info", log_config=log_config)


if __name__ == "__main__":
    main()
