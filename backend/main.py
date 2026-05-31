from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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
from database import db

app = FastAPI(title="VendaFácil PDV", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    import sync_client
    import fiscal
    import backup
    sync_client.iniciar_em_background()
    fiscal.iniciar_em_background()
    backup.iniciar_em_background()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "app": "vendafacil-pdv", "version": app.version}


# ── Ativação / licença (controle central pelo Painel SaaS) ──
class AtivacaoInput(BaseModel):
    login: str
    senha: str


@app.get("/api/ativacao/status")
async def ativacao_status() -> dict:
    return conta_mod.status()


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
