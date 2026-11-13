"""Copia as tabelas do painel de um Postgres (Supabase) para o SQLite do painel.

Uso (na VPS, com o servico parado):

    /opt/vendafacil/venv/bin/python migrar_supabase_para_sqlite.py \
        --origem "postgresql://..." --destino /opt/vendafacil/dados/painel.db

- Cria o schema do proprio painel (o mesmo de `painel/database.py`) se faltar.
- Preserva os ids e a ordem das tabelas.
- Recusa um destino que ja tenha linhas (para nao duplicar nem sobrescrever).
- Nunca imprime a connection string nem os hashes de senha.

A senha de admin continua valida (PBKDF2 e a mesma funcao nos dois bancos),
mas os tokens JWT antigos nao: todos precisam entrar de novo.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

TABELAS = ["admins", "contas", "vendas_sync", "fin_config", "fin_custos"]


def _schema_do_painel() -> str:
    raiz = Path(__file__).resolve().parent
    candidatos = [raiz / "painel", Path("/opt/vendafacil/painel"), raiz]
    for pasta in candidatos:
        if (pasta / "database.py").exists():
            sys.path.insert(0, str(pasta))
            break
    else:
        sys.exit("nao achei painel/database.py; rode este script ao lado da pasta painel/")

    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("SUPABASE_DB_URL", None)
    from database import _SCHEMA_SQLITE  # noqa: PLC0415 - import tardio de proposito

    return _SCHEMA_SQLITE


def _colunas(con, tabela: str) -> list[str]:
    return [r[1] for r in con.execute(f"PRAGMA table_info({tabela})")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--origem", required=True, help="connection string do Postgres de origem")
    ap.add_argument("--destino", required=True, help="caminho do painel.db de destino")
    args = ap.parse_args()

    try:
        import psycopg
    except ImportError:
        sys.exit("psycopg nao instalado neste Python (use o venv do painel)")

    destino = Path(args.destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    sqlite = sqlite3.connect(destino)
    sqlite.executescript(_schema_do_painel())
    sqlite.commit()

    preenchidas = []
    for tabela in TABELAS:
        try:
            total = sqlite.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
        except sqlite3.Error:
            continue
        if total:
            preenchidas.append(f"{tabela}={total}")
    if preenchidas:
        sqlite.close()
        sys.exit("destino ja tem dados (" + ", ".join(preenchidas) + "); abortando sem tocar em nada")

    with psycopg.connect(args.origem, connect_timeout=20) as pg:
        resumo = []
        for tabela in TABELAS:
            existe = pg.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s",
                (tabela,),
            ).fetchone()
            if not existe:
                resumo.append(f"{tabela}=ausente")
                continue

            colunas_pg = [
                r[0]
                for r in pg.execute(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema='public' AND table_name=%s
                    ORDER BY ordinal_position
                    """,
                    (tabela,),
                )
            ]
            colunas_sqlite = _colunas(sqlite, tabela)
            comuns = [c for c in colunas_pg if c in colunas_sqlite]
            if not comuns:
                resumo.append(f"{tabela}=sem colunas em comum")
                continue

            lista = ", ".join(comuns)
            linhas = pg.execute(f"SELECT {lista} FROM {tabela} ORDER BY id").fetchall()
            marcadores = ", ".join("?" * len(comuns))
            sqlite.executemany(
                f"INSERT INTO {tabela} ({lista}) VALUES ({marcadores})",
                [tuple(linha) for linha in linhas],
            )
            sqlite.commit()
            resumo.append(f"{tabela}={len(linhas)}")

        print("migrado: " + " | ".join(resumo))

        print("conferencia (origem x destino):")
        for tabela in TABELAS:
            existe = pg.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s",
                (tabela,),
            ).fetchone()
            origem = pg.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0] if existe else "n/a"
            try:
                destino_qtd = sqlite.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
            except sqlite3.Error:
                destino_qtd = "n/a"
            print(f"  {tabela}: origem={origem} destino={destino_qtd}")

    sqlite.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
