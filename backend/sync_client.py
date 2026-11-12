"""Envio das vendas locais para o Painel SaaS (best-effort, offline-first).

As vendas são gravadas localmente primeiro (o caixa nunca espera a internet).
Um loop em segundo plano envia as pendentes ao painel quando há conexão; o que
não for enviado fica na fila e tenta de novo depois. É idempotente (cada venda
tem um UUID e o painel ignora duplicadas).
"""
import json
import threading
import urllib.error
import urllib.request
import uuid as uuidlib

import conta as conta_mod
from database import db

INTERVALO_SEG = 120
_TIMEOUT = 8


def _enviar(token: str, vendas: list[dict]) -> list[str]:
    url = f"{conta_mod.PAINEL_URL}/api/sync/vendas"
    body = json.dumps({"vendas": vendas}).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
        if r.status != 200:
            return []
        try:
            data = json.loads(r.read().decode() or "{}")
        except (UnicodeError, json.JSONDecodeError):
            return []
    if not isinstance(data, dict):
        return []
    if "aceitas" in data:
        aceitas = data["aceitas"]
        if not isinstance(aceitas, list) or not all(isinstance(u, str) for u in aceitas):
            return []
        return aceitas
    recebidas = data.get("recebidas")
    if type(recebidas) is int and recebidas == len(vendas):
        return [v["uuid"] for v in vendas]
    return []


def enviar_pendentes() -> int:
    """Envia as vendas ainda não sincronizadas. Retorna quantas foram aceitas."""
    if not conta_mod.licenca_obrigatoria():
        return 0
    token = conta_mod.token_sync()
    if not token:
        return 0
    pendentes = db.vendas_pendentes_sync()
    if not pendentes:
        return 0

    payload, ids = [], []
    for v in pendentes:
        if not v.get("uuid"):
            v["uuid"] = str(uuidlib.uuid4())
            db.set_venda_uuid(v["id"], v["uuid"])
        payload.append({
            "uuid": v["uuid"], "total": v["total"], "desconto": v["desconto"],
            "forma_pagamento": v["forma_pagamento"], "criado_em": v["criado_em"],
        })
        ids.append(v["id"])

    try:
        aceitas = set(_enviar(token, payload))
        ids_ok = [i for i, v in zip(ids, payload) if v["uuid"] in aceitas]
        db.marcar_vendas_sincronizadas(ids_ok)
        return len(ids_ok)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return 0  # offline → tenta no próximo ciclo
    return 0


def _loop(parar: threading.Event) -> None:
    while not parar.is_set():
        try:
            enviar_pendentes()
        except Exception:
            pass
        parar.wait(INTERVALO_SEG)


def iniciar_em_background(parar: threading.Event) -> threading.Thread | None:
    if not conta_mod.licenca_obrigatoria():
        return
    t = threading.Thread(target=_loop, args=(parar,), daemon=True, name="vf-sync")
    t.start()
    return t
