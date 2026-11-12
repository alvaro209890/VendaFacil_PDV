"""S13: dois processos/conexões não podem inicializar dois administradores."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import database


def test_s13_bootstrap_atomico_em_conexoes_distintas(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DB_PATH', tmp_path / 'bootstrap.db')
    primeiro = database.Database()
    segundo = database.Database()
    barreira = Barrier(2)

    def criar(par):
        db, login = par
        barreira.wait(timeout=5)
        return db.create_admin(login, 'Admin de teste', 'hash_fixture')

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(criar, [(primeiro, 'um'), (segundo, 'dois')]))
        assert sum(r is not None for r in resultados) == 1
        assert primeiro.count_admins() == 1
        assert segundo.create_admin('tres', 'Terceiro', 'hash_fixture') is None
    finally:
        primeiro._conn.close()
        segundo._conn.close()
