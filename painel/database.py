"""Banco do Painel SaaS VendaFácil.

Guarda os ADMINs (você, dono do sistema), as CONTAS das lojas (cada mercado
que compra/aluga o sistema) e um espelho das VENDAS sincronizadas pelos PDVs
para você acompanhar de forma centralizada.

Dois backends, escolhidos automaticamente:
  • Postgres (Supabase/Render) — quando DATABASE_URL (ou SUPABASE_DB_URL)
    está definido. É o modo de produção na nuvem.
  • SQLite local — fallback para desenvolvimento e VPS, em ./dados/painel.db.
"""
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _data_dir() -> Path:
    env = os.environ.get("PAINEL_DATA_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent / "dados"


DATA_DIR = _data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "painel.db"

# String de conexão Postgres (Supabase). Ex.:
#   postgresql://postgres:SENHA@db.<ref>.supabase.co:5432/postgres
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")


def agora() -> str:
    return datetime.now(timezone.utc).isoformat()


# DDL por dialeto: a única diferença real é o tipo da PK autoincremento e o
# tipo numérico das vendas.
_SCHEMA_SQLITE = """
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        nome TEXT NOT NULL,
        senha_hash TEXT NOT NULL,
        criado_em TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS contas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_loja TEXT NOT NULL,
        login TEXT NOT NULL UNIQUE,
        senha_hash TEXT NOT NULL,
        ativo INTEGER NOT NULL DEFAULT 1,
        plano TEXT NOT NULL DEFAULT 'mensal',
        licenca_expira_em TEXT,
        observacao TEXT,
        criado_em TEXT NOT NULL,
        ultimo_acesso TEXT
    );
    CREATE TABLE IF NOT EXISTS vendas_sync (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conta_id INTEGER NOT NULL,
        venda_uuid TEXT NOT NULL,
        total REAL NOT NULL,
        desconto REAL NOT NULL DEFAULT 0,
        forma_pagamento TEXT,
        criado_em_local TEXT,
        recebido_em TEXT NOT NULL,
        payload TEXT,
        UNIQUE(conta_id, venda_uuid)
    );
"""

_SCHEMA_PG = """
    CREATE TABLE IF NOT EXISTS admins (
        id SERIAL PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        nome TEXT NOT NULL,
        senha_hash TEXT NOT NULL,
        criado_em TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS contas (
        id SERIAL PRIMARY KEY,
        nome_loja TEXT NOT NULL,
        login TEXT NOT NULL UNIQUE,
        senha_hash TEXT NOT NULL,
        ativo INTEGER NOT NULL DEFAULT 1,
        plano TEXT NOT NULL DEFAULT 'mensal',
        licenca_expira_em TEXT,
        observacao TEXT,
        criado_em TEXT NOT NULL,
        ultimo_acesso TEXT
    );
    CREATE TABLE IF NOT EXISTS vendas_sync (
        id SERIAL PRIMARY KEY,
        conta_id INTEGER NOT NULL,
        venda_uuid TEXT NOT NULL,
        total DOUBLE PRECISION NOT NULL,
        desconto DOUBLE PRECISION NOT NULL DEFAULT 0,
        forma_pagamento TEXT,
        criado_em_local TEXT,
        recebido_em TEXT NOT NULL,
        payload TEXT,
        UNIQUE(conta_id, venda_uuid)
    );
"""


class Database:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.pg = bool(DATABASE_URL)
        if self.pg:
            import psycopg
            from psycopg.rows import dict_row
            self._psycopg = psycopg
            self._integrity_errors: tuple = (psycopg.errors.UniqueViolation,
                                             psycopg.IntegrityError)
            self._conn = psycopg.connect(
                DATABASE_URL, autocommit=True, row_factory=dict_row
            )
        else:
            self._integrity_errors = (sqlite3.IntegrityError,)
            self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            with self._conn:
                self._conn.execute("PRAGMA journal_mode = WAL")
        self._init_schema()

    # ── Infra ──
    def _ph(self, sql: str) -> str:
        """SQLite usa '?'; Postgres usa '%s'."""
        return sql.replace("?", "%s") if self.pg else sql

    def _init_schema(self) -> None:
        ddl = _SCHEMA_PG if self.pg else _SCHEMA_SQLITE
        with self._lock:
            if self.pg:
                with self._conn.cursor() as cur:
                    cur.execute(ddl)
            else:
                with self._conn:
                    self._conn.executescript(ddl)

    def _fetchone(self, sql: str, params: tuple = ()) -> Optional[dict]:
        with self._lock:
            cur = self._conn.cursor()
            try:
                cur.execute(self._ph(sql), params)
                row = cur.fetchone()
            finally:
                cur.close()
            return dict(row) if row else None

    def _fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._lock:
            cur = self._conn.cursor()
            try:
                cur.execute(self._ph(sql), params)
                rows = cur.fetchall()
            finally:
                cur.close()
            return [dict(r) for r in rows]

    def _exec(self, sql: str, params: tuple = ()) -> int:
        """Executa um write e devolve rowcount."""
        with self._lock:
            cur = self._conn.cursor()
            try:
                cur.execute(self._ph(sql), params)
                if not self.pg:
                    self._conn.commit()
                return cur.rowcount
            finally:
                cur.close()

    def _insert_id(self, sql: str, params: tuple) -> Optional[int]:
        """INSERT que retorna o id gerado. None se violou UNIQUE."""
        with self._lock:
            cur = self._conn.cursor()
            try:
                if self.pg:
                    cur.execute(self._ph(sql) + " RETURNING id", params)
                    return cur.fetchone()["id"]
                cur.execute(sql, params)
                self._conn.commit()
                return cur.lastrowid
            except self._integrity_errors:
                return None
            finally:
                cur.close()

    # ── Admins ──
    def get_admin_by_email(self, email: str) -> Optional[dict]:
        return self._fetchone("SELECT * FROM admins WHERE email = ?", (email.lower(),))

    def count_admins(self) -> int:
        row = self._fetchone("SELECT COUNT(*) AS c FROM admins")
        return int(row["c"]) if row else 0

    def create_admin(self, email: str, nome: str, senha_hash: str) -> Optional[dict]:
        new_id = self._insert_id(
            "INSERT INTO admins (email, nome, senha_hash, criado_em) VALUES (?,?,?,?)",
            (email.lower(), nome, senha_hash, agora()),
        )
        if new_id is None:
            return None
        return {"id": new_id, "email": email.lower(), "nome": nome}

    # ── Contas (lojas) ──
    def listar_contas(self) -> list[dict]:
        return self._fetchall(
            "SELECT id, nome_loja, login, ativo, plano, licenca_expira_em, "
            "observacao, criado_em, ultimo_acesso FROM contas ORDER BY criado_em DESC"
        )

    def get_conta_by_login(self, login: str) -> Optional[dict]:
        return self._fetchone("SELECT * FROM contas WHERE login = ?", (login.lower(),))

    def get_conta(self, conta_id: int) -> Optional[dict]:
        return self._fetchone("SELECT * FROM contas WHERE id = ?", (conta_id,))

    def criar_conta(
        self, nome_loja: str, login: str, senha_hash: str, plano: str,
        licenca_expira_em: Optional[str], observacao: Optional[str],
    ) -> Optional[dict]:
        new_id = self._insert_id(
            "INSERT INTO contas (nome_loja, login, senha_hash, ativo, plano, "
            "licenca_expira_em, observacao, criado_em) VALUES (?,?,?,1,?,?,?,?)",
            (nome_loja, login.lower(), senha_hash, plano,
             licenca_expira_em, observacao, agora()),
        )
        if new_id is None:
            return None
        return self.get_conta(new_id)

    def atualizar_conta(self, conta_id: int, campos: dict) -> bool:
        if not campos:
            return False
        permitidos = {"nome_loja", "ativo", "plano", "licenca_expira_em",
                      "observacao", "senha_hash"}
        sets, vals = [], []
        for k, v in campos.items():
            if k in permitidos:
                sets.append(f"{k} = ?")
                vals.append(v)
        if not sets:
            return False
        vals.append(conta_id)
        return self._exec(
            f"UPDATE contas SET {', '.join(sets)} WHERE id = ?", tuple(vals)
        ) > 0

    def marcar_acesso(self, conta_id: int) -> None:
        self._exec(
            "UPDATE contas SET ultimo_acesso = ? WHERE id = ?", (agora(), conta_id)
        )

    # ── Vendas sincronizadas ──
    def registrar_venda_sync(self, conta_id: int, v: dict) -> bool:
        import json
        new_id = self._insert_id(
            "INSERT INTO vendas_sync (conta_id, venda_uuid, total, desconto, "
            "forma_pagamento, criado_em_local, recebido_em, payload) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (conta_id, v.get("uuid"), float(v.get("total", 0)),
             float(v.get("desconto", 0)), v.get("forma_pagamento"),
             v.get("criado_em"), agora(), json.dumps(v, ensure_ascii=False)),
        )
        return new_id is not None  # None = já recebida (idempotente)

    def resumo_vendas(self, conta_id: int) -> dict:
        row = self._fetchone(
            "SELECT COUNT(*) AS qtd, COALESCE(SUM(total),0) AS total "
            "FROM vendas_sync WHERE conta_id = ?", (conta_id,)
        )
        return {"qtd_vendas": row["qtd"], "total_vendido": row["total"]}


db = Database()
