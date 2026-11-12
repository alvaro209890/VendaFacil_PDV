"""Estado operacional sem exportar dados de clientes ou credenciais."""
import base64
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates

import backup
import fiscal_direto
from database import db, verificar_integridade
from version import APP_VERSION


def _integro(arquivo: Path) -> bool:
    try:
        verificar_integridade(arquivo)
        return True
    except ValueError:
        return False


def _ultimo_backup() -> dict | None:
    arquivos = backup.BACKUP_DIR.glob("vendafacil-*.db")
    try:
        ultimo = max(arquivos, key=lambda p: p.stat().st_mtime_ns, default=None)
        if ultimo is None:
            return None
        modificado = datetime.fromtimestamp(ultimo.stat().st_mtime, timezone.utc)
    except OSError:
        return None
    return {"nome": ultimo.name, "criado_em": modificado.isoformat(), "integro": _integro(ultimo)}


def _certificado(config: dict) -> tuple[bool | None, str | None]:
    arquivo = config.get("certificado_a1_b64")
    senha = config.get("certificado_senha")
    if not arquivo or not senha:
        return None, None
    try:
        chave, cert, _ = load_key_and_certificates(base64.b64decode(arquivo, validate=True), senha.encode())
        if cert is not None and chave is not None:
            agora = datetime.now(timezone.utc)
            return (cert.not_valid_before_utc <= agora < cert.not_valid_after_utc,
                    cert.not_valid_after_utc.isoformat())
    except (TypeError, ValueError):
        pass
    return False, None


def _servico(config: dict, apto: bool | None) -> dict:
    if (not apto or not config.get("habilitado") or db.modo_consulta or config.get("ambiente") != "homologacao"
            or (config.get("provedor_fiscal") or "sefaz_mt_direto") != "sefaz_mt_direto"):
        return {"situacao": "não consultado", "cstat": None}
    try:
        resultado = fiscal_direto.status_servico("65", config)
        cstat = str(resultado.get("cstat") or "")
        if len(cstat) == 3 and cstat.isascii() and cstat.isdigit():
            return {"situacao": "consultado", "cstat": cstat}
    except fiscal_direto.FiscalDiretoError:
        pass
    return {"situacao": "indisponível", "cstat": None}


def resumo(user_id: int) -> dict:
    caminho = Path(db.caminho_db())
    try:
        config = db.get_config_fiscal()
        pendentes, contingencia, ultima_sync = db.contagens_diagnostico(user_id)
    except sqlite3.Error:
        # Backup anterior à migração pode ser aberto em modo consulta.
        config, pendentes, contingencia, ultima_sync = {}, None, None, None
    valido, vence = _certificado(config)
    ambiente = config.get("ambiente")
    return {
        "versao": APP_VERSION,
        "banco": {"caminho": str(caminho), "bytes": caminho.stat().st_size if caminho.is_file() else 0,
                  "livre_bytes": shutil.disk_usage(caminho.parent).free, "integro": _integro(caminho)},
        "ultimo_backup": _ultimo_backup(),
        "fiscal": {"ambiente": ambiente if ambiente in {"homologacao", "producao"} else None,
                   "certificado_valido": valido, "certificado_vence_em": vence,
                   "sefaz": _servico(config, valido), "pendentes": pendentes, "contingencia": contingencia},
        "ultima_sincronizacao": ultima_sync,
    }
