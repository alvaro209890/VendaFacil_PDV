"""U07: total do dia independente da página e do fuso do computador."""
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
import database
import vendas
from auth import _agora, _gerar_jwt, _token_user
from main import app


@pytest.fixture
def dia_mt(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_DIR', tmp_path)
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'diario.db')
    local = database.Database()
    monkeypatch.setattr(vendas, 'db', local)
    dono = local.create_user('dono', 'Dono', 'hash_fixture', _agora())
    outro = local.create_user('outro', 'Outro', 'hash_fixture', _agora())
    with local._lock, local._conn:
        def inserir(uid, total, instante, status='concluida'):
            local._conn.execute(
                "INSERT INTO vendas (user_id,total,desconto,forma_pagamento,status,criado_em) VALUES (?,?,0,'dinheiro',?,?)",
                (uid, total, status, instante))
        for _ in range(101):
            inserir(dono['id'], .1, '2026-11-12T04:00:00+00:00')
        inserir(dono['id'], .2, '2026-11-12T23:59:59-04:00')
        inserir(dono['id'], 700, '2026-11-12T03:59:59+00:00')
        inserir(dono['id'], 900, '2026-11-13T04:00:00+00:00')
        inserir(dono['id'], 800, '2026-11-12T12:00:00+00:00', 'cancelada')
        inserir(outro['id'], 600, '2026-11-12T12:00:00+00:00')
    headers = {'Authorization': 'Bearer ' + _gerar_jwt(_token_user(dono))}
    with TestClient(app) as client:
        yield client, local, headers
    local.close()


@pytest.mark.parametrize('pagina', ['limit=100', 'limit=1&offset=100'])
def test_u07_api_total_sem_truncar_e_sem_canceladas(dia_mt, monkeypatch, pagina):
    api, _, headers = dia_mt
    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):
            # Em SP já é dia 13, mas em MT ainda é dia 12.
            return datetime(2026, 11, 13, 3, 30, tzinfo=timezone.utc).astimezone(tz)
    monkeypatch.setattr(database, 'datetime', Relogio, raising=False)
    r = api.get('/api/vendas?' + pagina, headers=headers)
    assert r.status_code == 200
    assert r.json().get('resumo_hoje') == {
        'data': '2026-11-12', 'fuso': 'America/Cuiaba', 'quantidade': 102, 'total': 10.3}


@pytest.mark.parametrize('instante,dia', [
    (datetime(2026, 12, 1, 3, 30, tzinfo=timezone.utc), '2026-11-30'),
    (datetime(2027, 1, 1, 3, 30, tzinfo=timezone.utc), '2026-12-31'),
])
def test_u07_virada_mes_e_ano(dia_mt, monkeypatch, instante, dia):
    _, local, _ = dia_mt
    dono = local.get_user_by_usuario('dono')['id']
    with local._conn:
        for timestamp, valor in [(dia + 'T23:59:59-04:00', .25),
                                  (instante.date().isoformat() + 'T04:00:00+00:00', 500)]:
            local._conn.execute(
                "INSERT INTO vendas (user_id,total,desconto,forma_pagamento,status,criado_em) "
                "VALUES (?,?,0,'dinheiro','concluida',?)", (dono, valor, timestamp))
    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):
            return instante.astimezone(tz)
    monkeypatch.setattr(database, 'datetime', Relogio)
    assert local.resumo_vendas_hoje(dono) == {
        'data': dia, 'fuso': 'America/Cuiaba', 'quantidade': 1, 'total': .25}
