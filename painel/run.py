"""Sobe o Painel SaaS.

- Desenvolvimento local: `python run.py` (porta 8080).
- Render: usa este mesmo arquivo como start command; a porta vem da variável
  de ambiente PORT, que o Render injeta automaticamente.
- VPS: prefira o systemd (deploy/painel-vps/).
"""
import os
import uvicorn
from main import app

if __name__ == "__main__":
    # No Render a porta chega via $PORT; localmente cai no PAINEL_PORT.
    port = int(os.environ.get("PORT") or os.environ.get("PAINEL_PORT") or "8080")
    uvicorn.run(
        app,
        host=os.environ.get("PAINEL_HOST", "0.0.0.0"),
        port=port,
    )
