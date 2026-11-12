"""Backup local do banco do PDV.

Os dados do lojista ficam num SQLite na própria máquina. Aqui o lojista pode:
  - baixar um backup (.db) a qualquer momento;
  - restaurar a partir de um backup;
  - contar com backups automáticos diários (mantém os últimos N).

Tudo local — não depende de internet.
"""
import logging
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from auth import _verificar_jwt
from database import db, verificar_integridade
from paths import DATA_DIR

router = APIRouter()
log = logging.getLogger(__name__)

BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

MANTER = int(os.environ.get("VENDAFACIL_BACKUPS_MANTER", "14"))   # quantos guardar
INTERVALO_SEG = int(os.environ.get("VENDAFACIL_BACKUP_INTERVALO_SEG", str(24 * 3600)))


def _auth(request: Request) -> int:
    auth = request.headers.get("Authorization", "")
    payload = _verificar_jwt(auth[7:]) if auth.startswith("Bearer ") else None
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return int(payload["sub"])


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def _gerar_backup(prefixo: str = "backup") -> Path:
    destino = BACKUP_DIR / f"vendafacil-{prefixo}-{_stamp()}.db"
    with tempfile.TemporaryDirectory(prefix=".vf-backup-", dir=BACKUP_DIR) as pasta:
        temporario = Path(pasta) / "copia.db"
        db.backup_para(temporario)
        try:
            verificar_integridade(temporario)
        except ValueError:
            log.error("Backup descartado por falha de integridade.")
            raise
        temporario.replace(destino)
    return destino


def _limpar_antigos() -> None:
    arquivos = sorted(BACKUP_DIR.glob("vendafacil-auto-*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in arquivos[MANTER:]:
        try:
            p.unlink()
        except OSError as exc:
            log.warning("Falha na retenção de backup (%s).", type(exc).__name__)


# ── Rotas ──
@router.get("/exportar")
def exportar(request: Request):
    """Gera e baixa um backup (.db) consistente do banco."""
    _auth(request)
    caminho = _gerar_backup("manual")
    return FileResponse(
        str(caminho), media_type="application/octet-stream", filename=caminho.name
    )


@router.get("/listar")
def listar(request: Request) -> dict:
    _auth(request)
    itens = []
    for p in sorted(BACKUP_DIR.glob("vendafacil-*.db"), key=lambda x: x.stat().st_mtime, reverse=True):
        st = p.stat()
        itens.append({
            "nome": p.name,
            "tamanho_kb": round(st.st_size / 1024, 1),
            "data": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
        })
    return {"backups": itens, "pasta": str(BACKUP_DIR)}


@router.post("/restaurar")
async def restaurar(request: Request) -> dict:
    """Restaura o banco a partir de um arquivo .db enviado no corpo.

    Antes de substituir, salva o banco atual como 'pre-restauracao' por segurança.
    """
    _auth(request)
    raw = await request.body()
    if not raw:
        raise HTTPException(status_code=400, detail="Envie o arquivo de backup (.db).")
    return await run_in_threadpool(_restaurar_bytes, raw)


def _restaurar_bytes(raw: bytes) -> dict:
    try:
        with tempfile.TemporaryDirectory(prefix=".vf-upload-", dir=BACKUP_DIR) as pasta:
            arquivo = Path(pasta) / "backup.db"
            arquivo.write_bytes(raw)
            db.restaurar_de(arquivo, lambda: _gerar_backup("pre-restauracao"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


# ── Backup automático em segundo plano ──
def _loop(parar: threading.Event) -> None:
    while not parar.is_set():
        try:
            _gerar_backup("auto")
            _limpar_antigos()
        except Exception as exc:
            log.error("Backup automático falhou (%s).", type(exc).__name__)
        parar.wait(INTERVALO_SEG)


def iniciar_em_background(parar: threading.Event) -> threading.Thread:
    tarefa = threading.Thread(target=_loop, args=(parar,), daemon=True, name="vf-backup")
    tarefa.start()
    return tarefa
