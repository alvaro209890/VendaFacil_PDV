"""Proteção simples contra força-bruta no login (em memória).

Conta as falhas por chave (ex.: e-mail/login). Após MAX falhas dentro de
JANELA segundos, bloqueia novas tentativas por COOLDOWN segundos. Em caso de
sucesso, zera o contador da chave.

Como o painel roda com 1 worker no Render, o estado em memória é suficiente.
"""
import time
import threading

MAX = 5
JANELA = 300        # 5 min para acumular falhas
COOLDOWN = 300      # bloqueio de 5 min após estourar

_lock = threading.Lock()
_falhas: dict[str, list[float]] = {}
_bloqueio: dict[str, float] = {}


def bloqueado(chave: str) -> int:
    """Retorna os segundos restantes de bloqueio (0 se liberado)."""
    chave = (chave or "").lower()
    with _lock:
        ate = _bloqueio.get(chave, 0)
        rest = int(ate - time.time())
        return rest if rest > 0 else 0


def registrar_falha(chave: str) -> None:
    chave = (chave or "").lower()
    agora = time.time()
    with _lock:
        tentativas = [t for t in _falhas.get(chave, []) if agora - t < JANELA]
        tentativas.append(agora)
        _falhas[chave] = tentativas
        if len(tentativas) >= MAX:
            _bloqueio[chave] = agora + COOLDOWN
            _falhas[chave] = []


def limpar(chave: str) -> None:
    chave = (chave or "").lower()
    with _lock:
        _falhas.pop(chave, None)
        _bloqueio.pop(chave, None)
