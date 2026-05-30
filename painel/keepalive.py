"""Anti-hibernação no Render free.

O Render free derruba o serviço após ~15 min sem requisições. Quando
`RENDER_EXTERNAL_URL` está definido (o Render injeta essa variável com a URL
pública automaticamente), um loop em background pinga o próprio `/health` a
cada ~10 min, gerando tráfego e mantendo a instância acordada.

Fora do Render (desenvolvimento/local) a variável não existe e nada roda.
Ajuste o intervalo com KEEPALIVE_INTERVALO_SEG (padrão 600s).
"""
import os
import threading
import time
import urllib.request

INTERVALO_SEG = int(os.environ.get("KEEPALIVE_INTERVALO_SEG", "600"))


def _loop(url: str) -> None:
    while True:
        time.sleep(INTERVALO_SEG)
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                r.read()
        except Exception:
            pass  # best-effort; tenta de novo no próximo ciclo


def iniciar_em_background() -> None:
    base = os.environ.get("RENDER_EXTERNAL_URL")
    if not base:
        return  # só no Render
    url = base.rstrip("/") + "/health"
    threading.Thread(target=_loop, args=(url,), daemon=True, name="keepalive").start()
