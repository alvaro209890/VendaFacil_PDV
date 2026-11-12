"""X15/P36: prazo de cancelamento contado da autorização (dhRecbto), não da criação."""
from datetime import datetime, timedelta, timezone

import pytest

import fiscal


def _iso(minutos_atras: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutos_atras)).isoformat()


def _nota(modelo: str, *, criado: int, autorizado: int | None):
    nota = {"modelo": modelo, "criado_em": _iso(criado)}
    if autorizado is not None:
        nota["autorizado_em"] = _iso(autorizado)
    return nota


def test_x15_nfce_recem_autorizada_permite_cancelar_mesmo_criada_ha_horas():
    # A venda pode ter sido criada de manhã e a nota autorizada agora (retentativa
    # ou contingência transmitida depois): o prazo conta da autorização.
    nota = _nota("65", criado=180, autorizado=1)
    fiscal._verificar_prazo_cancelamento(nota)  # não levanta


def test_x15_nfce_fora_dos_30_minutos_da_autorizacao_recusa():
    nota = _nota("65", criado=10, autorizado=40)
    with pytest.raises(fiscal.FiscalError, match="30 minutos"):
        fiscal._verificar_prazo_cancelamento(nota)


def test_x15_nfe_usa_prazo_de_2_horas_da_autorizacao():
    fiscal._verificar_prazo_cancelamento(_nota("55", criado=600, autorizado=60))
    with pytest.raises(fiscal.FiscalError, match="2 horas"):
        fiscal._verificar_prazo_cancelamento(_nota("55", criado=5, autorizado=150))


def test_x15_sem_autorizado_em_cai_para_criado_em():
    # Notas antigas (antes da coluna) continuam com o comportamento anterior.
    with pytest.raises(fiscal.FiscalError):
        fiscal._verificar_prazo_cancelamento(_nota("65", criado=60, autorizado=None))
    fiscal._verificar_prazo_cancelamento(_nota("65", criado=5, autorizado=None))


@pytest.mark.parametrize("modelo,idade,permite", [("65", 29, True), ("65", 40, False),
                                                ("55", 119, True), ("55", 130, False)])
def test_x11_mesmo_instante_utc_e_mt_na_virada_de_mes(monkeypatch, modelo, idade, permite):
    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 12, 1, 4, 5, tzinfo=timezone.utc).astimezone(tz)
    monkeypatch.setattr(fiscal, "datetime", Relogio)
    instante = Relogio.now(timezone.utc) - timedelta(minutes=idade)
    for referencia in (instante.isoformat(), instante.astimezone(timezone(timedelta(hours=-4))).isoformat()):
        nota = {"modelo": modelo, "autorizado_em": referencia}
        if permite:
            fiscal._verificar_prazo_cancelamento(nota)
        else:
            with pytest.raises(fiscal.FiscalError):
                fiscal._verificar_prazo_cancelamento(nota)
