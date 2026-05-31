"""Ativação e licença do PDV (offline-first).

O login da loja é controlado centralmente pelo Painel SaaS (na VPS). O PDV:
  1. Ativa uma vez informando login/senha da loja (exige internet nesse momento).
  2. Guarda o resultado em dados/conta.json (token + validade + status).
  3. Revalida online periodicamente (padrão a cada 12h) quando há internet; nos
     logins entre uma revalidação e outra usa o cache (instantâneo, sem rede).
     Offline, continua funcionando dentro de um período de carência (padrão 30
     dias). Se a conta estiver bloqueada/vencida no cache, revalida sempre, para
     o desbloqueio/renovação aplicar assim que reconectar.
  4. Se você bloquear/expirar a conta no painel, na próxima revalidação online
     o PDV trava.

Se VENDAFACIL_PAINEL_URL não estiver definido, a licença é DESLIGADA e o
sistema roda 100% local (útil em desenvolvimento ou venda sem controle central).
"""
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

from paths import DATA_DIR

try:
    from painel_config import PAINEL_URL as _PAINEL_PADRAO
except ImportError:
    _PAINEL_PADRAO = ""

# Env tem prioridade; senão usa o valor embutido no build (painel_config.py).
PAINEL_URL = (os.environ.get("VENDAFACIL_PAINEL_URL") or _PAINEL_PADRAO).rstrip("/")
CARENCIA_DIAS = int(os.environ.get("VENDAFACIL_CARENCIA_DIAS", "30"))
# De quanto em quanto tempo revalidar online quando a licença está saudável.
# Entre uma revalidação e outra, o login usa o cache (instantâneo, sem rede).
REVALIDA_INTERVALO_HORAS = int(os.environ.get("VENDAFACIL_REVALIDA_HORAS", "12"))
CONTA_FILE = DATA_DIR / "conta.json"
_TIMEOUT = 6


def licenca_obrigatoria() -> bool:
    return bool(PAINEL_URL)


def _horas_desde(iso: str | None) -> float:
    d = _parse(iso)
    if not d:
        return 1e9
    return (_now() - d).total_seconds() / 3600.0


def _cache_saudavel(estado: dict) -> bool:
    """Cache OK = conta ativa e licença ainda na validade. Quando NÃO saudável
    (bloqueada/vencida), revalidamos sempre para o desbloqueio/renovação aplicar
    assim que houver internet."""
    if not estado.get("ativo", True):
        return False
    venc = _parse(estado.get("licenca_expira_em"))
    if venc and venc < _now():
        return False
    return True


def _precisa_revalidar(estado: dict) -> bool:
    if not _cache_saudavel(estado):
        return True
    return _horas_desde(estado.get("validado_em")) >= REVALIDA_INTERVALO_HORAS


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        d = datetime.fromisoformat(iso)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _load() -> dict | None:
    if not CONTA_FILE.exists():
        return None
    try:
        return json.loads(CONTA_FILE.read_text())
    except (ValueError, OSError):
        return None


def _save(d: dict) -> None:
    CONTA_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2))


def _http(method: str, path: str, body: dict | None = None, token: str | None = None):
    url = f"{PAINEL_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
        return r.status, json.loads(r.read().decode())


def ativar(login: str, senha: str) -> dict:
    """Primeira ativação — precisa de internet. Retorna o status já calculado."""
    if not licenca_obrigatoria():
        return status()
    try:
        _, data = _http("POST", "/api/conta/validar", {"login": login, "senha": senha})
    except urllib.error.HTTPError as e:
        try:
            detalhe = json.loads(e.read().decode()).get("detail", "Falha na ativação.")
        except Exception:
            detalhe = "Login ou senha incorretos."
        raise ValueError(detalhe)
    except urllib.error.URLError:
        raise ConnectionError("Sem conexão com o servidor. A 1ª ativação exige internet.")

    conta = data.get("conta", {})
    _save({
        "login": conta.get("login", login),
        "nome_loja": conta.get("nome_loja"),
        "token": data.get("token"),
        "ativo": conta.get("ativo", True),
        "licenca_expira_em": conta.get("licenca_expira_em"),
        "validado_em": _now().isoformat(),
    })
    if not data.get("ok"):
        raise ValueError(data.get("motivo", "Conta inativa."))
    return status()


def revalidar() -> dict | None:
    """Tenta atualizar o status junto ao painel usando o token salvo."""
    estado = _load()
    if not estado or not estado.get("token") or not licenca_obrigatoria():
        return estado
    try:
        _, data = _http("GET", "/api/conta/status", token=estado["token"])
    except (urllib.error.URLError, urllib.error.HTTPError):
        return estado  # offline → mantém cache
    estado.update({
        "ativo": data.get("ativo", estado.get("ativo")),
        "licenca_expira_em": data.get("licenca_expira_em"),
        "validado_em": _now().isoformat(),
    })
    _save(estado)
    return estado


def status() -> dict:
    """Estado da licença para a UI/login decidir liberar ou bloquear."""
    if not licenca_obrigatoria():
        return {"obrigatoria": False, "ativado": True, "bloqueado": False, "motivo": "Licença desativada (modo local)."}

    estado = _load()
    if not estado:
        return {"obrigatoria": True, "ativado": False, "bloqueado": True, "motivo": "Ative o sistema com a conta da loja."}

    # Revalida online de forma silenciosa SÓ quando necessário (cache vencido/
    # bloqueado, ou passou o intervalo). Caso contrário usa o cache — login
    # instantâneo e sem depender de rede.
    if _precisa_revalidar(estado):
        estado = revalidar() or estado

    motivo = "ok"
    bloqueado = False

    if not estado.get("ativo", True):
        bloqueado, motivo = True, "Conta bloqueada. Contate o suporte."

    venc = _parse(estado.get("licenca_expira_em"))
    if not bloqueado and venc and venc < _now():
        bloqueado, motivo = True, "Licença expirada. Renove para continuar."

    validado = _parse(estado.get("validado_em"))
    dias_offline = (_now() - validado).days if validado else 9999
    em_carencia = dias_offline <= CARENCIA_DIAS
    if not bloqueado and not em_carencia:
        bloqueado = True
        motivo = "Sem validação há muito tempo. Conecte à internet para revalidar."

    return {
        "obrigatoria": True,
        "ativado": True,
        "bloqueado": bloqueado,
        "motivo": motivo,
        "nome_loja": estado.get("nome_loja"),
        "licenca_expira_em": estado.get("licenca_expira_em"),
        "dias_desde_validacao": dias_offline,
        "carencia_dias": CARENCIA_DIAS,
    }


def token_sync() -> str | None:
    estado = _load()
    return estado.get("token") if estado else None
