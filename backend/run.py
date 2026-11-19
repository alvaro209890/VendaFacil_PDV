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
import subprocess
import sys
import threading
import time
import webbrowser
from http.client import HTTPConnection, HTTPException

import uvicorn

from main import app, heartbeat_expirou
from paths import DATA_DIR

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


def _caminho_edge() -> str | None:
    """msedge.exe instalado nesta máquina (x64/x86/perfil do usuário)."""
    pastas = [
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("ProgramFiles"),
        os.environ.get("LocalAppData"),
    ]
    for pasta in pastas:
        if not pasta:
            continue
        caminho = os.path.join(pasta, "Microsoft", "Edge", "Application", "msedge.exe")
        if os.path.isfile(caminho):
            return caminho
    return None


def _abrir_navegador() -> None:
    """Abre o PDV em janela de app no Edge, imprimindo direto (sem diálogo).

    ``--kiosk-printing`` manda ``window.print()`` direto para a impressora
    padrão do Windows: o recibo sai sozinho quando a venda fecha (James,
    19/11/2026: o Edge normal abria a pré-visualização e exigia um clique).
    O ``--user-data-dir`` separado evita que um Edge já aberto engula a janela
    e ignore a flag. Sem Edge instalado, cai no navegador padrão (com diálogo).
    """
    url = f"http://{HOST}:{PORT}/"
    if sys.platform == "win32":
        edge = _caminho_edge()
        if edge:
            perfil = DATA_DIR / "edge-caixa"
            try:
                perfil.mkdir(parents=True, exist_ok=True)
                subprocess.Popen(
                    [
                        edge,
                        "--kiosk-printing",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--noerrdialogs",
                        f"--user-data-dir={perfil}",
                        f"--app={url}",
                    ],
                    close_fds=True,
                )
                return
            except OSError:
                logging.getLogger(__name__).exception("Falha ao abrir o Edge; usando navegador padrão.")
    webbrowser.open(url)


def _fechar_sem_navegador() -> bool:
    """Encerrar o servidor quando o navegador para de mandar heartbeat?

    Desligado por padrão: navegador minimizado ou em outra aba reduz o
    heartbeat a ~1 por minuto e o PDV caía sozinho no meio do expediente
    (James, 14/11 15:43 e 16/11 19:11). Reabrir o atalho já reaproveita a
    instância ativa, então deixar o servidor no ar não atrapalha.
    """
    return os.environ.get("VENDAFACIL_FECHAR_SEM_NAVEGADOR") == "1"


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
        if empacotado and abrir and _fechar_sem_navegador():
            threading.Thread(target=_vigiar_heartbeat, args=(servidor, parar), daemon=True).start()
        try:
            servidor.run(sockets=[porta])
        finally:
            parar.set()
            navegador.cancel()
    return 0


if __name__ == "__main__":
    sys.exit(main())
