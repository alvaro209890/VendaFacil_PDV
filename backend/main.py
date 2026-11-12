import os
import sys
import threading
import time

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from paths import resource_path
from auth import router as auth_router, _verificar_jwt
import conta as conta_mod
from pydantic import BaseModel
from produtos import router as produtos_router
from vendas import router as vendas_router
from categorias import router as categorias_router
from clientes import router as clientes_router
from contas_receber import router as contas_receber_router
from pix import router as pix_router
from mercadopago import router as maquininha_router
from caixa import router as caixa_router
from backup import router as backup_router
from fiscal_config import router as fiscal_config_router
from fiscal_router import router as fiscal_router, nfe_router
from fiscal_servicos_router import router as fiscal_servicos_router
from database import db
from errors import configure_error_logging, register_error_handlers

configure_error_logging()


def urls_doc(empacotado: bool) -> dict:
    if empacotado:
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}


app = FastAPI(title="VendaFácil PDV", version="0.1.0", **urls_doc(getattr(sys, "frozen", False)))

# ── Watchdog: encerra o processo quando a aba do navegador é fechada ──
# Só ativo no .exe empacotado (sys.frozen). Em dev, o Uvicorn já cuida disso.
_HEARTBEAT_TIMEOUT = 30   # segundos sem ping → encerra
_HEARTBEAT_INTERVAL = 5   # frequência de verificação do watchdog
_ultimo_heartbeat: float = time.monotonic()


def _watchdog_loop() -> None:
    """Thread daemon: mata o processo se não receber heartbeat por TIMEOUT segundos."""
    while True:
        time.sleep(_HEARTBEAT_INTERVAL)
        if time.monotonic() - _ultimo_heartbeat > _HEARTBEAT_TIMEOUT:
            os._exit(0)


if getattr(sys, "frozen", False):
    _t = threading.Thread(target=_watchdog_loop, daemon=True, name="heartbeat-watchdog")
    _t.start()
register_error_handlers(app)

def _origens_pdv() -> list[str]:
    porta = os.environ.get("VENDAFACIL_PORT", "3020")
    origens = [
        f"http://127.0.0.1:{porta}",
        f"http://localhost:{porta}",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
    extra = os.environ.get("VENDAFACIL_CORS_ORIGINS", "")
    origens.extend(item.strip() for item in extra.split(",") if item.strip())
    return origens


app.add_middleware(
    CORSMiddleware,
    allow_origins=_origens_pdv(),
    allow_methods=["*"],
    allow_headers=["*"],
)

_ROTAS_PUBLICAS = {
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/registro"),
    ("GET", "/api/ativacao/status"),
    ("POST", "/api/ativacao"),
    ("POST", "/api/heartbeat"),
    ("GET", "/api/recuperacao"),
}

_GETS_COM_EFEITOS = {"/api/backup/exportar", "/api/maquininha/dispositivos",
                    "/api/maquininha/diagnostico", "/api/fiscal/servicos/status"}


@app.middleware("http")
async def exige_token_api(request: Request, call_next):
    path = request.url.path
    if request.method != "OPTIONS" and path.startswith("/api/") and (request.method, path) not in _ROTAS_PUBLICAS:
        header = request.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        if not token or not _verificar_jwt(token):
            return JSONResponse({"detail": "Token não informado."}, status_code=401)
    operacao_consulta = request.method == "GET" and path.rstrip("/") not in _GETS_COM_EFEITOS \
        and not path.startswith("/api/maquininha/cobranca/")
    if (db.modo_consulta and path.startswith("/api/") and not operacao_consulta
            and request.method != "OPTIONS"
            and (request.method, path) not in {("POST", "/api/auth/login"), ("POST", "/api/heartbeat")}):
        return JSONResponse({"detail": "Modo consulta: restaure o banco para voltar a operar."}, status_code=503)
    return await call_next(request)


@app.middleware("http")
async def normalize_leading_slashes(request: Request, call_next):
    path = request.scope.get("path", "")
    if isinstance(path, str) and path.startswith("//"):
        request.scope["path"] = "/" + path.lstrip("/")
    return await call_next(request)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(categorias_router, prefix="/api/categorias", tags=["categorias"])
app.include_router(produtos_router, prefix="/api/produtos", tags=["produtos"])
app.include_router(vendas_router, prefix="/api/vendas", tags=["vendas"])
app.include_router(fiscal_servicos_router, prefix="/api/fiscal/servicos", tags=["fiscal"])
app.include_router(clientes_router, prefix="/api/clientes", tags=["clientes"])
app.include_router(contas_receber_router, prefix="/api/contas-receber", tags=["contas-receber"])
app.include_router(pix_router, prefix="/api/pix", tags=["pix"])
app.include_router(maquininha_router, prefix="/api/maquininha", tags=["maquininha"])
app.include_router(caixa_router, prefix="/api/caixa", tags=["caixa"])
app.include_router(backup_router, prefix="/api/backup", tags=["backup"])
app.include_router(fiscal_config_router, prefix="/api/fiscal/config", tags=["fiscal"])
app.include_router(fiscal_router, prefix="/api/fiscal/nfce", tags=["fiscal"])
app.include_router(nfe_router, prefix="/api/fiscal/nfe", tags=["fiscal"])


def _get_user_id(request: Request) -> int:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não informado.")
    payload = _verificar_jwt(auth[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return int(payload["sub"])


@app.on_event("startup")
async def _iniciar_servicos() -> None:
    if db.modo_consulta:
        return
    import sync_client
    import fiscal
    import backup
    sync_client.iniciar_em_background()
    fiscal.iniciar_em_background()
    backup.iniciar_em_background()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "app": "vendafacil-pdv", "version": app.version}


@app.post("/api/heartbeat", include_in_schema=False)
async def heartbeat() -> dict:
    """Sinal de vida do frontend. Sem este ping por 30s o processo encerra."""
    global _ultimo_heartbeat
    _ultimo_heartbeat = time.monotonic()
    return {"ok": True}


# ── Ativação / licença (controle central pelo Painel SaaS) ──
class AtivacaoInput(BaseModel):
    login: str
    senha: str


@app.get("/api/ativacao/status")
async def ativacao_status() -> dict:
    return conta_mod.status(online=False) if db.modo_consulta else conta_mod.status()


@app.get("/api/recuperacao", include_in_schema=False)
async def recuperacao() -> dict:
    return {"somente_consulta": db.modo_consulta,
            "ultimo_backup": str(db.backup_recuperacao) if db.backup_recuperacao else None}


@app.post("/api/ativacao")
async def ativar(data: AtivacaoInput) -> dict:
    try:
        return conta_mod.ativar(data.login, data.senha)
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.get("/api/dashboard")
async def dashboard(request: Request) -> dict:
    user_id = _get_user_id(request)
    return db.get_dashboard(user_id)


@app.get("/api/relatorios/vendas")
async def relatorio_vendas(request: Request, inicio: str | None = None, fim: str | None = None) -> dict:
    user_id = _get_user_id(request)
    from datetime import date
    hoje = date.today().isoformat()
    if not inicio:
        inicio = hoje[:8] + "01"   # 1º dia do mês corrente
    if not fim:
        fim = hoje
    return db.relatorio_vendas(user_id, inicio, fim)


@app.get("/api/relatorios/fiscal")
async def relatorio_fiscal(request: Request, inicio: str | None = None, fim: str | None = None) -> dict:
    """Faturamento segregado por tratamento tributário (ICMS-ST / monofásico),
    para a apuração do Simples Nacional (PGDAS-D) sem bitributação."""
    user_id = _get_user_id(request)
    from datetime import date
    hoje = date.today().isoformat()
    if not inicio:
        inicio = hoje[:8] + "01"
    if not fim:
        fim = hoje
    return db.relatorio_fiscal_segregado(user_id, inicio, fim)


# ── Frontend embutido (serve o build do React na mesma origem) ──
# Habilitado automaticamente quando a pasta 'dist' existe ao lado do app
# (caso do .exe). Assim o sistema roda 100% local: abrir o navegador na
# porta do backend já mostra o PDV.
_DIST = resource_path("dist")
if _DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    async def _spa_root() -> FileResponse:
        return FileResponse(str(_DIST / "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str):
        # Rotas de API não resolvidas não devem cair no HTML do SPA.
        if full_path.startswith("api/") or full_path == "health":
            raise HTTPException(status_code=404, detail="Not Found")
        arquivo = _DIST / full_path
        if arquivo.is_file():
            return FileResponse(str(arquivo))
        return FileResponse(str(_DIST / "index.html"))
