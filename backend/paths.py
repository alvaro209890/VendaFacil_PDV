"""Resolução de caminhos portátil — funciona em desenvolvimento, no Render
e empacotado como .exe/binário (PyInstaller)."""
import os
import sys
from pathlib import Path


def data_dir() -> Path:
    """Pasta gravável para banco e segredos.

    Ordem de prioridade:
    1. VENDAFACIL_DATA_DIR (env) — usado no Render/servidor.
    2. Pasta "dados" ao lado do executável — quando empacotado (.exe).
    3. Pasta "dados" na raiz do projeto — em desenvolvimento.
    """
    env = os.environ.get("VENDAFACIL_DATA_DIR")
    if env:
        return Path(env)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "dados"
    return Path(__file__).resolve().parent.parent / "dados"


def resource_path(rel: str) -> Path:
    """Caminho de recursos somente-leitura embutidos (ex: frontend 'dist').

    Quando empacotado, o PyInstaller extrai os recursos em sys._MEIPASS.
    """
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    else:
        base = Path(__file__).resolve().parent.parent
    return base / rel


DATA_DIR = data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)
