"""Sobe o Painel SaaS (use em desenvolvimento). Na VPS, prefira o systemd."""
import os
import uvicorn
from main import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.environ.get("PAINEL_HOST", "0.0.0.0"),
        port=int(os.environ.get("PAINEL_PORT", "8080")),
    )
