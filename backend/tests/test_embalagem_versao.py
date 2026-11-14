from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('arquivo',['backend/version.py','installer/vendafacil.iss','scripts/roteiro_exe.py'])
def test_entrega_caixa_unidade_1016(arquivo):
    assert '"1.0.16"' in (ROOT/arquivo).read_text(encoding='utf-8')
