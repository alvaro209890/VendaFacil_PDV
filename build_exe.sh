#!/usr/bin/env bash
# Gera o executável do VendaFácil PDV no Linux (binário único).
# Para gerar o .exe de Windows, rode build_exe.bat NUMA MÁQUINA WINDOWS
# (o PyInstaller não faz cross-compile).
set -euo pipefail
cd "$(dirname "$0")"

# Node 20+ é necessário para o Vite 8. Ajuste se usar nvm:
#   nvm use 20
echo "==> Build do frontend (npm)"
npm install
npm run build

echo "==> Preparando ambiente Python"
cd backend
python3 -m venv .venv 2>/dev/null || true
.venv/bin/pip install -q -r requirements-build.txt

echo "==> Empacotando com PyInstaller"
.venv/bin/pyinstaller vendafacil.spec --noconfirm --distpath ../dist_exe --workpath ../build

echo
echo "OK! Executável gerado em: dist_exe/VendaFacilPDV"
echo "Rode com: ./dist_exe/VendaFacilPDV   (abre o navegador em http://127.0.0.1:3020)"
