"""Ponto de entrada do VendaFácil PDV empacotado (.exe / binário).

Sobe o servidor FastAPI local e abre o navegador já no PDV. Roda 100%
offline na própria máquina — o banco fica em ./dados/vendafacil.db, ao lado
do executável. Variáveis de ambiente (opcionais):

  VENDAFACIL_HOST       (padrão 127.0.0.1)
  VENDAFACIL_PORT       (padrão 3020)
  VENDAFACIL_NO_BROWSER = 1  → não abre o navegador automaticamente
"""
import os
import threading
import webbrowser

import uvicorn

from main import app

HOST = os.environ.get("VENDAFACIL_HOST", "127.0.0.1")
PORT = int(os.environ.get("VENDAFACIL_PORT", "3020"))


def _abrir_navegador() -> None:
    webbrowser.open(f"http://{HOST}:{PORT}/")


def main() -> None:
    if os.environ.get("VENDAFACIL_NO_BROWSER") != "1":
        threading.Timer(1.5, _abrir_navegador).start()
    print(f"VendaFácil PDV rodando em http://{HOST}:{PORT}/  (Ctrl+C para sair)")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
