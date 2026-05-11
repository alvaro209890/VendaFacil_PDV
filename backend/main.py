from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from auth import router as auth_router, _verificar_jwt
from produtos import router as produtos_router
from vendas import router as vendas_router
from categorias import router as categorias_router
from clientes import router as clientes_router
from contas_receber import router as contas_receber_router
from pix import router as pix_router
from database import db

app = FastAPI(title="VendaFácil PDV", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(categorias_router, prefix="/api/categorias", tags=["categorias"])
app.include_router(produtos_router, prefix="/api/produtos", tags=["produtos"])
app.include_router(vendas_router, prefix="/api/vendas", tags=["vendas"])
app.include_router(clientes_router, prefix="/api/clientes", tags=["clientes"])
app.include_router(contas_receber_router, prefix="/api/contas-receber", tags=["contas-receber"])
app.include_router(pix_router, prefix="/api/pix", tags=["pix"])


def _get_user_id(request: Request) -> int:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não informado.")
    payload = _verificar_jwt(auth[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    return int(payload["sub"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "app": "vendafacil-pdv", "version": app.version}


@app.get("/api/dashboard")
async def dashboard(request: Request) -> dict:
    user_id = _get_user_id(request)
    return db.get_dashboard(user_id)
