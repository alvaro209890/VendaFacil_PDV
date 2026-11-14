"""A versão de entrega é uma só: backend, instalador e roteiro andam juntos."""
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _versao_backend() -> str:
    texto = (ROOT / "backend/version.py").read_text(encoding="utf-8")
    achado = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', texto)
    assert achado, "APP_VERSION não encontrado em backend/version.py"
    return achado.group(1)


def test_versao_no_formato_x_y_z():
    assert re.fullmatch(r"\d+\.\d+\.\d+", _versao_backend()), _versao_backend()


@pytest.mark.parametrize("arquivo", ["installer/vendafacil.iss", "scripts/roteiro_exe.py"])
def test_versao_dos_arquivos_de_entrega_igual_ao_backend(arquivo):
    """Antes o teste fixava a versão e quebrava a cada entrega; agora cobra que
    os três arquivos contem a mesma versão do backend."""
    versao = _versao_backend()
    assert f'"{versao}"' in (ROOT / arquivo).read_text(encoding="utf-8")
