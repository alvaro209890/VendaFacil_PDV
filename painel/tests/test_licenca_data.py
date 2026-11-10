"""L08: data inválida não vira licença perpétua; o dia vale até o fim em MT."""
from datetime import datetime, timezone
from main import _licenca_valida


def test_l08_data_invalida_nao_libera():
    ok, motivo = _licenca_valida({'ativo': True, 'licenca_expira_em': 'nao-e-data'})
    assert ok is False
    assert 'inválida' in motivo.lower() or 'invalida' in motivo.lower()


def test_l08_data_vale_ate_o_fim_do_dia_em_mt():
    conta = {'ativo': True, 'licenca_expira_em': '2026-11-10'}
    ainda = datetime(2026, 11, 11, 3, 0, tzinfo=timezone.utc)  # 23:00 em Cuiabá
    ok, _ = _licenca_valida(conta, ainda)
    assert ok is True
    depois = datetime(2026, 11, 11, 4, 0, tzinfo=timezone.utc)  # 00:00 do dia 11 em Cuiabá
    ok, motivo = _licenca_valida(conta, depois)
    assert ok is False
    assert 'expirada' in motivo.lower()
