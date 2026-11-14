from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('arquivo',['backend/version.py','installer/vendafacil.iss','scripts/roteiro_exe.py'])
def test_entrega_embalagem_1015(arquivo):
    assert '"1.0.15"' in (ROOT/arquivo).read_text(encoding='utf-8')
