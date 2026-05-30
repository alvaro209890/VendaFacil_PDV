# -*- mode: python ; coding: utf-8 -*-
# Empacota o VendaFácil PDV num único executável (onefile).
# Uso:  pyinstaller vendafacil.spec   (rodar dentro de backend/)
# O frontend buildado (../dist) é embutido e servido pelo próprio FastAPI.
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

here = SPECPATH
dist_dir = os.path.join(here, "..", "dist")

datas = [(dist_dir, "dist")]
# qrcode embute fontes/recursos próprios em alguns casos
datas += collect_data_files("qrcode")

# uvicorn carrega loops/protocolos dinamicamente — precisa coletar submódulos
hiddenimports = collect_submodules("uvicorn")

a = Analysis(
    ["run.py"],
    pathex=[here],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="VendaFacilPDV",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=True,          # mostra janela de log; troque para False se quiser ocultar
    # icon="icone.ico",    # opcional: aponte para um .ico (Windows) se quiser ícone próprio
)
